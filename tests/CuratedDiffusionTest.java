package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.File;
import java.nio.file.Files;
import java.util.*;

/** Production asset-store upgrade and pairing checks. No weights or model inference. */
public final class CuratedDiffusionTest {
    private static int checks;
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); checks++; }
    private static JSONObject read(File file) throws Exception { return new JSONObject(new String(Files.readAllBytes(file.toPath()), "UTF-8")); }
    public static int run(File root, File catalogue) throws Exception {
        checks = 0;
        File repo = catalogue.getAbsoluteFile().getParentFile().getParentFile();
        String[][] profiles = {
            {"sdxl_base_q4_0_catalogue_v1", "sd_variants_trained/manifests/sdxl_base_q4_0.json"},
            {"sd15_pixelart_redmond_catalogue_v1", "sd_variants_trained/manifests/sd15_style_pixelart.json"},
            {"sdxl_pixelart_nerijs_catalogue_v1", "sd_variants_trained/manifests/sdxl_style_pixelart.json"},
            {"sd15_lcm_lora_catalogue_v1", "sd_variants_trained/manifests/sd15_lcm_lora.json"},
            {"sdxl_lcm_lora_catalogue_v1", "sd_variants_trained/manifests/sdxl_lcm_lora.json"},
            {"sd_turbo_q8_0_catalogue_v1", "sd_distilled_trained/sd_turbo_q8_0.json"}
        };
        BundleStore store = new BundleStore(new File(root, "curated-upgrade"));
        Map<String, JSONObject> originals = new LinkedHashMap<>();
        for (String[] profile : profiles) {
            JSONObject old = read(new File(repo, "research/" + profile[1]));
            ModelBundle imported = new ModelBundle(old); store.declare(imported); originals.put(imported.id, old);
            store.saveSettings(imported.id, new JSONObject().put(AdapterSpec.isAdapter(imported) ? "scale" : "width", AdapterSpec.isAdapter(imported) ? 0.75 : 640));
        }
        JSONArray entries = read(catalogue).getJSONArray("bundles");
        for (int i = 0; i < entries.length(); i++) store.declare(new ModelBundle(entries.getJSONObject(i)));
        BundleStore restored = new BundleStore(new File(root, "curated-upgrade"));
        check(restored.snapshot().length() == entries.length() + profiles.length, "App catalogue refresh coexists with every old imported immutable ID");
        for (Map.Entry<String, JSONObject> old : originals.entrySet()) {
            check(DataFiles.canonical(restored.bundle(old.getKey()).json()).equals(DataFiles.canonical(old.getValue())), "Old imported manifests are unchanged");
            String key = old.getValue().has("adapter") ? "scale" : "width";
            check(restored.settings(old.getKey()).getJSONObject("values").getDouble(key) == (key.equals("scale") ? 0.75 : 640), "Saved settings survive the refresh and store restart");
        }
        ModelBundle sd15 = restored.bundle("sd15_ss_q4_0_r031b5f5"), sdxl = restored.bundle(profiles[0][0]);
        for (String[] profile : profiles) {
            ModelBundle current = restored.bundle(profile[0]); JSONObject old = read(new File(repo, "research/" + profile[1]));
            check(!current.id.equals(old.getString("id")) && !current.modelId.equals(old.getString("modelId")), "Curated metadata uses fresh bundle and model identities");
            check(DataFiles.canonical(current.json().getJSONArray("components")).equals(DataFiles.canonical(old.getJSONArray("components"))), "Curated assets retain complete exact trained-host URLs, pins, sizes and hashes");
            check(DataFiles.canonical(current.parameters().json()).equals(DataFiles.canonical(old.getJSONObject("parameters"))), "Curated parameters preserve the checked native recipe contract");
            check(!restored.plan(current.id).getBoolean("installed") && !restored.record(current.id).has("transfer"), "Browsing/catalogue declaration neither installs nor downloads a model");
            check(!current.json().getJSONObject("resources").getBoolean("estimateKnown") && current.json().getJSONObject("evidence").getInt("physicalDeviceTests") == 0, "Unknown phone resources and device evidence remain explicit");
            if (AdapterSpec.isAdapter(current)) {
                AdapterSpec.requirePair(current.architecture.equals("sd15") ? sd15 : sdxl, current); checks++;
                boolean rejected = false;
                try { AdapterSpec.requirePair(current.architecture.equals("sd15") ? sdxl : sd15, current); } catch (IllegalArgumentException expected) { rejected = true; }
                check(rejected, "Cross-architecture bases are rejected by production pairing");
                check(restored.settings(current.id).getJSONObject("values").getDouble("scale") == old.getJSONObject("parameters").getJSONObject("fields").getJSONObject("scale").getDouble("default"), "New LoRA defaults do not inherit old imported settings");
            }
        }
        return checks;
    }
}
