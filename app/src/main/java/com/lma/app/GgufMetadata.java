package com.lma.app;

import java.io.EOFException;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import org.json.JSONObject;

/** Reads bounded GGUF v2/v3 metadata; never allocates tensors or tokenizer arrays. */
public final class GgufMetadata {
    private static final long HEADER_LIMIT = 64L * 1024 * 1024;
    private GgufMetadata() {}
    private static void available(RandomAccessFile file, long bytes) throws IOException {
        if (bytes < 0 || bytes > HEADER_LIMIT - file.getFilePointer() || bytes > file.length() - file.getFilePointer()) throw new EOFException("GGUF 元数据超限或文件不完整");
    }
    private static long number(RandomAccessFile file, int bytes) throws IOException {
        available(file, bytes); long result = 0;
        for (int i = 0; i < bytes; i++) result |= (long) file.readUnsignedByte() << (i * 8);
        return result;
    }
    private static void skip(RandomAccessFile file, long bytes) throws IOException { available(file, bytes); file.seek(file.getFilePointer() + bytes); }
    private static String string(RandomAccessFile file, int max) throws IOException {
        long length = number(file, 8); if (length < 0 || length > max) throw new IOException("GGUF 字符串超限");
        available(file, length); byte[] data = new byte[(int) length]; file.readFully(data); return new String(data, StandardCharsets.UTF_8);
    }
    private static int width(int type) throws IOException {
        switch (type) {
            case 0: case 1: case 7: return 1;
            case 2: case 3: return 2;
            case 4: case 5: case 6: return 4;
            case 10: case 11: case 12: return 8;
            default: throw new IOException("未知 GGUF 元数据类型");
        }
    }
    private static void skipValue(RandomAccessFile file, int type) throws IOException {
        if (type == 8) { skip(file, number(file, 8)); return; }
        if (type == 9) {
            int element = (int) number(file, 4); long count = number(file, 8);
            if (count < 0 || count > 8000000 || element == 9) throw new IOException("GGUF 数组超限或不支持嵌套数组");
            if (element == 8) for (long i = 0; i < count; i++) skip(file, number(file, 8));
            else skip(file, Math.multiplyExact(count, width(element)));
            return;
        }
        skip(file, width(type));
    }
    public static JSONObject read(File source) throws Exception {
        try (RandomAccessFile file = new RandomAccessFile(source, "r")) {
            if (number(file, 4) != 0x46554747L) throw new IOException("文件不是 GGUF");
            long version = number(file, 4); if (version != 2 && version != 3) throw new IOException("当前只读取 GGUF v2 / v3 元数据");
            number(file, 8); long count = number(file, 8);
            if (count < 0 || count > 100000) throw new IOException("GGUF 元数据条目过多");
            String architecture = ""; Map<String, Long> lengths = new HashMap<>();
            for (long i = 0; i < count; i++) {
                String key = string(file, 1024); int type = (int) number(file, 4);
                if (key.equals("general.architecture") && type == 8) architecture = string(file, 128);
                else if (key.endsWith(".context_length") && (type == 4 || type == 5 || type == 10 || type == 11)) {
                    long value = number(file, width(type));
                    if (value > 1 && value <= Integer.MAX_VALUE && lengths.size() < 32) lengths.put(key, value);
                } else skipValue(file, type);
                Long context = lengths.get(architecture + ".context_length");
                if (!architecture.isEmpty() && context != null) return new JSONObject().put("source", "gguf").put("architecture", architecture).put("contextLength", context).put("ggufVersion", version);
            }
            return new JSONObject().put("source", "unknown").put("architecture", architecture).put("contextLength", 0).put("error", "GGUF 未提供可识别的架构上下文上限");
        }
    }
}
