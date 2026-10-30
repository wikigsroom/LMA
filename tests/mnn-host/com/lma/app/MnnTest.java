package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/** Host protocol/file fixtures only: the child writes JSON, never a generated image. */
public final class MnnTest {
    private static int passed;
    private interface Action { void run() throws Exception; }
    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); passed++; }
    private static void rejects(Action action, String message) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(message); }
    private static JSONObject metadata() throws Exception { return new JSONObject().put("model_type", "qwen3").put("hidden_size", 1024).put("attention_mask", "float").put("attention_type", "full").put("tie_embeddings", new JSONArray("[0,77791232,19447808,4,64]")); }
    private static JSONObject request(ModelBundle bundle) throws Exception {
        return new JSONObject().put("bundleId", bundle.id).put("type", "image.generate").put("input", new JSONObject().put("prompt", MnnSpec.EDIT_PROMPT))
            .put("parameters", bundle.parameters().normalize(new JSONObject(), new JSONObject()).getJSONObject("values")).put("allowUnmeasured", true);
    }
    private static ModelBundle altered(ModelBundle b, String key, Object value) throws Exception { return new ModelBundle(b.json().put(key, value)); }
    private static void child(String path) throws Exception {
        JSONObject command = new JSONObject(new String(Files.readAllBytes(Paths.get(path)), "UTF-8"));
        if (command.getJSONObject("parameters").getInt("seed") == 99) { System.out.println(new JSONObject().put("event", "error").put("message", "explicit child failure")); System.exit(3); }
        Path root = Paths.get(command.getString("workspace"));
        for (String role : MnnSpec.roles()) if (!Files.isRegularFile(root.resolve(MnnSpec.group(role)).resolve(MnnSpec.filename(role)))) throw new IOException("Missing selected component");
        JSONObject config = new JSONObject(new String(Files.readAllBytes(root.resolve("llm/config.json")), "UTF-8"));
        JSONObject model = new JSONObject(new String(Files.readAllBytes(root.resolve("llm/llm_config.json")), "UTF-8"));
        if (config.has("base_dir") || model.length() != 5 || model.has("chat_template") || model.has("base_dir") || config.getBoolean("use_mmap") || config.getBoolean("prompt_cache")) throw new IOException("Unreviewed config reached child");
        JSONObject receipt = new JSONObject().put("fixture", "JSON_NOT_AN_IMAGE").put("command", command).put("config", config).put("metadata", model);
        Files.write(Paths.get(command.getString("output")), receipt.toString().getBytes("UTF-8"));
        System.out.println(new JSONObject().put("event", "progress").put("stage", "sampling").put("fraction", .5));
        System.out.println(new JSONObject().put("event", "complete").put("output", command.getString("output")));
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2 && args[0].equals("child")) { child(args[1]); return; }
        File root = new File(args[0]); root.mkdirs(); final File sourceImage = new File(args[2]);
        RecipeCatalogue recipes = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])), "UTF-8")));
        JSONObject template = recipes.template("sana_edit_mnn_cpu_v1"), raw = DataFiles.copy(template.getJSONObject("definition"));
        File values = new File(root, "fixture-data"); values.mkdirs(); Map<String, File> files = new LinkedHashMap<>(); JSONArray components = new JSONArray();
        for (String role : MnnSpec.roles()) {
            File file = new File(values, role + ".fixture");
            if (role.equals("llm_data")) { try (RandomAccessFile out = new RandomAccessFile(file, "rw")) { out.setLength(97239040); } }
            else Files.write(file.toPath(), (role.equals("llm_config") ? metadata().put("base_dir", "/outside/user/assets/").put("llm_model", "https://invalid.example/model").put("chat_template", "NOT_EXECUTED").toString() : "NOT_A_MODEL_" + role).getBytes("UTF-8"));
            files.put(role, file); String format = role.equals("llm_config") ? "json" : role.equals("tokenizer") ? "text" : role.endsWith("_data") ? "mnn_data" : "mnn";
            components.put(new JSONObject().put("role", role).put("path", role + ".fixture").put("format", format).put("bytes", file.length()).put("sha256", DataFiles.sha256(file)));
        }
        ModelBundle bundle = new ModelBundle(raw.put("schema", ModelBundle.SCHEMA).put("id", "sana_fixture").put("modelId", "sana_fixture").put("recipeId", "sana_edit_mnn_cpu_v1").put("name", "Not a model").put("components", components));
        MnnSpec.validate(bundle, "image.generate"); check(true, "Complete 15-component mobile recipe validates");
        for (String role : MnnSpec.roles()) {
            JSONObject b = bundle.json(); JSONArray shortened = new JSONArray();
            for (int i = 0; i < components.length(); i++) if (!components.getJSONObject(i).getString("role").equals(role)) shortened.put(components.getJSONObject(i));
            ModelBundle missing = new ModelBundle(b.put("components", shortened)); rejects(() -> MnnSpec.validate(missing, "image.generate"), "Every required component is enforced");
            JSONArray wrong = new JSONArray(components.toString()); for (int i=0;i<wrong.length();i++) if (wrong.getJSONObject(i).getString("role").equals(role)) wrong.getJSONObject(i).put("format", "bin");
            ModelBundle mismatch = new ModelBundle(bundle.json().put("components", wrong)); rejects(() -> MnnSpec.validate(mismatch, "image.generate"), "Formats are role specific");
        }
        for (String[] change : new String[][]{{"engine", "sd_cpp"}, {"backend", "vulkan"}, {"pipeline", "sana"}, {"architecture", "sana600m"}}) rejects(() -> MnnSpec.validate(altered(bundle, change[0], change[1]), "image.generate"), "Other routes fail locally");
        rejects(() -> MnnSpec.validate(bundle, "video.generate"), "Image engine cannot claim video");
        JSONObject safe = MnnSpec.metadata(files.get("llm_config"), files.get("llm_data").length()); check(safe.length() == 5 && !safe.has("base_dir") && !safe.has("chat_template"), "Arbitrary user config is never merged");
        rejects(() -> MnnSpec.metadata(files.get("llm_config"), 100), "External embedding references cannot exceed selected weights");
        File bad = new File(root, "bad.json");
        for (String badTie : Arrays.asList("[-1,77791232,19447808,4,64]", "[0,77791232,19447808,3,64]", "[0,77791232,19447808,4,63]", "[0,77791231,19447808,4,64]", "[0,77791232,1,4,64]", "[0,77791232,19447808,4,64,2]")) {
            Files.write(bad.toPath(), metadata().put("tie_embeddings", new JSONArray(badTie)).toString().getBytes("UTF-8")); rejects(() -> MnnSpec.metadata(bad, 97239040), "Malformed tied embedding layout rejected");
        }
        InputSpec inputs = MnnSpec.inputs();
        check(inputs.json().getString("fixedPrompt").equals(MnnSpec.EDIT_PROMPT), "Signed input contract declares the actual fixed conditioning");
        rejects(() -> inputs.validate(new JSONArray(), request(bundle).getJSONObject("input")), "Source image is mandatory before queue submission");
        JSONObject receipt = new JSONObject().put("role", "source_image").put("bytes", sourceImage.length()).put("metadata", new JSONObject().put("mime", "image/png").put("width", 512).put("height", 512));
        inputs.validate(new JSONArray().put(receipt), request(bundle).getJSONObject("input")); check(true, "Matched local PNG satisfies the input contract");
        rejects(() -> inputs.validate(new JSONArray().put(receipt), new JSONObject().put("prompt", "arbitrary text")), "A restored or API prompt cannot override model conditioning");
        JSONObject oversized = DataFiles.copy(receipt); oversized.getJSONObject("metadata").put("width", 4096).put("height", 4096);
        rejects(() -> inputs.validate(new JSONArray().put(oversized), request(bundle).getJSONObject("input")), "Declared oversized image fails before loading a model");
        ModelBundle legacy = new ModelBundle(bundle.json().put("architecture", "sana_mobile").put("pipeline", "sana_mnn_v1").put("recipeId", "sana_mnn_cpu_v1"));
        check(legacy.id.equals(bundle.id), "Legacy metadata remains readable without migration or identifier replacement");
        rejects(() -> MnnSpec.validate(legacy, "image.generate"), "Legacy text-to-image declaration is clearly incompatible");
        JSONObject selected = request(bundle); JSONObject planned = MnnSpec.prepare(bundle, selected).getJSONObject("diffusionPlan");
        check(planned.getString("profile").equals("sana_edit_mnn") && planned.getJSONObject("parameters").getInt("width") == 512, "Sana plan is derived independently");
        check(!selected.has("diffusionPlan"), "Saved settings/request are not mutated");
        JSONObject large = request(bundle); large.getJSONObject("parameters").put("width", 99999).put("height", 511).put("steps", 999).put("threads", 99).put("maxInputTokens", 99999).put("cfg", 99);
        JSONObject clamped = MnnSpec.prepare(bundle, large).getJSONObject("diffusionPlan").getJSONObject("parameters");
        check(clamped.getInt("width") == 512 && clamped.getInt("height") == 512 && clamped.getInt("steps") == 50 && clamped.getInt("threads") == 32 && clamped.getInt("maxInputTokens") == 1792 && clamped.getDouble("cfg") == 4, "Native pipeline/application maxima and alignment are enforced");
        JSONObject negative = request(bundle); negative.getJSONObject("input").put("negativePrompt", "explicit negative"); rejects(() -> MnnSpec.prepare(bundle, negative), "Negative input is not silently discarded");
        negative.getJSONObject("parameters").put("useCfg", true); rejects(() -> MnnSpec.prepare(bundle, negative), "Fixed edit route rejects CFG and arbitrary negative conditioning");
        JSONObject adapter = request(bundle).put("adapters", new JSONArray().put(new JSONObject().put("bundleId", "other").put("scale", 1))); rejects(() -> MnnSpec.prepare(bundle, adapter), "Unsupported LoRA cannot reach worker");
        JSONObject empty = request(bundle); empty.getJSONObject("input").put("prompt", " "); rejects(() -> MnnSpec.prepare(bundle, empty), "Empty prompt fails before worker");
        LmaApp app = new LmaApp(new File(root, "app")); app.bundles = new BundleStore(new File(app.getFilesDir(), "bundles")); app.bundles.declare(bundle); String token = app.bundles.request(bundle.id);
        for (ModelBundle.Component component : bundle.components) { Files.copy(files.get(component.role).toPath(), app.bundles.partial(component.objectId).toPath(), StandardCopyOption.REPLACE_EXISTING); app.bundles.accept(bundle.id, token, component, app.bundles.partial(component.objectId)); }
        app.bundles.install(bundle.id, token); AtomicInteger launches = new AtomicInteger();
        File binary = new File(System.getProperty("java.home"), "bin/java.exe");
        NativeWorker.Launcher launcher = builder -> { launches.incrementAndGet(); List<String> command = new ArrayList<>(); command.add(binary.getPath()); command.add("-Dfile.encoding=UTF-8"); command.add("-Dstdout.encoding=UTF-8"); command.add("-cp"); command.add(System.getProperty("java.class.path")); command.add(MnnTest.class.getName()); command.add("child"); command.add(builder.command().get(1)); return new ProcessBuilder(command).redirectErrorStream(true).start(); };
        MnnEngine engine = new MnnEngine(app, binary, new JSONObject().put("engine", "mnn_diffusion"), launcher);
        JSONObject frozen = engine.prepare(bundle, request(bundle)); File staging = new File(root, "staging"); staging.mkdirs(); JSONObject execution = new JSONObject(); AtomicInteger progress = new AtomicInteger();
        try (BundleStore.Lease lease = app.bundles.acquire(bundle.id)) {
            LocalEngine.Context context = new LocalEngine.Context() {
                public BundleStore.Lease model() { return lease; } public JSONObject request() { return frozen; }
                public File input(String role) { if (!role.equals("source_image")) throw new IllegalArgumentException(role); return sourceImage; }
                public File output(String suffix) { return new File(staging, UUID.randomUUID() + "." + suffix); }
                public void check() {} public void process(Process process) {} public void execution(JSONObject value) throws Exception { execution.put("details", value); }
                public void progress(String stage, Double fraction) { progress.incrementAndGet(); }
            };
            File output = engine.generate(context); JSONObject result = new JSONObject(new String(Files.readAllBytes(output.toPath()), "UTF-8"));
            check(result.getString("fixture").equals("JSON_NOT_AN_IMAGE"), "Actual host child tests the production protocol without claiming image generation");
            check(result.getJSONObject("config").getInt("thread_num") == 4 && !result.getJSONObject("config").has("base_dir"), "Bounded CPU configuration reaches actual child");
            check(execution.getJSONObject("details").getJSONObject("effectiveParameters").getLong("seed") >= 0, "Actual random seed is recorded before launch");
            check(progress.get() > 0 && app.nativeProcess == null, "Native progress and process ownership complete");
            check(new File(app.getFilesDir(), "engine-work").list().length == 0, "Private hardlink workspace is removed after child exit");
            check(DataFiles.sha256(lease.file("llm_config")).equals(bundle.component("llm_config").sha256), "Sanitizing config never overwrites installed metadata");
            frozen.getJSONObject("diffusionPlan").getJSONObject("parameters").put("steps", 2); rejects(() -> engine.generate(context), "Frozen plan tampering fails before launch");
            frozen.getJSONObject("parameters").put("seed", 99); frozen.put("diffusionPlan", MnnSpec.prepare(bundle, frozen).getJSONObject("diffusionPlan")); rejects(() -> engine.generate(context), "Actual native child failure propagates locally");
            check(app.nativeProcess == null && new File(app.getFilesDir(), "engine-work").list().length == 0, "Failure cleans process and private workspace");
        }
        check(launches.get() == 2, "Invalid frozen plan did not start an extra child");
        EngineWorkspace held = new EngineWorkspace(new File(root, "deferred"), () -> {}); held.link("models", "held.mnn", files.get("diffusion"));
        Process sleeper = new ProcessBuilder(binary.getPath(), "-cp", System.getProperty("java.class.path"), MnnSleep.class.getName()).start(); held.closeAfter(sleeper);
        check(held.directory().isDirectory(), "Workspace remains available while a child still lives"); sleeper.destroyForcibly(); sleeper.waitFor(3, TimeUnit.SECONDS);
        long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(5); while (held.directory().exists() && System.nanoTime()<deadline) Thread.sleep(10);
        check(!held.directory().exists() && files.get("diffusion").isFile(), "Deferred cleanup preserves original data after actual process exit");
        System.out.println(new JSONObject().put("passed", passed).put("actual_host_children", launches.get()).put("production_mnn_binding", true).put("model_inference", false).put("image_outputs", false));
    }
}
final class MnnSleep { public static void main(String[] args) throws Exception { Thread.sleep(30000); } }
