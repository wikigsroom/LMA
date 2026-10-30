package com.lma.app;

import com.lma.app.core.Protocol;
import com.lma.app.core.ExecutionGate;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class ChatRunner {
    private final LmaService owner;
    private final LmaApp app;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private volatile boolean cancelled;
    private volatile HttpURLConnection connection;
    public ChatRunner(LmaService owner, LmaApp app) { this.owner = owner; this.app = app; }
    public synchronized void send(String text) throws Exception {
        synchronized (app.requestGate) {
        text = text.trim();
        if (text.isEmpty() || text.length() > 12000) throw new IllegalArgumentException("请输入 1–12000 个字符");
        if (app.generating || app.textRequestBusy) throw new IllegalStateException("上一条回复仍在生成");
        if (!owner.engine.wanted()) throw new IllegalStateException("请先选择并加载一个本地模型");
        JSONObject settings = app.settings(app.engineModel); String session = app.chats.session();
        if (session.isEmpty()) session = app.chats.create(app.engineModel);
        JSONArray history = app.chats.history(session, settings.getInt("context"));
        app.chats.append(session, "user", text, "done");
        String responseId = app.chats.append(session, "assistant", "", "generating");
        JSONArray messages = new JSONArray();
        String system = settings.getString("systemPrompt");
        if (!system.trim().isEmpty()) messages.put(new JSONObject().put("role", "system").put("content", system));
        for (int i = 0; i < history.length(); i++) messages.put(history.get(i));
        messages.put(new JSONObject().put("role", "user").put("content", text));
        JSONObject request = new JSONObject(); request.put("model", app.engineModel).put("messages", messages).put("stream", true)
                .put("max_tokens", settings.getInt("maxTokens")).put("temperature", settings.getDouble("temperature"))
                .put("stream_options", new JSONObject().put("include_usage", true));
        final ExecutionGate.Ticket slot = app.execution.enqueue("chat", app.engineModel);
        cancelled = false; app.generating = true; app.emit(); owner.activityChanged();
        worker.execute(() -> generate(request, responseId, slot));
        }
    }
    public void cancel() { cancelled = true; HttpURLConnection active = connection; if (active != null) active.disconnect(); }
    public void close() { cancel(); worker.shutdown(); }
    private void generate(JSONObject request, String responseId, ExecutionGate.Ticket slot) {
        long started = System.currentTimeMillis(); StringBuilder text = new StringBuilder(), reasoning = new StringBuilder();
        final int[] tokens = {0}; final boolean[] done = {false}; final long[] lastFlush = {0};
        String status = "done", errorMessage = "";
        HttpURLConnection active = null;
        try {
            ExecutionGate.Check check = () -> { if (cancelled || Thread.currentThread().isInterrupted()) throw new java.io.InterruptedIOException("生成已取消"); };
            slot.await(check); owner.engine.ensureReady(slot, request.getString("model"), check); check.run();
            active = Net.engine(app, "/v1/chat/completions"); connection = active;
            if (cancelled) throw new java.io.InterruptedIOException("生成已取消");
            active.setRequestMethod("POST"); active.setDoOutput(true); active.setRequestProperty("Content-Type", "application/json; charset=utf-8"); active.setRequestProperty("Accept", "text/event-stream");
            byte[] body = request.toString().getBytes(StandardCharsets.UTF_8); active.setFixedLengthStreamingMode(body.length);
            try (java.io.OutputStream out = active.getOutputStream()) { out.write(body); }
            if (active.getResponseCode() != 200) throw new java.io.IOException(Net.errorBody(active));
            try (InputStreamReader in = new InputStreamReader(active.getInputStream(), StandardCharsets.UTF_8)) {
                Protocol.readSse(in, data -> {
                    slot.checkOwner();
                    if (cancelled) return false;
                    if (data.trim().equals("[DONE]")) { done[0] = true; return false; }
                    try {
                        JSONObject chunk = new JSONObject(data);
                        if (chunk.has("error")) throw new java.io.IOException(chunk.get("error").toString());
                        JSONObject usage = chunk.optJSONObject("usage"); if (usage != null) tokens[0] = usage.optInt("completion_tokens", tokens[0]);
                        JSONArray choices = chunk.optJSONArray("choices");
                        if (choices != null && choices.length() > 0) {
                            JSONObject choice = choices.getJSONObject(0), delta = choice.optJSONObject("delta");
                            if (delta != null) {
                                Object content = delta.opt("content"); if (content instanceof String) text.append((String) content);
                                Object thought = delta.opt("reasoning_content"); if (!(thought instanceof String)) thought = delta.opt("reasoning");
                                if (thought instanceof String) reasoning.append((String) thought);
                            }
                            if (!choice.isNull("finish_reason") && !choice.optString("finish_reason").isEmpty()) done[0] = true;
                        }
                        if (text.length() + reasoning.length() > 1024 * 1024) throw new java.io.IOException("回复过长，已停止并保存内容");
                        long now = System.currentTimeMillis();
                        if (now - lastFlush[0] > 160) {
                            app.chats.update(responseId, text.toString(), reasoning.toString(), "generating", "", tokens[0], now - started); app.emit(); lastFlush[0] = now;
                        }
                    } catch (org.json.JSONException error) { throw new java.io.IOException("接口返回了无法解析的流数据", error); }
                    return true;
                });
            }
            slot.checkOwner(); slot.finishResourceMonitoring();
            if (!done[0] && !cancelled) throw new java.io.IOException("连接中断，已保留收到的回复");
        } catch (Exception error) {
            if (!cancelled) { status = "error"; errorMessage = !slot.resourceFailure().isEmpty() ? slot.resourceFailure() : error.getMessage() == null ? "请求失败" : error.getMessage(); app.log("对话中断：" + errorMessage); }
        } finally {
            if (cancelled) status = "stopped";
            if (active != null) active.disconnect(); connection = null;
            app.chats.update(responseId, text.toString(), reasoning.toString(), status, errorMessage, tokens[0], System.currentTimeMillis() - started);
            synchronized (app.requestGate) { app.generating = false; }
            slot.close(); owner.engine.resumeIfIdle(); app.emit(); owner.activityChanged();
        }
    }
}
