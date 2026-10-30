package com.lma.app.core;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.util.*;

/** Reads selected ModelProto metadata strings by seeking over graph/tensor fields. Never loads ONNX weights. */
public final class OnnxMetadata {
    private OnnxMetadata() {}
    private static final Set<String> WANTED = new HashSet<>(Arrays.asList("n_speakers", "speaker_names", "id2speaker"));
    public static Map<String, String> read(File file) throws IOException {
        Map<String, String> result = new LinkedHashMap<>();
        try (RandomAccessFile input = new RandomAccessFile(file, "r")) {
            long end = input.length(); int fields = 0, entries = 0, textBytes = 0;
            if (end == 0) throw new IOException("Empty ONNX metadata input");
            while (input.getFilePointer() < end) {
                if (++fields > 4096) throw new IOException("Too many ONNX top-level fields");
                long tag = tag(input, end); int wire = (int) tag & 7, field = (int) (tag >>> 3);
                if (field != 14) { skip(input, end, wire); continue; }
                if (wire != 2 || ++entries > 512) throw new IOException("Invalid ONNX metadata entry");
                long length = length(input, end), entryEnd = input.getFilePointer() + length;
                long keyAt = -1, keySize = 0, valueAt = -1, valueSize = 0; int parts = 0;
                while (input.getFilePointer() < entryEnd) {
                    if (++parts > 32) throw new IOException("Too many ONNX metadata entry fields");
                    long item = tag(input, entryEnd); int number = (int) (item >>> 3), type = (int) item & 7;
                    if (number != 1 && number != 2) { skip(input, entryEnd, type); continue; }
                    if (type != 2) throw new IOException("Invalid ONNX metadata string");
                    long size = length(input, entryEnd), start = input.getFilePointer();
                    if (number == 1) { if (keyAt >= 0) throw new IOException("Duplicate ONNX metadata key field"); keyAt = start; keySize = size; }
                    else { if (valueAt >= 0) throw new IOException("Duplicate ONNX metadata value field"); valueAt = start; valueSize = size; }
                    input.seek(start + size);
                }
                if (keyAt >= 0 && keySize <= 256) {
                    String key = text(input, keyAt, keySize);
                    if (WANTED.contains(key)) {
                        if (valueAt < 0 || valueSize > 65536 || (textBytes += (int) valueSize) > 1048576) throw new IOException("Missing or excessive ONNX voice metadata");
                        if (result.put(key, text(input, valueAt, valueSize)) != null) throw new IOException("Duplicate ONNX voice metadata property");
                    }
                }
                input.seek(entryEnd);
            }
            if (input.length() != end) throw new IOException("ONNX metadata input changed while reading");
        }
        return Collections.unmodifiableMap(result);
    }
    private static String text(RandomAccessFile input, long at, long size) throws IOException {
        input.seek(at); byte[] bytes = new byte[(int) size]; input.readFully(bytes);
        try { return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString(); }
        catch (CharacterCodingException invalid) { throw new IOException("Invalid UTF-8 in ONNX metadata", invalid); }
    }
    private static long varint(RandomAccessFile input, long end) throws IOException {
        long value = 0;
        for (int shift = 0; shift < 63; shift += 7) {
            if (input.getFilePointer() >= end) throw new EOFException("Truncated ONNX varint");
            int next = input.readUnsignedByte(); value |= (long) (next & 127) << shift;
            if ((next & 128) == 0) return value;
        }
        throw new IOException("ONNX varint overflow");
    }
    private static long tag(RandomAccessFile input, long end) throws IOException {
        long tag = varint(input, end);
        if (tag > 0xffffffffL || tag >>> 3 == 0) throw new IOException("Invalid ONNX protobuf tag");
        return tag;
    }
    private static long length(RandomAccessFile input, long end) throws IOException {
        long size = varint(input, end);
        if (size > end - input.getFilePointer()) throw new EOFException("ONNX field exceeds its message");
        return size;
    }
    private static void skip(RandomAccessFile input, long end, int wire) throws IOException {
        if (wire == 0) { varint(input, end); return; }
        long size;
        if (wire == 2) size = length(input, end);
        else if (wire == 1) size = 8;
        else if (wire == 5) size = 4;
        else throw new IOException("Unsupported ONNX protobuf wire type");
        if (size > end - input.getFilePointer()) throw new EOFException("Truncated ONNX field");
        input.seek(input.getFilePointer() + size);
    }
}
