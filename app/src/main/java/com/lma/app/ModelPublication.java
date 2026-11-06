package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Adapter from actual local stores to the API publication cache, never a model probe. */
final class ModelPublication implements ApiCatalogue.Source {
    private final LmaApp app;
    private final EngineHost engine;
    ModelPublication(LmaApp app, EngineHost engine) { this.app = app; this.engine = engine; }
    @Override public String version() {
        return TemplateProfiles.revision() + ":" + app.store.publicationRevision() + ":" + (app.bundles == null ? 0 : app.bundles.publicationRevision()) + ":" + (app.prepared == null ? 0 : app.prepared.publicationRevision());
    }
    @Override public JSONArray build() throws Exception {
        JSONArray result = new JSONArray(), text = app.store.publicationSnapshot(); Set<String> aliases = new HashSet<>();
        for (int i = 0; i < text.length(); i++) {
            JSONObject record = text.getJSONObject(i), config = record.getJSONObject("config"), values = config.getJSONObject("values"), limits = config.getJSONObject("limits");
            String id = record.getString("id"), bound = record.optString("bundleId"); if (!bound.isEmpty()) aliases.add(bound);
            JSONObject fields = new JSONObject();
            fields.put("context", numeric("integer", 2, limits.getInt("contextMax"), values.getInt("context")))
                    .put("maxTokens", numeric("integer", 1, limits.optInt("outputGuardMax", limits.getInt("maxTokensMax")), values.getInt("maxTokens")))
                    .put("threads", numeric("integer", 1, limits.getInt("threadsMax"), values.getInt("threads")))
                    .put("temperature", numeric("number", 0, 2, values.getDouble("temperature")))
                    .put("reasoning", new JSONObject().put("type", "enum").put("values", new JSONArray().put("off").put("auto").put("on")).put("default", values.getString("reasoning")));
            JSONObject schema = new JSONObject().put("version", 1).put("fields", fields), inputs = new JSONObject().put("text.generate", InputSpec.promptOnly().json());
            JSONObject model = base(id, record.getString("name"), "llama_text", bound.isEmpty() ? id : bound, "legacy_gguf", "cpu", new JSONArray().put("text"), inputs, schema, values,
                    ApiCatalogue.hash(new JSONObject(record.toString()).put("config", JSONObject.NULL).put("download", JSONObject.NULL)));
            JSONObject uncensored = record.optJSONObject("uncensored"); if (uncensored != null) model.put("uncensored", uncensored);
            if(app.capabilities!=null)model.getJSONObject("x_lma").put("native_capabilities",app.capabilities.describe(record));
            model.getJSONObject("x_lma").getJSONObject("tags").put("foundation", new JSONArray().put("engine:llama_text").put("pipeline:llama_text").put("backend:cpu")).put("format", new JSONArray().put("gguf"));
            if (uncensored != null && !uncensored.optString("status", "unknown").equals("unknown")) model.getJSONObject("x_lma").getJSONObject("tags").getJSONArray("content").put(new JSONObject().put("label", "Uncensored").put("status", "metadata_hint").put("source", JSONObject.NULL));
            result.put(model);
        }
        if (app.bundles == null || app.localEngines == null) return result;
        JSONArray records = app.bundles.publicationSnapshot();
        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.getJSONObject(i); ModelBundle bundle = app.bundles.bundle(record.getString("id"));
            if (aliases.contains(bundle.id) || AdapterSpec.isAdapter(bundle)) continue;
            try {
                JSONObject inputs = app.localEngines.inputSchemas(bundle);
                if (inputs.length() == 0) continue;
                for (Iterator<String> it = inputs.keys(); it.hasNext();) app.localEngines.require(bundle, it.next());
                JSONObject values = record.getJSONObject("config").getJSONObject("values");
                JSONObject model = base(bundle.id, bundle.name, bundle.engine, bundle.id, bundle.recipeId, values.optString("executionBackend", bundle.backend), new JSONArray(bundle.tasks), inputs, record.getJSONObject("parameterSchema"), values, ApiCatalogue.hash(bundle.json()));
                model.put("model_id", bundle.modelId).put("tags", bundle.tags());
                JSONObject tags = model.getJSONObject("x_lma").getJSONObject("tags");
                tags.put("foundation", new JSONArray().put("engine:" + bundle.engine).put("pipeline:" + bundle.pipeline).put("architecture:" + bundle.architecture).put("backend:" + model.getString("backend")));
                Set<String> formats = new LinkedHashSet<>(); for (ModelBundle.Component component : bundle.components) formats.add(component.format); tags.put("format", new JSONArray(formats));
                JSONObject content = bundle.json().optJSONObject("content");
                if (content != null && !content.optString("classification", "unclassified").equals("unclassified")) tags.getJSONArray("content").put(new JSONObject().put("label", content.getString("classification").toUpperCase(Locale.ROOT)).put("status", content.optString("basis").equals("publisher_card") ? "publisher_checked" : "metadata_hint").put("source", content.has("sourceUrl") ? content.getString("sourceUrl") : JSONObject.NULL));
                result.put(model);
            } catch (Exception incompatible) { /* Invalid records stay in Local management with their own diagnostics. */ }
        }
        return result;
    }
    private static JSONObject numeric(String type, double min, double max, Number value) throws Exception { return new JSONObject().put("type", type).put("minimum", min).put("maximum", max).put("default", value); }
    private static JSONObject base(String id, String name, String engine, String bundle, String recipe, String backend, JSONArray tasks, JSONObject inputs, JSONObject schema, JSONObject values, String revision) throws Exception {
        JSONArray operations = new JSONArray(), mimes = new JSONArray();
        for (Iterator<String> it = inputs.keys(); it.hasNext();) {
            String operation = it.next(); operations.put(operation);
            mimes.put(operation.equals("image.generate") ? "image/png" : operation.equals("video.generate") ? "video/mp4" : operation.equals("mesh.generate") ? "model/gltf-binary" : operation.equals("text.generate") ? "text/plain" : "audio/wav");
        }
        JSONObject publicValues = ApiCatalogue.publicParameters(values), publicSchema = ApiCatalogue.parameterSchema(schema);
        JSONArray backends = new JSONArray().put(backend); JSONObject backendField = publicSchema.getJSONObject("properties").optJSONObject("executionBackend"); if (backendField != null && backendField.has("enum")) backends = backendField.getJSONArray("enum");
        JSONObject publication = new JSONObject().put("source", "user_local_assets").put("eligible", true).put("bundle_id", bundle).put("model_revision", revision).put("recipe_revision", recipe + "@" + LmaApp.VERSION).put("config_revision", 0).put("complete_variant", false);
        JSONObject capabilities = new JSONObject().put("operations", operations).put("tags", new JSONObject().put("task", tasks).put("foundation", new JSONArray()).put("format", new JSONArray()).put("content", new JSONArray()))
                .put("publication", publication).put("input_schemas", inputs).put("parameter_schema", publicSchema).put("saved_parameters", publicValues).put("output_mimes", mimes).put("backend_options", backends)
                .put("streams", new JSONObject().put("text_tokens", operations.toString().contains("text.generate")).put("stage_events", true).put("incremental_pcm", false).put("incremental_images", false))
                .put("evidence", new JSONObject().put("program_verified", false).put("phone_real_output_verified", false).put("quality_accepted", false).put("background_endurance_verified", false).put("record_refs", new JSONArray()));
        return new JSONObject().put("id", id).put("object", "model").put("owned_by", "local").put("name", name).put("task_tags", tasks).put("engine", engine).put("bundle_id", bundle).put("recipe", recipe).put("backend", backend)
                .put("installed", true).put("parameters", new JSONObject().put("values", publicValues).put("schemaVersion", schema.optInt("version", 1))).put("parameter_error", "").put("input_schemas", inputs).put("x_lma", capabilities)
                .put("__config_signature", ApiCatalogue.hash(new JSONObject().put("values", values).put("schema", schema)));
    }
    @Override public JSONObject readiness(JSONObject model) throws Exception {
        String bundle = model.getString("bundle_id");
        boolean loaded = model.getString("engine").equals("llama_text") ? model.getString("id").equals(app.engineModel) && engine != null && engine.ready() : app.bundles != null && app.bundles.inUse(bundle);
        boolean busy = app.generating || app.textRequestBusy || app.jobHost != null && !app.jobHost.activeId().isEmpty();
        JSONObject capacity = app.jobs == null ? new JSONObject() : app.jobs.capacity();
        boolean available = capacity.optInt("pending") < capacity.optInt("pendingLimit", 64) && capacity.optInt("history") < capacity.optInt("historyLimit", 256);
        JSONArray reasons = new JSONArray(); if (busy) reasons.put("execution_slot_busy"); if (!available) reasons.put("queue_capacity_exhausted");
        return new JSONObject().put("loaded", loaded).put("available", available).put("status", busy ? "busy" : loaded ? "loaded" : "unloaded").put("reason_codes", reasons);
    }
}
