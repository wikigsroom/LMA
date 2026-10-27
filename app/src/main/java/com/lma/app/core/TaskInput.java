package com.lma.app.core;

import org.json.JSONObject;
import java.util.*;

/** Current prompt-task contract; unsupported input fields fail rather than being silently ignored. */
public final class TaskInput {
    private TaskInput() {}
    public static JSONObject validate(JSONObject source) throws Exception {
        for (Iterator<String> it = source.keys(); it.hasNext();) if (!Arrays.asList("bundleId", "type", "input", "parameters", "allowUnmeasured").contains(it.next())) throw new IllegalArgumentException("Unknown task request field");
        ModelBundle.key(source.getString("bundleId"));
        if (!Arrays.asList("text.generate", "image.generate", "video.generate", "speech.synthesize", "audio.generate").contains(source.getString("type"))) throw new IllegalArgumentException("Unknown local task type");
        if (source.has("allowUnmeasured") && !(source.get("allowUnmeasured") instanceof Boolean)) throw new IllegalArgumentException("allowUnmeasured must be an explicit boolean");
        if (source.has("parameters") && !(source.get("parameters") instanceof JSONObject)) throw new IllegalArgumentException("parameters must be a JSON object");
        JSONObject input = source.getJSONObject("input");
        for (Iterator<String> it = input.keys(); it.hasNext();) if (!Arrays.asList("prompt", "negativePrompt").contains(it.next())) throw new IllegalArgumentException("Unsupported input field; this task contract accepts prompt text only");
        if (!(input.get("prompt") instanceof String) || input.getString("prompt").trim().isEmpty() || input.getString("prompt").length() > 16000) throw new IllegalArgumentException("Use a nonempty prompt of at most 16000 characters");
        if (input.has("negativePrompt") && (!(input.get("negativePrompt") instanceof String) || input.getString("negativePrompt").length() > 16000)) throw new IllegalArgumentException("negativePrompt must be text of at most 16000 characters");
        if (source.toString().length() > 32000) throw new IllegalArgumentException("Task request is too large");
        return DataFiles.copy(source);
    }
    public static String fingerprint(JSONObject source) throws Exception {
        return Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(DataFiles.canonical(source).getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }
}
