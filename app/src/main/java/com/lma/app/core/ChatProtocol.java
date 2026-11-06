package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** OpenAI function tools remain client-owned. This class never executes a tool. */
public final class ChatProtocol {
    public static final int MAX_MESSAGES = 1024, MAX_TEXT_BYTES = 1024 * 1024;
    private ChatProtocol() {}
    static void fields(JSONObject value, String path, String... names) {
        Set<String> allowed = new HashSet<>(Arrays.asList(names));
        for (Iterator<String> it = value.keys(); it.hasNext();) { String name = it.next(); if (!allowed.contains(name)) throw new RequestError(path.isEmpty() ? name : path + "." + name, "Unsupported request field"); }
    }
    static String text(Object value, String path) {
        if (!(value instanceof String)) throw new RequestError(path, "Expected a string");
        String result = (String)value;
        if (result.length() > MAX_TEXT_BYTES || result.getBytes(StandardCharsets.UTF_8).length > MAX_TEXT_BYTES) throw new RequestError(path, "Text exceeds the 1 MiB UTF-8 limit");
        return result;
    }
    static String name(Object value, String path) {
        String result = text(value, path);
        if (!result.matches("[A-Za-z0-9_-]{1,64}")) throw new RequestError(path, "Use a function name of 1–64 letters, digits, underscores or hyphens");
        return result;
    }
    private static void content(JSONObject message, String path, boolean nullable) throws Exception {
        Object value = message.opt("content");
        if (value == null || value == JSONObject.NULL) { if (!nullable) throw new RequestError(path + ".content", "Message content is required"); return; }
        if (value instanceof String) { text(value, path + ".content"); return; }
        if (!(value instanceof JSONArray)) throw new RequestError(path + ".content", "Use a string or text content parts");
        JSONArray parts = (JSONArray)value; int bytes = 0;
        if (parts.length() > 1024) throw new RequestError(path + ".content", "Too many content parts");
        for (int i = 0; i < parts.length(); i++) {
            JSONObject part = parts.getJSONObject(i); String at = path + ".content[" + i + "]";
            fields(part, at, "type", "text");
            if (!part.optString("type").equals("text")) throw new RequestError(at + ".type", "This endpoint accepts text parts; media URLs are not fetched");
            bytes += text(part.opt("text"), at + ".text").getBytes(StandardCharsets.UTF_8).length;
            if (bytes > MAX_TEXT_BYTES) throw new RequestError(path + ".content", "Message content exceeds 1 MiB UTF-8");
        }
    }
    public static void messages(JSONObject request) throws Exception {
        if (!(request.opt("messages") instanceof JSONArray)) throw new RequestError("messages", "Use a message array");
        JSONArray messages = request.getJSONArray("messages"); Set<String> pending = new HashSet<>();
        if (messages.length() < 1 || messages.length() > MAX_MESSAGES) throw new RequestError("messages", "Use 1–1024 messages within the model context");
        for (int i = 0; i < messages.length(); i++) {
            String at = "messages[" + i + "]";
            if (!(messages.opt(i) instanceof JSONObject)) throw new RequestError(at, "Expected a message object");
            JSONObject message = messages.getJSONObject(i); String role = message.optString("role");
            if (!Arrays.asList("system", "developer", "user", "assistant", "tool").contains(role)) throw new RequestError(at + ".role", "Unsupported message role");
            if (!role.equals("tool") && !pending.isEmpty()) throw new RequestError(at, "Return every pending tool result before the next message");
            if (role.equals("assistant")) {
                fields(message, at, "role", "content", "name", "tool_calls", "refusal", "reasoning_content", "reasoning");
                JSONArray calls = message.optJSONArray("tool_calls");
                if (message.has("tool_calls") && !message.isNull("tool_calls") && calls == null) throw new RequestError(at + ".tool_calls", "Expected a tool-call array");
                boolean hasCalls = calls != null && calls.length() > 0;
                content(message, at, hasCalls || message.has("refusal") && !message.isNull("refusal"));
                if (calls != null) {
                    if (calls.length() > 128) throw new RequestError(at + ".tool_calls", "At most 128 calls per turn");
                    for (int j = 0; j < calls.length(); j++) {
                        String callAt = at + ".tool_calls[" + j + "]"; JSONObject call = calls.getJSONObject(j);
                        fields(call, callAt, "id", "type", "function");
                        String id = text(call.opt("id"), callAt + ".id");
                        if (id.isEmpty() || id.length() > 256 || !pending.add(id)) throw new RequestError(callAt + ".id", "Tool-call IDs must be nonempty and unique in the turn");
                        if (!call.optString("type").equals("function")) throw new RequestError(callAt + ".type", "Use a function tool");
                        JSONObject function = call.getJSONObject("function"); fields(function, callAt + ".function", "name", "arguments");
                        name(function.opt("name"), callAt + ".function.name"); text(function.opt("arguments"), callAt + ".function.arguments");
                    }
                }
                for (String key : Arrays.asList("refusal", "reasoning_content", "reasoning")) if (message.has(key) && !message.isNull(key)) text(message.get(key), at + "." + key);
            } else if (role.equals("tool")) {
                fields(message, at, "role", "content", "tool_call_id"); content(message, at, false);
                String id = text(message.opt("tool_call_id"), at + ".tool_call_id");
                if (!pending.remove(id)) throw new RequestError(at + ".tool_call_id", "Tool result has no matching pending call, or is duplicated");
            } else { fields(message, at, "role", "content", "name"); content(message, at, false); }
            if (message.has("name")) text(message.opt("name"), at + ".name");
        }
        if (!pending.isEmpty()) throw new RequestError("messages", "Missing results for pending tool calls");
    }
    public static void tools(JSONObject request) throws Exception {
        JSONArray tools = request.optJSONArray("tools"); Map<String, JSONObject> definitions = new LinkedHashMap<>();
        if (request.has("tools") && tools == null) throw new RequestError("tools", "Use a function-tool array");
        if (tools != null) {
            if (tools.length() > 128) throw new RequestError("tools", "At most 128 function definitions");
            for (int i = 0; i < tools.length(); i++) {
                String at = "tools[" + i + "]"; JSONObject tool = tools.getJSONObject(i); fields(tool, at, "type", "function");
                if (!tool.optString("type").equals("function")) throw new RequestError(at + ".type", "Use client-executed function tools");
                JSONObject function = tool.getJSONObject("function"); fields(function, at + ".function", "name", "description", "parameters", "strict");
                String name = name(function.opt("name"), at + ".function.name");
                if (definitions.put(name, tool) != null) throw new RequestError(at + ".function.name", "Duplicate function name");
                if (function.has("description")) text(function.opt("description"), at + ".function.description");
                if (function.has("strict") && !(function.opt("strict") instanceof Boolean) && !function.isNull("strict")) throw new RequestError(at + ".function.strict", "Use a boolean");
                if (!function.has("parameters")) function.put("parameters", new JSONObject().put("type", "object").put("properties", new JSONObject()));
                if (!(function.opt("parameters") instanceof JSONObject)) throw new RequestError(at + ".function.parameters", "Use a JSON Schema object");
                JsonSchema.check(function.getJSONObject("parameters"), at + ".function.parameters");
            }
        }
        if (request.has("parallel_tool_calls") && !(request.opt("parallel_tool_calls") instanceof Boolean)) throw new RequestError("parallel_tool_calls", "Use a boolean");
        Object choice = request.opt("tool_choice");
        if (choice == null || choice == JSONObject.NULL) choice = definitions.isEmpty() ? "none" : "auto";
        if (choice instanceof String) {
            if (!Arrays.asList("none", "auto", "required").contains(choice)) throw new RequestError("tool_choice", "Use none, auto, required or a named function");
            if (choice.equals("required") && definitions.isEmpty()) throw new RequestError("tool_choice", "Required tool choice needs at least one tool");
        } else if (choice instanceof JSONObject) {
            JSONObject selected = (JSONObject)choice; fields(selected, "tool_choice", "type", "function");
            if (!selected.optString("type").equals("function")) throw new RequestError("tool_choice.type", "Use a function selection");
            JSONObject function = selected.getJSONObject("function"); fields(function, "tool_choice.function", "name");
            String name = name(function.opt("name"), "tool_choice.function.name");
            if (!definitions.containsKey(name)) throw new RequestError("tool_choice.function.name", "Selected function is not declared");
            // Preserve every declaration and the public named-choice contract.
            // NativeToolRequest adapts grammar selection separately from rendering.
        } else throw new RequestError("tool_choice", "Invalid tool choice");
        if (tools != null || request.has("tool_choice")) request.put("tool_choice", choice);
        if (!definitions.isEmpty() && !request.has("parallel_tool_calls")) request.put("parallel_tool_calls", true);
    }
}
