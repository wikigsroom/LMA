package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.security.MessageDigest;
import java.util.Base64;

/** Bounded, ordered PCM events from one owned worker, verified against its final WAV. */
public final class AudioPcm {
    private AudioPcm() {}
    public static final String SCHEMA = "lma.audio-stream/1";
    public static final class Format {
        public final int sampleRate, channels, maxFrames, maxChunkFrames;
        public Format(JSONObject value) throws IOException {
            if (!SCHEMA.equals(value.optString("schema")) || !"pcm_s16le".equals(value.optString("format"))) throw new IOException("Unsupported audio stream format");
            sampleRate = integer(value, "sampleRate", 8000, 48000); channels = integer(value, "channels", 1, 2);
            maxFrames = integer(value, "maxFrames", 1, sampleRate * 120); maxChunkFrames = integer(value, "maxChunkFrames", 1, 4800);
            if ((long) maxFrames * channels * 2 > 24 * 1024 * 1024) throw new IOException("Audio stream exceeds its byte limit");
        }
        public JSONObject json() throws org.json.JSONException { return new JSONObject().put("schema", SCHEMA).put("format", "pcm_s16le").put("sampleRate", sampleRate).put("channels", channels).put("maxFrames", maxFrames).put("maxChunkFrames", maxChunkFrames); }
    }
    public static final class Chunk {
        public final int sequence, startFrame, frames;
        public final byte[] pcm;
        private Chunk(int sequence, int startFrame, int frames, byte[] pcm) { this.sequence = sequence; this.startFrame = startFrame; this.frames = frames; this.pcm = pcm; }
        public JSONObject json() throws org.json.JSONException { return new JSONObject().put("sequence", sequence).put("startFrame", startFrame).put("frames", frames).put("bytes", pcm.length); }
    }
    public static final class Sequence {
        public final Format format;
        private final MessageDigest digest;
        private int next, frames;
        private boolean ended;
        public Sequence(Format format) throws Exception { this.format = format; digest = MessageDigest.getInstance("SHA-256"); }
        public Chunk chunk(JSONObject event) throws Exception {
            if (ended || next >= 4096 || !SCHEMA.equals(event.optString("schema"))) throw new IOException("Invalid or late audio chunk");
            int sequence = integer(event, "sequence", 0, 4095), start = integer(event, "startFrame", 0, format.maxFrames), count = integer(event, "frames", 1, format.maxChunkFrames);
            if (sequence != next || start != frames || count > format.maxFrames - frames || integer(event, "sampleRate", 8000, 48000) != format.sampleRate || integer(event, "channels", 1, 2) != format.channels) throw new IOException("Audio chunks are out of order or use a different format");
            String encoded = event.optString("pcm", ""); int bytes = count * format.channels * 2;
            if (encoded.length() != (bytes + 2) / 3 * 4) throw new IOException("Audio chunk has an invalid encoded size");
            byte[] pcm;
            try { pcm = Base64.getDecoder().decode(encoded); } catch (IllegalArgumentException error) { throw new IOException("Invalid audio chunk encoding", error); }
            if (pcm.length != bytes || !Base64.getEncoder().encodeToString(pcm).equals(encoded)) throw new IOException("Audio chunk has a truncated or noncanonical payload");
            Chunk chunk = new Chunk(sequence, start, count, pcm); digest.update(pcm); next++; frames += count; return chunk;
        }
        public void end(JSONObject event) throws IOException {
            if (ended || next == 0 || !SCHEMA.equals(event.optString("schema")) || integer(event, "nextSequence", 1, 4096) != next || integer(event, "frames", 1, format.maxFrames) != frames) throw new IOException("Audio stream did not end at its published boundary");
            ended = true;
        }
        public void verify(File wav) throws Exception {
            if (!ended) throw new IOException("Audio stream ended without a final boundary");
            JSONObject info = WaveFile.inspect(wav);
            if (info.getInt("formatCode") != 1 || info.getInt("bitsPerSample") != 16 || info.getInt("sampleRate") != format.sampleRate || info.getInt("channels") != format.channels || info.getLong("samples") != frames) throw new IOException("Final WAV format differs from streamed audio");
            MessageDigest actual = MessageDigest.getInstance("SHA-256");
            try (RandomAccessFile in = new RandomAccessFile(wav, "r")) {
                in.seek(12); byte[] buffer = new byte[16384];
                while (in.getFilePointer() < in.length()) {
                    int tag = in.readInt(); long size = Integer.toUnsignedLong(Integer.reverseBytes(in.readInt())), end = in.getFilePointer() + size;
                    if (tag == 0x64617461) while (in.getFilePointer() < end) { if (Thread.currentThread().isInterrupted()) throw new IOException("Audio verification stopped"); int n = in.read(buffer, 0, (int) Math.min(buffer.length, end - in.getFilePointer())); if (n < 1) throw new EOFException(); actual.update(buffer, 0, n); }
                    in.seek(end + (size & 1));
                }
            }
            if (!MessageDigest.isEqual(digest.digest(), actual.digest())) throw new IOException("Final WAV samples differ from streamed audio");
        }
    }
    public static int integer(JSONObject value, String key, int min, int max) throws IOException {
        Object raw = value.opt(key); if (!(raw instanceof Number)) throw new IOException("Audio field must be an integer: " + key);
        double number = ((Number) raw).doubleValue(); if (!Double.isFinite(number) || number < min || number > max || number != Math.rint(number)) throw new IOException("Audio field is outside its limit: " + key); return (int) number;
    }
}
