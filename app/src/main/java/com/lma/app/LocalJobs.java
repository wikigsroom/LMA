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
    private final Runnable changed;
    private final ExecutorService worker = Executors.newSingleThreadExecutor(r -> new Thread(r, "LMA-local-jobs"));
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor(r -> new Thread(r, "LMA-engine-timeout"));
    private final AtomicBoolean pumping = new AtomicBoolean();
    private volatile boolean closed;
    private volatile String activeId = "";
    private volatile Process activeProcess;
    public LocalJobs(LmaApp app, Runnable changed) { this.app = app; this.changed = changed; }
    public JSONObject submit(JSONObject input, String idempotencyKey) throws Exception {
        if (closed) throw new IllegalStateException("任务服务正在停止");
        input = TaskInput.validate(input);
        String submissionHash = TaskInput.fingerprint(input);
        JSONObject previous = app.jobs.lookup(idempotencyKey);
        if (previous != null) { if (!submissionHash.equals(previous.getJSONObject("request").optString("submissionHash"))) throw new IllegalStateException("此幂等键已经用于另一个任务请求"); return previous; }
        String id = input.getString("bundleId"), type = input.getString("type"); ModelBundle bundle = app.bundles.bundle(id);
        String tag = type.equals("image.generate") ? "image" : type.equals("video.generate") ? "video" : type.equals("text.generate") ? "text" : type.equals("speech.synthesize") || type.equals("audio.generate") ? "audio" : "";
        if (tag.isEmpty() || !bundle.tasks.contains(tag)) throw new IllegalArgumentException("所选模型没有对应的输出能力");
        if (AdapterSpec.isAdapter(bundle)) throw new IllegalArgumentException("LoRA 需要先选择兼容的基础模型，不能单独生成");
        LocalEngine selectedEngine = app.localEngines.require(bundle, type);
        JSONObject in = input.getJSONObject("input"); String prompt = in.optString("prompt");
        if (prompt.trim().isEmpty() || prompt.length() > 16000 || in.optString("negativePrompt").length() > 16000) throw new IllegalArgumentException("请填写不超过 16000 字符的提示词");
        JSONObject effective = bundle.parameters().normalize(app.bundles.settings(id).getJSONObject("values"), input.optJSONObject("parameters") == null ? new JSONObject() : input.getJSONObject("parameters"));
        JSONObject request = new JSONObject().put("bundleId", id).put("type", type).put("input", DataFiles.copy(in)).put("parameters", effective.getJSONObject("values"))
                .put("adjustments", effective.getJSONArray("adjustments")).put("parameterSchemaVersion", effective.getInt("schemaVersion")).put("allowUnmeasured", input.optBoolean("allowUnmeasured", false)).put("submissionHash", submissionHash);
        if (input.has("adapters")) request.put("adapters", DataFiles.copy(input).getJSONArray("adapters"));
        request = ModelSelection.prepare(app.bundles, bundle, request);
        request = selectedEngine.prepare(bundle, request);
        admission(bundle, request);
        JSONObject job = app.jobs.submit(request, idempotencyKey); app.prefs.edit().putBoolean("desiredJobs", true).apply(); wake(); changed.run(); return job;
    }
    public JSONObject retry(String id, String key) throws Exception {
        JSONObject old = app.jobs.get(id);
        if (!java.util.Arrays.asList("failed", "interrupted", "cancelled").contains(old.getString("state"))) throw new IllegalStateException("仅已失败、中断或取消的任务可以重试");
        JSONObject request = DataFiles.copy(old.getJSONObject("request")); request.remove("submissionHash"); request.remove("adjustments"); request.remove("parameterSchemaVersion"); request.remove("adapterAdjustments");
        return submit(request, key);
    }
    private JSONObject admission(ModelBundle bundle, JSONObject request) throws Exception {
        if (!app.engineState.equals("stopped") && !app.engineState.equals("error")) throw new IllegalStateException("请先停止文本模型，再提交媒体任务；本机一次运行一个大型引擎");
        if (!request.optBoolean("allowUnmeasured")) throw new IllegalStateException("此配方尚无本机实测记录；请明确选择允许尝试未测配方后运行");
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo(); ((ActivityManager) app.getSystemService(LmaApp.ACTIVITY_SERVICE)).getMemoryInfo(memory);
        long reserve = Math.max(384L * 1024 * 1024, memory.totalMem / 8), budget = Math.max(0, memory.availMem - reserve);
        JSONObject resources = bundle.json().optJSONObject("resources"); long estimate = resources == null ? 0 : resources.optLong("estimatedPeakRamBytes");
        boolean baseEstimateKnown = estimate > 0; long adapterEstimate = 0;
        JSONArray selectedAdapters = request.optJSONArray("adapters");
        if (selectedAdapters != null) for (int i = 0; i < selectedAdapters.length(); i++) adapterEstimate = Math.addExact(adapterEstimate, AdapterSpec.extraRam(app.bundles.bundle(selectedAdapters.getJSONObject(i).getString("bundleId"))));
        estimate = Math.addExact(estimate, adapterEstimate);
        if (memory.lowMemory || budget < 128L * 1024 * 1024 || estimate > 0 && estimate > budget) throw new IOException("当前共享内存不足，请释放内存或选择更小的合法配方");
        if (Build.VERSION.SDK_INT >= 29 && ((PowerManager) app.getSystemService(LmaApp.POWER_SERVICE)).getCurrentThermalStatus() >= PowerManager.THERMAL_STATUS_SEVERE) throw new IOException("手机当前温度过高，请降温后重试");
        JSONObject p = request.getJSONObject("parameters"); long width = p.optLong("width", 512), height = p.optLong("height", 512), frames = request.getString("type").equals("video.generate") ? p.optLong("frames", 17) : 1;
        if (width < 1 || height < 1 || width > 16384 || height > 16384 || frames < 1 || frames > 1000) throw new IOException("输出尺寸超出基座预算范围");
        long outputBytes = Math.addExact(Math.multiplyExact(Math.multiplyExact(width, height), Math.multiplyExact(frames, 4)), 128L * 1024 * 1024);
        if (app.getFilesDir().getUsableSpace() < outputBytes) throw new IOException("生成产物和临时帧所需空间不足");
        return new JSONObject().put("availableRamBytes", memory.availMem).put("reservedRamBytes", reserve).put("budgetRamBytes", budget).put("estimatedPeakRamBytes", estimate)
                .put("estimateKnown", baseEstimateKnown).put("adapterExtraRamGuardBytes", adapterEstimate).put("deviceValidated", false).put("outputReserveBytes", outputBytes).put("checkedAt", System.currentTimeMillis());
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
            }
        });
    }
    private void run(JSONObject job) throws Exception {
        String id = job.getString("id"), token = job.getString("token"); activeId = id; AtomicBoolean timedOut = new AtomicBoolean(); JSONObject request = job.getJSONObject("request");
        ScheduledFuture<?> timeout = timer.schedule(() -> { timedOut.set(true); destroy(activeProcess); }, 2, TimeUnit.HOURS); String artifactId = "";
        try (BundleStore.Selection selection = app.bundles.acquireAll(ModelSelection.ids(request))) {
            BundleStore.Lease model = selection.models.get(0);
            java.util.List<BundleStore.Lease> adapters = selection.models.subList(1, selection.models.size());
            JSONObject executionDetails = new JSONObject();
            JSONObject resourcePlan = admission(model.bundle, request); app.jobs.progress(id, token, "loading", null); changed.run(); LocalEngine engine = app.localEngines.require(model.bundle, request.getString("type"));
            File output = engine.generate(new LocalEngine.Context() {
                @Override public BundleStore.Lease model() { return model; }
                @Override public java.util.List<BundleStore.Lease> adapters() { return adapters; }
                @Override public JSONObject request() { return DataFiles.copy(request); }
                @Override public File output(String suffix) throws Exception { return app.artifacts.staging(id, suffix); }
                @Override public void check() throws Exception { if (closed) throw new IOException("任务服务已结束"); if (timedOut.get()) throw new IOException("本地执行超过应用的两小时单任务保护时限"); app.jobs.check(id, token); }
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
            if (!artifactId.isEmpty()) try { app.artifacts.remove(artifactId); } catch (Exception cleanup) { app.log("结果清理待重试：" + cleanup.getMessage()); }
            if (closed) app.jobs.interrupt(id, token, "服务结束；此引擎没有可续步 checkpoint，可明确重试新任务");
            else app.jobs.finish(id, token, new JSONArray(), timedOut.get() ? "本地执行超过应用的两小时单任务保护时限" : error.getMessage() == null ? error.toString() : error.getMessage());
        } finally {
            timeout.cancel(false); destroy(activeProcess); activeProcess = null; activeId = "";
            try { app.artifacts.discardStaging(id); } catch (Exception error) { app.log("临时产物清理失败：" + error.getMessage()); } changed.run();
        }
    }
    private static void destroy(Process process) { if (process == null) return; process.destroy(); try { if (!process.waitFor(2, TimeUnit.SECONDS)) process.destroyForcibly(); } catch (InterruptedException error) { Thread.currentThread().interrupt(); process.destroyForcibly(); } }
    private static void signalStop(Process process) {
        if (process == null) return;
        process.destroy();
        Thread reaper = new Thread(() -> destroy(process), "LMA-worker-stop"); reaper.setDaemon(true); reaper.start();
    }
    @Override public synchronized void close() { closed = true; signalStop(activeProcess); timer.shutdownNow(); worker.shutdown(); }
}
