package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Actual production adapter/core code with metadata-only GGUF bytes and a literal-text HTTP child. */
public final class TextEngineTest {
    private static int passed;
    private interface Action { void run() throws Exception; }
    private static void check(boolean result, String why) { if (!result) throw new AssertionError(why); passed++; }
    private static void rejects(Action action, String why) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(why); }
    private static void little(ByteArrayOutputStream out, long n, int size) { for (int i = 0; i < size; i++) out.write((int) (n >> (8 * i)) & 255); }
    private static void string(ByteArrayOutputStream out, String text) throws Exception { byte[] bytes = text.getBytes("UTF-8"); little(out, bytes.length, 8); out.write(bytes); }
    private static byte[] gguf(int context) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); little(out, 0x46554747L, 4); little(out, 3, 4); little(out, 0, 8); little(out, 2, 8);
        string(out, "general.architecture"); little(out, 8, 4); string(out, "llama"); string(out, "llama.context_length"); little(out, 4, 4); little(out, context, 4);
        out.write("metadata fixture only, zero tensors".getBytes("UTF-8")); return out.toByteArray();
    }
    private static String hash(byte[] value) throws Exception { return Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(value)); }
    private static ModelBundle bundle(RecipeCatalogue recipes, byte[] value) throws Exception {
        JSONObject asset = new JSONObject().put("repository", "fixture/text").put("revision", String.join("", Collections.nCopies(40, "a"))).put("path", "fixture.gguf").put("format", "gguf").put("bytes", value.length).put("sha256", hash(value));
        asset.put("url", "https://huggingface.co/fixture/text/resolve/" + asset.getString("revision") + "/fixture.gguf");
        return recipes.compose("text_gguf_cpu_v1", new JSONObject().put("text_gguf", asset));
    }
    private static void install(BundleStore store, ModelBundle bundle, byte[] bytes) throws Exception {
        store.declare(bundle); String token = store.request(bundle.id); ModelBundle.Component c = bundle.components.get(0);
        Files.write(store.partial(c.objectId).toPath(), bytes); store.accept(bundle.id, token, c, store.partial(c.objectId)); store.install(bundle.id, token);
    }
    private static String event(String delta, String finish) { return "data: {\"choices\":[{\"index\":0,\"delta\":" + delta + ",\"finish_reason\":" + (finish == null ? "null" : "\"" + finish + "\"") + "}]}\n\n"; }
    private static JSONObject consume(String stream) throws Exception { return TextResult.consume(new ByteArrayInputStream(stream.getBytes("UTF-8")), () -> {}, characters -> {}); }
    private static final class Context implements LocalEngine.Context {
        final BundleStore.Lease lease; final JSONObject request; final File folder;
        final AtomicBoolean cancelled = new AtomicBoolean(); final CountDownLatch generating = new CountDownLatch(1);
        Process child; JSONObject execution = new JSONObject(); int progress;
        Context(BundleStore.Lease lease, JSONObject request, File folder) { this.lease = lease; this.request = DataFiles.copy(request); this.folder = folder; folder.mkdirs(); }
        public BundleStore.Lease model() { return lease; }
        public JSONObject request() { return DataFiles.copy(request); }
        public File output(String suffix) { return new File(folder, "fixture-result." + suffix); }
        public void check() throws Exception { if (cancelled.get()) throw new IOException("explicit fixture cancellation"); }
        public void progress(String stage, Double fraction) throws Exception { check(); progress++; if (stage.equals("generating")) generating.countDown(); }
        public void process(Process value) throws Exception { child = value; check(); }
        public void execution(JSONObject value) throws Exception { check(); execution = DataFiles.copy(value); }
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); root.mkdirs(); LmaApp app = new LmaApp(root); app.bundles = new BundleStore(new File(root, "models"));
        RecipeCatalogue recipes = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])), StandardCharsets.UTF_8)));
        byte[] bytes = gguf(1024); ModelBundle model = bundle(recipes, bytes); install(app.bundles, model, bytes);
        File executable = new File(System.getProperty("java.home"), "bin/java.exe");
        TextEngine runtime = new TextEngine(app, executable, new JSONObject().put("engine", "llama_text"));
        app.bundles.setParameterResolver(runtime::schema);
        JSONObject saved = app.bundles.saveSettings(model.id, new JSONObject().put("context", 90000).put("maxTokens", 100000));
        check(saved.getJSONObject("values").getInt("context") == 1024 && saved.getJSONObject("values").getInt("maxTokens") == 1023, "Actual GGUF metadata and dependent output ceiling clamp on save");
        check(app.bundles.snapshot().getJSONObject(0).getJSONObject("parameterSchema").getBoolean("contextKnown"), "UI receives actual limits separately from the immutable manifest");
        check(model.parameters().json().getJSONObject("fields").getJSONObject("context").getInt("maximum") == 131072, "Runtime bounds never rewrite immutable model provenance");
        app.bundles.saveSettings(model.id, new JSONObject().put("context", 128).put("maxTokens", 500));
        check(app.bundles.settings(model.id).getJSONObject("values").getInt("maxTokens") == 127, "Changing context reclamps output immediately");
        rejects(() -> app.bundles.saveSettings(model.id, new JSONObject().put("remote", true)), "No unsupported parameter survives native validation");
        ModelBundle other = bundle(recipes, gguf(512)); app.bundles.declare(other);
        check(app.bundles.parameters(other.id).json().getJSONObject("fields").getJSONObject("context").getInt("maximum") == 8192, "Uninstalled GGUF uses an explicitly unknown application guard");
        JSONObject before = app.bundles.planUpdate(model.id, other.id, "copy");
        app.bundles.prepareUpdate(model.id, other.id, "copy", before.getString("review"));
        install(app.bundles, other, gguf(512));
        JSONObject after = app.bundles.planUpdate(model.id, other.id, "copy");
        check(!before.getString("review").equals(after.getString("review")), "Discovered GGUF limits invalidate an earlier version review");
        rejects(() -> app.bundles.activateUpdate(model.id, other.id, "copy", before.getString("review")), "Pre-download consent cannot activate changed GGUF limits");
        rejects(() -> app.bundles.activateUpdate(model.id, other.id, "copy", after.getString("review")), "A replacement review cannot overwrite an existing user plan");
        app.bundles.cancelUpdate(model.id, before.getString("review"));
        JSONObject reviewed = app.bundles.planUpdate(model.id, other.id, "copy");
        app.bundles.activateUpdate(model.id, other.id, "copy", reviewed.getString("review"));
        check(app.bundles.versionHistory(model.id).getString("activeBundleId").equals(other.id), "Explicit re-review activates the verified target with actual constraints");
        check(app.bundles.settings(model.id).getJSONObject("values").getInt("context") == 128, "Other models and updates preserve source settings");
        JSONObject cycle = model.parameters().json(); cycle.getJSONObject("fields").getJSONObject("context").put("maximumFrom", new JSONObject().put("field", "maxTokens"));
        rejects(() -> new ParameterSchema(cycle), "Cycles in dependent limits are rejected");
        JSONObject missing = model.parameters().json(); missing.getJSONObject("fields").getJSONObject("maxTokens").getJSONObject("maximumFrom").put("field", "missing");
        rejects(() -> new ParameterSchema(missing), "Dependent references must exist");
        JSONObject wrongType = model.json(); wrongType.getJSONObject("parameters").getJSONObject("fields").getJSONObject("context").put("type", "number");
        rejects(() -> TextSpec.validate(new ModelBundle(wrongType), "text.generate"), "Imported schemas must match actual engine types");
        wrongType.put("id", "bad_text_fixture"); app.bundles.declare(new ModelBundle(wrongType));
        JSONArray records = app.bundles.snapshot(); boolean isolated = false;
        for (int i = 0; i < records.length(); i++) if (records.getJSONObject(i).getString("id").equals("bad_text_fixture")) isolated = records.getJSONObject(i).has("parameterError");
        check(isolated && records.length() == 3, "One incompatible text recipe reports a local error without disabling the model library");
        rejects(() -> TextSpec.validate(model, "speech.synthesize"), "Text weights cannot claim speech output");
        rejects(() -> TextSpec.prompt(new JSONObject().put("prompt", "a\u0000b")), "No embedded prompt terminator");
        rejects(() -> TextSpec.prompt(new JSONObject().put("prompt", "hello").put("negativePrompt", "discard me")), "Negative prompts are not silently ignored");
        String valid = event("{\"reasoning\":\"思考\"}", null) + event("{\"content\":\"正文 <script>x</script>\"}", "length") + "data: [DONE]\n\n";
        JSONObject result = consume(valid);
        check(result.getString("content").contains("<script>") && result.getString("reasoning").equals("思考") && result.getString("finishReason").equals("length"), "Lossless Unicode, markup and reasoning stay distinct as data");
        check(consume(event("{\"reasoning_content\":\"thought only\"}", "stop") + "data: [DONE]\n\n").getString("content").isEmpty(), "Reasoning-only output remains inspectable");
        rejects(() -> consume(event("{\"content\":\"partial\"}", "stop")), "A truncated stream never commits success");
        rejects(() -> consume(event("{\"content\":\"partial\"}", null) + "data: [DONE]\n\n"), "DONE alone does not prove a completed generation");
        rejects(() -> consume(event("{}", "stop") + "data: [DONE]\n\n"), "An empty result is rejected");
        rejects(() -> consume(event("{\"content\":[\"nontext\"]}", "stop") + "data: [DONE]\n\n"), "Nontext payloads are rejected");
        rejects(() -> consume(event("{\"tool_calls\":[]}", "stop") + "data: [DONE]\n\n"), "Unsupported tool execution is rejected");
        rejects(() -> consume(event("{\"content\":\"a\"}", "stop") + event("{\"content\":\"after finish\"}", "stop") + "data: [DONE]\n\n"), "No content after a finish event");
        rejects(() -> consume("data: {\"error\":\"fixture error\"}\n\n"), "Engine error events cannot become saved results");
        rejects(() -> consume("data: " + String.join("", Collections.nCopies(131073, "x")) + "\n\n"), "Event lines are bounded");
        byte[] invalid = valid.getBytes("UTF-8"); invalid[10] = (byte) 0xff;
        rejects(() -> TextResult.consume(new ByteArrayInputStream(invalid), () -> {}, characters -> {}), "Malformed UTF-8 fails closed");
        rejects(() -> TextResult.consume(new ByteArrayInputStream(valid.getBytes("UTF-8")), () -> { throw new IOException("cancel"); }, n -> {}), "Cancellation is checked before parsing");
        File file = new File(root, "result.json"); TextResult.write(file, result);
        check(TextResult.inspect(file).getString("mime").equals(TextResult.MIME), "Typed artifact inspector validates actual saved JSON");
        ArtifactStore artifacts = new ArtifactStore(new File(root, "artifacts"), TextResult::inspect); File staged = artifacts.staging("text-job", "json"); TextResult.write(staged, result);
        check(artifacts.commit("text-job", staged, new JSONObject().put("fixture", true), () -> {}).getJSONObject("metadata").getString("mime").equals(TextResult.MIME), "Actual artifact store accepts and hashes typed text results");
        Files.write(file.toPath(), "{\"schema\":\"unknown\"}".getBytes("UTF-8")); rejects(() -> TextResult.inspect(file), "Arbitrary JSON is not accepted as text output");
        JSONObject request = new JSONObject().put("type", "text.generate").put("bundleId", model.id).put("input", new JSONObject().put("prompt", "USER_PROMPT_FIXTURE")).put("parameters", app.bundles.settings(model.id).getJSONObject("values")).put("adjustments", new JSONArray());
        JSONObject prepared = runtime.prepare(model, request);
        check(prepared.getJSONObject("textMetadata").getInt("contextLength") == 1024, "Submission freezes actual GGUF limits");
        for (String mode : Arrays.asList("ok", "truncated", "error", "redirect", "missing-mime", "wrong-alias", "exit")) {
            File folder = new File(root, mode); folder.mkdirs(); File record = new File(folder, "request.json");
            TextEngine engine = new TextEngine(app, executable, new JSONObject().put("engine", "llama_text"), builder -> {
                List<String> command = builder.command(); check(!command.toString().contains("USER_PROMPT_FIXTURE") && !command.contains(builder.environment().get("LLAMA_API_KEY")), "Prompt and private key are absent from process argv");
                check(command.contains("127.0.0.1") && command.contains("none") && command.contains("--no-webui"), "CPU-only loopback endpoint with web UI disabled");
                List<String> launch = new ArrayList<>(Arrays.asList(executable.getPath(), "-Dfile.encoding=UTF-8", "-cp", System.getProperty("java.class.path"), "com.lma.app.TextServerFixture", mode, record.getPath())); launch.addAll(command.subList(1, command.size()));
                ProcessBuilder host = new ProcessBuilder(launch).redirectErrorStream(true); host.environment().put("LLAMA_API_KEY", builder.environment().get("LLAMA_API_KEY")); return host.start();
            });
            try (BundleStore.Lease lease = app.bundles.acquire(model.id)) {
                Context context = new Context(lease, prepared, folder);
                if (mode.equals("ok")) {
                    JSONObject output = TextResult.read(engine.generate(context)); check(output.getString("content").contains("HTTP 测试") && output.getJSONObject("usage").getInt("completion_tokens") == 7, "Actual authenticated host HTTP child streams literal Unicode text and usage");
                    JSONObject posted = new JSONObject(new String(Files.readAllBytes(record.toPath()), StandardCharsets.UTF_8));
                    check(posted.getString("model").equals(model.id) && posted.getInt("max_tokens") == 127 && posted.getBoolean("stream"), "Fixed bundle ID and independent output ceiling reach actual HTTP request");
                    check(context.execution.getJSONObject("ggufMetadata").getInt("contextLength") == 1024 && context.progress >= 3, "Execution provenance and progress use the shared context");
                } else rejects(() -> engine.generate(context), "Incomplete/redirected/unowned endpoint fails: " + mode);
                check(context.child != null && !context.child.isAlive() && app.nativeProcess == null, "Child ownership is released before another job: " + mode);
            }
        }
        File waiting = new File(root, "cancel"); waiting.mkdirs();
        TextEngine waitingEngine = new TextEngine(app, executable, new JSONObject(), builder -> {
            List<String> launch = new ArrayList<>(Arrays.asList(executable.getPath(), "-cp", System.getProperty("java.class.path"), "com.lma.app.TextServerFixture", "wait", new File(waiting, "request.json").getPath())); launch.addAll(builder.command().subList(1, builder.command().size()));
            ProcessBuilder host = new ProcessBuilder(launch); host.environment().put("LLAMA_API_KEY", builder.environment().get("LLAMA_API_KEY")); return host.start();
        });
        try (BundleStore.Lease lease = app.bundles.acquire(model.id)) {
            Context context = new Context(lease, prepared, waiting); ExecutorService thread = Executors.newSingleThreadExecutor();
            Future<?> future = thread.submit(() -> { try { waitingEngine.generate(context); throw new AssertionError("Cancelled generation succeeded"); } catch (IOException expected) {} catch (Exception error) { throw new RuntimeException(error); } });
            try { check(context.generating.await(10, TimeUnit.SECONDS), "Owned streaming generation starts"); context.cancelled.set(true); context.child.destroy(); future.get(10, TimeUnit.SECONDS); check(!context.child.isAlive() && app.nativeProcess == null, "Cancellation kills the real fixture child and releases ownership"); }
            finally { if (context.child != null) context.child.destroyForcibly(); thread.shutdownNow(); }
        }
        System.out.println(new JSONObject().put("passed", passed).put("physical_device", false).put("model_inference", false).put("downloaded_model_weights", false).put("actual_host_child_processes", true).put("actual_loopback_http", true).put("output_is_literal_fixture", true));
    }
}
