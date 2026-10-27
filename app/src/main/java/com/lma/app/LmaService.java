package com.lma.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import org.json.JSONObject;
import com.lma.app.core.BundleTransfers;
import com.lma.app.core.ModelBundle;

public final class LmaService extends Service {
    private static final String CHANNEL = "lma_runtime";
    private static final int NOTIFICATION = 41;
    public EngineHost engine;
    private ChatRunner chat;
    private Downloads downloads;
    private BundleTransfers bundleTransfers;
    private LocalJobs localJobs;
    private ApiHost api;
    private LmaApp app;
    private final Handler main = new Handler(Looper.getMainLooper());
    private PowerManager.WakeLock cpu;
    private WifiManager.WifiLock wifi;
    private boolean restored, stopping;
    private long lastNotification;
    private boolean transfersBusy() { return downloads != null && downloads.busy() || bundleTransfers != null && bundleTransfers.busy(); }
    private boolean apiBusy() { return api != null && api.ready() && api.wanted(); }
    private boolean jobsBusy() { return localJobs != null && localJobs.busy(); }
    private final Runnable idleStop = () -> { if (!stopping && engine != null && !engine.wanted() && !transfersBusy() && !jobsBusy() && !apiBusy() && !app.generating) stopSelf(); };

    @Override public void onCreate() {
        super.onCreate(); app = (LmaApp) getApplication();
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(CHANNEL, "LMA 本地模型服务", NotificationManager.IMPORTANCE_LOW));
        Notification notification = notification("正在准备本地模型服务");
        if (Build.VERSION.SDK_INT >= 34) startForeground(NOTIFICATION, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        else startForeground(NOTIFICATION, notification);
        PowerManager power = (PowerManager) getSystemService(POWER_SERVICE);
        cpu = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "LMA:local-model-service"); cpu.setReferenceCounted(false); cpu.acquire();
        try {
            wifi = ((WifiManager) getApplicationContext().getSystemService(WIFI_SERVICE)).createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "LMA:local-api");
            wifi.setReferenceCounted(false); wifi.acquire();
        } catch (Exception error) { app.log("Wi-Fi 唤醒锁不可用：" + error.getMessage()); }
        engine = new EngineHost(this, app); chat = new ChatRunner(this, app); downloads = new Downloads(this, app);
        if (app.bundles != null) bundleTransfers = new BundleTransfers(app.bundles,
                (component, offset, observer) -> {
                    String token = app.prefs.getString("hfToken", "");
                    String[] sources = Net.modelSources(component.url, token.isEmpty() ? app.prefs.getString("source", "auto") : "official");
                    return Net.downloadCandidates(sources, offset, "", observer::opened, token);
                }, new BundleTransfers.Listener() {
                    @Override public void changed() { activityChanged(); }
                    @Override public void installed(String id) { app.log("模型包已完整安装：" + id); activityChanged(); }
                    @Override public void failed(String id, String message) { app.error("模型包下载失败：" + message); activityChanged(); }
                });
        if (app.jobs != null && app.artifacts != null && app.localEngines != null) { localJobs = new LocalJobs(app, this::activityChanged); app.jobHost = localJobs; }
        api = new ApiHost(this, app); app.apiHost = api;
    }
    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && "STOP_ALL".equals(intent.getAction())) { stopAll(); return START_NOT_STICKY; }
        JSONObject command = new JSONObject();
        try {
            command = intent == null || intent.getStringExtra("command") == null ? new JSONObject() : new JSONObject(intent.getStringExtra("command"));
            String action = command.optString("action", "restore");
            if (!restored) {
                restored = true;
                if (!action.equals("load") && !action.equals("stopEngine") && !action.equals("stopAll") && app.prefs.getBoolean("desiredRunning", false)) {
                    String selected = app.prefs.getString("selectedModel", "");
                    if (!selected.isEmpty() && app.store.modelFile(selected).isFile()) engine.load(selected);
                }
                if (action.equals("restore")) downloads.resumeInterrupted();
                if (localJobs != null && app.prefs.getBoolean("desiredJobs", false) && !action.equals("stopAll")) localJobs.wake();
            }
            if (!action.equals("stopApi") && !action.equals("stopAll") && api.wanted()) api.start();
            switch (action) {
                case "startApi": api.start(); break;
                case "stopApi": api.stop(); break;
                case "declareBundle": { requireBundles(); ModelBundle bundle = new ModelBundle(command.getJSONObject("manifest")); app.bundles.declare(bundle); command.put("result", app.bundles.plan(bundle.id)); break; }
                case "submitTask": requireJobs(); api.start(); command.put("result", localJobs.submit(command.getJSONObject("request"), command.optString("idempotencyKey"))); break;
                case "cancelTask": requireJobs(); localJobs.cancel(command.getString("id")); break;
                case "deleteTask": requireJobs(); app.jobs.remove(command.getString("id")); break;
                case "deleteArtifact": requireJobs(); app.artifacts.remove(command.getString("id")); break;
                case "retryTask": { requireJobs(); api.start(); JSONObject old = app.jobs.get(command.getString("id")); if (!old.getString("state").equals("failed") && !old.getString("state").equals("interrupted") && !old.getString("state").equals("cancelled")) throw new IllegalStateException("仅已失败、中断或取消的任务可以重试"); command.put("result", localJobs.retry(old.getString("id"), "")); break; }
                case "downloadBundle": case "resumeBundle": requireBundles(); bundleTransfers.download(command.getString("id")); break;
                case "importBundle": {
                    requireBundles(); String id = command.getString("id"); JSONObject uris = command.getJSONObject("uris");
                    java.util.Map<String, BundleTransfers.Input> files = new java.util.HashMap<>();
                    for (ModelBundle.Component component : app.bundles.bundle(id).components) {
                        if (!uris.has(component.role)) { if (!app.bundles.hasObject(component)) throw new IllegalArgumentException("导入缺少组件；不会转为网络下载：" + component.role); continue; }
                        android.net.Uri uri = android.net.Uri.parse(uris.getString(component.role));
                        if (!"content".equals(uri.getScheme())) throw new IllegalArgumentException("请从系统文件选择器导入模型组件");
                        files.put(component.role, () -> getContentResolver().openInputStream(uri));
                    }
                    bundleTransfers.importFiles(id, files); break;
                }
                case "pauseBundle": requireBundles(); bundleTransfers.pause(command.getString("id")); break;
                case "deleteBundle": {
                    requireBundles(); String id = command.getString("id");
                    if (bundleTransfers.busy(id)) throw new IllegalStateException("请先暂停下载，等待传输结束后删除模型包");
                    app.bundles.remove(id, command.optBoolean("removeSettings", false)); break;
                }
                case "saveBundleSettings": requireBundles(); app.bundles.saveSettings(command.getString("id"), command.getJSONObject("settings")); break;
                case "download": downloads.enqueue(command.getString("id"), ""); break;
                case "pauseDownload": downloads.pause(command.getString("id")); break;
                case "resumeDownload": {
                    String id = command.getString("id"); downloads.enqueue(id, app.store.download(id).optString("uri")); break;
                }
                case "load": if (jobsBusy()) throw new IllegalStateException("请先完成或取消本地生成任务，再加载文本模型"); api.start(); engine.load(command.getString("id")); break;
                case "stopEngine": chat.cancel(); api.cancelText(); engine.stop(); break;
                case "stopAll": app.finishCommand(command, null); stopAll(); return START_NOT_STICKY;
                case "send": chat.send(command.getString("text")); break;
                case "cancelChat": chat.cancel(); api.cancelText(); break;
                case "deleteModel": {
                    String id = command.getString("id");
                    if (downloads.busy(id)) throw new IllegalStateException("请先暂停下载，再删除模型");
                    app.store.remove(id); break;
                }
                case "addModel": {
                    String id = app.store.addCustom(command.getString("name"), command.getString("url"), command.optString("sha256"), false);
                    downloads.enqueue(id, ""); break;
                }
                case "addHubModel": {
                    String id = app.store.addHub(command.getJSONObject("model"));
                    if (!app.store.modelFile(id).isFile()) downloads.enqueue(id, "");
                    break;
                }
                case "import": {
                    String id = app.store.addCustom(command.getString("name"), "", "", true);
                    downloads.enqueue(id, command.getString("uri")); break;
                }
                case "saveSettings": saveSettings(command.getJSONObject("settings")); break;
                case "saveModelSettings": saveModelSettings(command.getString("id"), command.getJSONObject("settings")); break;
                case "restore": break;
                default: throw new IllegalArgumentException("未知操作");
            }
            app.finishCommand(command, null);
        } catch (Exception error) { app.finishCommand(command, error); }
        activityChanged(); return START_STICKY;
    }
    public void modelInstalled(String id) {
        main.post(() -> {
            if (stopping) return;
            if (app.prefs.getBoolean("autoLoad", true) && !engine.wanted() && app.prefs.getString("selectedModel", "").isEmpty()) {
                try { api.start(); engine.load(id); } catch (Exception error) { app.error(error.getMessage()); }
            }
        });
    }
    public void activityChanged() {
        main.post(() -> {
            if (stopping) return;
            main.removeCallbacks(idleStop); updateNotification(); app.emit();
            if (!engine.wanted() && !transfersBusy() && !jobsBusy() && !apiBusy() && !app.generating) main.postDelayed(idleStop, 1800);
        });
    }
    public void updateNotification() {
        main.post(() -> {
            if (stopping || System.currentTimeMillis() - lastNotification < 900) return;
            lastNotification = System.currentTimeMillis();
            String text = app.engineDetail;
            if (downloads != null && downloads.busy()) {
                String id = downloads.activeId();
                if (!id.isEmpty()) {
                    JSONObject state = app.store.download(id); long total = state.optLong("total"), bytes = state.optLong("received");
                    text = state.optString("state").equals("verifying") ? "正在校验模型文件" : "正在下载模型" + (total > 0 ? " · " + Math.min(100, bytes * 100 / total) + "%" : "");
                } else text = "模型下载排队中";
                if (engine != null && engine.ready()) text += " · API 运行中";
            } else if (bundleTransfers != null && bundleTransfers.busy()) text = "正在下载或校验模型组件 · 后台继续运行";
            else if (jobsBusy()) text = "正在执行本地生成任务 · 退出页面后继续";
            else if (app.generating || app.textRequestBusy) text = "正在本地生成回复 · 后台继续运行";
            if (!jobsBusy() && !transfersBusy() && !app.generating && !app.textRequestBusy && apiBusy() && !engine.wanted()) text = "模型接口运行中 · 可提交本机任务";
            getSystemService(NotificationManager.class).notify(NOTIFICATION, notification(text));
        });
    }
    private Notification notification(String text) {
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, LmaService.class).setAction("STOP_ALL"), PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL).setSmallIcon(R.drawable.ic_notification).setContentTitle("LMA · 本地模型工作台")
                .setContentText(text).setContentIntent(open).setOngoing(true).setOnlyAlertOnce(true)
                .addAction(new Notification.Action.Builder(null, "停止服务", stop).build()).build();
    }
    private void saveModelSettings(String id, JSONObject changes) throws Exception {
        JSONObject current = app.store.inspectModel(id).getJSONObject("values"), next = app.store.previewConfig(id, changes);
        boolean reload = id.equals(app.engineModel) && engine.wanted() && ModelSettings.reload(current, next);
        if (reload && (app.generating || app.textRequestBusy)) throw new IllegalStateException("请先停止当前回复，再修改此模型的加载参数");
        app.store.saveConfig(id, next);
        if (reload) { engine.stop(); engine.load(id); }
        app.emit();
    }
    private void saveSettings(JSONObject value) throws Exception {
        for (String key : ModelSettings.KEYS) if (value.has(key)) throw new IllegalArgumentException("模型参数已移至本地模型的独立设置");
        int port = value.optInt("port", app.prefs.getInt("port", 8080));
        String source = value.optString("source", app.prefs.getString("source", "auto"));
        String theme = value.optString("theme", app.prefs.getString("theme", "system"));
        boolean lan = value.optBoolean("lan", app.prefs.getBoolean("lan", false));
        if (port < 1024 || port > 65535) throw new IllegalArgumentException("服务端口需要 1024–65535");
        if (!source.equals("auto") && !source.equals("huggingface") && !source.equals("mirror")) throw new IllegalArgumentException("未知下载源");
        if (!theme.equals("system") && !theme.equals("light") && !theme.equals("dark")) throw new IllegalArgumentException("未知主题");
        boolean reload = port != app.prefs.getInt("port", 8080) || lan != app.prefs.getBoolean("lan", false);
        if (reload && (app.generating || app.textRequestBusy)) throw new IllegalStateException("请先停止生成，再修改服务监听参数");
        if (reload && api.ready()) api.configure(port, lan);
        SharedPreferences.Editor edit = app.prefs.edit().putInt("port", port).putString("source", source).putString("theme", theme).putBoolean("lan", lan);
        if (value.has("boot")) edit.putBoolean("boot", value.getBoolean("boot"));
        if (value.has("autoLoad")) edit.putBoolean("autoLoad", value.getBoolean("autoLoad"));
        edit.apply();
        // The public listener changes independently; the native engine always stays on private loopback.
        app.emit();
    }
    private void stopAll() {
        stopping = true; main.removeCallbacks(idleStop); app.prefs.edit().putBoolean("desiredRunning", false).apply();
        app.prefs.edit().putBoolean("desiredJobs", false).apply();
        if (localJobs != null) try { localJobs.cancelAll(); } catch (Exception error) { app.log("任务停止记录失败：" + error.getMessage()); }
        api.stop(); chat.cancel(); downloads.pauseAll(); if (bundleTransfers != null) bundleTransfers.close(); engine.stop(); stopSelf();
    }
    @Override public void onDestroy() {
        stopping = true; main.removeCallbacksAndMessages(null);
        if (api != null) { api.close(); if (app.apiHost == api) app.apiHost = null; }
        if (localJobs != null) { localJobs.close(); if (app.jobHost == localJobs) app.jobHost = null; }
        if (chat != null) chat.close(); if (downloads != null) downloads.close(); if (bundleTransfers != null) bundleTransfers.close(); if (engine != null) engine.close();
        if (cpu != null && cpu.isHeld()) cpu.release(); if (wifi != null && wifi.isHeld()) wifi.release();
        if (!app.engineState.equals("error")) app.engineState = "stopped";
        app.engineStarted = 0; app.emit(); stopForeground(STOP_FOREGROUND_REMOVE); super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
    private void requireBundles() { if (bundleTransfers == null) throw new IllegalStateException("模型包存储不可用：" + app.bundleStoreError); }
    private void requireJobs() { if (localJobs == null) throw new IllegalStateException("本地任务基座不可用：" + app.bundleStoreError); }
}
