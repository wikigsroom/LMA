package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.*;

/** Host production-core lifecycle contracts. Fixture bytes are never inference evidence. */
public final class PreparationTest {
    interface Action { void run() throws Exception; }
    static int checks, fixtureChildren, trainedChildren;
    static final byte[] SOURCE = "user-checkpoint\n".getBytes(StandardCharsets.UTF_8), OUTPUT = "derived-user-data\n".getBytes(StandardCharsets.UTF_8);
    static void check(boolean ok, String message) { checks++; if (!ok) throw new AssertionError(message); }
    static void rejects(Action action, String message) throws Exception { boolean failed = false; try { action.run(); } catch (Exception expected) { failed = true; } check(failed, message); }
    static String sha(byte[] bytes) throws Exception { return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    static void write(File file, byte[] bytes) throws Exception { Files.createDirectories(file.getParentFile().toPath()); Files.write(file.toPath(), bytes); }
    static JSONObject json(File file) throws Exception { return new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8)); }
    static PreparationPlan fixturePlan() throws Exception {
        JSONObject output = new JSONObject().put("file", "prepared.data").put("role", "diffusion_model").put("bytes", OUTPUT.length).put("sha256", sha(OUTPUT));
        JSONObject stage = new JSONObject().put("id", "prepare").put("module", "fixture").put("operation", "convert").put("receipt", "preparation.json").put("receiptSchema", "lma.fixture-preparation/1").put("outputs", new JSONArray().put(output)).put("graphs", new JSONArray());
        return new PreparationPlan(new JSONObject().put("schema", "lma.asset-preparation/1").put("id", "fixture_v1").put("name", "Fixture preparation").put("sourceRole", "checkpoint").put("sourceSha256", sha(SOURCE)).put("sourceBytes", SOURCE.length).put("stages", new JSONArray().put(stage)));
    }
    static ModelBundle fixtureBundle(PreparationPlan plan) throws Exception {
        JSONObject component = new JSONObject().put("role", "checkpoint").put("path", "checkpoint.bin").put("format", "safetensors").put("sha256", plan.sourceSha256).put("bytes", plan.sourceBytes).put("url", "https://huggingface.co/example/fixture/resolve/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/checkpoint.bin").put("repository", "example/fixture").put("revision", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
        return new ModelBundle(new JSONObject().put("schema", "lma.model-bundle/1").put("id", "fixture_source").put("modelId", "fixture_model").put("recipeId", "source_v1").put("name", "Structural fixture").put("engine", "fixture").put("architecture", "fixture").put("pipeline", "source_v1").put("backend", "cpu").put("tasks", new JSONArray().put("video")).put("parameters", new JSONObject().put("version", 1).put("fields", new JSONObject())).put("components", new JSONArray().put(component)));
    }
    static JSONObject receipt(PreparationPlan plan, String schema) throws Exception { return new JSONObject().put("schema", schema).put("ok", true).put("source_sha256_verified", true).put("source_sha256", plan.sourceSha256).put("source_bytes", plan.sourceBytes); }
    static void outputs(PreparedAssets.Session session, PreparationPlan plan) throws Exception {
        write(new File(session.directory, "prepare/prepared.data"), OUTPUT);
        write(new File(session.directory, "prepare/preparation.json"), receipt(plan, "lma.fixture-preparation/1").toString().getBytes(StandardCharsets.UTF_8));
    }
    static JSONObject request(ModelBundle bundle, PreparationPlan plan) throws Exception { return new JSONObject().put("type", "model.prepare").put("bundleId", bundle.id).put("preparationId", plan.id).put("planFingerprint", plan.fingerprint); }
    static File java() { return new File(new File(System.getProperty("java.home"), "bin"), System.getProperty("os.name").startsWith("Windows") ? "java.exe" : "java"); }
    static void fixtureWorker(String requestFile, String mode) throws Exception {
        JSONObject command = json(new File(requestFile)); File root = new File(command.getString("storage_root"), command.getString("output_name"));
        if (mode.equals("oversized")) { char[] bytes = new char[1024 * 1024 + 1]; Arrays.fill(bytes, 'x'); System.out.println(new String(bytes)); return; }
        System.out.println(new JSONObject().put("phase", "convert").put("bytes", 1).put("total_bytes", 2)); System.out.flush();
        if (mode.equals("cancel")) { Thread.sleep(30000); return; }
        File source = new File(command.getString("checkpoint")); byte[] actual = Files.readAllBytes(source.toPath());
        if (actual.length != command.getLong("expected_source_bytes") || !sha(actual).equals(command.getString("expected_source_sha256"))) throw new IOException("Source changed");
        Files.createDirectory(root.toPath());
        JSONObject record = new JSONObject().put("schema", "lma.fixture-preparation/1").put("ok", true).put("source_sha256_verified", true).put("source_sha256", sha(actual)).put("source_bytes", actual.length);
        write(new File(root, "preparation.json"), record.toString().getBytes(StandardCharsets.UTF_8));
        if (!mode.equals("missing")) write(new File(root, "prepared.data"), OUTPUT);
        System.out.println(record);
    }
    static void contracts(File root) throws Exception {
        PreparationPlan plan = fixturePlan(); ModelBundle bundle = fixtureBundle(plan); File source = new File(root, "source.bin"); write(source, SOURCE);
        check(plan.matches(bundle), "Exact source identity selects a preparation plan");
        check(plan.fingerprint.equals(new PreparationPlan(new JSONObject(plan.json().toString())).fingerprint), "Plan identity survives persistence");
        JSONObject wrong = plan.json(); wrong.put("sourceSha256", "bad"); rejects(() -> new PreparationPlan(wrong), "Malformed source digest rejected");
        JSONObject duplicate = plan.json(); duplicate.getJSONArray("stages").put(duplicate.getJSONArray("stages").getJSONObject(0)); rejects(() -> new PreparationPlan(duplicate), "Duplicate stages rejected");
        JSONObject traversal = plan.json(); traversal.getJSONArray("stages").getJSONObject(0).getJSONArray("outputs").getJSONObject(0).put("file", "../source.bin"); rejects(() -> new PreparationPlan(traversal), "Output traversal rejected");
        JSONObject request = request(bundle, plan); check(TaskInput.validate(request).getString("type").equals("model.prepare"), "Preparation has its own strict task contract");
        for (String field : Arrays.asList("checkpoint", "url", "module", "parameters", "input")) { JSONObject bad = DataFiles.copy(request).put(field, "untrusted"); rejects(() -> TaskInput.validate(bad), "Client cannot supply " + field); }
        BundleStore bundles = new BundleStore(new File(root, "bundles")); bundles.declare(bundle);
        bundles.adoptLocal(bundle, Collections.singletonMap("checkpoint", source), new JSONObject(), () -> {});
        JobStore jobs = new JobStore(new File(root, "jobs")); JSONObject job = jobs.submit(request, "prep-key");
        check(jobs.submit(request, "prep-key").getString("id").equals(job.getString("id")), "Idempotent preparation reuses the task");
        rejects(() -> bundles.remove(bundle.id, false, jobs), "Queued preparation retains its source bundle");
        JSONObject active = jobs.claimNext(); String jobId = active.getString("id"), token = active.getString("token");
        File preparedRoot = new File(root, "prepared"); String committedId;
        try (PreparedAssets store = new PreparedAssets(preparedRoot)) {
            rejects(() -> new PreparedAssets(preparedRoot), "A second owner cannot recover live workspaces");
            try (PreparedAssets.Session session = store.begin(jobId)) {
                outputs(session, plan); write(new File(session.directory, "prepare/prepared.data"), new byte[OUTPUT.length]);
                rejects(() -> session.commit(plan, bundle.id, () -> {}), "Same-size corrupted output cannot commit"); check(store.snapshot(bundle.id).length() == 0, "Failed verification has no result");
            }
            try (PreparedAssets.Session session = store.begin(jobId)) {
                outputs(session, plan); JSONObject bad = receipt(plan, "lma.fixture-preparation/1").put("source_sha256_verified", false); write(new File(session.directory, "prepare/preparation.json"), bad.toString().getBytes(StandardCharsets.UTF_8));
                rejects(() -> session.commit(plan, bundle.id, () -> {}), "Receipt must establish full source identity");
            }
            try (PreparedAssets.Session session = store.begin(jobId)) {
                outputs(session, plan); rejects(() -> session.commit(plan, bundle.id, () -> { throw new IOException("cancelled"); }), "Cancellation prevents publication");
            }
            try (PreparedAssets.Session session = store.begin(jobId)) {
                outputs(session, plan); JSONObject record = session.commit(plan, bundle.id, () -> jobs.check(jobId, token)); committedId = record.getString("id");
                jobs.finishPreparation(jobId, token, record, ""); check(jobs.get(jobId).getString("state").equals("succeeded"), "A committed preparation finishes without fake media");
                check(jobs.get(jobId).getJSONArray("artifacts").length() == 0, "Prepared weights are not generated media artifacts");
                rejects(() -> jobs.finishPreparation(jobId, token, record, ""), "Stale completion token rejected");
            }
            check(store.contains(bundle.id, plan), "Prepared identity is discoverable");
            try (PreparedAssets.Lease lease = store.acquire(committedId, () -> {})) {
                lease.record().put("id", "mutated"); check(lease.record().getString("id").equals(committedId), "Lease identity is immutable to consumers");
                check(Arrays.equals(Files.readAllBytes(lease.file("diffusion_model").toPath()), OUTPUT), "Leases expose declared model data");
                rejects(() -> lease.file("other"), "Undeclared role rejected"); rejects(() -> store.remove(committedId), "Leased data cannot be deleted");
            }
            JSONArray copy = store.snapshot(bundle.id); copy.getJSONObject(0).put("bytes", 1); check(store.snapshot(bundle.id).getJSONObject(0).getLong("bytes") == OUTPUT.length, "Snapshots do not mutate persistent receipts");
            try (PreparedAssets.Session session = store.begin("orphan_job")) { outputs(session, plan); rejects(() -> session.commit(plan, bundle.id, () -> {}), "Existing prepared data is not overwritten"); }
            PreparationPlan cancelPlan = new PreparationPlan(plan.json().put("id", "fixture_cancel"));
            JSONObject cancelJob = jobs.submit(request(bundle, cancelPlan), "cancel-publication"); JSONObject cancelOwned = jobs.claimNext();
            String cancelId = cancelOwned.getString("id"), cancelToken = cancelOwned.getString("token");
            try (PreparedAssets.Session session = store.begin(cancelId)) {
                outputs(session, cancelPlan); JSONObject result = session.commit(cancelPlan, bundle.id, () -> jobs.check(cancelId, cancelToken));
                JSONObject wrongPlan = DataFiles.copy(result).put("planId", "wrong_plan"); rejects(() -> jobs.finishPreparation(cancelId, cancelToken, wrongPlan, ""), "Mismatched result cannot finish an immutable task");
                jobs.cancel(cancelId); jobs.finishPreparation(cancelId, cancelToken, result, "");
                check(jobs.get(cancelId).getString("state").equals("cancelled"), "Cancellation wins over a late successful converter");
                store.reconcile(jobs); check(store.snapshot(bundle.id).length() == 1, "Cancelled publication is removed without touching the successful assets");
            }
            PreparationPlan crashPlan = new PreparationPlan(plan.json().put("id", "fixture_crash"));
            jobs.submit(request(bundle, crashPlan), "interrupted-publication"); JSONObject crashOwned = jobs.claimNext();
            try (PreparedAssets.Session session = store.begin(crashOwned.getString("id"))) { outputs(session, crashPlan); session.commit(crashPlan, bundle.id, () -> jobs.check(crashOwned.getString("id"), crashOwned.getString("token"))); }
            PreparedAssets.Session orphan = store.begin("orphan_job"); outputs(orphan, plan);
        }
        try (PreparedAssets store = new PreparedAssets(preparedRoot)) {
            check(store.contains(bundle.id, plan), "Restart retains committed user data"); check(new File(preparedRoot, "work").list().length == 0, "Restart removes only owned incomplete preparation work");
            store.reconcile(new JobStore(new File(root, "jobs"))); check(store.snapshot(bundle.id).length() == 1, "Restart removes interrupted publication while successful job data survives");
            store.remove(committedId); check(store.snapshot(bundle.id).length() == 0, "Independent prepared-data deletion");
        }
        check(Arrays.equals(Files.readAllBytes(source.toPath()), SOURCE), "All operations preserve the original source");
        for (String mode : Arrays.asList("ok", "missing", "oversized", "cancel")) {
            try (PreparedAssets store = new PreparedAssets(new File(root, "process-" + mode)); PreparedAssets.Session session = store.begin("process_job")) {
                AtomicBoolean cancelled = new AtomicBoolean(); AtomicReference<Process> owned = new AtomicReference<>();
                NativePreparation.Context context = new NativePreparation.Context() {
                    public void check() throws IOException { if (cancelled.get()) throw new IOException("cancelled"); }
                    public void progress(String stage, Double fraction) { if (mode.equals("cancel") && fraction != null && fraction > 0) { cancelled.set(true); owned.get().destroy(); } }
                    public File graphs(PreparationPlan.Stage stage) { throw new AssertionError("Fixture has no graphs"); }
                    public Process start(ProcessBuilder builder) throws Exception {
                        builder.command(Arrays.asList(java().getPath(), "-cp", System.getProperty("java.class.path"), PreparationTest.class.getName(), "--worker", builder.command().get(1), mode));
                        Process child = builder.start(); owned.set(child); fixtureChildren++; return child;
                    }
                };
                Action run = () -> { NativePreparation.run(plan, source, Collections.singletonMap("fixture", java()), session, context); session.commit(plan, bundle.id, context::check); };
                if (mode.equals("ok")) { run.run(); check(store.contains(bundle.id, plan), "Native process protocol commits verified outputs"); }
                else rejects(run, "Failed/missing/oversized/cancelled process cannot commit: " + mode);
                check(owned.get() == null || !owned.get().isAlive(), "Process is reaped before temporary files are removed: " + mode);
            }
        }
    }
    static void trained(String[] args) throws Exception {
        File root = new File(args[1]); Files.createDirectories(root.toPath()); JSONObject catalogue = json(new File(args[2])); PreparationPlan plan = new PreparationPlan(catalogue.getJSONArray("plans").getJSONObject(0));
        JSONArray candidates = json(new File(args[3])).getJSONArray("bundles"); ModelBundle bundle = null;
        for (int i = 0; i < candidates.length(); i++) { ModelBundle candidate = new ModelBundle(candidates.getJSONObject(i)); if (plan.matches(candidate)) { bundle = candidate; break; } }
        if (bundle == null) throw new AssertionError("No matching source bundle"); final ModelBundle selected = bundle;
        File source = new File(args[4]); BundleStore bundles = new BundleStore(new File(root, "bundles")); bundles.declare(bundle); bundles.adoptLocal(bundle, Collections.singletonMap(plan.sourceRole, source), new JSONObject(), () -> {});
        JobStore jobs = new JobStore(new File(root, "jobs")); JSONObject submitted = jobs.submit(request(bundle, plan), "trained-preparation"); JSONObject claimed = jobs.claimNext(); String id = claimed.getString("id"), token = claimed.getString("token");
        Map<String,File> programs = new HashMap<>(); programs.put("ltx098_dit_prepare", new File(args[5])); programs.put("ltx098_vae_prepare", new File(args[6])); File graphRoot = new File(args[7]);
        AtomicReference<Process> child = new AtomicReference<>();
        try (PreparedAssets prepared = new PreparedAssets(new File(root, "prepared")); BundleStore.Selection selection = bundles.acquireAll(Collections.singletonList(bundle.id)); PreparedAssets.Session session = prepared.begin(id)) {
            NativePreparation.Context context = new NativePreparation.Context() {
                public void check() throws IOException { jobs.check(id, token); }
                public void progress(String stage, Double fraction) throws Exception { check(); jobs.progress(id, token, stage, fraction); }
                public File graphs(PreparationPlan.Stage stage) { return graphRoot; }
                public Process start(ProcessBuilder builder) throws Exception { check(); Process p = builder.start(); child.set(p); trainedChildren++; return p; }
            };
            NativePreparation.run(plan, selection.models.get(0).file(plan.sourceRole), programs, session, context);
            JSONObject result = session.commit(plan, bundle.id, context::check); jobs.finishPreparation(id, token, result, "");
            check(jobs.get(id).getString("state").equals("succeeded"), "Full trained asset preparation succeeds through production Java core");
            check(result.getJSONArray("outputs").length() == 20, "All twenty pinned runtime assets verified");
            check(child.get() != null && !child.get().isAlive(), "Final real converter exited");
            try (PreparedAssets.Lease lease = prepared.acquire(result.getString("id"), () -> {})) { check(lease.file("diffusion_model").length() == 3849516416L, "Prepared DiT is accessible under a verified lease"); }
            check(source.isFile() && source.length() == plan.sourceBytes, "Original trained checkpoint retained");
            result.put("hostProductionCore", true).put("physicalAndroid", false).put("modelInference", false).put("releaseReady", false).put("nativeChildren", trainedChildren).put("checks", checks);
            write(new File(root, "trained-result.json"), result.toString(2).getBytes(StandardCharsets.UTF_8)); System.out.println(new JSONObject().put("passed", true).put("checks", checks).put("actualTrainedPreparations", 1).put("nativeChildren", trainedChildren).put("outputBytes", plan.outputBytes));
        }
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("--worker")) { fixtureWorker(args[1], args[2]); return; }
        if (args[0].equals("--trained")) { trained(args); return; }
        File root = new File(args[0]); Files.createDirectories(root.toPath()); contracts(root);
        System.out.println(new JSONObject().put("passed", true).put("checks", checks).put("fixtureNativeChildren", fixtureChildren).put("modelInference", false).put("physicalAndroid", false));
    }
}
