package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Real filesystem/transfer failures with arbitrary bytes, never model execution. */
public final class BundleUpdateTest {
    private static int passed;
    private interface Action { void run() throws Exception; }
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); passed++; }
    private static void rejects(Action action, String message) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(message); }
    private static byte[] data(String text) throws Exception { return ("fixture bytes, not model weights: " + text).getBytes("UTF-8"); }
    private static JSONObject component(String role, String value) throws Exception {
        byte[] bytes = data(value);
        return new JSONObject().put("role", role).put("path", role + ".bin").put("format", "fixture_data").put("bytes", bytes.length)
                .put("sha256", Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(bytes)));
    }
    private static JSONObject field(String type, Object value) throws Exception { return new JSONObject().put("type", type).put("default", value); }
    private static JSONObject manifest(String id, boolean newer) throws Exception {
        JSONObject fields = new JSONObject().put("steps", field("integer", 4).put("minimum", 1).put("maximum", newer ? 8 : 20))
                .put("sampler", field("enum", "euler").put("values", newer ? new JSONArray().put("euler") : new JSONArray().put("euler").put("lcm")))
                .put("note", field("string", "new").put("maxLength", newer ? 4 : 32)).put("enabled", field("boolean", true))
                .put("width", field("integer", 512).put("minimum", 64).put("maximum", 768).put("multipleOf", 64))
                .put("height", field("integer", 512).put("minimum", 64).put("maximum", 768).put("multipleOf", 64))
                .put("changedType", field(newer ? "string" : "integer", newer ? "new" : 2));
        fields.put(newer ? "newField" : "removedField", field("integer", newer ? 7 : 3));
        JSONArray shapes = new JSONArray().put(new JSONObject().put("width", 512).put("height", 512))
                .put(new JSONObject().put("width", 768).put("height", newer ? 768 : 512));
        return new JSONObject().put("schema", ModelBundle.SCHEMA).put("id", id).put("modelId", id).put("name", id).put("recipeId", id + "_recipe")
                .put("engine", "fixture_engine").put("architecture", "fixture_arch").put("pipeline", "fixture_pipeline").put("backend", "cpu")
                .put("tasks", new JSONArray().put("image")).put("license", newer ? "target license" : "source license")
                .put("parameters", new JSONObject().put("fields", fields).put("allowedShapes", shapes))
                .put("components", new JSONArray().put(component("model", newer ? "new" : "old")).put(component("codec", "shared"))
                        .put(component(newer ? "added" : "removed", newer ? "added" : "removed")));
    }
    private static void install(BundleStore store, String id) throws Exception {
        String token = store.request(id); if (token.isEmpty()) return;
        for (ModelBundle.Component c : store.bundle(id).components) {
            if (store.hasObject(c)) continue;
            String content = c.role.equals("model") ? id.startsWith("new") ? "new" : "old" : c.role.equals("codec") ? "shared" : c.role;
            Files.write(store.partial(c.objectId).toPath(), data(content)); store.accept(id, token, c, store.partial(c.objectId));
        }
        store.install(id, token);
    }
    private static JSONObject row(JSONArray array, String field, String expected) throws Exception {
        for (int i = 0; i < array.length(); i++) if (array.getJSONObject(i).getString(field).equals(expected)) return array.getJSONObject(i);
        throw new AssertionError("Missing " + expected);
    }
    private static JSONObject version(BundleStore store, String id) throws Exception { return row(store.snapshot(), "id", id).getJSONObject("version"); }
    private static void activate(BundleStore store, JSONObject p) throws Exception { store.activateUpdate(p.getString("fromBundleId"), p.getString("toBundleId"), p.getString("settingsMode"), p.getString("review")); }
    public static int run(File root) throws Exception {
        File dir = new File(root, "versioned-assets"); BundleStore initial = new BundleStore(dir);
        ModelBundle old = new ModelBundle(manifest("old_v1", false)), newer = new ModelBundle(manifest("new_v2", true));
        initial.declare(old); initial.declare(newer); install(initial, old.id);
        JSONObject savedProfile = initial.saveSettings(old.id, new JSONObject().put("steps", 18).put("sampler", "lcm").put("note", "old model note").put("width", 768));
        savedProfile.getJSONObject("values").put("steps", 1);
        check(initial.settings(old.id).getJSONObject("values").getInt("steps") == 18, "Editing a returned save result cannot mutate persisted model settings");
        initial.saveSettings(newer.id, new JSONObject().put("steps", 6));
        JSONObject preview = initial.planUpdate(old.id, newer.id, "copy"); String review = preview.getString("review");
        check(!initial.plan(newer.id).getBoolean("installed") && !row(initial.snapshot(), "id", newer.id).has("transfer"), "Reviewing versions never creates transfers or installs assets");
        check(preview.getJSONObject("download").getLong("reusableBytes") == newer.component("codec").bytes, "Preview discloses verified shared assets");
        JSONArray diffs = preview.getJSONArray("components");
        check(row(diffs, "role", "model").getString("change").equals("changed"), "Changed weight content is disclosed");
        check(row(diffs, "role", "codec").getString("change").equals("unchanged"), "Identical component is disclosed");
        check(row(diffs, "role", "added").getString("change").equals("added") && row(diffs, "role", "removed").getString("change").equals("removed"), "Added and removed components are separate");
        JSONArray params = preview.getJSONObject("settings").getJSONArray("changes");
        check(row(params, "field", "steps").getInt("to") == 8 && row(params, "field", "steps").getString("reason").equals("clamped"), "Old values clamp to the new model limits");
        check(row(params, "field", "sampler").getString("reason").equals("selection_reset"), "Removed enum options reset with disclosure");
        check(row(params, "field", "note").getString("reason").equals("length_reset"), "New text length limits disclose a default reset");
        check(row(params, "field", "changedType").getString("reason").equals("type_reset"), "Incompatible types are not blindly copied");
        check(row(params, "field", "removedField").isNull("to") && row(params, "field", "newField").getInt("to") == 7, "Removed/new parameters retain explicit migration reasons");
        check(row(params, "field", "width").getString("reason").equals("joint_shape_reset") && preview.getJSONObject("settings").getJSONObject("values").getInt("width") == 512, "Individually valid dimensions still respect complete compiled shapes");
        check(initial.planUpdate(old.id, newer.id, "keep").getJSONObject("settings").getJSONObject("values").getInt("steps") == 6, "Users can retain target version settings instead of migrating");
        rejects(() -> initial.planUpdate(old.id, old.id, "copy"), "A version update needs a distinct manifest");
        rejects(() -> initial.planUpdate(old.id, newer.id, "automatic"), "Unknown settings policies fail locally");
        rejects(() -> initial.activateUpdate(old.id, newer.id, "copy", review), "Incomplete target cannot replace the installed model");
        rejects(() -> initial.prepareUpdate(old.id, newer.id, "copy", String.join("", Collections.nCopies(64, "0"))), "Unreviewed changes cannot be prepared");
        for (String key : Arrays.asList("engine", "architecture", "pipeline", "backend")) {
            JSONObject different = manifest("other_" + key, true).put(key, "different"); ModelBundle b = new ModelBundle(different); initial.declare(b);
            rejects(() -> initial.planUpdate(old.id, b.id, "copy"), "An update cannot silently change " + key);
        }
        ModelBundle otherTask = new ModelBundle(manifest("other_task", true).put("tasks", new JSONArray().put("audio"))); initial.declare(otherTask);
        rejects(() -> initial.planUpdate(old.id, otherTask.id, "copy"), "Task capabilities do not change implicitly");
        initial.prepareUpdate(old.id, newer.id, "copy", review);
        check(!row(initial.snapshot(), "id", newer.id).has("transfer") && version(initial, old.id).getBoolean("isActive"), "Preparing an update alone keeps the old version and starts no download");
        initial.request(newer.id); // Simulate process death with a pending transfer.
        BundleStore store = new BundleStore(dir);
        check(store.pendingUpdate(old.id).getString("toBundleId").equals(newer.id) && row(store.snapshot(), "id", newer.id).getJSONObject("transfer").getString("state").equals("paused"), "Restart preserves the plan but requires explicit transfer resume");
        check(store.planUpdate(old.id, newer.id, "copy").getString("review").equals(review), "Transfer status changes do not invalidate a reviewed asset/config selection");
        AtomicInteger network = new AtomicInteger(), failures = new AtomicInteger();
        BundleTransfers transfers = new BundleTransfers(store, (c, offset, observer) -> { network.incrementAndGet(); throw new IOException("No implicit network allowed"); }, new BundleTransfers.Listener() {
            public void changed() {} public void installed(String id) {} public void failed(String id, String message) { failures.incrementAndGet(); }
        });
        try {
            Map<String, BundleTransfers.Input> imports = new HashMap<>(); imports.put("model", () -> new ByteArrayInputStream(data("bad"))); imports.put("added", () -> new ByteArrayInputStream(data("added")));
            transfers.importFiles(newer.id, imports); check(transfers.awaitIdle(5, TimeUnit.SECONDS), "Corrupt imports terminate without blocking the queue");
            check(failures.get() == 1 && !store.plan(newer.id).getBoolean("installed") && store.plan(old.id).getBoolean("installed"), "Failed verification preserves the old installed model");
            check(version(store, old.id).getString("activeBundleId").equals(old.id) && store.settings(old.id).getJSONObject("values").getInt("steps") == 18, "Failed updates preserve current version and parameters");
            check(network.get() == 0, "Imported failure never falls back to network");
            imports.put("model", () -> new ByteArrayInputStream(data("new"))); transfers.importFiles(newer.id, imports);
            check(transfers.awaitIdle(5, TimeUnit.SECONDS) && store.plan(newer.id).getBoolean("installed"), "Explicit import installs all verified target assets");
            check(version(store, old.id).getString("activeBundleId").equals(old.id), "Successful installation alone does not activate the update");
        } finally { transfers.close(); }
        try (BundleStore.Lease lease = store.acquire(old.id)) { rejects(() -> activate(store, preview), "Activation cannot race a running task lease"); }
        File blocked = new File(dir, "bundles.json.pending"); check(blocked.mkdir(), "Metadata failure fixture is isolated under the test workspace");
        try { rejects(() -> activate(store, preview), "A metadata write failure cannot partially activate an update"); }
        finally { Files.delete(blocked.toPath()); }
        check(version(store, old.id).getString("activeBundleId").equals(old.id) && store.settings(newer.id).getJSONObject("values").getInt("steps") == 6, "Failed durable commit leaves target settings and active pointer untouched");
        JobStore jobs = new JobStore(new File(root, "versioned-jobs"));
        JSONObject request = new JSONObject().put("type", "image.generate").put("bundleId", old.id).put("input", new JSONObject().put("prompt", "old task"))
                .put("parameters", new JSONObject().put("steps", 18));
        JSONObject queued = jobs.submit(request, "version-queue");
        activate(store, preview);
        check(version(store, newer.id).getBoolean("isActive") && !version(store, newer.id).has("pending"), "Explicit activation changes the pointer and clears the update plan atomically");
        check(store.settings(newer.id).getJSONObject("values").getInt("steps") == 8 && store.settings(old.id).getJSONObject("values").getInt("steps") == 18, "Migration applies only to the target; old settings remain available for rollback");
        check(DataFiles.canonical(jobs.get(queued.getString("id")).getJSONObject("request")).equals(DataFiles.canonical(request)), "Activation preserves queued fixed-version task requests");
        check(store.plan(old.id).getBoolean("installed") && store.object(old.component("model").objectId).isFile(), "Activation retains old asset bytes");
        check(store.bundle(newer.id).json().getString("license").equals("target license") && store.bundle(old.id).id.equals(old.id), "Target attribution and immutable source identities remain separate");
        rejects(() -> activate(store, preview), "A stale activation cannot replay over the current version");
        rejects(() -> store.remove(old.id, false, jobs), "Queued fixed-version jobs protect old assets from deletion");
        jobs.cancel(queued.getString("id")); store.remove(old.id, false, jobs);
        check(!store.plan(old.id).getBoolean("installed") && store.hasObject(newer.component("codec")) && store.plan(newer.id).getBoolean("installed"), "Explicit cleanup of old assets retains shared objects and the new model");
        JSONObject rollback = store.planUpdate(newer.id, old.id, "keep");
        rejects(() -> activate(store, rollback), "Rollback needs the selected old assets to be restored explicitly");
        install(store, old.id); activate(store, rollback);
        check(store.settings(old.id).getJSONObject("values").getInt("steps") == 18 && store.settings(newer.id).getJSONObject("values").getInt("steps") == 8, "Rollback can preserve both independent version profiles");
        BundleStore reopened = new BundleStore(dir);
        check(version(reopened, old.id).getBoolean("isActive") && reopened.versionHistory(old.id).getJSONArray("history").length() == 2, "Current version and explicit switch history survive reopening");
        JSONObject publicVersion = version(reopened, old.id); publicVersion.getJSONArray("members").put("not_declared");
        check(reopened.versionHistory(old.id).getJSONArray("members").length() == 2, "Editing a public version snapshot cannot corrupt internal immutable membership");
        JSONObject pending = reopened.planUpdate(old.id, newer.id, "keep"); reopened.prepareUpdate(old.id, newer.id, "keep", pending.getString("review"));
        reopened.saveSettings(old.id, new JSONObject().put("steps", 17));
        check(version(reopened, old.id).getJSONObject("pending").getBoolean("stale"), "Settings changes visibly invalidate an old review");
        rejects(() -> activate(reopened, pending), "Stale migration consent cannot overwrite updated settings");
        rejects(() -> reopened.cancelUpdate(old.id, String.join("", Collections.nCopies(64, "0"))), "Stale cancellation cannot clear a newer plan");
        reopened.cancelUpdate(old.id, pending.getString("review"));
        check(reopened.pendingUpdate(old.id) == null && reopened.plan(old.id).getBoolean("installed") && reopened.plan(newer.id).getBoolean("installed"), "Cancelling a plan retains both installed asset sets");
        JSONObject fresh = reopened.planUpdate(old.id, newer.id, "keep");
        check(!fresh.getString("review").equals(pending.getString("review")), "Cancelled plan fingerprints cannot be reused");
        rejects(() -> reopened.prepareUpdate(old.id, newer.id, "keep", pending.getString("review")), "Expired consent cannot restart a cancelled plan");
        try (BundleStore.Lease lease = reopened.acquire(newer.id)) { rejects(() -> activate(reopened, fresh), "An active target lease also prevents profile replacement"); }
        reopened.saveSettings(newer.id, new JSONObject().put("steps", 7));
        rejects(() -> activate(reopened, fresh), "Target profile edits also invalidate earlier consent");
        check(reopened.settings(newer.id).getJSONObject("values").getInt("steps") == 7, "A rejected stale review preserves edited target values");
        ModelBundle origin = new ModelBundle(manifest("other_origin", false)), otherVersion = new ModelBundle(manifest("new_other", true));
        reopened.declare(origin); reopened.declare(otherVersion); install(reopened, origin.id); install(reopened, otherVersion.id);
        JSONObject otherPlan = reopened.planUpdate(origin.id, otherVersion.id, "keep"); activate(reopened, otherPlan);
        rejects(() -> reopened.planUpdate(old.id, otherVersion.id, "copy"), "A user update cannot merge two independent model histories");
        ModelBundle loraA = new ModelBundle(AdapterTest.manifest("version_lora_a", "sd15", true));
        JSONObject restricted = AdapterTest.manifest("version_lora_b", "sd15", true); restricted.getJSONObject("adapter").put("baseModelIds", new JSONArray().put("specific_base"));
        ModelBundle loraB = new ModelBundle(restricted);
        rejects(() -> BundleUpdates.compatible(loraA, loraB), "Changed LoRA base constraints require independent registration rather than silently migrating a pairing");
        JSONObject sourceMetadata = manifest("metadata_target", true); sourceMetadata.getJSONArray("components").getJSONObject(1).put("repository", "fixture/codec").put("revision", String.join("", Collections.nCopies(40, "a")));
        ModelBundle metadataTarget = new ModelBundle(sourceMetadata);
        JSONObject metadataPlan = BundleUpdates.plan(newer, metadataTarget, reopened.settings(newer.id).getJSONObject("values"), new JSONObject(), new JSONObject(), new JSONObject(), "copy");
        check(row(metadataPlan.getJSONArray("components"), "role", "codec").getString("change").equals("source_changed"), "Equal bytes with changed provenance are disclosed separately");
        reopened.remove(old.id, false, jobs);
        JSONObject missingCurrent = reopened.planUpdate(old.id, newer.id, "keep"); activate(reopened, missingCurrent);
        check(version(reopened, newer.id).getBoolean("isActive") && !reopened.plan(old.id).getBoolean("installed"), "An explicitly deleted current asset can switch to an already installed retained version without downloads");
        File corruptDir = new File(root, "invalid-version-metadata"); check(corruptDir.mkdir(), "Corrupt metadata fixture stays isolated");
        JSONObject damaged = new JSONObject(new String(Files.readAllBytes(new File(dir, "bundles.json").toPath()), "UTF-8"));
        damaged.getJSONObject("versions").getJSONObject(old.id).put("activeBundleId", "missing_member");
        Files.write(new File(corruptDir, "bundles.json").toPath(), damaged.toString().getBytes("UTF-8"));
        rejects(() -> new BundleStore(corruptDir), "Corrupt version pointers fail without silently resetting a user's history");
        return passed;
    }
}
