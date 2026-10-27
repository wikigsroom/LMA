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
    public interface ParameterResolver { ParameterSchema resolve(ModelBundle bundle) throws Exception; }
    private ParameterResolver parameterResolver = ModelBundle::parameters;
    public synchronized void setParameterResolver(ParameterResolver resolver) { parameterResolver = Objects.requireNonNull(resolver); }
    public synchronized ParameterSchema parameters(String id) throws Exception { return parameterResolver.resolve(bundle(id)); }
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
        if (!next.has("versions")) next.put("versions", new JSONObject());
        validateVersions(next);
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
            if (seen.add(c.objectId)) { total = Math.addExact(total, c.bytes); if (present) reusable += c.bytes; else remaining += Math.max(0, c.bytes - Math.min(c.bytes, partial(c.objectId).length())); }
            files.put(new JSONObject().put("role", c.role).put("path", c.path).put("importPath", c.importPath).put("bytes", c.bytes).put("objectId", c.objectId).put("sha256", c.sha256).put("gitBlobSha1", c.gitBlobSha1).put("integrityAlgorithm", c.integrityAlgorithm).put("verifiedSha256", present ? verifiedSha256(c, state) : "").put("reusable", present).put("downloadable", !c.url.isEmpty()));
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
    private String verifiedSha256(ModelBundle.Component c, JSONObject data) {
        JSONObject receipt = data.optJSONObject("objects").optJSONObject(c.objectId);
        return receipt == null ? "" : receipt.optString("sha256", c.sha256);
    }
    private boolean hasObject(ModelBundle.Component c, JSONObject data) throws IOException {
        JSONObject receipt = data.optJSONObject("objects").optJSONObject(c.objectId); File f = object(c.objectId);
        return receipt != null && (c.gitBlobSha1.isEmpty() || c.gitBlobSha1.equals(receipt.optString("gitBlobSha1")) && Protocol.isSha256(receipt.optString("sha256"))) && receipt.optLong("bytes") == c.bytes && f.isFile() && f.length() == c.bytes && receipt.optLong("modified") == f.lastModified();
    }
    private boolean complete(ModelBundle bundle, JSONObject data) throws IOException { for (ModelBundle.Component c : bundle.components) if (!hasObject(c, data)) return false; return true; }
    public File object(String hash) throws IOException { if (!Protocol.isSha256(hash)) throw new IOException("Invalid component hash"); return DataFiles.child(objects, hash.toLowerCase(Locale.ROOT)); }
    public File partial(String hash) throws IOException { if (!Protocol.isSha256(hash)) throw new IOException("Invalid component hash"); return DataFiles.child(partials, hash.toLowerCase(Locale.ROOT) + ".part"); }
    public ReentrantLock componentLock(String hash) { if (!Protocol.isSha256(hash)) throw new IllegalArgumentException("Invalid component hash"); return componentLocks.computeIfAbsent(hash, key -> new ReentrantLock()); }
    /** Hash outside the metadata monitor; cancellation remains responsive during verification. */
    public void accept(String id, String token, ModelBundle.Component c, File candidate) throws Exception {
        synchronized (this) {
            ModelBundle.Component expected = bundle(id).component(c.role);
            if (!expected.objectId.equals(c.objectId) || expected.bytes != c.bytes || !expected.path.equals(c.path)) throw new IOException("Component does not belong to the selected bundle");
            check(id, token);
        }
        ReentrantLock lock = componentLock(c.objectId); lock.lockInterruptibly();
        try {
        File actual = candidate.getCanonicalFile();
        if (!actual.equals(partial(c.objectId)) && !actual.equals(object(c.objectId))) throw new IOException("Component is outside managed storage");
        if (actual.length() != c.bytes) throw new IOException("Component size mismatch: " + c.role);
        JSONObject verified;
        try { verified = ComponentIntegrity.verify(actual, c, () -> check(id, token)); }
        catch (ComponentIntegrity.Mismatch error) { if (actual.equals(partial(c.objectId))) actual.delete(); throw error; }
        synchronized (this) {
            check(id, token); File target = object(c.objectId);
            if (!actual.equals(target)) DataFiles.move(actual, target);
            JSONObject next = DataFiles.copy(state);
            next.getJSONObject("objects").put(c.objectId, verified.put("modified", target.lastModified()).put("verifiedAt", System.currentTimeMillis()));
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
    public synchronized JSONObject settings(String id) throws Exception { return parameters(id).normalize(entry(id).getJSONObject("settings"), new JSONObject()); }
    public synchronized JSONObject saveSettings(String id, JSONObject changes) throws Exception {
        if (leases.containsKey(id)) throw new IllegalStateException("Model is in use; stop its task before changing settings");
        JSONObject effective = parameters(id).normalize(entry(id).getJSONObject("settings"), changes);
        JSONObject next = DataFiles.copy(state); next.getJSONObject("bundles").getJSONObject(id).put("settings", DataFiles.copy(effective.getJSONObject("values"))); persist(next); return effective;
    }
    public synchronized JSONArray snapshot() throws Exception {
        JSONArray result = new JSONArray(); JSONObject entries = state.getJSONObject("bundles");
        for (Iterator<String> it = entries.keys(); it.hasNext();) {
            String id = it.next(); JSONObject e = DataFiles.copy(entries.getJSONObject(id)); ModelBundle b = new ModelBundle(e.getJSONObject("manifest"));
            try { e.put("config", settings(id)).put("parameterSchema", parameters(id).json()); }
            catch (Exception unavailable) { e.put("config", b.parameters().normalize(e.getJSONObject("settings"), new JSONObject())).put("parameterSchema", b.parameters().json()).put("parameterError", unavailable.getMessage() == null ? "当前引擎无法解析此配方参数" : unavailable.getMessage()); }
            e.put("id", id).put("tags", b.tags()).put("plan", plan(id)).put("installed", e.optBoolean("installed") && complete(b, state)).put("inUse", leases.containsKey(id)).put("version", versionInfo(id)); result.put(e);
        }
        return result;
    }
    private static void validateVersions(JSONObject data) throws Exception {
        JSONObject groups = data.getJSONObject("versions"), entries = data.getJSONObject("bundles"); Set<String> seen = new HashSet<>();
        for (Iterator<String> it = groups.keys(); it.hasNext();) {
            String id = ModelBundle.key(it.next()); JSONObject group = groups.getJSONObject(id); JSONArray members = group.getJSONArray("members");
            boolean active = false;
            if (members.length() == 0 || group.getLong("generation") < 0 || group.getJSONArray("history").length() > 64) throw new IOException("Invalid model version history");
            for (int i = 0; i < members.length(); i++) {
                String member = ModelBundle.key(members.getString(i));
                if (!entries.has(member) || !seen.add(member)) throw new IOException("Invalid model version membership");
                active |= member.equals(group.getString("activeBundleId"));
            }
            if (!active || !group.getString("id").equals(id)) throw new IOException("Invalid active model version");
        }
        Set<String> pending = new HashSet<>();
        for (Iterator<String> it = groups.keys(); it.hasNext();) {
            JSONObject group = groups.getJSONObject(it.next()), update = group.optJSONObject("pending"); if (update == null) continue;
            String target = ModelBundle.key(update.getString("toBundleId")); boolean member = false;
            JSONArray members = group.getJSONArray("members"); for (int i = 0; i < members.length(); i++) member |= members.getString(i).equals(target);
            if (!update.getString("fromBundleId").equals(group.getString("activeBundleId")) || !entries.has(target) || !Protocol.isSha256(update.getString("review"))
                    || !Arrays.asList("copy", "keep").contains(update.getString("settingsMode")) || !pending.add(target) || seen.contains(target) && !member)
                throw new IOException("Invalid pending model update");
        }
    }
    private JSONObject versionGroup(String id) throws Exception {
        entry(id); JSONObject groups = state.getJSONObject("versions");
        for (Iterator<String> it = groups.keys(); it.hasNext();) {
            JSONObject group = groups.getJSONObject(it.next()); JSONArray members = group.getJSONArray("members");
            for (int i = 0; i < members.length(); i++) if (members.getString(i).equals(id)) return group;
            JSONObject pending = group.optJSONObject("pending"); if (pending != null && pending.getString("toBundleId").equals(id)) return group;
        }
        return null;
    }
    private JSONObject initialVersion(String id) throws Exception {
        return new JSONObject().put("id", id).put("activeBundleId", id).put("members", new JSONArray().put(id)).put("generation", 0).put("history", new JSONArray());
    }
    private JSONObject versionIdentity(JSONObject group) throws Exception {
        return new JSONObject().put("id", group.getString("id")).put("activeBundleId", group.getString("activeBundleId"))
                .put("members", group.getJSONArray("members")).put("generation", group.getLong("generation"));
    }
    /** Read-only preview; no network, transfer, manifest mutation or implicit activation. */
    public synchronized JSONObject planUpdate(String from, String to, String mode) throws Exception {
        ModelBundle source = bundle(from), target = bundle(to); JSONObject group = versionGroup(from), other = versionGroup(to);
        if (group == null) {
            if (!entry(from).optBoolean("installed") || !complete(source, state)) throw new IllegalStateException("Install the source model before its first version update");
            group = initialVersion(from);
        }
        if (!group.getString("activeBundleId").equals(from)) throw new IllegalStateException("Start updates from the current model version");
        if (other != null && !other.getString("id").equals(group.getString("id"))) throw new IllegalStateException("The target belongs to another model version history");
        return BundleUpdates.plan(source, target, settings(from).getJSONObject("values"), settings(to).getJSONObject("values"), versionIdentity(group), plan(to), mode, parameters(from), parameters(to));
    }
    private JSONObject reviewedUpdate(String from, String to, String mode, String review) throws Exception {
        JSONObject plan = planUpdate(from, to, mode);
        if (!Protocol.isSha256(review) || !review.equals(plan.getString("review"))) throw new IllegalStateException("Model settings or version selection changed; review the update again");
        JSONObject group = versionGroup(from), pending = group == null ? null : group.optJSONObject("pending");
        if (pending != null && (!pending.getString("toBundleId").equals(to) || !pending.getString("settingsMode").equals(mode) || !pending.getString("review").equals(review)))
            throw new IllegalStateException("Cancel the existing update plan before replacing it");
        return plan;
    }
    /** Persist the explicit choice; App startup will neither download nor activate it. */
    public synchronized JSONObject prepareUpdate(String from, String to, String mode, String review) throws Exception {
        JSONObject plan = reviewedUpdate(from, to, mode, review), old = versionGroup(from);
        JSONObject group = old == null ? initialVersion(from) : DataFiles.copy(old), next = DataFiles.copy(state);
        group.put("pending", new JSONObject().put("fromBundleId", from).put("toBundleId", to).put("settingsMode", mode).put("review", review).put("createdAt", System.currentTimeMillis()));
        next.getJSONObject("versions").put(group.getString("id"), group); persist(next); return plan;
    }
    public synchronized JSONObject pendingUpdate(String id) throws Exception {
        JSONObject group = versionGroup(id), pending = group == null ? null : group.optJSONObject("pending"); return pending == null ? null : DataFiles.copy(pending);
    }
    public synchronized void cancelUpdate(String id, String review) throws Exception {
        JSONObject old = versionGroup(id), pending = old == null ? null : old.optJSONObject("pending");
        if (pending == null || !pending.getString("review").equals(review)) throw new IllegalStateException("The update plan changed; reopen version management");
        JSONObject next = DataFiles.copy(state), group = next.getJSONObject("versions").getJSONObject(old.getString("id"));
        group.remove("pending"); group.put("generation", Math.addExact(group.getLong("generation"), 1)); persist(next);
    }
    /** One durable metadata commit switches preference/settings. Old files/settings and exact job IDs remain intact. */
    public synchronized JSONObject activateUpdate(String from, String to, String mode, String review) throws Exception {
        JSONObject plan = reviewedUpdate(from, to, mode, review);
        if (!entry(to).optBoolean("installed") || !complete(bundle(to), state)) throw new IllegalStateException("Download/import and verify every target component before activation");
        if (leases.containsKey(from) || leases.containsKey(to)) throw new IllegalStateException("Stop tasks using either version before activation");
        JSONObject existing = versionGroup(from), group = existing == null ? initialVersion(from) : DataFiles.copy(existing), next = DataFiles.copy(state);
        JSONArray members = group.getJSONArray("members"); boolean member = false;
        for (int i = 0; i < members.length(); i++) member |= members.getString(i).equals(to); if (!member) members.put(to);
        JSONArray history = group.getJSONArray("history"), retained = new JSONArray();
        for (int i = Math.max(0, history.length() - 63); i < history.length(); i++) retained.put(history.get(i));
        retained.put(new JSONObject().put("fromBundleId", from).put("toBundleId", to).put("settingsMode", mode).put("review", review).put("at", System.currentTimeMillis()));
        group.put("activeBundleId", to).put("generation", Math.addExact(group.getLong("generation"), 1)).put("history", retained); group.remove("pending");
        next.getJSONObject("versions").put(group.getString("id"), group);
        next.getJSONObject("bundles").getJSONObject(to).put("settings", plan.getJSONObject("settings").getJSONObject("values"));
        persist(next); return new JSONObject().put("bundleId", to).put("version", versionInfo(to)).put("settings", settings(to));
    }
    public synchronized JSONObject versionHistory(String id) throws Exception {
        JSONObject group = versionGroup(id); return group == null ? initialVersion(id) : DataFiles.copy(group);
    }
    private JSONObject versionInfo(String id) throws Exception {
        JSONObject group = versionGroup(id); if (group == null) return new JSONObject();
        JSONObject info = new JSONObject().put("groupId", group.getString("id")).put("activeBundleId", group.getString("activeBundleId"))
                .put("isActive", id.equals(group.getString("activeBundleId"))).put("members", new JSONArray(group.getJSONArray("members").toString())).put("historyCount", group.getJSONArray("history").length());
        JSONObject pending = group.optJSONObject("pending");
        if (pending != null) {
            JSONObject value = DataFiles.copy(pending); String target = pending.getString("toBundleId"); value.put("targetName", bundle(target).name).put("ready", plan(target).getBoolean("installed"));
            try { value.put("stale", !planUpdate(pending.getString("fromBundleId"), target, pending.getString("settingsMode")).getString("review").equals(pending.getString("review"))); }
            catch (Exception error) { value.put("stale", true).put("error", error.getMessage()); }
            info.put("pending", value);
        }
        return info;
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
        public JSONObject integrity() throws Exception {
            synchronized (BundleStore.this) {
                if (closed) throw new IOException("Model lease is closed"); JSONObject result = new JSONObject();
                for (ModelBundle.Component c : bundle.components) {
                    if (!hasObject(c)) throw new IOException("A leased component changed");
                    result.put(c.role, new JSONObject().put("algorithm", c.integrityAlgorithm).put("expectedSha256", c.sha256).put("expectedGitBlobSha1", c.gitBlobSha1).put("sha256", verifiedSha256(c, state)).put("bytes", c.bytes));
                }
                return result;
            }
        }
        public File file(String role) throws IOException { synchronized (BundleStore.this) { if (closed) throw new IOException("Model lease is closed"); return object(bundle.component(role).objectId); } }
        @Override public void close() { synchronized (BundleStore.this) { if (!closed) { closed = true; int n = leases.get(bundle.id) - 1; if (n == 0) leases.remove(bundle.id); else leases.put(bundle.id, n); } } }
    }
    /** Submit and delete share this monitor, so queued jobs keep their exact input versions. */
    public synchronized void remove(String id, boolean removeSettings, JobStore jobs) throws Exception {
        if (jobs != null && jobs.referencesBundle(id)) throw new IllegalStateException("Model is referenced by a queued/running task; cancel or finish it before deleting assets");
        remove(id, removeSettings);
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
            if (other.optBoolean("installed") || active) for (ModelBundle.Component c : new ModelBundle(other.getJSONObject("manifest")).components) keep.add(c.objectId);
        }
        ModelBundle b = new ModelBundle(e.getJSONObject("manifest"));
        for (ModelBundle.Component c : b.components) if (!keep.contains(c.objectId)) {
            ReentrantLock lock = componentLock(c.objectId);
            if (lock.tryLock()) { try { object(c.objectId).delete(); partial(c.objectId).delete(); } finally { lock.unlock(); } }
        }
    }
}
