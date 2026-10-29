package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Phone-private results with validated media, hashes and immutable generation provenance. */
public final class ArtifactStore {
    public interface Inspector { JSONObject inspect(File file) throws Exception; }
    public interface References { boolean contains(String id) throws Exception; }
    public static final long MAX_INPUT_BYTES = 512L * 1024 * 1024;
    public static final long SPACE_RESERVE = 128L * 1024 * 1024;
    private References references = id -> false;
    private final java.util.concurrent.Semaphore imports = new java.util.concurrent.Semaphore(2);
    public synchronized void references(References guard) { if (guard == null) throw new IllegalArgumentException("Missing input reference guard"); references = guard; }
    private final File root, staging, media;
    private final AtomicFile index;
    private final Inspector inspector;
    private JSONObject state;
    private final Map<String, Integer> readers = new HashMap<>();
    public ArtifactStore(File directory, Inspector inspector) throws Exception {
        root = directory.getCanonicalFile(); staging = new File(root, "staging"); media = new File(root, "media"); this.inspector = inspector;
        if ((!staging.isDirectory() && !staging.mkdirs()) || (!media.isDirectory() && !media.mkdirs())) throw new IOException("Cannot create artifact storage");
        index = new AtomicFile(new File(root, "artifacts.json"));
        try { state = DataFiles.read(index, 16 * 1024 * 1024); }
        catch (FileNotFoundException missing) { state = new JSONObject().put("schema", "lma.artifacts/1").put("artifacts", new JSONObject()); }
        if (!state.getString("schema").equals("lma.artifacts/1")) throw new IOException("Unsupported artifact storage schema");
    }
    public File staging(String jobId, String suffix) throws IOException {
        ModelBundle.key(jobId); if (!suffix.matches("[a-z0-9]{1,12}")) throw new IOException("Invalid output suffix");
        return DataFiles.child(staging, jobId + "_" + UUID.randomUUID().toString().replace("-", "") + "." + suffix);
    }
    public File inputPart(String importId, String filename) throws IOException {
        ModelBundle.key(importId); File file = DataFiles.child(staging, filename);
        if (!file.getParentFile().equals(staging) || !file.getName().startsWith(importId + "_") || !file.getName().endsWith(".input")) throw new IOException("Invalid private input staging identity"); return file;
    }
    /** App startup only, before imports/HTTP are admitted. Preserve all registered partial inputs. */
    public void recoverInputs(Set<String> retained) throws IOException {
        for (String filename : retained) DataFiles.child(staging, filename);
        File[] files = staging.listFiles(); if (files == null) throw new IOException("Cannot reconcile private input staging");
        for (File file : files) if (file.getName().matches("(?:input|upload)_[a-f0-9]{32}_[a-f0-9]{32}\\.input") && !retained.contains(file.getName()) && !file.delete()) throw new IOException("Cannot clean uncommitted input staging");
    }
    public synchronized JSONObject capacity() throws Exception { return new JSONObject().put("count", state.getJSONObject("artifacts").length()).put("limit", 2048); }
    public synchronized void requireCapacity() throws Exception {
        JSONObject slots = capacity(); if (slots.getInt("count") >= slots.getInt("limit")) throw new IOException("素材与结果库已满；请明确删除不再需要的文件后生成，清理任务记录不会删除结果");
    }
    /** Application startup only, before workers/readers are admitted. Published records remain authoritative. */
    public synchronized JSONObject reconcile(JobStore jobs) throws Exception {
        if (!readers.isEmpty()) throw new IllegalStateException("Cannot reconcile outputs while media is being read");
        JSONArray queue = jobs.snapshot();
        for (int i = 0; i < queue.length(); i++) if (Arrays.asList("loading", "running", "cancelling").contains(queue.getJSONObject(i).getString("state"))) throw new IllegalStateException("Output recovery requires startup-reconciled tasks");
        JSONObject entries = state.getJSONObject("artifacts"); Set<String> committed = new HashSet<>();
        for (Iterator<String> it = entries.keys(); it.hasNext();) { JSONObject record = get(it.next()); committed.add(record.getString("filename")); DataFiles.child(media, record.getString("filename")); }
        int recovered = 0, missing = 0, rejected = 0, unlinked = 0, removedStaging = 0, removedOrphans = 0, cleanupFailures = 0; long reclaimed = 0;
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            JSONObject record = get(it.next());
            try { file(record.getString("id")); } catch (IOException absent) { missing++; continue; }
            String result = jobs.recoverOutput(record);
            if (result.equals("recovered")) recovered++; else if (result.equals("rejected")) rejected++;
            else if (result.equals("unlinked") && !record.optString("jobId").isEmpty()) unlinked++;
        }
        File[] pending = staging.listFiles(), outputs = media.listFiles();
        if (pending == null || outputs == null) throw new IOException("Cannot inspect private output storage for recovery");
        for (File file : pending) if (file.getName().matches("job_[a-f0-9]{32}_[a-f0-9]{32}\\.[a-z0-9]{1,12}") && java.nio.file.Files.isRegularFile(file.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) {
            DataFiles.child(staging, file.getName()); long bytes = file.length();
            if (file.delete()) { removedStaging++; reclaimed = Math.addExact(reclaimed, bytes); } else cleanupFailures++;
        }
        for (File file : outputs) if (file.getName().matches("artifact_[a-f0-9]{32}\\.(?:png|jpg|wav|mp4|txt|json)") && !committed.contains(file.getName()) && java.nio.file.Files.isRegularFile(file.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)) {
            DataFiles.child(media, file.getName()); long bytes = file.length();
            if (file.delete()) { removedOrphans++; reclaimed = Math.addExact(reclaimed, bytes); } else cleanupFailures++;
        }
        return new JSONObject().put("schema", "lma.output-recovery/1").put("checkedAt", System.currentTimeMillis()).put("recoveredOutputs", recovered).put("missingOutputs", missing).put("rejectedBindings", rejected)
                .put("unlinkedOutputs", unlinked).put("discardedStagingFiles", removedStaging).put("discardedUncommittedFiles", removedOrphans).put("cleanupFailures", cleanupFailures).put("reclaimedBytes", reclaimed)
                .put("executionResumed", false).put("modelDownloads", false).put("integrityCheck", "committed_metadata_and_size_execution_rehashes_selected_inputs");
    }
    public JSONObject commit(String jobId, File generated, JSONObject provenance, DataFiles.Check check) throws Exception {
        ModelBundle.key(jobId); File candidate = generated.getCanonicalFile();
        if (!candidate.getParentFile().equals(staging) || !candidate.getName().startsWith(jobId + "_")) throw new IOException("Output does not belong to this task's staging area");
        if (!candidate.isFile() || candidate.length() < 1 || candidate.length() > 8L * 1024 * 1024 * 1024) throw new IOException("Empty or oversized output");
        check.run(); JSONObject metadata = inspector.inspect(candidate); String mime = metadata.getString("mime");
        return publish(jobId, candidate, metadata, DataFiles.sha256(candidate, check), provenance, new JSONObject().put("kind", "generated"), check);
    }
    public static String inputName(String name) {
        if (name == null || name.trim().isEmpty() || name.length() > 160 || name.indexOf('/') >= 0 || name.indexOf('\\') >= 0 || name.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException("Use a filename of 1-160 characters without paths/control characters"); return name;
    }
    public JSONObject imported(String importId) throws Exception {
        ModelBundle.key(importId);
        synchronized (this) {
            JSONObject entries = state.getJSONObject("artifacts");
            for (Iterator<String> it = entries.keys(); it.hasNext();) { JSONObject record = entries.getJSONObject(it.next()); JSONObject origin = record.optJSONObject("origin"); if (origin != null && importId.equals(origin.optString("importId"))) return DataFiles.copy(record); }
            return null;
        }
    }
    public JSONObject importStream(InputStream in, String name, DataFiles.Check check) throws Exception {
        inputName(name); if (in == null) throw new IOException("Cannot open the selected local document");
        if (!imports.tryAcquire()) throw new IllegalStateException("Two local input imports are already active");
        String id = "input_" + UUID.randomUUID().toString().replace("-", ""); File candidate = staging(id, "input");
        try {
            long copied = 0;
            try (FileOutputStream out = new FileOutputStream(candidate)) {
                byte[] buffer = new byte[256 * 1024]; int n;
                while ((n = in.read(buffer)) != -1) {
                    check.run(); if (n == 0) continue;
                    if (copied > MAX_INPUT_BYTES - n) throw new IOException("Input exceeds 512 MiB");
                    if (staging.getUsableSpace() < SPACE_RESERVE + n) throw new IOException("Not enough storage for a local input");
                    out.write(buffer, 0, n); copied += n;
                }
                out.getFD().sync();
            }
            return commitImport(id, candidate, name, copied, "", "android_document", check);
        } finally { try { discardStaging(id); } finally { imports.release(); } }
    }
    public JSONObject commitImport(String importId, File candidate, String name, long bytes, String expectedHash, String channel, DataFiles.Check check) throws Exception {
        ModelBundle.key(importId); inputName(name);
        if (!Arrays.asList("api_upload", "android_document").contains(channel) || !expectedHash.isEmpty() && !expectedHash.matches("[a-f0-9]{64}")) throw new IllegalArgumentException("Invalid local input identity");
        JSONObject existing = imported(importId);
        if (existing != null) {
            if (existing.getLong("bytes") != bytes || !existing.getJSONObject("origin").getString("name").equals(name) || !expectedHash.isEmpty() && !expectedHash.equals(existing.getString("sha256"))) throw new IllegalStateException("This input import already has a different identity");
            file(existing.getString("id")); return existing;
        }
        File file = candidate.getCanonicalFile();
        if (!file.getParentFile().equals(staging) || !file.getName().startsWith(importId + "_")) throw new IOException("Input does not belong to this private import");
        if (bytes < 1 || bytes > MAX_INPUT_BYTES || !file.isFile() || file.length() != bytes) throw new IOException("Input is empty, incomplete or exceeds 512 MiB");
        check.run(); String digest = DataFiles.sha256(file, check);
        if (!expectedHash.isEmpty() && !digest.equals(expectedHash)) throw new IOException("Input SHA256 does not match; nothing was imported");
        JSONObject metadata = inspector.inspect(file); String mime = metadata.getString("mime");
        if (!Arrays.asList("image/png", "image/jpeg", "audio/wav", "video/mp4").contains(mime)) throw new IOException("Import PNG/JPEG, PCM WAV or MP4 media");
        JSONObject origin = new JSONObject().put("kind", "imported").put("channel", channel).put("importId", importId).put("name", name);
        synchronized (this) {
            existing = imported(importId); if (existing != null) return existing;
            return publish("", file, metadata, digest, new JSONObject().put("source", "user_selected_local_media"), origin, check);
        }
    }
    private synchronized JSONObject publish(String jobId, File candidate, JSONObject metadata, String digest, JSONObject provenance, JSONObject origin, DataFiles.Check check) throws Exception {
        String mime = metadata.getString("mime"), extension;
        switch (mime) {
            case "image/png": extension = "png"; break; case "image/jpeg": extension = "jpg"; break;
            case "audio/wav": extension = "wav"; break; case "video/mp4": extension = "mp4"; break;
            case "text/plain": extension = "txt"; break; case TextResult.MIME: extension = "json"; break; default: throw new IOException("Unsupported output MIME type");
        }
        check.run();
        {
            requireCapacity();
            String id = "artifact_" + UUID.randomUUID().toString().replace("-", ""); String filename = id + "." + extension;
            File target = DataFiles.child(media, filename);
            JSONObject record = new JSONObject().put("id", id).put("jobId", jobId).put("filename", filename).put("metadata", DataFiles.copy(metadata))
                    .put("sha256", digest).put("bytes", candidate.length()).put("createdAt", System.currentTimeMillis()).put("provenance", DataFiles.copy(provenance)).put("origin", DataFiles.copy(origin));
            check.run(); DataFiles.move(candidate, target); JSONObject next = DataFiles.copy(state); next.getJSONObject("artifacts").put(id, record);
            try { DataFiles.write(index, next); }
            catch (Exception error) { try { DataFiles.move(target, candidate); } catch (Exception restore) { error.addSuppressed(restore); } throw error; }
            state = next; return DataFiles.copy(record);
        }
    }
    public synchronized JSONObject get(String id) throws Exception {
        JSONObject record = state.getJSONObject("artifacts").optJSONObject(ModelBundle.key(id));
        if (record == null) throw new IllegalArgumentException("Unknown artifact"); JSONObject result = DataFiles.copy(record); if (!result.has("origin")) result.put("origin", new JSONObject().put("kind", "generated")); return result;
    }
    public synchronized File file(String id) throws Exception {
        JSONObject record = get(id); File file = DataFiles.child(media, record.getString("filename"));
        if (!file.isFile() || file.length() != record.getLong("bytes")) throw new IOException("Result file is missing or changed"); return file;
    }
    public synchronized JSONArray snapshot() throws Exception {
        JSONObject entries = state.getJSONObject("artifacts"); JSONArray result = new JSONArray();
        for (Iterator<String> it = entries.keys(); it.hasNext();) { String id = it.next(); JSONObject record = get(id); File file = DataFiles.child(media, record.getString("filename")); record.put("available", file.isFile() && file.length() == record.getLong("bytes")); record.put("inUse", readers.containsKey(id) || references.contains(id)); record.remove("filename"); record.remove("provenance"); result.put(record); }
        return result;
    }
    public synchronized Lease acquire(String id) throws Exception { File file = file(id); readers.put(id, readers.getOrDefault(id, 0) + 1); return new Lease(id, file); }
    public InputStream open(String id, ByteRange range) throws Exception {
        Lease lease = acquire(id);
        try {
            RandomAccessFile in = new RandomAccessFile(lease.file, "r");
            try { if (range.start > in.length() - range.length) throw new IOException("Result range is outside the file"); in.seek(range.start); }
            catch (Exception error) { in.close(); throw error; }
            return new InputStream() {
                private long remaining = range.length; private boolean closed;
                @Override public int read() throws IOException { byte[] one = new byte[1]; return read(one, 0, 1) < 0 ? -1 : one[0] & 255; }
                @Override public int read(byte[] bytes, int offset, int count) throws IOException {
                    if (closed) throw new IOException("Result stream is closed");
                    if (count == 0) return 0; if (remaining == 0) return -1;
                    int n = in.read(bytes, offset, (int) Math.min(remaining, count));
                    if (n < 0) throw new EOFException("Result changed during download"); remaining -= n; return n;
                }
                @Override public void close() throws IOException { if (!closed) { closed = true; try { in.close(); } finally { lease.close(); } } }
            };
        } catch (Exception error) { lease.close(); throw error; }
    }
    public final class Lease implements AutoCloseable {
        public final String id; public final File file; private boolean closed;
        private Lease(String id, File file) { this.id = id; this.file = file; }
        @Override public void close() { synchronized (ArtifactStore.this) { if (!closed) { closed = true; int count = readers.get(id) - 1; if (count == 0) readers.remove(id); else readers.put(id, count); } } }
    }
    public synchronized void remove(String id) throws Exception {
        if (readers.containsKey(id) || references.contains(id)) throw new IllegalStateException("Media is referenced by a queued/running task or active read/export");
        File target = DataFiles.child(media, get(id).getString("filename")); JSONObject next = DataFiles.copy(state); next.getJSONObject("artifacts").remove(id);
        DataFiles.write(index, next); state = next; if (target.exists() && !target.delete()) throw new IOException("Result entry removed; file cleanup is still needed");
    }
    public void discardStaging(String jobId) throws IOException {
        ModelBundle.key(jobId); File[] files = staging.listFiles(); if (files == null) return;
        for (File file : files) if (file.getName().startsWith(jobId + "_") && !file.delete()) throw new IOException("Cannot remove task staging data");
    }
}
