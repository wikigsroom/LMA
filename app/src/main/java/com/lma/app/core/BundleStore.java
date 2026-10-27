package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

/** Shared immutable components and an atomic installed-bundle index, owned by Application. */
public final class BundleStore {
    private final File root, objects, partials;
    private final AtomicFile file;
    private JSONObject state;
    private final Map<String, Integer> leases = new HashMap<>();
    private final ConcurrentHashMap<String, ReentrantLock> componentLocks = new ConcurrentHashMap<>();
    public BundleStore(File directory) throws Exception {
        root = directory.getCanonicalFile(); objects = new File(root, "objects"); partials = new File(root, "partial");
        if ((!objects.isDirectory() && !objects.mkdirs()) || (!partials.isDirectory() && !partials.mkdirs())) throw new IOException("Cannot create model storage");
        file = new AtomicFile(new File(root, "bundles.json"));
        try { state = DataFiles.read(file, 8 * 1024 * 1024); }
        catch (FileNotFoundException missing) { state = new JSONObject().put("schema", "lma.bundle-store/1").put("bundles", new JSONObject()).put("objects", new JSONObject()); }
        if (!state.getString("schema").equals("lma.bundle-store/1")) throw new IOException("Unsupported model store schema");
        JSONObject next = DataFiles.copy(state), entries = next.getJSONObject("bundles");
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            JSONObject entry = entries.getJSONObject(it.next()), transfer = entry.optJSONObject("transfer");
            if (transfer != null && Arrays.asList("queued", "downloading", "verifying", "installing").contains(transfer.optString("state")))
                transfer.put("state", "paused").put("token", "").put("error", "Transfer interrupted; resume explicitly");
            if (entry.optBoolean("installed") && !complete(new ModelBundle(entry.getJSONObject("manifest")), next)) entry.put("installed", false).put("error", "A required component is missing or changed");
        }
        persist(next);
    }
    private void persist(JSONObject next) throws IOException { DataFiles.write(file, next, 8 * 1024 * 1024); state = next; }
    private JSONObject entry(String id) throws Exception {
        JSONObject value = state.getJSONObject("bundles").optJSONObject(ModelBundle.key(id));
        if (value == null) throw new IllegalArgumentException("Unknown model bundle"); return value;
    }
    public synchronized ModelBundle bundle(String id) throws Exception { return new ModelBundle(entry(id).getJSONObject("manifest")); }
    public synchronized void declare(ModelBundle bundle) throws Exception {
        JSONObject existing = state.getJSONObject("bundles").optJSONObject(bundle.id);
        if (existing != null) {
            if (!DataFiles.canonical(existing.getJSONObject("manifest")).equals(DataFiles.canonical(bundle.json()))) throw new IllegalArgumentException("Bundle IDs are immutable; choose a new versioned bundle ID");
            return;
        }
        JSONObject next = DataFiles.copy(state);
        next.getJSONObject("bundles").put(bundle.id, new JSONObject().put("manifest", bundle.json()).put("installed", false).put("settings", new JSONObject()));
        persist(next);
    }
    public synchronized JSONObject plan(String id) throws Exception {
        ModelBundle b = bundle(id); long total = 0, reusable = 0, remaining = 0; Set<String> seen = new HashSet<>(); JSONArray files = new JSONArray();
        for (ModelBundle.Component c : b.components) {
            boolean present = hasObject(c);
            if (seen.add(c.sha256)) { total = Math.addExact(total, c.bytes); if (present) reusable += c.bytes; else remaining += Math.max(0, c.bytes - Math.min(c.bytes, partial(c.sha256).length())); }
            files.put(new JSONObject().put("role", c.role).put("path", c.path).put("bytes", c.bytes).put("sha256", c.sha256).put("reusable", present).put("downloadable", !c.url.isEmpty()));
        }
        return new JSONObject().put("bundleId", id).put("components", files).put("totalBytes", total).put("reusableBytes", reusable).put("remainingBytes", remaining)
                .put("availableBytes", root.getUsableSpace()).put("installed", entry(id).optBoolean("installed") && complete(b, state));
    }
    /** Explicit user action only. Construction, declaration and planning never enqueue a transfer. */
    public synchronized String request(String id) throws Exception {
        JSONObject next = DataFiles.copy(state), e = next.getJSONObject("bundles").getJSONObject(ModelBundle.key(id));
        if (e.optBoolean("installed") && complete(bundle(id), next)) return "";
        String token = UUID.randomUUID().toString();
        JSONObject transfer = new JSONObject().put("state", "queued").put("token", token).put("received", 0).put("error", "").put("updatedAt", System.currentTimeMillis());
        e.put("transfer", transfer); persist(next); return token;
    }
    public synchronized void check(String id, String token) throws IOException {
        try {
            JSONObject transfer = entry(id).optJSONObject("transfer");
            if (transfer == null || token.isEmpty() || !token.equals(transfer.optString("token")) || transfer.optString("state").equals("paused")) throw new IOException("Transfer paused or superseded");
        } catch (IOException error) { throw error; } catch (Exception error) { throw new IOException(error); }
    }
    public synchronized void progress(String id, String token, String status, String role, long received, String error) throws Exception {
        check(id, token);
        if (!Arrays.asList("downloading", "verifying", "installing", "failed").contains(status)) throw new IllegalArgumentException("Invalid transfer state");
        JSONObject next = DataFiles.copy(state), t = next.getJSONObject("bundles").getJSONObject(id).getJSONObject("transfer");
        t.put("state", status).put("role", role).put("received", received).put("error", error).put("updatedAt", System.currentTimeMillis());
        persist(next);
    }
    public synchronized void pause(String id) throws Exception {
        JSONObject next = DataFiles.copy(state), e = next.getJSONObject("bundles").getJSONObject(ModelBundle.key(id)), transfer = e.optJSONObject("transfer");
        if (transfer != null) transfer.put("state", "paused").put("token", "").put("error", "").put("updatedAt", System.currentTimeMillis());
        persist(next);
    }
    public synchronized boolean hasObject(ModelBundle.Component c) throws IOException { return hasObject(c, state); }
    private boolean hasObject(ModelBundle.Component c, JSONObject data) throws IOException {
        JSONObject receipt = data.optJSONObject("objects").optJSONObject(c.sha256); File f = object(c.sha256);
        return receipt != null && receipt.optLong("bytes") == c.bytes && f.isFile() && f.length() == c.bytes && receipt.optLong("modified") == f.lastModified();
    }
    private boolean complete(ModelBundle bundle, JSONObject data) throws IOException { for (ModelBundle.Component c : bundle.components) if (!hasObject(c, data)) return false; return true; }
    public File object(String hash) throws IOException { if (!Protocol.isSha256(hash)) throw new IOException("Invalid component hash"); return DataFiles.child(objects, hash.toLowerCase(Locale.ROOT)); }
    public File partial(String hash) throws IOException { if (!Protocol.isSha256(hash)) throw new IOException("Invalid component hash"); return DataFiles.child(partials, hash.toLowerCase(Locale.ROOT) + ".part"); }
    public ReentrantLock componentLock(String hash) { if (!Protocol.isSha256(hash)) throw new IllegalArgumentException("Invalid component hash"); return componentLocks.computeIfAbsent(hash, key -> new ReentrantLock()); }
    /** Hash outside the metadata monitor; cancellation remains responsive during verification. */
    public void accept(String id, String token, ModelBundle.Component c, File candidate) throws Exception {
        synchronized (this) {
            ModelBundle.Component expected = bundle(id).component(c.role);
            if (!expected.sha256.equals(c.sha256) || expected.bytes != c.bytes || !expected.path.equals(c.path)) throw new IOException("Component does not belong to the selected bundle");
            check(id, token);
        }
        ReentrantLock lock = componentLock(c.sha256); lock.lockInterruptibly();
        try {
        File actual = candidate.getCanonicalFile();
        if (!actual.equals(partial(c.sha256)) && !actual.equals(object(c.sha256))) throw new IOException("Component is outside managed storage");
        if (actual.length() != c.bytes) throw new IOException("Component size mismatch: " + c.role);
        if (!DataFiles.sha256(actual, () -> check(id, token)).equals(c.sha256)) { if (actual.equals(partial(c.sha256))) actual.delete(); throw new IOException("Component SHA256 mismatch: " + c.role); }
        synchronized (this) {
            check(id, token); File target = object(c.sha256);
            if (!actual.equals(target)) DataFiles.move(actual, target);
            JSONObject next = DataFiles.copy(state);
            next.getJSONObject("objects").put(c.sha256, new JSONObject().put("bytes", c.bytes).put("modified", target.lastModified()).put("verifiedAt", System.currentTimeMillis()));
            persist(next);
        }
        } finally { lock.unlock(); }
    }
    public synchronized void install(String id, String token) throws Exception {
        check(id, token); ModelBundle b = bundle(id);
        if (!complete(b, state)) throw new IOException("Required components are incomplete; bundle remains uninstalled");
        JSONObject next = DataFiles.copy(state), e = next.getJSONObject("bundles").getJSONObject(id);
        e.put("installed", true).put("installedAt", System.currentTimeMillis()).put("error", "");
        e.getJSONObject("transfer").put("state", "installed").put("token", "").put("error", ""); persist(next);
    }
    public synchronized JSONObject settings(String id) throws Exception { return bundle(id).parameters().normalize(entry(id).getJSONObject("settings"), new JSONObject()); }
    public synchronized JSONObject saveSettings(String id, JSONObject changes) throws Exception {
        if (leases.containsKey(id)) throw new IllegalStateException("Model is in use; stop its task before changing settings");
        JSONObject effective = bundle(id).parameters().normalize(entry(id).getJSONObject("settings"), changes);
        JSONObject next = DataFiles.copy(state); next.getJSONObject("bundles").getJSONObject(id).put("settings", effective.getJSONObject("values")); persist(next); return effective;
    }
    public synchronized JSONArray snapshot() throws Exception {
        JSONArray result = new JSONArray(); JSONObject entries = state.getJSONObject("bundles");
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            String id = it.next(); JSONObject e = DataFiles.copy(entries.getJSONObject(id)); ModelBundle b = new ModelBundle(e.getJSONObject("manifest"));
            e.put("id", id).put("tags", b.tags()).put("plan", plan(id)).put("config", settings(id)).put("installed", e.optBoolean("installed") && complete(b, state)).put("inUse", leases.containsKey(id)); result.put(e);
        }
        return result;
    }
    public synchronized Lease acquire(String id) throws Exception {
        ModelBundle b = bundle(id);
        if (!entry(id).optBoolean("installed") || !complete(b, state)) throw new IOException("Select and download all required components first");
        leases.put(id, leases.getOrDefault(id, 0) + 1); return new Lease(b);
    }
    /** Acquires the complete explicit selection atomically; failed acquisition releases all references. */
    public synchronized Selection acquireAll(List<String> ids) throws Exception {
        if (ids.isEmpty() || ids.size() > 9 || new HashSet<>(ids).size() != ids.size()) throw new IllegalArgumentException("Invalid model selection");
        List<Lease> held = new ArrayList<>();
        try { for (String id : ids) held.add(acquire(id)); return new Selection(held); }
        catch (Exception error) { for (Lease lease : held) lease.close(); throw error; }
    }
    public final class Selection implements AutoCloseable {
        public final List<Lease> models;
        Selection(List<Lease> models) { this.models = Collections.unmodifiableList(new ArrayList<>(models)); }
        @Override public void close() { for (Lease lease : models) lease.close(); }
    }
    public final class Lease implements AutoCloseable {
        public final ModelBundle bundle;
        private boolean closed;
        Lease(ModelBundle bundle) { this.bundle = bundle; }
        public File file(String role) throws IOException { synchronized (BundleStore.this) { if (closed) throw new IOException("Model lease is closed"); return object(bundle.component(role).sha256); } }
        @Override public void close() { synchronized (BundleStore.this) { if (!closed) { closed = true; int n = leases.get(bundle.id) - 1; if (n == 0) leases.remove(bundle.id); else leases.put(bundle.id, n); } } }
    }
    public synchronized void remove(String id, boolean removeSettings) throws Exception {
        JSONObject e = entry(id);
        if (leases.containsKey(id)) throw new IllegalStateException("Model is used by a running task");
        JSONObject transfer = e.optJSONObject("transfer");
        if (transfer != null && Arrays.asList("queued", "downloading", "verifying", "installing").contains(transfer.optString("state"))) throw new IllegalStateException("Pause the transfer before deleting a bundle");
        JSONObject next = DataFiles.copy(state), changed = next.getJSONObject("bundles").getJSONObject(id);
        changed.put("installed", false).remove("transfer"); if (removeSettings) changed.put("settings", new JSONObject());
        // Commit the reference change before any destructive cleanup. Orphans after interruption are harmless.
        persist(next);
        Set<String> keep = new HashSet<>(); JSONObject entries = state.getJSONObject("bundles");
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            JSONObject other = entries.getJSONObject(it.next()); JSONObject t = other.optJSONObject("transfer");
            boolean active = t != null;
            if (other.optBoolean("installed") || active) for (ModelBundle.Component c : new ModelBundle(other.getJSONObject("manifest")).components) keep.add(c.sha256);
        }
        ModelBundle b = new ModelBundle(e.getJSONObject("manifest"));
        for (ModelBundle.Component c : b.components) if (!keep.contains(c.sha256)) {
            ReentrantLock lock = componentLock(c.sha256);
            if (lock.tryLock()) { try { object(c.sha256).delete(); partial(c.sha256).delete(); } finally { lock.unlock(); } }
        }
    }
}
