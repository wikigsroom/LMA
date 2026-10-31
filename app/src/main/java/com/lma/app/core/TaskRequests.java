package com.lma.app.core;

import org.json.JSONObject;
import java.util.Arrays;

/** Rebuild user-editable requests without carrying execution receipts or admission decisions. */
public final class TaskRequests {
    private TaskRequests() {}
    public static boolean generation(String type) {
        return Arrays.asList("text.generate", "image.generate", "video.generate", "speech.synthesize", "audio.generate", "mesh.generate").contains(type);
    }
    public static JSONObject replay(JSONObject frozen) throws Exception {
        String type = frozen.getString("type");
        String[] fields = "model.prepare".equals(type)
                ? new String[]{"bundleId", "type", "preparationId", "planFingerprint"}
                : "model.assemble".equals(type)
                ? new String[]{"bundleId", "type", "preparedAssetsId", "assemblyId", "assemblyFingerprint"}
                : new String[]{"bundleId", "type", "input", "parameters", "allowUnmeasured", "adapters"};
        JSONObject request = new JSONObject();
        for (String field : fields) if (frozen.has(field)) request.put(field, frozen.get(field));
        return TaskInput.validate(request);
    }
    public static JSONObject editable(JSONObject frozen) throws Exception {
        if (!generation(frozen.optString("type"))) throw new IllegalArgumentException("Only generation tasks can be opened in the editor");
        return replay(frozen).put("allowUnmeasured", false);
    }
    public static JSONObject fromArtifact(JSONObject artifact) throws Exception {
        if ("imported".equals(artifact.optJSONObject("origin") == null ? "" : artifact.getJSONObject("origin").optString("kind")))
            throw new IllegalArgumentException("Imported media has no generation request; select it as a reference input");
        JSONObject provenance = artifact.getJSONObject("provenance");
        if (!"same_android_phone".equals(provenance.optString("execution"))) throw new IllegalArgumentException("This result has no local generation request");
        JSONObject result = editable(provenance.getJSONObject("request"));
        if (!result.getString("bundleId").equals(provenance.getJSONObject("bundle").getString("id"))) throw new IllegalArgumentException("Result model identity does not match its request");
        return result;
    }
    /** Drafts may contain an empty prompt; all other request shape constraints still apply. */
    public static JSONObject draft(JSONObject source) throws Exception {
        if (!generation(source.optString("type"))) throw new IllegalArgumentException("Only generation requests can be saved as drafts");
        JSONObject request = DataFiles.copy(source), input = request.getJSONObject("input");
        Object prompt = input.get("prompt");
        if (!(prompt instanceof String)) throw new IllegalArgumentException("Draft prompt must be text");
        boolean empty = ((String) prompt).trim().isEmpty();
        if (((String) prompt).length() > 16000) throw new IllegalArgumentException("Draft prompt is too long");
        if (empty) input.put("prompt", "draft");
        request = TaskInput.validate(request);
        if (empty) request.getJSONObject("input").put("prompt", prompt);
        if (request.toString().length() > 32000) throw new IllegalArgumentException("Draft request is too large");
        return request.put("allowUnmeasured", false);
    }
}
