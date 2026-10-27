package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Text-only public requests with the selected model's saved output ceiling and sampling defaults. */
public final class TextRequest {
    private TextRequest() {}
    public static JSONObject normalize(String path, JSONObject input, String model, JSONObject settings) throws Exception {
        Set<String> allowed = new HashSet<>(Arrays.asList("model", "messages", "prompt", "stream", "max_tokens", "max_completion_tokens", "temperature", "top_p", "top_k", "min_p", "seed", "stop", "presence_penalty", "frequency_penalty", "repeat_penalty", "stream_options", "response_format", "logit_bias", "logprobs", "top_logprobs", "n", "cache_prompt"));
        for (Iterator<String> it = input.keys(); it.hasNext();) if (!allowed.contains(it.next())) throw new IllegalArgumentException("Unsupported text request field");
        if (!input.optString("model", model).equals(model)) throw new IllegalStateException("The requested text model is not loaded; select/load it in the App first");
        JSONObject request = DataFiles.copy(input); request.put("model", model);
        if (path.equals("/v1/chat/completions")) {
            if (input.has("prompt")) throw new IllegalArgumentException("Use messages for chat completions");
            JSONArray messages = input.getJSONArray("messages");
            if (messages.length() < 1 || messages.length() > 128) throw new IllegalArgumentException("Use 1–128 text messages");
            for (int i = 0; i < messages.length(); i++) {
                JSONObject message = messages.getJSONObject(i);
                for (Iterator<String> it = message.keys(); it.hasNext();) if (!Arrays.asList("role", "content", "name").contains(it.next())) throw new IllegalArgumentException("Only plain text chat messages are supported");
                if (!Arrays.asList("system", "developer", "user", "assistant").contains(message.getString("role")) || !(message.get("content") instanceof String)) throw new IllegalArgumentException("Only plain text chat messages are supported; media URLs are not fetched");
                if (message.getString("content").length() > 64000) throw new IllegalArgumentException("A chat message is too long");
            }
        } else {
            if (input.has("messages") || !(input.get("prompt") instanceof String) || input.getString("prompt").isEmpty() || input.getString("prompt").length() > 64000) throw new IllegalArgumentException("Use a nonempty plain text prompt");
        }
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
            if (options.length() > 1 || options.length() == 1 && !(options.opt("include_usage") instanceof Boolean)) throw new IllegalArgumentException("Unsupported stream options");
        }
        if (input.has("stop")) {
            Object stop = input.get("stop"); JSONArray stops = stop instanceof String ? new JSONArray().put(stop) : input.getJSONArray("stop");
            if (stops.length() > 8) throw new IllegalArgumentException("At most eight stop strings are allowed");
            for (int i = 0; i < stops.length(); i++) if (!(stops.get(i) instanceof String) || stops.getString(i).length() > 256) throw new IllegalArgumentException("Invalid stop string");
        }
        if (input.has("response_format")) {
            JSONObject format = input.getJSONObject("response_format");
            if (format.length() != 1 || !Arrays.asList("text", "json_object").contains(format.optString("type"))) throw new IllegalArgumentException("Use text or json_object response format");
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
