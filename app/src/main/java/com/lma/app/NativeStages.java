package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Owned, sequential signed-App CLI stages. Neither models nor API requests select executables. */
final class NativeStages {
    private NativeStages() {}
    interface Receipt { boolean matches(JSONObject value) throws Exception; }
    static JSONObject run(LmaApp app, File binary, LocalEngine.Context context, List<String> arguments,
                          File output, String stage, Receipt receipt, NativeWorker.Launcher launcher) throws Exception {
        context.check();
        if (!binary.isFile() || !binary.canExecute() || output.exists()) throw new IOException("本地阶段引擎或新输出路径不可用");
        List<String> command = new ArrayList<>(); command.add(binary.getPath()); command.addAll(arguments);
        Process process = null; JSONObject result = null; String failure = ""; long last = 0; int lines = 0, bytes = 0;
        try {
            ProcessBuilder builder = new ProcessBuilder(command).directory(app.getFilesDir()).redirectErrorStream(true);
            builder.environment().put("LD_LIBRARY_PATH", binary.getParent());
            synchronized (app.nativeProcessLock) {
                context.check();
                if (app.nativeProcess != null && app.nativeProcess.isAlive()) throw new IOException("另一个本地引擎仍在运行");
                process = launcher.start(builder); app.nativeProcess = process; context.process(process);
            }
            try (InputStream stream = new BufferedInputStream(process.getInputStream())) {
                String line;
                while ((line = line(stream)) != null) {
                    context.check(); bytes += line.length();
                    if (++lines > 8192 || bytes > 8 * 1024 * 1024) throw new IOException("本地阶段状态输出超出限制");
                    JSONObject value; try { value = new JSONObject(line); } catch (Exception diagnostic) { continue; }
                    if (value.has("error") || value.has("ok") && !value.getBoolean("ok")) failure = value.optString("error", "本地阶段执行失败");
                    else if (receipt.matches(value)) {
                        if (result != null || !failure.isEmpty()) throw new IOException("本地阶段重复或迟到的完成记录");
                        result = value;
                    } else if (System.nanoTime() - last > 500_000_000L) {
                        Double fraction = null;
                        if (value.optInt("total") > 0) fraction = (double) value.optInt("done") / value.getInt("total");
                        else if (value.optString("event").equals("step_end")) fraction = value.optInt("step") / 8.0;
                        if (fraction != null && Double.isFinite(fraction)) context.progress(stage, Math.max(0, Math.min(1, fraction)));
                        last = System.nanoTime();
                    }
                }
            }
            context.check();
            if (!process.waitFor(10, TimeUnit.SECONDS) || process.exitValue() != 0 || result == null || !failure.isEmpty() || !output.isFile() || output.length() == 0)
                throw new IOException(failure.isEmpty() ? "本地阶段未完整完成：" + stage : failure);
            return DataFiles.copy(result);
        } finally {
            if (process != null) try { ProcessControl.stop(process); }
            finally { synchronized (app.nativeProcessLock) { if (app.nativeProcess == process && !process.isAlive()) app.nativeProcess = null; } }
        }
    }
    private static String line(InputStream stream) throws IOException {
        ByteArrayOutputStream value = new ByteArrayOutputStream(); int b;
        while ((b = stream.read()) != -1) { if (b == '\n') break; if (value.size() >= 65536) throw new IOException("本地阶段状态行过长"); value.write(b); }
        return b == -1 && value.size() == 0 ? null : new String(value.toByteArray(), StandardCharsets.UTF_8);
    }
}
