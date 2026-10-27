package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Queue-owned execution of the existing signed llama server, on private phone loopback only. */
public final class TextEngine implements LocalEngine {
    interface Launcher { Process start(ProcessBuilder builder) throws IOException; }
    private final LmaApp app;
    private final File binary;
    private final JSONObject build;
    private final Launcher launcher;
    private final java.util.concurrent.ConcurrentMap<String, JSONObject> metadataCache = new java.util.concurrent.ConcurrentHashMap<>();
    private JSONObject metadata(ModelBundle bundle) throws Exception {
        if (!app.bundles.plan(bundle.id).optBoolean("installed")) return new JSONObject().put("source", "unknown").put("contextLength", 0);
        String identity = bundle.components.get(0).objectId;
        if (!metadataCache.containsKey(identity)) try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) { metadataCache.put(identity, GgufMetadata.read(lease.file("text_gguf"))); }
        return DataFiles.copy(metadataCache.get(identity));
    }
    public ParameterSchema schema(ModelBundle bundle) throws Exception { TextSpec.validate(bundle, "text.generate"); return new ParameterSchema(ModelSettings.runtimeSchema(bundle.parameters().json(), metadata(bundle))); }
    public TextEngine(LmaApp app, File binary, JSONObject build) { this(app, binary, build, ProcessBuilder::start); }
    TextEngine(LmaApp app, File binary, JSONObject build, Launcher launcher) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); this.launcher = launcher; }
    @Override public String id() { return "llama_text"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        TextSpec.validate(bundle, type);
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 缺少签名文本运行引擎");
    }
    static JSONObject parameters(JSONObject requested, JSONObject metadata) throws Exception {
        for (Iterator<String> it = requested.keys(); it.hasNext();) if (!TextSpec.FIELDS.contains(it.next())) throw new IOException("未知文本模型参数");
        JSONObject result = ModelSettings.normalize(ModelSettings.defaults(), requested, metadata);
        // A known model limit is distinct from this queue's conservative allocation guard.
        if (result.getInt("context") > 131072) result = ModelSettings.normalize(result, new JSONObject().put("context", 131072), metadata);
        if (result.getString("systemPrompt").indexOf('\0') >= 0) throw new IOException("系统提示词包含无效终止符");
        return result;
    }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        validate(bundle, request.getString("type")); TextSpec.prompt(request.getJSONObject("input"));
        try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) {
            JSONObject metadata = GgufMetadata.read(lease.file("text_gguf"));
            JSONObject before = request.getJSONObject("parameters"), effective = parameters(before, metadata), out = DataFiles.copy(request);
            JSONArray adjustments = out.getJSONArray("adjustments");
            for (String field : TextSpec.FIELDS) if (!DataFiles.canonical(before.opt(field)).equals(DataFiles.canonical(effective.opt(field)))) adjustments.put(new JSONObject().put("field", field).put("requested", before.opt(field)).put("effective", effective.get(field)).put("reason", "gguf_context_or_device_application_limit"));
            return out.put("parameters", effective).put("textMetadata", metadata);
        }
    }
    private static HttpURLConnection connection(int port, String key, String path) throws IOException {
        if (port < 1 || port > 65535 || key.isEmpty() || !Arrays.asList("/health", "/v1/models", "/v1/chat/completions").contains(path)) throw new IOException("无效本机引擎端点");
        HttpURLConnection result = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        result.setInstanceFollowRedirects(false); result.setConnectTimeout(1000); result.setReadTimeout(path.equals("/v1/chat/completions") ? 300000 : 1500);
        result.setRequestProperty("Authorization", "Bearer " + key); result.setRequestProperty("Accept", path.equals("/v1/chat/completions") ? "text/event-stream" : "application/json"); return result;
    }
    private static JSONObject json(HttpURLConnection connection) throws Exception {
        if (connection.getResponseCode() != 200) throw new IOException("本机文本引擎端点暂未就绪");
        try (InputStream in = connection.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096]; int n;
            while ((n = in.read(buffer)) != -1) { if (out.size() > 65536 - n) throw new IOException("本机文本引擎元数据过长"); out.write(buffer, 0, n); }
            return new JSONObject(new String(out.toByteArray(), StandardCharsets.UTF_8));
        }
    }
    private static void ready(Process child, int port, String key, String alias, Context context) throws Exception {
        long until = System.nanoTime() + TimeUnit.MINUTES.toNanos(5);
        while (System.nanoTime() < until) {
            context.check(); if (!child.isAlive()) throw new IOException("本机文本引擎在载入期间退出；请核对模型架构与资源");
            HttpURLConnection health = connection(port, key, "/health"); boolean healthy = false;
            try { healthy = json(health).optString("status").equals("ok"); } catch (IOException notReady) {} finally { health.disconnect(); }
            if (healthy) {
                HttpURLConnection models = connection(port, key, "/v1/models");
                try {
                    JSONArray data = json(models).getJSONArray("data");
                    if (data.length() != 1 || !data.getJSONObject(0).optString("id").equals(alias)) throw new IOException("本机文本端点不属于当前任务");
                    context.check(); return;
                } finally { models.disconnect(); }
            }
            Thread.sleep(100);
        }
        throw new IOException("文本模型载入超过五分钟保护时限");
    }
    private static void stop(Process process) throws IOException {
        if (process == null) return;
        process.destroy();
        try { if (!process.waitFor(3, TimeUnit.SECONDS)) { process.destroyForcibly(); if (!process.waitFor(3, TimeUnit.SECONDS)) throw new IOException("文本工作进程尚未退出"); } }
        catch (InterruptedException error) { process.destroyForcibly(); Thread.currentThread().interrupt(); throw new IOException("文本进程清理被中断", error); }
    }
    private static void add(List<String> command, String... values) { Collections.addAll(command, values); }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(); BundleStore.Lease model = context.model(); validate(model.bundle, request.getString("type")); context.check();
        String prompt = TextSpec.prompt(request.getJSONObject("input"));
        JSONObject metadata = GgufMetadata.read(model.file("text_gguf")), settings = parameters(request.getJSONObject("parameters"), metadata);
        if (!DataFiles.canonical(settings).equals(DataFiles.canonical(request.getJSONObject("parameters")))) throw new IOException("文本参数约束已变化，请重新提交任务");
        int port; try (ServerSocket reserve = new ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))) { port = reserve.getLocalPort(); }
        byte[] secret = new byte[24]; new java.security.SecureRandom().nextBytes(secret); String key = Protocol.hex(secret);
        List<String> command = new ArrayList<>(); command.add(binary.getAbsolutePath());
        add(command, "-m", model.file("text_gguf").getAbsolutePath(), "--alias", model.bundle.id, "--host", "127.0.0.1", "--port", String.valueOf(port));
        add(command, "-t", String.valueOf(settings.getInt("threads")), "-c", String.valueOf(settings.getInt("context")), "-b", "64", "-ub", "64", "-np", "1", "-ngl", "0", "--device", "none", "--jinja", "--no-webui", "--reasoning", settings.getString("reasoning"));
        ProcessBuilder builder = new ProcessBuilder(command).directory(app.getFilesDir()).redirectErrorStream(true);
        builder.environment().put("LD_LIBRARY_PATH", app.getApplicationInfo().nativeLibraryDir); builder.environment().put("LLAMA_API_KEY", key);
        Process child = null; Thread drain = null; HttpURLConnection inference = null;
        try {
            context.progress("loading", null);
            synchronized (app.nativeProcessLock) {
                context.check(); if (app.nativeProcess != null && app.nativeProcess.isAlive()) throw new IOException("另一个本机引擎仍在运行，请等待其退出");
                child = launcher.start(builder); app.nativeProcess = child;
            }
            context.process(child); final Process owned = child;
            // Native diagnostics are private and discarded: prompts and credentials never enter UI logs.
            drain = new Thread(() -> { try (InputStream in = owned.getInputStream()) { byte[] bytes = new byte[8192]; while (in.read(bytes) != -1) {} } catch (IOException ignored) {} }, "LMA-text-diagnostics"); drain.setDaemon(true); drain.start();
            ready(child, port, key, model.bundle.id, context);
            JSONArray messages = new JSONArray();
            if (!settings.getString("systemPrompt").isEmpty()) messages.put(new JSONObject().put("role", "system").put("content", settings.getString("systemPrompt")));
            messages.put(new JSONObject().put("role", "user").put("content", prompt));
            JSONObject payload = TextRequest.normalize("/v1/chat/completions", new JSONObject().put("messages", messages).put("stream", true).put("stream_options", new JSONObject().put("include_usage", true)), model.bundle.id, settings);
            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            inference = connection(port, key, "/v1/chat/completions"); inference.setRequestMethod("POST"); inference.setDoOutput(true); inference.setRequestProperty("Content-Type", "application/json; charset=utf-8"); inference.setFixedLengthStreamingMode(body.length);
            context.check(); try (OutputStream out = inference.getOutputStream()) { out.write(body); }
            if (inference.getResponseCode() != 200 || !String.valueOf(inference.getHeaderField("Content-Type")).toLowerCase(Locale.ROOT).startsWith("text/event-stream")) throw new IOException("本机文本引擎未返回有效生成流；请核对配方与聊天模板");
            context.progress("generating", null); final long[] update = {0}; JSONObject result;
            try (InputStream stream = inference.getInputStream()) { result = TextResult.consume(stream, context::check, characters -> { long now = System.nanoTime(); if (now - update[0] >= TimeUnit.MILLISECONDS.toNanos(100)) { context.progress("generating", null); update[0] = now; } }); }
            context.check(); context.execution(new JSONObject().put("effectiveParameters", settings).put("ggufMetadata", metadata).put("textUsage", result.getJSONObject("usage")).put("finishReason", result.getString("finishReason")));
            context.progress("saving", null); File output = context.output("json"); TextResult.write(output, result); context.check(); return output;
        } finally {
            if (inference != null) inference.disconnect();
            try { stop(child); }
            finally {
                if (child != null) { try { child.getInputStream().close(); } catch (IOException ignored) {} }
                if (drain != null) try { drain.join(1000); } catch (InterruptedException error) { Thread.currentThread().interrupt(); }
                synchronized (app.nativeProcessLock) { if (app.nativeProcess == child && (child == null || !child.isAlive())) app.nativeProcess = null; }
            }
        }
    }
}
