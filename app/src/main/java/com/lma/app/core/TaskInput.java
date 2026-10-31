package com.lma.app.core;

import org.json.JSONObject;
import org.json.JSONArray;
import java.util.*;

/** Text and explicitly bound local-media inputs; paths and remote URLs are never task inputs. */
public final class TaskInput {
    private TaskInput() {}
    public static JSONObject validate(JSONObject source) throws Exception {
        if ("model.assemble".equals(source.optString("type"))) {
            for (Iterator<String> it = source.keys(); it.hasNext();) if (!Arrays.asList("bundleId", "type", "preparedAssetsId", "assemblyId", "assemblyFingerprint").contains(it.next())) throw new IllegalArgumentException("Assembly accepts selected asset IDs and a signed plan, never paths or downloads");
            ModelBundle.key(source.getString("bundleId")); ModelBundle.key(source.getString("assemblyId"));
            if (!source.getString("preparedAssetsId").matches("prep_[a-f0-9]{32}") || !Protocol.isSha256(source.getString("assemblyFingerprint"))) throw new IllegalArgumentException("Select prepared assets and the current App assembly plan");
            return DataFiles.copy(source);
        }
        if ("model.prepare".equals(source.optString("type"))) {
            for (Iterator<String> it = source.keys(); it.hasNext();) if (!Arrays.asList("bundleId", "type", "preparationId", "planFingerprint").contains(it.next())) throw new IllegalArgumentException("Unknown preparation field; paths and executable modules cannot be supplied");
            ModelBundle.key(source.getString("bundleId")); ModelBundle.key(source.getString("preparationId"));
            if (!Protocol.isSha256(source.getString("planFingerprint"))) throw new IllegalArgumentException("Select the current App preparation plan");
            return DataFiles.copy(source);
        }
        for (Iterator<String> it = source.keys(); it.hasNext();) if (!Arrays.asList("bundleId", "type", "input", "parameters", "allowUnmeasured", "adapters").contains(it.next())) throw new IllegalArgumentException("Unknown task request field");
        ModelBundle.key(source.getString("bundleId"));
        if (!Arrays.asList("text.generate", "image.generate", "video.generate", "speech.synthesize", "audio.generate", "mesh.generate").contains(source.getString("type"))) throw new IllegalArgumentException("Unknown local task type");
        if (source.has("allowUnmeasured") && !(source.get("allowUnmeasured") instanceof Boolean)) throw new IllegalArgumentException("allowUnmeasured must be an explicit boolean");
        if (source.has("parameters") && !(source.get("parameters") instanceof JSONObject)) throw new IllegalArgumentException("parameters must be a JSON object");
        if (source.has("adapters")) {
            if (!source.getString("type").equals("image.generate")) throw new IllegalArgumentException("LoRA selection requires an image generation task");
            JSONArray adapters = source.getJSONArray("adapters");
            if (adapters.length() > 8) throw new IllegalArgumentException("At most eight LoRAs can be selected");
            Set<String> ids = new HashSet<>(); ids.add(source.getString("bundleId"));
            for (int i = 0; i < adapters.length(); i++) {
                JSONObject item = adapters.getJSONObject(i);
                for (Iterator<String> it = item.keys(); it.hasNext();) if (!Arrays.asList("bundleId", "scale").contains(it.next())) throw new IllegalArgumentException("Unknown adapter selection field");
                if (!ids.add(ModelBundle.key(item.getString("bundleId")))) throw new IllegalArgumentException("Select each model or adapter only once");
                if (item.has("scale") && (!(item.get("scale") instanceof Number) || !Double.isFinite(item.getDouble("scale")))) throw new IllegalArgumentException("LoRA scale must be a finite number");
            }
        }
        JSONObject input = source.getJSONObject("input");
        for (Iterator<String> it = input.keys(); it.hasNext();) if (!Arrays.asList("prompt", "negativePrompt", "artifacts", "transcripts").contains(it.next())) throw new IllegalArgumentException("Unsupported input field; use prompt text and explicit local artifact references");
        if (!(input.get("prompt") instanceof String) || input.getString("prompt").trim().isEmpty() || input.getString("prompt").length() > 16000) throw new IllegalArgumentException("Use a nonempty prompt of at most 16000 characters");
        if (input.has("negativePrompt") && (!(input.get("negativePrompt") instanceof String) || input.getString("negativePrompt").length() > 16000)) throw new IllegalArgumentException("negativePrompt must be text of at most 16000 characters");
        if (input.has("transcripts")) {
            JSONObject transcripts = input.getJSONObject("transcripts");
            if (transcripts.length() > 8) throw new IllegalArgumentException("At most eight reference transcripts are allowed");
            for (Iterator<String> it = transcripts.keys(); it.hasNext();) {
                String role = InputSpec.key(it.next()); Object value = transcripts.get(role);
                if (!(value instanceof String) || ((String) value).trim().isEmpty() || ((String) value).length() > 4000 || ((String) value).indexOf('\0') >= 0) throw new IllegalArgumentException("Reference transcripts must contain 1-4000 text characters without NUL");
            }
        }
        if (input.has("artifacts")) {
            JSONArray refs = input.getJSONArray("artifacts");
            if (refs.length() < 1 || refs.length() > 8) throw new IllegalArgumentException("Select 1-8 local inputs");
            Set<String> roles = new HashSet<>();
            for (int i = 0; i < refs.length(); i++) {
                JSONObject ref = refs.getJSONObject(i);
                for (Iterator<String> it = ref.keys(); it.hasNext();) if (!Arrays.asList("role", "artifactId").contains(it.next())) throw new IllegalArgumentException("Use an artifact ID and role; paths, URLs and client receipts are not accepted");
                if (!roles.add(InputSpec.key(ref.getString("role")))) throw new IllegalArgumentException("Select each input role only once");
                ModelBundle.key(ref.getString("artifactId"));
            }
        }
        if (source.toString().length() > 32000) throw new IllegalArgumentException("Task request is too large");
        return DataFiles.copy(source);
    }
    public static String fingerprint(JSONObject source) throws Exception {
        return Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(DataFiles.canonical(source).getBytes(java.nio.charset.StandardCharsets.UTF_8)));
    }
}
