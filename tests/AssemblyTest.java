package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Production association/storage contracts. Fixture data supplies no inference evidence. */
public final class AssemblyTest {
    static int checks;
    static String repeat(char value, int count) { char[] data = new char[count]; Arrays.fill(data, value); return new String(data); }
    interface Action { void run() throws Exception; }
    static void check(boolean ok, String message) { checks++; if (!ok) throw new AssertionError(message); }
    static void rejects(Action action, String message) throws Exception { boolean failed = false; try { action.run(); } catch (Exception expected) { failed = true; } check(failed, message); }
    static JSONObject descriptor(ModelBundle source, PreparationPlan plan, ModelBundle target) throws Exception {
        JSONArray roles = new JSONArray();
        for (PreparationPlan.Stage stage : plan.stages) for (PreparationPlan.Output output : stage.outputs) roles.put(new JSONObject().put("source", output.role).put("target", output.role));
        return new JSONObject().put("schema", "lma.model-assembly/1").put("id", "fixture_assembly").put("name", "User-selected association")
                .put("sourceBundleId", source.id).put("preparationId", plan.id).put("bundleId", target.id).put("roles", roles);
    }
    static JSONObject request(AssemblyPlan plan, JSONObject prepared) throws Exception {
        return new JSONObject().put("type", "model.assemble").put("bundleId", plan.bundleId).put("preparedAssetsId", prepared.getString("id"))
                .put("assemblyId", plan.id).put("assemblyFingerprint", plan.fingerprint);
    }
    static JSONObject run(AssemblyPlan plan, PreparedAssets prepared, BundleStore bundles, JSONObject raw, JobStore jobs, boolean cancelAfter) throws Exception {
        JSONObject input = TaskInput.validate(raw).put("assemblySourceFingerprint", TaskInput.fingerprint(prepared.record(raw.getString("preparedAssetsId"))));
        JSONObject submitted = jobs.submit(input, ""), job = jobs.claimNext();
        check(job.getString("id").equals(submitted.getString("id")), "Association uses the ordinary persistent job queue");
        String id = job.getString("id"), token = job.getString("token");
        PreparedModelAssembly.Context context = new PreparedModelAssembly.Context() {
            public void check() throws IOException { jobs.check(id, token); }
            public void progress(String stage) throws Exception { check(); jobs.progress(id, token, stage, null); }
        };
        JSONObject result = PreparedModelAssembly.run(plan, prepared, bundles, input, id, context);
        rejects(() -> jobs.finishAssembly(id, token, DataFiles.copy(result).put("sourceFingerprint", repeat('0', 64)), ""), "Mismatched source receipt cannot complete a task");
        if (cancelAfter) jobs.cancel(id);
        jobs.finishAssembly(id, token, result, "");
        check(jobs.get(id).getString("state").equals(cancelAfter ? "cancelled" : "succeeded"), "Cancellation wins over late completion");
        check(jobs.get(id).getJSONArray("artifacts").length() == 0, "Association never fabricates a generated media artifact");
        rejects(() -> jobs.finishAssembly(id, token, result, ""), "Stale tokens cannot complete a second time");
        return result;
    }
    static void contracts(File root) throws Exception {
        PreparationPlan preparation = PreparationTest.fixturePlan(); ModelBundle source = PreparationTest.fixtureBundle(preparation);
        byte[] dependency = "explicit user dependency".getBytes("UTF-8");
        JSONObject mapped = new JSONObject().put("role", "diffusion_model").put("path", "prepared.data").put("format", "bin").put("bytes", PreparationTest.OUTPUT.length).put("sha256", PreparationTest.sha(PreparationTest.OUTPUT));
        JSONObject remaining = new JSONObject().put("role", "text_encoder").put("path", "encoder.data").put("format", "bin").put("bytes", dependency.length).put("sha256", PreparationTest.sha(dependency))
                .put("repository", "example/fixture").put("revision", repeat('a', 40)).put("url", "https://huggingface.co/example/fixture/resolve/" + repeat('a', 40) + "/encoder.data");
        ModelBundle target = new ModelBundle(source.json().put("id", "fixture_runtime").put("components", new JSONArray().put(mapped).put(remaining))
                .put("parameters", new JSONObject().put("fields", new JSONObject().put("steps", new JSONObject().put("type", "integer").put("default", 20).put("minimum", 1).put("maximum", 100)))));
        JSONObject signed = descriptor(source, preparation, target); AssemblyPlan plan = new AssemblyPlan(signed, preparation, target);
        check(plan.describe(target).getLong("linkedBytes") == PreparationTest.OUTPUT.length, "The review discloses the exact local bytes reused");
        check(plan.describe(target).getJSONArray("remainingComponents").getJSONObject(0).getString("role").equals("text_encoder"), "The review discloses each remaining explicit dependency");
        rejects(() -> new AssemblyPlan(DataFiles.copy(signed).put("url", "https://example.invalid/code"), preparation, target), "Assembly descriptors cannot select external code or URLs");
        rejects(() -> new AssemblyPlan(DataFiles.copy(signed).put("roles", new JSONArray().put(new JSONObject().put("source", "diffusion_model").put("target", "text_encoder"))), preparation, target), "Role swaps cannot bind different trained bytes");
        rejects(() -> new AssemblyPlan(DataFiles.copy(signed).put("roles", new JSONArray().put(signed.getJSONArray("roles").getJSONObject(0)).put(signed.getJSONArray("roles").getJSONObject(0))), preparation, target), "Duplicate association roles fail");
        rejects(() -> new AssemblyPlan(DataFiles.copy(signed).put("sourceBundleId", target.id), preparation, target), "Source and runtime manifests remain independent");
        ModelBundle changed = new ModelBundle(target.json().put("description", "Changed signed manifest"));
        check(!new AssemblyPlan(signed, preparation, changed).fingerprint.equals(plan.fingerprint), "The runtime manifest is bound into the on-device plan identity");
        JobStore jobs = new JobStore(new File(root, "jobs")); BundleStore bundles = new BundleStore(new File(root, "bundles")); bundles.declare(target);
        bundles.saveSettings(target.id, new JSONObject().put("steps", 37));
        File preparedRoot = new File(root, "prepared"); String preparedId;
        try (PreparedAssets prepared = new PreparedAssets(preparedRoot)) {
            JSONObject record;
            try (PreparedAssets.Session session = prepared.begin("fixture_preparation")) { PreparationTest.outputs(session, preparation); record = session.commit(preparation, source.id, () -> {}); }
            preparedId = record.getString("id"); JSONObject raw = request(plan, record);
            check(TaskInput.validate(raw).length() == 5, "Clients select only signed plan/model/record IDs");
            for (String field : Arrays.asList("input", "parameters", "path", "url", "assemblySourceFingerprint")) rejects(() -> TaskInput.validate(DataFiles.copy(raw).put(field, "unexpected")), "Client-injected " + field + " fails");
            rejects(() -> TaskInput.validate(DataFiles.copy(raw).put("preparedAssetsId", "../outside")), "Prepared IDs cannot select paths");
            rejects(() -> plan.matches(DataFiles.copy(record).put("planFingerprint", repeat('0', 64)), target), "Mismatched preparation identity fails");
            rejects(() -> plan.matches(record, changed), "Changed runtime identity fails");
            JSONObject queued = jobs.submit(DataFiles.copy(raw).put("assemblySourceFingerprint", TaskInput.fingerprint(record)), "queued-assembly");
            check(jobs.referencesPrepared(preparedId), "Queued tasks protect their prepared source");
            rejects(() -> prepared.remove(preparedId, jobs), "Queued source deletion fails");
            rejects(() -> bundles.remove(target.id, false, jobs), "Queued target deletion fails");
            jobs.cancel(queued.getString("id")); check(!jobs.referencesPrepared(preparedId), "Cancellation releases queued source references");
            try (PreparedAssets.Lease lease = prepared.acquire(preparedId, () -> {})) {
                rejects(() -> prepared.remove(preparedId, jobs), "Active leases protect source files");
                File file = lease.file("diffusion_model"); long stamp = file.lastModified();
                Files.write(file.toPath(), new byte[PreparationTest.OUTPUT.length]); file.setLastModified(stamp);
                rejects(() -> prepared.acquire(preparedId, () -> {}), "Same-size same-time tampering is detected by full SHA verification");
                Files.write(file.toPath(), PreparationTest.OUTPUT); file.setLastModified(stamp);
                Map<String,File> map = Collections.singletonMap("diffusion_model", file);
                rejects(() -> bundles.adoptLocal(target, map, new JSONObject(), () -> {}), "Legacy complete adoption still requires all components");
                rejects(() -> bundles.adoptAvailableLocal(target, Collections.emptyMap(), new JSONObject(), () -> {}), "Empty partial adoption fails");
                rejects(() -> bundles.adoptAvailableLocal(target, Collections.singletonMap("unknown", file), new JSONObject(), () -> {}), "Undeclared component roles fail");
                AtomicInteger ticks = new AtomicInteger();
                rejects(() -> bundles.adoptAvailableLocal(target, map, new JSONObject(), () -> { if (ticks.incrementAndGet() >= 2) throw new IOException("cancel during SHA"); }), "Cancellation interrupts verification");
                check(!bundles.plan(target.id).getBoolean("installed") && bundles.plan(target.id).getLong("reusableBytes") == 0, "Cancelled staging is never advertised as an installed model");
            }
            JSONObject result = run(plan, prepared, bundles, raw, jobs, false);
            check(!result.getBoolean("installed") && result.getLong("remainingBytes") == dependency.length, "Only verified local components are associated");
            check(bundles.record(target.id).getJSONObject("transfer").getString("state").equals("paused"), "Missing user dependencies stay paused without transfer tokens");
            check(bundles.settings(target.id).getJSONObject("values").getInt("steps") == 37, "Association preserves per-model user settings");
            rejects(() -> bundles.acquire(target.id), "A partially associated model cannot be loaded");
            File dependencyFile = new File(root, "user-selected-encoder.data"); PreparationTest.write(dependencyFile, dependency);
            bundles.adoptAvailableLocal(target, Collections.singletonMap("text_encoder", dependencyFile), new JSONObject(), () -> {});
            try (PreparedAssets.Lease from = prepared.acquire(preparedId, () -> {}); BundleStore.Lease to = bundles.acquire(target.id)) {
                check(Files.isSameFile(from.file("diffusion_model").toPath(), to.file("diffusion_model").toPath()), "Source and runtime records share verified hardlinks without copying bytes");
            }
            bundles.remove(target.id, false, jobs); check(prepared.snapshot(source.id).getJSONObject(0).getBoolean("available"), "Deleting the runtime model preserves the independently owned preparation");
            bundles.declare(target); run(plan, prepared, bundles, raw, jobs, true);
            check(!bundles.plan(target.id).getBoolean("installed"), "Late cancellation preserves only paused verified associations");
            bundles.adoptAvailableLocal(target, Collections.singletonMap("text_encoder", dependencyFile), new JSONObject(), () -> {});
            prepared.remove(preparedId, jobs);
            try (BundleStore.Lease to = bundles.acquire(target.id)) { check(Arrays.equals(Files.readAllBytes(to.file("diffusion_model").toPath()), PreparationTest.OUTPUT), "Deleting prepared data preserves the runtime owner's hardlink"); }
        }
        BundleStore restarted = new BundleStore(new File(root, "bundles")); check(restarted.plan(target.id).getBoolean("installed"), "Restart retains explicitly completed user assets");
        try (PreparedAssets prepared = new PreparedAssets(preparedRoot)) { check(prepared.snapshot(source.id).length() == 0, "Restart preserves independent prepared-data deletion"); }
    }
    static void trained(String[] args) throws Exception {
        File root = new File(args[1]), preparedRoot = new File(args[2]);
        PreparationPlan preparation = new PreparationPlan(PreparationTest.json(new File(args[3])).getJSONArray("plans").getJSONObject(0));
        JSONArray bundlesJson = PreparationTest.json(new File(args[4])).getJSONArray("bundles"); ModelBundle target = null;
        JSONObject descriptor = PreparationTest.json(new File(args[5])).getJSONArray("plans").getJSONObject(0);
        for (int i = 0; i < bundlesJson.length(); i++) if (bundlesJson.getJSONObject(i).getString("id").equals(descriptor.getString("bundleId"))) target = new ModelBundle(bundlesJson.getJSONObject(i));
        AssemblyPlan plan = new AssemblyPlan(descriptor, preparation, target); BundleStore bundles = new BundleStore(new File(root, "runtime-assets")); bundles.declare(target);
        JobStore jobs = new JobStore(new File(root, "jobs"));
        try (PreparedAssets prepared = new PreparedAssets(preparedRoot)) {
            JSONObject record = prepared.snapshot(plan.sourceBundleId).getJSONObject(0), raw = request(plan, record), result = run(plan, prepared, bundles, raw, jobs, false);
            JSONArray files = bundles.plan(target.id).getJSONArray("components"); int count = 0;
            try (PreparedAssets.Lease source = prepared.acquire(record.getString("id"), () -> {})) {
                for (int i = 0; i < files.length(); i++) { JSONObject file = files.getJSONObject(i); if (!file.getBoolean("reusable")) continue; count++;
                    File object = new File(root, "runtime-assets/objects/" + target.component(file.getString("role")).objectId);
                    check(Files.isSameFile(source.file(file.getString("role")).toPath(), object.toPath()), "Actual trained output is a shared hardlink");
                }
            }
            check(count == 20 && !result.getBoolean("installed"), "Exactly 20 actual trained components are reused; T5 remains uninstalled");
            check(result.getLong("linkedBytes") == 6061184991L && result.getLong("remainingBytes") == 3386858497L, "Actual bytes and remaining T5 dependencies match signed manifests");
            check(bundles.record(target.id).getJSONObject("transfer").getString("state").equals("paused"), "Actual runtime entry remains paused");
            result.put("assemblyFingerprint", plan.fingerprint).put("bundleFingerprint", plan.bundleFingerprint).put("hardlinksVerified", count).put("sourceRetained", true);
            PreparationTest.write(new File(root, "trained-result.json"), result.toString(2).getBytes("UTF-8"));
        }
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("--trained")) trained(args); else contracts(new File(args[0]));
        System.out.println(new JSONObject().put("passed", true).put("checks", checks).put("actualTrainedAssociations", args[0].equals("--trained") ? 1 : 0).put("modelInference", false).put("physicalAndroid", false));
    }
}
