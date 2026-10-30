package com.lma.app;

import com.lma.app.core.*;
import com.sun.net.httpserver.HttpServer;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Host filesystem/HTTP tests. Fixtures are byte sequences, not runnable models or Android evidence. */
public final class FoundationTest {
    private static int passed;
    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); passed++; }
    private interface Action { void run() throws Exception; }
    private static void rejects(Action action, String message) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(message); }
    private static String hash(byte[] bytes) throws Exception { return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    private static JSONObject component(String role, byte[] bytes) throws Exception {
        return new JSONObject().put("role", role).put("path", role + ".bin").put("format", "fixture_data").put("bytes", bytes.length).put("sha256", hash(bytes)).put("url", "https://fixture.invalid/" + role);
    }
    private static JSONObject manifest(String id, JSONObject... components) throws Exception {
        JSONArray files = new JSONArray(); for (JSONObject component : components) files.put(component);
        JSONObject fields = new JSONObject().put("steps", new JSONObject().put("type", "integer").put("default", 4).put("minimum", 1).put("maximum", 20).put("presets", new JSONArray().put(4).put(8).put(20)));
        return new JSONObject().put("schema", ModelBundle.SCHEMA).put("id", id).put("modelId", id).put("recipeId", "fixture_recipe_v1").put("name", "Byte fixture " + id)
                .put("engine", "fixture_engine").put("architecture", "fixture_arch").put("pipeline", "fixture_pipeline").put("backend", "cpu").put("tasks", new JSONArray().put("image"))
                .put("parameters", new JSONObject().put("version", 1).put("fields", fields)).put("components", files);
    }
    private static void accept(BundleStore store, String id, String token, ModelBundle.Component c, byte[] data) throws Exception {
        Files.write(store.partial(c.sha256).toPath(), data); store.accept(id, token, c, store.partial(c.sha256));
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); if (!root.isDirectory()) throw new IllegalArgumentException("Create a fresh test directory");
        byte[] a = new byte[300000], b = new byte[20000]; new Random(1941).nextBytes(a); new Random(1920).nextBytes(b);
        JSONObject catalogue = new JSONObject(new String(Files.readAllBytes(new File(args[1]).toPath()), "UTF-8"));
        ModelBundle catalogued = new ModelBundle(catalogue.getJSONArray("bundles").getJSONObject(0));
        check(catalogued.id.equals("sd15_ss_q4_0_r031b5f5") && catalogued.tasks.contains("image"), "Production bundle metadata passes the same runtime schema as user imports");
        BundleStore cataloguedStore = new BundleStore(new File(root, "catalogued-assets")); cataloguedStore.declare(catalogued);
        check(!cataloguedStore.plan(catalogued.id).getBoolean("installed") && !cataloguedStore.snapshot().getJSONObject(0).has("transfer"), "Declaring the shipped SD recipe installs no model and starts no transfer");
        check(catalogued.parameters().normalize(new JSONObject(), new JSONObject()).getJSONObject("values").getInt("width") == 512, "Shipped recipe defaults satisfy its parameter schema");
        passed += CuratedDiffusionTest.run(root, new File(args[1]));
        JSONObject first = manifest("one", component("backbone", a), component("decoder", b));
        rejects(() -> new ModelBundle(DataFiles.copy(first).put("schema", "future")), "Unknown bundle versions must fail");
        JSONObject bad = DataFiles.copy(first); bad.getJSONArray("components").getJSONObject(0).put("path", "../outside.bin");
        rejects(() -> new ModelBundle(bad), "Path traversal must fail");
        JSONObject code = DataFiles.copy(first); code.getJSONArray("components").getJSONObject(0).put("path", "runner.so");
        rejects(() -> new ModelBundle(code), "Downloaded execution code must fail");
        JSONObject unpinned = DataFiles.copy(first); unpinned.getJSONArray("components").getJSONObject(0).put("url", "https://huggingface.co/test/model/resolve/main/backbone.bin");
        rejects(() -> new ModelBundle(unpinned), "Unpinned HF revisions must fail");
        JSONObject noHash = DataFiles.copy(first); noHash.getJSONArray("components").getJSONObject(0).put("sha256", "");
        rejects(() -> new ModelBundle(noHash), "Every dependency needs a hash");
        BundleStore store = new BundleStore(new File(root, "assets"));
        check(store.snapshot().length() == 0, "Fresh installation works with no model assets");
        ModelBundle bundle = new ModelBundle(first); store.declare(bundle);
        rejects(() -> bundle.tasks.add("video"), "A declared bundle cannot mutate its checked output capabilities");
        JSONObject unicode = DataFiles.copy(first); String revision = String.join("", Collections.nCopies(40, "a"));
        unicode.getJSONArray("components").getJSONObject(0).put("path", "音色/voice 1.bin").put("repository", "fixture/voice").put("revision", revision).put("url", "https://huggingface.co/fixture/voice/resolve/" + revision + "/%E9%9F%B3%E8%89%B2/voice%201.bin");
        check(new ModelBundle(unicode).component("backbone").path.equals("音色/voice 1.bin"), "Pinned HF paths retain Unicode and spaces without becoming filesystem destinations");
        check(!store.snapshot().getJSONObject(0).has("transfer"), "Catalogue declaration cannot create download work");
        check(store.plan("one").getLong("remainingBytes") == a.length + b.length, "Plan discloses all dependency sizes");
        check(!store.partial(hash(a)).exists(), "Browsing/planning must not create model bytes");
        check(bundle.tags().getJSONArray("task").getString(0).equals("task:image"), "Output capability is tagged independently");
        check(!store.plan("one").getBoolean("installed"), "Declared does not mean installed");
        String token = store.request("one");
        rejects(() -> store.accept("one", token, new ModelBundle(manifest("wrong", component("backbone", b))).component("backbone"), store.partial(hash(b))), "A transfer cannot promote components outside its selected bundle");
        accept(store, "one", token, bundle.component("backbone"), a);
        rejects(() -> store.install("one", token), "A missing dependency prevents atomic installation");
        rejects(() -> store.acquire("one"), "An incomplete model cannot be used");
        accept(store, "one", token, bundle.component("decoder"), b); store.install("one", token);
        check(store.plan("one").getBoolean("installed"), "Complete verified bundle installs");
        check(store.plan("one").getLong("reusableBytes") == a.length + b.length, "Installed objects are reusable");
        rejects(() -> store.declare(new ModelBundle(DataFiles.copy(first).put("engine", "replacement"))), "An app/catalogue refresh cannot silently replace a recipe");
        ModelBundle second = new ModelBundle(manifest("two", component("backbone", a))); store.declare(second);
        String secondToken = store.request("two"); store.install("two", secondToken);
        check(store.plan("two").getLong("remainingBytes") == 0, "A sibling recipe reuses shared data");
        BundleStore.Lease lease = store.acquire("one");
        check(lease.file("backbone").length() == a.length, "Runtime lease resolves pinned component roles");
        rejects(() -> store.remove("one", false), "Running models are protected from deletion");
        rejects(() -> store.saveSettings("one", new JSONObject().put("steps", 8)), "Running settings cannot mutate underneath a task");
        lease.close(); lease.close();
        JSONObject clamped = store.saveSettings("one", new JSONObject().put("steps", "1000"));
        check(clamped.getJSONObject("values").getInt("steps") == 20 && clamped.getJSONArray("adjustments").length() == 1, "Editable numeric text clamps at the recipe limit with a reason");
        check(store.settings("two").getJSONObject("values").getInt("steps") == 4, "Settings remain independent per model recipe");
        store.remove("one", false);
        check(store.object(hash(a)).isFile() && !store.object(hash(b)).exists(), "Deleting a model keeps another installed model's shared component");
        check(store.settings("one").getJSONObject("values").getInt("steps") == 20, "Optional settings retention works independently of data deletion");
        check(store.plan("two").getBoolean("installed"), "Other models remain usable after deletion");
        String stale = store.request("one"); store.pause("one");
        rejects(() -> store.check("one", stale), "A paused generation cannot commit later");
        BundleStore restored = new BundleStore(new File(root, "assets"));
        check(restored.plan("two").getBoolean("installed"), "Upgrade/restart retains complete model assets");
        check(restored.settings("one").getJSONObject("values").getInt("steps") == 20, "Upgrade/restart retains independent settings");
        String interrupted = restored.request("one"); restored.progress("one", interrupted, "downloading", "decoder", 1, "");
        BundleStore afterCrash = new BundleStore(new File(root, "assets"));
        rejects(() -> afterCrash.check("one", interrupted), "Crash recovery invalidates old transfer ownership");
        check(find(afterCrash.snapshot(), "one").getJSONObject("transfer").getString("state").equals("paused"), "App upgrade never automatically restarts asset downloads");
        String corruptToken = afterCrash.request("one"); Files.write(afterCrash.partial(hash(b)).toPath(), new byte[b.length]);
        rejects(() -> afterCrash.accept("one", corruptToken, bundle.component("decoder"), afterCrash.partial(hash(b))), "Incorrect component hash cannot install");
        check(!afterCrash.partial(hash(b)).exists(), "A corrupt partial is discarded so explicit retry can recover");
        JSONObject fields = new JSONObject().put("width", new JSONObject().put("type", "integer").put("default", 512).put("minimum", 64).put("maximum", 768).put("multipleOf", 64))
                .put("height", new JSONObject().put("type", "integer").put("default", 320).put("minimum", 64).put("maximum", 512).put("multipleOf", 64));
        ParameterSchema shapes = new ParameterSchema(new JSONObject().put("fields", fields).put("allowedShapes", new JSONArray().put(new JSONObject().put("width", 512).put("height", 320)).put(new JSONObject().put("width", 768).put("height", 512))));
        rejects(() -> shapes.normalize(new JSONObject(), new JSONObject().put("width", 768).put("height", 320)), "Valid individual dimensions still need a valid joint compiled shape");
        check(shapes.normalize(new JSONObject(), new JSONObject().put("width", 9999).put("height", 9999)).getJSONObject("values").getInt("width") == 768, "Over-limit shape inputs normalize to legal maximums");
        rejects(() -> shapes.normalize(new JSONObject(), new JSONObject().put("width", "NaN")), "Non-finite input is rejected");
        rejects(() -> shapes.normalize(new JSONObject(), new JSONObject().put("otherModelField", 1)), "Unknown parameters cannot leak into another model schema");
        transferTest(root, a, b);
        int adapterChecks = AdapterTest.run(root); passed += adapterChecks;
        int recipeChecks = RecipeTest.run(root, new File(args[2])); passed += recipeChecks;
        int updateChecks = BundleUpdateTest.run(root); passed += updateChecks;
        jobsAndArtifacts(root);
        ranges();
        System.out.println(new JSONObject().put("passed", passed).put("adapter_contract_assertions", adapterChecks).put("recipe_integrity_assertions", recipeChecks).put("model_update_assertions", updateChecks).put("android_device", false).put("model_inference", false).put("scope", "production bundle storage, parameter validation and transfer state on host filesystems/HTTP"));
    }
    private static JSONObject find(JSONArray entries, String id) throws Exception { for (int i = 0; i < entries.length(); i++) if (entries.getJSONObject(i).getString("id").equals(id)) return entries.getJSONObject(i); throw new AssertionError("Missing bundle"); }
    private static void ranges() throws Exception {
        ByteRange all = ByteRange.parse(null, 100); check(!all.partial && all.start == 0 && all.length == 100, "Unranged preview returns the complete file");
        ByteRange part = ByteRange.parse("bytes=20-49", 100); check(part.start == 20 && part.length == 30 && part.contentRange(100).equals("bytes 20-49/100"), "Media seeking uses an exact bounded byte range");
        check(ByteRange.parse("bytes=-10", 100).start == 90 && ByteRange.parse("bytes=-1000", 100).length == 100, "Suffix ranges cannot escape the artifact");
        check(ByteRange.parse("bytes=90-999", 100).length == 10 && ByteRange.parse("bytes=90-", 100).length == 10, "Open and oversized end ranges stop at EOF");
        for (String invalid : Arrays.asList("bytes=100-", "bytes=30-20", "bytes=0-1,5-6", "bytes=-0", "bytes=99999999999999999999999-", "other=1-2")) rejects(() -> ByteRange.parse(invalid, 100), "Invalid or unsatisfiable media range is rejected: " + invalid);
    }
    private static void jobsAndArtifacts(File root) throws Exception {
        File directory = new File(root, "jobs"); JobStore jobs = new JobStore(directory);
        JSONObject request = new JSONObject().put("type", "image.generate").put("bundleId", "one").put("parameters", new JSONObject().put("steps", 4)).put("input", new JSONObject().put("prompt", "fixture"));
        JSONObject queued = jobs.submit(request, "retry-safe-key"); String id = queued.getString("id");
        check(jobs.submit(DataFiles.copy(request), "retry-safe-key").getString("id").equals(id), "An idempotent API retry does not duplicate a generation");
        rejects(() -> jobs.submit(DataFiles.copy(request).put("type", "video.generate"), "retry-safe-key"), "Reusing an idempotency key for a different task fails");
        request.getJSONObject("parameters").put("steps", 20);
        check(jobs.get(id).getJSONObject("request").getJSONObject("parameters").getInt("steps") == 4, "Queue snapshots do not follow later parameter edits");
        JSONObject claimed = jobs.claimNext(); String token = claimed.getString("token");
        check(claimed.getString("id").equals(id) && !jobs.get(id).has("token"), "Claim ownership is private to the active worker");
        check(jobs.claimNext() == null, "Only one heavy task can own the queue");
        jobs.progress(id, token, "sampling", 0.5);
        rejects(() -> jobs.progress(id, token, "sampling", 1.1), "Invalid engine progress cannot be advertised");
        rejects(() -> jobs.finish(id, token, new JSONArray(), ""), "No-output engine completion cannot become success");
        ArtifactStore artifacts = new ArtifactStore(new File(root, "artifacts"), f -> new JSONObject().put("mime", "text/plain").put("characters", f.length()));
        File staged = artifacts.staging(id, "txt"); Files.write(staged.toPath(), "host fixture output, not model inference".getBytes("UTF-8"));
        JSONObject result = artifacts.commit(id, staged, claimed.getJSONObject("request"), () -> jobs.check(id, token)); String artifactId = result.getString("id");
        check(artifacts.file(artifactId).isFile() && !staged.exists(), "Validated output moves atomically from staging to the private result library");
        try (InputStream preview = artifacts.open(artifactId, ByteRange.parse("bytes=5-11", result.getLong("bytes")))) {
            rejects(() -> artifacts.remove(artifactId), "A preview stream protects the artifact until WebView closes it");
            ByteArrayOutputStream read = new ByteArrayOutputStream(); int next; while ((next = preview.read()) != -1) read.write(next);
            check(new String(read.toByteArray(), "UTF-8").equals("fixture"), "Artifact preview returns only the requested byte interval");
        }
        check(result.getString("sha256").equals(DataFiles.sha256(artifacts.file(artifactId))), "Result metadata binds actual bytes to a hash");
        jobs.finish(id, token, new JSONArray().put(artifactId), "");
        check(jobs.get(id).getString("state").equals("succeeded"), "Only committed artifact references complete a job");
        rejects(() -> jobs.finish(id, token, new JSONArray().put(artifactId), ""), "Duplicate or stale process completion cannot rewrite a terminal task");
        ArtifactStore.Lease reader = artifacts.acquire(artifactId);
        rejects(() -> artifacts.remove(artifactId), "An active input/export lease protects result files"); reader.close();
        ArtifactStore reopened = new ArtifactStore(new File(root, "artifacts"), f -> new JSONObject().put("mime", "text/plain"));
        check(reopened.get(artifactId).getJSONObject("provenance").getJSONObject("parameters").getInt("steps") == 4, "Result provenance survives restart with its original effective parameters");
        JSONObject another = jobs.submit(request, ""); String second = another.getString("id"); JSONObject secondClaim = jobs.claimNext();
        jobs.cancel(second); rejects(() -> jobs.check(second, secondClaim.getString("token")), "Cancellation stops further work in the current generation");
        jobs.finish(second, secondClaim.getString("token"), new JSONArray().put(artifactId), "");
        check(jobs.get(second).getString("state").equals("cancelled") && jobs.get(second).getJSONArray("artifacts").length() == 0, "Late output cannot convert a cancelled task into success");
        JSONObject beforeCrash = jobs.submit(request, "crash-key"); String third = beforeCrash.getString("id"); JSONObject oldClaim = jobs.claimNext();
        JobStore recovered = new JobStore(directory);
        check(recovered.get(third).getString("state").equals("interrupted"), "Process death records interruption without inventing a resumable checkpoint");
        rejects(() -> recovered.check(third, oldClaim.getString("token")), "A previous process generation loses ownership after recovery");
        check(recovered.get(id).getString("state").equals("succeeded"), "Completed jobs remain complete after a crash elsewhere");
        JSONObject waiting = recovered.submit(request, "queued-key"); String fourth = waiting.getString("id"); recovered.cancel(fourth);
        check(recovered.get(fourth).getString("state").equals("cancelled"), "A queued task cancels without starting an engine");
        JSONObject events = recovered.events(0, id);
        check(events.getJSONArray("events").length() >= 4 && events.getLong("cursor") > 0, "Durable events provide a cursor independent of WebView lifetime");
        artifacts.remove(artifactId); check(artifacts.snapshot().length() == 0, "Explicit result deletion updates the durable library");
        File badDirectory = new File(root, "corrupt-index"); badDirectory.mkdirs(); File corrupt = new File(badDirectory, "jobs.json"); Files.write(corrupt.toPath(), "{broken metadata".getBytes("UTF-8"));
        rejects(() -> new JobStore(badDirectory), "Corrupted metadata must be reported rather than reset silently");
        check(new String(Files.readAllBytes(corrupt.toPath()), "UTF-8").equals("{broken metadata"), "Failure preserves original metadata for recovery");
    }
    private static void transferTest(File root, byte[] a, byte[] b) throws Exception {
        BundleStore store = new BundleStore(new File(root, "network-assets"));
        ModelBundle bundle = new ModelBundle(manifest("network", component("backbone", a), component("decoder", b))); store.declare(bundle);
        AtomicInteger requests = new AtomicInteger(), resumed = new AtomicInteger(), installed = new AtomicInteger();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0); ExecutorService threads = Executors.newCachedThreadPool(); server.setExecutor(threads);
        server.createContext("/", exchange -> {
            try {
                boolean main = exchange.getRequestURI().getPath().equals("/backbone"); byte[] data = main ? a : b; requests.incrementAndGet();
                String range = exchange.getRequestHeaders().getFirst("Range"); int start = range == null ? 0 : Integer.parseInt(range.substring(6, range.length() - 1));
                if (start > 0) { resumed.incrementAndGet(); exchange.getResponseHeaders().set("Content-Range", "bytes " + start + "-" + (data.length - 1) + "/" + data.length); }
                exchange.sendResponseHeaders(start > 0 ? 206 : 200, data.length - start);
                int count = main && requests.get() == 1 ? 120000 : data.length - start;
                exchange.getResponseBody().write(data, start, count);
            } finally { exchange.close(); }
        }); server.start();
        BundleTransfers.Listener listener = new BundleTransfers.Listener() { public void changed() {} public void installed(String id) { installed.incrementAndGet(); } public void failed(String id, String message) {} };
        BundleTransfers transfers = new BundleTransfers(store, (c, offset, observer) -> {
            HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:" + server.getAddress().getPort() + "/" + c.role).openConnection();
            connection.setConnectTimeout(2000); connection.setReadTimeout(2000); if (offset > 0) connection.setRequestProperty("Range", "bytes=" + offset + "-"); observer.opened(connection); return connection;
        }, listener);
        try {
            check(requests.get() == 0, "Service construction never downloads a recommended model");
            transfers.download(bundle.id); check(transfers.awaitIdle(15, TimeUnit.SECONDS), "Interrupted download reaches a durable terminal state");
            check(!store.plan(bundle.id).getBoolean("installed") && store.partial(hash(a)).length() == 120000, "A truncated network transfer retains a resumable partial without declaring installation");
            transfers.download(bundle.id); check(transfers.awaitIdle(15, TimeUnit.SECONDS), "Explicit resume completes");
            check(resumed.get() == 1 && installed.get() == 1 && store.plan(bundle.id).getBoolean("installed"), "HTTP Range resume verifies the complete dependency bundle");
            int before = requests.get(); transfers.download(bundle.id); check(requests.get() == before, "An installed bundle never downloads again on selection");
            ModelBundle imports = new ModelBundle(manifest("imported", component("backbone", a), component("decoder", b))); store.declare(imports);
            transfers.importFiles(imports.id, Collections.emptyMap()); check(transfers.awaitIdle(5, TimeUnit.SECONDS), "Reused imports complete");
            check(requests.get() == before && installed.get() == 2, "Already verified components install a second recipe without network traffic");
        } finally { transfers.close(); server.stop(0); threads.shutdownNow(); }
    }
}
