package com.lma.app;

import org.json.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Production controller exercised with metadata fixtures; no weights and no Android runtime. */
public final class HubRecipeTest {
    private static final String REV = "0123456789abcdef0123456789abcdef01234567";
    private static final String OID = String.join("", Collections.nCopies(40, "b")), SHA = String.join("", Collections.nCopies(64, "a"));
    private static final List<String> checks = new ArrayList<>();
    private interface Action { void run() throws Exception; }
    private interface Condition { boolean get() throws Exception; }
    private static void check(boolean ok, String name) { if (!ok) throw new AssertionError(name); checks.add(name); }
    private static void rejects(Action action, String name) throws Exception { try { action.run(); } catch (Exception e) { checks.add(name); return; } throw new AssertionError(name); }
    private static void waitFor(Condition condition) throws Exception { long end = System.nanoTime() + 5000000000L; while (!condition.get()) { if (System.nanoTime() > end) throw new AssertionError("Metadata fixture timed out"); Thread.sleep(10); } }
    private static JSONObject command(String action) { return new JSONObject().put("action", action).put("requestId", UUID.randomUUID().toString()); }
    private static JSONObject entry(String path) { return new JSONObject().put("type", "file").put("path", path).put("size", 128).put("oid", OID); }
    private static void files(HubCatalog catalog, String repository) throws Exception { catalog.dispatch(command("hubFiles").put("repository", repository)); waitFor(() -> !catalog.snapshot().getJSONObject("files").getBoolean("loading")); check(catalog.snapshot().getJSONObject("files").optString("error").isEmpty(), "Component metadata request completes"); }
    private static String draft(HubCatalog catalog) throws Exception { return catalog.snapshot().getJSONObject("recipeDraft").getString("draftId"); }
    private static JSONObject binding(HubCatalog catalog, String role, String path) throws Exception {
        JSONObject repo = catalog.snapshot().getJSONObject("files").getJSONObject("repository");
        return command("hubRecipeBind").put("draftId", draft(catalog)).put("role", role).put("repository", repo.getString("id")).put("revision", repo.getString("revision")).put("path", path);
    }
    public static List<String> run(Path root) throws Exception {
        checks.clear(); JSONObject repo = new JSONObject().put("id", "fixture/model").put("revision", REV).put("uncensored", new JSONObject().put("declared", false).put("detected", true));
        JSONObject regular = HubClient.asset(repo, entry("tokens.txt"));
        check(regular.getString("gitBlobSha1").equals(OID) && !regular.has("sha256"), "Regular HF Git identity is not labeled publisher SHA256");
        check(HubClient.asset(repo, entry("tokenizer.model")).getString("format").equals("sentencepiece"), "SentencePiece remains user-selected model data");
        check(HubClient.asset(repo, entry("weights.data")).getString("format").equals("onnx_data"), "External ONNX weights are selectable data components");
        check(HubClient.asset(repo, entry("transformer.mnn")).getString("format").equals("mnn"), "MNN graphs are selectable user data");
        check(HubClient.asset(repo, entry("llm/llm.mnn.weight")).getString("format").equals("mnn_data"), "MNN external weights are selectable separately");
        JSONObject lfs = HubClient.asset(repo, entry("model.onnx").put("lfs", new JSONObject().put("oid", SHA).put("size", 128)));
        check(lfs.getString("sha256").equals(SHA) && !lfs.has("gitBlobSha1"), "LFS files retain publisher SHA256");
        check(!HubClient.asset(repo, entry("model.onnx").put("lfs", new JSONObject().put("oid", "bad"))).getString("blocked").isEmpty(), "Bad LFS digests cannot fall back to pointer blob identity");
        check(!HubClient.asset(repo, entry("model.onnx").put("lfs", new JSONObject().put("oid", SHA).put("size", 127))).getString("blocked").isEmpty(), "Conflicting LFS size is blocked");
        check(!HubClient.asset(repo, entry("tokens.txt").put("oid", "")).getString("blocked").isEmpty(), "Regular files require a verifiable Git blob ID");
        check(!HubClient.asset(repo, entry("runner.py")).getString("blocked").isEmpty(), "Executable/source formats are not selectable data components");
        check(!HubClient.asset(repo, entry("tokens.txt").put("size", 1.5)).getString("blocked").isEmpty(), "Fractional declared byte lengths are blocked");
        rejects(() -> HubClient.asset(repo, entry("../tokens.txt")), "Traversal metadata cannot become a component");
        rejects(() -> HubClient.asset(new JSONObject(repo.toString()).put("revision", "main"), entry("tokens.txt")), "Component metadata requires a frozen revision");
        JSONObject missingSize = entry("tokens.txt"); missingSize.remove("size");
        check(!HubClient.asset(repo, missingSize).getString("blocked").isEmpty(), "Missing size blocks a component without failing the entire file page");
        check(!HubClient.asset(repo, entry("tokens.txt").put("size", "128")).getString("blocked").isEmpty(), "String sizes are not trusted numeric component metadata");
        check(!HubClient.asset(repo, entry("model.onnx").put("lfs", "invalid")).getString("blocked").isEmpty(), "Malformed LFS metadata cannot select the Git pointer instead");
        AtomicInteger contentRequests = new AtomicInteger();
        HubClient client = new HubClient("official", "", (address, source, token) -> {
            if (address.contains("/resolve/")) { contentRequests.incrementAndGet(); throw new AssertionError("Browsing fetched asset content"); }
            String name = address.contains("fixture/voices") ? "fixture/voices" : "fixture/model";
            if (address.contains("/tree/")) {
                JSONArray items = address.contains("cursor=two") ? new JSONArray().put(entry("extra.json")) : new JSONArray().put(entry("model.onnx").put("lfs", new JSONObject().put("oid", SHA))).put(entry("tokens.txt")).put(entry("voices.bin"));
                String link = address.contains("cursor=two") ? null : "<https://huggingface.co/api/models/" + name + "/tree/" + REV + "?cursor=two>; rel=\"next\"";
                return new HubClient.Response(items.toString(), link, "fixture");
            }
            return new HubClient.Response(new JSONObject().put("id", name).put("sha", REV).put("pipeline_tag", "text-to-speech").toString(), null, "fixture");
        });
        Path disk = root.resolve("build/hub-tests/recipes-" + UUID.randomUUID());
        LmaApp app = new LmaApp(disk.toFile(), root.resolve("app/src/main/assets").toFile(), root.resolve("build/test-libraries").toFile());
        try (HubCatalog catalog = new HubCatalog(app, () -> client)) {
            check(catalog.snapshot().getJSONArray("recipeTemplates").length() == 29, "HF controller loads signed data-only recipe templates including native Qwen, MOSS speech and sound effects");
            files(catalog, "fixture/model"); check(catalog.snapshot().getJSONObject("files").getJSONArray("assets").length() == 3, "HF file pages expose ONNX, binary and text component metadata");
            catalog.dispatch(command("hubRecipeStart").put("repository", "fixture/model")); String initial = draft(catalog);
            catalog.dispatch(command("hubRecipeTemplate").put("draftId", initial).put("templateId", "kokoro_en_cpu_v1"));
            check(!draft(catalog).equals(initial), "Changing templates invalidates old component commands");
            rejects(() -> catalog.dispatch(binding(catalog, "model", "model.onnx").put("draftId", initial)), "Stale template selection is rejected");
            rejects(() -> catalog.dispatch(command("hubRecipeDeclare").put("draftId", draft(catalog))), "Incomplete selections cannot be declared");
            rejects(() -> catalog.dispatch(binding(catalog, "model", "missing.onnx")), "Only files on the current native metadata page can bind");
            rejects(() -> catalog.dispatch(binding(catalog, "model", "tokens.txt")), "Native role constraints reject a text file as model weights");
            rejects(() -> catalog.dispatch(binding(catalog, "unknown_role", "tokens.txt")), "Unknown component roles are rejected");
            catalog.dispatch(binding(catalog, "model", "model.onnx")); catalog.dispatch(binding(catalog, "tokens", "tokens.txt"));
            JSONObject stalePage = binding(catalog, "voices", "voices.bin");
            catalog.dispatch(command("hubFilePage").put("direction", "next")); waitFor(() -> !catalog.snapshot().getJSONObject("files").getBoolean("loading"));
            rejects(() -> catalog.dispatch(stalePage), "A file removed by pagination cannot bind from a stale page");
            files(catalog, "fixture/voices");
            rejects(() -> catalog.dispatch(stalePage), "A different repository invalidates stale page commands");
            check(catalog.snapshot().getJSONObject("recipeDraft").getJSONObject("bindings").length() == 2, "Cross-repository browsing preserves already frozen choices");
            catalog.dispatch(binding(catalog, "voices", "voices.bin"));
            JSONObject declaration = command("hubRecipeDeclare").put("draftId", draft(catalog)); catalog.dispatch(declaration);
            String id = declaration.getJSONObject("result").getString("bundleId"); JSONObject selected = app.bundles.bundle(id).json();
            check(selected.getJSONArray("components").length() == 4 && selected.getString("schema").equals("lma.model-bundle/2"), "Declaration includes all user-selected files and the disclosed fixed lexicon");
            check(selected.getJSONArray("components").getJSONObject(1).getString("repository").equals("fixture/voices"), "A selected component retains its own source repository");
            check(!app.bundles.snapshot().getJSONObject(0).has("transfer") && !app.bundles.plan(id).getBoolean("installed") && contentRequests.get() == 0, "Browsing and declaration never start a transfer or install a model");
            JSONObject repeat = command("hubRecipeDeclare").put("draftId", draft(catalog)); catalog.dispatch(repeat);
            check(repeat.getJSONObject("result").getString("bundleId").equals(id) && app.bundles.snapshot().length() == 1, "Repeated explicit declaration is idempotent");
        }
        return new ArrayList<>(checks);
    }
}
