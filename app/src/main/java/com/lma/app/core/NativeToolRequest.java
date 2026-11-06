package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Private pinned-llama bridge: rendering sees all tools; named grammar sees one. */
public final class NativeToolRequest {
    private NativeToolRequest() {}
    public static String selected(JSONObject request) {
        JSONObject choice = request.optJSONObject("tool_choice");
        JSONObject function = choice == null ? null : choice.optJSONObject("function");
        return function == null ? "" : function.optString("name");
    }
    public static JSONObject adapt(JSONObject request) throws Exception {
        JSONObject wire = new JSONObject(request.toString());
        // Templates without explicit call IDs associate parallel results by order.
        // Public IDs/content stay intact; only the private rendering copy is ordered.
        JSONArray messages = wire.optJSONArray("messages");
        if (messages != null) for (int i = 0; i < messages.length(); i++) {
            JSONArray calls = messages.getJSONObject(i).optJSONArray("tool_calls");
            if (calls == null || calls.length() < 2) continue;
            Map<String, JSONObject> results = new HashMap<>(); int end = i + 1;
            while (end < messages.length() && messages.getJSONObject(end).optString("role").equals("tool")) {
                JSONObject result = messages.getJSONObject(end++); results.put(result.getString("tool_call_id"), result);
            }
            if (results.size() != calls.length()) throw new RequestError("messages", "Parallel tool results must match their call IDs");
            for (int n = 0; n < calls.length(); n++) {
                JSONObject result = results.get(calls.getJSONObject(n).getString("id"));
                if (result == null) throw new RequestError("messages", "Parallel tool result ID does not match its call");
                messages.put(i + 1 + n, result);
            }
            i = end - 1;
        }
        String selected = selected(request);
        if (selected.isEmpty()) return wire;
        JSONArray all = wire.getJSONArray("tools"), allowed = new JSONArray();
        for (int i = 0; i < all.length(); i++) {
            JSONObject tool = all.getJSONObject(i);
            if (selected.equals(tool.getJSONObject("function").getString("name"))) allowed.put(tool);
        }
        if (allowed.length() != 1) throw new RequestError("tool_choice", "Selected function is not declared exactly once");
        // b29c606 common_chat_template_direct_apply_impl overlays extra_context
        // AFTER input.tools. Autoparser grammar retains the selected input.tools.
        wire.put("chat_template_kwargs", new JSONObject().put("tools", all));
        wire.put("tools", allowed).put("tool_choice", "required");
        return wire;
    }
}
