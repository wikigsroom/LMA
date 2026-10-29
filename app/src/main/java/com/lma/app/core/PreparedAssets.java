package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.*;

/** Verified derived user data, separate from source bundles and generated media. */
public final class PreparedAssets implements AutoCloseable {
    private final File root, work, assets;
    private final AtomicFile index;
    private final FileChannel owner;
    private final FileLock ownership;
    private final Map<String,Integer> leases = new HashMap<>();
    private JSONObject state;
    private boolean closed;
    public PreparedAssets(File directory) throws Exception {
        root = privateDirectory(directory); work = privateDirectory(new File(root, "work")); assets = privateDirectory(new File(root, "assets"));
        owner = new RandomAccessFile(new File(root, "owner.lock"), "rw").getChannel();
        FileLock lock;
        try { lock = owner.tryLock(); if (lock == null) throw new IOException("Prepared asset storage is owned by another App instance"); }
        catch (Exception error) { owner.close(); throw error; }
        ownership = lock; index = new AtomicFile(new File(root, "index.json"));
        try {
            try { state = DataFiles.read(index, 16 * 1024 * 1024); }
            catch (FileNotFoundException absent) { state = new JSONObject().put("schema", "lma.prepared-assets/1").put("entries", new JSONObject()); }
            if (!state.getString("schema").equals("lma.prepared-assets/1")) throw new IOException("Unsupported prepared asset storage");
            JSONObject entries = state.getJSONObject("entries");
            for (Iterator<String> it = entries.keys(); it.hasNext();) ownedId(it.next());
            // Android converters carry a parent-death guard. No former App child can own these workspaces.
            for (File folder : children(work)) if (isOwned(folder.getName())) erase(work, folder.getName());
            for (File folder : children(assets)) if (isOwned(folder.getName()) && !entries.has(folder.getName())) erase(assets, folder.getName());
            DataFiles.write(index, state);
        } catch (Exception error) { ownership.release(); owner.close(); throw error; }
    }
    private static File privateDirectory(File file) throws IOException {
        File expected = new File(file.getAbsoluteFile().getParentFile().getCanonicalFile(), file.getName());
        if (Files.isSymbolicLink(file.toPath()) || !expected.equals(file.getCanonicalFile())) throw new IOException("Prepared asset root is an alias");
        Files.createDirectories(expected.toPath());
        if (!Files.isDirectory(expected.toPath(), LinkOption.NOFOLLOW_LINKS)) throw new IOException("Prepared asset root is not a directory");
        return expected;
    }
    private static File[] children(File file) throws IOException { File[] list = file.listFiles(); if (list == null) throw new IOException("Cannot inspect prepared asset storage"); return list; }
    private static boolean isOwned(String id) { return id != null && id.matches("prep_[a-f0-9]{32}"); }
    private static String ownedId(String id) throws IOException { if (!isOwned(id)) throw new IOException("Invalid prepared asset ID"); return id; }
    private void checkOpen() throws IOException { if (closed) throw new IOException("Prepared asset storage is closed"); }
    private void persist(JSONObject next) throws IOException { DataFiles.write(index, next); state = next; }
    public synchronized Session begin(String jobId) throws Exception {
        checkOpen(); ModelBundle.key(jobId); String id = "prep_" + UUID.randomUUID().toString().replace("-", "");
        File folder = new File(work, id); Files.createDirectory(folder.toPath()); return new Session(id, jobId, folder);
    }
    public synchronized JSONArray snapshot(String bundleId) throws Exception {
        checkOpen(); JSONArray result = new JSONArray(); JSONObject entries = state.getJSONObject("entries");
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            JSONObject record = entries.getJSONObject(it.next()); if (!bundleId.isEmpty() && !bundleId.equals(record.getString("bundleId"))) continue;
            JSONObject copy = DataFiles.copy(record); copy.put("available", intact(record)).put("inUse", leases.containsKey(record.getString("id"))); result.put(copy);
        }
        return result;
    }
    public synchronized JSONObject record(String id) throws Exception {
        checkOpen(); ownedId(id); return DataFiles.copy(state.getJSONObject("entries").getJSONObject(id));
    }
    public synchronized void remove(String id, JobStore jobs) throws Exception {
        if (jobs != null && jobs.referencesPrepared(id)) throw new IOException("Prepared assets are referenced by a queued/running task");
        remove(id);
    }
    public synchronized boolean contains(String bundleId, PreparationPlan plan) throws Exception {
        JSONArray records = snapshot(bundleId);
        for (int i = 0; i < records.length(); i++) if (records.getJSONObject(i).getString("planFingerprint").equals(plan.fingerprint) && records.getJSONObject(i).getBoolean("available")) return true;
        return false;
    }
    /** A commit interrupted before successful task completion must not become a completed result. */
    public synchronized void reconcile(JobStore jobs) throws Exception {
        Map<String,String> states = new HashMap<>(); JSONArray history = jobs.snapshot();
        for (int i = 0; i < history.length(); i++) { JSONObject job = history.getJSONObject(i); states.put(job.getString("id"), job.getString("state")); }
        JSONArray records = snapshot("");
        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.getJSONObject(i); String status = states.get(record.getString("jobId"));
            if (Arrays.asList("failed", "cancelled", "interrupted").contains(status)) remove(record.getString("id"));
        }
    }
    private boolean intact(JSONObject record) throws Exception {
        File folder = new File(assets, ownedId(record.getString("id")));
        if (!Files.isDirectory(folder.toPath(), LinkOption.NOFOLLOW_LINKS) || Files.isSymbolicLink(folder.toPath())) return false;
        JSONArray outputs = record.getJSONArray("outputs");
        for (int i = 0; i < outputs.length(); i++) {
            JSONObject output = outputs.getJSONObject(i); File file;
            try { file = DataFiles.child(folder, output.getString("path")); } catch (IOException invalid) { return false; }
            if (!Files.isRegularFile(file.toPath(), LinkOption.NOFOLLOW_LINKS) || file.length() != output.getLong("bytes") || file.lastModified() != output.getLong("modified")) return false;
        }
        return true;
    }
    public synchronized void remove(String id) throws Exception {
        checkOpen(); ownedId(id); if (leases.containsKey(id)) throw new IOException("Prepared assets are used by a running task");
        JSONObject next = DataFiles.copy(state); if (!next.getJSONObject("entries").has(id)) throw new IOException("Unknown prepared assets");
        next.getJSONObject("entries").remove(id); persist(next); erase(assets, id);
    }
    public Lease acquire(String id, DataFiles.Check check) throws Exception {
        JSONObject record;
        synchronized (this) {
            checkOpen(); ownedId(id); record = DataFiles.copy(state.getJSONObject("entries").getJSONObject(id));
            if (!intact(record)) throw new IOException("Prepared assets are missing or changed"); leases.put(id, leases.getOrDefault(id, 0) + 1);
        }
        Lease lease = new Lease(record);
        try {
            JSONArray outputs = record.getJSONArray("outputs");
            for (int i = 0; i < outputs.length(); i++) { JSONObject output = outputs.getJSONObject(i); verify(lease.file(output.getString("role")), output.getLong("bytes"), output.getString("sha256"), check); }
            return lease;
        } catch (Exception error) { lease.close(); throw error; }
    }
    public final class Lease implements AutoCloseable {
        private final JSONObject record; private boolean released;
        private Lease(JSONObject record) { this.record = record; }
        public JSONObject record() { return DataFiles.copy(record); }
        public File file(String role) throws Exception {
            synchronized (PreparedAssets.this) {
                if (released) throw new IOException("Prepared asset lease is closed"); JSONArray outputs = record.getJSONArray("outputs");
                for (int i = 0; i < outputs.length(); i++) { JSONObject output = outputs.getJSONObject(i); if (role.equals(output.getString("role"))) return DataFiles.child(new File(assets, record.getString("id")), output.getString("path")); }
                throw new IOException("Unknown prepared component role");
            }
        }
        @Override public void close() { synchronized (PreparedAssets.this) { if (!released) { released = true; String id = record.optString("id"); int count = leases.get(id) - 1; if (count == 0) leases.remove(id); else leases.put(id, count); } } }
    }
    public final class Session implements AutoCloseable {
        public final String id, jobId; public final File directory;
        private boolean committed, discarded;
        private Session(String id, String jobId, File directory) { this.id = id; this.jobId = jobId; this.directory = directory; }
        public JSONObject commit(PreparationPlan plan, String bundleId, DataFiles.Check check) throws Exception {
            ModelBundle.key(bundleId); JSONArray outputs = new JSONArray(); check.run();
            for (PreparationPlan.Stage stage : plan.stages) {
                JSONObject receipt = readJson(DataFiles.child(directory, stage.id + "/" + stage.receipt), 1024 * 1024);
                if (!receipt.getString("schema").equals(stage.receiptSchema) || !receipt.getBoolean("ok") || !receipt.getBoolean("source_sha256_verified") || !receipt.getString("source_sha256").equals(plan.sourceSha256) || receipt.getLong("source_bytes") != plan.sourceBytes) throw new IOException("Native preparation did not verify the selected source");
                for (PreparationPlan.Output output : stage.outputs) {
                    String path = stage.id + "/" + output.file; File file = DataFiles.child(directory, path); verify(file, output.bytes, output.sha256, check);
                    outputs.put(new JSONObject().put("role", output.role).put("path", path).put("bytes", output.bytes).put("sha256", output.sha256).put("modified", file.lastModified()));
                }
            }
            JSONObject record = new JSONObject().put("id", id).put("jobId", jobId).put("bundleId", bundleId).put("planId", plan.id).put("planFingerprint", plan.fingerprint)
                    .put("sourceSha256", plan.sourceSha256).put("sourceBytes", plan.sourceBytes).put("sourceRetained", true).put("bytes", plan.outputBytes).put("outputs", outputs).put("createdAt", System.currentTimeMillis());
            synchronized (PreparedAssets.this) {
                checkOpen(); check.run(); if (committed || discarded) throw new IOException("Preparation session already ended");
                if (contains(bundleId, plan)) throw new IOException("These assets are already prepared; keep or explicitly delete the existing copy");
                JSONObject next = DataFiles.copy(state); if (next.getJSONObject("entries").length() >= 256) throw new IOException("Prepared asset history is full");
                File target = new File(assets, id); if (Files.exists(target.toPath(), LinkOption.NOFOLLOW_LINKS)) throw new IOException("Prepared asset destination already exists");
                Files.move(directory.toPath(), target.toPath());
                try { check.run(); next.getJSONObject("entries").put(id, record); persist(next); committed = true; }
                catch (Exception error) { erase(assets, id); throw error; }
                return DataFiles.copy(record);
            }
        }
        @Override public void close() throws IOException { synchronized (PreparedAssets.this) { if (!committed && !discarded) { erase(work, id); discarded = true; } } }
    }
    public static JSONObject readJson(File file, int limit) throws Exception {
        if (!Files.isRegularFile(file.toPath(), LinkOption.NOFOLLOW_LINKS)) throw new IOException("Missing preparation receipt");
        try (InputStream input = new FileInputStream(file)) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] buffer = new byte[8192]; int count;
            while ((count = input.read(buffer)) >= 0) { if (bytes.size() > limit - count) throw new IOException("Preparation receipt is too large"); bytes.write(buffer, 0, count); }
            return new JSONObject(new String(bytes.toByteArray(), java.nio.charset.StandardCharsets.UTF_8));
        }
    }
    public static void verify(File file, long bytes, String sha256, DataFiles.Check check) throws Exception {
        BasicFileAttributes before = Files.readAttributes(file.toPath(), BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!before.isRegularFile() || before.size() != bytes) throw new IOException("Prepared asset size/type mismatch");
        MessageDigest hash = MessageDigest.getInstance("SHA-256"); byte[] buffer = new byte[4 * 1024 * 1024]; long read = 0; int count;
        try (InputStream input = new BufferedInputStream(new FileInputStream(file))) { while ((count = input.read(buffer)) >= 0) { check.run(); hash.update(buffer, 0, count); read += count; } }
        BasicFileAttributes after = Files.readAttributes(file.toPath(), BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        check.run(); if (!after.isRegularFile() || read != bytes || after.size() != bytes || !before.lastModifiedTime().equals(after.lastModifiedTime()) || !Objects.equals(before.fileKey(), after.fileKey()) || !Protocol.hex(hash.digest()).equals(sha256)) throw new IOException("Prepared asset identity mismatch");
    }
    private static void erase(File parent, String id) throws IOException {
        ownedId(id); Path path = new File(parent, id).toPath();
        if (!path.getParent().equals(parent.toPath()) || Files.isSymbolicLink(parent.toPath())) throw new IOException("Preparation cleanup escaped its owned root");
        if (!Files.exists(path, LinkOption.NOFOLLOW_LINKS)) return;
        Files.walkFileTree(path, new SimpleFileVisitor<Path>() {
            @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) throws IOException { delete(file); return FileVisitResult.CONTINUE; }
            @Override public FileVisitResult postVisitDirectory(Path directory, IOException error) throws IOException { if (error != null) throw error; delete(directory); return FileVisitResult.CONTINUE; }
        });
    }
    private static void delete(Path path) throws IOException {
        for (int attempt = 0; ; attempt++) {
            try { Files.deleteIfExists(path); return; }
            catch (FileSystemException busy) {
                if (attempt >= 9) throw busy;
                try { Thread.sleep(50); } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); throw new IOException("Preparation cleanup interrupted; owned files remain for recovery", interrupted); }
            }
        }
    }
    @Override public synchronized void close() throws IOException { if (!closed) { if (!leases.isEmpty()) throw new IOException("Prepared assets still have active leases"); closed = true; ownership.release(); owner.close(); } }
}
