package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Actual sd.cpp worker binding; native binaries are never supplied by a model bundle. */
public final class SdEngine implements LocalEngine {
    private final LmaApp app;
    private final File binary;
    private final JSONObject build;
    private final NativeWorker.Launcher launcher;
    public SdEngine(LmaApp app, File binary, JSONObject build) { this(app, binary, build, ProcessBuilder::start); }
    SdEngine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); this.launcher = launcher; }
    @Override public String id() { return "sd_cpp"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装扩散运行引擎");
        SdSpec.validate(bundle, type);
    }
    @Override public JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        try (BundleStore.Selection selected = app.bundles.acquireAll(ModelSelection.ids(request))) {
            List<ModelBundle> adapters = new ArrayList<>(); for (int i = 1; i < selected.models.size(); i++) adapters.add(selected.models.get(i).bundle);
            return SdSpec.prepare(bundle, adapters, request);
        }
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(), components = new JSONObject(); BundleStore.Lease lease = context.model();
        validate(lease.bundle, request.getString("type")); context.check();
        boolean video = request.getString("type").equals("video.generate"); File generated = context.output(video ? "rgb" : "png");
        List<ModelBundle> adapters = new ArrayList<>(); for (BundleStore.Lease adapter : context.adapters()) adapters.add(adapter.bundle);
        JSONObject planned = SdSpec.prepare(lease.bundle, adapters, request).getJSONObject("diffusionPlan");
        if (!request.has("diffusionPlan") || !DataFiles.canonical(planned).equals(DataFiles.canonical(request.getJSONObject("diffusionPlan")))) throw new IOException("扩散采样快照不匹配，请明确重试任务");
        JSONObject parameters = DataFiles.copy(planned.getJSONObject("parameters"));
        if (parameters.optLong("seed", -1) == -1) parameters.put("seed", new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        context.execution(new JSONObject().put("effectiveParameters", parameters).put("pipeline", lease.bundle.pipeline).put("samplingProfile", planned.getString("profile")).put("samplingAdjustments", planned.getJSONArray("adjustments")));
        for (ModelBundle.Component c : lease.bundle.components) components.put(c.role, lease.file(c.role).getPath());
        JSONObject condition = LcmCondition.descriptor(lease.bundle);
        if (condition != null) condition = LcmCondition.verify(lease.bundle, lease.file(LcmCondition.ROLE));
        JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", request.getString("type")).put("input", request.getJSONObject("input"))
                .put("parameters", parameters).put("pipeline", lease.bundle.pipeline).put("architecture", lease.bundle.architecture).put("samplingProfile", planned.getString("profile"))
                .put("components", components).put("output", generated.getPath()).put("loras", ModelSelection.nativeLoras(lease, context.adapters(), request));
        if (condition != null) command.put("conditionBias", condition);
        Map<String, String> environment = new HashMap<>();
        String[][] vocab = {{"clip_merges", "CLIP_MERGES"}, {"qwen_merges", "QWEN_MERGES"}, {"mistral_merges", "MISTRAL_MERGES"}, {"mistral_vocab", "MISTRAL_JSON"}, {"t5_tokenizer", "T5_JSON"}, {"umt5_tokenizer", "UMT5_JSON"}, {"gemma_merges", "GEMMA_MERGES"}, {"gemma_vocab", "GEMMA_JSON"}};
        for (String[] item : vocab) if (components.has(item[0])) environment.put("LMA_VOCAB_" + item[1], components.getString(item[0]));
        NativeWorker.run(app, binary, context, command, generated, environment, launcher);
        if (video) {
            context.progress("encoding", null); File encoded = context.output("mp4");
            VideoEncoder.encode(generated, encoded, () -> { try { context.check(); } catch (Exception error) { throw new IOException(error); } });
            return encoded;
        }
        return generated;
    }
}
