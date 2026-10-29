package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Transient previews only. Never store PCM in job JSON, and never promote partial audio to an artifact. */
public final class AudioStreams {
    private static final int LIMIT = 4;
    private final File root;
    private final LinkedHashMap<String, Entry> streams = new LinkedHashMap<>();
    private static final class Entry {
        final String id; final AudioPcm.Format format; final File file; final List<JSONObject> chunks = new ArrayList<>();
        int frames; String state = "streaming", artifactId = "";
        Entry(String id, AudioPcm.Format format, File file) { this.id = id; this.format = format; this.file = file; }
        JSONObject summary() throws Exception { return new JSONObject().put("jobId", id).put("format", format.json()).put("state", state).put("nextSequence", chunks.size()).put("frames", frames).put("durationMs", (long) frames * 1000 / format.sampleRate).put("artifactId", artifactId).put("transient", true); }
    }
    public AudioStreams(File directory) throws IOException {
        root = directory.getCanonicalFile(); if (!root.isDirectory() && !root.mkdirs()) throw new IOException("Cannot create audio preview storage");
        File[] stale = root.listFiles(); if (stale == null) throw new IOException("Cannot inspect audio preview storage");
        for (File file : stale) { if (!file.getCanonicalFile().getParentFile().equals(root) || !file.isFile() || !file.delete()) throw new IOException("Cannot remove an interrupted audio preview"); }
    }
    public synchronized void begin(String jobId, AudioPcm.Format format) throws IOException {
        validId(jobId); if (streams.containsKey(jobId)) throw new IOException("Audio preview already exists for this task");
        // The shared execution gate admits one native worker. Keep at most one active preview as well.
        for (Entry entry : streams.values()) if (entry.state.equals("streaming")) throw new IOException("Another audio preview is still active");
        while (streams.size() >= LIMIT) { String oldest = streams.keySet().iterator().next(); remove(oldest); }
        File file = new File(root, jobId + ".pcm"); if (!file.createNewFile()) throw new IOException("Audio preview path already exists"); streams.put(jobId, new Entry(jobId, format, file));
    }
    public synchronized void append(String jobId, AudioPcm.Chunk chunk) throws Exception {
        Entry entry = entry(jobId);
        if (!entry.state.equals("streaming") || chunk.sequence != entry.chunks.size() || chunk.startFrame != entry.frames || chunk.frames < 1 || chunk.frames > entry.format.maxChunkFrames || chunk.frames > entry.format.maxFrames - entry.frames || chunk.pcm.length != chunk.frames * entry.format.channels * 2 || entry.chunks.size() >= 4096) throw new IOException("Audio preview chunk is inconsistent");
        long start = (long) entry.frames * entry.format.channels * 2;
        try (RandomAccessFile out = new RandomAccessFile(entry.file, "rw")) { if (out.length() != start) throw new IOException("Audio preview extent changed"); out.seek(start); out.write(chunk.pcm); out.getFD().sync(); }
        catch (IOException failure) { entry.state = "failed"; throw failure; }
        entry.chunks.add(chunk.json()); entry.frames += chunk.frames;
    }
    public synchronized void finish(String jobId, String state, String artifactId) throws IOException {
        Entry entry = streams.get(jobId); if (entry == null) return;
        if (!Arrays.asList("succeeded", "failed", "cancelled", "interrupted").contains(state)) throw new IOException("Invalid terminal audio preview state");
        if (state.equals("succeeded") && (entry.frames == 0 || artifactId.isEmpty() || entry.state.equals("failed"))) throw new IOException("A successful preview requires a committed full result");
        entry.state = state; entry.artifactId = state.equals("succeeded") ? artifactId : "";
    }
    public synchronized JSONObject get(String jobId, int after) throws Exception {
        Entry entry = entry(jobId); if (after < 0 || after > entry.chunks.size()) throw new IllegalArgumentException("Audio cursor is outside the published range");
        JSONObject value = entry.summary(); JSONArray chunks = new JSONArray();
        for (int i = after; i < Math.min(entry.chunks.size(), after + 32); i++) chunks.put(DataFiles.copy(entry.chunks.get(i)));
        return value.put("chunks", chunks).put("cursor", after + chunks.length());
    }
    public synchronized byte[] read(String jobId, int sequence) throws Exception {
        Entry entry = entry(jobId); if (sequence < 0 || sequence >= entry.chunks.size()) throw new IllegalArgumentException("Audio chunk is not available");
        JSONObject chunk = entry.chunks.get(sequence); byte[] bytes = new byte[chunk.getInt("bytes")];
        try (RandomAccessFile in = new RandomAccessFile(entry.file, "r")) { in.seek((long) chunk.getInt("startFrame") * entry.format.channels * 2); in.readFully(bytes); } return bytes;
    }
    public synchronized JSONArray snapshot() throws Exception { JSONArray values = new JSONArray(); for (Entry entry : streams.values()) values.put(entry.summary()); return values; }
    public synchronized void remove(String jobId) throws IOException { Entry entry = streams.get(jobId); if (entry == null) return; if (entry.state.equals("streaming")) throw new IOException("An active audio preview cannot be removed"); if (!entry.file.delete()) throw new IOException("Cannot remove audio preview"); streams.remove(jobId); }
    private Entry entry(String id) throws IOException { validId(id); Entry entry = streams.get(id); if (entry == null) throw new IOException("Audio preview expired or has not started"); return entry; }
    private static void validId(String id) throws IOException { if (id == null || !id.matches("[a-zA-Z0-9_-]{1,128}")) throw new IOException("Invalid audio task ID"); }
}
