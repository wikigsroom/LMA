package com.lma.app;

import com.lma.app.core.Protocol;
import java.io.File;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONObject;

/** Deterministic API fixtures exercise the production HF client, controller and durable store. */
public final class HubTest {
    private static final String REV = "0123456789abcdef0123456789abcdef01234567";
    private static final String HASH = String.join("", Collections.nCopies(64, "a"));
    private static final List<String> passed = new ArrayList<>();
    private interface Checked { void run() throws Exception; }
    private interface Condition { boolean value() throws Exception; }
    private static void check(boolean ok, String name) { if (!ok) throw new AssertionError(name); passed.add(name); System.out.println("PASS " + name); }
    private static void rejects(Checked operation, String name) throws Exception { try { operation.run(); } catch (Exception expected) { check(true, name); return; } throw new AssertionError("Not rejected: " + name); }
    private static void waitFor(Condition condition) throws Exception { long end = System.currentTimeMillis() + 7000; while (System.currentTimeMillis() < end) { if (condition.value()) return; Thread.sleep(10); } throw new AssertionError("Async request timed out"); }
    private static JSONObject repository(String id) throws Exception { return HubClient.model(new JSONObject().put("id", id).put("sha", REV).put("pipeline_tag", "text-generation").put("tags", new JSONArray())); }
    private static JSONObject entry(String path) { return new JSONObject().put("type", "file").put("path", path).put("size", 420000000).put("lfs", new JSONObject().put("oid", HASH)); }
    private static JSONObject command(String action) { return new JSONObject().put("action", action).put("requestId", action + System.nanoTime()); }
    public static void main(String[] args) throws Exception {
        Path root = Paths.get(args[0]), output = root.resolve("build/hub-tests"); Files.createDirectories(output);
        check(HubClient.query("https://huggingface.co/owner/model/tree/main").equals("owner/model"), "HF links resolve to repository identity");
        check(HubClient.query("owner/model").equals("owner/model") && HubClient.query("Qwen 中文").equals("Qwen 中文"), "Repository names and Unicode keywords are accepted");
        rejects(() -> HubClient.query("https://huggingface.co.evil/owner/model"), "Search rejects lookalike HF hosts");
        rejects(() -> HubClient.query("https://user@huggingface.co/owner/model"), "Search rejects URL credentials");
        rejects(() -> HubClient.repositoryId("owner/../model"), "Repository traversal is rejected");
        rejects(() -> HubClient.validPage("https://evil.test/api/models?cursor=x", "/api/models"), "Pagination cannot redirect to arbitrary hosts");
        rejects(() -> HubClient.validPage("https://huggingface.co/api/datasets?cursor=x", "/api/models"), "Pagination stays on the expected API path");
        rejects(() -> HubClient.validPage("http://huggingface.co/api/models", "/api/models"), "Pagination cannot downgrade HTTPS");
        check(HubClient.validPage("https://hf-mirror.com/api/models?cursor=x", "/api/models").startsWith(HubClient.ORIGIN), "Mirror pagination is canonicalized before source selection");
        check(Net.acceptsHubToken(new URL("https://huggingface.co/api/models")), "HF credentials are allowed at the official HTTPS origin");
        check(!Net.acceptsHubToken(new URL("https://hf-mirror.com/a")) && !Net.acceptsHubToken(new URL("https://cdn-lfs.huggingface.co/a")) && !Net.acceptsHubToken(new URL("https://huggingface.co:444/a")) && !Net.acceptsHubToken(new URL("http://huggingface.co/a")), "HF credentials are excluded from mirrors, CDNs, other ports and HTTP");
        List<String> addresses = new ArrayList<>();
        HubClient client = new HubClient("mirror", "", (address, source, token) -> {
            addresses.add(address);
            if (address.contains("/tree/")) return new HubClient.Response(new JSONArray().put(new JSONObject().put("type", "directory").put("path", "nested")).put(entry("README.md")).put(entry("nested/模型 Q4_K_M.gguf")).toString(), "<https://huggingface.co/api/models/owner/model/tree/" + REV + "?cursor=two>; rel=\"next\"", "hf-mirror.com");
            if (address.contains("/api/models/owner/model")) return new HubClient.Response(new JSONObject().put("id", "owner/model").put("sha", REV).put("pipeline_tag", "text-generation").toString(), null, "hf-mirror.com");
            return new HubClient.Response(new JSONArray().put(new JSONObject().put("id", "owner/model")).toString(), "<https://huggingface.co/api/models?cursor=two>; rel=\"next\"", "hf-mirror.com");
        });
        JSONObject result = client.search("中文 model", "gguf", "downloads", "");
        check(addresses.get(0).contains("filter=gguf") && addresses.get(0).contains("%E4%B8%AD%E6%96%87%20model"), "GGUF keyword search uses an encoded remote query");
        check(!result.getString("next").isEmpty() && result.getJSONArray("items").length() == 1, "HF Link pagination is retained");
        client.search("anything", "all", "likes", ""); check(!addresses.get(1).contains("filter=") && addresses.get(1).contains("sort=likes"), "All-format search does not impose the GGUF filter");
        client.search("owner/model", "all", "downloads", ""); check(addresses.get(2).endsWith("/api/models/owner/model"), "Exact repository search opens the repository directly");
        JSONObject repo = client.repository("owner/model"), files = client.files(repo, "");
        check(files.getJSONArray("items").length() == 1 && files.getString("next").contains("/tree/" + REV), "Only GGUF files are offered and file pagination remains commit-pinned");
        JSONObject file = files.getJSONArray("items").getJSONObject(0);
        check(file.getString("url").contains("/resolve/" + REV + "/nested/%E6%A8%A1%E5%9E%8B%20Q4_K_M.gguf") && file.getString("sha256").equals(HASH), "Download URL preserves nested paths and pins the publisher hash");
        check(file.getString("quant").equals("Q4_K_M") && file.getString("blocked").isEmpty(), "Quantization and downloadable size are exposed");
        rejects(() -> HubClient.file(repo, entry("../model.gguf")), "File traversal is rejected");
        rejects(() -> HubClient.file(repo, entry("folder\\model.gguf")), "Backslash model paths are rejected");
        rejects(() -> HubClient.file(repo, entry("bad\nmodel.gguf")), "Control characters in model paths are rejected");
        rejects(() -> HubClient.file(repo, entry("model.safetensors")), "Non-GGUF files cannot enter the native download selection");
        rejects(() -> HubClient.file(repo, entry("model.gguf").put("lfs", new JSONObject().put("oid", "bad-hash"))), "Invalid publisher hashes are rejected");
        check(!HubClient.file(repo, entry("model-00001-of-00003.gguf")).getString("blocked").isEmpty(), "Split GGUF files explain their unsupported status");
        check(!HubClient.file(repo, entry("mmproj-F16.gguf")).getString("blocked").isEmpty(), "Vision projectors cannot be loaded as text models");
        check(!HubClient.file(new JSONObject(repo.toString()).put("task", "automatic-speech-recognition"), entry("model.gguf")).getString("blocked").isEmpty(), "A GGUF speech task is not misrepresented as a chat model");
        rejects(() -> HubClient.selected(repo, HubClient.file(repo, entry("model.gguf").put("size", HubClient.MAX_FILE + 1))), "The downloader size limit is enforced before selection");
        JSONObject normal = HubClient.uncensored("owner/normal", new JSONArray()), marked = HubClient.uncensored("owner/normal", new JSONArray().put("abliterated"));
        check(!normal.getBoolean("detected") && marked.getBoolean("detected") && !marked.getBoolean("declared") && !marked.getBoolean("refusalRateTested"), "Metadata labels never become verified publisher claims or refusal measurements");
        JSONObject selected = HubClient.selected(repo, file);
        check(selected.getString("id").equals(HubClient.selected(repo, file).getString("id")) && Protocol.safeId(selected.getString("id")).startsWith("hf_") && !selected.getBoolean("recommended"), "HF imports have stable safe IDs and never join recommendations");
        Path storeFiles = Files.createTempDirectory(output, "store-");
        LmaApp app = new LmaApp(storeFiles.toFile(), root.resolve("app/src/main/assets").toFile(), root.resolve("build/test-libraries").toFile());
        String id = app.store.addHub(selected); int count = app.store.snapshot().length();
        check(app.store.addHub(selected).equals(id) && app.store.snapshot().length() == count, "Selecting the same pinned HF file does not duplicate local records");
        rejects(() -> app.store.addHub(new JSONObject(selected.toString()).put("url", "https://evil.test/model.gguf")), "The durable store rejects a substituted download URL");
        Files.write(app.store.modelFile(id).toPath(), new byte[24]);
        LmaApp reopened = new LmaApp(storeFiles.toFile(), root.resolve("app/src/main/assets").toFile(), root.resolve("build/test-libraries").toFile());
        check(reopened.store.model(id).getString("repository").equals("owner/model") && reopened.store.snapshot().getJSONObject(count - 1).getBoolean("installed"), "HF entries and installed status survive store recreation");
        reopened.store.remove(id); rejects(() -> reopened.store.model(id), "Deleting a HF entry removes its private file and durable metadata");
        JSONArray curated = new JSONObject(new String(Files.readAllBytes(root.resolve("app/src/main/assets/models.json")), StandardCharsets.UTF_8)).getJSONArray("models");
        List<String> recommended = new ArrayList<>(); for (int i = 0; i < curated.length(); i++) if (curated.getJSONObject(i).getBoolean("recommended")) recommended.add(curated.getJSONObject(i).getString("id"));
        check(recommended.toString().equals("[m08, m06, m01]"), "Original recommendation IDs and order are preserved");
        CountDownLatch entered = new CountDownLatch(1), release = new CountDownLatch(1);
        HubClient delayed = new HubClient("mirror", "", (address, source, token) -> {
            if (address.contains("search=old")) { entered.countDown(); if (!release.await(5, TimeUnit.SECONDS)) throw new Exception("Fixture timeout"); }
            String name = address.contains("search=old") ? "owner/old" : "owner/new";
            return new HubClient.Response(new JSONArray().put(new JSONObject().put("id", name)).toString(), null, "fixture");
        });
        try (HubCatalog catalog = new HubCatalog(app, () -> delayed)) {
            catalog.dispatch(command("hubSearch").put("query", "old")); check(entered.await(3, TimeUnit.SECONDS), "Discovery executes outside the UI caller");
            catalog.dispatch(command("hubSearch").put("query", "new")); release.countDown();
            waitFor(() -> !catalog.snapshot().getBoolean("searching"));
            check(catalog.snapshot().getJSONArray("items").getJSONObject(0).getString("id").equals("owner/new"), "A stale search cannot replace the latest query results");
        }
        try (HubCatalog catalog = new HubCatalog(app, () -> client)) {
            catalog.dispatch(command("hubFiles").put("repository", "owner/model")); waitFor(() -> !catalog.snapshot().getJSONObject("files").getBoolean("loading"));
            JSONObject selection = command("hubDownload").put("repository", "owner/model").put("revision", REV).put("path", file.getString("path"));
            check(catalog.selected(selection).getString("url").equals(selected.getString("url")), "Download selection is resolved from native repository metadata");
            rejects(() -> catalog.selected(new JSONObject(selection.toString()).put("path", "invented.gguf")), "A WebView command cannot invent a file download");
            rejects(() -> catalog.selected(new JSONObject(selection.toString()).put("revision", HASH)), "A stale WebView revision cannot select a file");
            catalog.dispatch(command("hubFilePage").put("direction", "next")); waitFor(() -> !catalog.snapshot().getJSONObject("files").getBoolean("loading"));
            check(catalog.snapshot().getJSONObject("files").getInt("page") == 2 && catalog.snapshot().getJSONObject("files").getBoolean("previous"), "File pages track backward navigation without unpinning the commit");
            catalog.dispatch(command("hubFilePage").put("direction", "previous")); waitFor(() -> !catalog.snapshot().getJSONObject("files").getBoolean("loading"));
            check(catalog.snapshot().getJSONObject("files").getInt("page") == 1, "Returning to the first file page works");
            catalog.dispatch(command("hubToken").put("token", "hf_TEST_ONLY")); check(app.prefs.getString("hfToken", "").equals("hf_TEST_ONLY"), "Optional HF credentials are saved independently from model metadata");
            rejects(() -> catalog.dispatch(command("hubToken").put("token", "hf_bad\r\nInjected: value")), "HF credentials cannot inject HTTP headers");
            catalog.dispatch(command("hubToken").put("token", "")); check(app.prefs.getString("hfToken", "missing").isEmpty(), "Clearing HF credentials is explicit and durable");
        }
        try (HubCatalog catalog = new HubCatalog(app, () -> new HubClient("mirror", "", (a, s, t) -> { throw new java.io.IOException("Network fixture unavailable"); }))) {
            catalog.dispatch(command("hubSearch")); waitFor(() -> !catalog.snapshot().getBoolean("searching"));
            check(catalog.snapshot().getString("error").contains("unavailable") && app.lastError.isEmpty(), "HF network failures stay in the discovery panel without interrupting inference");
        }
        for (String name : HubRecipeTest.run(root)) { passed.add(name); System.out.println("PASS " + name); }
        JSONObject report = new JSONObject().put("passed", passed.size()).put("checks", passed).put("network", "deterministic API fixtures").put("android_framework", "host adapters").put("phone_inference_tested", false);
        Files.write(output.resolve("results.json"), (report.toString(2) + "\n").getBytes(StandardCharsets.UTF_8));
    }
}
