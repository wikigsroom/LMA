package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Signed-engine input roles. Model metadata cannot enable an unsupported input path. */
public final class InputSpec {
    private final JSONObject roles;
    private String promptHelp = "";
    private String fixedPrompt;
    public InputSpec(JSONObject roles) throws Exception {
        this.roles = DataFiles.copy(roles);
        if (roles.length() > 8) throw new IllegalArgumentException("At most eight input roles are allowed");
        for (Iterator<String> it = roles.keys(); it.hasNext();) {
            String role = it.next(); key(role); JSONObject rule = roles.getJSONObject(role);
            Set<String> fields = new HashSet<>(Arrays.asList("label", "required", "mimes", "maxBytes", "minDurationMs", "maxDurationMs", "maxPixels", "transcript"));
            for (Iterator<String> names = rule.keys(); names.hasNext();) if (!fields.contains(names.next())) throw new IllegalArgumentException("Unknown input rule");
            if (!(rule.get("required") instanceof Boolean) || rule.getString("label").isEmpty() || rule.getString("label").length() > 80) throw new IllegalArgumentException("Invalid input role description");
            JSONArray mimes = rule.getJSONArray("mimes");
            if (mimes.length() < 1 || mimes.length() > 6) throw new IllegalArgumentException("Input MIME types are required");
            for (int i = 0; i < mimes.length(); i++) if (!Arrays.asList("image/png", "image/jpeg", "audio/wav", "video/mp4", TextResult.MIME).contains(mimes.getString(i))) throw new IllegalArgumentException("Unsupported input MIME type");
            for (String limit : Arrays.asList("maxBytes", "minDurationMs", "maxDurationMs", "maxPixels")) if (rule.has(limit) && (!(rule.get(limit) instanceof Number) || !Double.isFinite(rule.getDouble(limit)) || rule.getDouble(limit) != rule.getLong(limit) || rule.getLong(limit) < 1)) throw new IllegalArgumentException("Invalid input limit");
            if (rule.has("minDurationMs") && rule.has("maxDurationMs") && rule.getLong("minDurationMs") > rule.getLong("maxDurationMs")) throw new IllegalArgumentException("Reversed input duration limits");
            if (!rule.has("maxBytes") || rule.getLong("maxBytes") > ArtifactStore.MAX_INPUT_BYTES) throw new IllegalArgumentException("Input byte limit is required");
            if (rule.has("transcript")) {
                JSONObject text = rule.getJSONObject("transcript");
                for (Iterator<String> names = text.keys(); names.hasNext();) if (!Arrays.asList("label", "maxLength").contains(names.next())) throw new IllegalArgumentException("Unknown transcript rule");
                if (!(text.get("label") instanceof String) || text.getString("label").trim().isEmpty() || text.getString("label").length() > 80 || !(text.get("maxLength") instanceof Number) || text.getDouble("maxLength") != text.getInt("maxLength") || text.getInt("maxLength") < 1 || text.getInt("maxLength") > 4000) throw new IllegalArgumentException("Invalid transcript rule");
            }
        }
    }
    public InputSpec(JSONObject roles, String promptHelp) throws Exception {
        this(roles);
        if (promptHelp == null || promptHelp.length() > 400 || promptHelp.indexOf('\0') >= 0) throw new IllegalArgumentException("Invalid prompt help");
        this.promptHelp = promptHelp;
    }
    public InputSpec withFixedPrompt(String value) {
        if (value == null || value.trim().isEmpty() || value.length() > 4000 || value.indexOf(0) >= 0) throw new IllegalArgumentException("Invalid fixed prompt");
        fixedPrompt = value; return this;
    }
    public static InputSpec promptOnly() throws Exception { return new InputSpec(new JSONObject()); }
    public JSONObject json() throws Exception { JSONObject result = new JSONObject().put("version", 1).put("roles", DataFiles.copy(roles)); if (!promptHelp.isEmpty()) result.put("promptHelp", promptHelp); if (fixedPrompt != null) result.put("fixedPrompt", fixedPrompt); return result; }
    public static String key(String role) {
        if (role == null || !role.matches("[a-z][a-z0-9_]{0,47}")) throw new IllegalArgumentException("Invalid input role"); return role;
    }
    public void validate(JSONArray receipts) throws Exception {
        validate(receipts, new JSONObject());
    }
    public void validate(JSONArray receipts, JSONObject input) throws Exception {
        if (fixedPrompt != null && (!fixedPrompt.equals(input.optString("prompt")) || !input.optString("negativePrompt").isEmpty())) throw new IllegalArgumentException("This recipe requires its declared fixed prompt without negative conditioning");
        JSONObject transcripts = input.has("transcripts") ? input.getJSONObject("transcripts") : new JSONObject();
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < receipts.length(); i++) {
            JSONObject receipt = receipts.getJSONObject(i); String role = key(receipt.getString("role"));
            if (!seen.add(role)) throw new IllegalArgumentException("Select each input role only once");
            JSONObject rule = roles.optJSONObject(role);
            if (rule == null) throw new IllegalArgumentException("This model/recipe does not accept input role: " + role);
            JSONObject metadata = receipt.getJSONObject("metadata"); boolean allowed = false;
            for (int j = 0; j < rule.getJSONArray("mimes").length(); j++) if (rule.getJSONArray("mimes").getString(j).equals(metadata.getString("mime"))) allowed = true;
            if (!allowed) throw new IllegalArgumentException("Input media type does not match role: " + role);
            if (receipt.getLong("bytes") < 1 || receipt.getLong("bytes") > rule.getLong("maxBytes")) throw new IllegalArgumentException("Input exceeds this recipe's byte limit: " + role);
            if (rule.has("maxDurationMs") && (!metadata.has("durationMs") || metadata.getLong("durationMs") < 1 || metadata.getLong("durationMs") > rule.getLong("maxDurationMs"))) throw new IllegalArgumentException("Input duration is unknown or exceeds this recipe's limit: " + role);
            if (rule.has("minDurationMs") && (!metadata.has("durationMs") || metadata.getLong("durationMs") < rule.getLong("minDurationMs"))) throw new IllegalArgumentException("Input is shorter than this recipe requires: " + role);
            if (rule.has("maxPixels") && (!metadata.has("width") || !metadata.has("height") || metadata.getLong("width") < 1 || metadata.getLong("height") < 1 || Math.multiplyExact(metadata.getLong("width"), metadata.getLong("height")) > rule.getLong("maxPixels"))) throw new IllegalArgumentException("Input dimensions are unknown or exceed this recipe's limit: " + role);
            if (rule.has("transcript")) {
                Object value = transcripts.opt(role);
                if (!(value instanceof String) || ((String) value).trim().isEmpty() || ((String) value).length() > rule.getJSONObject("transcript").getInt("maxLength") || ((String) value).indexOf('\0') >= 0) throw new IllegalArgumentException("Provide the matching reference transcript: " + role);
            }
        }
        for (Iterator<String> it = transcripts.keys(); it.hasNext();) {
            String role = key(it.next());
            if (!seen.contains(role) || !roles.getJSONObject(role).has("transcript")) throw new IllegalArgumentException("Transcript requires a selected input role that accepts text: " + role);
        }
        for (Iterator<String> it = roles.keys(); it.hasNext();) { String role = it.next(); if (roles.getJSONObject(role).getBoolean("required") && !seen.contains(role)) throw new IllegalArgumentException("A local input is required: " + role); }
    }
}
