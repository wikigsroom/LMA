package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** HF regular files use Git blob identity; SHA256 is always measured after explicit transfer. */
public final class ComponentIntegrity {
    public static final class Mismatch extends IOException {
        public Mismatch(String message) { super(message); }
    }
    private ComponentIntegrity() {}
    public static String gitObjectKey(String oid) throws Exception {
        return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(("lma.git-blob/1\n" + oid).getBytes(StandardCharsets.US_ASCII)));
    }
    public static JSONObject verify(File file, ModelBundle.Component component, DataFiles.Check check) throws Exception {
        if (file.length() != component.bytes) throw new IOException("Component size mismatch: " + component.role);
        MessageDigest sha256 = MessageDigest.getInstance("SHA-256"), git = component.gitBlobSha1.isEmpty() ? null : MessageDigest.getInstance("SHA-1");
        if (git != null) git.update(("blob " + component.bytes + "\0").getBytes(StandardCharsets.US_ASCII));
        long total = 0;
        try (InputStream input = new FileInputStream(file)) {
            byte[] buffer = new byte[256 * 1024]; int count;
            while ((count = input.read(buffer)) != -1) {
                check.run(); total = Math.addExact(total, count);
                if (total > component.bytes) throw new IOException("Component exceeds pinned size: " + component.role);
                sha256.update(buffer, 0, count); if (git != null) git.update(buffer, 0, count);
            }
        }
        check.run(); if (total != component.bytes) throw new IOException("Component changed during verification: " + component.role);
        String actual = Protocol.hex(sha256.digest()), gitHash = git == null ? "" : Protocol.hex(git.digest());
        if (!component.sha256.isEmpty() && !component.sha256.equals(actual) || git != null && !component.gitBlobSha1.equals(gitHash)) throw new Mismatch("Component integrity mismatch: " + component.role);
        return new JSONObject().put("algorithm", component.integrityAlgorithm).put("sha256", actual).put("gitBlobSha1", gitHash).put("bytes", total);
    }
}
