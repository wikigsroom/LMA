package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

/** Byte fixtures only: component selection/integrity, never phone/model compatibility evidence. */
public final class RecipeTest {
    private static int passed;
    private static final String REV = "1234567890123456789012345678901234567890";
    private interface Action { void run() throws Exception; }
    private static void check(boolean ok, String reason) { if (!ok) throw new AssertionError(reason); passed++; }
    private static void rejects(Action action, String reason) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(reason); }
    private static String sha(String algorithm, byte[] data) throws Exception { return Protocol.hex(MessageDigest.getInstance(algorithm).digest(data)); }
    private static String git(byte[] data) throws Exception { MessageDigest md = MessageDigest.getInstance("SHA-1"); md.update(("blob " + data.length + "\0").getBytes(StandardCharsets.US_ASCII)); return Protocol.hex(md.digest(data)); }
    private static JSONObject asset(String format, byte[] data) throws Exception {
        String path = "shared/model." + (format.equals("text") ? "txt" : format);
        return new JSONObject().put("repository", "fixture/data").put("revision", REV).put("path", path).put("format", format).put("bytes", data.length)
                .put("url", "https://huggingface.co/fixture/data/resolve/" + REV + "/" + path).put("gitBlobSha1", git(data));
    }
    private static JSONObject manifest(JSONObject component) throws Exception {
        return new JSONObject().put("schema", ModelBundle.SCHEMA_V2).put("id", "git_fixture").put("modelId", "git_fixture").put("recipeId", "fixture_recipe")
                .put("name", "Not a model").put("engine", "fixture_engine").put("architecture", "fixture_arch").put("pipeline", "fixture_pipeline").put("backend", "cpu")
                .put("tasks", new JSONArray().put("audio")).put("components", new JSONArray().put(component));
    }
    public static int run(File root, File templates) throws Exception {
        passed = 0; byte[] data = "host byte fixture\n".getBytes(StandardCharsets.UTF_8);
        JSONObject c = asset("text", data).put("role", "tokens"), source = manifest(c); ModelBundle bundle = new ModelBundle(source);
        ModelBundle.Component component = bundle.component("tokens");
        check(!component.objectId.equals(sha("SHA-256", data)) && component.sha256.isEmpty(), "An opaque Git object key must not impersonate content SHA256");
        check(!component.gitBlobSha1.equals(sha("SHA-1", data)), "Git integrity includes the blob header");
        JSONObject legacy = DataFiles.copy(source).put("schema", ModelBundle.SCHEMA); rejects(() -> new ModelBundle(legacy), "Schema 1 cannot silently change digest semantics");
        JSONObject invalid = DataFiles.copy(source); invalid.getJSONArray("components").getJSONObject(0).put("sha256", sha("SHA-256", data));
        JSONObject both = invalid; rejects(() -> new ModelBundle(both), "Schema 2 accepts exactly one expected digest");
        for (String field : Arrays.asList("gitBlobSha1", "url", "importPath")) {
            JSONObject bad = DataFiles.copy(source); bad.getJSONArray("components").getJSONObject(0).put(field, field.equals("gitBlobSha1") ? "xyz" : field.equals("url") ? "https://fixture.invalid/model.txt" : "../outside");
            rejects(() -> new ModelBundle(bad), "Reject malformed digest, non-HF Git URL or import traversal");
        }
        File disk = new File(root, "git-integrity"); BundleStore store = new BundleStore(disk); store.declare(bundle);
        check(!store.plan(bundle.id).getBoolean("installed") && !store.snapshot().getJSONObject(0).has("transfer"), "Registering a recipe does not transfer files");
        String token = store.request(bundle.id); Files.write(store.partial(component.objectId).toPath(), data);
        rejects(() -> ComponentIntegrity.verify(store.partial(component.objectId), component, () -> { throw new IOException("cancelled"); }), "Verification honors cancellation");
        check(store.partial(component.objectId).isFile(), "Cancellation preserves resumable data");
        byte[] wrong = data.clone(); wrong[0] ^= 1; Files.write(store.partial(component.objectId).toPath(), wrong);
        rejects(() -> store.accept(bundle.id, token, component, store.partial(component.objectId)), "Correct size with wrong Git blob identity is rejected");
        check(!store.partial(component.objectId).exists(), "Known-bad complete data is not retained as resumable");
        Files.write(store.partial(component.objectId).toPath(), data); store.accept(bundle.id, token, component, store.partial(component.objectId)); store.install(bundle.id, token);
        JSONObject plan = store.plan(bundle.id), receipt = plan.getJSONArray("components").getJSONObject(0);
        check(plan.getBoolean("installed") && receipt.getString("verifiedSha256").equals(sha("SHA-256", data)), "Installation records independently measured SHA256");
        check(receipt.getString("gitBlobSha1").equals(git(data)) && receipt.getString("integrityAlgorithm").equals("git_blob_sha1"), "Download plans disclose the actual expected algorithm");
        try (BundleStore.Lease lease = store.acquire(bundle.id)) {
            check(lease.integrity().getJSONObject("tokens").getString("sha256").equals(sha("SHA-256", data)), "Task leases carry the actual receipt into provenance");
            rejects(() -> store.remove(bundle.id, true), "Running references protect the selected component");
        }
        BundleStore imported = new BundleStore(new File(root, "git-explicit-import")); imported.declare(bundle);
        java.util.concurrent.atomic.AtomicInteger fetched = new java.util.concurrent.atomic.AtomicInteger();
        BundleTransfers.Listener listener = new BundleTransfers.Listener() { public void changed() {} public void installed(String id) {} public void failed(String id, String error) {} };
        try (BundleTransfers transfers = new BundleTransfers(imported, (file, offset, observer) -> { fetched.incrementAndGet(); throw new IOException("Unexpected network fetch during explicit import"); }, listener)) {
            transfers.importFiles(bundle.id, Collections.singletonMap("tokens", () -> new ByteArrayInputStream(data)));
            if (!transfers.awaitIdle(5, java.util.concurrent.TimeUnit.SECONDS)) throw new AssertionError("Explicit Git file import did not complete");
        }
        BundleStore recovered = new BundleStore(disk);
        check(recovered.plan(bundle.id).getBoolean("installed") && imported.plan(bundle.id).getBoolean("installed") && fetched.get() == 0
                && imported.plan(bundle.id).getJSONArray("components").getJSONObject(0).getString("verifiedSha256").equals(sha("SHA-256", data)), "Explicit Git file import verifies through production transfers without network and survives storage restart");
        JSONObject second = DataFiles.copy(source).put("id", "git_shared").put("modelId", "git_shared"); ModelBundle shared = new ModelBundle(second); recovered.declare(shared);
        check(recovered.plan(shared.id).getLong("remainingBytes") == 0, "Another explicit recipe reuses an already verified Git object");
        String secondToken = recovered.request(shared.id); recovered.install(shared.id, secondToken); recovered.remove(bundle.id, true);
        check(recovered.plan(shared.id).getBoolean("installed"), "Removing one model preserves shared assets");
        RecipeCatalogue catalogue = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(templates.toPath()), StandardCharsets.UTF_8)));
        check(catalogue.list().length() == 44, "Forty-four signed data-only templates preserve existing routes and add speech / 3D recipes");
        for (int i = 0; i < catalogue.list().length(); i++) {
            JSONObject template = catalogue.list().getJSONObject(i), bindings = new JSONObject(); JSONArray requirements = template.getJSONArray("requirements"); String id = template.getString("id");
            for (int n = 0; n < requirements.length(); n++) { JSONObject r = requirements.getJSONObject(n); bindings.put(r.getString("role"), asset(r.getJSONArray("formats").getString(0), data)); }
            ModelBundle selected = catalogue.compose(id, bindings);
            if (id.equals("qwen3_tts_06b_base_cpu_v1")) {
                check(selected.component("talker").provides.contains("text_tokenizer") && selected.component("talker").provides.contains("code_predictor") && selected.component("talker").provides.contains("speaker_assets"), "Physical Talker explicitly provides three embedded dependencies");
                check(selected.tags().getJSONArray("dependency").toString().contains("dependency:audio_codec") && selected.tags().getJSONArray("dependency").toString().contains("dependency:text_tokenizer"), "Embedded and separate dependencies share independent tags");
                JSONObject invalidEmbedded = selected.json(); invalidEmbedded.getJSONArray("components").getJSONObject(0).put("provides", new JSONArray().put("../outside"));
                rejects(() -> new ModelBundle(invalidEmbedded), "Embedded roles use bounded identifiers, never paths");
            }
            check(selected.components.size() == requirements.length() + template.getJSONArray("fixedComponents").length(), "Every selected and fixed dependency is present");
            check(catalogue.compose(id, bindings).id.equals(selected.id), "The same explicit file selection has stable identity");
            check(selected.json().getJSONObject("evidence").getInt("physicalDeviceTests") == 0 && !selected.json().getJSONObject("uncensored").getBoolean("declared"), "File selection cannot create device or publisher verification");
            for (ModelBundle.Component file : selected.components) check(file.importPath.startsWith(file.role + "/"), "Import paths separate same-named files by role");
            String primary = template.getString("primaryRole"); JSONObject missing = DataFiles.copy(bindings); missing.remove(primary); rejects(() -> catalogue.compose(id, missing), "Required assets cannot be omitted");
            JSONObject extra = DataFiles.copy(bindings).put("shell", asset("bin", data)); rejects(() -> catalogue.compose(id, extra), "Unknown component roles cannot inject commands or executable providers");
            JSONObject badFormat = DataFiles.copy(bindings); badFormat.getJSONObject(primary).put("format", "python"); rejects(() -> catalogue.compose(id, badFormat), "Role format checks are native");
            JSONObject different = DataFiles.copy(bindings); different.getJSONObject(primary).put("repository", "fixture/other").put("url", different.getJSONObject(primary).getString("url").replace("fixture/data", "fixture/other"));
            check(!catalogue.compose(id, different).id.equals(selected.id), "Changed source metadata creates a distinct immutable selection");
        }
        rejects(() -> catalogue.template("unknown_template"), "Unknown templates cannot load unshipped engines");
        return passed;
    }
}
