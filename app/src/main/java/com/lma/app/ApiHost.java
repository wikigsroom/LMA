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
    private volatile HttpURLConnection textConnection;
    private volatile ExecutionGate.Ticket textSlot;
    public ApiHost(LmaService owner, LmaApp app) { this.owner = owner; this.app = app; api = new LocalApi(this); }
    public synchronized boolean ready() { return !closed && server != null; }
    public boolean wanted() { return app.prefs.getBoolean("desiredApi", false); }
    public synchronized void start() throws Exception {
        configure(app.prefs.getInt("port", 8080), app.prefs.getBoolean("lan", false));
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
    public void cancelText() { cancellation.incrementAndGet(); HttpURLConnection connection = textConnection; if (connection != null) connection.disconnect(); }
    @Override public synchronized void close() { closed = true; closeListener(); app.apiState = "stopped"; }
    @Override public InputUploads uploads() throws Exception { if (app.uploads == null) throw new IllegalStateException("Input upload storage is unavailable"); return app.uploads; }
    @Override public String apiKey() { return app.prefs.getString("apiKey", ""); }
    @Override public JSONObject health() throws Exception {
        return new JSONObject().put("status", "ok").put("version", LmaApp.VERSION).put("execution", "same_android_phone")
                .put("scheduler", app.execution.snapshot()).put("textState", app.engineState).put("textRequestActive", app.textRequestBusy).put("jobActive", app.jobHost == null ? "" : app.jobHost.activeId())
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
        JSONObject limits = new JSONObject().put("json_body_bytes", LocalHttp.MAX_BODY).put("image_n_max", 1).put("image_formats", new JSONArray().put("png"))
                .put("speech_formats", new JSONArray().put("wav")).put("sse_lifetime_seconds", 120).put("sse_connections", 2).put("heavy_execution_slots", 1)
                .put("upload_chunk_bytes", LocalHttp.MAX_BODY).put("input_file_bytes_max", 536870912).put("sync_wait_seconds", 120).put("generation_wall_time_seconds", JSONObject.NULL).put("catalogue_idle_reads", "cached_metadata_only");
        return new JSONObject().put("schema", "lma.capabilities/1").put("instance_id", metadata.getString("instance_id")).put("catalogue", metadata)
                .put("models", snapshot.getJSONArray("data")).put("limits", limits).put("profiles", new JSONArray().put("openai_subset").put("lma_extension")).put("execution", "same_android_phone");
    }
    @Override public synchronized ApiSubmissions submissions() throws Exception {
        if (submissionJournal == null) submissionJournal = new ApiSubmissions(new File(app.getFilesDir(), "api"));
        return submissionJournal;
    }
    @Override public JSONObject freezePublic(JSONObject request) throws Exception { return LocalJobs.freezePublic(app, request); }
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
        JSONObject request; ExecutionGate.Ticket slot; long ticket = cancellation.get();
        synchronized (app.requestGate) {
            if (closed || server == null) throw new IOException("模型接口正在停止");
            if (app.generating || app.textRequestBusy) throw new IllegalStateException("本机推理槽正忙，请等待当前任务完成");
            String selected = input.optString("model", app.engineModel); OpenAiRequests.model(this, selected, "text.generate");
            request = TextRequest.normalize(path, input, selected, app.settings(selected));
            slot = app.execution.enqueue("api", selected); textSlot = slot; app.textRequestBusy = true;
        }
        owner.activityChanged(); HttpURLConnection connection = null;
        try {
            ExecutionGate.Check check = () -> { if (closed || server == null || cancellation.get() != ticket || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("文本请求已取消"); };
            slot.await(check); owner.engine.selectForApi(slot, request.getString("model"), check); owner.engine.ensureReady(slot, request.getString("model"), check); check.run();
            connection = Net.engine(app, path); textConnection = connection;
            if (closed || server == null || ticket != cancellation.get()) throw new IOException("文本请求已取消");
            connection.setRequestMethod("POST"); connection.setDoOutput(true); connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("Accept", request.optBoolean("stream") ? "text/event-stream" : "application/json");
            byte[] payload = request.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8); connection.setFixedLengthStreamingMode(payload.length);
            try (OutputStream out = connection.getOutputStream()) { out.write(payload); }
            int status = connection.getResponseCode();
            if (status != 200) throw new LocalHttp.Failure(status >= 400 && status <= 599 ? status : 502, "text_engine_error", Net.errorBody(connection));
            String mime = request.optBoolean("stream") ? "text/event-stream; charset=utf-8" : "application/json; charset=utf-8";
            HttpURLConnection active = connection;
            InputStream in = new FilterInputStream(connection.getInputStream()) {
                private boolean released;
                private long received;
                @Override public int read() throws IOException { byte[] one = new byte[1]; return read(one, 0, 1) < 0 ? -1 : one[0] & 255; }
                @Override public int read(byte[] bytes, int offset, int length) throws IOException {
                    slot.checkOwner(); int count;
                    try { count = super.read(bytes, offset, length); } catch (IOException error) { slot.checkOwner(); throw error; }
                    slot.checkOwner(); if (count < 0) slot.finishResourceMonitoring();
                    if (count > 0 && (received += count) > 16L * 1024 * 1024) throw new IOException("文本响应超出应用的 16 MiB 保护上限"); return count;
                }
                @Override public void close() throws IOException { if (!released) { released = true; try { super.close(); } finally { releaseText(active, slot); } } }
            };
            return LocalHttp.Response.stream(200, mime, connection.getContentLengthLong(), in).header("X-LMA-Max-Tokens", String.valueOf(request.getInt("max_tokens")));
        } catch (Exception error) { String resourceFailure = slot.resourceFailure(); releaseText(connection, slot); if (!resourceFailure.isEmpty()) throw new IOException(resourceFailure, error); throw error; }
    }
    private void releaseText(HttpURLConnection connection, ExecutionGate.Ticket slot) {
        if (connection != null) connection.disconnect();
        synchronized (app.requestGate) { if (textSlot == slot) { textSlot = null; if (textConnection == connection) textConnection = null; app.textRequestBusy = false; } }
        slot.close(); owner.engine.resumeIfIdle(); owner.activityChanged();
    }
}
