package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.*;
import java.util.*;

/** Native OpenAI replies, including strict arguments, are checked before tool execution by a client. */
public final class ToolReply {
    public static final int MAX_RESPONSE_BYTES = 16 * 1024 * 1024;
    private final JSONObject request;
    private final Map<String, JSONObject> functions = new LinkedHashMap<>();
    private final JSONObject responseSchema;
    private final boolean hold;
    private static final class CallParts {
        String id = ""; final StringBuilder name = new StringBuilder(), arguments = new StringBuilder();
        JSONObject json() throws Exception { return new JSONObject().put("id", id).put("type", "function").put("function", new JSONObject().put("name", name.toString()).put("arguments", arguments.toString())); }
    }
    public ToolReply(JSONObject request) throws Exception {
        this.request = request; boolean strict = false; JSONArray tools = request.optJSONArray("tools");
        if (tools != null) for (int i = 0; i < tools.length(); i++) { JSONObject function = tools.getJSONObject(i).getJSONObject("function"); functions.put(function.getString("name"), function); strict |= function.optBoolean("strict"); }
        JSONObject format = request.optJSONObject("response_format"), wrapper = format == null ? null : format.optJSONObject("json_schema");
        responseSchema = wrapper != null && wrapper.optBoolean("strict") ? wrapper.getJSONObject("schema") : null;
        hold = strict || responseSchema != null;
    }
    public boolean enabled() { return !functions.isEmpty() || request.has("tool_choice") || responseSchema != null; }
    private void validate(JSONObject message, String finish) throws Exception {
        JSONArray calls = message.optJSONArray("tool_calls"); int count = calls == null ? 0 : calls.length();
        if (count > 128 || count > 1 && !request.optBoolean("parallel_tool_calls", true)) throw new IOException("The local engine violated parallel_tool_calls");
        String choice = request.optString("tool_choice", "auto");
        if (count > 0 && choice.equals("none")) throw new IOException("The local engine called a tool while tool_choice was none");
        if (count == 0 && (finish.equals("tool_calls") || choice.equals("required") && !finish.equals("length"))) throw new IOException("The local engine did not produce the required tool call");
        Set<String> ids = new HashSet<>();
        for (int i = 0; i < count; i++) {
            JSONObject call = calls.getJSONObject(i); String id = call.optString("id");
            if (id.isEmpty() || id.length() > 256 || !ids.add(id) || !call.optString("type").equals("function")) throw new IOException("The local engine returned invalid tool-call identifiers");
            JSONObject function = call.getJSONObject("function"), definition = functions.get(function.optString("name"));
            if (definition == null || !(function.opt("arguments") instanceof String)) throw new IOException("The local engine returned an undeclared function or invalid arguments");
            String arguments = function.getString("arguments"); if (arguments.getBytes(StandardCharsets.UTF_8).length > ChatProtocol.MAX_TEXT_BYTES) throw new IOException("Tool arguments exceed 1 MiB");
            if (definition.optBoolean("strict")) {
                if (!finish.equals("tool_calls")) throw new IOException("Strict tool arguments were interrupted before completion; increase the model output limit");
                try { JsonSchema.validate(definition.getJSONObject("parameters"), parse(arguments)); }
                catch (Exception error) { throw new IOException("The local engine returned arguments outside the strict function schema", error); }
            }
        }
        if (count > 0 && !Arrays.asList("tool_calls", "length").contains(finish)) throw new IOException("The local engine returned an invalid tool finish reason");
        if (responseSchema != null && finish.equals("stop") && count == 0 && message.isNull("refusal")) {
            try { JsonSchema.validate(responseSchema, parse(message.optString("content"))); }
            catch (Exception error) { throw new IOException("The local engine returned content outside the strict response schema", error); }
        }
    }
    private static Object parse(String text) throws Exception {
        // Android JSONTokener accepts non-JSON extensions (single quotes,
        // unquoted keys and trailing commas). Never deliver those as strict JSON.
        Syntax syntax = new Syntax(text); syntax.value(0); syntax.space();
        if (syntax.at != text.length()) throw new IOException("Trailing JSON content");
        org.json.JSONTokener tokener = new org.json.JSONTokener(text); Object value = tokener.nextValue(); if (tokener.nextClean() != 0) throw new IOException("Trailing JSON content"); return value;
    }
    private static final class Syntax {
        final String text; int at;
        Syntax(String text) { this.text = text; }
        void space() { while (at < text.length() && " \t\r\n".indexOf(text.charAt(at)) >= 0) at++; }
        boolean take(char ch) { space(); if (at < text.length() && text.charAt(at) == ch) { at++; return true; } return false; }
        void need(char ch) throws IOException { if (!take(ch)) throw new IOException("Invalid generated JSON syntax"); }
        void string() throws IOException {
            need('"'); boolean closed = false;
            while (at < text.length()) {
                char ch = text.charAt(at++); if (ch == '"') { closed = true; break; }
                if (ch < 32) throw new IOException("Unescaped JSON control character");
                if (ch == '\\') {
                    if (at == text.length()) throw new IOException("Incomplete JSON escape"); char escaped = text.charAt(at++);
                    if (escaped == 'u') { for (int i = 0; i < 4; i++) if (at == text.length() || Character.digit(text.charAt(at++), 16) < 0) throw new IOException("Invalid JSON Unicode escape"); }
                    else if ("\"\\/bfnrt".indexOf(escaped) < 0) throw new IOException("Invalid JSON escape");
                }
            }
            if (!closed) throw new IOException("Incomplete JSON string");
        }
        void digits() throws IOException { int start = at; while (at < text.length() && text.charAt(at) >= '0' && text.charAt(at) <= '9') at++; if (at == start) throw new IOException("Invalid JSON number"); }
        void value(int depth) throws IOException {
            if (depth > 64) throw new IOException("Generated JSON nesting exceeds 64 levels");
            space(); if (at == text.length()) throw new IOException("Missing JSON value"); char ch = text.charAt(at);
            if (ch == '"') { string(); return; }
            if (take('{')) { if (take('}')) return; do { string(); need(':'); value(depth + 1); } while (take(',')); need('}'); return; }
            if (take('[')) { if (take(']')) return; do { value(depth + 1); } while (take(',')); need(']'); return; }
            for (String literal : Arrays.asList("true", "false", "null")) if (text.startsWith(literal, at)) { at += literal.length(); return; }
            if (at < text.length() && text.charAt(at) == '-') at++;
            if (at < text.length() && text.charAt(at) == '0') at++; else digits();
            if (at < text.length() && text.charAt(at) == '.') { at++; digits(); }
            if (at < text.length() && (text.charAt(at) == 'e' || text.charAt(at) == 'E')) { at++; if (at < text.length() && (text.charAt(at) == '+' || text.charAt(at) == '-')) at++; digits(); }
        }
    }
    public byte[] complete(InputStream in) throws Exception {
        byte[] bytes = read(in, MAX_RESPONSE_BYTES); JSONObject result = new JSONObject(StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(bytes)).toString());
        JSONArray choices = result.getJSONArray("choices");
        if (choices.length() != 1) throw new IOException("The local engine returned an unexpected choice count");
        JSONObject choice = choices.getJSONObject(0); validate(choice.getJSONObject("message"), choice.getString("finish_reason")); return bytes;
    }
    public void stream(InputStream in, OutputStream out) throws Exception {
        if (!enabled()) { copy(in, out); return; }
        Reader reader = new InputStreamReader(in, StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT));
        StringBuilder eventData = new StringBuilder(), content = new StringBuilder(), refusal = new StringBuilder(); Map<Integer, CallParts> calls = new TreeMap<>();
        ByteArrayOutputStream pending = responseSchema != null ? new ByteArrayOutputStream() : null;
        int total = 0; boolean finished = false, done = false;
        while (true) {
            String line = line(reader); if (line == null) break; total += line.getBytes(StandardCharsets.UTF_8).length + 1;
            if (total > MAX_RESPONSE_BYTES) throw new IOException("Text response exceeds 16 MiB");
            if (!line.isEmpty()) { if (line.startsWith("data:")) { if (eventData.length() > 0) eventData.append('\n'); eventData.append(line.substring(5).replaceFirst("^ ", "")); } else if (!line.startsWith(":") && !line.startsWith("event:") && !line.startsWith("id:") && !line.startsWith("retry:")) throw new IOException("Invalid local text event"); continue; }
            if (eventData.length() == 0) continue;
            String payload = eventData.toString(); eventData.setLength(0);
            if (payload.equals("[DONE]")) { if (!finished) throw new IOException("The local engine ended without a finish reason"); write(out, "data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8)); done = true; break; }
            JSONObject event = new JSONObject(payload); if (event.has("error")) throw new IOException("The local text engine reported a streaming error");
            JSONArray choices = event.getJSONArray("choices");
            if (choices.length() > 1) throw new IOException("Unexpected streamed choice count");
            if (choices.length() == 1) {
                JSONObject choice = choices.getJSONObject(0); if (choice.optInt("index", 0) != 0) throw new IOException("Unexpected streamed choice index");
                JSONObject delta = choice.getJSONObject("delta");
                if (delta.opt("refusal") instanceof String) refusal.append(delta.getString("refusal"));
                if (finished && (delta.has("tool_calls") || delta.has("content") && !delta.isNull("content") && !delta.optString("content").isEmpty())) throw new IOException("The local engine continued after finishing");
                if (delta.opt("content") instanceof String && responseSchema != null) { content.append(delta.getString("content")); if (content.length() > ChatProtocol.MAX_TEXT_BYTES) throw new IOException("Structured response exceeds its size limit"); }
                JSONArray fragments = delta.optJSONArray("tool_calls");
                // Stream real text/reasoning immediately. Only executable strict
                // tool deltas wait until their complete arguments pass validation.
                if (hold && fragments != null && fragments.length() > 0 && pending == null) pending = new ByteArrayOutputStream();
                if (fragments != null) for (int i = 0; i < fragments.length(); i++) {
                    JSONObject fragment = fragments.getJSONObject(i); Object rawIndex = fragment.opt("index");
                    if (!(rawIndex instanceof Number) || ((Number)rawIndex).doubleValue() != ((Number)rawIndex).intValue()) throw new IOException("Invalid tool-call index");
                    int index = ((Number)rawIndex).intValue(); if (index < 0 || index >= 128) throw new IOException("Invalid tool-call index");
                    CallParts call = calls.get(index); if (call == null) { call = new CallParts(); calls.put(index, call); }
                    if (fragment.has("id") && !fragment.isNull("id")) { String id = fragment.getString("id"); if (!call.id.isEmpty() && !call.id.equals(id)) throw new IOException("Tool-call ID changed while streaming"); call.id = id; }
                    if (fragment.has("type") && !fragment.isNull("type") && !fragment.getString("type").equals("function")) throw new IOException("Unexpected streamed tool type");
                    JSONObject function = fragment.optJSONObject("function");
                    if (function != null) for (String key : Arrays.asList("name", "arguments")) if (function.has(key) && !function.isNull(key)) { String part = function.getString(key); StringBuilder accumulated = key.equals("name") ? call.name : call.arguments; accumulated.append(part); if (accumulated.length() > (key.equals("name") ? 64 : ChatProtocol.MAX_TEXT_BYTES)) throw new IOException("Tool name or arguments exceed their size limit"); }
                }
                if (choice.has("finish_reason") && !choice.isNull("finish_reason")) {
                    if (finished) throw new IOException("Duplicate text finish event");
                    JSONArray complete = new JSONArray(); for (CallParts call : calls.values()) complete.put(call.json());
                    JSONObject message = new JSONObject().put("content", content.toString()); if (complete.length() > 0) message.put("tool_calls", complete); if (refusal.length() > 0) message.put("refusal", refusal.toString());
                    validate(message, choice.getString("finish_reason")); finished = true;
                }
            }
            byte[] bytes = ("data: " + payload + "\n\n").getBytes(StandardCharsets.UTF_8);
            if (pending != null) { pending.write(bytes); if (pending.size() > MAX_RESPONSE_BYTES) throw new IOException("Strict response exceeds its size limit"); if (finished) { write(out, pending.toByteArray()); pending = null; } }
            else write(out, bytes);
        }
        if (!done) throw new IOException("The local text stream disconnected before [DONE]");
    }
    private static String line(Reader reader) throws IOException { StringBuilder out = new StringBuilder(); int ch; while ((ch = reader.read()) != -1) { if (ch == '\n') return out.toString(); if (ch != '\r') out.append((char)ch); if (out.length() > 2 * 1024 * 1024) throw new IOException("Text event line exceeds 2 MiB"); } return out.length() == 0 ? null : out.toString(); }
    public static byte[] read(InputStream in, int maximum) throws IOException { ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buffer = new byte[16384]; int count; while ((count = in.read(buffer)) != -1) { if (out.size() + count > maximum) throw new IOException("Text response exceeds its size limit"); out.write(buffer, 0, count); } return out.toByteArray(); }
    public static void copy(InputStream in, OutputStream out) throws IOException { byte[] buffer = new byte[16384]; int total = 0, count; while ((count = in.read(buffer)) != -1) { if ((total += count) > MAX_RESPONSE_BYTES) throw new IOException("Text response exceeds 16 MiB"); synchronized (out) { out.write(buffer, 0, count); out.flush(); } } }
    public static void write(OutputStream out, byte[] bytes) throws IOException { synchronized (out) { out.write(bytes); out.flush(); } }
}
