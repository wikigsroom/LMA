package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;

/** Validate actual uncompressed WAV structure, including block/rate consistency and bounded chunks. */
public final class WaveFile {
    private WaveFile() {}
    public static JSONObject inspect(File file) throws Exception {
        try (RandomAccessFile in = new RandomAccessFile(file, "r")) {
            if (in.length() < 44 || in.readInt() != 0x52494646 || Integer.toUnsignedLong(Integer.reverseBytes(in.readInt())) != in.length() - 8 || in.readInt() != 0x57415645) throw new IOException("WAV RIFF size or signature is invalid");
            int channels = 0, rate = 0, bits = 0, format = 0, align = 0, chunks = 0; long dataBytes = 0, byteRate = 0;
            while (in.getFilePointer() < in.length()) {
                if (Thread.currentThread().isInterrupted()) throw new IOException("WAV inspection was stopped");
                if (++chunks > 16384 || in.getFilePointer() > in.length() - 8) throw new IOException("WAV chunk table is incomplete or exceeds its limit");
                int tag = in.readInt(); long size = Integer.toUnsignedLong(Integer.reverseBytes(in.readInt())), start = in.getFilePointer(), next = start + size + (size & 1);
                if (next > in.length()) throw new IOException("WAV data chunk is incomplete");
                if (tag == 0x666d7420) {
                    if (format != 0 || size < 16) throw new IOException("WAV format chunk is missing or duplicated");
                    format = Short.toUnsignedInt(Short.reverseBytes(in.readShort())); channels = Short.toUnsignedInt(Short.reverseBytes(in.readShort())); rate = Integer.reverseBytes(in.readInt());
                    byteRate = Integer.toUnsignedLong(Integer.reverseBytes(in.readInt())); align = Short.toUnsignedInt(Short.reverseBytes(in.readShort())); bits = Short.toUnsignedInt(Short.reverseBytes(in.readShort()));
                } else if (tag == 0x64617461) dataBytes = Math.addExact(dataBytes, size);
                in.seek(next);
            }
            if ((format != 1 && format != 3) || format == 3 && bits != 32 || channels < 1 || channels > 8 || rate < 8000 || rate > 192000 || (bits != 16 && bits != 24 && bits != 32) || align != channels * bits / 8 || byteRate != rate * (long) align || dataBytes < align || dataBytes % align != 0) throw new IOException("WAV sampling format is unsupported, inconsistent or empty");
            return new JSONObject().put("mime", "audio/wav").put("sampleRate", rate).put("channels", channels).put("bitsPerSample", bits).put("samples", dataBytes / align).put("durationMs", dataBytes * 1000 / byteRate);
        }
    }
}
