package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Collections;

/** Local CPU Sana pipelines; each version owns an independent component contract. */
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
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装 MNN Sana 本地引擎");
        if (bundle.pipeline.equals(SanaSprintSpec.PIPELINE)) SanaSprintSpec.validate(bundle, type); else MnnSpec.validate(bundle, type);
    }
    @Override public InputSpec inputs(ModelBundle bundle, String type) throws Exception {
        if (bundle.pipeline.equals(SanaSprintSpec.PIPELINE)) return new InputSpec(new JSONObject(), "Sana-Sprint：固定 1024×1024，1–4 步；使用内嵌引导。较长提示词按配方截断，不使用负面提示词。").withNegativePrompt(false);
        return bundle.pipeline.equals("sana_edit_mnn_v1") ? MnnSpec.inputs() : InputSpec.promptOnly();
    }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        if (bundle.pipeline.equals(SanaSprintSpec.PIPELINE)) {
            SanaSprintSpec.validate(bundle, request.getString("type"));
            try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) { SanaSprintSpec.metadata(lease.file("encoder_config")); }
            return SanaSprintSpec.prepare(bundle, request);
        }
        try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) { MnnSpec.metadata(lease.file("llm_config"), lease.file("llm_data").length()); }
        return MnnSpec.prepare(bundle, request);
    }
    private static void write(File file, JSONObject data) throws Exception {
        try (FileOutputStream out = new FileOutputStream(file)) { out.write(data.toString().getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(); BundleStore.Lease lease = context.model(); validate(lease.bundle, request.getString("type")); context.check();
        if (lease.bundle.pipeline.equals(SanaSprintSpec.PIPELINE)) return generateSprint(context);
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
    private File generateSprint(Context context) throws Exception {
        JSONObject request = context.request(); BundleStore.Lease lease = context.model();
        if (!context.adapters().isEmpty()) throw new IOException("Sana-Sprint 不支持 LoRA");
        JSONObject plan = SanaSprintSpec.prepare(lease.bundle, request).getJSONObject("diffusionPlan");
        if (!request.has("diffusionPlan") || !DataFiles.canonical(plan).equals(DataFiles.canonical(request.getJSONObject("diffusionPlan")))) throw new IOException("Sana-Sprint 采样快照不匹配，请明确重试任务");
        SanaSprintSpec.metadata(lease.file("encoder_config"));
        JSONObject parameters = DataFiles.copy(plan.getJSONObject("parameters"));
        if (parameters.getInt("seed") == -1) parameters.put("seed", new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        context.execution(new JSONObject().put("effectiveParameters", parameters).put("pipeline", lease.bundle.pipeline).put("samplingProfile", SanaSprintSpec.PROFILE).put("samplingAdjustments", plan.getJSONArray("adjustments")));
        EngineWorkspace workspace = new EngineWorkspace(new File(app.getFilesDir(), "engine-work"), context::check); final Process[] child = {null};
        try {
            for (ModelBundle.Component component : lease.bundle.components) workspace.link("sprint", SanaSprintSpec.filename(component.role), lease.file(component.role));
            String prompt = SanaSprintSpec.normalizedPrompt(request.getJSONObject("input").getString("prompt"));
            if (prompt.isEmpty()) throw new IOException("请输入非空提示词");
            File output = context.output("png"); JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", "image.generate").put("pipeline", SanaSprintSpec.PIPELINE)
                .put("input", new JSONObject().put("prompt", prompt).put("negativePrompt", "")).put("parameters", parameters)
                .put("workspace", new File(workspace.directory(), "sprint").getPath()).put("output", output.getPath());
            NativeWorker.run(app, binary, context, command, output, Collections.emptyMap(), builder -> { Process process = launcher.start(builder); child[0] = process; return process; });
            return output;
        } finally { workspace.closeAfter(child[0]); }
    }
}
