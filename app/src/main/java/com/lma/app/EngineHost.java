package com.lma.app;

import com.lma.app.core.BundleStore;
import com.lma.app.core.ExecutionGate;
import com.lma.app.core.ProcessControl;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/** Persistent text residency shares the service execution slot with every queued engine. */
public final class EngineHost {
    private final LmaService owner;
    private final LmaApp app;
    private final AtomicLong generation = new AtomicLong();
    private final ExecutorService workers = Executors.newCachedThreadPool();
    private volatile Process process;
    private volatile BundleStore.Lease currentLease;
    private volatile boolean desired, closed;
    private volatile int failures;
    private ExecutionGate.Ticket warmTicket;
    interface Launcher { Process start(ProcessBuilder builder) throws IOException; }
    private final Launcher launcher;
    public EngineHost(LmaService owner, LmaApp app) { this(owner, app, ProcessBuilder::start); }
    EngineHost(LmaService owner, LmaApp app, Launcher launcher) { this.owner = owner; this.app = app; this.launcher = launcher; }
    public boolean wanted() { return desired; }
    public boolean ready() { return desired && app.engineState.equals("ready") && process != null && process.isAlive(); }

    public void load(String id) throws Exception {
        synchronized (app.requestGate) { synchronized (this) {
            if (closed) throw new IllegalStateException("推理服务正在停止，请稍后重试");
            app.store.model(id);
            if (!app.store.installed(id)) throw new IllegalStateException("请先下载或导入这个模型");
            if (app.generating || app.textRequestBusy) throw new IllegalStateException("请先停止当前回复，再切换模型");
            if (ready() && id.equals(app.engineModel)) return;
            desired = true; failures = 0; long request = generation.incrementAndGet(); destroyProcess();
            app.prefs.edit().putString("selectedModel", id).putBoolean("desiredRunning", true).apply();
            app.engineModel = id;
            try { queueWarm(id, request); } catch (Exception error) { fail(request, error, false); throw error; }
        } }
    }
    private void queueWarm(String id, long request) throws Exception { queueWarm(id, request, app.execution.enqueue("load", id)); }
    private void queueWarm(String id, long request, ExecutionGate.Ticket ticket) throws Exception {
        if (warmTicket != null) warmTicket.close();
        warmTicket = ticket;
        app.engineState = "waiting"; app.engineDetail = "已选择文本模型，等待本机执行槽"; app.engineStarted = 0; app.emit(); owner.activityChanged();
        workers.execute(() -> {
            try (ExecutionGate.Ticket slot = ticket) {
                ExecutionGate.Check check = () -> { if (!current(request)) throw new InterruptedIOException("文本加载请求已取消或更改"); };
                slot.await(check); check.run(); launch(id, request, slot, check);
            } catch (Exception error) { fail(request, error, false); }
            finally { synchronized (this) { if (warmTicket == ticket) warmTicket = null; } owner.activityChanged(); }
        });
    }
    /** Restore only an explicitly wanted local model; never selects or downloads an asset. */
    public void resumeIfIdle() {
        if (app.jobHost != null && app.jobHost.busy()) return;
        synchronized (this) {
            if (closed || !desired || ready() || warmTicket != null) return;
            long request = generation.get();
            try {
                ExecutionGate.Ticket idle = app.execution.enqueueIfIdle("load", app.engineModel);
                if (idle == null) return;
                request = generation.incrementAndGet(); queueWarm(app.engineModel, request, idle);
            } catch (Exception error) { fail(request, error, false); }
        }
    }
    /** Called by a chat/API ticket after earlier jobs finish, with the frozen requested alias. */
    public void ensureReady(ExecutionGate.Ticket slot, String id, ExecutionGate.Check check) throws Exception {
        slot.checkOwner(); check.run(); long request;
        synchronized (this) {
            if (closed || !desired || !id.equals(app.engineModel)) throw new IOException("所选文本模型已停止或更改，请重新提交");
            if (ready()) return;
            if (warmTicket != null) { warmTicket.close(); warmTicket = null; }
            request = generation.incrementAndGet();
        }
        try { launch(id, request, slot, check); }
        catch (Exception error) {
            boolean cancelled = false; try { check.run(); } catch (Exception stopped) { cancelled = true; }
            fail(request, error, cancelled); throw error;
        }
        check.run();
        if (!ready() || !id.equals(app.engineModel)) throw new IOException("文本模型未就绪或已更改");
    }
    /** Executed only with the shared slot: finish replies first, then reap old memory ownership. */
    public void park(ExecutionGate.Ticket slot) throws Exception {
        slot.checkOwner();
        synchronized (this) {
            generation.incrementAndGet();
            if (warmTicket != null) { warmTicket.close(); warmTicket = null; }
            destroyProcess();
            if (desired) { app.engineState = "suspended"; app.engineDetail = "文本模型暂时卸载，由本机队列使用执行槽；空闲后恢复"; }
            app.engineStarted = 0;
        }
        synchronized (app.nativeProcessLock) {
            Process previous = app.nativeProcess; ProcessControl.stop(previous);
            if (app.nativeProcess == previous && (previous == null || !previous.isAlive())) app.nativeProcess = null;
        }
        app.emit(); owner.activityChanged();
    }
    public void configure(String id, JSONObject changes) throws Exception {
        synchronized (app.requestGate) { synchronized (this) {
            JSONObject current = app.store.inspectModel(id).getJSONObject("values"), next = app.store.previewConfig(id, changes);
            boolean reload = id.equals(app.engineModel) && wanted() && ModelSettings.reload(current, next);
            if (reload && (app.generating || app.textRequestBusy)) throw new IllegalStateException("请先停止当前回复，再修改此模型的加载参数");
            BundleStore.Lease held = id.equals(app.engineModel) && process != null && process.isAlive() ? currentLease : null;
            app.store.saveConfig(id, next, held);
            if (reload) { stop(); load(id); }
        } }
    }
    public synchronized void stop() {
        desired = false; generation.incrementAndGet();
        if (warmTicket != null) { warmTicket.close(); warmTicket = null; }
        app.prefs.edit().putBoolean("desiredRunning", false).apply(); destroyProcess();
        app.engineState = "stopped"; app.engineDetail = "文本模型已停止；其他已启动接口与任务独立管理"; app.engineStarted = 0; app.emit(); owner.activityChanged();
    }
    public synchronized void close() {
        closed = true; desired = false; generation.incrementAndGet();
        if (warmTicket != null) { warmTicket.close(); warmTicket = null; }
        destroyProcess(); workers.shutdown();
    }
    private boolean current(long request) { return !closed && desired && request == generation.get(); }
    private synchronized void destroyProcess() {
        Process old = process; process = null; currentLease = null;
        if (old != null) {
            old.destroy();
            workers.execute(() -> { try { ProcessControl.stop(old); } catch (IOException error) { app.log(error.getMessage()); } });
        }
    }
    private void fail(long request, Exception error, boolean cancelled) {
        synchronized (this) {
            if (!current(request)) return;
            destroyProcess();
            if (cancelled) { app.engineState = "suspended"; app.engineDetail = "文本请求已取消；原模型仍为用户选择"; }
            else {
                desired = false; app.prefs.edit().putBoolean("desiredRunning", false).apply(); app.engineState = "error";
                app.engineDetail = "加载失败：" + error.getMessage(); app.error(app.engineDetail);
            }
        }
        app.emit(); owner.activityChanged();
    }
    private void launch(String id, long request, ExecutionGate.Ticket slot, ExecutionGate.Check check) throws Exception {
        BundleStore.Lease lease = null;
        try {
            check.run(); if (!current(request)) throw new InterruptedIOException("文本模型已停止或更改"); slot.checkOwner();
            synchronized (this) { if (!current(request)) return; app.engineState = "loading"; app.engineDetail = "正在加载用户选择的本地模型"; }
            app.emit(); owner.activityChanged();
            File nativeDir = new File(app.getApplicationInfo().nativeLibraryDir), binary = new File(nativeDir, "libllama-server.so");
            if (!binary.isFile() || !binary.canExecute()) throw new IOException("推理组件未正确安装，请重新安装 LMA APK");
            lease = app.store.acquireBundle(id); app.store.inspectModel(id); JSONObject settings = app.settings(id);
            int privatePort;
            try (java.net.ServerSocket reserved = new java.net.ServerSocket(0, 1, java.net.InetAddress.getByName("127.0.0.1"))) { privatePort = reserved.getLocalPort(); }
            byte[] randomKey = new byte[24]; new java.security.SecureRandom().nextBytes(randomKey);
            String privateKey = com.lma.app.core.Protocol.hex(randomKey); List<String> command = new ArrayList<>();
            command.add(binary.getAbsolutePath()); add(command, "-m", app.store.modelFile(id).getAbsolutePath()); add(command, "--alias", id);
            add(command, "--host", "127.0.0.1"); add(command, "--port", String.valueOf(privatePort));
            add(command, "-t", String.valueOf(settings.getInt("threads"))); add(command, "-c", String.valueOf(settings.getInt("context")));
            add(command, "-b", "64"); add(command, "-ub", "64"); add(command, "-np", "1"); add(command, "-ngl", "0"); add(command, "--device", "none");
            command.add("--jinja"); command.add("--no-webui"); command.add("--metrics"); add(command, "--reasoning", settings.getString("reasoning"));
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true).directory(app.getFilesDir());
            builder.environment().put("LD_LIBRARY_PATH", nativeDir.getAbsolutePath());
            builder.environment().put("ADSP_LIBRARY_PATH", nativeDir.getAbsolutePath() + ";/vendor/lib/rfsa/adsp;/vendor/dsp;/system/lib/rfsa/adsp;/dsp");
            builder.environment().put("LLAMA_API_KEY", privateKey);
            final Process active;
            synchronized (app.nativeProcessLock) {
                check.run(); if (!current(request)) throw new InterruptedIOException("文本加载已取消");
                Process previous = app.nativeProcess; ProcessControl.stop(previous); slot.checkOwner();
                check.run();
                synchronized (this) {
                    if (!current(request)) throw new InterruptedIOException("文本加载已取消");
                    active = launcher.start(builder); process = active; currentLease = lease;
                    app.nativeProcess = active; app.nativePort = privatePort; app.nativeApiKey = privateKey;
                    final BundleStore.Lease ownedLease = lease;
                    workers.execute(() -> watchExit(active, id, request, ownedLease));
                    workers.execute(() -> drain(active)); lease = null;
                }
            }
            app.log("启动模型：" + app.store.model(id).optString("name") + " · CPU / " + settings.getInt("threads") + " 线程");
            long deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(5);
            while (current(request) && process == active && active.isAlive() && System.nanoTime() < deadline) {
                check.run(); HttpURLConnection health = null;
                try {
                    health = Net.engine(app, "/health"); health.setConnectTimeout(1000); health.setReadTimeout(1000);
                    if (health.getResponseCode() == 200 && new JSONObject(Store.read(health.getInputStream(), 65536)).optString("status").equals("ok") && ownsEndpoint(id)) {
                        synchronized (this) {
                            if (!current(request) || process != active) throw new InterruptedIOException("文本加载已更改");
                            app.engineState = "ready"; app.engineDetail = "模型已就绪，可以对话或连接 API"; app.engineStarted = System.currentTimeMillis();
                        }
                        app.emit(); owner.activityChanged(); return;
                    }
                } catch (Exception ignored) {} finally { if (health != null) health.disconnect(); }
                Thread.sleep(100);
            }
            // The registered exit watcher owns bounded recovery, including exits before readiness.
            if (!active.isAlive() && current(request)) return;
            check.run();
            if (current(request)) throw new IOException("模型加载超时，请尝试更小模型或降低上下文");
            throw new InterruptedIOException("文本模型已停止或更改");
        } finally { if (lease != null) lease.close(); }
    }
    private void watchExit(Process active, String id, long request, BundleStore.Lease held) {
        try {
            int code = active.waitFor(); if (held != null) held.close();
            synchronized (app.nativeProcessLock) { if (app.nativeProcess == active) app.nativeProcess = null; }
            synchronized (this) {
                if (!current(request) || process != active) return;
                process = null; currentLease = null; failures++;
                app.log("模型进程退出，代码 " + code + "；恢复次数 " + failures + "/3");
                if (failures > 3) {
                    desired = false; app.prefs.edit().putBoolean("desiredRunning", false).apply(); app.engineState = "error";
                    app.engineDetail = "模型进程连续退出（" + code + "），请查看日志并尝试较小模型"; app.error(app.engineDetail); owner.activityChanged(); return;
                }
                app.engineState = "recovering"; app.engineDetail = "模型意外停止，正在恢复（" + failures + "/3）";
            }
            app.emit(); owner.updateNotification(); Thread.sleep(Math.min(30000, 1500L << (failures - 1)));
            if (current(request)) resumeIfIdle();
        } catch (InterruptedException error) { Thread.currentThread().interrupt(); }
        finally { if (!active.isAlive()) { if (held != null) held.close(); app.migrateTextModels(); } }
    }
    private void drain(Process active) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(active.getInputStream(), StandardCharsets.UTF_8))) {
            String line; while ((line = reader.readLine()) != null) app.log(line);
        } catch (Exception ignored) {}
    }
    private boolean ownsEndpoint(String id) {
        HttpURLConnection connection = null;
        try {
            connection = Net.engine(app, "/v1/models"); connection.setConnectTimeout(1000); connection.setReadTimeout(1000);
            if (connection.getResponseCode() != 200) return false;
            org.json.JSONArray data = new JSONObject(Store.read(connection.getInputStream(), 65536)).optJSONArray("data");
            if (data != null) for (int i = 0; i < data.length(); i++) if (data.getJSONObject(i).optString("id").equals(id)) return true;
        } catch (Exception ignored) {} finally { if (connection != null) connection.disconnect(); }
        return false;
    }
    private static void add(List<String> command, String key, String value) { command.add(key); command.add(value); }
}
