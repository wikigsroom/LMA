package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Real private host files/hardlinks and a literal HTTP child fixture. No tensors or model output. */
public final class MigrationTest {
    private static final List<String> passed = new ArrayList<>();
    private static Path root, work, assets, libraries;
    private static RecipeCatalogue recipes;
    private interface Checked { void run() throws Exception; }
    private interface Condition { boolean value() throws Exception; }
    private static void check(boolean ok, String name) { if (!ok) throw new AssertionError(name); passed.add(name); }
    private static void rejects(Checked action, String name) throws Exception { try { action.run(); } catch (Exception expected) { check(true, name); return; } throw new AssertionError(name); }
    private static void waitFor(Condition condition, String name) throws Exception { long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(12); while (System.nanoTime() < until) { if (condition.value()) return; Thread.sleep(25); } throw new AssertionError(name); }
    private static LmaApp app(String name) { return new LmaApp(work.resolve(name).toFile(), assets.toFile(), libraries.toFile()); }
    private static void string(ByteBuffer b, String s) { byte[] bytes = s.getBytes(StandardCharsets.UTF_8); b.putLong(bytes.length).put(bytes); }
    private static byte[] gguf(int context) {
        ByteBuffer b = ByteBuffer.allocate(768 * 1024).order(ByteOrder.LITTLE_ENDIAN);
        b.put(new byte[]{'G','G','U','F'}).putInt(3).putLong(0).putLong(2);
        string(b, "general.architecture"); b.putInt(8); string(b, "llama");
        string(b, "llama.context_length"); b.putInt(4).putInt(context);
        return b.array(); // Deliberately zero tensors, metadata only, never used for inference.
    }
    private static String add(LmaApp app, String name, byte[] data, String digest) throws Exception {
        String id = app.store.addCustom(name, "https://example.invalid/" + name + ".gguf", digest, false);
        Files.write(app.store.modelFile(id).toPath(), data); return id;
    }
    private static String digest(byte[] data) throws Exception { return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(data)); }
    private static String bundleId(String id, String hash) throws Exception { return "legacy_" + digest((id + ":" + hash).getBytes(StandardCharsets.UTF_8)); }
    private static JSONObject outcome(JSONArray values, String id) throws Exception { for (int i = 0; i < values.length(); i++) if (values.getJSONObject(i).getString("id").equals(id)) return values.getJSONObject(i); throw new AssertionError("Missing migration outcome"); }
    private static boolean inUse(LmaApp app, String id) throws Exception { JSONArray all = app.bundles.snapshot(); for (int i = 0; i < all.length(); i++) if (all.getJSONObject(i).getString("id").equals(id)) return all.getJSONObject(i).getBoolean("inUse"); return false; }

    private static void testMigration() throws Exception {
        LmaApp app = app("normal"); String catalogue = DataFiles.canonical(app.store.model("m08"));
        check(app.store.migrateExisting(recipes, () -> {}).length() == 0, "Zero-model upgrade creates no models or transfers");
        check(app.bundles.snapshot().length() == 0, "Catalogue metadata does not install weights");
        byte[] data = gguf(1024); String id = add(app, "private", data, ""); Path old = app.store.modelFile(id).toPath();
        Path held = work.resolve("original-inode.gguf"); Files.createLink(held, old);
        app.store.saveConfig(id, new JSONObject().put("context", 4096).put("maxTokens", 3000).put("systemPrompt", "保留我的配置\nKeep my profile"));
        JSONObject result = outcome(app.store.migrateExisting(recipes, () -> {}), id); String bound = result.getString("bundleId");
        check(result.getString("state").equals("migrated"), "Existing custom GGUF is adopted locally");
        check(bound.equals(bundleId(id, digest(data))) && app.store.bundleId(id).equals(bound), "Binding identity fixes the original ID and measured bytes");
        check(Files.isSameFile(held, app.store.modelFile(id).toPath()), "CAS reuses the original inode without a model copy");
        check(!Files.exists(old), "Obsolete private filename is removed only after binding commit");
        check(app.store.installed(id) && app.bundles.plan(bound).getBoolean("installed"), "Legacy and shared records agree on installation");
        check(app.store.config(id).getJSONObject("values").getInt("context") == 1024, "Migration reads actual GGUF context metadata");
        check(app.store.config(id).getJSONObject("values").getInt("maxTokens") == 1023, "Migrated output obeys actual joint context bound");
        check(app.store.config(id).getJSONObject("values").getString("systemPrompt").equals("保留我的配置\nKeep my profile"), "Unicode profile survives byte-for-byte");
        check(DataFiles.canonical(app.store.model("m08")).equals(catalogue), "Recommended publisher metadata and labels are unchanged");
        check(app.store.model(id).getString("id").equals(id), "Original public model ID is preserved");
        check(app.prefs.getString("selectedModel", "").isEmpty(), "Migration does not select or load a model");
        check(app.bundles.record(bound).getJSONObject("transfer").getString("origin").equals("existing_app_files"), "Adoption records local provenance without a network transfer");
        app.store.saveConfig(id, new JSONObject().put("maxTokens", 77));
        check(app.bundles.settings(bound).getJSONObject("values").getInt("maxTokens") == 77, "Legacy editor writes the shared per-model profile");
        app.bundles.saveSettings(bound, new JSONObject().put("temperature", 0.2));
        check(app.store.config(id).getJSONObject("values").getDouble("temperature") == 0.2, "Shared editor is authoritative for legacy requests");
        check(app.store.migrateExisting(recipes, () -> {}).length() == 0, "Repeated migration is idempotent and preserves edited defaults");
        Store reopened = new Store(app);
        check(reopened.bundleId(id).equals(bound) && reopened.installed(id), "Atomic binding survives Store reconstruction");
        check(reopened.config(id).getJSONObject("values").getInt("maxTokens") == 77, "Restart preserves the shared model profile");
        ApiHost api = new ApiHost(new LmaService(), app);
        JSONArray listed = api.models(); int oldId = 0, duplicate = 0;
        for (int i = 0; i < listed.length(); i++) { JSONObject m = listed.getJSONObject(i); if (m.getString("id").equals(id)) { oldId++; check(m.getString("bundle_id").equals(bound), "API exposes immutable job bundle ID beside legacy alias"); } if (m.getString("id").equals(bound)) duplicate++; }
        check(oldId == 1 && duplicate == 0, "API retains one record for a migrated model"); api.close();
        try (BundleStore.Lease lease = app.bundles.acquire(bound)) {
            check(Files.isSameFile(lease.file("text_gguf").toPath(), held), "A shared task leases the actual migrated file");
            rejects(() -> app.store.remove(id), "Legacy delete respects shared task asset leases");
            rejects(() -> app.store.saveConfig(id, new JSONObject().put("context", 512)), "Legacy settings respect shared task leases");
        }
        JSONObject job = app.jobs.submit(new JSONObject().put("bundleId", bound).put("type", "text.generate").put("input", new JSONObject().put("prompt", "fixture")), "migration-job");
        rejects(() -> app.store.remove(id), "Queued jobs protect migrated assets against legacy deletion");
        app.jobs.cancel(job.getString("id"));
        String second = add(app, "second", data, ""); app.store.migrateExisting(recipes, () -> {}); String secondBundle = app.store.bundleId(second);
        check(!secondBundle.equals(bound) && Files.isSameFile(app.store.modelFile(second).toPath(), held), "Distinct model profiles share identical verified bytes");
        check(app.store.config(second).getJSONObject("values").getInt("maxTokens") != 77, "Shared bytes do not merge model settings");
        app.store.remove(id);
        check(!app.bundles.plan(bound).getBoolean("installed") && app.store.installed(second), "Deleting one migrated model retains another installed reference");
        check(Files.exists(app.store.modelFile(second).toPath()), "Shared component remains available after deletion");
        check(app.store.migrateExisting(recipes, () -> {}).length() == 0, "Deleted models are not implicitly reinstalled");
        check(app.store.config(second).getJSONObject("values").getString("systemPrompt").equals(ModelSettings.SYSTEM), "Other profiles survive migration and deletion");
    }

    private static void testOrigins() throws Exception {
        LmaApp app = app("origins"); byte[] data = gguf(2048); String hash = digest(data), revision = String.join("", Collections.nCopies(40, "a"));
        JSONObject repository = new JSONObject().put("id", "fixture/text").put("revision", revision).put("uncensored", new JSONObject().put("status", "unknown").put("declared", false).put("detected", false));
        JSONObject file = HubClient.file(repository, new JSONObject().put("path", "nested/model.gguf").put("size", data.length).put("lfs", new JSONObject().put("oid", hash)));
        String id = app.store.addHub(HubClient.selected(repository, file)); Files.write(app.store.modelFile(id).toPath(), data);
        app.engineModel = id; app.engineState = "ready";
        check(app.store.migrateExisting(recipes, () -> {}).length() == 0 && app.store.bundleId(id).isEmpty(), "Active legacy model waits for migration without altering its loaded path");
        app.engineState = "stopped"; app.engineModel = "";
        String imported = app.store.addCustom("device-file", "", "", true); Files.write(app.store.modelFile(imported).toPath(), data);
        app.store.migrateExisting(recipes, () -> {}); ModelBundle model = app.bundles.bundle(app.store.bundleId(id));
        check(model.modelId.equals(id) && id.startsWith("hf_"), "HF selection retains its original stable ID");
        check(model.component("text_gguf").repository.equals("fixture/text") && model.component("text_gguf").revision.equals(revision), "Migration retains pinned HF repository and revision");
        check(model.component("text_gguf").path.equals("nested/model.gguf") && model.component("text_gguf").url.equals("https://huggingface.co/fixture/text/resolve/" + revision + "/nested/model.gguf"), "Pinned download URL and exact component path remain consistent");
        check(!model.json().getJSONObject("uncensored").optBoolean("declared"), "Migration cannot promote an unknown content declaration");
        check(app.bundles.bundle(app.store.bundleId(imported)).component("text_gguf").url.isEmpty(), "Device imports remain local-only assets without fabricated download URLs");
        JSONObject queued = new JSONObject().put("state", "queued"); String pending = app.store.addCustom("queued", "https://example.invalid/queued.gguf", "", false); app.store.updateDownload(pending, queued, true);
        check(new Store(app).download(pending).getString("state").equals("paused"), "Queued legacy transfers also require explicit resume after upgrade");
        String large = add(app, "large-context", gguf(262144), ""); app.store.inspectModel(large); app.store.saveConfig(large, new JSONObject().put("context", 200000)); app.store.migrateExisting(recipes, () -> {});
        JSONObject limits = app.store.config(large).getJSONObject("limits");
        check(limits.getInt("contextMax") == 131072 && limits.getInt("contextMetadataMax") == 262144 && limits.getString("contextLimitSource").equals("application_or_recipe"), "Legacy editor distinguishes the effective shared guard from model metadata");
        check(app.store.previewConfig(large, new JSONObject().put("context", 200000)).getInt("context") == 131072, "Native legacy preview enforces the shared context guard");
        JSONObject plan = app.bundles.planUpdate(app.store.bundleId(id), app.store.bundleId(imported), "copy");
        check(plan.getString("fromBundleId").equals(app.store.bundleId(id)), "Migrated HF model participates in the ordinary version-review protocol");
    }
    private static void testConcurrentSettings() throws Exception {
        LmaApp app = app("concurrent"); String id = add(app, "editing", gguf(2048), "");
        CountDownLatch hashing = new CountDownLatch(1), proceed = new CountDownLatch(1); AtomicInteger checks = new AtomicInteger();
        ExecutorService worker = Executors.newSingleThreadExecutor();
        try {
            Future<JSONArray> migration = worker.submit(() -> app.store.migrateExisting(recipes, () -> {
                if (checks.incrementAndGet() == 3) {
                    hashing.countDown();
                    try { if (!proceed.await(5, TimeUnit.SECONDS)) throw new IOException("Concurrent settings fixture timed out"); }
                    catch (InterruptedException error) { Thread.currentThread().interrupt(); throw new InterruptedIOException("fixture cancelled"); }
                }
            }));
            check(hashing.await(5, TimeUnit.SECONDS), "Actual hashing runs outside the legacy settings monitor");
            app.store.saveConfig(id, new JSONObject().put("maxTokens", 55).put("systemPrompt", "saved during verification")); proceed.countDown(); migration.get(10, TimeUnit.SECONDS);
            check(app.store.config(id).getJSONObject("values").getString("systemPrompt").equals("saved during verification"), "Binding commits a user edit saved concurrently with hashing");
            check(app.bundles.settings(app.store.bundleId(id)).getJSONObject("values").getInt("maxTokens") == 55, "Concurrent output default reaches the shared profile without reset");
        } finally { proceed.countDown(); worker.shutdownNow(); worker.awaitTermination(5, TimeUnit.SECONDS); }
    }
    private static void testFailures() throws Exception {
        LmaApp app = app("failures"); byte[] data = gguf(2048);
        String bad = add(app, "bad", data, String.join("", Collections.nCopies(64, "0")));
        Path source = app.store.modelFile(bad).toPath(); String before = DataFiles.sha256(source.toFile());
        JSONObject failed = outcome(app.store.migrateExisting(recipes, () -> {}), bad);
        check(failed.getString("state").equals("failed") && app.store.bundleId(bad).isEmpty(), "Publisher hash mismatch does not bind a model");
        check(Files.exists(source) && DataFiles.sha256(source.toFile()).equals(before), "Failed adoption preserves original bytes");
        check(!app.bundles.object(String.join("", Collections.nCopies(64, "0"))).exists(), "Unverified data never appears under a trusted CAS name");
        check(app.bundles.snapshot().length() == 0, "Failed validation publishes no installed bundle");
        String broken = add(app, "broken", new byte[32], "");
        check(outcome(app.store.migrateExisting(recipes, () -> {}), broken).getString("state").equals("failed"), "Broken GGUF metadata remains an explicit migration error");
        check(Files.exists(app.store.modelFile(broken).toPath()), "Invalid legacy file remains available for user management");
        LmaApp cancelled = app("cancelled"); String id = add(cancelled, "interrupt", data, ""); Path old = cancelled.store.modelFile(id).toPath();
        AtomicInteger calls = new AtomicInteger();
        rejects(() -> cancelled.store.migrateExisting(recipes, () -> { if (calls.incrementAndGet() >= 4) throw new InterruptedIOException("fixture cancellation"); }), "Cancellation interrupts verification before publication");
        check(cancelled.store.bundleId(id).isEmpty() && Files.exists(old), "Cancelled migration leaves the legacy binding and source intact");
        File[] parts = new File(cancelled.getFilesDir(), "bundles/partial").listFiles((dir, name) -> name.contains(".adopt-"));
        check(parts != null && parts.length == 0, "Handled cancellation cleans staged adoption links");
        cancelled.store.migrateExisting(recipes, () -> {});
        check(cancelled.store.installed(id) && !cancelled.store.bundleId(id).isEmpty(), "Interrupted migration can be retried without fetching weights");
        LmaApp crashed = app("binding-interrupted"); String cid = add(crashed, "commit", data, ""); Path cold = crashed.store.modelFile(cid).toPath(); String cb = bundleId(cid, digest(data));
        rejects(() -> crashed.store.migrateExisting(recipes, () -> { try { if (crashed.bundles.plan(cb).optBoolean("installed")) throw new InterruptedIOException("after CAS commit"); } catch (IllegalArgumentException absent) {} catch (JSONException absent) {} catch (InterruptedIOException stop) { throw stop; } catch (Exception error) { throw new IOException(error); } }), "Interruption between CAS and legacy-index commits is recoverable");
        check(Files.exists(cold) && crashed.store.bundleId(cid).isEmpty(), "CAS-first interruption retains the original authoritative record");
        crashed.store.migrateExisting(recipes, () -> {});
        check(crashed.store.bundleId(cid).equals(cb), "Retry reuses the same immutable identity after partial metadata commit");
        String partial = crashed.store.addCustom("partial", "https://example.invalid/partial.gguf", "", false);
        Files.write(crashed.store.partFile(partial).toPath(), new byte[200]); crashed.store.updateDownload(partial, new JSONObject().put("state", "downloading"), true);
        Store reopened = new Store(crashed); check(reopened.download(partial).getString("state").equals("paused"), "Upgrade leaves unfinished legacy downloads explicitly paused");
        check(reopened.bundleId(partial).isEmpty() && crashed.store.partFile(partial).length() == 200, "Partial data is neither installed nor migrated");
        Downloads restored = new Downloads(new LmaService(), crashed);
        try { restored.resumeInterrupted(); check(!restored.busy(), "Service restoration does not start any network model transfer"); } finally { restored.close(); }
        File orphan = new File(crashed.getFilesDir(), "bundles/partial/" + digest(data) + ".adopt-11111111-1111-1111-1111-111111111111"); Files.createLink(orphan.toPath(), crashed.store.modelFile(cid).toPath());
        File regular = crashed.bundles.partial(digest(data)); Files.write(regular.toPath(), new byte[42]);
        new BundleStore(new File(crashed.getFilesDir(), "bundles"));
        check(!orphan.exists() && regular.length() == 42, "Restart discards only orphan adoption links and retains resumable parts");
    }

    private static void testPersistentLease() throws Exception {
        LmaApp app = app("persistent"); String id = add(app, "loaded", gguf(512), ""); app.store.migrateExisting(recipes, () -> {}); String bound = app.store.bundleId(id);
        LmaService service = new LmaService(); AtomicReference<Process> child = new AtomicReference<>();
        EngineHost engine = new EngineHost(service, app, builder -> {
            List<String> command = new ArrayList<>(); command.add(Paths.get(System.getProperty("java.home"), "bin", "java.exe").toString()); command.add("-Dsun.net.useExclusiveBind=false"); command.add("-cp"); command.add(System.getProperty("java.class.path")); command.add("com.lma.app.HostServer"); command.addAll(builder.command().subList(1, builder.command().size()));
            ProcessBuilder fixture = new ProcessBuilder(command).redirectErrorStream(true); fixture.environment().putAll(builder.environment()); fixture.environment().put("LMA_HOST_BEHAVIOR", "normal"); fixture.environment().put("LMA_HOST_LAST_REQUEST", work.resolve("persistent-request.json").toString()); Process value = fixture.start(); child.set(value); return value;
        }); service.engine = engine;
        try {
            engine.load(id); waitFor(engine::ready, "Mapped legacy engine readiness");
            check(inUse(app, bound), "Persistent legacy engine holds the shared bundle lease");
            rejects(() -> app.bundles.remove(bound, false), "Generic deletion cannot remove a loaded legacy engine asset");
            rejects(() -> app.store.remove(id), "Legacy deletion still blocks the currently loaded model");
            Process original = child.get(); engine.configure(id, new JSONObject().put("maxTokens", 33));
            check(app.bundles.settings(bound).getJSONObject("values").getInt("maxTokens") == 33 && child.get() == original, "Owner can edit future output defaults without restarting the loaded process");
            app.textRequestBusy = true;
            rejects(() -> engine.configure(id, new JSONObject().put("context", 256)), "Active API request prevents changing loaded context"); app.textRequestBusy = false;
            engine.configure(id, new JSONObject().put("context", 256)); waitFor(() -> engine.ready() && child.get() != original, "Reload mapped engine after configuration change");
            check(!original.isAlive() && app.bundles.settings(bound).getJSONObject("values").getInt("context") == 256, "Context edit reloads one process and preserves its shared profile");
            engine.stop(); waitFor(() -> !inUse(app, bound), "Lease released after process exit");
            check(child.get() != null && !child.get().isAlive(), "Persistent process exits before its shared lease is released");
            app.store.remove(id); check(!app.bundles.plan(bound).getBoolean("installed"), "Stopped migrated engine can be deleted through one store");
        } finally { engine.close(); Process value = child.get(); if (value != null && value.isAlive()) { value.destroyForcibly(); value.waitFor(5, TimeUnit.SECONDS); } }
    }

    public static void main(String[] args) throws Exception {
        root = Paths.get(args[0]); work = Paths.get(args[1]); assets = root.resolve("app/src/main/assets"); libraries = work.resolve("libraries"); Files.createDirectories(libraries);
        Path binary = libraries.resolve("libllama-server.so"); Files.write(binary, new byte[]{1}); binary.toFile().setExecutable(true);
        recipes = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(assets.resolve("recipe-templates.json")), StandardCharsets.UTF_8)));
        testMigration(); testOrigins(); testConcurrentSettings(); testFailures(); testPersistentLease();
        System.out.println(new JSONObject().put("passed", passed.size()).put("checks", new JSONArray(passed)).put("physical_device_tested", false).put("model_inference_tested", false).put("actual_host_hardlinks", true).put("actual_host_child", true).put("automatic_downloads", false));
    }
}
