package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

/** Production stores and HTTP routes; explicit execution/media fixtures, no inference. */
public final class TaskWorkbenchTest {
    private static final List<String> checks = new ArrayList<>();
    private static void check(boolean condition, String name) { if (!condition) throw new AssertionError(name); checks.add(name); }
    private interface Op { void run() throws Exception; }
    private static void reject(Op op, String name) throws Exception { try { op.run(); } catch (IllegalArgumentException | IllegalStateException | IOException | JSONException expected) { checks.add(name); return; } throw new AssertionError(name); }
    private static JSONObject request(String id, String type, String prompt) {
        return new JSONObject().put("bundleId", id).put("type", type).put("input", new JSONObject().put("prompt", prompt)).put("parameters", new JSONObject().put("seed", 42)).put("allowUnmeasured", true);
    }
    private static final class Reply {
        final int code; final JSONObject data;
        Reply(int code, JSONObject data) { this.code = code; this.data = data; }
    }
    private static Reply http(int port, String method, String path, JSONObject payload, String key) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        c.setConnectTimeout(2000); c.setReadTimeout(3000); c.setRequestMethod(method); c.setRequestProperty("Authorization", "Bearer " + key);
        try {
            if (payload != null) { byte[] data = payload.toString().getBytes(StandardCharsets.UTF_8); c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json"); c.setFixedLengthStreamingMode(data.length); try (OutputStream out = c.getOutputStream()) { out.write(data); } }
            int code = c.getResponseCode(); InputStream stream = code >= 400 ? c.getErrorStream() : c.getInputStream();
            ByteArrayOutputStream out = new ByteArrayOutputStream(); if (stream != null) try (InputStream in = stream) { byte[] b = new byte[1024]; int n; while ((n = in.read(b)) != -1) out.write(b, 0, n); }
            return new Reply(code, out.size() == 0 ? new JSONObject() : new JSONObject(new String(out.toByteArray(), StandardCharsets.UTF_8)));
        } finally { c.disconnect(); }
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]), directory = new File(root, "drafts"); TaskDrafts drafts = new TaskDrafts(directory);
        for (String type : Arrays.asList("text.generate", "image.generate", "video.generate", "speech.synthesize", "audio.generate")) {
            JSONObject r = request("model_" + type.split("\\.")[0], type, ""); JSONObject saved = drafts.save(r, 0);
            check(saved.getJSONObject("request").getJSONObject("input").getString("prompt").isEmpty(), type + " accepts an unfinished draft");
            check(!saved.getJSONObject("request").getBoolean("allowUnmeasured") && r.getBoolean("allowUnmeasured"), type + " resets admission choice without mutating its caller");
        }
        JSONObject frozen = request("reuse_model", "image.generate", "<script>字面输入</script>");
        frozen.put("adapters", new JSONArray().put(new JSONObject().put("bundleId", "style_lora").put("scale", .75)));
        frozen.getJSONObject("input").put("artifacts", new JSONArray().put(new JSONObject().put("role", "reference_image").put("artifactId", "artifact_fixture")));
        frozen.put("submissionHash", "f".repeat(64)).put("inputReceipts", new JSONArray().put("stale")).put("resourcePlan", new JSONObject()).put("diffusionPlan", new JSONObject()).put("parameterSchemaVersion", 2).put("unknownFutureReceipt", true);
        JSONObject editable = TaskRequests.editable(frozen);
        check(editable.length() == 6 && !editable.has("submissionHash") && !editable.has("inputReceipts") && !editable.has("unknownFutureReceipt"), "Editable requests allow only user request fields, including future receipt removal");
        check(editable.getJSONArray("adapters").getJSONObject(0).getDouble("scale") == .75 && editable.getJSONObject("input").getJSONArray("artifacts").length() == 1, "LoRA strength and explicit media references survive restore");
        check(!editable.getBoolean("allowUnmeasured") && TaskRequests.replay(frozen).getBoolean("allowUnmeasured"), "Editor reconfirms admission; explicit retry preserves the original choice for revalidation");
        editable.getJSONObject("parameters").put("seed", 1); check(frozen.getJSONObject("parameters").getInt("seed") == 42, "Editing never mutates immutable task provenance");
        JSONObject preparation = new JSONObject().put("type", "model.prepare").put("bundleId", "source_model").put("preparationId", "prepare_v1").put("planFingerprint", "a".repeat(64)).put("preparationSource", new JSONObject());
        check(TaskRequests.replay(preparation).length() == 4, "Preparation retry drops execution metadata while retaining the signed plan");
        reject(() -> TaskRequests.editable(preparation), "Preparation is not presented as a generation form");
        reject(() -> drafts.save(frozen, 0), "Draft write rejects client execution receipts");
        JSONObject first = drafts.save(TaskRequests.editable(frozen), 0); long revision = first.getLong("revision");
        TaskDrafts restarted = new TaskDrafts(directory);
        check(restarted.get("reuse_model").getJSONObject("request").getJSONObject("parameters").getInt("seed") == 42, "Draft survives a new store instance without installed model assets");
        JSONObject updated = restarted.save(request("reuse_model", "image.generate", "updated"), revision);
        reject(() -> restarted.save(request("reuse_model", "image.generate", "stale"), revision), "Concurrent stale save cannot overwrite the newer draft");
        reject(() -> restarted.remove("reuse_model", revision), "Concurrent stale deletion is rejected");
        updated.getJSONObject("request").getJSONObject("input").put("prompt", "mutated");
        check(restarted.get("reuse_model").getJSONObject("request").getJSONObject("input").getString("prompt").equals("updated"), "Returned records are independent copies");
        restarted.remove("reuse_model", updated.getLong("revision")); JSONObject recreated = restarted.save(request("reuse_model", "image.generate", "recreated"), 0);
        check(recreated.getLong("revision") > updated.getLong("revision"), "Delete/recreate cannot reuse an old revision");
        reject(() -> restarted.save(request("reuse_model", "image.generate", "old"), updated.getLong("revision")), "Old editor cannot overwrite a recreated draft");
        reject(() -> TaskDrafts.revision(new JSONObject().put("expectedRevision", .5)), "Fractional revision rejected");
        reject(() -> TaskDrafts.revision(new JSONObject().put("expectedRevision", "0")), "String revision rejected");
        reject(() -> restarted.save(request("escape", "image.generate", "ok").put("input", new JSONObject().put("prompt", "ok").put("path", "C:/outside")), 0), "Drafts cannot add paths or external execution inputs");
        reject(() -> restarted.save(request("../escape", "image.generate", "ok"), 0), "Draft model ID path traversal rejected");
        reject(() -> restarted.save(request("huge", "image.generate", "x".repeat(16001)), 0), "Oversized draft rejected before persistence");
        JSONObject artifactRecord = new JSONObject().put("provenance", new JSONObject().put("execution", "same_android_phone").put("request", frozen).put("bundle", new JSONObject().put("id", "reuse_model")));
        check(TaskRequests.fromArtifact(artifactRecord).getJSONObject("input").getString("prompt").contains("字面"), "Result provenance can restore a request independently of task history");
        reject(() -> TaskRequests.fromArtifact(DataFiles.copy(artifactRecord).put("origin", new JSONObject().put("kind", "imported"))), "Imported media never masquerades as generated provenance");
        JSONObject mismatch = DataFiles.copy(artifactRecord); mismatch.getJSONObject("provenance").getJSONObject("bundle").put("id", "another");
        reject(() -> TaskRequests.fromArtifact(mismatch), "Mismatched result/request model rejected");
        final TaskDrafts apiDrafts = restarted; final int[] notifications = {0}; JobStore jobs = new JobStore(new File(root, "jobs"));
        ArtifactStore artifacts = new ArtifactStore(new File(root, "artifacts"), file -> new JSONObject().put("mime", "image/png").put("fixture", true));
        LocalApi.Runtime runtime = new LocalApi.Runtime() {
            public String apiKey() { return "fixture-key"; }
            public JSONObject health() { return new JSONObject().put("fixture", true); }
            public JSONArray models() { return new JSONArray(); }
            public JSONArray engines() { return new JSONArray(); }
            public TaskDrafts drafts() { return apiDrafts; }
            public void draftsChanged() { notifications[0]++; }
            public JobStore jobs() { return jobs; }
            public ArtifactStore artifacts() { return artifacts; }
            public JSONObject submit(JSONObject r, String key) throws Exception { return jobs.submit(r, key); }
            public void cancel(String id) throws Exception { jobs.cancel(id); }
            public LocalHttp.Response text(String path, JSONObject input) { return LocalApi.json(200, new JSONObject().put("fixture", true)); }
        };
        try (LocalHttp server = new LocalHttp("127.0.0.1", 0, new LocalApi(runtime))) {
            int port = server.port();
            check(http(port, "GET", "/v1/drafts", null, "wrong").code == 401, "Draft API requires the existing Bearer key");
            JSONObject body = new JSONObject().put("request", request("api_model", "audio.generate", "")).put("expectedRevision", 0);
            Reply saved = http(port, "POST", "/v1/drafts", body, "fixture-key"); long rev = saved.data.getLong("revision");
            check(saved.code == 200 && !saved.data.getJSONObject("request").getBoolean("allowUnmeasured"), "Actual HTTP saves a nonexecuting draft with admission reset");
            check(jobs.snapshot().length() == 0 && artifacts.snapshot().length() == 0, "Saving drafts does not submit jobs or create outputs");
            check(http(port, "POST", "/v1/drafts", body, "fixture-key").code == 409, "Actual HTTP stale write returns a state conflict");
            check(http(port, "GET", "/v1/drafts/api_model", null, "fixture-key").data.getLong("revision") == rev, "Actual HTTP reads the same durable draft");
            check(http(port, "POST", "/v1/drafts/api_model/delete", new JSONObject().put("expectedRevision", rev), "fixture-key").code == 200, "Actual HTTP deletes only the selected draft revision");
            check(http(port, "GET", "/v1/drafts/api_model", null, "fixture-key").code == 404, "Deleted draft returns an explicit not-found response");
            check(notifications[0] == 2, "Only committed API draft writes notify the App view");
            JSONObject queued = jobs.submit(frozen, "frozen"); String jobId = queued.getString("id");
            Reply edit = http(port, "GET", "/v1/jobs/" + jobId + "/request", null, "fixture-key");
            check(edit.code == 200 && !edit.data.has("submissionHash") && !edit.data.getBoolean("allowUnmeasured"), "HTTP task restore uses the same sanitized request core");
            check(jobs.snapshot().length() == 1, "Opening a task request cannot enqueue a duplicate");
            File output = artifacts.staging(jobId, "png"); Files.write(output.toPath(), new byte[]{1, 2, 3});
            JSONObject a = artifacts.commit(jobId, output, artifactRecord.getJSONObject("provenance"), () -> {}); String artifactId = a.getString("id");
            jobs.cancel(jobId); jobs.remove(jobId);
            check(http(port, "GET", "/v1/artifacts/" + artifactId + "/request", null, "fixture-key").code == 200, "Actual stored result restores parameters after deleting its task record");
            check(http(port, "POST", "/v1/jobs/" + jobId + "/request", new JSONObject(), "fixture-key").code == 404, "Deleted task is not silently reconstructed as a new job");
        }
        check(new TaskDrafts(directory).get("reuse_model").getJSONObject("request").getJSONObject("input").getString("prompt").equals("recreated"), "API operations preserve other models across restart");
        System.out.println(new JSONObject().put("passed", true).put("checks", new JSONArray(checks)).put("count", checks.size()).put("actual_socket_io", true).put("actual_persistence_io", true).put("android_execution_tested", false).put("model_inference_tested", false));
    }
}
