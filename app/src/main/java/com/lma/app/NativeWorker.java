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
    static void run(LmaApp app, File binary, LocalEngine.Context context, JSONObject command, File output, Map<String, String> environment) throws Exception {
        run(app, binary, context, command, output, environment, ProcessBuilder::start);
    }
    static void run(LmaApp app, File binary, LocalEngine.Context context, JSONObject command, File output, Map<String, String> environment, Launcher launcher) throws Exception {
        run(app, binary, context, command, output, environment, new JSONObject(), launcher);
    }
    static void run(LmaApp app, File binary, LocalEngine.Context context, JSONObject command, File output, Map<String, String> environment, JSONObject initialExecution, Launcher launcher) throws Exception {
        File input = context.output("json"); Process process = null;
        try {
            AudioPcm.Sequence audio = null;
            if (command.has("audioStream")) {
                if (!context.audioStreaming()) throw new IOException("This task has no audio stream consumer");
                AudioPcm.Format format = new AudioPcm.Format(command.getJSONObject("audioStream"));
                audio = new AudioPcm.Sequence(format); context.check(); context.audioStart(format);
            }
            try (FileOutputStream file = new FileOutputStream(input)) { file.write(command.toString().getBytes(StandardCharsets.UTF_8)); file.getFD().sync(); }
            ProcessBuilder builder = new ProcessBuilder(binary.getPath(), input.getPath()).directory(app.getFilesDir()).redirectErrorStream(true);
            builder.environment().put("LD_LIBRARY_PATH", binary.getParent()); builder.environment().putAll(environment);
            synchronized (app.nativeProcessLock) {
                context.check();
                if (app.nativeProcess != null && app.nativeProcess.isAlive()) throw new IOException("另一个本地引擎仍在运行，请先停止它");
                process = launcher.start(builder); app.nativeProcess = process; context.process(process);
            }
            boolean complete = false; String failure = ""; long last = 0; JSONObject execution = DataFiles.copy(initialExecution);
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
                    } else if (kind.equals("stage")) context.progress(event.optString("stage", "generating"), null);
                    else if (kind.equals("progress") && System.nanoTime() - last > 500_000_000L) {
                        last = System.nanoTime(); double value = event.optDouble("fraction", Double.NaN);
                        if (!Double.isFinite(value)) { int steps = event.optInt("steps"); value = steps > 0 ? (double) event.optInt("step") / steps : Double.NaN; }
                        context.progress(event.optString("stage", "sampling"), Double.isFinite(value) ? Math.max(0, Math.min(1, value)) : null);
                    }
                }
            }
            context.check();
            if (!process.waitFor(10, TimeUnit.SECONDS) || process.exitValue() != 0 || !complete || !failure.isEmpty() || !output.isFile() || output.length() == 0) throw new IOException(failure.isEmpty() ? "本地引擎未完成输出；请检查组件、资源和设备兼容性" : failure);
            if (audio != null) { context.check(); audio.verify(output); context.check(); }
        } finally {
            if (process != null) {
                process.destroy();
                try { if (!process.waitFor(3, TimeUnit.SECONDS)) { process.destroyForcibly(); process.waitFor(3, TimeUnit.SECONDS); } }
                finally { synchronized (app.nativeProcessLock) { if (app.nativeProcess == process && !process.isAlive()) app.nativeProcess = null; } }
            }
            input.delete();
        }
    }
    private static String line(InputStream stream) throws IOException {
        ByteArrayOutputStream text = new ByteArrayOutputStream(); int b;
        while ((b = stream.read()) != -1) { if (b == '\n') break; if (text.size() >= 65536) throw new IOException("引擎状态行过长"); text.write(b); }
        return b == -1 && text.size() == 0 ? null : new String(text.toByteArray(), StandardCharsets.UTF_8);
    }
}
