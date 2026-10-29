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
    @Override public JSONArray models() throws Exception {
        JSONArray result = new JSONArray(), text = app.store.snapshot(); java.util.Set<String> aliases = new java.util.HashSet<>();
        for (int i = 0; i < text.length(); i++) {
            JSONObject model = text.getJSONObject(i); if (!model.optBoolean("installed")) continue;
            String id = model.getString("id"); if (!model.optString("bundleId").isEmpty()) aliases.add(model.getString("bundleId"));
            result.put(new JSONObject().put("id", id).put("object", "model").put("owned_by", "local").put("name", model.getString("name"))
                    .put("task_tags", new JSONArray().put("text")).put("foundation_tags", model.getJSONArray("baseSupportTags"))
                    .put("uncensored", model.optJSONObject("uncensored") == null ? new JSONObject().put("status", "unknown") : model.getJSONObject("uncensored"))
                    .put("engine", "llama_text").put("bundle_id", model.optString("bundleId")).put("installed", true)
                    .put("loaded", id.equals(app.engineModel) && owner.engine.ready()).put("parameters", model.getJSONObject("config")));
        }
        if (app.bundles != null) {
            JSONArray bundles = app.bundles.snapshot();
            for (int i = 0; i < bundles.length(); i++) {
                JSONObject record = bundles.getJSONObject(i);
                JSONArray derived = app.prepared == null ? new JSONArray() : app.assemblies == null ? app.prepared.snapshot(record.getString("id")) : app.assemblies.snapshot(record.getString("id"));
                if (!record.optBoolean("installed") && derived.length() == 0 && (!record.has("transfer") || record.getJSONObject("plan").optLong("reusableBytes") == 0)) continue;
                ModelBundle bundle = app.bundles.bundle(record.getString("id")); if (aliases.contains(bundle.id)) continue;
                result.put(new JSONObject().put("id", bundle.id).put("model_id", bundle.modelId).put("object", "model").put("owned_by", "local").put("name", bundle.name)
                        .put("task_tags", new JSONArray(bundle.tasks)).put("tags", bundle.tags()).put("uncensored", new JSONObject().put("status", "unknown"))
                        .put("input_schemas", app.localEngines.inputSchemas(bundle)).put("engine", bundle.engine).put("recipe", bundle.recipeId).put("backend", bundle.backend)
                        .put("preparation_plans", app.preparations == null ? new JSONArray() : app.preparations.options(bundle)).put("prepared_assets", derived)
                        .put("installed", record.optBoolean("installed")).put("reusable_bytes", record.getJSONObject("plan").optLong("reusableBytes")).put("remaining_bytes", record.getJSONObject("plan").optLong("remainingBytes"))
                        .put("loaded", record.optBoolean("inUse")).put("parameters", record.getJSONObject("config")).put("parameter_error", record.optString("parameterError")).put("version", record.getJSONObject("version")).put("deviceValidated", false));
            }
        }
        return result;
    }
    @Override public JSONArray engines() throws Exception { return app.localEngines == null ? new JSONArray() : app.localEngines.snapshot(); }
    @Override public void draftsChanged() { app.emit(); }
    @Override public void jobsChanged() { app.emit(); }
    @Override public TaskDrafts drafts() throws Exception { if (app.taskDrafts == null) throw new IOException("Draft storage is unavailable"); return app.taskDrafts; }
    @Override public JobStore jobs() throws Exception { if (app.jobs == null) throw new IOException("任务存储不可用"); return app.jobs; }
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
            if (!owner.engine.wanted()) throw new IllegalStateException("请先在 App 中选择并加载已安装的文本模型");
            if (app.generating || app.textRequestBusy) throw new IllegalStateException("本机推理槽正忙，请等待当前任务完成");
            request = TextRequest.normalize(path, input, app.engineModel, app.settings(app.engineModel));
            slot = app.execution.enqueue("api", app.engineModel); textSlot = slot; app.textRequestBusy = true;
        }
        owner.activityChanged(); HttpURLConnection connection = null;
        try {
            ExecutionGate.Check check = () -> { if (closed || server == null || cancellation.get() != ticket || Thread.currentThread().isInterrupted()) throw new InterruptedIOException("文本请求已取消"); };
            slot.await(check); owner.engine.ensureReady(slot, request.getString("model"), check); check.run();
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
                    int count = super.read(bytes, offset, length); if (count > 0 && (received += count) > 16L * 1024 * 1024) throw new IOException("文本响应超出应用的 16 MiB 保护上限"); return count;
                }
                @Override public void close() throws IOException { if (!released) { released = true; try { super.close(); } finally { releaseText(active, slot); } } }
            };
            return LocalHttp.Response.stream(200, mime, connection.getContentLengthLong(), in).header("X-LMA-Max-Tokens", String.valueOf(request.getInt("max_tokens")));
        } catch (Exception error) { releaseText(connection, slot); throw error; }
    }
    private void releaseText(HttpURLConnection connection, ExecutionGate.Ticket slot) {
        if (connection != null) connection.disconnect();
        synchronized (app.requestGate) { if (textSlot == slot) { textSlot = null; if (textConnection == connection) textConnection = null; app.textRequestBusy = false; } }
        slot.close(); owner.engine.resumeIfIdle(); owner.activityChanged();
    }
}
