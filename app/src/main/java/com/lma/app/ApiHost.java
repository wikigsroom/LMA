package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;

/** Foreground-service-owned public gateway; native text engines remain private loopback children. */
public final class ApiHost implements LocalApi.Runtime, AutoCloseable {
    private final LmaApp app;
    private final LmaService owner;
    private final LocalApi api;
    private volatile LocalHttp server;
    private int port;
    private boolean lan;
    private volatile boolean closed;
    private final java.util.concurrent.atomic.AtomicLong cancellation = new java.util.concurrent.atomic.AtomicLong();
    private final TextAdmission textAdmission = new TextAdmission();
    private final java.util.Map<ExecutionGate.Ticket, TextCall> textCalls = new java.util.LinkedHashMap<>();
    private final java.util.concurrent.ScheduledExecutorService textPulses = java.util.concurrent.Executors.newScheduledThreadPool(2, runnable -> { Thread thread = new Thread(runnable, "LMA-text-heartbeat"); thread.setDaemon(true); return thread; });
    private static final class TextCall {
        final JSONObject request; final ExecutionGate.Ticket slot; final TextAdmission.Lease admission; final long epoch; final int context;
        volatile HttpURLConnection connection; volatile boolean cancelled; volatile Thread thread; private boolean finished;
        JSONObject diagnostic;
        TextCall(JSONObject request, ExecutionGate.Ticket slot, TextAdmission.Lease admission, long epoch, int context) { this.request = request; this.slot = slot; this.admission = admission; this.epoch = epoch; this.context = context; }
        synchronized void cancel() { if (finished) return; cancelled = true; HttpURLConnection active = connection; if (active != null) active.disconnect(); Thread worker = thread; if (worker != null && worker != Thread.currentThread()) worker.interrupt(); }
        synchronized void finish() { finished = true; thread = null; }
    }
    public ApiHost(LmaService owner, LmaApp app) { this.owner = owner; this.app = app; api = new LocalApi(this); }
    // Bounded in-memory metadata only: no prompts, arguments, results, keys or personal file paths.
    private final java.util.ArrayDeque<JSONObject> toolDiagnostics = new java.util.ArrayDeque<>();
    public synchronized JSONArray toolDiagnostics() throws Exception { return new JSONArray(new JSONArray(toolDiagnostics).toString()); }
    private synchronized void traceText(TextCall call, int tokens) throws Exception {
        JSONArray tools = call.request.optJSONArray("tools"), names = new JSONArray(), results = new JSONArray();
        if (tools != null) for (int i = 0; i < tools.length(); i++) names.put(tools.getJSONObject(i).getJSONObject("function").getString("name"));
        JSONArray messages = call.request.optJSONArray("messages");
        if (messages != null) for (int i = 0; i < messages.length(); i++) { JSONObject m = messages.getJSONObject(i); if (m.optString("role").equals("tool")) results.put(m.getString("tool_call_id")); }
        if (names.length() == 0 && results.length() == 0) return;
        call.diagnostic = new JSONObject().put("model", call.request.getString("model")).put("toolCount", names.length()).put("toolNames", names)
            .put("toolDefinitionsSha256", TemplateProfiles.hash(tools == null ? "[]" : tools.toString())).put("inputTokens", tokens)
            .put("toolResultIds", results).put("toolChoice", call.request.opt("tool_choice")).put("stream", call.request.optBoolean("stream"))
            .put("template", TemplateProfiles.status(call.request.getString("model"))).put("delivery", "generating");
        if (toolDiagnostics.size() >= 12) toolDiagnostics.removeFirst(); toolDiagnostics.addLast(call.diagnostic);
    }
    private synchronized void traceReply(TextCall call, JSONObject message, String finish) throws Exception {
        if (call.diagnostic == null) return;
        JSONArray calls = message.optJSONArray("tool_calls"), summary = new JSONArray();
        if (calls != null) for (int i = 0; i < calls.length(); i++) {
            JSONObject c = calls.getJSONObject(i), f = c.getJSONObject("function");
            summary.put(new JSONObject().put("id", c.getString("id")).put("name", f.getString("name")).put("argumentsSha256", TemplateProfiles.hash(f.getString("arguments"))));
        }
        call.diagnostic.put("delivery", "validated").put("finishReason", finish).put("calls", summary);
    }
    private synchronized void traceFailure(TextCall call, String code) throws Exception {
        if (call.diagnostic != null) call.diagnostic.put("delivery", "failed").put("errorCode", code);
    }
    public synchronized boolean ready() { return !closed && server != null; }
    public boolean wanted() { return app.prefs.getBoolean("desiredApi", false); }
    public synchronized void start() throws Exception {
        configure(app.prefs.getInt("port", com.lma.app.core.ApiPort.DEFAULT), app.prefs.getBoolean("lan", false));
        app.prefs.edit().putBoolean("desiredApi", true).apply(); owner.activityChanged();
    }
    public synchronized void configure(int nextPort, boolean nextLan) throws Exception {
        if (closed) throw new IllegalStateException("接口服务正在停止");
        if (server != null && port == nextPort && lan == nextLan) return;
        if (app.textRequestBusy) throw new IllegalStateException("请先完成或停止文本请求，再修改接口监听地址");
        LocalHttp previous = server;
        if (previous != null && port == nextPort) { previous.close(); server = null; }
        try {
            LocalHttp replacement = new LocalHttp(nextLan ? "0.0.0.0" : "127.0.0.1", nextPort, api);
            if (previous != null) previous.close(); server = replacement; port = nextPort; lan = nextLan;
            app.apiState = "ready"; app.apiDetail = nextLan ? "接口已启动 · 手机执行，允许局域网客户端" : "接口已启动 · 仅本机客户端";
        } catch (IOException error) {
            if (previous != null && server == null) try { server = new LocalHttp(lan ? "0.0.0.0" : "127.0.0.1", port, api); }
            catch (IOException restore) { app.apiState = "error"; app.apiDetail = "原接口监听恢复失败"; }
            if (server == null) { app.apiState = "error"; app.apiDetail = "接口端口不可用：" + nextPort; }
            throw new IOException("接口端口 " + nextPort + " 已被占用或不能监听，请更换端口", error);
        }
        app.emit();
    }
    public synchronized void stop() {
        app.prefs.edit().putBoolean("desiredApi", false).apply(); closeListener(); app.apiState = "stopped"; app.apiDetail = "模型接口已关闭"; owner.activityChanged();
    }
    private void closeListener() { if (server != null) server.close(); server = null; cancelText(); }
    public void cancelText() { cancellation.incrementAndGet(); synchronized (app.requestGate) { for (TextCall call : textCalls.values()) call.cancel(); } }
    @Override public synchronized void close() { closed = true; closeListener(); textPulses.shutdownNow(); app.apiState = "stopped"; }
    @Override public InputUploads uploads() throws Exception { if (app.uploads == null) throw new IllegalStateException("Input upload storage is unavailable"); return app.uploads; }
    @Override public String apiKey() { return app.prefs.getString("apiKey", ""); }
    @Override public JSONObject health() throws Exception {
        return new JSONObject().put("status", "ok").put("version", LmaApp.VERSION).put("execution", "same_android_phone")
                .put("scheduler", app.execution.snapshot()).put("textQueue", textAdmission.snapshot()).put("textState", app.engineState).put("textRequestActive", app.textRequestBusy).put("jobActive", app.jobHost == null ? "" : app.jobHost.activeId())
                .put("toolTemplate", TemplateProfiles.status(app.engineModel)).put("recentToolRequests", toolDiagnostics())
                .put("foundationReady", app.jobs != null && app.artifacts != null && app.localEngines != null).put("modelInferenceTested", false);
    }
    private ApiCatalogue catalogue;
    private ApiSubmissions submissionJournal;
    private synchronized ApiCatalogue catalogueStore() throws Exception {
        if (catalogue == null) catalogue = new ApiCatalogue(new File(app.getFilesDir(), "api"), new ModelPublication(app, owner.engine));
        return catalogue;
    }
    @Override public JSONArray models() throws Exception { return catalogue().getJSONArray("data"); }
    @Override public JSONObject catalogue() throws Exception { return catalogueStore().snapshot(); }
    @Override public JSONObject model(String id) throws Exception { return catalogueStore().model(id); }
    public void invalidateCatalogue() { synchronized (this) { if (catalogue != null) catalogue.invalidate(); } }
    @Override public JSONObject capabilities() throws Exception {
        JSONObject snapshot = catalogue(), metadata = snapshot.getJSONObject("x_lma");
        JSONObject limits = new JSONObject().put("json_body_bytes", LocalHttp.MAX_BODY).put("text_json_body_bytes", LocalHttp.MAX_TEXT_BODY).put("text_messages_max", ChatProtocol.MAX_MESSAGES).put("text_message_utf8_bytes", ChatProtocol.MAX_TEXT_BYTES).put("text_requests_max", TextAdmission.MAX_REQUESTS).put("text_queue_bytes", TextAdmission.MAX_BYTES).put("function_tools", true).put("tool_execution", "client").put("strict_output_validation", "before_delivery").put("image_n_max", 1).put("image_formats", new JSONArray().put("png"))
                .put("speech_formats", new JSONArray().put("wav")).put("sse_lifetime_seconds", 120).put("sse_connections", 2).put("heavy_execution_slots", 1)
                .put("upload_chunk_bytes", LocalHttp.MAX_BODY).put("input_file_bytes_max", 536870912).put("sync_wait_seconds", 120).put("generation_wall_time_seconds", JSONObject.NULL).put("catalogue_idle_reads", "cached_metadata_only");
        return new JSONObject().put("schema", "lma.capabilities/1").put("instance_id", metadata.getString("instance_id")).put("catalogue", metadata)
                .put("models", snapshot.getJSONArray("data")).put("chat_input_types",new JSONArray().put("text")).put("app_visual_bridge",new JSONObject().put("input_types",new JSONArray().put("image").put("sampled_video_frames")).put("requires_reviewed_component_pair",true)).put("tools",new JSONArray().put(new JSONObject().put("id",CompositionSpec.ID).put("type","media.compose").put("input_schema",CompositionSpec.inputs().json()).put("parameters",new JSONObject().put("durationSeconds","5.1–60").put("voiceGain","0–2").put("musicGain","0–2")))).put("task_chains",new JSONObject().put("endpoint","/v1/lma/chains").put("max_steps",8).put("requires_idempotency_key",true)).put("limits", limits).put("profiles", new JSONArray().put("openai_subset").put("lma_extension")).put("execution", "same_android_phone");
    }
    @Override public synchronized ApiSubmissions submissions() throws Exception {
        if (submissionJournal == null) submissionJournal = new ApiSubmissions(new File(app.getFilesDir(), "api"));
        return submissionJournal;
    }
    @Override public JSONObject freezePublic(JSONObject request) throws Exception { return LocalJobs.freezePublic(app, request); }
    @Override public boolean localComposition(){return true;}
    @Override public com.lma.app.core.WorkflowStore workflows()throws Exception{if(app.workflows==null)throw new IOException("计划存储不可用");return app.workflows;}
    @Override public JSONObject createChain(JSONObject draft,String key)throws Exception{if(app.conversations==null)throw new IOException("计划服务不可用");return app.conversations.chain(new JSONObject().put("draft",draft).put("idempotencyKey",key));}
    @Override public void workflowsChanged(){if(app.conversations!=null)app.conversations.wake();app.emit();}
    @Override public String adapter(String id) throws Exception {
        ModelBundle bundle = app.bundles.bundle(ModelBundle.key(id));
        if (!AdapterSpec.isAdapter(bundle) || !app.bundles.plan(id).getBoolean("installed")) throw new LocalHttp.Failure(404, "lma_adapter_unavailable", "Select a complete installed LoRA component");
        return bundle.id;
    }
    @Override public JSONArray engines() throws Exception { return app.localEngines == null ? new JSONArray() : app.localEngines.snapshot(); }
    @Override public void draftsChanged() { app.emit(); }
    @Override public void jobsChanged() { app.emit(); }
    @Override public TaskDrafts drafts() throws Exception { if (app.taskDrafts == null) throw new IOException("Draft storage is unavailable"); return app.taskDrafts; }
    @Override public JobStore jobs() throws Exception { if (app.jobs == null) throw new IOException("任务存储不可用"); return app.jobs; }
    @Override public AudioStreams audioStreams() throws Exception { if (app.audioStreams == null) throw new IOException("音频试听暂不可用"); return app.audioStreams; }
    @Override public ArtifactStore artifacts() throws Exception { if (app.artifacts == null) throw new IOException("产物存储不可用"); return app.artifacts; }
    @Override public JSONObject preflight(JSONObject request) throws Exception { return LocalJobs.preflight(app, request); }
    @Override public JSONObject submit(JSONObject request, String idempotencyKey) throws Exception {
        LocalJobs jobs = app.jobHost; if (jobs == null) throw new IOException("任务运行器不可用"); return jobs.submit(request, idempotencyKey);
    }
    @Override public void cancel(String id) throws Exception { LocalJobs jobs = app.jobHost; if (jobs == null) throw new IOException("任务运行器不可用"); jobs.cancel(id); }
    @Override public LocalHttp.Response text(String path, JSONObject input) throws Exception {
        final TextCall call;
        synchronized (app.requestGate) {
            if (closed || server == null) throw new IOException("模型接口正在停止");
            String selected = input.optString("model", app.engineModel); OpenAiRequests.model(this, selected, "text.generate");
            JSONObject settings = app.settings(selected), request = TextRequest.normalize(path, input, selected, settings);
            TextAdmission.Lease admission = textAdmission.acquire(input.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
            try { ExecutionGate.Ticket slot = app.execution.enqueue("api", selected); call = new TextCall(request, slot, admission, cancellation.get(), settings.getInt("context")); textCalls.put(slot, call); app.textRequestBusy = true; }
            catch (Exception error) { admission.close(); throw error; }
        }
        owner.activityChanged(); final String requestId = "lma-" + java.util.UUID.randomUUID().toString();
        if (call.request.optBoolean("stream")) {
            return new LocalHttp.Response(200, "text/event-stream; charset=utf-8", -1, new LocalHttp.Body() {
                @Override public void write(OutputStream out) throws Exception {
                    call.thread = Thread.currentThread();
                    java.util.concurrent.ScheduledFuture<?> heartbeat = textPulses.scheduleWithFixedDelay(() -> {
                        try { ToolReply.write(out, ": lma keepalive\n\n".getBytes(java.nio.charset.StandardCharsets.UTF_8)); }
                        catch (IOException error) { call.cancel(); }
                    }, 2, 8, java.util.concurrent.TimeUnit.SECONDS);
                    try {
                        HttpURLConnection connection = openText(call, path); ToolReply guard = new ToolReply(call.request, (message, finish) -> traceReply(call, message, finish));
                        try (InputStream in = connection.getInputStream()) { guard.stream(in, out); }
                        call.slot.finishResourceMonitoring();
                    } catch (Exception error) {
                        String resourceFailure = call.slot.resourceFailure();
                        String code = !resourceFailure.isEmpty() ? "resource_limit_exceeded" : error instanceof LocalHttp.Failure ? ((LocalHttp.Failure)error).code : call.cancelled ? "request_cancelled" : "invalid_model_output";
                        traceFailure(call, code);
                        String param = error instanceof LocalHttp.Failure ? ((LocalHttp.Failure)error).param : error instanceof RequestError ? ((RequestError)error).param : null;
                        String message = LocalApi.safeMessage(!resourceFailure.isEmpty() ? resourceFailure : error.getMessage() == null ? "Local text request failed" : error.getMessage());
                        JSONObject detail = new JSONObject().put("message", message).put("type", "lma_local_error").put("code", code).put("param", param == null ? JSONObject.NULL : param).put("request_id", requestId);
                        try { ToolReply.write(out, ("data: " + new JSONObject().put("error", detail).toString() + "\n\n").getBytes(java.nio.charset.StandardCharsets.UTF_8)); } catch (IOException disconnected) { call.cancel(); }
                    } finally { heartbeat.cancel(false); releaseText(call); }
                }
                @Override public void close() { call.cancel(); releaseText(call); }
            }).header("X-Request-ID", requestId).header("X-LMA-Max-Tokens", String.valueOf(call.request.getInt("max_tokens")));
        }
        try {
            call.thread = Thread.currentThread(); HttpURLConnection connection = openText(call, path); ToolReply guard = new ToolReply(call.request, (message, finish) -> traceReply(call, message, finish));
            if (guard.enabled()) {
                byte[] bytes; try (InputStream in = connection.getInputStream()) { bytes = guard.complete(in); }
                call.slot.finishResourceMonitoring(); releaseText(call);
                return LocalHttp.Response.bytes(200, "application/json; charset=utf-8", bytes).header("X-Request-ID", requestId).header("X-LMA-Max-Tokens", String.valueOf(call.request.getInt("max_tokens")));
            }
            InputStream in = new FilterInputStream(connection.getInputStream()) {
                private long received;
                @Override public int read() throws IOException { byte[] one = new byte[1]; return read(one, 0, 1) < 0 ? -1 : one[0] & 255; }
                @Override public int read(byte[] bytes, int offset, int length) throws IOException { checkText(call); call.slot.checkOwner(); int count = super.read(bytes, offset, length); if (count < 0) call.slot.finishResourceMonitoring(); if (count > 0 && (received += count) > ToolReply.MAX_RESPONSE_BYTES) throw new IOException("Text response exceeds 16 MiB"); return count; }
                @Override public void close() throws IOException { try { super.close(); } finally { releaseText(call); } }
            };
            return LocalHttp.Response.stream(200, "application/json; charset=utf-8", connection.getContentLengthLong(), in).header("X-Request-ID", requestId).header("X-LMA-Max-Tokens", String.valueOf(call.request.getInt("max_tokens")));
        } catch (Exception error) { String resourceFailure = call.slot.resourceFailure(); traceFailure(call, error instanceof LocalHttp.Failure ? ((LocalHttp.Failure)error).code : call.cancelled ? "request_cancelled" : "invalid_model_output"); releaseText(call); if (!resourceFailure.isEmpty()) throw new LocalHttp.Failure(503, "resource_limit_exceeded", resourceFailure); if (error instanceof LocalHttp.Failure || error instanceof RequestError) throw error; throw new LocalHttp.Failure(call.cancelled ? 409 : 502, call.cancelled ? "request_cancelled" : "invalid_model_output", LocalApi.safeMessage(error.getMessage())); }
    }
    private void checkText(TextCall call) throws IOException { if (closed || server == null || call.cancelled || cancellation.get() != call.epoch || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("文本请求已取消"); }
    private HttpURLConnection openText(TextCall call, String path) throws Exception {
        ExecutionGate.Check check = () -> checkText(call); call.slot.await(check);
        owner.engine.selectForApi(call.slot, call.request.getString("model"), check); owner.engine.ensureReady(call.slot, call.request.getString("model"), check); check.run();
        if (path.equals("/v1/chat/completions")) TemplateProfiles.admit(call.request.getString("model"), call.request);
        JSONObject wire = NativeToolRequest.adapt(call.request);
        String prompt = path.equals("/v1/chat/completions") ? nativeJson(call, "/apply-template", wire).getString("prompt") : call.request.getString("prompt");
        // Match pinned server-context.cpp tokenize_input_prompts(..., true, true).
        // The model vocabulary decides whether BOS/EOS are needed; counting only
        // the rendered text can otherwise admit a full prompt with no output room.
        JSONObject tokens = nativeJson(call, "/tokenize", new JSONObject().put("content", prompt).put("add_special", true).put("parse_special", true));
        int inputTokens = tokens.getJSONArray("tokens").length(), available = call.context - inputTokens;
        if (available < 1) throw new LocalHttp.Failure(400, "context_length_exceeded", "The rendered conversation and tools exceed the selected model context (" + inputTokens + " input tokens / " + call.context + " context)", path.equals("/v1/chat/completions") ? "messages" : "prompt");
        call.request.put("max_tokens", Math.min(call.request.getInt("max_tokens"), available));
        traceText(call, inputTokens);
        wire.put("max_tokens", call.request.getInt("max_tokens"));
        check.run(); HttpURLConnection connection = Net.engine(app, path); call.connection = connection;
        connection.setRequestMethod("POST"); connection.setDoOutput(true); connection.setRequestProperty("Content-Type", "application/json; charset=utf-8"); connection.setRequestProperty("Accept", call.request.optBoolean("stream") ? "text/event-stream" : "application/json");
        byte[] bytes = wire.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8); connection.setFixedLengthStreamingMode(bytes.length);
        try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
        int status = connection.getResponseCode(); if (status != 200) throw nativeFailure(connection, status); check.run(); return connection;
    }
    private JSONObject nativeJson(TextCall call, String path, JSONObject body) throws Exception {
        checkText(call); HttpURLConnection connection = Net.engine(app, path); call.connection = connection;
        try {
            connection.setRequestMethod("POST"); connection.setDoOutput(true); connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] bytes = body.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8); connection.setFixedLengthStreamingMode(bytes.length); try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            int status = connection.getResponseCode(); if (status != 200) throw nativeFailure(connection, status);
            try (InputStream in = connection.getInputStream()) { JSONObject value = new JSONObject(new String(ToolReply.read(in, ToolReply.MAX_RESPONSE_BYTES), java.nio.charset.StandardCharsets.UTF_8)); checkText(call); return value; }
        } finally { connection.disconnect(); if (call.connection == connection) call.connection = null; }
    }
    private LocalHttp.Failure nativeFailure(HttpURLConnection connection, int status) {
        String code = "text_engine_error", param = null, message = "The local text engine returned HTTP " + status;
        try (InputStream in = connection.getErrorStream()) {
            if (in != null) { JSONObject value = new JSONObject(new String(ToolReply.read(in, 128 * 1024), java.nio.charset.StandardCharsets.UTF_8)); JSONObject error = value.optJSONObject("error"); if (error == null) error = value; message = LocalApi.safeMessage(error.optString("message", message)); if (error.opt("code") instanceof String) code = error.getString("code"); if (error.opt("param") instanceof String) param = error.getString("param"); if (error.optString("type").contains("context") || code.contains("context")) code = "context_length_exceeded"; }
        } catch (Exception ignored) {}
        if (status >= 500 && message.startsWith("The model produced output that does not match the expected ")) {
            // Pinned native parser failure: distinguish invalid model output from
            // a transport/server outage. No partial function is sent for execution.
            status = 502; code = "invalid_model_output";
        }
        return new LocalHttp.Failure(status >= 400 && status <= 599 ? status : 502, code, message, param);
    }
    private void releaseText(TextCall call) {
        synchronized (app.requestGate) {
            if (textCalls.remove(call.slot) == null) return;
            call.finish();
            HttpURLConnection connection = call.connection; call.connection = null; if (connection != null) connection.disconnect();
            call.slot.close(); call.admission.close(); app.textRequestBusy = !textCalls.isEmpty();
        }
        owner.engine.resumeIfIdle(); owner.activityChanged();
    }
}
