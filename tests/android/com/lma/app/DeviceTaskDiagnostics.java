package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Bundle;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Explicit physical diagnostics: tiny owned files and --info/--devices only; never model inference. */
public final class DeviceTaskDiagnostics extends Instrumentation {
    private interface Action { void run() throws Exception; }
    private JSONObject attempt(Action action) throws Exception {
        try { action.run(); return new JSONObject().put("success", true); }
        catch (Exception error) {
            JSONObject value = new JSONObject().put("success", false).put("type", error.getClass().getName()).put("message", String.valueOf(error.getMessage()));
            if (error instanceof FileSystemException) value.put("reason", String.valueOf(((FileSystemException)error).getReason()));
            Throwable cause = error.getCause(); if (cause != null) value.put("cause", cause.toString());
            return value;
        }
    }
    private JSONObject worker(LmaApp app, String binary, String option) throws Exception {
        ProcessBuilder builder = new ProcessBuilder(new File(app.getApplicationInfo().nativeLibraryDir, binary).getPath(), option).directory(app.getFilesDir()).redirectErrorStream(true);
        builder.environment().put("LD_LIBRARY_PATH", app.getApplicationInfo().nativeLibraryDir);
        Process child = builder.start(); ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        Thread reader = new Thread(() -> { try (InputStream input = child.getInputStream()) { byte[] buffer = new byte[2048]; int n; while ((n = input.read(buffer)) != -1) synchronized(bytes) { if (bytes.size() + n <= 32768) bytes.write(buffer, 0, n); } } catch (IOException ignored) {} });
        reader.start(); boolean ended = child.waitFor(25, TimeUnit.SECONDS);
        if (!ended) { child.destroyForcibly(); child.waitFor(3, TimeUnit.SECONDS); }
        reader.join(3000); String text; synchronized(bytes) { text = bytes.toString("UTF-8"); }
        return new JSONObject().put("option", option).put("ended", ended).put("exit", child.isAlive() ? -999 : child.exitValue()).put("output", text);
    }
    @Override public void onCreate(Bundle args) { super.onCreate(args); start(); }
    @Override public void onStart() {
        JSONObject result = new JSONObject(); File folder = null;
        try {
            startActivitySync(new android.content.Intent(getTargetContext(), MainActivity.class).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK));
            LmaApp app = (LmaApp)getTargetContext().getApplicationContext();
            if (app.jobs == null) throw new IllegalStateException("Application foundation unavailable: " + app.bundleStoreError);
            if (app.generating || app.textRequestBusy || app.jobs.capacity().getInt("pending") != 0) throw new IllegalStateException("Diagnostic requires no active tasks");
            result.put("version", LmaApp.VERSION).put("physicalDevice", true).put("modelInference", false).put("completeWeightsDownloaded", false);
            folder = new File(app.getFilesDir(), "task-diagnostic-" + UUID.randomUUID());
            if (!folder.mkdir()) throw new IOException("Cannot create diagnostic directory");
            final File original = new File(folder, "source");
            try (FileOutputStream out = new FileOutputStream(original)) { out.write(new byte[]{1,2,3,4}); }
            final File root = folder;
            result.put("nioHardlink", attempt(() -> Files.createLink(new File(root,"nio-hard").toPath(), original.toPath())));
            result.put("osHardlink", attempt(() -> android.system.Os.link(original.getPath(), new File(root,"os-hard").getPath())));
            result.put("nioSymlink", attempt(() -> Files.createSymbolicLink(new File(root,"nio-soft").toPath(), original.toPath())));
            result.put("osSymlink", attempt(() -> android.system.Os.symlink(original.getPath(), new File(root,"os-soft").getPath())));
            result.put("workspace", attempt(() -> { try (EngineWorkspace work = new EngineWorkspace(new File(root,"work"), () -> {})) { File staged = work.link("models", "fixture.gguf", original); if (staged.length() != 4) throw new IOException("Staged bytes differ"); } }));
            JSONArray models = new JSONArray();
            for (String id : new String[]{"trellis2_pbr512_cpu_v1", "pixal3d_geometry512_cpu_v1", "wan21_13b_q4_vulkan_catalogue_v1"}) {
                ModelBundle bundle = app.bundles.bundle(id); JSONArray files = new JSONArray();
                for (ModelBundle.Component c : bundle.components) {
                    File file = app.bundles.object(c.objectId);
                    files.put(new JSONObject().put("role", c.role).put("present", file.isFile()).put("bytesMatch", file.length() == c.bytes).put("receiptValid", app.bundles.hasObject(c)));
                }
                models.put(new JSONObject().put("id", id).put("components", files));
            }
            result.put("models", models).put("wanInfo", worker(app, "liblma-wan-vulkan.so", "--info")).put("wanDevices", worker(app, "liblma-wan-vulkan.so", "--devices"));
            JSONObject selection = app.bundles.bundle("wan21_13b_q4_vulkan_catalogue_v1").parameters().normalize(new JSONObject(), new JSONObject()).getJSONObject("values");
            JSONObject request = new JSONObject().put("bundleId", "wan21_13b_q4_vulkan_catalogue_v1").put("type", "video.generate").put("input", new JSONObject().put("prompt", "bounded capability diagnostic")).put("parameters", selection).put("allowUnmeasured", true);
            int before = app.jobs.capacity().getInt("history");
            JSONObject report = LocalJobs.preflight(app, request);
            result.put("wanPreflight", new JSONObject().put("canEnqueue", report.getBoolean("canEnqueue")).put("issues", report.getJSONArray("issues")).put("historyUnchanged", before == app.jobs.capacity().getInt("history")));
            result.put("status", "passed");
        } catch (Throwable error) { try { result.put("status", "failed").put("error", error.toString()); } catch (Exception ignored) {} }
        finally {
            if (folder != null) {
                try { File work = new File(folder,"work"); if (work.isDirectory()) { EngineWorkspace.recover(work); work.delete(); } } catch (IOException ignored) { }
                File[] files = folder.listFiles(); if (files != null) for (File file : files) if (!file.isDirectory() || Files.isSymbolicLink(file.toPath())) file.delete(); folder.delete();
            }
        }
        Bundle output = new Bundle(); output.putString("lma_task_diagnostics", result.toString()); finish(Activity.RESULT_OK, output);
    }
}
