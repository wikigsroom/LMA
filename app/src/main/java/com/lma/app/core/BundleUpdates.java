package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** User-reviewed version changes. Manifests and job bundle IDs never change. */
public final class BundleUpdates {
    private BundleUpdates() {}
    public static void compatible(ModelBundle from, ModelBundle to) throws Exception {
        if (from.id.equals(to.id)) throw new IllegalArgumentException("Select a different immutable bundle version");
        if (!from.engine.equals(to.engine) || !from.architecture.equals(to.architecture) || !from.pipeline.equals(to.pipeline)
                || !from.backend.equals(to.backend) || !from.tasks.equals(to.tasks)
                || !DataFiles.canonical(from.json().optJSONObject("adapter")).equals(DataFiles.canonical(to.json().optJSONObject("adapter"))))
            throw new IllegalArgumentException("An update must preserve engine, architecture, pipeline, backend, tasks and adapter constraints; add other models independently");
    }
    private static Map<String, ModelBundle.Component> roles(ModelBundle bundle) {
        Map<String, ModelBundle.Component> result = new TreeMap<>();
        for (ModelBundle.Component c : bundle.components) result.put(c.role, c);
        return result;
    }
    private static JSONObject component(ModelBundle.Component c) throws Exception {
        if (c == null) return null;
        return new JSONObject().put("path", c.path).put("importPath", c.importPath).put("bytes", c.bytes).put("format", c.format)
                .put("repository", c.repository).put("revision", c.revision).put("objectId", c.objectId)
                .put("sha256", c.sha256).put("gitBlobSha1", c.gitBlobSha1);
    }
    private static boolean numeric(String type) { return type.equals("integer") || type.equals("number"); }
    private static JSONObject fields(ParameterSchema b) { JSONObject f = b.json().optJSONObject("fields"); return f == null ? new JSONObject() : f; }
    /** Migration is previewed with reasons; old settings are never mutated. */
    public static JSONObject settings(ModelBundle from, ModelBundle to, JSONObject oldValues, JSONObject targetValues, String mode) throws Exception { return settings(from.parameters(), to.parameters(), oldValues, targetValues, mode); }
    private static JSONObject settings(ParameterSchema from, ParameterSchema to, JSONObject oldValues, JSONObject targetValues, String mode) throws Exception {
        if (!mode.equals("copy") && !mode.equals("keep")) throw new IllegalArgumentException("Choose copy or keep for model settings");
        JSONObject oldFields = fields(from), newFields = fields(to);
        JSONObject defaults = to.normalize(new JSONObject(), new JSONObject()).getJSONObject("values");
        JSONObject candidate = DataFiles.copy(mode.equals("keep") ? targetValues : defaults);
        Map<String, String> reasons = new HashMap<>();
        if (mode.equals("copy")) for (Iterator<String> it = newFields.keys(); it.hasNext();) {
            String key = it.next(); JSONObject target = newFields.getJSONObject(key), previous = oldFields.optJSONObject(key);
            if (previous == null || !oldValues.has(key)) { reasons.put(key, "new_default"); continue; }
            String a = previous.getString("type"), b = target.getString("type"); Object value = oldValues.get(key);
            if (!a.equals(b) && !(numeric(a) && numeric(b))) { reasons.put(key, "type_reset"); continue; }
            if (b.equals("string") && ((String) value).length() > target.optInt("maxLength", 16000)) { reasons.put(key, "length_reset"); continue; }
            if (b.equals("enum")) {
                boolean supported = false; JSONArray options = target.getJSONArray("values");
                for (int i = 0; i < options.length(); i++) if (options.get(i).equals(value)) supported = true;
                if (!supported) { reasons.put(key, "selection_reset"); continue; }
            }
            candidate.put(key, value); reasons.put(key, "retained");
        }
        JSONObject effective;
        try { effective = to.normalize(candidate, new JSONObject()); }
        catch (IllegalArgumentException invalidShape) {
            // Each schema's defaults are valid. Reset only the jointly compiled dimensions.
            JSONArray shapes = to.json().optJSONArray("allowedShapes");
            if (!mode.equals("copy") || shapes == null || shapes.length() == 0) throw invalidShape;
            Set<String> dimensions = new HashSet<>();
            for (int i = 0; i < shapes.length(); i++) for (Iterator<String> it = shapes.getJSONObject(i).keys(); it.hasNext();) dimensions.add(it.next());
            for (String key : dimensions) { candidate.put(key, defaults.get(key)); reasons.put(key, "joint_shape_reset"); }
            effective = to.normalize(candidate, new JSONObject());
        }
        JSONArray adjustments = effective.getJSONArray("adjustments");
        for (int i = 0; i < adjustments.length(); i++) reasons.put(adjustments.getJSONObject(i).getString("field"), "clamped");
        JSONObject values = effective.getJSONObject("values"); Set<String> keys = new TreeSet<>();
        for (Iterator<String> it = oldValues.keys(); it.hasNext();) keys.add(it.next());
        for (Iterator<String> it = values.keys(); it.hasNext();) keys.add(it.next());
        JSONArray changes = new JSONArray();
        for (String key : keys) changes.put(new JSONObject().put("field", key)
                .put("from", oldValues.has(key) ? oldValues.get(key) : JSONObject.NULL)
                .put("to", values.has(key) ? values.get(key) : JSONObject.NULL)
                .put("reason", !values.has(key) ? "removed" : mode.equals("keep") ? "target_settings" : reasons.getOrDefault(key, "retained")));
        return new JSONObject().put("values", values).put("changes", changes).put("adjustments", adjustments);
    }
    public static JSONObject plan(ModelBundle from, ModelBundle to, JSONObject oldValues, JSONObject targetValues, JSONObject version, JSONObject download, String mode) throws Exception { return plan(from, to, oldValues, targetValues, version, download, mode, from.parameters(), to.parameters()); }
    public static JSONObject plan(ModelBundle from, ModelBundle to, JSONObject oldValues, JSONObject targetValues, JSONObject version, JSONObject download, String mode, ParameterSchema sourceSchema, ParameterSchema targetSchema) throws Exception {
        compatible(from, to);
        JSONObject migration = settings(sourceSchema, targetSchema, oldValues, targetValues, mode);
        JSONObject identity = new JSONObject().put("from", from.json()).put("to", to.json()).put("sourceSettings", oldValues)
                .put("targetSettings", targetValues).put("version", version).put("settingsMode", mode).put("sourceParameterSchema", sourceSchema.json()).put("targetParameterSchema", targetSchema.json());
        String review = Protocol.hex(MessageDigest.getInstance("SHA-256").digest(DataFiles.canonical(identity).getBytes(StandardCharsets.UTF_8)));
        Map<String, ModelBundle.Component> old = roles(from), next = roles(to); Set<String> all = new TreeSet<>(old.keySet()); all.addAll(next.keySet());
        JSONArray components = new JSONArray();
        for (String role : all) {
            ModelBundle.Component a = old.get(role), b = next.get(role); JSONObject before = component(a), after = component(b);
            String change = a == null ? "added" : b == null ? "removed" : !a.objectId.equals(b.objectId) || a.bytes != b.bytes ? "changed"
                    : DataFiles.canonical(before).equals(DataFiles.canonical(after)) ? "unchanged" : "source_changed";
            components.put(new JSONObject().put("role", role).put("change", change).put("from", before == null ? JSONObject.NULL : before).put("to", after == null ? JSONObject.NULL : after));
        }
        JSONArray metadataChanges = new JSONArray();
        for (String key : Arrays.asList("modelId", "recipeId", "license", "capabilities", "uncensored", "parameters", "description")) {
            Object a = from.json().opt(key), b = to.json().opt(key);
            if (!DataFiles.canonical(a).equals(DataFiles.canonical(b))) metadataChanges.put(key);
        }
        return new JSONObject().put("fromBundleId", from.id).put("toBundleId", to.id).put("settingsMode", mode).put("review", review)
                .put("components", components).put("settings", migration).put("metadataChanges", metadataChanges).put("download", download);
    }
}
