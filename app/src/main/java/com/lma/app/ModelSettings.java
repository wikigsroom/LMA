package com.lma.app;

import org.json.JSONArray;
import org.json.JSONObject;

/** Per-model inference preferences and the bounds actually available for that file. */
public final class ModelSettings {
    public static final String SYSTEM = "你是一个有帮助的本地助手。请优先使用用户的语言，准确、清楚地回答。";
    public static final String[] KEYS = {"threads", "context", "maxTokens", "temperature", "reasoning", "systemPrompt"};
    private ModelSettings() {}
    public static JSONObject defaults() throws Exception {
        return new JSONObject().put("threads", Math.min(4, Runtime.getRuntime().availableProcessors())).put("context", 2048).put("maxTokens", 512)
                .put("temperature", 0.7).put("reasoning", "off").put("systemPrompt", SYSTEM);
    }
    private static double numeric(JSONObject value, String key, double fallback) {
        if (!value.has(key)) return fallback;
        Object raw = value.opt(key); double number;
        try { number = raw instanceof Number ? ((Number) raw).doubleValue() : Double.parseDouble(String.valueOf(raw)); }
        catch (Exception error) { throw new IllegalArgumentException("请输入有效的数值：" + key); }
        if (!Double.isFinite(number)) throw new IllegalArgumentException("请输入有限的数值：" + key);
        return number;
    }
    private static int bounded(JSONObject value, String key, int fallback, int min, int max) { return (int) Math.max(min, Math.min(max, Math.floor(numeric(value, key, fallback)))); }
    public static JSONObject normalize(JSONObject base, JSONObject changes, JSONObject metadata) throws Exception {
        JSONObject value = new JSONObject(base.toString());
        for (String key : KEYS) if (changes.has(key)) value.put(key, changes.get(key));
        JSONObject limits = limits(metadata, value.optInt("context", 2048));
        int context = bounded(value, "context", 2048, 2, limits.getInt("contextMax"));
        return new JSONObject().put("threads", bounded(value, "threads", 4, 1, limits.getInt("threadsMax"))).put("context", context)
                .put("maxTokens", bounded(value, "maxTokens", 512, 1, context - 1))
                .put("temperature", Math.max(0, Math.min(2, numeric(value, "temperature", 0.7))))
                .put("reasoning", reasoning(value.optString("reasoning", "off"))).put("systemPrompt", system(value.optString("systemPrompt", SYSTEM)));
    }
    private static String reasoning(String value) { if (!value.equals("off") && !value.equals("auto") && !value.equals("on")) throw new IllegalArgumentException("未知思考模式"); return value; }
    private static String system(String value) { if (value.length() > 4000) throw new IllegalArgumentException("系统提示词超过 4000 个字符"); return value; }
    public static JSONObject limits(JSONObject metadata, int context) throws Exception {
        int declared = metadata.optInt("contextLength");
        int maximum = declared > 1 ? declared : 8192;
        int effective = Math.max(2, Math.min(maximum, context));
        return new JSONObject().put("contextMax", maximum).put("contextKnown", declared > 1).put("maxTokensMax", effective - 1)
                .put("threadsMax", Math.max(1, Runtime.getRuntime().availableProcessors())).put("temperatureMax", 2)
                .put("outputBasis", "context-minus-one; prompt tokens also consume the context");
    }
    public static boolean reload(JSONObject old, JSONObject next) { return old.optInt("threads") != next.optInt("threads") || old.optInt("context") != next.optInt("context") || !old.optString("reasoning").equals(next.optString("reasoning")); }
    public static JSONArray adjusted(JSONObject requested, JSONObject saved) throws Exception {
        JSONArray keys = new JSONArray();
        for (String key : new String[]{"threads", "context", "maxTokens", "temperature"}) if (requested.has(key) && numeric(requested, key, saved.getDouble(key)) != saved.getDouble(key)) keys.put(key);
        return keys;
    }
}
