package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.IOException;
import java.util.*;

/** An App-signed association of prepared outputs with a complete runtime model manifest. */
public final class AssemblyPlan {
    public final String id, name, sourceBundleId, preparationId, preparationFingerprint, bundleId, bundleFingerprint, fingerprint;
    public final Map<String,String> roles;
    private final JSONObject source;
    public AssemblyPlan(JSONObject value, PreparationPlan preparation, ModelBundle target) throws Exception {
        if (!"lma.model-assembly/1".equals(value.getString("schema"))) throw new IOException("Unsupported model assembly plan");
        Set<String> allowed = new HashSet<>(Arrays.asList("schema", "id", "name", "sourceBundleId", "preparationId", "bundleId", "roles"));
        for (Iterator<String> it = value.keys(); it.hasNext();) if (!allowed.contains(it.next())) throw new IOException("Unknown assembly plan field");
        id = ModelBundle.key(value.getString("id")); name = value.getString("name");
        if (name.isEmpty() || name.length() > 160) throw new IOException("Invalid assembly plan name");
        sourceBundleId = ModelBundle.key(value.getString("sourceBundleId")); preparationId = ModelBundle.key(value.getString("preparationId"));
        bundleId = ModelBundle.key(value.getString("bundleId"));
        if (preparation == null || !preparationId.equals(preparation.id) || sourceBundleId.equals(bundleId) || !bundleId.equals(target.id)) throw new IOException("Invalid signed assembly dependencies");
        preparationFingerprint = preparation.fingerprint; bundleFingerprint = TaskInput.fingerprint(target.json());
        JSONArray list = value.getJSONArray("roles");
        if (list.length() < 1 || list.length() > 64) throw new IOException("Invalid assembly component count");
        Map<String,String> selected = new LinkedHashMap<>(); Set<String> destinations = new HashSet<>();
        for (int i = 0; i < list.length(); i++) {
            JSONObject item = list.getJSONObject(i);
            if (item.length() != 2 || !item.has("source") || !item.has("target")) throw new IOException("Assembly components select roles, never file paths");
            String from = ModelBundle.key(item.getString("source")), to = ModelBundle.key(item.getString("target"));
            if (selected.put(from, to) != null || !destinations.add(to)) throw new IOException("Select every assembly component at most once");
        }
        roles = Collections.unmodifiableMap(selected); source = DataFiles.copy(value);
        fingerprint = TaskInput.fingerprint(new JSONObject().put("plan", source).put("preparationFingerprint", preparationFingerprint).put("bundleFingerprint", bundleFingerprint));
        validate(preparation, target);
    }
    public JSONObject json() { return DataFiles.copy(source); }
    public void validate(PreparationPlan preparation, ModelBundle target) throws Exception {
        if (!preparation.id.equals(preparationId) || !preparation.fingerprint.equals(preparationFingerprint)) throw new IOException("Assembly requires a different preparation contract");
        target(target); Map<String,PreparationPlan.Output> outputs = new HashMap<>();
        for (PreparationPlan.Stage stage : preparation.stages) for (PreparationPlan.Output output : stage.outputs) outputs.put(output.role, output);
        for (Map.Entry<String,String> role : roles.entrySet()) {
            PreparationPlan.Output output = outputs.get(role.getKey()); ModelBundle.Component component = target.component(role.getValue());
            if (output == null || component.bytes != output.bytes || !component.sha256.equals(output.sha256)) throw new IOException("Assembly component differs from the signed preparation output");
        }
    }
    private void target(ModelBundle target) throws Exception {
        if (!bundleId.equals(target.id) || !bundleFingerprint.equals(TaskInput.fingerprint(target.json()))) throw new IOException("Runtime model manifest changed; explicitly review the current assembly plan");
    }
    public void matches(JSONObject prepared, ModelBundle target) throws Exception {
        target(target);
        if (!sourceBundleId.equals(prepared.getString("bundleId")) || !preparationId.equals(prepared.getString("planId")) || !preparationFingerprint.equals(prepared.getString("planFingerprint"))) throw new IOException("Prepared assets do not belong to the selected assembly plan");
        Map<String,JSONObject> outputs = new HashMap<>(); JSONArray list = prepared.getJSONArray("outputs");
        for (int i = 0; i < list.length(); i++) { JSONObject output = list.getJSONObject(i); if (outputs.put(output.getString("role"), output) != null) throw new IOException("Duplicate prepared role"); }
        for (Map.Entry<String,String> role : roles.entrySet()) {
            JSONObject output = outputs.get(role.getKey()); ModelBundle.Component component = target.component(role.getValue());
            if (output == null || component.bytes != output.getLong("bytes") || !component.sha256.equals(output.getString("sha256"))) throw new IOException("Prepared runtime component differs from the selected model");
        }
    }
    public JSONObject describe(ModelBundle target) throws Exception {
        target(target); long bytes = 0; Set<String> mapped = new HashSet<>(roles.values()); JSONArray remaining = new JSONArray();
        for (ModelBundle.Component component : target.components) {
            if (mapped.contains(component.role)) bytes = Math.addExact(bytes, component.bytes);
            else remaining.put(new JSONObject().put("role", component.role).put("path", component.path).put("bytes", component.bytes)
                    .put("sha256", component.sha256).put("repository", component.repository).put("revision", component.revision).put("url", component.url));
        }
        return new JSONObject().put("id", id).put("name", name).put("fingerprint", fingerprint).put("bundleId", bundleId)
                .put("preparationFingerprint", preparationFingerprint).put("bundleFingerprint", bundleFingerprint)
                .put("linkedComponents", roles.size()).put("linkedBytes", bytes).put("remainingComponents", remaining)
                .put("automaticDownloads", false).put("modelInference", false).put("physicalAndroid", false);
    }
}
