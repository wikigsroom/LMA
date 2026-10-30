package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.Collections;

/** Actual SentencePiece -> autoregressive ONNX -> audio codec CPU worker on this phone. */
public final class MossNanoEngine implements LocalEngine {
    private final LmaApp app;
    private final File binary;
    private final JSONObject build;
    private final SpeechVoices voices = new SpeechVoices();
    private final NativeWorker.Launcher launcher;
    public MossNanoEngine(LmaApp app, File binary, JSONObject build) { this(app, binary, build, ProcessBuilder::start); }
    MossNanoEngine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); this.launcher = launcher; }
    @Override public String id() { return "moss_nano_ort"; }
    @Override public ParameterSchema schema(ModelBundle bundle) throws Exception {
        ParameterSchema schema = bundle.parameters(); ModelBundle.Component component = bundle.component("manifest");
        if (!app.bundles.hasObject(component)) return schema;
        try { return voices.nano(schema, app.bundles.object(component.sha256)); }
        catch (IOException | org.json.JSONException unavailable) { return SpeechVoices.unavailable(schema); }
    }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装 MOSS Nano 本地语音引擎");
        MossNanoSpec.validate(bundle, type);
    }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        TtsSpec.text(request.getJSONObject("input"));
        try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) {
            JSONObject normalized = MossNanoSpec.parameters(request.getJSONObject("parameters"), MossNanoSpec.voices(MossNanoSpec.readMetadata(lease.file("manifest"))));
            JSONObject result = DataFiles.copy(request); JSONArray adjustments = result.optJSONArray("adjustments");
            if (adjustments == null) adjustments = new JSONArray();
            JSONArray changes = normalized.getJSONArray("adjustments");
            for (int i = 0; i < changes.length(); i++) adjustments.put(changes.getJSONObject(i).put("reason", "actual_voice_count_or_engine_application_guard"));
            return result.put("parameters", normalized.getJSONObject("values")).put("adjustments", adjustments);
        }
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(); BundleStore.Lease lease = context.model();
        validate(lease.bundle, request.getString("type")); context.check(); TtsSpec.text(request.getJSONObject("input"));
        int voices = MossNanoSpec.voices(MossNanoSpec.readMetadata(lease.file("manifest")));
        JSONObject parameters = MossNanoSpec.parameters(request.getJSONObject("parameters"), voices).getJSONObject("values");
        try (EngineWorkspace workspace = new EngineWorkspace(new File(app.getFilesDir(), "engine-work"), context::check)) {
            JSONObject components = new JSONObject();
            for (ModelBundle.Component component : lease.bundle.components) components.put(component.role, workspace.link(MossNanoSpec.group(component.role), MossNanoSpec.filename(component), lease.file(component.role)).getPath());
            File output = context.output("wav");
            JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", "speech.synthesize").put("pipeline", "moss_nano")
                .put("input", request.getJSONObject("input")).put("parameters", parameters).put("components", components).put("workspace", workspace.directory().getPath()).put("output", output.getPath());
            NativeWorker.run(app, binary, context, command, output, Collections.emptyMap(), launcher);
            return output;
        }
    }
}
