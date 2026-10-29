package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.IOException;
import java.util.*;

/** Internal, signed-App preparation recipe. It is never loaded from a user model bundle. */
public final class PreparationPlan {
    public final String id, name, sourceRole, sourceSha256, fingerprint;
    public final long sourceBytes, outputBytes, reserveBytes;
    public final List<Stage> stages;
    private final JSONObject source;
    public static final class Output {
        public final String file, role, sha256; public final long bytes;
        Output(JSONObject value) throws Exception {
            file = EngineWorkspace.filename(value.getString("file")); role = ModelBundle.key(value.getString("role"));
            sha256 = value.getString("sha256"); bytes = value.getLong("bytes");
            if (!Protocol.isSha256(sha256) || bytes < 1 || bytes > 64L * 1024 * 1024 * 1024) throw new IOException("Invalid prepared asset identity");
        }
    }
    public static final class Stage {
        public final String id, module, operation, receipt, receiptSchema;
        public final List<Output> outputs; public final JSONArray graphs;
        Stage(JSONObject value) throws Exception {
            id = ModelBundle.key(value.getString("id")); module = ModelBundle.key(value.getString("module"));
            operation = ModelBundle.key(value.getString("operation")); receipt = EngineWorkspace.filename(value.getString("receipt"));
            receiptSchema = value.getString("receiptSchema"); if (receiptSchema.length() > 120) throw new IOException("Invalid preparation receipt schema");
            JSONArray files = value.getJSONArray("outputs"); if (files.length() < 1 || files.length() > 64) throw new IOException("Invalid preparation output count");
            List<Output> checked = new ArrayList<>(); Set<String> names = new HashSet<>(); names.add(receipt.toLowerCase(Locale.ROOT));
            for (int i = 0; i < files.length(); i++) { Output output = new Output(files.getJSONObject(i)); if (!names.add(output.file.toLowerCase(Locale.ROOT))) throw new IOException("Duplicate preparation filename"); checked.add(output); }
            outputs = Collections.unmodifiableList(checked);
            graphs = new JSONArray(value.optJSONArray("graphs") == null ? "[]" : value.getJSONArray("graphs").toString());
            if (graphs.length() > 32) throw new IOException("Too many architecture graphs");
            names.clear();
            for (int i = 0; i < graphs.length(); i++) {
                JSONObject graph = graphs.getJSONObject(i); String file = EngineWorkspace.filename(graph.getString("file"));
                if (!names.add(file.toLowerCase(Locale.ROOT)) || !Protocol.isSha256(graph.getString("sha256")) || graph.getLong("bytes") < 1 || graph.getLong("bytes") > 4 * 1024 * 1024) throw new IOException("Invalid architecture graph");
            }
        }
    }
    public PreparationPlan(JSONObject value) throws Exception {
        if (!value.getString("schema").equals("lma.asset-preparation/1")) throw new IOException("Unsupported preparation plan");
        id = ModelBundle.key(value.getString("id")); name = value.getString("name");
        if (name.isEmpty() || name.length() > 160) throw new IOException("Invalid preparation name");
        sourceRole = ModelBundle.key(value.getString("sourceRole")); sourceSha256 = value.getString("sourceSha256"); sourceBytes = value.getLong("sourceBytes");
        if (!Protocol.isSha256(sourceSha256) || sourceBytes < 1 || sourceBytes > 128L * 1024 * 1024 * 1024) throw new IOException("Invalid preparation source identity");
        JSONArray list = value.getJSONArray("stages"); if (list.length() < 1 || list.length() > 8) throw new IOException("Invalid preparation stage count");
        List<Stage> checked = new ArrayList<>(); Set<String> names = new HashSet<>(), roles = new HashSet<>(); long total = 0;
        for (int i = 0; i < list.length(); i++) {
            Stage stage = new Stage(list.getJSONObject(i)); if (!names.add(stage.id)) throw new IOException("Duplicate preparation stage");
            for (Output output : stage.outputs) { if (!roles.add(output.role)) throw new IOException("Duplicate prepared component role"); total = Math.addExact(total, output.bytes); }
            checked.add(stage);
        }
        stages = Collections.unmodifiableList(checked); outputBytes = total; reserveBytes = Math.addExact(total, 128L * 1024 * 1024);
        source = DataFiles.copy(value); fingerprint = TaskInput.fingerprint(source);
    }
    public boolean matches(ModelBundle bundle) {
        try { ModelBundle.Component c = bundle.component(sourceRole); return c.bytes == sourceBytes && c.sha256.equals(sourceSha256); }
        catch (IllegalArgumentException absent) { return false; }
    }
    public JSONObject json() { return DataFiles.copy(source); }
    public JSONObject describe() throws Exception {
        return new JSONObject().put("id", id).put("name", name).put("fingerprint", fingerprint).put("sourceRole", sourceRole)
                .put("sourceBytes", sourceBytes).put("outputBytes", outputBytes).put("requiredFreeBytes", reserveBytes)
                .put("stageCount", stages.size()).put("downloads", false).put("generatesMedia", false).put("deviceValidated", false);
    }
}
