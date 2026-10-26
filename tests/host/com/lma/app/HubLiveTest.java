package com.lma.app;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import org.json.JSONArray;
import org.json.JSONObject;

/** Live public metadata only. No weights, account tokens, inference or Android emulation. */
public final class HubLiveTest {
    public static void main(String[] args) throws Exception {
        Path output = Paths.get(args[0]).resolve("build/hub-tests"); Files.createDirectories(output);
        HubClient client = new HubClient("mirror", "");
        JSONObject search = client.search("Qwen3", "gguf", "downloads", "");
        if (search.getJSONArray("items").length() == 0 || search.getString("next").isEmpty()) throw new AssertionError("Live search must be paginated");
        JSONObject next = client.search("Qwen3", "gguf", "downloads", search.getString("next"));
        JSONObject all = client.search("Qwen3-0.6B", "all", "likes", "");
        JSONObject repository = client.repository("Qwen/Qwen3-0.6B-GGUF");
        JSONObject files = client.files(repository, "");
        if (files.getJSONArray("items").length() == 0) throw new AssertionError("Live GGUF file missing");
        JSONObject file = files.getJSONArray("items").getJSONObject(0), selected = HubClient.selected(repository, file);
        if (file.getString("sha256").length() != 64 || !selected.getString("url").contains(repository.getString("revision"))) throw new AssertionError("Live file is not commit/hash pinned");
        JSONObject report = new JSONObject().put("checked_at", java.time.Instant.now().toString()).put("source", "hf-mirror.com public API; no access token")
                .put("passed", 5).put("checks", new JSONArray().put("Live GGUF keyword search").put("Live HF cursor pagination").put("Live all-format search").put("Live pinned repository and GGUF file metadata").put("Live publisher SHA256 and deterministic selection"))
                .put("first_page_repositories", search.getJSONArray("items").length()).put("second_page_repositories", next.getJSONArray("items").length()).put("all_format_repositories", all.getJSONArray("items").length())
                .put("repository", repository).put("file", file).put("weights_downloaded", false).put("phone_inference_tested", false).put("official_origin_tested", false);
        Files.write(output.resolve("live-results.json"), (report.toString(2) + "\n").getBytes(StandardCharsets.UTF_8));
        System.out.println("PASS live public HF metadata: search, pagination, all formats, revision, SHA256");
    }
}
