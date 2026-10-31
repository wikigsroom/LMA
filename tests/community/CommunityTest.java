package com.lma.app;

import com.lma.app.core.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.json.*;

/** Production descriptors and request planning only; never opens a trained checkpoint. */
public final class CommunityTest {
    private static int passed;
    private static void check(boolean value) { if (!value) throw new AssertionError("Community contract " + (passed + 1)); passed++; }
    private interface Attempt { void run() throws Exception; }
    private static void rejects(Attempt fn) throws Exception { try { fn.run(); } catch (IllegalArgumentException error) { passed++; return; } throw new AssertionError("Expected rejected content declaration"); }
    private static JSONObject read(Path p) throws Exception { return new JSONObject(new String(Files.readAllBytes(p), StandardCharsets.UTF_8)); }
    public static void main(String[] args) throws Exception {
        Path root = Paths.get(args[0]);
        JSONArray all = read(root.resolve("app/src/main/assets/model-bundles.json")).getJSONArray("bundles");
        JSONArray extra = read(root.resolve("catalogue/community-bundles.json")).getJSONArray("bundles");
        check(all.length() == 67); check(extra.length() == 44);
        Set<String> ids = new HashSet<>(), families = new HashSet<>(); int images = 0, videos = 0, adult = 0;
        for (int i = 0; i < extra.length(); i++) {
            ModelBundle b = new ModelBundle(extra.getJSONObject(i));
            check(ids.add(b.id));
            JSONObject m = b.json(), c = m.getJSONObject("content");
            families.add(m.getJSONObject("community").getString("family"));
            String type = b.tasks.contains("video") ? "video.generate" : "image.generate";
            SdSpec.validate(b, type); check(true);
            if (type.equals("image.generate")) images++; else videos++;
            if (c.getString("classification").equals("nsfw")) adult++;
            check(!c.getBoolean("modelQualityTested"));
            check(m.getJSONObject("evidence").getInt("physicalDeviceTests") == 0);
            check(m.getJSONObject("evidence").getJSONObject("header").getInt("trainedWeightBytesFetched") == 0);
            check(b.tags().getJSONArray("content").getString(0).equals("content:" + c.getString("classification")));
            JSONObject p = b.parameters().normalize(new JSONObject(), new JSONObject()).getJSONObject("values");
            JSONObject request = new JSONObject().put("bundleId", b.id).put("type", type).put("parameters", p).put("input", new JSONObject().put("prompt", "A quiet mountain landscape"));
            JSONObject planned = SdSpec.prepare(b, Collections.emptyList(), request);
            check(planned.getString("bundleId").equals(b.id));
            JSONObject over = b.parameters().normalize(new JSONObject(), new JSONObject().put("steps", 9999)).getJSONObject("values");
            check(over.getInt("steps") == 200);
            for (ModelBundle.Component component : b.components) {
                check(component.sha256.length() == 64); check(component.revision.matches("[a-f0-9]{40}"));
                check(component.url.contains("/resolve/" + component.revision + "/"));
            }
        }
        check(images == 30 && videos == 14 && adult == 28 && families.size() == 14);
        JSONObject hinted = ContentMetadata.repository("owner/nsfw-model", new JSONArray());
        check(hinted.getString("basis").equals("repository_hint")); ContentMetadata.validate(hinted);
        JSONObject flagged = ContentMetadata.repository("owner/model", new JSONArray().put("not-for-all-audiences"));
        check(flagged.getString("classification").equals("sensitive")); ContentMetadata.validate(flagged);
        JSONObject tagged = ContentMetadata.repository("owner/model", new JSONArray().put("nsfw"));
        check(tagged.getString("basis").equals("hf_nsfw_tag")); ContentMetadata.validate(tagged);
        JSONObject unknown = ContentMetadata.repository("owner/unfiltered-model", new JSONArray().put("text-to-image"));
        check(unknown.getString("classification").equals("unclassified"));
        ContentMetadata.validate(unknown);
        for (String link : Arrays.asList("javascript:alert(1)", "http://huggingface.co/o/m", "https://localhost/card", "https://huggingface.co@evil.invalid/o/m")) {
            rejects(() -> ContentMetadata.validate(new JSONObject(tagged.toString()).put("sourceUrl", link)));
        }
        rejects(() -> ContentMetadata.validate(new JSONObject(tagged.toString()).put("modelQualityTested", true)));
        rejects(() -> ContentMetadata.validate(new JSONObject(flagged.toString()).put("classification", "nsfw")));
        rejects(() -> ContentMetadata.validate(new JSONObject(unknown.toString()).put("basis", "publisher_card")));
        JSONObject hf = HubClient.model(new JSONObject().put("id", "publisher/model").put("tags", new JSONArray().put("nsfw")).put("pipeline_tag", "text-to-video"));
        check(hf.getJSONArray("taskTags").getString(0).equals("video")); check(hf.getJSONObject("content").getString("basis").equals("hf_nsfw_tag"));
        RecipeCatalogue recipes = new RecipeCatalogue(read(root.resolve("app/src/main/assets/recipe-templates.json")));
        ModelBundle sample = new ModelBundle(extra.getJSONObject(0));
        JSONObject primary = new JSONObject(sample.component("model").repository.isEmpty() ? "{}" : extra.getJSONObject(0).getJSONArray("components").getJSONObject(0).toString());
        primary.put("content", tagged);
        ModelBundle composed = recipes.compose("sd15_checkpoint_cpu_v1", new JSONObject().put("model", primary));
        check(composed.json().getJSONObject("content").getString("classification").equals("nsfw"));
        primary.put("content", unknown);
        ModelBundle other = recipes.compose("sd15_checkpoint_cpu_v1", new JSONObject().put("model", primary));
        check(!composed.id.equals(other.id));
        System.out.println(new JSONObject().put("passed", passed).put("bundles", extra.length()).put("images", images).put("videos", videos).put("nsfwLabels", adult).put("families", families.size()).put("modelInference", false).put("physicalAndroid", false));
    }
}
