package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.nio.file.Files;
import java.util.*;

/** Exercises production selection/storage contracts with arbitrary bytes, never LoRA inference. */
public final class AdapterTest {
    private static int passed;
    private interface Action { void run() throws Exception; }
    private static void check(boolean test, String message) { if (!test) throw new AssertionError(message); passed++; }
    private static void rejects(Action action, String message) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(message); }
    public static JSONObject manifest(String id, String arch, boolean adapter) throws Exception {
        byte[] data = ("fixture bytes, not a model: " + id).getBytes("UTF-8");
        String sha = Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(data));
        JSONObject component = new JSONObject().put("role", adapter ? "lora" : "model").put("path", id + ".safetensors").put("format", "safetensors").put("bytes", data.length).put("sha256", sha);
        JSONObject scale = new JSONObject().put("type", "number").put("default", 0.75).put("minimum", -2).put("maximum", 2).put("presets", new JSONArray().put(0.5).put(0.75).put(1));
        JSONObject manifest = new JSONObject().put("schema", ModelBundle.SCHEMA).put("id", id).put("modelId", id).put("recipeId", id + "_recipe").put("name", id).put("engine", "sd_cpp").put("architecture", arch).put("pipeline", adapter ? "lora" : arch).put("backend", "cpu").put("tasks", new JSONArray().put("image")).put("components", new JSONArray().put(component)).put("parameters", new JSONObject().put("fields", adapter ? new JSONObject().put("scale", scale) : new JSONObject()));
        if (adapter) manifest.put("adapter", new JSONObject().put("schema", "lma.adapter/1").put("kind", "lora").put("baseArchitectures", new JSONArray().put(arch)).put("basePipelines", new JSONArray().put(arch)));
        return manifest;
    }
    private static JSONObject request(String base, String... adapters) throws Exception {
        JSONArray selected = new JSONArray(); for (String id : adapters) selected.put(new JSONObject().put("bundleId", id));
        return new JSONObject().put("bundleId", base).put("type", "image.generate").put("input", new JSONObject().put("prompt", "new fixture prompt")).put("parameters", new JSONObject()).put("adapters", selected).put("allowUnmeasured", true);
    }
    private static void install(BundleStore store, ModelBundle bundle) throws Exception {
        store.declare(bundle); String token = store.request(bundle.id);
        for (ModelBundle.Component component : bundle.components) {
            Files.write(store.partial(component.sha256).toPath(), ("fixture bytes, not a model: " + bundle.id).getBytes("UTF-8"));
            store.accept(bundle.id, token, component, store.partial(component.sha256));
        }
        store.install(bundle.id, token);
    }
    private static JSONObject entry(BundleStore store, String id) throws Exception {
        JSONArray all = store.snapshot(); for (int i = 0; i < all.length(); i++) if (all.getJSONObject(i).getString("id").equals(id)) return all.getJSONObject(i);
        throw new AssertionError("Missing entry");
    }
    public static int run(File root) throws Exception {
        ModelBundle sd15 = new ModelBundle(manifest("base15", "sd15", false)), sdxl = new ModelBundle(manifest("basexl", "sdxl", false));
        ModelBundle a15 = new ModelBundle(manifest("adapter15", "sd15", true)), axl = new ModelBundle(manifest("adapterxl", "sdxl", true));
        AdapterSpec.requirePair(sd15, a15); AdapterSpec.requirePair(sdxl, axl); check(true, "SD 1.5 and SDXL adapter declarations resolve through one contract");
        check(a15.tags().getJSONArray("dependency").toString().contains("dependency:base_model"), "Adapters retain image output tags and an explicit base dependency");
        rejects(() -> AdapterSpec.requirePair(sd15, axl), "Cross-family pairing fails before inference");
        rejects(() -> AdapterSpec.requirePair(a15, a15), "Adapters cannot be bases");
        JSONObject limited = manifest("limited", "sd15", true); limited.getJSONObject("adapter").put("baseModelIds", new JSONArray().put("another_model"));
        rejects(() -> AdapterSpec.requirePair(sd15, new ModelBundle(limited)), "Model-specific training restrictions are enforced");
        JSONObject lcm = manifest("lcm", "sd15", true); lcm.getJSONObject("adapter").put("basePipelines", new JSONArray().put("sd15_lcm"));
        rejects(() -> AdapterSpec.requirePair(sd15, new ModelBundle(lcm)), "An LCM-only declaration cannot silently use a plain SD recipe");
        AdapterSpec.requirePair(new ModelBundle(manifest("lcm_base", "sd15", false).put("pipeline", "sd15_lcm")), new ModelBundle(lcm)); check(true, "A matching LCM base recipe can be paired");
        JSONObject wide = manifest("wide", "sd15", true); wide.getJSONObject("parameters").getJSONObject("fields").getJSONObject("scale").put("maximum", 99);
        rejects(() -> new ModelBundle(wide), "Imported adapter schemas cannot expand the engine scale range");
        JSONObject future = manifest("future", "sd15", true); future.getJSONObject("adapter").put("schema", "lma.adapter/2");
        rejects(() -> new ModelBundle(future), "Unknown adapter versions fail");
        JSONObject runner = manifest("runner", "sd15", true); runner.getJSONObject("adapter").put("command", "execute");
        rejects(() -> new ModelBundle(runner), "Adapter metadata cannot supply commands");
        JSONObject mismatch = manifest("wrong", "sd15", true); mismatch.getJSONObject("adapter").put("basePipelines", new JSONArray().put("sdxl"));
        rejects(() -> new ModelBundle(mismatch), "Declared architecture and pipeline must agree");
        JSONObject duplicate = manifest("duplicate", "sd15", true); duplicate.getJSONObject("adapter").getJSONArray("baseArchitectures").put("sd15");
        rejects(() -> new ModelBundle(duplicate), "Compatibility lists reject duplicates");
        JSONObject wrongRole = manifest("role", "sd15", true); wrongRole.getJSONArray("components").getJSONObject(0).put("role", "model");
        rejects(() -> new ModelBundle(wrongRole), "Adapters declare adapter weights rather than a standalone model role");
        JSONObject extraField = manifest("extra", "sd15", true); extraField.getJSONObject("parameters").getJSONObject("fields").put("threads", new JSONObject().put("type", "integer").put("default", 2));
        rejects(() -> new ModelBundle(extraField), "Adapter settings cannot masquerade as base generation settings");
        TaskInput.validate(request(sd15.id, a15.id)); check(true, "The public task contract admits explicit peer selection");
        rejects(() -> TaskInput.validate(request(sd15.id, a15.id, a15.id)), "Duplicate LoRAs are rejected");
        rejects(() -> TaskInput.validate(request(sd15.id, sd15.id)), "Self dependency is rejected");
        JSONObject unknown = request(sd15.id, a15.id); unknown.getJSONArray("adapters").getJSONObject(0).put("path", "/outside/file");
        rejects(() -> TaskInput.validate(unknown), "API clients cannot supply model paths");
        JSONObject badScale = request(sd15.id, a15.id); badScale.getJSONArray("adapters").getJSONObject(0).put("scale", "NaN");
        rejects(() -> TaskInput.validate(badScale), "Scale is a finite JSON number");
        rejects(() -> TaskInput.validate(request(sd15.id, a15.id).put("type", "speech.synthesize")), "Speech tasks cannot silently ignore LoRAs");
        rejects(() -> TaskInput.validate(request(sd15.id, "a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9")), "Nine adapters exceed the native guard");
        BundleStore store = new BundleStore(new File(root, "adapter-assets")); install(store, sd15); install(store, a15); install(store, sdxl); install(store, axl);
        JSONObject input = request(sd15.id, a15.id), prepared = ModelSelection.prepare(store, sd15, input);
        check(prepared.getJSONArray("adapters").getJSONObject(0).getDouble("scale") == 0.75, "Omitted scale freezes the adapter's saved default");
        store.saveSettings(a15.id, new JSONObject().put("scale", -1.25));
        check(prepared.getJSONArray("adapters").getJSONObject(0).getDouble("scale") == 0.75, "Later per-adapter settings do not change queued scales");
        check(ModelSelection.prepare(store, sd15, input).getJSONArray("adapters").getJSONObject(0).getDouble("scale") == -1.25, "New tasks use the newly saved independent scale");
        JSONObject excessive = request(sd15.id, a15.id); excessive.getJSONArray("adapters").getJSONObject(0).put("scale", 100);
        JSONObject clamped = ModelSelection.prepare(store, sd15, excessive);
        check(clamped.getJSONArray("adapters").getJSONObject(0).getDouble("scale") == 2 && clamped.getJSONArray("adapterAdjustments").length() == 1, "Over-limit scale is clamped to the adapter's declared upper bound with evidence");
        check(!excessive.has("adapterAdjustments") && excessive.getJSONArray("adapters").getJSONObject(0).getInt("scale") == 100, "Preparation does not mutate caller-owned request data");
        rejects(() -> ModelSelection.prepare(store, sdxl, request(sd15.id, axl.id)), "Base manifest must match the selected ID");
        check(a15.tags().getJSONArray("capability").toString().contains("image_adapter") && a15.tags().getString("kind").equals("kind:adapter"), "Adapter capability/kind tags derive from the checked contract");
        rejects(() -> ModelSelection.prepare(store, a15, request(a15.id)), "Standalone LoRA task fails explicitly");
        rejects(() -> ModelSelection.prepare(store, sd15, request(sd15.id, axl.id)), "Installed cross-family selection still fails");
        check(!entry(store, sd15.id).getBoolean("inUse") && !entry(store, axl.id).getBoolean("inUse"), "Failed pair resolution releases every lease");
        try (BundleStore.Selection held = store.acquireAll(ModelSelection.ids(prepared))) {
            check(held.models.size() == 2 && entry(store, a15.id).getBoolean("inUse"), "A running selection holds base and adapter references together");
            rejects(() -> store.remove(sd15.id, false), "The running base cannot be deleted");
            rejects(() -> store.remove(a15.id, false), "The running adapter cannot be deleted");
            rejects(() -> store.saveSettings(a15.id, new JSONObject().put("scale", 1)), "In-use adapter settings are protected");
            JSONArray nativeLoras = ModelSelection.nativeLoras(held.models.get(0), held.models.subList(1, held.models.size()), prepared);
            check(nativeLoras.getJSONObject(0).getString("path").equals(held.models.get(1).file("lora").getAbsolutePath()) && nativeLoras.getJSONObject(0).getDouble("scale") == 0.75, "Only leased verified object paths and frozen scales reach the native command");
            rejects(() -> ModelSelection.nativeLoras(held.models.get(0), Collections.emptyList(), prepared), "Missing dependency leases fail");
            JSONObject invalid = DataFiles.copy(prepared); invalid.getJSONArray("adapters").getJSONObject(0).put("scale", 5);
            rejects(() -> ModelSelection.nativeLoras(held.models.get(0), held.models.subList(1, held.models.size()), invalid), "Native command resolution rejects unnormalized scales");
        }
        check(!entry(store, sd15.id).getBoolean("inUse") && !entry(store, a15.id).getBoolean("inUse"), "Completion and cancellation scopes release both peers");
        rejects(() -> store.acquireAll(Arrays.asList(sd15.id, "missing")), "Missing explicit dependencies fail atomically");
        check(!entry(store, sd15.id).getBoolean("inUse"), "Partial acquisition failure releases the already-acquired base");
        ModelBundle absent = new ModelBundle(manifest("not_installed", "sd15", true)); store.declare(absent);
        rejects(() -> ModelSelection.prepare(store, sd15, request(sd15.id, absent.id)), "Missing adapter bytes never start a task");
        check(!entry(store, absent.id).has("transfer"), "Missing adapter resolution never creates a download");
        check(AdapterSpec.extraRam(a15) == a15.component("lora").bytes * 4, "Adapter RAM admission includes a declared conservative expansion guard");
        store.remove(a15.id, false); check(entry(store, sd15.id).getBoolean("installed"), "Deleting an idle adapter preserves the base model and foundation");
        return passed;
    }
}
