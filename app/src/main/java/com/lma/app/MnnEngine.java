package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Collections;

/** Real CPU Qwen3 encoder -> matched Sana diffusion -> local PNG worker. */
public final class MnnEngine implements LocalEngine {
    private final LmaApp app;
    private final File binary;
    private final JSONObject build;
    private final NativeWorker.Launcher launcher;
    public MnnEngine(LmaApp app, File binary, JSONObject build) { this(app, binary, build, ProcessBuilder::start); }
    MnnEngine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); this.launcher = launcher; }
    @Override public String id() { return "mnn_diffusion"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装 MNN Sana 本地引擎"); MnnSpec.validate(bundle, type);
    }
    @Override public InputSpec inputs(ModelBundle bundle, String type) throws Exception { return bundle.pipeline.equals("sana_edit_mnn_v1") ? MnnSpec.inputs() : InputSpec.promptOnly(); }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) { MnnSpec.metadata(lease.file("llm_config"), lease.file("llm_data").length()); }
        return MnnSpec.prepare(bundle, request);
    }
    private static void write(File file, JSONObject data) throws Exception {
        try (FileOutputStream out = new FileOutputStream(file)) { out.write(data.toString().getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(); BundleStore.Lease lease = context.model(); validate(lease.bundle, request.getString("type")); context.check();
        if (!context.adapters().isEmpty()) throw new IOException("当前 Sana 配方不支持 LoRA");
        JSONObject plan = MnnSpec.prepare(lease.bundle, request).getJSONObject("diffusionPlan");
        if (!request.has("diffusionPlan") || !DataFiles.canonical(plan).equals(DataFiles.canonical(request.getJSONObject("diffusionPlan")))) throw new IOException("Sana 采样快照不匹配，请明确重试任务");
        JSONObject parameters = DataFiles.copy(plan.getJSONObject("parameters"));
        if (parameters.getLong("seed") == -1) parameters.put("seed", new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        JSONObject metadata = MnnSpec.metadata(lease.file("llm_config"), lease.file("llm_data").length());
        context.execution(new JSONObject().put("effectiveParameters", parameters).put("pipeline", lease.bundle.pipeline).put("samplingProfile", "sana_edit_mnn").put("samplingAdjustments", plan.getJSONArray("adjustments")));
        EngineWorkspace workspace = new EngineWorkspace(new File(app.getFilesDir(), "engine-work"), context::check); final Process[] child = {null};
        try {
            for (ModelBundle.Component component : lease.bundle.components) if (!component.role.equals("llm_config")) workspace.link(MnnSpec.group(component.role), MnnSpec.filename(component.role), lease.file(component.role));
            File llm = new File(workspace.directory(), "llm"); write(new File(llm, "llm_config.json"), metadata); write(new File(llm, "config.json"), MnnSpec.runtimeConfig(parameters, workspace.directory()));
            File image = context.input("source_image");
            if (!image.isFile() || image.length() < 8 || image.length() > 16L * 1024 * 1024) throw new IOException("请选择已验证且不超过 16 MiB 的本地 PNG / JPEG");
            File output = context.output("png"); JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", "image.generate").put("pipeline", lease.bundle.pipeline)
                .put("input", new JSONObject().put("prompt", MnnSpec.EDIT_PROMPT).put("negativePrompt", "").put("imagePath", image.getCanonicalPath())).put("parameters", parameters).put("workspace", workspace.directory().getPath()).put("output", output.getPath());
            NativeWorker.run(app, binary, context, command, output, Collections.emptyMap(), builder -> { Process process = launcher.start(builder); child[0] = process; return process; });
            return output;
        } finally { workspace.closeAfter(child[0]); }
    }
}
