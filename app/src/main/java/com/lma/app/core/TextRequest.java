package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Public text/function requests with the selected model's saved sampling and output limits. */
public final class TextRequest {
    private TextRequest() {}
    public static JSONObject normalize(String path, JSONObject input, String model, JSONObject settings) throws Exception {
        JSONObject request = DataFiles.copy(input); input = request;
        List<String> optional = new ArrayList<>(); for (Iterator<String> it = request.keys(); it.hasNext();) optional.add(it.next());
        for (String key : optional) if (request.isNull(key)) request.remove(key);
        Set<String> allowed = new HashSet<>(Arrays.asList("model", "messages", "prompt", "stream", "max_tokens", "max_completion_tokens", "temperature", "top_p", "top_k", "min_p", "seed", "stop", "presence_penalty", "frequency_penalty", "repeat_penalty", "stream_options", "response_format", "logit_bias", "logprobs", "top_logprobs", "n", "cache_prompt", "store", "tools", "tool_choice", "parallel_tool_calls", "metadata", "user", "safety_identifier", "prompt_cache_key", "service_tier", "reasoning_effort"));
        for (Iterator<String> it = input.keys(); it.hasNext();) { String key = it.next(); if (!allowed.contains(key)) throw new RequestError(key, "Unsupported text request field"); }
        if (!input.optString("model", model).equals(model)) throw new IllegalStateException("The requested text model is not loaded; select/load it in the App first");
        request.put("model", model);
        if (path.equals("/v1/chat/completions")) {
            if (input.has("prompt")) throw new IllegalArgumentException("Use messages for chat completions");
            ChatProtocol.messages(request); ChatProtocol.tools(request);
        } else {
            if (input.has("messages") || !(input.get("prompt") instanceof String) || input.getString("prompt").isEmpty()) throw new RequestError("prompt", "Use a nonempty plain text prompt");
            ChatProtocol.text(input.get("prompt"), "prompt");
            for (String key : Arrays.asList("tools", "tool_choice", "parallel_tool_calls")) if (input.has(key)) throw new RequestError(key, "Function tools require /v1/chat/completions");
        }
        if (input.has("store") && !input.isNull("store") && !(input.get("store") instanceof Boolean)) throw new RequestError("store", "Use a boolean");
        if (input.optBoolean("store")) throw new RequestError("store", "Stored completion retrieval is unavailable; use store:false");
        request.remove("store"); // No completion record is persisted by this proxy.
        if (input.has("reasoning_effort") && !Arrays.asList("none", "minimal", "low", "medium", "high", "xhigh").contains(input.opt("reasoning_effort"))) throw new RequestError("reasoning_effort", "Use none, minimal, low, medium, high or xhigh; behavior follows the model template");
        for (String key : Arrays.asList("user", "safety_identifier", "prompt_cache_key")) if (input.has(key) && !input.isNull(key)) { String value = ChatProtocol.text(input.get(key), key); if (value.length() > 256) throw new RequestError(key, "Identifier exceeds 256 characters"); request.remove(key); }
        if (input.has("metadata") && !input.isNull("metadata")) {
            JSONObject metadata = input.getJSONObject("metadata"); if (metadata.length() > 16) throw new RequestError("metadata", "At most sixteen metadata fields");
            for (Iterator<String> it = metadata.keys(); it.hasNext();) { String key = it.next(); if (key.length() > 64 || !(metadata.get(key) instanceof String) || metadata.getString(key).length() > 512) throw new RequestError("metadata", "Metadata keys/values exceed their string limits"); }
            request.remove("metadata");
        }
        if (input.has("service_tier") && !input.isNull("service_tier")) { if (!Arrays.asList("auto", "default").contains(input.getString("service_tier"))) throw new RequestError("service_tier", "This local server offers auto/default service tier"); request.remove("service_tier"); }
        for (Iterator<String> it = new ArrayList<>(allowed).iterator(); it.hasNext();) { String key = it.next(); if (request.isNull(key)) request.remove(key); }
        if (input.has("max_tokens") && input.has("max_completion_tokens")) throw new IllegalArgumentException("Use one output-token field");
        String tokenField = input.has("max_completion_tokens") ? "max_completion_tokens" : "max_tokens";
        double requested = number(input, tokenField, settings.getInt("maxTokens"));
        if (requested < 1) throw new IllegalArgumentException("Output token count must be positive");
        int maximum = Math.min(settings.getInt("maxTokens"), settings.getInt("context") - 1);
        request.remove("max_completion_tokens"); request.put("max_tokens", (int) Math.max(1, Math.min(maximum, Math.floor(requested))));
        request.put("temperature", bounded(input, "temperature", settings.getDouble("temperature"), 0, 2));
        for (String key : Arrays.asList("stream", "cache_prompt", "logprobs")) if (input.has(key) && !(input.get(key) instanceof Boolean)) throw new IllegalArgumentException("Use a boolean for " + key);
        for (String key : Arrays.asList("top_p", "min_p")) if (input.has(key)) request.put(key, bounded(input, key, 1, 0, 1));
        for (String key : Arrays.asList("presence_penalty", "frequency_penalty")) if (input.has(key)) request.put(key, bounded(input, key, 0, -2, 2));
        if (input.has("repeat_penalty")) request.put("repeat_penalty", bounded(input, "repeat_penalty", 1, 0, 4));
        if (input.has("top_k")) request.put("top_k", (int) Math.floor(bounded(input, "top_k", 40, 0, 1000)));
        if (input.has("seed")) request.put("seed", (long) Math.floor(bounded(input, "seed", -1, -1, Integer.MAX_VALUE)));
        if (input.has("n") && number(input, "n", 1) != 1) throw new IllegalArgumentException("Only one text generation slot is available");
        if (input.has("top_logprobs")) request.put("top_logprobs", (int) Math.floor(bounded(input, "top_logprobs", 0, 0, 20)));
        if (input.has("stream_options")) {
            JSONObject options = input.getJSONObject("stream_options");
            ChatProtocol.fields(options, "stream_options", "include_usage", "include_obfuscation");
            for (String key : Arrays.asList("include_usage", "include_obfuscation")) if (options.has(key) && !(options.opt(key) instanceof Boolean)) throw new RequestError("stream_options." + key, "Use a boolean");
            if (options.optBoolean("include_obfuscation")) throw new RequestError("stream_options.include_obfuscation", "Stream obfuscation is unavailable");
            request.getJSONObject("stream_options").remove("include_obfuscation");
        }
        if (input.has("stop")) {
            Object stop = input.get("stop"); JSONArray stops = stop instanceof String ? new JSONArray().put(stop) : input.getJSONArray("stop");
            if (stops.length() > 8) throw new IllegalArgumentException("At most eight stop strings are allowed");
            for (int i = 0; i < stops.length(); i++) if (!(stops.get(i) instanceof String) || stops.getString(i).length() > 256) throw new IllegalArgumentException("Invalid stop string");
        }
        if (input.has("response_format")) {
            JSONObject format = input.getJSONObject("response_format");
            String type = format.optString("type");
            if (type.equals("json_schema")) {
                ChatProtocol.fields(format, "response_format", "type", "json_schema"); JSONObject wrapper = format.getJSONObject("json_schema");
                ChatProtocol.fields(wrapper, "response_format.json_schema", "name", "description", "schema", "strict");
                ChatProtocol.name(wrapper.opt("name"), "response_format.json_schema.name");
                JsonSchema.check(wrapper.getJSONObject("schema"), "response_format.json_schema.schema");
                if (wrapper.has("strict") && !(wrapper.opt("strict") instanceof Boolean)) throw new RequestError("response_format.json_schema.strict", "Use a boolean");
            } else if (format.length() != 1 || !Arrays.asList("text", "json_object").contains(type)) throw new RequestError("response_format", "Use text, json_object or json_schema response format");
        }
        if (input.has("logit_bias")) {
            JSONObject bias = request.getJSONObject("logit_bias"); if (bias.length() > 2048) throw new IllegalArgumentException("Too many token biases");
            for (Iterator<String> it = bias.keys(); it.hasNext();) { String key = it.next(); if (!key.matches("[0-9]{1,9}")) throw new IllegalArgumentException("Invalid token bias ID"); bias.put(key, bounded(bias, key, 0, -100, 100)); }
        }
        return request;
    }
    private static double number(JSONObject input, String key, double fallback) {
        if (!input.has(key)) return fallback;
        Object value = input.opt(key); if (!(value instanceof Number) || !Double.isFinite(((Number) value).doubleValue())) throw new IllegalArgumentException("Use a finite numeric value for " + key);
        return ((Number) value).doubleValue();
    }
    private static double bounded(JSONObject input, String key, double fallback, double minimum, double maximum) { return Math.max(minimum, Math.min(maximum, number(input, key, fallback))); }
}
