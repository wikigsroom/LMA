package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Actual host scheduling/process/HTTP checks. All weights and outputs are non-inference fixtures. */
public final class SchedulerTest {
    private static int passed;
    private static Path work, root;
    private static final List<String> checks = new ArrayList<>();
    private static final List<Process> children = Collections.synchronizedList(new ArrayList<>());
    private static void check(boolean value, String name) { if (!value) throw new AssertionError(name); passed++; checks.add(name); }
    private interface Condition { boolean get() throws Exception; }
    private static void until(Condition condition, String message) throws Exception {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(15);
        while (System.nanoTime() < end) { if (condition.get()) return; Thread.sleep(15); }
        throw new AssertionError(message);
    }
    private static List<String> command(String main) {
        return new ArrayList<>(Arrays.asList(Paths.get(System.getProperty("java.home"), "bin", "java.exe").toString(), "-Dsun.net.useExclusiveBind=false", "-Dfile.encoding=UTF-8", "-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8", "-cp", System.getProperty("java.class.path"), main));
    }
    private static Process worker(JSONObject input) throws Exception {
        Path command = work.resolve("worker-" + UUID.randomUUID() + ".json"); Files.write(command, input.toString().getBytes(StandardCharsets.UTF_8));
        List<String> args = command(SchedulerTest.class.getName()); args.add("worker"); args.add(command.toString());
        Process process = new ProcessBuilder(args).redirectErrorStream(true).start(); children.add(process); return process;
    }
    private static void runWorker(String path) throws Exception {
        JSONObject input = new JSONObject(new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8));
        Path release = Paths.get(input.getString("release"));
        System.out.println(new JSONObject().put("event", "stage").put("stage", "generating")); System.out.flush();
        if (input.has("started")) Files.write(Paths.get(input.getString("started")), new byte[]{1});
        while (!Files.exists(release)) Thread.sleep(15);
        if (input.has("output")) {
            Files.write(Paths.get(input.getString("output")), input.has("inputPath") ? Files.readAllBytes(Paths.get(input.getString("inputPath"))) : new byte[]{1, 2, 3, 4});
            System.out.println(new JSONObject().put("event", "complete").put("output", input.getString("output"))); System.out.flush();
        }
    }
    private static void gateChecks() throws Exception {
        ExecutionGate gate = new ExecutionGate(); ExecutorService pool = Executors.newCachedThreadPool();
        ExecutionGate.Ticket first = gate.enqueue("api", "text"), cancelled = gate.enqueue("job", "cancelled"), chat = gate.enqueue("chat", "text"), last = gate.enqueue("job", "image");
        List<String> order = Collections.synchronizedList(new ArrayList<>()); CountDownLatch entered = new CountDownLatch(1), releaseChat = new CountDownLatch(1);
        try {
            first.await(() -> {}); AtomicBoolean stop = new AtomicBoolean();
            Future<?> skip = pool.submit(() -> { try { cancelled.await(() -> { if (stop.get()) throw new IOException("cancel"); }); throw new AssertionError("Cancelled waiter acquired"); } catch (Exception expected) {} });
            Future<?> c = pool.submit(() -> { try (ExecutionGate.Ticket slot = chat) { slot.await(() -> {}); order.add("chat"); entered.countDown(); releaseChat.await(); } catch (Exception error) { throw new RuntimeException(error); } });
            Future<?> d = pool.submit(() -> { try (ExecutionGate.Ticket slot = last) { slot.await(() -> {}); order.add("job"); } catch (Exception error) { throw new RuntimeException(error); } });
            check(gate.snapshot().getInt("waitingCount") == 3, "Every operation type uses one FIFO");
            stop.set(true); skip.get(5, TimeUnit.SECONDS); first.close();
            check(entered.await(5, TimeUnit.SECONDS), "Cancelling a waiting job unblocks the next text operation");
            check(order.equals(Collections.singletonList("chat")), "A later worker cannot overtake an earlier text request");
            releaseChat.countDown(); c.get(5, TimeUnit.SECONDS); d.get(5, TimeUnit.SECONDS);
            check(order.equals(Arrays.asList("chat", "job")), "Slot remains exclusive through the entire operation");
            check(gate.snapshot().isNull("active") && gate.snapshot().getInt("waitingCount") == 0, "Completed and cancelled tickets leave no slot leak");
            first.close(); check(gate.snapshot().isNull("active"), "Repeated close does not affect another owner");
            ExecutionGate.Ticket held = gate.enqueue("job", "slow-exit"); held.await(() -> {});
            Path release = work.resolve("deferred-release"), started = work.resolve("deferred-started");
            Process child = worker(new JSONObject().put("release", release).put("started", started));
            until(() -> Files.exists(started), "Deferred child starts"); AtomicBoolean cleaned = new AtomicBoolean();
            ExecutionGate.Ticket next = gate.enqueue("api", "text");
            held.releaseAfter(child, () -> cleaned.set(true)); held.close();
            check(child.isAlive() && !cleaned.get(), "A live child retains ownership and its cleanup callback");
            check(gate.snapshot().getJSONObject("active").getString("state").equals("reaping"), "Late process exit is visible as reaping");
            Future<?> waiting = pool.submit(() -> { try (ExecutionGate.Ticket slot = next) { slot.await(() -> {}); check(!child.isAlive() && cleaned.get(), "The next operation starts only after actual exit and cleanup"); } catch (Exception error) { throw new RuntimeException(error); } });
            Files.write(release, new byte[]{1}); waiting.get(10, TimeUnit.SECONDS);
            check(gate.snapshot().isNull("active"), "Deferred process release eventually frees the slot");
        } finally { releaseChat.countDown(); first.close(); cancelled.close(); chat.close(); last.close(); pool.shutdownNow(); }
    }
    private static void string(ByteBuffer b, String value) { byte[] data = value.getBytes(StandardCharsets.UTF_8); b.putLong(data.length).put(data); }
    private static byte[] gguf() {
        ByteBuffer b = ByteBuffer.allocate(768 * 1024).order(ByteOrder.LITTLE_ENDIAN);
        b.put(new byte[]{'G', 'G', 'U', 'F'}).putInt(3).putLong(0).putLong(2);
        string(b, "general.architecture"); b.putInt(8); string(b, "llama"); string(b, "llama.context_length"); b.putInt(4).putInt(1024);
        return b.array(); // Zero tensors; accepted only by the literal HostServer protocol fixture.
    }
    private static JSONObject request(String prompt) { return new JSONObject().put("bundleId", "image_fixture").put("type", "image.generate").put("allowUnmeasured", true).put("input", new JSONObject().put("prompt", prompt)); }
    private static JSONObject text(String prompt) { return new JSONObject().put("stream", true).put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", prompt))); }
    private static boolean state(LmaApp app, JSONObject job, String expected) throws Exception { return app.jobs.get(job.getString("id")).getString("state").equals(expected); }
    private static final class FixtureEngine implements LocalEngine {
        final LmaApp app; final List<Process> started = new CopyOnWriteArrayList<>();
        FixtureEngine(LmaApp app) { this.app = app; }
        @Override public String id() { return "fixture_engine"; }
        @Override public JSONObject describe() { return new JSONObject().put("engine", id()).put("hostProtocolFixture", true); }
        @Override public void validate(ModelBundle bundle, String type) throws Exception { if (!type.equals("image.generate")) throw new IOException("Fixture accepts image tasks only"); }
        @Override public InputSpec inputs(ModelBundle bundle, String type) throws Exception {
            return new InputSpec(new JSONObject().put("reference_image", new JSONObject().put("label", "Host protocol input").put("required", false).put("mimes", new JSONArray().put("image/png")).put("maxBytes", 1024 * 1024).put("maxPixels", 1024)));
        }
        @Override public File generate(Context context) throws Exception {
            String prompt = context.request().getJSONObject("input").getString("prompt"); File output = context.output("png");
            JSONObject input = new JSONObject().put("release", work.resolve(prompt + ".release")).put("output", output).put("started", work.resolve(prompt + ".started"));
            if (context.request().getJSONObject("input").has("artifacts")) input.put("inputPath", context.input("reference_image").getPath());
            NativeWorker.run(app, new File(app.getApplicationInfo().nativeLibraryDir, "fixture.so"), context, input, output, Collections.emptyMap(), builder -> {
                for (Process previous : children) if (previous.isAlive()) throw new IOException("Physical child overlap at worker launch");
                List<String> args = command(SchedulerTest.class.getName()); args.add("worker"); args.add(builder.command().get(1));
                Process process = new ProcessBuilder(args).redirectErrorStream(true).start(); children.add(process); started.add(process); return process;
            });
            return output;
        }
    }
    private static void release(String name) throws Exception { Files.write(work.resolve(name + ".release"), new byte[]{1}); }
    private static void started(String name) throws Exception { until(() -> Files.exists(work.resolve(name + ".started")), name + " enters actual worker"); }
    private static void runtimeChecks() throws Exception {
        Path libraries = work.resolve("libraries"); Files.createDirectories(libraries); Files.write(libraries.resolve("libllama-server.so"), new byte[]{1});
        LmaApp app = new LmaApp(work.resolve("app").toFile(), root.resolve("app/src/main/assets").toFile(), libraries.toFile());
        app.artifacts = new ArtifactStore(new File(app.getFilesDir(), "fixture-results"), file -> new JSONObject().put("mime", "image/png").put("width", 1).put("height", 1).put("hostInspectorFixture", true));
        app.artifacts.references(app.jobs::referencesArtifact);
        String alias = app.store.addCustom("Existing local text fixture", "https://fixture.invalid/metadata.gguf", "", false);
        Files.write(app.store.modelFile(alias).toPath(), gguf());
        RecipeCatalogue recipes = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(root.resolve("app/src/main/assets/recipe-templates.json")), StandardCharsets.UTF_8)));
        app.store.migrateExisting(recipes, () -> {});
        app.store.saveConfig(alias, new JSONObject().put("context", 512).put("maxTokens", 37).put("systemPrompt", "Frozen local profile"));
        byte[] data = {5, 6, 7}; Path input = work.resolve("image-data.bin"); Files.write(input, data);
        JSONObject component = new JSONObject().put("role", "backbone").put("path", "image.bin").put("format", "fixture_data").put("bytes", data.length).put("sha256", DataFiles.sha256(input.toFile()));
        ModelBundle bundle = new ModelBundle(new JSONObject().put("schema", ModelBundle.SCHEMA).put("id", "image_fixture").put("modelId", "image_fixture").put("recipeId", "fixture_recipe_v1").put("name", "Arbitrary-byte scheduler fixture")
                .put("engine", "fixture_engine").put("architecture", "fixture_arch").put("pipeline", "fixture_pipeline").put("backend", "cpu").put("tasks", new JSONArray().put("image"))
                .put("parameters", new JSONObject().put("version", 1).put("fields", new JSONObject().put("steps", new JSONObject().put("type", "integer").put("minimum", 1).put("maximum", 4).put("default", 1))))
                .put("components", new JSONArray().put(component)));
        app.bundles.adoptLocal(bundle, Collections.singletonMap("backbone", input.toFile()), new JSONObject(), () -> {});
        FixtureEngine fixture = new FixtureEngine(app); app.localEngines.fixture(fixture);
        LmaService service = new LmaService(); List<Process> residents = new CopyOnWriteArrayList<>();
        EngineHost engine = new EngineHost(service, app, builder -> {
            for (Process previous : children) if (previous.isAlive()) throw new IOException("Physical child overlap at text launch");
            List<String> args = command(HostServer.class.getName()); args.addAll(builder.command().subList(1, builder.command().size()));
            ProcessBuilder launcher = new ProcessBuilder(args).redirectErrorStream(true); launcher.environment().putAll(builder.environment());
            launcher.environment().put("LMA_HOST_BEHAVIOR", "normal"); launcher.environment().put("LMA_HOST_LAST_REQUEST", work.resolve("last-text-request.json").toString());
            Process process = launcher.start(); children.add(process); residents.add(process); return process;
        }); service.engine = engine;
        LocalJobs jobs = new LocalJobs(app, engine, () -> {}); app.jobHost = jobs;
        ChatRunner chat = new ChatRunner(service, app); ApiHost api = new ApiHost(service, app); ExecutorService pool = Executors.newCachedThreadPool();
        try (java.net.ServerSocket port = new java.net.ServerSocket(0)) { app.prefs.edit().putInt("port", port.getLocalPort()).apply(); }
        try {
            byte[] inputBytes = Base64.getDecoder().decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lWQAAAAASUVORK5CYII=");
            JSONObject imported = app.artifacts.importStream(new ByteArrayInputStream(inputBytes), "host-input.png", () -> {}); String inputId = imported.getString("id");
            JSONObject inputRequest = request("input-job"); inputRequest.getJSONObject("input").put("artifacts", new JSONArray().put(new JSONObject().put("role", "reference_image").put("artifactId", inputId)));
            int preflight = PreflightChecks.run(app, api, inputRequest); passed += preflight; checks.add("Actual production task preflight, invariants and HTTP: " + preflight);
            JSONObject inputJob;
            try (ExecutionGate.Ticket blocker = app.execution.enqueue("api", "fixture-blocker")) {
                blocker.await(() -> {}); inputJob = jobs.submit(inputRequest, "input-job");
                JSONObject preview = LocalJobs.preflight(app, inputRequest);
                check(preview.getBoolean("canEnqueue") && DataFiles.canonical(preview.getJSONObject("effectiveParameters")).equals(DataFiles.canonical(inputJob.getJSONObject("request").getJSONObject("parameters"))), "Preflight and the actual queued snapshot share parameter resolution");
                check(preview.getString("submissionHash").equals(inputJob.getJSONObject("request").getString("submissionHash")), "Preview and submission fingerprint exactly the same user request");
                until(() -> app.jobs.get(inputJob.getString("id")).optString("stage").equals("waiting_engine"), "Input job waits for the real shared slot");
                check(app.jobs.referencesArtifact(inputId), "Production submission pins media before the engine slot is available");
                boolean protectedInput = false; try { app.artifacts.remove(inputId); } catch (IllegalStateException expected) { protectedInput = true; }
                check(protectedInput, "Queued production jobs block deletion of their input media");
            }
            started("input-job"); release("input-job"); until(() -> state(app, inputJob, "succeeded") && !jobs.busy(), "Actual child consumes selected input bytes");
            JSONObject consumed = app.artifacts.get(app.jobs.get(inputJob.getString("id")).getJSONArray("artifacts").getString(0));
            check(consumed.getString("sha256").equals(imported.getString("sha256")), "Production engine context passes only the selected private file to the actual host child");
            check(consumed.getJSONObject("provenance").getJSONObject("request").getJSONArray("inputReceipts").getJSONObject(0).getString("artifactId").equals(inputId), "Committed production output retains immutable input provenance");
            byte[] tampered = inputBytes.clone(); tampered[tampered.length - 1] ^= 1; Files.write(app.artifacts.file(inputId).toPath(), tampered); int beforeTamper = fixture.started.size();
            JSONObject corrupted = DataFiles.copy(inputRequest); corrupted.getJSONObject("input").put("prompt", "input-corrupted"); JSONObject corruptJob = jobs.submit(corrupted, "input-corrupted");
            until(() -> state(app, corruptJob, "failed") && !jobs.busy(), "Corrupt input fails before child startup");
            check(fixture.started.size() == beforeTamper && app.jobs.get(corruptJob.getString("id")).getString("error").contains("changed"), "Actual production runner rehashes same-size input corruption before launching a worker");
            Files.write(app.artifacts.file(inputId).toPath(), inputBytes);
            JSONObject cancelledInput = DataFiles.copy(inputRequest); cancelledInput.getJSONObject("input").put("prompt", "input-cancel"); JSONObject inputCancelJob = jobs.submit(cancelledInput, "input-cancel"); started("input-cancel");
            jobs.cancel(inputCancelJob.getString("id")); until(() -> state(app, inputCancelJob, "cancelled") && !jobs.busy(), "Input child cancellation cleans its leases");
            until(() -> app.nativeProcess == null || !app.nativeProcess.isAlive(), "Input cancellation reaps its actual child");
            app.artifacts.remove(inputId); check(!app.jobs.referencesArtifact(inputId), "Cancelled production input jobs release deletion protection after actual child cleanup");
            app.artifacts.remove(consumed.getString("id")); fixture.started.clear();
            api.start(); engine.load(alias); until(engine::ready, "Initial resident becomes ready");
            check(residents.size() == 1 && residents.get(0).isAlive(), "Explicit load starts one real host resident");
            check(app.store.config(alias).getJSONObject("values").getInt("maxTokens") == 37, "Per-model profile is preserved before scheduling");
            LocalHttp.Response reply = api.text("/v1/chat/completions", text("stop"));
            app.memory.values.availMem = 64L * 1024 * 1024; app.memory.values.lowMemory = true;
            JSONObject first = jobs.submit(request("first"), "first");
            until(() -> app.jobs.get(first.getString("id")).getString("stage").equals("waiting_engine"), "Job waits for active text response");
            check(fixture.started.isEmpty(), "Submitting a job never preempts an active API stream");
            check(!state(app, first, "failed"), "Queue preflight uses total capacity before reclaiming idle resident memory");
            check(jobs.submit(request("first"), "first").getString("id").equals(first.getString("id")), "Idempotent submission does not add an execution ticket");
            app.memory.values.availMem = 6L * 1024 * 1024 * 1024; app.memory.values.lowMemory = false; reply.close();
            started("first"); check(!residents.get(0).isAlive(), "Old resident is reaped before the job worker starts");
            check(engine.wanted() && app.engineState.equals("suspended") && app.prefs.getBoolean("desiredRunning", false), "Temporary eviction retains the user's selected resident preference");
            try { app.bundles.remove(bundle.id, false, app.jobs); throw new AssertionError("Deleted active asset"); } catch (IllegalStateException expected) { passed++; checks.add("Running jobs retain model assets"); }
            Future<LocalHttp.Response> waitingApi = pool.submit(() -> api.text("/v1/chat/completions", text("after-image")));
            until(() -> app.textRequestBusy && app.execution.snapshot().getInt("waitingCount") > 0, "API queues behind worker");
            check(!waitingApi.isDone(), "Synchronous API waits for the same slot instead of rejecting a parked model");
            release("first"); LocalHttp.Response response = waitingApi.get(15, TimeUnit.SECONDS); ByteArrayOutputStream received = new ByteArrayOutputStream();
            response.body.write(received); response.close();
            check(received.toString("UTF-8").contains("你好"), "The original API returns the literal host stream after engine switching");
            until(() -> state(app, first, "succeeded") && engine.ready(), "Job finishes and original text residency returns");
            check(app.engineModel.equals(alias) && residents.size() == 2, "Text resumes with the original stable alias");
            JSONObject sent = new JSONObject(new String(Files.readAllBytes(work.resolve("last-text-request.json")), StandardCharsets.UTF_8));
            check(sent.getInt("max_tokens") == 37 && sent.getString("model").equals(alias), "Queued API keeps the requested model and its normalized output bound");
            check(app.artifacts.snapshot().length() == 1, "Job and artifact lifecycle still commit through production stores");

            JSONObject second = jobs.submit(request("second"), "second"); started("second");
            chat.send("queued-chat"); until(() -> app.generating && app.execution.snapshot().getInt("waitingCount") > 0, "Chat waits behind a job");
            check(app.chats.last().getString("status").equals("generating"), "Waiting chat retains its history placeholder");
            chat.cancel(); until(() -> !app.generating, "Waiting chat cancels promptly");
            check(app.chats.last().getString("status").equals("stopped"), "Cancelling a waiting chat saves an explicit stopped status");
            check(fixture.started.get(1).isAlive(), "Cancelling a waiting chat does not kill the active media worker");
            release("second"); until(() -> state(app, second, "succeeded") && engine.ready(), "Idle queue restores the wanted text model");

            JSONObject third = jobs.submit(request("third"), "third"); started("third"); int oldResidentCount = residents.size(); engine.stop();
            check(!engine.wanted() && fixture.started.get(2).isAlive(), "Stopping the suspended resident does not cancel an independent job");
            release("third"); until(() -> state(app, third, "succeeded") && !jobs.busy(), "Stopped-resident job completes");
            check(residents.size() == oldResidentCount && app.engineState.equals("stopped"), "Queue completion never revives a user-stopped model");

            JSONObject fourth = jobs.submit(request("fourth"), "fourth"); started("fourth"); engine.load(alias);
            check(app.engineState.equals("waiting") && residents.size() == oldResidentCount && fixture.started.get(3).isAlive(), "Loading during a job waits without killing its process");
            engine.stop(); release("fourth"); until(() -> state(app, fourth, "succeeded") && !jobs.busy(), "Cancelled warm-load job completes");
            check(residents.size() == oldResidentCount, "Cancelling a queued load prevents delayed model resurrection");

            engine.load(alias); until(engine::ready, "Text reloads explicitly"); LocalHttp.Response held = api.text("/v1/chat/completions", text("stop"));
            JSONObject fifth = jobs.submit(request("fifth"), "fifth"); until(() -> app.jobs.get(fifth.getString("id")).getString("stage").equals("waiting_engine"), "Cancellable job waits");
            jobs.cancel(fifth.getString("id")); until(() -> state(app, fifth, "cancelled") && !jobs.busy(), "Waiting job cancellation completes");
            check(engine.ready() && fixture.started.size() == 4, "Cancelling a waiting job preserves active text residency"); held.close();

            JSONObject sixth = jobs.submit(request("sixth"), "sixth"); started("sixth");
            Future<Boolean> cancelledApi = pool.submit(() -> { try (LocalHttp.Response ignored = api.text("/v1/chat/completions", text("cancel-api"))) { return false; } catch (InterruptedIOException expected) { return true; } });
            until(() -> app.textRequestBusy && app.execution.snapshot().getInt("waitingCount") > 0, "Cancellable API waits"); api.cancelText();
            check(cancelledApi.get(5, TimeUnit.SECONDS), "API cancellation also removes a waiting slot request");
            check(!app.textRequestBusy && fixture.started.get(4).isAlive(), "Cancelling queued API does not cancel the worker");
            Future<Boolean> disconnected = pool.submit(() -> {
                java.net.HttpURLConnection client = (java.net.HttpURLConnection) new java.net.URL("http://127.0.0.1:" + app.prefs.getInt("port", 0) + "/v1/chat/completions").openConnection();
                try {
                    client.setRequestMethod("POST"); client.setDoOutput(true); client.setRequestProperty("Content-Type", "application/json");
                    client.setRequestProperty("Authorization", "Bearer " + api.apiKey()); client.setReadTimeout(10000);
                    try (OutputStream out = client.getOutputStream()) { out.write(text("listener-close").toString().getBytes(StandardCharsets.UTF_8)); }
                    return client.getResponseCode() == 200;
                } catch (IOException expected) { return false; } finally { client.disconnect(); }
            });
            until(() -> app.textRequestBusy && app.execution.snapshot().getInt("waitingCount") > 0, "Public listener waits for a native worker");
            api.stop(); check(!disconnected.get(5, TimeUnit.SECONDS), "Closing the listener disconnects a queued real HTTP client");
            until(() -> !app.textRequestBusy, "Closing listener releases waiting handler ownership");
            check(fixture.started.get(4).isAlive(), "Closing the API listener preserves an independent running job"); api.start();
            release("sixth"); until(() -> state(app, sixth, "succeeded") && engine.ready(), "Cancelled-API job still succeeds");

            chat.send("stop"); until(() -> { JSONObject active = app.execution.snapshot().optJSONObject("active"); return app.generating && active != null && active.getString("kind").equals("chat"); }, "Chat owns the slot");
            JSONObject seventh = jobs.submit(request("seventh"), "seventh"); until(() -> app.jobs.get(seventh.getString("id")).getString("stage").equals("waiting_engine"), "Job waits behind chat");
            check(fixture.started.size() == 5, "Media submission preserves active in-app text generation"); chat.cancel(); started("seventh");
            check(app.chats.last().getString("status").equals("stopped"), "Active chat cancellation releases the slot after saving history");
            release("seventh"); until(() -> state(app, seventh, "succeeded") && engine.ready(), "Chat-to-media transition completes");

            app.power.status = 3; int beforeThermal = fixture.started.size(); JSONObject thermal = jobs.submit(request("thermal"), "thermal");
            until(() -> state(app, thermal, "failed"), "Thermal execution admission rejects locally"); app.power.status = 0;
            until(engine::ready, "Text returns after failed media admission");
            check(fixture.started.size() == beforeThermal, "Execution-time thermal checks prevent spawning an unsafe worker");
            check(app.jobs.get(thermal.getString("id")).getString("error").contains("温度"), "Actual admission failure remains visible on the job");

            JSONObject finalJob = jobs.submit(request("service-close"), "service-close"); started("service-close"); engine.stop(); jobs.close();
            until(() -> state(app, finalJob, "interrupted") && !jobs.busy(), "Service shutdown interrupts an active job");
            until(() -> app.nativeProcess == null || !app.nativeProcess.isAlive(), "Shutdown reaps actual child");
            check(app.execution.snapshot().isNull("active"), "Service shutdown releases the shared slot after actual process exit");
            check(app.store.config(alias).getJSONObject("values").getInt("maxTokens") == 37 && app.store.installed(alias), "Switching and service cancellation preserve existing weights and per-model defaults");
            check(api.health().getJSONObject("scheduler").getString("policy").equals("single_engine_fifo"), "API health publishes real scheduler state");
            check(app.bundles.record(bundle.id).getJSONObject("transfer").getString("state").equals("installed"), "Scheduling never starts a model transfer");
        } finally { engine.stop(); chat.close(); api.close(); jobs.close(); engine.close(); pool.shutdownNow(); }
    }
    private static void assemblyChecks() throws Exception {
        LmaApp app = new LmaApp(work.resolve("assembly-app").toFile(), root.resolve("app/src/main/assets").toFile(), work.resolve("libraries").toFile());
        PreparationPlan preparation = PreparationTest.fixturePlan(); ModelBundle source = PreparationTest.fixtureBundle(preparation);
        JSONObject component = new JSONObject().put("role", "diffusion_model").put("path", "prepared.data").put("format", "bin").put("bytes", PreparationTest.OUTPUT.length).put("sha256", PreparationTest.sha(PreparationTest.OUTPUT));
        JSONObject missing = new JSONObject().put("role", "text_encoder").put("path", "encoder.bin").put("format", "bin").put("bytes", 1).put("sha256", PreparationTest.sha(new byte[]{42}));
        ModelBundle target = new ModelBundle(source.json().put("id", "assembly_runtime").put("components", new JSONArray().put(component).put(missing))); app.bundles.declare(target);
        app.prepared = new PreparedAssets(new File(app.getFilesDir(), "prepared"));
        JSONObject record;
        try (PreparedAssets.Session session = app.prepared.begin("fixture_prepare")) { PreparationTest.outputs(session, preparation); record = session.commit(preparation, source.id, () -> {}); }
        JSONObject descriptor = new JSONObject().put("schema", "lma.model-assembly/1").put("id", "fixture_assembly").put("name", "Fixture association")
                .put("sourceBundleId", source.id).put("preparationId", preparation.id).put("bundleId", target.id)
                .put("roles", new JSONArray().put(new JSONObject().put("source", "diffusion_model").put("target", "diffusion_model")));
        AssemblyPlan plan = new AssemblyPlan(descriptor, preparation, target); app.assemblies = new LmaApp.AssemblyOptions(); app.assemblies.plan = plan;
        JSONObject input = new JSONObject().put("type", "model.assemble").put("bundleId", target.id).put("preparedAssetsId", record.getString("id")).put("assemblyId", plan.id).put("assemblyFingerprint", plan.fingerprint);
        LmaService service = new LmaService(); EngineHost engine = new EngineHost(service, app, builder -> { throw new IOException("Asset association must not spawn an inference child"); }); service.engine = engine;
        LocalJobs jobs = new LocalJobs(app, engine, () -> {}); ApiHost api = new ApiHost(service, app);
        ExecutionGate.Ticket hold = app.execution.enqueue("chat", "hold-assembly"); hold.await(() -> {});
        try {
            JSONObject cancelled = jobs.submit(input, "assembly-key");
            check(jobs.submit(input, "assembly-key").getString("id").equals(cancelled.getString("id")), "Assembly shares production idempotency handling");
            until(() -> !app.jobs.get(cancelled.getString("id")).getString("state").equals("queued"), "Assembly waits on the occupied execution slot");
            try { jobs.submit(input, "duplicate-assembly"); throw new AssertionError("Duplicate association accepted"); } catch (IOException expected) { check(true, "A runtime model has only one active association task"); }
            try { app.prepared.remove(record.getString("id"), app.jobs); throw new AssertionError("Waiting source deleted"); } catch (IOException expected) { check(true, "Production queue protects prepared data while waiting for the engine slot"); }
            jobs.cancel(cancelled.getString("id")); hold.close(); until(() -> state(app, cancelled, "cancelled") && !jobs.busy(), "Waiting assembly cancels without acquiring an installed target");
            JSONObject retry = jobs.retry(cancelled.getString("id"), "assembly-retry"); until(() -> state(app, retry, "succeeded") && !jobs.busy(), "Explicit retry rebinds the private source fingerprint");
            JSONObject completed = app.jobs.get(retry.getString("id")); check(completed.has("assembly") && completed.getJSONArray("artifacts").length() == 0, "Production runner publishes an association receipt without media");
            check(!app.bundles.plan(target.id).getBoolean("installed") && app.bundles.record(target.id).getJSONObject("transfer").getString("state").equals("paused"), "Production runner keeps missing dependencies paused");
            JSONArray models = api.models(); JSONObject visible = null; for (int i = 0; i < models.length(); i++) if (models.getJSONObject(i).getString("id").equals(target.id)) visible = models.getJSONObject(i);
            check(visible != null && !visible.getBoolean("installed") && visible.getLong("remaining_bytes") == 1, "API discovery shows partially associated models without claiming installation");
            check(app.execution.snapshot().isNull("active") && !app.prefs.getBoolean("desiredJobs", false), "Association completion releases the shared execution slot and idle preference");
        } finally { hold.close(); jobs.close(); api.close(); engine.close(); app.prepared.close(); }
    }
    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("worker")) { runWorker(args[1]); return; }
        root = Paths.get(args[0]); work = Paths.get(args[1]); Files.createDirectories(work);
        try {
            gateChecks(); runtimeChecks(); assemblyChecks(); int audio=AudioQueueChecks.run(root,work.resolve("audio-queue"));passed+=audio;checks.add("Production incremental audio task lifecycle: "+audio);
            System.out.println(new JSONObject().put("passed", passed).put("checks", new JSONArray(checks)).put("actual_host_children", true).put("actual_loopback_http", true)
                    .put("production_job_runner", true).put("physical_android", false).put("model_inference", false).put("automatic_model_downloads", false));
        } finally { for (Process child : children) { child.destroyForcibly(); child.waitFor(5, TimeUnit.SECONDS); } }
    }
}
