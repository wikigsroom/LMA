package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Event-versioned local publication. Reads never inspect weights or start engines. */
public final class ApiCatalogue {
    public interface Source {
        String version() throws Exception;
        JSONArray build() throws Exception;
        JSONObject readiness(JSONObject model) throws Exception;
    }
    private final AtomicFile file;
    private final Source source;
    private JSONObject state;
    private JSONArray cached = new JSONArray();
    private String seen = null;
    private long rebuilds;
    public ApiCatalogue(File directory, Source source) throws Exception {
        if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create API catalogue storage");
        file = new AtomicFile(new File(directory, "catalogue.json")); this.source = source;
        try { state = DataFiles.read(file, 4 * 1024 * 1024); }
        catch (FileNotFoundException missing) {
            state = new JSONObject().put("schema", "lma.catalogue-state/1").put("instance_id", "lma_" + UUID.randomUUID().toString().replace("-", ""))
                    .put("revision", 0).put("updated_at", System.currentTimeMillis() / 1000).put("signature", "").put("models", new JSONObject());
            DataFiles.write(file, state, 4 * 1024 * 1024);
        }
        if (!state.getString("schema").equals("lma.catalogue-state/1")) throw new IOException("Unknown API catalogue state");
    }
    public synchronized void invalidate() { seen = null; }
    private void refresh() throws Exception {
        String version = source.version();
        if (version.equals(seen)) return;
        JSONArray built = source.build(); List<JSONObject> sorted = new ArrayList<>(); Set<String> ids = new HashSet<>();
        JSONObject next = DataFiles.copy(state), records = next.getJSONObject("models");
        for (int i = 0; i < built.length(); i++) {
            JSONObject model = DataFiles.copy(built.getJSONObject(i)); String id = ModelBundle.key(model.getString("id"));
            if (!ids.add(id)) throw new IllegalArgumentException("Duplicate published model ID");
            JSONObject capabilities = model.getJSONObject("x_lma"), publication = capabilities.getJSONObject("publication");
            if (!publication.getBoolean("eligible") || capabilities.getJSONArray("operations").length() == 0) throw new IllegalArgumentException("Only eligible generation models can be published");
            String config = model.optString("__config_signature", hash(new JSONObject().put("values", capabilities.getJSONObject("saved_parameters")).put("schema", capabilities.getJSONObject("parameter_schema"))));
            model.remove("__config_signature");
            JSONObject previous = records.optJSONObject(id);
            if (previous == null) previous = new JSONObject().put("created", System.currentTimeMillis() / 1000).put("config_revision", 0).put("config_hash", "");
            if (!previous.getString("config_hash").equals(config)) previous.put("config_revision", Math.addExact(previous.getLong("config_revision"), 1)).put("config_hash", config);
            publication.put("config_revision", previous.getLong("config_revision")); model.put("created", previous.getLong("created"));
            records.put(id, previous); sorted.add(model);
        }
        Collections.sort(sorted, (left, right) -> left.optString("id").compareTo(right.optString("id")));
        JSONArray models = new JSONArray(); for (JSONObject model : sorted) models.put(model);
        String signature = hash(models);
        if (!signature.equals(state.getString("signature"))) {
            next.put("signature", signature).put("revision", Math.addExact(state.getLong("revision"), 1)).put("updated_at", System.currentTimeMillis() / 1000);
            DataFiles.write(file, next, 4 * 1024 * 1024); state = next;
        }
        cached = models; seen = version; rebuilds++;
    }
    public synchronized JSONObject snapshot() throws Exception {
        refresh(); JSONArray models = new JSONArray(cached.toString());
        for (int i = 0; i < models.length(); i++) {
            JSONObject model = models.getJSONObject(i), ready = source.readiness(model);
            ready.put("assets_complete", true).put("runner_available", true).put("configuration_valid", true).put("preflight_required", true);
            model.getJSONObject("x_lma").put("ready", ready); model.put("loaded", ready.getBoolean("loaded"));
        }
        JSONObject metadata = new JSONObject().put("schema", "lma.catalogue/1").put("instance_id", state.getString("instance_id"))
                .put("revision", state.getLong("revision")).put("updated_at", state.getLong("updated_at")).put("state", "current");
        return new JSONObject().put("object", "list").put("data", models).put("x_lma", metadata);
    }
    public synchronized JSONObject model(String id) throws Exception {
        ModelBundle.key(id); JSONArray models = snapshot().getJSONArray("data");
        for (int i = 0; i < models.length(); i++) if (models.getJSONObject(i).getString("id").equals(id)) return models.getJSONObject(i);
        throw new LocalHttp.Failure(404, "lma_model_unavailable", "The requested model is not installed and configured for local API use");
    }
    public synchronized long rebuilds() { return rebuilds; }
    public static String hash(Object value) throws Exception {
        return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(DataFiles.canonical(value).getBytes(StandardCharsets.UTF_8)));
    }
    /** Public tunables only; private prompts, paths and credentials never enter discovery. */
    public static JSONObject publicParameters(JSONObject values) throws Exception {
        JSONObject result = new JSONObject();
        for (Iterator<String> it = values.keys(); it.hasNext();) { String key = it.next(); if (publicField(key)) result.put(key, values.get(key)); }
        return result;
    }
    public static boolean publicField(String key) {
        return !key.toLowerCase(Locale.ROOT).matches(".*(prompt|path|filename|credential|secret|apikey|referenceaudio).*");
    }
    public static JSONObject parameterSchema(JSONObject nativeSchema) throws Exception {
        JSONObject result = new JSONObject().put("type", "object").put("additionalProperties", false), properties = new JSONObject();
        JSONObject fields = nativeSchema.optJSONObject("fields");
        if (fields != null) for (Iterator<String> it = fields.keys(); it.hasNext();) {
            String key = it.next(); if (!publicField(key)) continue;
            JSONObject nativeField = fields.getJSONObject(key), field = DataFiles.copy(nativeField); String type = field.optString("type");
            field.remove("choices"); field.remove("label"); field.remove("help");
            if (field.optDouble("alignmentOrigin", 0) != 0 && field.has("multipleOf")) {
                field.put("x_lma_alignment", new JSONObject().put("origin", field.get("alignmentOrigin")).put("multipleOf", field.remove("multipleOf")));
            }
            field.remove("alignmentOrigin");
            if (type.equals("enum")) { field.put("type", "string"); if (field.has("values")) field.put("enum", field.getJSONArray("values")); }
            field.remove("values"); properties.put(key, field);
        }
        return result.put("properties", properties);
    }
}
