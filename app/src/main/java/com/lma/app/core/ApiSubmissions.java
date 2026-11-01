package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Durable caller-key journal, independent of removable UI task history. */
public final class ApiSubmissions {
    public interface Submitter {
        JSONObject freeze(JSONObject request) throws Exception;
        JSONObject lookup(String key) throws Exception;
        JSONObject submit(JSONObject frozen, String key) throws Exception;
        JSONObject get(String id) throws Exception;
    }
    private final AtomicFile file;
    private JSONObject state;
    private static final long RETENTION = 86400000L;
    public ApiSubmissions(File directory) throws Exception {
        if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create API submission storage");
        file = new AtomicFile(new File(directory, "submissions.json"));
        try { state = DataFiles.read(file, 16 * 1024 * 1024); }
        catch (FileNotFoundException missing) { state = new JSONObject().put("schema", "lma.api-submissions/1").put("records", new JSONObject()); }
        if (!state.getString("schema").equals("lma.api-submissions/1")) throw new IOException("Unknown API submission journal");
    }
    public synchronized JSONObject submit(String endpoint, String callerKey, JSONObject original, Submitter submitter) throws Exception {
        if (callerKey.isEmpty() || callerKey.length() > 160 || callerKey.chars().anyMatch(c -> c < 33 || c > 126)) throw new LocalHttp.Failure(400, "lma_idempotency_key_required", "Use a printable Idempotency-Key of 1-160 characters");
        // Lookup namespace deliberately excludes body/model/defaults. Conflicts are checked after lookup.
        String namespace = ApiCatalogue.hash(new JSONObject().put("endpoint", endpoint).put("key", callerKey));
        String fingerprint = ApiCatalogue.hash(original); JSONObject records = state.getJSONObject("records"), record = records.optJSONObject(namespace);
        if (record != null && !record.getString("request_hash").equals(fingerprint)) throw new LocalHttp.Failure(409, "lma_idempotency_conflict", "This key already belongs to another request");
        if (record == null) {
            prune(submitter);
            if (state.getJSONObject("records").length() >= 1024) throw new LocalHttp.Failure(503, "lma_idempotency_capacity", "API submission retention is full; active and recent entries cannot be evicted");
            record = new JSONObject().put("request_hash", fingerprint).put("model", original.getString("model")).put("native_key", "api_" + namespace)
                    .put("frozen", submitter.freeze(DataFiles.copy(original))).put("created_at", System.currentTimeMillis()).put("state", "submitting");
            JSONObject next = DataFiles.copy(state); next.getJSONObject("records").put(namespace, record); persist(next); record = state.getJSONObject("records").getJSONObject(namespace);
        }
        if (record.has("job_id")) {
            try { return submitter.get(record.getString("job_id")); }
            catch (IllegalArgumentException missing) { throw new LocalHttp.Failure(410, "lma_job_history_removed", "This task was already accepted; its history was removed. It will not be generated again"); }
        }
        JSONObject job = submitter.lookup(record.getString("native_key"));
        if (job == null) job = submitter.submit(DataFiles.copy(record.getJSONObject("frozen")), record.getString("native_key"));
        if (job.optBoolean("historyRemoved")) throw new LocalHttp.Failure(410, "lma_job_history_removed", "This request was previously accepted; a removed task is never regenerated automatically");
        JSONObject next = DataFiles.copy(state), saved = next.getJSONObject("records").getJSONObject(namespace);
        saved.put("job_id", job.getString("id")).put("state", "accepted"); persist(next); return job;
    }
    private void prune(Submitter submitter) throws Exception {
        JSONObject next = DataFiles.copy(state), records = next.getJSONObject("records"); List<String> expired = new ArrayList<>();
        for (Iterator<String> it = records.keys(); it.hasNext();) {
            String key = it.next(); JSONObject record = records.getJSONObject(key); if (!record.has("job_id")) continue;
            JSONObject job;
            try { job = submitter.get(record.getString("job_id")); }
            catch (IllegalArgumentException missing) { job = submitter.lookup(record.getString("native_key")); if (job == null) continue; }
            long finished = job.optLong("finishedAt");
            if (Arrays.asList("succeeded", "failed", "cancelled", "interrupted").contains(job.optString("state")) && finished > 0 && System.currentTimeMillis() - finished >= RETENTION) expired.add(key);
        }
        if (!expired.isEmpty()) { for (String key : expired) records.remove(key); persist(next); }
    }
    private void persist(JSONObject next) throws IOException { DataFiles.write(file, next, 16 * 1024 * 1024); state = next; }
    public synchronized String modelForJob(String id, String fallback) throws Exception {
        JSONObject records = state.getJSONObject("records");
        for (Iterator<String> it = records.keys(); it.hasNext();) { JSONObject record = records.getJSONObject(it.next()); if (id.equals(record.optString("job_id"))) return record.getString("model"); }
        return fallback;
    }
}
