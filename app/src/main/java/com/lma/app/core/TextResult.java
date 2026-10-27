package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.*;
import java.util.*;

/** Bounded, lossless text/reasoning results from the phone's private llama SSE endpoint. */
public final class TextResult {
    public static final String MIME = "application/vnd.lma.text+json";
    public static final int MAX_BYTES = 8 * 1024 * 1024;
    private static final int MAX_CHARACTERS = 1000000;
    private TextResult() {}
    public interface Check { void run() throws Exception; }
    public interface Progress { void received(int characters) throws Exception; }
    private static Reader reader(InputStream in, int limit) {
        InputStream bounded = new FilterInputStream(in) {
            private int count;
            private void add(int n) throws IOException { if (n > 0 && (count += n) > limit) throw new IOException("文本响应超过应用大小限制"); }
            @Override public int read() throws IOException { int n = super.read(); if (n >= 0) add(1); return n; }
            @Override public int read(byte[] b, int off, int len) throws IOException { int n = in.read(b, off, len); add(n); return n; }
        };
        return new BufferedReader(new InputStreamReader(bounded, StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)), 8192);
    }
    private static String line(Reader reader) throws IOException {
        StringBuilder out = new StringBuilder(); int ch;
        while ((ch = reader.read()) != -1) {
            if (ch == '\n') return out.toString();
            if (ch != '\r') out.append((char) ch);
            if (out.length() > 128 * 1024) throw new IOException("文本事件行超过应用限制");
        }
        return out.length() == 0 ? null : out.toString();
    }
    private static void append(StringBuilder out, Object value) throws IOException {
        if (value == null || value == JSONObject.NULL) return;
        if (!(value instanceof String)) throw new IOException("文本引擎返回了非文本内容");
        out.append((String) value);
    }
    private static JSONObject usage(JSONObject value) throws Exception {
        JSONObject out = new JSONObject();
        if (value == null) return out;
        for (String key : Arrays.asList("prompt_tokens", "completion_tokens", "total_tokens")) if (value.has(key)) {
            Object raw = value.get(key);
            if (!(raw instanceof Number) || !Double.isFinite(((Number) raw).doubleValue()) || ((Number) raw).doubleValue() < 0 || ((Number) raw).doubleValue() > Integer.MAX_VALUE || ((Number) raw).doubleValue() != Math.floor(((Number) raw).doubleValue())) throw new IOException("文本 token 计数无效");
            out.put(key, ((Number) raw).longValue());
        }
        return out;
    }
    public static JSONObject consume(InputStream input, Check check, Progress progress) throws Exception {
        Reader stream = reader(input, 16 * 1024 * 1024); StringBuilder data = new StringBuilder(), content = new StringBuilder(), reasoning = new StringBuilder();
        String finish = ""; JSONObject tokens = new JSONObject(); boolean done = false;
        while (true) {
            check.run(); String line = line(stream);
            if (line == null) throw new IOException("文本生成连接在完成事件前中断");
            if (line.startsWith(":")) continue;
            if (!line.isEmpty()) {
                if (line.startsWith("data:")) { if (data.length() > 0) data.append('\n'); data.append(line.substring(5).replaceFirst("^ ", "")); }
                else if (!line.startsWith("event:") && !line.startsWith("id:") && !line.startsWith("retry:")) throw new IOException("文本生成事件格式无效");
                if (data.length() > 256 * 1024) throw new IOException("文本事件超过应用限制");
                continue;
            }
            if (data.length() == 0) continue;
            String payload = data.toString(); data.setLength(0);
            if (payload.equals("[DONE]")) { done = true; break; }
            JSONObject event = new JSONObject(payload);
            if (event.has("error")) throw new IOException("本机文本引擎报告生成错误");
            if (event.has("usage") && !event.isNull("usage")) tokens = usage(event.getJSONObject("usage"));
            JSONArray choices = event.getJSONArray("choices");
            if (choices.length() == 0) continue;
            if (choices.length() != 1 || choices.getJSONObject(0).optInt("index", 0) != 0) throw new IOException("本机文本任务只接受一个输出序列");
            JSONObject choice = choices.getJSONObject(0), delta = choice.getJSONObject("delta");
            if (delta.has("tool_calls") || delta.has("function_call")) throw new IOException("此任务仅支持文本输出");
            if (!finish.isEmpty()) throw new IOException("文本引擎在结束后继续返回内容");
            append(content, delta.opt("content"));
            if (delta.has("reasoning_content") && delta.has("reasoning")) throw new IOException("文本引擎返回了重复的思考通道");
            append(reasoning, delta.has("reasoning_content") ? delta.opt("reasoning_content") : delta.opt("reasoning"));
            if (content.length() + reasoning.length() > MAX_CHARACTERS) throw new IOException("文本结果超过应用字符限制");
            if (choice.has("finish_reason") && !choice.isNull("finish_reason")) {
                finish = choice.getString("finish_reason");
                if (!Arrays.asList("stop", "length").contains(finish)) throw new IOException("文本引擎未正常完成生成");
            }
            progress.received(content.length() + reasoning.length());
        }
        if (!done || finish.isEmpty() || content.length() + reasoning.length() == 0) throw new IOException("文本引擎未返回完整的文本结果");
        check.run();
        return validate(new JSONObject().put("schema", "lma.text-result/1").put("content", content.toString()).put("reasoning", reasoning.toString()).put("finishReason", finish).put("usage", tokens));
    }
    public static JSONObject validate(JSONObject value) throws Exception {
        if (!value.getString("schema").equals("lma.text-result/1")) throw new IOException("未知文本结果格式");
        for (Iterator<String> it = value.keys(); it.hasNext();) if (!Arrays.asList("schema", "content", "reasoning", "finishReason", "usage").contains(it.next())) throw new IOException("未知文本结果字段");
        Object content = value.get("content"), reasoning = value.get("reasoning");
        if (!(content instanceof String) || !(reasoning instanceof String) || ((String) content).length() + ((String) reasoning).length() < 1 || ((String) content).length() + ((String) reasoning).length() > MAX_CHARACTERS) throw new IOException("文本结果为空或超限");
        if (!Arrays.asList("stop", "length").contains(value.getString("finishReason"))) throw new IOException("文本结果缺少有效结束原因");
        return DataFiles.copy(value).put("usage", usage(value.getJSONObject("usage")));
    }
    public static JSONObject read(File file) throws Exception {
        if (!file.isFile() || file.length() > MAX_BYTES) throw new IOException("文本结果不存在或超限");
        StringBuilder out = new StringBuilder();
        try (Reader in = reader(new FileInputStream(file), MAX_BYTES)) { char[] buffer = new char[8192]; int n; while ((n = in.read(buffer)) != -1) out.append(buffer, 0, n); }
        return validate(new JSONObject(out.toString()));
    }
    public static void write(File file, JSONObject value) throws Exception {
        byte[] bytes = validate(value).toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_BYTES) throw new IOException("文本结果超过应用大小限制");
        try (FileOutputStream out = new FileOutputStream(file)) { out.write(bytes); out.getFD().sync(); }
    }
    public static JSONObject inspect(File file) throws Exception {
        JSONObject result = read(file);
        return new JSONObject().put("mime", MIME).put("characters", result.getString("content").length()).put("reasoningCharacters", result.getString("reasoning").length()).put("finishReason", result.getString("finishReason")).put("usage", result.getJSONObject("usage"));
    }
}
