package com.lma.app;

import com.lma.app.core.DataFiles;
import com.lma.app.core.AudioPcm;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Shared ownership and private-file protocol for actual signed-App native workers. */
final class NativeWorker {
    private NativeWorker() {}
    interface Launcher { Process start(ProcessBuilder builder) throws IOException; }
    /** Drain stderr independently: native libraries must never corrupt JSON event framing. */
    private static final class DiagnosticDrain extends Thread {
        private final InputStream stream;
        private volatile String code = "";
        DiagnosticDrain(InputStream stream) { super("LMA-native-stderr"); this.stream = stream; setDaemon(true); start(); }
        @Override public void run() {
            try (InputStream in = stream) {
                byte[] buffer = new byte[4096]; String tail = ""; int count;
                while ((count = in.read(buffer)) != -1) {
                    String part = tail + new String(buffer, 0, count, StandardCharsets.UTF_8);
                    if (part.contains("no voxels produced")) code = "empty_structure";
                    else if (part.contains("std::bad_alloc")) code = "allocation_failed";
                    else if (part.contains("checkpoint has no cross_attn") || part.contains("these are Pixal3D weights")) code = "model_family_mismatch";
                    else if (part.contains("Vulkan 1.2 required")) code = "vulkan_1_2_required";
                    else if (code.isEmpty() && part.contains("CANNOT LINK EXECUTABLE")) code = "native_loader_error";
                    else if (code.isEmpty() && (part.toLowerCase(Locale.ROOT).contains("out of memory") || part.contains("failed to allocate"))) code = "allocation_failed";
                    tail = part.substring(Math.max(0, part.length() - 128));
                }
            } catch (IOException ignored) { }
        }
        void finish() { try { join(3000); } catch (InterruptedException stopped) { Thread.currentThread().interrupt(); } }
    }
    static void requireVulkan(LmaApp app, File binary, Launcher launcher) throws Exception {
        ProcessBuilder builder = new ProcessBuilder(binary.getPath(), "--devices").directory(app.getFilesDir()).redirectErrorStream(false);
        builder.environment().put("LD_LIBRARY_PATH", binary.getParent());
        Process process = launcher.start(builder); DiagnosticDrain errors = new DiagnosticDrain(process.getErrorStream());
        ByteArrayOutputStream stdout = new ByteArrayOutputStream();
        Thread reader = new Thread(() -> { try (InputStream in = process.getInputStream()) { byte[] b = new byte[2048]; int n; while ((n = in.read(b)) != -1) synchronized (stdout) { if (stdout.size() + n <= 65536) stdout.write(b, 0, n); } } catch (IOException ignored) { } }, "LMA-device-query");
        reader.setDaemon(true); reader.start();
        try {
            if (!process.waitFor(15, TimeUnit.SECONDS)) throw new IOException("GPU 能力检查超时；未提交生成任务，请稍后重新打开 App 检查");
            reader.join(3000); errors.finish(); boolean available = false;
            synchronized (stdout) {
                for (String line : stdout.toString("UTF-8").split("\\r?\\n")) try {
                    JSONObject item = new JSONObject(line);
                    available |= java.util.regex.Pattern.compile("(?im)^vulkan0\\t").matcher(item.optString("devices")).find();
                } catch (Exception ignored) { }
            }
            if (process.exitValue() != 0 || !available) throw new IOException(errors.code.equals("vulkan_1_2_required")
                ? "当前手机未提供此引擎要求的 Vulkan 1.2 GPU；请在模型 → 本地 → 该模型参数中将运行后端选择为 cpu，再提交任务。现有权重可直接复用，无需重新下载。"
                : "当前签名引擎未发现可用 Vulkan GPU；请在本地模型参数中明确选择 cpu 后重试。未自动切换后端或下载模型。");
        } finally {
            com.lma.app.core.ProcessControl.stop(process); reader.join(3000); errors.finish();
        }
    }
    static void run(LmaApp app, File binary, LocalEngine.Context context, JSONObject command, File output, Map<String, String> environment) throws Exception {
        run(app, binary, context, command, output, environment, ProcessBuilder::start);
    }
    static void run(LmaApp app, File binary, LocalEngine.Context context, JSONObject command, File output, Map<String, String> environment, Launcher launcher) throws Exception {
        run(app, binary, context, command, output, environment, new JSONObject(), launcher);
    }
    static void run(LmaApp app, File binary, LocalEngine.Context context, JSONObject command, File output, Map<String, String> environment, JSONObject initialExecution, Launcher launcher) throws Exception {
        File input = context.output("json"); Process process = null; DiagnosticDrain diagnostics = null;
        try {
            AudioPcm.Sequence audio = null;
            if (command.has("audioStream")) {
                if (!context.audioStreaming()) throw new IOException("This task has no audio stream consumer");
                AudioPcm.Format format = new AudioPcm.Format(command.getJSONObject("audioStream"));
                audio = new AudioPcm.Sequence(format); context.check(); context.audioStart(format);
            }
            try (FileOutputStream file = new FileOutputStream(input)) { file.write(command.toString().getBytes(StandardCharsets.UTF_8)); file.getFD().sync(); }
            ProcessBuilder builder = new ProcessBuilder(binary.getPath(), input.getPath()).directory(app.getFilesDir()).redirectErrorStream(false);
            builder.environment().put("LD_LIBRARY_PATH", binary.getParent()); builder.environment().putAll(environment);
            synchronized (app.nativeProcessLock) {
                context.check();
                if (app.nativeProcess != null && app.nativeProcess.isAlive()) throw new IOException("另一个本地引擎仍在运行，请先停止它");
                process = launcher.start(builder); app.nativeProcess = process; context.process(process);
            }
            diagnostics = new DiagnosticDrain(process.getErrorStream());
            boolean complete = false; String failure = ""; long last = 0;
            String lastProgressStage = ""; int lastProgressSteps = -1; double lastProgressFraction = Double.NaN;
            JSONObject execution = DataFiles.copy(initialExecution);
            try (InputStream stream = new BufferedInputStream(process.getInputStream())) {
                String line;
                while ((line = line(stream)) != null) {
                    context.check(); JSONObject event;
                    try { event = new JSONObject(line); } catch (Exception ignored) { continue; }
                    String kind = event.optString("event");
                    if (kind.equals("error")) failure = event.optString("message", "本地引擎执行失败");
                    else if (kind.equals("audio_chunk")) {
                        if (audio == null || complete || !failure.isEmpty()) throw new IOException("Unexpected audio chunk from this worker");
                        context.audioChunk(audio.chunk(event));
                    } else if (kind.equals("audio_end")) {
                        if (audio == null || complete || !failure.isEmpty()) throw new IOException("Unexpected audio end from this worker");
                        audio.end(event);
                    }
                    else if (kind.equals("complete")) {
                        if (!event.getString("output").equals(output.getPath()) || complete) throw new IOException("引擎输出记录与任务不一致");
                        complete = true;
                    } else if (kind.equals("execution")) {
                        JSONObject details = event.getJSONObject("details");
                        for (Iterator<String> keys = details.keys(); keys.hasNext();) { String key = keys.next(); execution.put(key, details.get(key)); }
                        context.execution(DataFiles.copy(execution));
                    } else if (kind.equals("stage")) {
                        lastProgressStage = ""; lastProgressSteps = -1; lastProgressFraction = Double.NaN;
                        context.progress(event.optString("stage", "generating"), null);
                    }
                    else if (kind.equals("progress")) {
                        int steps = event.optInt("steps", -1); double value = event.optDouble("fraction", Double.NaN);
                        if (!Double.isFinite(value)) value = steps > 0 ? (double) event.optInt("step") / steps : Double.NaN;
                        if (Double.isFinite(value)) value = Math.max(0, Math.min(1, value));
                        String stage = event.optString("stage", "sampling"); long now = System.nanoTime();
                        // Stage changes, the first completed step and completion must survive throttling.
                        if (!stage.equals(lastProgressStage) || steps != lastProgressSteps
                                || (value == 0 && lastProgressFraction > 0) || (value > 0 && !(lastProgressFraction > 0))
                                || (value >= 1 && !(lastProgressFraction >= 1)) || now - last > 500_000_000L) {
                            last = now; lastProgressStage = stage; lastProgressSteps = steps; lastProgressFraction = value;
                            context.progress(stage, Double.isFinite(value) ? value : null);
                        }
                    }
                }
            }
            context.check();
            boolean ended = process.waitFor(10, TimeUnit.SECONDS); diagnostics.finish();
            int exit = ended ? process.exitValue() : -999;
            execution.put("workerExitCode", exit).put("workerCompleteEvent", complete).put("workerDiagnosticCode", diagnostics.code);
            context.execution(DataFiles.copy(execution));
            if (!ended || exit != 0 || !complete || !failure.isEmpty() || !output.isFile() || output.length() == 0) {
                if (diagnostics.code.equals("empty_structure")) failure = "3D 稀疏结构为空，尚未生成网格；请提高采样步数（建议 12 步）、使用模型推荐引导强度并重试，或更换种子与清晰主体图片";
                else if (diagnostics.code.equals("allocation_failed")) failure = "本机引擎内存分配失败；请关闭其他应用、降低模型支持的分辨率或选择更轻量的模型后重试";
                else if (diagnostics.code.equals("model_family_mismatch")) failure = "3D 权重与所选模型架构不匹配；请在本地模型中重新核对组件及配方";
                else if (failure.isEmpty()) failure = diagnostics.code.equals("vulkan_1_2_required") ? "当前手机未提供此引擎要求的 Vulkan 1.2 GPU；请使用兼容设备或明确选择 CPU 配方"
                    : "本地引擎未完成输出（退出码 " + exit + "，诊断 " + (diagnostics.code.isEmpty() ? "无结构化错误" : diagnostics.code) + "）；可在任务详情查看退出信息";
                throw new IOException(failure);
            }
            if (audio != null) { context.check(); audio.verify(output); context.check(); }
        } finally {
            if (process != null) {
                process.destroy();
                try { if (!process.waitFor(3, TimeUnit.SECONDS)) { process.destroyForcibly(); process.waitFor(3, TimeUnit.SECONDS); } }
                finally { synchronized (app.nativeProcessLock) { if (app.nativeProcess == process && !process.isAlive()) app.nativeProcess = null; } }
            }
            if (diagnostics != null) diagnostics.finish();
            input.delete();
        }
    }
    private static String line(InputStream stream) throws IOException {
        ByteArrayOutputStream text = new ByteArrayOutputStream(); int b;
        while ((b = stream.read()) != -1) { if (b == '\n') break; if (text.size() >= 65536) throw new IOException("引擎状态行过长"); text.write(b); }
        return b == -1 && text.size() == 0 ? null : new String(text.toByteArray(), StandardCharsets.UTF_8);
    }
}
