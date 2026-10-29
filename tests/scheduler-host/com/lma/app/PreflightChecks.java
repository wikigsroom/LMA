package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Actual production resolver and authenticated sockets; no Android/model execution evidence. */
final class PreflightChecks {
    private static int passed;
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); passed++; }
    private static JSONObject copy(JSONObject value) throws Exception { return DataFiles.copy(value); }
    private static JSONObject issue(LmaApp app, JSONObject request, String stage) throws Exception {
        JSONObject result = LocalJobs.preflight(app, request);
        check(!result.getBoolean("canEnqueue") && result.getJSONArray("issues").getJSONObject(0).getString("code").equals(stage), "Preflight blocks at " + stage);
        return result;
    }
    private static Map<String,String> disk(File root) throws Exception {
        Map<String,String> result = new TreeMap<>();
        try (java.util.stream.Stream<Path> paths = Files.walk(root.toPath())) {
            for (Path path : (Iterable<Path>) paths.filter(Files::isRegularFile)::iterator) result.put(root.toPath().relativize(path).toString(), DataFiles.sha256(path.toFile()));
        }
        return result;
    }
    private static JSONObject http(LmaApp app, ApiHost api, String method, JSONObject request, boolean authorized, int status) throws Exception {
        HttpURLConnection client = (HttpURLConnection) new URL("http://127.0.0.1:" + app.prefs.getInt("port", 0) + "/v1/jobs/preflight").openConnection();
        try {
            client.setRequestMethod(method); client.setConnectTimeout(3000); client.setReadTimeout(5000);
            if (authorized) client.setRequestProperty("Authorization", "Bearer " + api.apiKey());
            if (request != null) { client.setDoOutput(true); client.setRequestProperty("Content-Type", "application/json"); try (OutputStream out = client.getOutputStream()) { out.write(request.toString().getBytes(StandardCharsets.UTF_8)); } }
            check(client.getResponseCode() == status, "Actual preflight HTTP status " + status);
            try (InputStream in = status < 400 ? client.getInputStream() : client.getErrorStream()) { return new JSONObject(Store.read(in, 128 * 1024)); }
        } finally { client.disconnect(); }
    }
    static int run(LmaApp app, ApiHost api, JSONObject request) throws Exception {
        int jobs = app.jobs.snapshot().length(); boolean desired = app.prefs.getBoolean("desiredJobs", false);
        Map<String,String> before = disk(app.getFilesDir()); String settings = DataFiles.canonical(app.bundles.settings(request.getString("bundleId")));
        JSONObject oversized = copy(request).put("parameters", new JSONObject().put("steps", 999));
        JSONObject ready = LocalJobs.preflight(app, oversized);
        check(ready.getBoolean("canEnqueue") && ready.getJSONObject("effectiveParameters").getInt("steps") == 4 && ready.getJSONArray("adjustments").length() > 0, "Actual resolver previews clamped effective values");
        check(oversized.getJSONObject("parameters").getInt("steps") == 999, "Resolver does not mutate the client's request");
        check(!ready.getBoolean("deviceValidated") && !ready.getBoolean("modelInferenceTested"), "Readiness never claims device or inference acceptance");
        check(ready.getJSONArray("warnings").getJSONObject(0).getString("code").equals("memory_estimate_unknown"), "Unknown memory estimates remain explicit");
        JSONObject consent = issue(app, copy(request).put("allowUnmeasured", false), "consent");
        check(consent.has("resources") && consent.has("effectiveParameters"), "Consent failure still gives parameter and resource diagnostics");
        JSONObject unknown = copy(request).put("bundleId", "missing_model_fixture"); issue(app, unknown, "models");
        issue(app, copy(request).put("type", "video.generate"), "models");
        JSONObject empty = copy(request); empty.getJSONObject("input").put("prompt", "   "); issue(app, empty, "request");
        JSONObject parameter = copy(request).put("parameters", new JSONObject().put("steps", "wrong")); issue(app, parameter, "parameters");
        JSONObject missingInput = copy(request); missingInput.getJSONObject("input").put("artifacts", new JSONArray().put(new JSONObject().put("role", "reference_image").put("artifactId", "absent_artifact"))); issue(app, missingInput, "inputs");
        JSONObject wrongRole = copy(request); wrongRole.getJSONObject("input").getJSONArray("artifacts").getJSONObject(0).put("role", "unknown_role"); issue(app, wrongRole, "inputs");
        long total = app.memory.values.totalMem, available = app.memory.values.availMem;
        try {
            app.memory.values.totalMem = 400L * 1024 * 1024; issue(app, request, "resources");
            app.memory.values.totalMem = total; app.memory.values.availMem = 64L * 1024 * 1024; app.memory.values.lowMemory = true;
            JSONObject pressure = LocalJobs.preflight(app, request);
            check(pressure.getBoolean("canEnqueue") && pressure.getJSONArray("warnings").getJSONObject(0).getString("code").equals("current_memory_pressure"), "Transient pressure is a queue warning, not a successful execution claim");
        } finally { app.memory.values.totalMem = total; app.memory.values.availMem = available; app.memory.values.lowMemory = false; }
        check(settings.equals(DataFiles.canonical(app.bundles.settings(request.getString("bundleId")))) && before.equals(disk(app.getFilesDir())), "Every preview and failure leaves model defaults and durable stores unchanged");
        JSONArray bundles = app.bundles.snapshot(); boolean leased = false;
        for (int i=0;i<bundles.length();i++) leased |= bundles.getJSONObject(i).optBoolean("inUse");
        check(!leased && app.execution.snapshot().getInt("waitingCount") == 0 && app.execution.snapshot().isNull("active"), "Preflight leaves no model lease or execution slot");
        JSONObject missingManifest = app.bundles.bundle(request.getString("bundleId")).json();
        missingManifest.put("id", "missing_components_fixture").put("modelId", "missing_components_fixture");
        missingManifest.getJSONArray("components").getJSONObject(0).put("sha256", String.join("", Collections.nCopies(64, "0")));
        app.bundles.declare(new ModelBundle(missingManifest));
        Map<String,String> declared = disk(app.getFilesDir());
        JSONObject absent = issue(app, copy(request).put("bundleId", "missing_components_fixture"), "assets");
        check(!absent.getJSONArray("modelAssets").getJSONObject(0).getJSONArray("components").getJSONObject(0).getBoolean("present"), "Missing components have actionable role-level inventory");
        check(!app.bundles.record("missing_components_fixture").has("transfer") && declared.equals(disk(app.getFilesDir())), "Missing assets never cause a transfer, installation or persisted plan");
        JSONObject engineManifest = copy(missingManifest).put("id", "missing_engine_fixture").put("modelId", "missing_engine_fixture").put("engine", "absent_engine"); app.bundles.declare(new ModelBundle(engineManifest));
        issue(app, copy(request).put("bundleId", "missing_engine_fixture"), "engine");
        api.start();
        try {
            check(http(app, api, "POST", request, true, 200).getBoolean("canEnqueue"), "Authenticated production HTTP uses the actual shared resolver");
            check(!http(app, api, "POST", unknown, true, 200).getBoolean("canEnqueue"), "Blocked requests return a readable report without creating a failed job");
            http(app, api, "POST", request, false, 401); http(app, api, "GET", null, true, 405);
        } finally { api.stop(); }
        check(app.jobs.snapshot().length() == jobs && app.prefs.getBoolean("desiredJobs", false) == desired && app.nativeProcess == null, "Direct and HTTP checks never enqueue, launch a model or enable job restoration");
        JobStore original = app.jobs;
        try {
            app.jobs = new JobStore(new File(app.getFilesDir(), "preflight_capacity_fixture"));
            for (int i = 0; i < 64; i++) app.jobs.submit(request, "capacity_" + i);
            Map<String,String> full = disk(app.getFilesDir());
            JSONObject capacity = issue(app, request, "capacity");
            check(capacity.getJSONArray("issues").getJSONObject(0).getString("action").equals("manage_tasks") && capacity.getJSONObject("capacity").getJSONObject("jobs").getInt("pending") == 64, "Full queue produces actionable capacity diagnostics from the actual store");
            check(full.equals(disk(app.getFilesDir())), "Capacity checks remain read-only even when the queue is full");
        } finally { app.jobs = original; }
        return passed;
    }
}
