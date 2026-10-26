package com.lma.app;

import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/** Native server lifecycle is owned by the foreground Service, never by WebView. */
public final class EngineHost {
    private final LmaService owner;
    private final LmaApp app;
    private final AtomicLong generation = new AtomicLong();
    private final ExecutorService workers = Executors.newCachedThreadPool();
    private volatile Process process;
    private volatile boolean desired;
    private volatile boolean closed;
    private volatile int failures;
    interface Launcher { Process start(ProcessBuilder builder) throws java.io.IOException; }
    private final Launcher launcher;
    public EngineHost(LmaService owner, LmaApp app) { this(owner, app, ProcessBuilder::start); }
    EngineHost(LmaService owner, LmaApp app, Launcher launcher) { this.owner = owner; this.app = app; this.launcher = launcher; }
    public boolean wanted() { return desired; }
    public boolean ready() { return desired && app.engineState.equals("ready") && process != null && process.isAlive(); }

    public synchronized void load(String id) throws Exception {
        if (closed) throw new IllegalStateException("推理服务正在停止，请稍后重试");
        app.store.model(id);
        if (!app.store.modelFile(id).isFile()) throw new IllegalStateException("请先下载或导入这个模型");
        if (app.generating) throw new IllegalStateException("请先停止当前回复，再切换模型");
        if (ready() && id.equals(app.engineModel)) return;
        desired = true; failures = 0;
        long request = generation.incrementAndGet(); destroyProcess();
        app.prefs.edit().putString("selectedModel", id).putBoolean("desiredRunning", true).apply();
        app.engineModel = id; app.engineState = "loading"; app.engineDetail = "正在加载模型，首次加载可能需要一段时间"; app.engineStarted = 0; app.emit(); owner.activityChanged();
        workers.execute(() -> launch(id, request));
    }
    public synchronized void stop() {
        desired = false; generation.incrementAndGet(); app.prefs.edit().putBoolean("desiredRunning", false).apply(); destroyProcess();
        app.engineState = "stopped"; app.engineDetail = "模型已停止，接口已关闭"; app.engineStarted = 0; app.emit(); owner.activityChanged();
    }
    public synchronized void close() { closed = true; desired = false; generation.incrementAndGet(); destroyProcess(); workers.shutdown(); }
    private boolean current(long request) { return !closed && desired && request == generation.get(); }
    private synchronized void destroyProcess() {
        Process old = process; process = null;
        if (old != null) {
            old.destroy();
            workers.execute(() -> { try { if (!old.waitFor(3, TimeUnit.SECONDS)) old.destroyForcibly(); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); old.destroyForcibly(); } });
        }
    }
    private void launch(String id, long request) {
        Process started = null;
        try {
            if (!current(request)) return;
            File nativeDir = new File(app.getApplicationInfo().nativeLibraryDir);
            File binary = new File(nativeDir, "libllama-server.so");
            if (!binary.isFile() || !binary.canExecute()) throw new java.io.IOException("推理组件未正确安装，请重新安装 LMA APK");
            JSONObject settings = app.settings();
            List<String> command = new ArrayList<>();
            command.add(binary.getAbsolutePath());
            add(command, "-m", app.store.modelFile(id).getAbsolutePath()); add(command, "--alias", id);
            add(command, "--host", settings.getBoolean("lan") ? "0.0.0.0" : "127.0.0.1");
            add(command, "--port", String.valueOf(settings.getInt("port")));
            add(command, "-t", String.valueOf(settings.getInt("threads"))); add(command, "-c", String.valueOf(settings.getInt("context")));
            add(command, "-b", "64"); add(command, "-ub", "64"); add(command, "-np", "1"); add(command, "-ngl", "0"); add(command, "--device", "none");
            command.add("--jinja"); command.add("--no-webui"); command.add("--metrics");
            add(command, "--reasoning", settings.getString("reasoning"));
            ProcessBuilder builder = new ProcessBuilder(command).redirectErrorStream(true);
            builder.directory(app.getFilesDir());
            builder.environment().put("LD_LIBRARY_PATH", nativeDir.getAbsolutePath());
            builder.environment().put("ADSP_LIBRARY_PATH", nativeDir.getAbsolutePath() + ";/vendor/lib/rfsa/adsp;/vendor/dsp;/system/lib/rfsa/adsp;/dsp");
            // Keep the API key out of process argv and application logs.
            builder.environment().put("LLAMA_API_KEY", settings.getString("apiKey"));
            synchronized (app.nativeProcessLock) {
                if (!current(request)) return;
                Process previous = app.nativeProcess;
                if (previous != null && previous.isAlive()) {
                    previous.destroy();
                    if (!previous.waitFor(3, TimeUnit.SECONDS)) { previous.destroyForcibly(); if (!previous.waitFor(3, TimeUnit.SECONDS)) throw new java.io.IOException("旧模型进程尚未退出，请稍后重试"); }
                }
                if (!current(request)) return;
                try (java.net.ServerSocket probe = new java.net.ServerSocket()) {
                    probe.setReuseAddress(true); probe.bind(new java.net.InetSocketAddress(settings.getBoolean("lan") ? "0.0.0.0" : "127.0.0.1", settings.getInt("port")));
                } catch (java.net.BindException error) { throw new java.io.IOException("服务端口 " + settings.getInt("port") + " 已被占用，请在设置中更换端口", error); }
                synchronized (this) {
                    if (!current(request)) return;
                    started = launcher.start(builder); process = started; app.nativeProcess = started;
                }
            }
            final Process active = started;
            app.log("启动模型：" + app.store.model(id).optString("name") + " · CPU / " + settings.getInt("threads") + " 线程");
            workers.execute(() -> drain(active));
            workers.execute(() -> watchExit(active, id, request));
            long deadline = System.currentTimeMillis() + 300000;
            while (current(request) && process == active && active.isAlive() && System.currentTimeMillis() < deadline) {
                HttpURLConnection health = null;
                try {
                    health = Net.local(app, "/health"); health.setReadTimeout(2500);
                    if (health.getResponseCode() == 200) {
                        String body = Store.read(health.getInputStream(), 65536);
                        if (new JSONObject(body).optString("status").equals("ok") && ownsEndpoint(id)) {
                            synchronized (this) {
                                if (!current(request) || process != active) return;
                                app.engineState = "ready"; app.engineDetail = "模型已就绪，可以对话或连接 API"; app.engineStarted = System.currentTimeMillis();
                            }
                            app.emit(); owner.activityChanged(); return;
                        }
                    }
                } catch (Exception ignored) {} finally { if (health != null) health.disconnect(); }
                Thread.sleep(700);
            }
            if (current(request) && process == active && active.isAlive()) throw new java.io.IOException("模型加载超时，请尝试更小模型或降低上下文");
        } catch (Exception error) {
            synchronized (this) {
                if (!current(request)) return;
                desired = false; app.prefs.edit().putBoolean("desiredRunning", false).apply(); destroyProcess();
                app.engineState = "error"; app.engineDetail = "加载失败：" + error.getMessage(); app.error(app.engineDetail);
            }
            owner.activityChanged();
        }
    }
    private void watchExit(Process active, String id, long request) {
        try {
            int code = active.waitFor();
            synchronized (this) {
                if (!current(request) || process != active) return; process = null; failures++;
                app.log("模型进程退出，代码 " + code + "；恢复次数 " + failures + "/3");
                if (failures > 3) {
                    desired = false; app.prefs.edit().putBoolean("desiredRunning", false).apply(); app.engineState = "error";
                    app.engineDetail = "模型进程连续退出（" + code + "），请查看日志并尝试较小模型"; app.error(app.engineDetail); owner.activityChanged(); return;
                }
                app.engineState = "recovering"; app.engineDetail = "模型意外停止，正在恢复（" + failures + "/3）";
            }
            app.emit(); owner.updateNotification();
            Thread.sleep(Math.min(30000, 1500L << (failures - 1)));
            if (current(request)) launch(id, request);
        } catch (InterruptedException error) { Thread.currentThread().interrupt(); }
    }
    private void drain(Process active) {
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(active.getInputStream(), StandardCharsets.UTF_8))) {
            String line; while ((line = reader.readLine()) != null) app.log(line);
        } catch (Exception ignored) {}
    }
    private boolean ownsEndpoint(String id) {
        HttpURLConnection connection = null;
        try {
            connection = Net.local(app, "/v1/models"); connection.setReadTimeout(2500);
            if (connection.getResponseCode() != 200) return false;
            org.json.JSONArray data = new JSONObject(Store.read(connection.getInputStream(), 65536)).optJSONArray("data");
            if (data == null) return false;
            for (int i = 0; i < data.length(); i++) if (data.getJSONObject(i).optString("id").equals(id)) return true;
        } catch (Exception ignored) {} finally { if (connection != null) connection.disconnect(); }
        return false;
    }
    private static void add(List<String> command, String key, String value) { command.add(key); command.add(value); }
}
