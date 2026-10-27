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
    private static final Set<String> PIPELINES = new HashSet<>(Arrays.asList("sd15", "sd21_turbo", "sd15_lcm", "sdxl", "sdxl_lcm", "z_image_turbo", "flux2_klein_4b", "qwen_image_21", "wan21_13b"));
    public SdEngine(LmaApp app, File binary, JSONObject build) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); }
    @Override public String id() { return "sd_cpp"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle bundle, String type) throws Exception {
        if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装扩散运行引擎");
        if (!bundle.engine.equals(id()) || !bundle.backend.equals("cpu") || !PIPELINES.contains(bundle.pipeline)) throw new IOException("当前扩散引擎没有匹配的管线或后端，请选择已适配配方");
        if (!type.equals("image.generate") && !type.equals("video.generate") || type.equals("video.generate") != bundle.pipeline.equals("wan21_13b")) throw new IOException("此配方不支持所选生成任务");
        if (bundle.components.stream().noneMatch(c -> c.role.equals("model") || c.role.equals("diffusion"))) throw new IOException("配方缺少主权重组件");
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request = context.request(), components = new JSONObject(); BundleStore.Lease lease = context.model();
        validate(lease.bundle, request.getString("type")); context.check();
        boolean video = request.getString("type").equals("video.generate"); File generated = context.output(video ? "rgb" : "png");
        JSONObject parameters = DataFiles.copy(request.getJSONObject("parameters"));
        if (parameters.optLong("seed", -1) == -1) parameters.put("seed", new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        context.execution(new JSONObject().put("effectiveParameters", parameters).put("pipeline", lease.bundle.pipeline));
        for (ModelBundle.Component c : lease.bundle.components) components.put(c.role, lease.file(c.role).getPath());
        JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", request.getString("type")).put("input", request.getJSONObject("input"))
                .put("parameters", parameters).put("components", components).put("output", generated.getPath());
        Map<String, String> environment = new HashMap<>();
        String[][] vocab = {{"clip_merges", "CLIP_MERGES"}, {"qwen_merges", "QWEN_MERGES"}, {"mistral_merges", "MISTRAL_MERGES"}, {"mistral_vocab", "MISTRAL_JSON"}, {"t5_tokenizer", "T5_JSON"}, {"umt5_tokenizer", "UMT5_JSON"}, {"gemma_merges", "GEMMA_MERGES"}, {"gemma_vocab", "GEMMA_JSON"}};
        for (String[] item : vocab) if (components.has(item[0])) environment.put("LMA_VOCAB_" + item[1], components.getString(item[0]));
        NativeWorker.run(app, binary, context, command, generated, environment);
        if (video) {
            context.progress("encoding", null); File encoded = context.output("mp4");
            VideoEncoder.encode(generated, encoded, () -> { try { context.check(); } catch (Exception error) { throw new IOException(error); } });
            return encoded;
        }
        return generated;
    }
}
