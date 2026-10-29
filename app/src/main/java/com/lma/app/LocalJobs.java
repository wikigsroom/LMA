package com.lma.app;

import android.app.ActivityManager;
import android.os.Build;
import android.os.PowerManager;
import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Service-owned queue runner shared by UI and API. Missing assets never trigger downloads. */
public final class LocalJobs implements AutoCloseable {
    private final LmaApp app;
    private final EngineHost resident;
    private final Runnable changed;
    private final ExecutorService worker = Executors.newSingleThreadExecutor(r -> new Thread(r, "LMA-local-jobs"));
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor(r -> new Thread(r, "LMA-engine-timeout"));
    private final AtomicBoolean pumping = new AtomicBoolean();
    private volatile boolean closed;
    private volatile String activeId = "";
    private volatile Process activeProcess;
    public LocalJobs(LmaApp app, EngineHost resident, Runnable changed) { this.app = app; this.resident = resident; this.changed = changed; }
    public JSONObject submit(JSONObject input, String idempotencyKey) throws Exception {
        synchronized (app.bundles) { synchronized (app.artifacts) { return submitLocked(input, idempotencyKey); } }
    }
    private JSONObject submitLocked(JSONObject input, String idempotencyKey) throws Exception {
        if (closed) throw new IllegalStateException("任务服务正在停止");
        input = TaskInput.validate(input);
        if (input.getString("type").equals("model.prepare")) return submitPreparation(input, idempotencyKey);
        if (input.getString("type").equals("model.assemble")) return submitAssembly(input, idempotencyKey);
        String submissionHash = TaskInput.fingerprint(input);
        JSONObject previous = app.jobs.lookup(idempotencyKey);
        if (previous != null) { if (!submissionHash.equals(previous.getJSONObject("request").optString("submissionHash"))) throw new IllegalStateException("此幂等键已经用于另一个任务请求"); return previous; }
        JSONObject request = new GenerationPlan(app).resolve(input);
        JSONObject job = app.jobs.submit(request, idempotencyKey); app.prefs.edit().putBoolean("desiredJobs", true).apply(); wake(); changed.run(); return job;
    }
    /** Same resolver as submit, with no queue, preference, transfer, API or engine launch. */
    public static JSONObject preflight(LmaApp app, JSONObject input) throws Exception {
        if (app.bundles == null || app.artifacts == null || app.localEngines == null) throw new IOException("本地任务模块不可用");
        synchronized (app.bundles) { synchronized (app.artifacts) {
            GenerationPlan plan = new GenerationPlan(app);
            try { plan.resolve(input); plan.report.put("canEnqueue", true); }
            catch (Exception error) {
                String message = error.getMessage(); if (message == null || message.isEmpty()) message = "本地检查未通过";
                plan.report.getJSONArray("issues").put(new JSONObject().put("code", plan.stage).put("message", message.substring(0, Math.min(1200, message.length())))
                        .put("action", plan.stage.equals("assets") || plan.stage.equals("models") || plan.stage.equals("engine") ? "manage_models" : plan.stage.equals("inputs") ? "manage_inputs" : "edit_request"));
            }
            return plan.report;
        } }
    }
    private static final class GenerationPlan {
        final LmaApp app;
        final JSONObject report;
        String stage = "request";
        GenerationPlan(LmaApp app) throws Exception {
            this.app = app;
            report = new JSONObject().put("schema", "lma.task-preflight/1").put("checkedAt", System.currentTimeMillis()).put("canEnqueue", false)
                    .put("deviceValidated", false).put("modelInferenceTested", false).put("checkedStages", new JSONArray()).put("issues", new JSONArray()).put("warnings", new JSONArray());
        }
        void next(String name) throws Exception { report.getJSONArray("checkedStages").put(stage); stage = name; }
        JSONObject resolve(JSONObject raw) throws Exception {
            JSONObject input = TaskInput.validate(raw);
            if (!TaskRequests.generation(input.getString("type"))) throw new IllegalArgumentException("运行前检查仅接受生成任务；运行资产准备和关联请使用对应方案");
            report.put("submissionHash", TaskInput.fingerprint(input));
            next("models");
            String id = input.getString("bundleId"), type = input.getString("type"); ModelBundle bundle = app.bundles.bundle(id);
            report.put("bundleId", id).put("type", type);
            String tag = type.equals("image.generate") ? "image" : type.equals("video.generate") ? "video" : type.equals("text.generate") ? "text" : "audio";
            if (!bundle.tasks.contains(tag)) throw new IllegalArgumentException("所选模型没有对应的输出能力");
            if (AdapterSpec.isAdapter(bundle)) throw new IllegalArgumentException("LoRA 需要先选择兼容的基础模型，不能单独生成");
            next("engine"); LocalEngine selectedEngine = app.localEngines.require(bundle, type);
            InputSpec spec = selectedEngine.inputs(bundle, type); report.put("inputSchema", spec.json());
            next("parameters");
            JSONObject in = input.getJSONObject("input"); String prompt = in.optString("prompt");
            if (prompt.trim().isEmpty() || prompt.length() > 16000 || in.optString("negativePrompt").length() > 16000) throw new IllegalArgumentException("请填写不超过 16000 字符的提示词");
            JSONObject effective = app.bundles.parameters(id).normalize(app.bundles.settings(id).getJSONObject("values"), input.optJSONObject("parameters") == null ? new JSONObject() : input.getJSONObject("parameters"));
            JSONObject request = new JSONObject().put("bundleId", id).put("type", type).put("input", DataFiles.copy(in)).put("parameters", effective.getJSONObject("values"))
                    .put("adjustments", effective.getJSONArray("adjustments")).put("parameterSchemaVersion", effective.getInt("schemaVersion")).put("allowUnmeasured", input.optBoolean("allowUnmeasured", false)).put("submissionHash", report.getString("submissionHash"));
            if (input.has("adapters")) request.put("adapters", DataFiles.copy(input).getJSONArray("adapters"));
            next("assets"); JSONArray assets = new JSONArray(); report.put("modelAssets", assets);
            boolean missing = false;
            for (String selected : ModelSelection.ids(request)) {
                JSONObject plan = app.bundles.plan(selected); JSONArray files = plan.getJSONArray("components"), inventory = new JSONArray();
                for (int i = 0; i < files.length(); i++) { JSONObject file = files.getJSONObject(i); inventory.put(new JSONObject().put("role", file.getString("role")).put("bytes", file.getLong("bytes")).put("present", file.getBoolean("reusable")).put("downloadable", file.getBoolean("downloadable"))); }
                assets.put(new JSONObject().put("bundleId", selected).put("installed", plan.getBoolean("installed")).put("remainingBytes", plan.getLong("remainingBytes")).put("components", inventory));
                if (!plan.getBoolean("installed")) missing = true;
            }
            if (missing) throw new IOException("所选模型或 LoRA 尚未完整安装；请在本地模型中明确下载、续传或导入缺少的组件");
            request = ModelSelection.prepare(app.bundles, bundle, request);
            next("inputs"); request = InputSelection.prepare(app.artifacts, spec, request);
            next("recipe"); request = selectedEngine.prepare(bundle, request);
            report.put("effectiveParameters", DataFiles.copy(request.getJSONObject("parameters"))).put("adjustments", new JSONArray(request.getJSONArray("adjustments").toString()));
            if (request.has("adapters")) report.put("effectiveAdapters", new JSONArray(request.getJSONArray("adapters").toString()));
            if (request.has("adapterAdjustments")) report.put("adapterAdjustments", new JSONArray(request.getJSONArray("adapterAdjustments").toString()));
            next("resources"); JSONObject resources = resourceSnapshot(app, bundle, request, false); report.put("resources", resources); checkResources(resources);
            if (resources.getBoolean("currentlyLowMemory") || resources.getLong("estimatedPeakRamBytes") > resources.getLong("availableRamBytes")) report.getJSONArray("warnings").put(new JSONObject().put("code", "current_memory_pressure").put("message", "当前可用内存偏低；允许排队，执行前会重新检查，可能需要先释放内存"));
            if (!resources.getBoolean("estimateKnown")) report.getJSONArray("warnings").put(new JSONObject().put("code", "memory_estimate_unknown").put("message", "此配方尚无可信峰值内存估算；检查通过不能保证能够完成生成"));
            next("consent"); if (!request.optBoolean("allowUnmeasured")) throw new IllegalStateException("此配方尚无本机实测记录；请明确选择允许尝试未测配方后运行");
            report.getJSONArray("checkedStages").put(stage); return request;
        }
    }
    public JSONObject retry(String id, String key) throws Exception {
        JSONObject old = app.jobs.get(id);
        if (!java.util.Arrays.asList("failed", "interrupted", "cancelled").contains(old.getString("state"))) throw new IllegalStateException("仅已失败、中断或取消的任务可以重试");
        JSONObject request = TaskRequests.replay(old.getJSONObject("request"));
        return submit(request, key);
    }
    private JSONObject submitPreparation(JSONObject input, String key) throws Exception {
        if (app.preparations == null || app.prepared == null) throw new IOException("此基座的模型资产准备模块不可用");
        String hash = TaskInput.fingerprint(input); JSONObject previous = app.jobs.lookup(key);
        if (previous != null) { if (!hash.equals(previous.getJSONObject("request").optString("submissionHash"))) throw new IOException("幂等键已用于其他请求"); return previous; }
        ModelBundle bundle = app.bundles.bundle(input.getString("bundleId")); PreparationPlan plan = app.preparations.require(input, bundle);
        if (!app.bundles.record(bundle.id).optBoolean("installed")) throw new IOException("请先明确下载或导入所选源模型；准备任务不会发起下载");
        if (app.prepared.contains(bundle.id, plan)) throw new IOException("此方案的运行资产已准备完成；可保留或单独删除后重新准备");
        JSONArray queued = app.jobs.snapshot();
        for (int i = 0; i < queued.length(); i++) {
            JSONObject job = queued.getJSONObject(i), request = job.getJSONObject("request");
            if (!java.util.Arrays.asList("succeeded", "failed", "cancelled", "interrupted").contains(job.getString("state")) && request.optString("type").equals("model.prepare") && request.getString("bundleId").equals(bundle.id) && request.optString("planFingerprint").equals(plan.fingerprint)) throw new IOException("这个源模型已有同一方案的准备任务，请查看任务页");
        }
        app.preparations.admission(plan);
        JSONObject request = DataFiles.copy(input).put("submissionHash", hash).put("sourceBundleFingerprint", TaskInput.fingerprint(bundle.json()))
                .put("preparationSource", new JSONObject().put("role", plan.sourceRole).put("bytes", plan.sourceBytes).put("sha256", plan.sourceSha256));
        JSONObject job = app.jobs.submit(request, key); app.prefs.edit().putBoolean("desiredJobs", true).apply(); wake(); changed.run(); return job;
    }
    private JSONObject submitAssembly(JSONObject input, String key) throws Exception {
        if (app.assemblies == null || app.prepared == null) throw new IOException("此基座的运行模型关联模块不可用");
        String hash = TaskInput.fingerprint(input); JSONObject previous = app.jobs.lookup(key);
        if (previous != null) { if (!hash.equals(previous.getJSONObject("request").optString("submissionHash"))) throw new IOException("幂等键已用于其他请求"); return previous; }
        AssemblyPlan plan = app.assemblies.require(input);
        JSONArray queued = app.jobs.snapshot();
        for (int i = 0; i < queued.length(); i++) {
            JSONObject job = queued.getJSONObject(i), request = job.getJSONObject("request");
            if (!java.util.Arrays.asList("succeeded", "failed", "cancelled", "interrupted").contains(job.getString("state")) && request.optString("type").equals("model.assemble") && request.getString("bundleId").equals(plan.bundleId)) throw new IOException("这个运行模型已有资产关联任务，请查看任务页");
        }
        app.assemblies.admission();
        JSONObject request = DataFiles.copy(input).put("submissionHash", hash).put("assemblySourceFingerprint", TaskInput.fingerprint(app.prepared.record(input.getString("preparedAssetsId"))));
        JSONObject job = app.jobs.submit(request, key); app.prefs.edit().putBoolean("desiredJobs", true).apply(); wake(); changed.run(); return job;
    }
    private JSONObject admission(ModelBundle bundle, JSONObject request, boolean executing) throws Exception {
        if (!request.optBoolean("allowUnmeasured")) throw new IllegalStateException("此配方尚无本机实测记录；请明确选择允许尝试未测配方后运行");
        JSONObject resources = resourceSnapshot(app, bundle, request, executing); checkResources(resources); return resources;
    }
    private static JSONObject resourceSnapshot(LmaApp app, ModelBundle bundle, JSONObject request, boolean executing) throws Exception {
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo(); ((ActivityManager) app.getSystemService(LmaApp.ACTIVITY_SERVICE)).getMemoryInfo(memory);
        long reserve = Math.max(384L * 1024 * 1024, memory.totalMem / 8), budget = Math.max(0, (executing ? memory.availMem : memory.totalMem) - reserve);
        JSONObject resources = bundle.json().optJSONObject("resources"); long estimate = resources == null ? 0 : resources.optLong("estimatedPeakRamBytes");
        boolean baseEstimateKnown = estimate > 0; long adapterEstimate = 0;
        JSONArray selectedAdapters = request.optJSONArray("adapters");
        if (selectedAdapters != null) for (int i = 0; i < selectedAdapters.length(); i++) adapterEstimate = Math.addExact(adapterEstimate, AdapterSpec.extraRam(app.bundles.bundle(selectedAdapters.getJSONObject(i).getString("bundleId"))));
        estimate = Math.addExact(estimate, adapterEstimate);
        JSONObject p = request.getJSONObject("parameters"); long width = p.optLong("width", 512), height = p.optLong("height", 512), frames = request.getString("type").equals("video.generate") ? p.optLong("frames", 17) : 1;
        if (width < 1 || height < 1 || width > 16384 || height > 16384 || frames < 1 || frames > 1000) throw new IOException("输出尺寸超出基座预算范围");
        long outputBytes = Math.addExact(Math.multiplyExact(Math.multiplyExact(width, height), Math.multiplyExact(frames, 4)), 128L * 1024 * 1024);
        int thermal = Build.VERSION.SDK_INT >= 29 ? ((PowerManager) app.getSystemService(LmaApp.POWER_SERVICE)).getCurrentThermalStatus() : -1;
        return new JSONObject().put("phase", executing ? "execution" : "queue_preflight").put("availableRamBytes", memory.availMem).put("reservedRamBytes", reserve).put("budgetRamBytes", budget).put("estimatedPeakRamBytes", estimate)
                .put("estimateKnown", baseEstimateKnown).put("adapterExtraRamGuardBytes", adapterEstimate).put("deviceValidated", false).put("outputReserveBytes", outputBytes).put("availableStorageBytes", app.getFilesDir().getUsableSpace())
                .put("currentlyLowMemory", memory.lowMemory).put("thermalStatus", thermal).put("checkedAt", System.currentTimeMillis());
    }
    private static void checkResources(JSONObject resources) throws Exception {
        boolean executing = resources.getString("phase").equals("execution"); long budget = resources.getLong("budgetRamBytes"), estimate = resources.getLong("estimatedPeakRamBytes");
        if (executing && resources.getBoolean("currentlyLowMemory") || budget < 128L * 1024 * 1024 || estimate > 0 && estimate > budget) throw new IOException("当前共享内存不足，请释放内存或选择更小的合法配方");
        if (executing && resources.getInt("thermalStatus") >= PowerManager.THERMAL_STATUS_SEVERE) throw new IOException("手机当前温度过高，请降温后重试");
        if (resources.getLong("availableStorageBytes") < resources.getLong("outputReserveBytes")) throw new IOException("生成产物和临时帧所需空间不足");
    }
    public boolean busy() { return pumping.get() || !activeId.isEmpty(); }
    public String activeId() { return activeId; }
    public void cancel(String id) throws Exception { app.jobs.cancel(id); if (id.equals(activeId)) signalStop(activeProcess); changed.run(); }
    public void cancelAll() throws Exception { JSONArray jobs = app.jobs.snapshot(); for (int i = 0; i < jobs.length(); i++) app.jobs.cancel(jobs.getJSONObject(i).getString("id")); signalStop(activeProcess); changed.run(); }
    public synchronized void wake() {
        if (closed || !pumping.compareAndSet(false, true)) return;
        worker.execute(() -> {
            try { while (!closed) { JSONObject job = app.jobs.claimNext(); if (job == null) break; run(job); } }
            catch (Exception error) { app.error("本地任务队列异常：" + error.getMessage()); }
            finally {
                pumping.set(false); changed.run();
                try { if (!closed) { boolean queued = false, active = false; JSONArray jobs = app.jobs.snapshot(); for (int i = 0; i < jobs.length(); i++) { String s = jobs.getJSONObject(i).getString("state"); if (s.equals("queued")) queued = true; if (s.equals("loading") || s.equals("running") || s.equals("cancelling")) active = true; } if (queued && !active) wake(); else if (queued) timer.schedule(this::wake, 250, TimeUnit.MILLISECONDS); else if (!active) app.prefs.edit().putBoolean("desiredJobs", false).apply(); } } catch (Exception error) { app.log("任务恢复检查失败：" + error.getMessage()); }
                resident.resumeIfIdle();
            }
        });
    }
    private void run(JSONObject job) throws Exception {
        String id = job.getString("id"), token = job.getString("token"); activeId = id; AtomicBoolean timedOut = new AtomicBoolean(); JSONObject request = job.getJSONObject("request");
        ScheduledFuture<?> timeout = null; String artifactId = "", preparedId = "";
        PreparedAssets.Session preparationSession = null;
        ExecutionGate.Ticket slot = null; boolean acquired = false, parked = false;
        BundleStore.Selection selection = null; InputSelection.Selection inputs = null;
        try {
            final ExecutionGate.Ticket owned = app.execution.enqueue("job", request.getString("bundleId")); slot = owned;
            app.jobs.progress(id, token, "waiting_engine", null); changed.run();
            ExecutionGate.Check check = () -> { if (closed) throw new IOException("任务服务已结束"); app.jobs.check(id, token); };
            owned.await(check); acquired = true; check.run(); parked = true; resident.park(owned); check.run();
            timeout = timer.schedule(() -> { timedOut.set(true); signalStop(activeProcess); }, 2, TimeUnit.HOURS);
            if (request.getString("type").equals("model.assemble")) {
                final AssemblyPlan plan = app.assemblies.require(request); app.assemblies.admission();
                PreparedModelAssembly.Context context = new PreparedModelAssembly.Context() {
                    @Override public void check() throws IOException { owned.checkOwner(); if (closed || timedOut.get()) throw new IOException("运行模型关联已停止或超时，已校验的本地文件保留"); app.jobs.check(id, token); }
                    @Override public void progress(String stage) throws Exception { check(); app.jobs.progress(id, token, stage, null); changed.run(); }
                };
                JSONObject result = PreparedModelAssembly.run(plan, app.prepared, app.bundles, request, id, context);
                app.jobs.finishAssembly(id, token, result, ""); return;
            }
            selection = app.bundles.acquireAll(ModelSelection.ids(request));
            BundleStore.Lease model = selection.models.get(0);
            if (request.getString("type").equals("model.prepare")) {
                final PreparationPlan plan = app.preparations.require(request, model.bundle); app.preparations.admission(plan);
                preparationSession = app.prepared.begin(id);
                NativePreparation.Context preparationContext = new NativePreparation.Context() {
                    @Override public void check() throws IOException { owned.checkOwner(); if (closed || timedOut.get()) throw new IOException("模型资产准备已停止或超时，源文件保留"); app.jobs.check(id, token); }
                    @Override public void progress(String stage, Double fraction) throws Exception { check(); app.jobs.progress(id, token, stage, fraction); changed.run(); }
                    @Override public File graphs(PreparationPlan.Stage stage) throws Exception { check(); return app.preparations.graphs(plan, stage); }
                    @Override public Process start(ProcessBuilder builder) throws Exception {
                        synchronized (app.nativeProcessLock) {
                            check(); if (app.nativeProcess != null && app.nativeProcess.isAlive()) throw new IOException("另一个本地进程仍在退出，请等待系统回收");
                            Process process = builder.start(); activeProcess = process; app.nativeProcess = process;
                            try { check(); } catch (Exception error) { destroy(process); throw error; } return process;
                        }
                    }
                };
                app.preparations.run(plan, model, preparationSession, preparationContext);
                JSONObject prepared = preparationSession.commit(plan, model.bundle.id, preparationContext::check); preparedId = prepared.getString("id");
                app.jobs.finishPreparation(id, token, prepared, "");
                if (!app.jobs.get(id).getString("state").equals("succeeded")) { app.prepared.remove(preparedId); preparedId = ""; }
                return;
            }
            java.util.List<BundleStore.Lease> adapters = selection.models.subList(1, selection.models.size());
            JSONObject executionDetails = new JSONObject();
            JSONObject resourcePlan = admission(model.bundle, request, true); app.jobs.progress(id, token, "loading", null); changed.run(); LocalEngine engine = app.localEngines.require(model.bundle, request.getString("type"));
            inputs = InputSelection.acquire(app.artifacts, engine.inputs(model.bundle, request.getString("type")), request, () -> { if (closed || timedOut.get()) throw new IOException("Input validation was stopped"); app.jobs.check(id, token); });
            final InputSelection.Selection selectedInputs = inputs;
            File output = engine.generate(new LocalEngine.Context() {
                @Override public BundleStore.Lease model() { return model; }
                @Override public java.util.List<BundleStore.Lease> adapters() { return adapters; }
                @Override public File input(String role) throws Exception { return selectedInputs.file(role); }
                @Override public JSONObject request() { return DataFiles.copy(request); }
                @Override public File output(String suffix) throws Exception { return app.artifacts.staging(id, suffix); }
                @Override public void check() throws Exception { owned.checkOwner(); if (closed) throw new IOException("任务服务已结束"); if (timedOut.get()) throw new IOException("本地执行超过应用的两小时单任务保护时限"); app.jobs.check(id, token); }
                @Override public void progress(String stage, Double fraction) throws Exception { check(); app.jobs.progress(id, token, stage, fraction); changed.run(); }
                @Override public void process(Process process) throws Exception { activeProcess = process; try { check(); } catch (Exception error) { destroy(process); throw error; } }
                @Override public void execution(JSONObject details) throws Exception { check(); if (details.toString().length() > 16000) throw new IOException("引擎执行元数据过长"); executionDetails.put("details", DataFiles.copy(details)); }
            });
            if (timedOut.get()) throw new IOException("本地执行超过应用的两小时单任务保护时限");
            JSONArray adapterManifests = new JSONArray(), adapterReceipts = new JSONArray(); for (BundleStore.Lease adapter : adapters) { adapterManifests.put(adapter.bundle.json()); adapterReceipts.put(new JSONObject().put("bundleId", adapter.bundle.id).put("components", adapter.integrity())); }
            JSONObject provenance = new JSONObject().put("adapters", adapterManifests).put("componentReceipts", model.integrity()).put("adapterComponentReceipts", adapterReceipts).put("request", request).put("bundle", model.bundle.json()).put("engine", engine.describe()).put("resourcePlan", resourcePlan).put("device", app.device()).put("execution", "same_android_phone").put("engineExecution", executionDetails);
            JSONObject artifact = app.artifacts.commit(id, output, provenance, () -> { if (closed || timedOut.get()) throw new IOException("任务已停止，结果不会记作成功"); app.jobs.check(id, token); }); artifactId = artifact.getString("id");
            app.jobs.finish(id, token, new JSONArray().put(artifactId), "");
            if (!app.jobs.get(id).getString("state").equals("succeeded")) { app.artifacts.remove(artifactId); artifactId = ""; }
        } catch (Exception error) {
            if (!preparedId.isEmpty()) try { app.prepared.remove(preparedId); } catch (Exception cleanup) { app.log("准备资产清理待重试：" + cleanup.getMessage()); }
            if (!artifactId.isEmpty()) try { app.artifacts.remove(artifactId); } catch (Exception cleanup) { app.log("结果清理待重试：" + cleanup.getMessage()); }
            if (closed) app.jobs.interrupt(id, token, "服务结束；此引擎没有可续步 checkpoint，可明确重试新任务");
            else app.jobs.finish(id, token, new JSONArray(), timedOut.get() ? "本地执行超过应用的两小时单任务保护时限" : error.getMessage() == null ? error.toString() : error.getMessage());
        } finally {
            if (timeout != null) timeout.cancel(false);
            Process child = activeProcess;
            try { ProcessControl.stop(child); } catch (IOException error) { app.log(error.getMessage()); }
            final BundleStore.Selection held = selection; final InputSelection.Selection heldInputs = inputs;
            final PreparedAssets.Session heldPreparation = preparationSession;
            Process remaining = child != null && child.isAlive() ? child : parked ? app.nativeProcess : null;
            Runnable cleanup = () -> {
                if (heldPreparation != null) try { heldPreparation.close(); } catch (IOException error) { app.log("准备临时文件清理待重试：" + error.getMessage()); }
                if (heldInputs != null) heldInputs.close();
                if (held != null) held.close();
                try { app.artifacts.discardStaging(id); } catch (Exception error) { app.log("临时产物清理失败：" + error.getMessage()); }
                changed.run();
            };
            if (slot != null && acquired) slot.releaseAfter(remaining, cleanup);
            else { if (slot != null) slot.close(); cleanup.run(); }
            activeProcess = null; activeId = ""; changed.run();
        }
    }
    private static void destroy(Process process) { try { ProcessControl.stop(process); } catch (IOException ignored) {} }
    private static void signalStop(Process process) {
        if (process == null) return;
        process.destroy();
        Thread reaper = new Thread(() -> destroy(process), "LMA-worker-stop"); reaper.setDaemon(true); reaper.start();
    }
    @Override public synchronized void close() { closed = true; signalStop(activeProcess); timer.shutdownNow(); worker.shutdown(); }
}
