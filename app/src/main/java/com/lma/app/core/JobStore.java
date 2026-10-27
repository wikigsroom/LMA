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
    public synchronized JSONObject submit(JSONObject request, String idempotencyKey) throws Exception {
        validateKey(idempotencyKey);
        if (request.toString().length() > 32000) throw new IllegalArgumentException("Task request is too large");
        String type = request.getString("type");
        if (!Arrays.asList("text.generate", "image.generate", "video.generate", "speech.synthesize", "audio.generate").contains(type)) throw new IllegalArgumentException("Unknown local task type");
        ModelBundle.key(request.getString("bundleId"));
        JSONArray jobs = state.getJSONArray("jobs"); int pending = 0;
        for (int i = 0; i < jobs.length(); i++) {
            JSONObject previous = jobs.getJSONObject(i);
            if (!idempotencyKey.isEmpty() && previous.optString("idempotencyKey").equals(idempotencyKey)) {
                if (!DataFiles.canonical(previous.getJSONObject("request")).equals(DataFiles.canonical(request))) throw new IllegalStateException("Idempotency key already belongs to a different request");
                return publicJob(previous);
            }
            if (!TERMINAL.contains(previous.getString("state"))) pending++;
        }
        if (pending >= 64 || jobs.length() >= 256) throw new IllegalStateException("Task history/queue is full; remove completed tasks first");
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
        JSONObject next = DataFiles.copy(state), job = find(next, id);
        if (token.isEmpty() || !token.equals(job.optString("token")) || TERMINAL.contains(job.getString("state"))) throw new IOException("Stale task completion rejected");
        boolean cancelled = job.getString("state").equals("cancelling");
        if (cancelled) { job.put("state", "cancelled").put("artifacts", new JSONArray()).put("error", ""); }
        else if (error != null && !error.isEmpty()) { job.put("state", "failed").put("error", error.length() > 2000 ? error.substring(0, 2000) : error); }
        else {
            if (artifacts == null || artifacts.length() == 0) throw new IllegalArgumentException("A successful generation requires a committed output artifact");
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
        JSONObject next = DataFiles.copy(state), job = find(next, id);
        if (!token.equals(job.optString("token")) || TERMINAL.contains(job.getString("state"))) return;
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
