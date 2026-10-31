package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Durable single-heavy-worker queue. A token owns one process generation and its results. */
public final class JobStore {
    private static final Set<String> TERMINAL = new HashSet<>(Arrays.asList("succeeded", "failed", "cancelled", "interrupted"));
    private final AtomicFile file;
    private JSONObject state;
    public JobStore(File directory) throws Exception {
        if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create job storage");
        file = new AtomicFile(new File(directory, "jobs.json"));
        try { state = DataFiles.read(file, 16 * 1024 * 1024); }
        catch (FileNotFoundException missing) { state = new JSONObject().put("schema", "lma.jobs/1").put("sequence", 0).put("jobs", new JSONArray()).put("events", new JSONArray()); }
        if (!state.getString("schema").equals("lma.jobs/1")) throw new IOException("Unsupported job storage schema");
        JSONObject next = DataFiles.copy(state); JSONArray jobs = next.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject job = jobs.getJSONObject(i); String status = job.getString("state");
            if (!TERMINAL.contains(status) && !status.equals("queued")) {
                job.put("state", status.equals("cancelling") ? "cancelled" : "interrupted").put("token", "").put("finishedAt", System.currentTimeMillis())
                        .put("error", "Execution was interrupted; no resumable engine checkpoint exists. Explicit retry starts a new task.");
                event(next, job, "reconciled");
            }
        }
        persist(next);
    }
    private void persist(JSONObject next) throws IOException { DataFiles.write(file, next); state = next; }
    private static JSONObject find(JSONObject source, String id) throws Exception {
        ModelBundle.key(id); JSONArray jobs = source.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) if (jobs.getJSONObject(i).getString("id").equals(id)) return jobs.getJSONObject(i);
        throw new IllegalArgumentException("Unknown task");
    }
    public synchronized JSONObject get(String id) throws Exception { return publicJob(find(state, id)); }
    public synchronized boolean referencesBundle(String id) throws Exception {
        ModelBundle.key(id); JSONArray jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject job = jobs.getJSONObject(i);
            if (!TERMINAL.contains(job.getString("state")) && ModelSelection.ids(job.getJSONObject("request")).contains(id)) return true;
        }
        return false;
    }
    public synchronized boolean referencesArtifact(String id) throws Exception {
        ModelBundle.key(id); JSONArray jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject job = jobs.getJSONObject(i);
            if (!TERMINAL.contains(job.getString("state")) && InputSelection.ids(job.getJSONObject("request")).contains(id)) return true;
        }
        return false;
    }
    public synchronized boolean referencesPrepared(String id) throws Exception {
        ModelBundle.key(id); JSONArray jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject job = jobs.getJSONObject(i), request = job.getJSONObject("request");
            if (!TERMINAL.contains(job.getString("state")) && id.equals(request.optString("preparedAssetsId"))) return true;
        }
        return false;
    }
    public synchronized JSONArray snapshot() throws Exception { JSONArray jobs = state.getJSONArray("jobs"), result = new JSONArray(); for (int i = 0; i < jobs.length(); i++) result.put(publicJob(jobs.getJSONObject(i))); return result; }
    public synchronized JSONArray summaries() throws Exception {
        JSONArray jobs = snapshot();
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject request = jobs.getJSONObject(i).getJSONObject("request"), input = request.optJSONObject("input"); String prompt = input == null ? "" : input.optString("prompt");
            request.remove("input"); request.put("inputSummary", prompt.length() > 200 ? prompt.substring(0, 200) + "…" : prompt);
        }
        return jobs;
    }
    private static JSONObject publicJob(JSONObject job) { JSONObject value = DataFiles.copy(job); value.remove("token"); return value; }
    public synchronized JSONObject lookup(String idempotencyKey) throws Exception {
        validateKey(idempotencyKey); if (idempotencyKey.isEmpty()) return null;
        JSONArray jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) if (jobs.getJSONObject(i).optString("idempotencyKey").equals(idempotencyKey)) return publicJob(jobs.getJSONObject(i));
        return null;
    }
    private static void validateKey(String key) { if (key == null || key.length() > 160 || key.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException("Invalid idempotency key"); }
    public synchronized JSONObject capacity() throws Exception {
        JSONArray jobs = state.getJSONArray("jobs"); int pending = 0;
        for (int i = 0; i < jobs.length(); i++) if (!TERMINAL.contains(jobs.getJSONObject(i).getString("state"))) pending++;
        return new JSONObject().put("history", jobs.length()).put("pending", pending).put("terminal", jobs.length() - pending).put("historyLimit", 256).put("pendingLimit", 64);
    }
    public synchronized void requireCapacity() throws Exception {
        JSONObject slots = capacity();
        if (slots.getInt("pending") >= slots.getInt("pendingLimit")) throw new IllegalStateException("本机队列已满；请等待任务结束，或明确取消不再需要的任务");
        if (slots.getInt("history") >= slots.getInt("historyLimit")) throw new IllegalStateException("任务历史已满；可在任务页检查并清理已结束记录，保留结果文件");
    }
    /** Review freezes terminal identities; tasks that finish later are not part of this selection. */
    public synchronized JSONObject historyPlan() throws Exception {
        JSONArray ids = new JSONArray(), jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) if (TERMINAL.contains(jobs.getJSONObject(i).getString("state"))) ids.put(jobs.getJSONObject(i).getString("id"));
        return new JSONObject().put("ids", ids).put("count", ids.length()).put("review", historyReview(ids)).put("capacity", capacity());
    }
    private String historyReview(JSONArray ids) throws Exception {
        if (ids == null || ids.length() > 256) throw new IllegalArgumentException("Choose at most 256 terminal task records");
        JSONArray selection = new JSONArray(); Set<String> seen = new HashSet<>();
        for (int i = 0; i < ids.length(); i++) {
            String id = ModelBundle.key(ids.getString(i)); if (!seen.add(id)) throw new IllegalArgumentException("Select each task record once");
            JSONObject job;
            try { job = find(state, id); } catch (IllegalArgumentException absent) { throw new IllegalStateException("任务记录已经变化，请重新检查清理范围"); }
            if (!TERMINAL.contains(job.getString("state"))) throw new IllegalStateException("清理只能选择已结束的任务记录；不会取消或删除排队 / 运行任务");
            selection.put(new JSONObject().put("id", id).put("state", job.getString("state")).put("createdAt", job.getLong("createdAt")).put("finishedAt", job.optLong("finishedAt")));
        }
        return TaskInput.fingerprint(new JSONObject().put("records", selection));
    }
    public synchronized JSONObject clearHistory(JSONObject input) throws Exception {
        for (Iterator<String> it = input.keys(); it.hasNext();) if (!Arrays.asList("ids", "review").contains(it.next())) throw new IllegalArgumentException("History cleanup accepts reviewed record IDs only");
        JSONArray ids = input.getJSONArray("ids");
        if (!historyReview(ids).equals(input.getString("review"))) throw new IllegalStateException("清理范围与确认内容不一致，请重新检查");
        if (ids.length() > 0) {
            Set<String> selected = new HashSet<>(); for (int i = 0; i < ids.length(); i++) selected.add(ids.getString(i));
            JSONObject next = DataFiles.copy(state); JSONArray jobs = next.getJSONArray("jobs");
            for (int i = jobs.length() - 1; i >= 0; i--) if (selected.contains(jobs.getJSONObject(i).getString("id"))) { event(next, jobs.getJSONObject(i), "removed"); jobs.remove(i); }
            persist(next);
        }
        return new JSONObject().put("removed", ids.length()).put("capacity", capacity());
    }
    /** Startup only: restore links to committed outputs without claiming the interrupted job succeeded. */
    public synchronized String recoverOutput(JSONObject artifact) throws Exception {
        String id = artifact.optString("jobId"); if (id.isEmpty()) return "unlinked";
        JSONObject job;
        try { job = find(state, id); } catch (IllegalArgumentException absent) { return "unlinked"; }
        JSONArray outputs = job.getJSONArray("artifacts"); String output = ModelBundle.key(artifact.getString("id"));
        for (int i = 0; i < outputs.length(); i++) if (output.equals(outputs.getString(i))) return "linked";
        if (!job.getString("state").equals("interrupted")) return "unlinked";
        JSONObject provenance = artifact.optJSONObject("provenance"), request = job.getJSONObject("request"), origin = artifact.optJSONObject("origin");
        if (!TaskRequests.generation(request.optString("type")) || origin != null && !origin.optString("kind").equals("generated") || provenance == null
                || !provenance.optString("execution").equals("same_android_phone") || !DataFiles.canonical(request).equals(DataFiles.canonical(provenance.optJSONObject("request")))
                || provenance.optJSONObject("bundle") == null || !request.getString("bundleId").equals(provenance.getJSONObject("bundle").optString("id"))) return "rejected";
        if (outputs.length() >= 16) return "rejected";
        JSONObject next = DataFiles.copy(state), restored = find(next, id); restored.getJSONArray("artifacts").put(output);
        restored.put("outputRecovery", new JSONObject().put("kind", "committed_output_after_interruption").put("at", System.currentTimeMillis()).put("executionResumed", false));
        event(next, restored, "output_recovered"); persist(next); return "recovered";
    }
    public synchronized JSONObject submit(JSONObject request, String idempotencyKey) throws Exception {
        validateKey(idempotencyKey);
        if (request.toString().length() > 32000) throw new IllegalArgumentException("Task request is too large");
        String type = request.getString("type");
        if (!Arrays.asList("text.generate", "image.generate", "video.generate", "speech.synthesize", "audio.generate", "mesh.generate", "model.prepare", "model.assemble").contains(type)) throw new IllegalArgumentException("Unknown local task type");
        ModelBundle.key(request.getString("bundleId"));
        JSONArray jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject previous = jobs.getJSONObject(i);
            if (!idempotencyKey.isEmpty() && previous.optString("idempotencyKey").equals(idempotencyKey)) {
                if (!DataFiles.canonical(previous.getJSONObject("request")).equals(DataFiles.canonical(request))) throw new IllegalStateException("Idempotency key already belongs to a different request");
                return publicJob(previous);
            }
        }
        requireCapacity();
        String id = "job_" + UUID.randomUUID().toString().replace("-", "");
        JSONObject job = new JSONObject().put("id", id).put("state", "queued").put("request", DataFiles.copy(request)).put("idempotencyKey", idempotencyKey)
                .put("createdAt", System.currentTimeMillis()).put("artifacts", new JSONArray()).put("error", "").put("stage", "queued");
        JSONObject next = DataFiles.copy(state); next.getJSONArray("jobs").put(job); event(next, job, "queued"); persist(next); return publicJob(job);
    }
    public synchronized JSONObject claimNext() throws Exception {
        JSONArray jobs = state.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) if (Arrays.asList("loading", "running", "cancelling").contains(jobs.getJSONObject(i).getString("state"))) return null;
        JSONObject next = DataFiles.copy(state); JSONArray queue = next.getJSONArray("jobs");
        for (int i = 0; i < queue.length(); i++) {
            JSONObject job = queue.getJSONObject(i);
            if (job.getString("state").equals("queued")) {
                job.put("state", "loading").put("stage", "loading").put("token", UUID.randomUUID().toString()).put("startedAt", System.currentTimeMillis());
                event(next, job, "loading"); persist(next); return DataFiles.copy(job);
            }
        }
        return null;
    }
    public synchronized void check(String id, String token) throws IOException {
        try {
            JSONObject job = find(state, id); String status = job.getString("state");
            if (token.isEmpty() || !token.equals(job.optString("token")) || !Arrays.asList("loading", "running").contains(status)) throw new IOException("Task cancelled, interrupted or superseded");
        } catch (IOException error) { throw error; } catch (Exception error) { throw new IOException(error); }
    }
    public synchronized void progress(String id, String token, String stage, Double fraction) throws Exception {
        check(id, token);
        if (stage == null || stage.isEmpty() || stage.length() > 120 || fraction != null && (!Double.isFinite(fraction) || fraction < 0 || fraction > 1)) throw new IllegalArgumentException("Invalid task progress");
        JSONObject next = DataFiles.copy(state), job = find(next, id);
        job.put("state", "running").put("stage", stage).put("progress", fraction == null ? JSONObject.NULL : fraction); event(next, job, "progress"); persist(next);
    }
    public synchronized void cancel(String id) throws Exception {
        JSONObject next = DataFiles.copy(state), job = find(next, id); String status = job.getString("state");
        if (TERMINAL.contains(status)) return;
        if (status.equals("queued")) job.put("state", "cancelled").put("finishedAt", System.currentTimeMillis()).put("token", "");
        else job.put("state", "cancelling");
        event(next, job, "cancel_requested"); persist(next);
    }
    public synchronized void finish(String id, String token, JSONArray artifacts, String error) throws Exception {
        finishResult(id, token, artifacts, null, error);
    }
    public synchronized void finish(String id, String token, JSONArray artifacts, String error, JSONObject resources) throws Exception {
        finishResult(id, token, artifacts, null, error, resources);
    }
    public synchronized void finishPreparation(String id, String token, JSONObject prepared, String error) throws Exception {
        finishPreparation(id, token, prepared, error, null);
    }
    public synchronized void finishPreparation(String id, String token, JSONObject prepared, String error, JSONObject resources) throws Exception {
        if (!find(state, id).getJSONObject("request").getString("type").equals("model.prepare")) throw new IOException("A generation task cannot finish as asset preparation");
        finishResult(id, token, new JSONArray(), prepared, error, resources);
    }
    public synchronized void finishAssembly(String id, String token, JSONObject assembly, String error) throws Exception {
        finishAssembly(id, token, assembly, error, null);
    }
    public synchronized void finishAssembly(String id, String token, JSONObject assembly, String error, JSONObject resources) throws Exception {
        if (!find(state, id).getJSONObject("request").getString("type").equals("model.assemble")) throw new IOException("Only an assembly task can finish with an association receipt");
        finishResult(id, token, new JSONArray(), assembly, error, resources);
    }
    private void finishResult(String id, String token, JSONArray artifacts, JSONObject prepared, String error) throws Exception {
        finishResult(id, token, artifacts, prepared, error, null);
    }
    private static void runtimeResources(JSONObject job, JSONObject resources) throws Exception {
        if (resources == null) return;
        if (resources.toString().length() > 4096 || !resources.optString("scope").equals("shared_system_availability_not_model_peak_memory")) throw new IllegalArgumentException("Invalid runtime resource summary");
        job.put("runtimeResources", DataFiles.copy(resources));
    }
    private void finishResult(String id, String token, JSONArray artifacts, JSONObject prepared, String error, JSONObject resources) throws Exception {
        JSONObject next = DataFiles.copy(state), job = find(next, id);
        if (token.isEmpty() || !token.equals(job.optString("token")) || TERMINAL.contains(job.getString("state"))) throw new IOException("Stale task completion rejected");
        runtimeResources(job, resources);
        boolean cancelled = job.getString("state").equals("cancelling");
        if (cancelled) { job.put("state", "cancelled").put("artifacts", new JSONArray()).put("error", ""); }
        else if (error != null && !error.isEmpty()) { job.put("state", "failed").put("error", error.length() > 2000 ? error.substring(0, 2000) : error); }
        else {
            if (job.getJSONObject("request").getString("type").equals("model.prepare")) {
                if (prepared == null || !prepared.getString("jobId").equals(id) || !prepared.getString("bundleId").equals(job.getJSONObject("request").getString("bundleId"))) throw new IllegalArgumentException("Preparation requires committed derived model assets");
                JSONObject request = job.getJSONObject("request"); ModelBundle.key(prepared.getString("id"));
                if (!prepared.getString("planId").equals(request.getString("preparationId")) || !prepared.getString("planFingerprint").equals(request.getString("planFingerprint")) || prepared.getJSONArray("outputs").length() < 1) throw new IllegalArgumentException("Prepared assets do not match the immutable task");
                job.put("preparation", DataFiles.copy(prepared));
            } else if (job.getJSONObject("request").getString("type").equals("model.assemble")) {
                JSONObject request = job.getJSONObject("request");
                if (prepared == null || !prepared.getString("schema").equals("lma.model-assembly-result/1") || !prepared.getString("jobId").equals(id)
                        || !prepared.getString("bundleId").equals(request.getString("bundleId")) || !prepared.getString("preparedAssetsId").equals(request.getString("preparedAssetsId"))
                        || !prepared.getString("assemblyId").equals(request.getString("assemblyId")) || !prepared.getString("assemblyFingerprint").equals(request.getString("assemblyFingerprint"))
                        || !prepared.getString("sourceFingerprint").equals(request.getString("assemblySourceFingerprint")) || prepared.getInt("linkedComponents") < 1 || prepared.getLong("linkedBytes") < 1
                        || prepared.getBoolean("automaticDownloads") || prepared.getBoolean("modelInference") || prepared.getBoolean("physicalAndroid")) throw new IllegalArgumentException("Assembly receipt does not match the immutable local task");
                job.put("assembly", DataFiles.copy(prepared));
            } else if (artifacts == null || artifacts.length() == 0) throw new IllegalArgumentException("A successful generation requires a committed output artifact");
            job.put("state", "succeeded").put("artifacts", new JSONArray(artifacts.toString()));
        }
        job.put("token", "").put("finishedAt", System.currentTimeMillis()); event(next, job, "finished"); persist(next);
    }
    public synchronized void remove(String id) throws Exception {
        if (!TERMINAL.contains(find(state, id).getString("state"))) throw new IllegalStateException("Cancel a queued/running task before removing it");
        JSONObject next = DataFiles.copy(state); JSONArray jobs = next.getJSONArray("jobs");
        for (int i = 0; i < jobs.length(); i++) if (jobs.getJSONObject(i).getString("id").equals(id)) { jobs.remove(i); break; }
        persist(next);
    }
    public synchronized void interrupt(String id, String token, String reason) throws Exception {
        interrupt(id, token, reason, null);
    }
    public synchronized void interrupt(String id, String token, String reason, JSONObject resources) throws Exception {
        JSONObject next = DataFiles.copy(state), job = find(next, id);
        if (!token.equals(job.optString("token")) || TERMINAL.contains(job.getString("state"))) return;
        runtimeResources(job, resources);
        job.put("state", job.getString("state").equals("cancelling") ? "cancelled" : "interrupted").put("token", "").put("error", reason).put("finishedAt", System.currentTimeMillis());
        event(next, job, "interrupted"); persist(next);
    }
    public synchronized JSONObject events(long after, String jobId) throws Exception {
        JSONArray events = state.getJSONArray("events"), result = new JSONArray(); long first = events.length() == 0 ? 0 : events.getJSONObject(0).getLong("sequence");
        if (!jobId.isEmpty()) find(state, jobId);
        for (int i = 0; i < events.length(); i++) { JSONObject e = events.getJSONObject(i); if (e.getLong("sequence") > after && (jobId.isEmpty() || jobId.equals(e.getString("jobId")))) result.put(DataFiles.copy(e)); }
        return new JSONObject().put("events", result).put("cursor", state.getLong("sequence")).put("truncated", after > 0 && first > after + 1);
    }
    private static void event(JSONObject next, JSONObject job, String kind) throws Exception {
        long sequence = next.getLong("sequence") + 1; next.put("sequence", sequence);
        JSONArray events = next.getJSONArray("events");
        events.put(new JSONObject().put("sequence", sequence).put("jobId", job.getString("id")).put("kind", kind).put("state", job.getString("state")).put("stage", job.optString("stage"))
                .put("progress", job.has("progress") ? job.get("progress") : JSONObject.NULL).put("time", System.currentTimeMillis()));
        while (events.length() > 512) events.remove(0);
    }
}
