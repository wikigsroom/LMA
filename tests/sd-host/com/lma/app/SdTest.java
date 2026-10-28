package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Actual production Java diffusion binding and literal child protocol; no tensors or images. */
public final class SdTest {
    private static int passed;
    private static RecipeCatalogue templates;
    private static final byte[] BYTES = "host fixture bytes, not weights or media".getBytes(java.nio.charset.StandardCharsets.UTF_8);
    private interface Checked { void run() throws Exception; }
    private static void check(boolean yes, String why) { if (!yes) throw new AssertionError(why); passed++; }
    private static void rejects(Checked action, String why) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(why); }
    private static ModelBundle bundle(String template) throws Exception {
        JSONObject t = templates.template(template), b = DataFiles.copy(t.getJSONObject("definition")); JSONArray components = new JSONArray();
        JSONArray requirements = t.getJSONArray("requirements"), fixed = t.getJSONArray("fixedComponents");
        for (int i = 0; i < requirements.length() + fixed.length(); i++) {
            JSONObject r = i < requirements.length() ? requirements.getJSONObject(i) : fixed.getJSONObject(i - requirements.length());
            String role = r.getString("role"), format = i < requirements.length() ? r.getJSONArray("formats").getString(0) : r.getString("format");
            components.put(new JSONObject().put("role", role).put("path", role + ".fixture").put("format", format).put("bytes", BYTES.length).put("sha256", Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(BYTES))));
        }
        return new ModelBundle(b.put("schema", ModelBundle.SCHEMA).put("id", template).put("modelId", template).put("recipeId", template).put("name", "Not a model").put("components", components));
    }
    private static ModelBundle altered(ModelBundle b, String key, Object value) throws Exception { return new ModelBundle(b.json().put(key, value)); }
    private static JSONObject request(ModelBundle b, ModelBundle... adapters) throws Exception {
        JSONArray list = new JSONArray(); for (ModelBundle a : adapters) list.put(new JSONObject().put("bundleId", a.id).put("scale", 1));
        return new JSONObject().put("bundleId", b.id).put("type", "image.generate").put("input", new JSONObject().put("prompt", "literal protocol fixture"))
            .put("parameters", b.parameters().normalize(new JSONObject(), new JSONObject()).getJSONObject("values")).put("adapters", list).put("allowUnmeasured", true);
    }
    private static void install(BundleStore store, ModelBundle b) throws Exception {
        store.declare(b); String token = store.request(b.id);
        for (ModelBundle.Component c : b.components) { Files.write(store.partial(c.objectId).toPath(), BYTES); store.accept(b.id, token, c, store.partial(c.objectId)); }
        store.install(b.id, token);
    }
    private static JSONObject plan(ModelBundle b, JSONObject request, ModelBundle... adapters) throws Exception { return SdSpec.prepare(b, Arrays.asList(adapters), request).getJSONObject("diffusionPlan"); }
    private static void child(String name) throws Exception {
        JSONObject command = new JSONObject(new String(Files.readAllBytes(Paths.get(name)), "UTF-8"));
        if (!command.getString("schema").equals("lma.engine-request/1")) throw new IOException("Invalid child protocol");
        if (command.getJSONObject("input").getString("prompt").equals("fixture-error")) { System.out.println(new JSONObject().put("event", "error").put("message", "literal child failure")); System.exit(2); }
        JSONObject components = command.getJSONObject("components");
        for (Iterator<String> it = components.keys(); it.hasNext();) if (!new File(components.getString(it.next())).isFile()) throw new IOException("Missing leased fixture bytes");
        if (!components.getString("clip_merges").equals(System.getenv("LMA_VOCAB_CLIP_MERGES"))) throw new IOException("Vocabulary environment must refer to user assets");
        Files.write(Paths.get(command.getString("output")), command.toString().getBytes("UTF-8"));
        System.out.println(new JSONObject().put("event", "complete").put("output", command.getString("output")));
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2 && args[0].equals("child")) { child(args[1]); return; }
        File root = new File(args[0]); root.mkdirs(); templates = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])), "UTF-8")));
        ModelBundle sd15 = bundle("sd15_checkpoint_cpu_v1"), xl = bundle("sdxl_checkpoint_cpu_v1"), turbo = bundle("sd21_turbo_checkpoint_cpu_v1"), lc = bundle("sd15_lcm_checkpoint_cpu_v1"), lcx = bundle("sdxl_lcm_checkpoint_cpu_v1");
        ModelBundle a = bundle("sd15_lcm_lora_cpu_v1"), ax = bundle("sdxl_lcm_lora_cpu_v1"), style = bundle("sd15_lora_cpu_v1");
        for (ModelBundle b : Arrays.asList(sd15, xl, turbo, lc, lcx, bundle("sd15_split_cpu_v1"), bundle("sdxl_split_cpu_v1"))) { SdSpec.validate(b, "image.generate"); check(true, "Complete classic component routes validate"); }
        for (String key : Arrays.asList("clip_l", "clip_g", "vae", "clip_merges")) {
            JSONObject b = bundle("sdxl_split_cpu_v1").json(); JSONArray c = new JSONArray(); for (int i=0;i<b.getJSONArray("components").length();i++) if (!b.getJSONArray("components").getJSONObject(i).getString("role").equals(key)) c.put(b.getJSONArray("components").getJSONObject(i));
            ModelBundle incomplete = new ModelBundle(b.put("components", c)); rejects(() -> SdSpec.validate(incomplete, "image.generate"), "Missing split component fails before process launch");
        }
        rejects(() -> SdSpec.validate(altered(sd15, "architecture", "sdxl"), "image.generate"), "Architecture cannot contradict the selected pipeline");
        rejects(() -> SdSpec.validate(altered(sd15, "backend", "vulkan"), "image.generate"), "Unshipped backend cannot be selected");
        rejects(() -> SdSpec.validate(sd15, "video.generate"), "Image route cannot claim video");
        rejects(() -> SdSpec.validate(a, "image.generate"), "Adapter is not a standalone pipeline");
        JSONObject both = sd15.json(); both.getJSONArray("components").put(DataFiles.copy(both.getJSONArray("components").getJSONObject(0)).put("role", "diffusion"));
        rejects(() -> SdSpec.validate(new ModelBundle(both), "image.generate"), "Ambiguous complete and split main weights fail");
        check(plan(sd15, request(sd15)).getString("profile").equals("standard"), "Ordinary recipe retains standard sampling");
        for (ModelBundle b : Arrays.asList(lc, lcx, turbo)) {
            JSONObject input = request(b); input.getJSONObject("parameters").put("steps", 99).put("cfg", 9).put("sampler", "euler"); String before = input.toString(); JSONObject p = plan(b, input);
            check(p.getJSONObject("parameters").getInt("steps") == (b == turbo ? 4 : 8), "Distilled step upper bound is applied");
            check(p.getJSONObject("parameters").getDouble("cfg") == 1, "Distilled CFG is disabled");
            check(p.getJSONObject("parameters").getString("sampler").equals(b == turbo ? "euler_a" : "lcm"), "Actual sampler is frozen");
            check(p.getJSONObject("parameters").getString("scheduler").equals(b == turbo ? "discrete" : "lcm"), "Actual scheduler is frozen");
            check(p.getJSONArray("adjustments").length() >= 3 && input.toString().equals(before), "Plan records changes without changing caller or saved profile");
            input.getJSONObject("input").put("negativePrompt", "blur"); rejects(() -> plan(b, input), "Unsupported negative conditioning is explicit");
        }
        JSONObject paired = request(sd15, a, style), p = plan(sd15, paired, a, style);
        check(p.getString("profile").equals("lcm") && p.getJSONObject("parameters").getInt("steps") == 8, "Explicit LCM-LoRA switches ordinary base sampling");
        check(plan(xl, request(xl, ax), ax).getString("profile").equals("lcm"), "SDXL LCM-LoRA uses the same signed policy");
        check(plan(sd15, request(sd15, style), style).getString("profile").equals("standard"), "Style LoRA does not imply consistency sampling");
        rejects(() -> plan(sd15, request(sd15, ax), ax), "LCM adapters remain architecture-specific");
        ModelBundle another = altered(a, "id", "another_lcm");
        rejects(() -> plan(sd15, request(sd15, a, another), a, another), "Two consistency accelerators fail explicitly");
        JSONObject zero = request(sd15, a); zero.getJSONArray("adapters").getJSONObject(0).put("scale", 0); rejects(() -> plan(sd15, zero, a), "Disabled LCM weights cannot enable LCM sampling");
        JSONObject unknown = a.json(); unknown.getJSONObject("adapter").put("sampling", "shell"); rejects(() -> new ModelBundle(unknown), "Sampling policy cannot introduce arbitrary execution");
        JSONObject manual = request(sd15); manual.getJSONObject("parameters").put("sampler", "lcm"); rejects(() -> plan(sd15, manual), "A normal checkpoint cannot silently claim consistency training");
        rejects(() -> plan(sd15, request(sd15, a)), "Adapter plan requires its complete ordered selection");
        LmaApp app = new LmaApp(new File(root, "app")); app.bundles = new BundleStore(new File(root, "assets"));
        for (ModelBundle b : Arrays.asList(sd15, xl, turbo, lc, lcx, a, ax, style)) install(app.bundles, b);
        File java = new File(System.getProperty("java.home"), "bin/java.exe"); AtomicInteger launched = new AtomicInteger();
        SdEngine engine = new SdEngine(app, java, new JSONObject(), builder -> {
            launched.incrementAndGet(); return launch(java, builder);
        });
        JSONObject frozen = engine.prepare(sd15, ModelSelection.prepare(app.bundles, sd15, paired));
        check(frozen.getJSONObject("parameters").getInt("steps") == 20 && frozen.getJSONObject("diffusionPlan").getJSONObject("parameters").getInt("steps") == 8, "Requested and effective sampling are separately reviewable");
        check(app.bundles.settings(sd15.id).getJSONObject("values").getInt("steps") == 20, "Preparing LCM does not save over ordinary base settings");
        try (BundleStore.Selection leases = app.bundles.acquireAll(ModelSelection.ids(frozen))) {
            TestContext context = new TestContext(root, leases, frozen); File output = engine.generate(context); JSONObject packet = new JSONObject(new String(Files.readAllBytes(output.toPath()), "UTF-8"));
            check(launched.get() == 1 && packet.getString("samplingProfile").equals("lcm"), "Actual binding launches a host protocol child with the frozen profile");
            check(packet.getJSONObject("parameters").getInt("steps") == 8 && packet.getJSONObject("parameters").getDouble("cfg") == 1, "Effective parameters reach the private worker file");
            check(packet.getJSONArray("loras").length() == 2 && packet.getJSONArray("loras").getJSONObject(0).getString("path").equals(leases.models.get(1).file("lora").getAbsolutePath()), "Base and every LoRA use held private object paths");
            check(packet.getJSONObject("parameters").getLong("seed") >= 0 && context.details.getString("samplingProfile").equals("lcm"), "Actual seed and policy are recorded for provenance");
            JSONObject bad = DataFiles.copy(frozen); bad.getJSONObject("diffusionPlan").getJSONObject("parameters").put("cfg", 7);
            rejects(() -> engine.generate(new TestContext(root, leases, bad)), "Tampered queued sampling plan fails before launching");
            check(launched.get() == 1 && app.nativeProcess == null, "Rejected plans cannot leave a child running");
            check(!context.json.exists(), "Private native request file is removed after completion");
        }
        for (ModelBundle b : Arrays.asList(turbo, lc, xl)) try (BundleStore.Selection leases = app.bundles.acquireAll(Collections.singletonList(b.id))) {
            JSONObject r = engine.prepare(b, request(b)); TestContext context = new TestContext(root, leases, r);
            JSONObject packet = new JSONObject(new String(Files.readAllBytes(engine.generate(context).toPath()), "UTF-8"));
            check(packet.getString("pipeline").equals(b.pipeline) && packet.getString("architecture").equals(b.architecture), "Other selected classic routes reach the common binding");
        }
        System.out.println(new JSONObject().put("passed", passed).put("production_sd_binding", true).put("actual_host_children", true).put("model_inference", false).put("physical_android", false).put("image_outputs", false));
    }
    private static Process launch(File java, ProcessBuilder original) throws IOException {
        ProcessBuilder b = new ProcessBuilder(java.getPath(), "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-cp", System.getProperty("java.class.path"), SdTest.class.getName(), "child", original.command().get(1)).directory(original.directory()).redirectErrorStream(true);
        b.environment().putAll(original.environment()); return b.start();
    }
    private static final class TestContext implements LocalEngine.Context {
        final BundleStore.Selection leases; final JSONObject request; final File directory; JSONObject details; File json;
        TestContext(File root, BundleStore.Selection leases, JSONObject request) { this.leases=leases;this.request=request;directory=new File(root,"out-"+UUID.randomUUID());directory.mkdirs(); }
        public BundleStore.Lease model() { return leases.models.get(0); }
        public List<BundleStore.Lease> adapters() { return leases.models.subList(1,leases.models.size()); }
        public JSONObject request() { return DataFiles.copy(request); }
        public File output(String suffix) { File file=new File(directory,"protocol-fixture."+suffix);if(suffix.equals("json"))json=file;return file; }
        public void check() {}
        public void progress(String stage, Double fraction) {}
        public void process(Process process) {}
        public void execution(JSONObject value) { details=DataFiles.copy(value); }
    }
}
