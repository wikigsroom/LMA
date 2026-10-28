package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Explicit, resumable, bounded input-media uploads. Never accepts a URL or model data. */
public final class InputUploads {
    public static final int CHUNK_BYTES = 256 * 1024;
    private final AtomicFile index;
    private final ArtifactStore artifacts;
    private JSONObject state;
    public InputUploads(File directory, ArtifactStore artifacts) throws Exception {
        if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create input upload storage");
        this.artifacts = artifacts; index = new AtomicFile(new File(directory, "uploads.json"));
        try { state = DataFiles.read(index, 1024 * 1024); }
        catch (FileNotFoundException absent) { state = new JSONObject().put("schema", "lma.input-uploads/1").put("uploads", new JSONObject()); }
        if (!state.getString("schema").equals("lma.input-uploads/1")) throw new IOException("Unsupported input upload schema");
        JSONObject next = DataFiles.copy(state), uploads = next.getJSONObject("uploads");
        for (Iterator<String> it = uploads.keys(); it.hasNext();) {
            String id = it.next(); JSONObject item = uploads.getJSONObject(id), imported = artifacts.imported(id);
            if (imported != null) { item.put("state", "completed").put("artifactId", imported.getString("id")); continue; }
            if (!item.getString("state").equals("uploading")) continue;
            File part = part(item); long received = item.getLong("received");
            if (!part.isFile() || part.length() < received) { item.put("state", "failed").put("error", "Private upload bytes are missing; explicitly cancel and create a new upload"); continue; }
            if (part.length() > received) try (RandomAccessFile out = new RandomAccessFile(part, "rw")) { out.setLength(received); out.getFD().sync(); }
        }
        save(next);
        Set<String> retained = new HashSet<>();
        for (Iterator<String> it = uploads.keys(); it.hasNext();) { JSONObject item = uploads.getJSONObject(it.next()); if (!item.getString("state").equals("completed")) retained.add(item.getString("part")); }
        artifacts.recoverInputs(retained);
    }
    private void save(JSONObject next) throws IOException { DataFiles.write(index, next, 1024 * 1024); state = next; }
    private JSONObject entry(String id) throws Exception {
        JSONObject item = state.getJSONObject("uploads").optJSONObject(ModelBundle.key(id));
        if (item == null) throw new IllegalArgumentException("Unknown input upload"); return item;
    }
    private File part(JSONObject item) throws Exception { return artifacts.inputPart(item.getString("id"), item.getString("part")); }
    private static JSONObject publicItem(JSONObject item) { JSONObject result = DataFiles.copy(item); result.remove("part"); return result; }
    public synchronized JSONObject get(String id) throws Exception { return publicItem(entry(id)); }
    public synchronized JSONArray snapshot() throws Exception {
        JSONArray result = new JSONArray(); JSONObject uploads = state.getJSONObject("uploads");
        for (Iterator<String> it = uploads.keys(); it.hasNext();) result.put(publicItem(uploads.getJSONObject(it.next()))); return result;
    }
    public synchronized JSONObject create(JSONObject request) throws Exception {
        for (Iterator<String> it = request.keys(); it.hasNext();) if (!Arrays.asList("name", "bytes", "sha256").contains(it.next())) throw new IllegalArgumentException("Upload declarations accept only name, bytes and SHA256");
        String name = ArtifactStore.inputName(request.getString("name")), digest = request.getString("sha256");
        if (!(request.get("bytes") instanceof Number) || request.getDouble("bytes") != request.getLong("bytes")) throw new IllegalArgumentException("Upload bytes must be an integer");
        long bytes = request.getLong("bytes");
        if (bytes < 1 || bytes > ArtifactStore.MAX_INPUT_BYTES || !digest.matches("[a-f0-9]{64}")) throw new IllegalArgumentException("Declare 1-512 MiB of input media and its lowercase SHA256");
        int active = 0; long reserved = bytes; JSONObject uploads = state.getJSONObject("uploads");
        if (uploads.length() >= 64) throw new IllegalStateException("Upload history is full; remove completed/cancelled sessions");
        for (Iterator<String> it = uploads.keys(); it.hasNext();) {
            JSONObject previous = uploads.getJSONObject(it.next());
            if (previous.getString("state").equals("uploading")) { active++; reserved = Math.addExact(reserved, previous.getLong("bytes") - previous.getLong("received")); }
        }
        if (active >= 4 || reserved > 1024L * 1024 * 1024) throw new IllegalStateException("At most four uploads and 1 GiB of pending input bytes are allowed");
        String id = "upload_" + UUID.randomUUID().toString().replace("-", ""); File part = artifacts.staging(id, "input");
        if (part.getParentFile().getUsableSpace() < reserved + ArtifactStore.SPACE_RESERVE) throw new IOException("Not enough storage for declared input uploads");
        try {
            try (FileOutputStream out = new FileOutputStream(part)) { out.getFD().sync(); }
            JSONObject record = new JSONObject().put("id", id).put("name", name).put("bytes", bytes).put("sha256", digest).put("part", part.getName())
                    .put("received", 0).put("state", "uploading").put("createdAt", System.currentTimeMillis()).put("chunkBytes", CHUNK_BYTES);
            JSONObject next = DataFiles.copy(state); next.getJSONObject("uploads").put(id, record); save(next); return publicItem(record);
        } catch (Exception error) { artifacts.discardStaging(id); throw error; }
    }
    public synchronized JSONObject append(String id, long offset, byte[] bytes) throws Exception {
        JSONObject item = entry(id);
        if (!item.getString("state").equals("uploading")) throw new IllegalStateException("This upload no longer accepts bytes");
        long received = item.getLong("received"), total = item.getLong("bytes");
        if (offset < 0 || bytes.length < 1 || bytes.length > CHUNK_BYTES || offset > total - bytes.length) throw new IllegalArgumentException("Use a nonempty bounded chunk within the declared input size");
        File part = part(item);
        if (!part.isFile() || part.length() != received) throw new IOException("Private input bytes changed; restart this upload explicitly");
        if (offset < received) {
            if (offset > received - bytes.length) throw new IllegalStateException("Chunk overlaps the committed offset; query upload status");
            byte[] previous = new byte[bytes.length];
            try (RandomAccessFile in = new RandomAccessFile(part, "r")) { in.seek(offset); in.readFully(previous); }
            if (!Arrays.equals(previous, bytes)) throw new IllegalStateException("Retried chunk differs from committed bytes"); return publicItem(item);
        }
        if (offset != received) throw new IllegalStateException("Chunk offset must equal received; query upload status");
        if (part.getUsableSpace() < ArtifactStore.SPACE_RESERVE + bytes.length) throw new IOException("Not enough storage to continue input upload");
        JSONObject next = DataFiles.copy(state); next.getJSONObject("uploads").getJSONObject(id).put("received", received + bytes.length);
        try (RandomAccessFile out = new RandomAccessFile(part, "rw")) {
            try { out.seek(received); out.write(bytes); out.getFD().sync(); save(next); }
            catch (Exception error) { out.setLength(received); out.getFD().sync(); throw error; }
        }
        return get(id);
    }
    public synchronized JSONObject complete(String id, DataFiles.Check check) throws Exception {
        JSONObject item = entry(id);
        if (item.getString("state").equals("failed")) throw new IllegalStateException(item.getString("error"));
        if (item.getLong("received") != item.getLong("bytes")) throw new IllegalStateException("Upload is incomplete; continue from received");
        JSONObject artifact = artifacts.commitImport(id, part(item), item.getString("name"), item.getLong("bytes"), item.getString("sha256"), "api_upload", check);
        JSONObject next = DataFiles.copy(state); next.getJSONObject("uploads").getJSONObject(id).put("state", "completed").put("artifactId", artifact.getString("id")); save(next);
        return artifact;
    }
    public synchronized void remove(String id) throws Exception {
        entry(id); JSONObject next = DataFiles.copy(state); next.getJSONObject("uploads").remove(id); save(next); artifacts.discardStaging(id);
    }
}
