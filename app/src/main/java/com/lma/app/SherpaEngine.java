package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONObject;
import java.io.*;
import java.util.Collections;

/** Actual offline sherpa C-API worker; all voice/language/model data belongs to the user bundle. */
public final class SherpaEngine implements LocalEngine {
    private final LmaApp app;
    private final File binary;
    private final JSONObject build;
    private final SpeechVoices voices = new SpeechVoices();
    public SherpaEngine(LmaApp app, File binary, JSONObject build) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); }
    @Override public String id() { return "sherpa_tts"; }
    @Override public ParameterSchema schema(ModelBundle bundle) throws Exception {
        ParameterSchema schema = bundle.parameters(); ModelBundle.Component component = bundle.component("model");
        if (!app.bundles.hasObject(component)) return schema;
        try { return voices.onnx(schema, app.bundles.object(component.sha256)); }
        catch (IOException | org.json.JSONException unavailable) { return SpeechVoices.unavailable(schema); }
    }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装本地语音运行引擎");
        TtsSpec.validate(bundle, type);
    }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        TtsSpec.text(request.getJSONObject("input"));
        JSONObject result = DataFiles.copy(request), before = request.getJSONObject("parameters"), values = TtsSpec.parameters(before, bundle.pipeline);
        org.json.JSONArray adjustments = result.optJSONArray("adjustments");
        if (adjustments == null) adjustments = new org.json.JSONArray();
        for (java.util.Iterator<String> keys = values.keys(); keys.hasNext();) {
            String key = keys.next();
            if (before.has(key) && before.getDouble(key) != values.getDouble(key)) adjustments.put(new JSONObject().put("field", key).put("requested", before.get(key)).put("effective", values.get(key)).put("reason", "engine_application_guard"));
        }
        return result.put("parameters", values).put("adjustments", adjustments);
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(); BundleStore.Lease lease = context.model();
        validate(lease.bundle, request.getString("type")); context.check();
        TtsSpec.text(request.getJSONObject("input"));
        JSONObject parameters = TtsSpec.parameters(request.getJSONObject("parameters"), lease.bundle.pipeline), components = new JSONObject();
        for (ModelBundle.Component component : lease.bundle.components) components.put(component.role, lease.file(component.role).getPath());
        File output = context.output("wav");
        JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", "speech.synthesize").put("pipeline", lease.bundle.pipeline)
                .put("input", request.getJSONObject("input")).put("parameters", parameters).put("components", components).put("output", output.getPath());
        NativeWorker.run(app, binary, context, command, output, Collections.emptyMap());
        return output;
    }
}
