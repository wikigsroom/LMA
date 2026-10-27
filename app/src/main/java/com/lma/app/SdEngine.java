package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

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
        boolean video = request.getString("type").equals("video.generate"); File generated = context.output(video ? "rgb" : "png"), input = context.output("json");
        JSONObject parameters = DataFiles.copy(request.getJSONObject("parameters"));
        if (parameters.optLong("seed", -1) == -1) parameters.put("seed", new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        context.execution(new JSONObject().put("effectiveParameters", parameters).put("pipeline", lease.bundle.pipeline));
        for (ModelBundle.Component c : lease.bundle.components) components.put(c.role, lease.file(c.role).getPath());
        JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", request.getString("type")).put("input", request.getJSONObject("input"))
                .put("parameters", parameters).put("components", components).put("output", generated.getPath());
        try (FileOutputStream out = new FileOutputStream(input)) { out.write(command.toString().getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
        Process process = null;
        try {
            ProcessBuilder builder = new ProcessBuilder(binary.getPath(), input.getPath()).directory(app.getFilesDir()).redirectErrorStream(true);
            builder.environment().put("LD_LIBRARY_PATH", binary.getParent());
            String[][] vocab = {{"clip_merges", "CLIP_MERGES"}, {"qwen_merges", "QWEN_MERGES"}, {"mistral_merges", "MISTRAL_MERGES"}, {"mistral_vocab", "MISTRAL_JSON"}, {"t5_tokenizer", "T5_JSON"}, {"umt5_tokenizer", "UMT5_JSON"}, {"gemma_merges", "GEMMA_MERGES"}, {"gemma_vocab", "GEMMA_JSON"}};
            for (String[] item : vocab) if (components.has(item[0])) builder.environment().put("LMA_VOCAB_" + item[1], components.getString(item[0]));
            synchronized (app.nativeProcessLock) {
                context.check(); if (app.nativeProcess != null && app.nativeProcess.isAlive()) throw new IOException("另一个本地引擎仍在运行，请先停止它");
                process = builder.start(); app.nativeProcess = process; context.process(process);
            }
            boolean complete = false; String errorMessage = ""; long last = 0;
            try (BufferedInputStream stream = new BufferedInputStream(process.getInputStream())) {
                String line;
                while ((line = line(stream)) != null) {
                    context.check(); JSONObject event;
                    try { event = new JSONObject(line); } catch (Exception ignored) { continue; }
                    String kind = event.optString("event");
                    if (kind.equals("error")) errorMessage = event.optString("message", "本地扩散引擎运行失败");
                    else if (kind.equals("complete")) { if (!event.getString("output").equals(generated.getPath())) throw new IOException("引擎输出路径与任务不一致"); complete = true; }
                    else if (kind.equals("stage")) context.progress(event.optString("stage", "generating"), null);
                    else if (kind.equals("progress") && System.nanoTime() - last > 500_000_000L) {
                        last = System.nanoTime(); int steps = event.optInt("steps"), step = event.optInt("step");
                        context.progress("sampling", steps > 0 ? Math.max(0, Math.min(1, (double) step / steps)) : null);
                    }
                }
            }
            context.check();
            if (!process.waitFor(10, TimeUnit.SECONDS) || process.exitValue() != 0 || !complete || !generated.isFile()) throw new IOException(errorMessage.isEmpty() ? "扩散引擎未完成输出；请检查组件、资源和设备兼容性" : errorMessage);
            if (video) { context.progress("encoding", null); File encoded = context.output("mp4"); VideoEncoder.encode(generated, encoded, () -> { try { context.check(); } catch (Exception error) { throw new IOException(error); } }); return encoded; }
            return generated;
        } finally {
            if (process != null) { process.destroy(); if (!process.waitFor(3, TimeUnit.SECONDS)) process.destroyForcibly(); synchronized (app.nativeProcessLock) { if (app.nativeProcess == process) app.nativeProcess = null; } }
            input.delete();
        }
    }
    private static String line(InputStream in) throws IOException {
        ByteArrayOutputStream text = new ByteArrayOutputStream(); int b;
        while ((b = in.read()) != -1) { if (b == '\n') break; if (text.size() > 65536) throw new IOException("引擎状态行过长"); text.write(b); }
        return b == -1 && text.size() == 0 ? null : new String(text.toByteArray(), StandardCharsets.UTF_8);
    }
}
