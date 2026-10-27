package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import org.json.JSONArray;
import java.util.*;

/** Durable metadata and content-addressed data; no model path is executable. */
public final class DataFiles {
    private DataFiles() {}
    public static JSONObject read(AtomicFile file, int limit) throws IOException {
        try (InputStream in = file.openRead()) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192]; int count;
            while ((count = in.read(buffer)) != -1) {
                if (out.size() > limit - count) throw new IOException("Metadata exceeds size limit");
                out.write(buffer, 0, count);
            }
            try { return new JSONObject(new String(out.toByteArray(), StandardCharsets.UTF_8)); }
            catch (Exception error) { throw new IOException("Invalid metadata; original file retained", error); }
        }
    }
    public static void write(AtomicFile file, JSONObject value) throws IOException {
        write(file, value, 16 * 1024 * 1024);
    }
    public static void write(AtomicFile file, JSONObject value, int limit) throws IOException {
        byte[] bytes = value.toString().getBytes(StandardCharsets.UTF_8);
        if (bytes.length > limit) throw new IOException("Metadata is full; remove unneeded records before adding more");
        FileOutputStream out = file.startWrite();
        try {
            out.write(bytes);
            file.finishWrite(out);
        } catch (Exception error) {
            file.failWrite(out); throw new IOException("Cannot commit metadata", error);
        }
    }
    public static JSONObject copy(JSONObject value) { try { return new JSONObject(value.toString()); } catch (Exception error) { throw new IllegalArgumentException(error); } }
    public static File child(File root, String relative) throws IOException {
        if (relative == null || !relative.matches("[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")) throw new IOException("Invalid asset path");
        for (String part : relative.split("/")) if (part.equals(".") || part.equals("..")) throw new IOException("Invalid asset path");
        File file = new File(root, relative).getCanonicalFile();
        if (!file.getPath().startsWith(root.getCanonicalPath() + File.separator)) throw new IOException("Asset path escapes storage");
        return file;
    }
    public static String sha256(File file) throws IOException { return sha256(file, () -> {}); }
    public interface Check { void run() throws IOException; }
    public static String sha256(File file, Check check) throws IOException {
        try (InputStream in = new FileInputStream(file)) {
            MessageDigest hash = MessageDigest.getInstance("SHA-256"); byte[] bytes = new byte[256 * 1024]; int count;
            while ((count = in.read(bytes)) != -1) { check.run(); hash.update(bytes, 0, count); }
            check.run(); return Protocol.hex(hash.digest());
        } catch (java.security.NoSuchAlgorithmException error) { throw new IOException(error); }
    }
    public static void move(File from, File to) throws IOException {
        Files.move(from.toPath(), to.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
    }
    public static String canonical(Object value) throws Exception {
        if (value instanceof JSONObject) {
            JSONObject object = (JSONObject) value; List<String> keys = new ArrayList<>(); for (Iterator<String> it = object.keys(); it.hasNext();) keys.add(it.next()); Collections.sort(keys);
            StringBuilder text = new StringBuilder("{");
            for (String key : keys) text.append(JSONObject.quote(key)).append(':').append(canonical(object.get(key))).append(',');
            return text.append('}').toString();
        }
        if (value instanceof JSONArray) { StringBuilder text = new StringBuilder("["); JSONArray array = (JSONArray) value; for (int i = 0; i < array.length(); i++) text.append(canonical(array.get(i))).append(','); return text.append(']').toString(); }
        return value instanceof String ? JSONObject.quote((String) value) : String.valueOf(value);
    }
}
