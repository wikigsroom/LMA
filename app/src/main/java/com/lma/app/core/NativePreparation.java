package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/** Runs only registered App programs; all request paths come from leased private storage. */
public final class NativePreparation {
    private NativePreparation() {}
    public interface Context {
        void check() throws IOException;
        void progress(String stage, Double fraction) throws Exception;
        Process start(ProcessBuilder builder) throws Exception;
        File graphs(PreparationPlan.Stage stage) throws Exception;
    }
    public static void run(PreparationPlan plan, File source, Map<String,File> programs, PreparedAssets.Session session, Context context) throws Exception {
        context.check();
        for (PreparationPlan.Stage stage : plan.stages) {
            File program = programs.get(stage.module); if (program == null || !program.isFile()) throw new IOException("Preparation program is missing from the App");
            JSONObject request = new JSONObject().put("operation", stage.operation).put("checkpoint", source.getCanonicalPath())
                    .put("expected_source_bytes", plan.sourceBytes).put("expected_source_sha256", plan.sourceSha256)
                    .put("storage_root", session.directory.getCanonicalPath()).put("output_name", stage.id).put("max_output_bytes", plan.reserveBytes);
            if (stage.graphs.length() > 0) request.put("graph_root", context.graphs(stage).getCanonicalPath());
            File command = DataFiles.child(session.directory, "request-" + stage.id + ".json");
            try (FileOutputStream out = new FileOutputStream(command)) { out.write(request.toString().getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
            Process process = null; JSONObject result = null; long last = 0; String failure = "";
            try {
                context.progress("preparing_" + stage.id, 0.0);
                ProcessBuilder builder = new ProcessBuilder(program.getCanonicalPath(), command.getCanonicalPath()).directory(session.directory).redirectErrorStream(true);
                builder.environment().put("LD_LIBRARY_PATH", program.getParentFile().getCanonicalPath());
                context.check(); process = context.start(builder); process.getOutputStream().close();
                try (InputStream stream = new BufferedInputStream(process.getInputStream())) {
                    String line;
                    while ((line = line(stream)) != null) {
                        context.check(); JSONObject event;
                        try { event = new JSONObject(line); } catch (Exception diagnostic) { failure = line.length() > 1000 ? line.substring(0, 1000) : line; continue; }
                        if (event.has("ok")) { result = event; if (!event.optBoolean("ok")) failure = event.optString("error", "Preparation failed"); }
                        else if (event.has("phase") && System.nanoTime() - last > 500_000_000L) {
                            last = System.nanoTime(); double total = event.optDouble("total_bytes", 0), done = event.optDouble("bytes", 0);
                            context.progress("preparing_" + stage.id, total > 0 ? Math.max(0, Math.min(1, done / total)) : null);
                        }
                    }
                }
                context.check();
                if (!process.waitFor(10, TimeUnit.SECONDS) || process.exitValue() != 0 || result == null || !result.optBoolean("ok") || !stage.receiptSchema.equals(result.optString("schema"))) throw new IOException(failure.isEmpty() ? "本机资产准备未完成，源文件保持不变" : failure);
                context.progress("preparing_" + stage.id, 1.0);
            } finally {
                ProcessControl.stop(process);
                if (process != null) { process.getInputStream().close(); process.getErrorStream().close(); process.getOutputStream().close(); }
                if (command.exists() && !command.delete()) throw new IOException("Cannot remove private preparation request");
            }
        }
        context.progress("verifying_prepared_assets", null);
    }
    private static String line(InputStream input) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(); int next;
        while ((next = input.read()) != -1 && next != '\n') { if (bytes.size() >= 1024 * 1024) throw new IOException("Preparation output exceeded its protocol limit"); bytes.write(next); }
        return next == -1 && bytes.size() == 0 ? null : new String(bytes.toByteArray(), StandardCharsets.UTF_8).trim();
    }
}
