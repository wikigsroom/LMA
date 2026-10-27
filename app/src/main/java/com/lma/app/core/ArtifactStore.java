package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Phone-private results with validated media, hashes and immutable generation provenance. */
public final class ArtifactStore {
    public interface Inspector { JSONObject inspect(File file) throws Exception; }
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
    public JSONObject commit(String jobId, File generated, JSONObject provenance, DataFiles.Check check) throws Exception {
        ModelBundle.key(jobId); File candidate = generated.getCanonicalFile();
        if (!candidate.getParentFile().equals(staging) || !candidate.getName().startsWith(jobId + "_")) throw new IOException("Output does not belong to this task's staging area");
        if (!candidate.isFile() || candidate.length() < 1 || candidate.length() > 8L * 1024 * 1024 * 1024) throw new IOException("Empty or oversized output");
        check.run(); JSONObject metadata = inspector.inspect(candidate); String mime = metadata.getString("mime");
        String extension;
        switch (mime) {
            case "image/png": extension = "png"; break; case "image/jpeg": extension = "jpg"; break;
            case "audio/wav": extension = "wav"; break; case "video/mp4": extension = "mp4"; break;
            case "text/plain": extension = "txt"; break; default: throw new IOException("Unsupported output MIME type");
        }
        String digest = DataFiles.sha256(candidate, check); check.run();
        synchronized (this) {
            if (state.getJSONObject("artifacts").length() >= 2048) throw new IOException("Result library is full; delete unneeded results first");
            String id = "artifact_" + UUID.randomUUID().toString().replace("-", ""); String filename = id + "." + extension;
            File target = DataFiles.child(media, filename);
            JSONObject record = new JSONObject().put("id", id).put("jobId", jobId).put("filename", filename).put("metadata", DataFiles.copy(metadata))
                    .put("sha256", digest).put("bytes", candidate.length()).put("createdAt", System.currentTimeMillis()).put("provenance", DataFiles.copy(provenance));
            check.run(); DataFiles.move(candidate, target); JSONObject next = DataFiles.copy(state); next.getJSONObject("artifacts").put(id, record);
            DataFiles.write(index, next); state = next; return DataFiles.copy(record);
        }
    }
    public synchronized JSONObject get(String id) throws Exception {
        JSONObject record = state.getJSONObject("artifacts").optJSONObject(ModelBundle.key(id));
        if (record == null) throw new IllegalArgumentException("Unknown artifact"); return DataFiles.copy(record);
    }
    public synchronized File file(String id) throws Exception {
        JSONObject record = get(id); File file = DataFiles.child(media, record.getString("filename"));
        if (!file.isFile() || file.length() != record.getLong("bytes")) throw new IOException("Result file is missing or changed"); return file;
    }
    public synchronized JSONArray snapshot() throws Exception {
        JSONObject entries = state.getJSONObject("artifacts"); JSONArray result = new JSONArray();
        for (Iterator<String> it = entries.keys(); it.hasNext();) { String id = it.next(); JSONObject record = get(id); File file = DataFiles.child(media, record.getString("filename")); record.put("available", file.isFile() && file.length() == record.getLong("bytes")); record.remove("filename"); record.remove("provenance"); result.put(record); }
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
        if (readers.containsKey(id)) throw new IllegalStateException("Result is used by an active task or export");
        File target = DataFiles.child(media, get(id).getString("filename")); JSONObject next = DataFiles.copy(state); next.getJSONObject("artifacts").remove(id);
        DataFiles.write(index, next); state = next; if (target.exists() && !target.delete()) throw new IOException("Result entry removed; file cleanup is still needed");
    }
    public void discardStaging(String jobId) throws IOException {
        ModelBundle.key(jobId); File[] files = staging.listFiles(); if (files == null) return;
        for (File file : files) if (file.getName().startsWith(jobId + "_") && !file.delete()) throw new IOException("Cannot remove task staging data");
    }
}
