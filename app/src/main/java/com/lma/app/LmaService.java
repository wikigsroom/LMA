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

public final class LmaService extends Service {
    private static final String CHANNEL = "lma_runtime";
    private static final int NOTIFICATION = 41;
    public EngineHost engine;
    private ChatRunner chat;
    private Downloads downloads;
    private LmaApp app;
    private final Handler main = new Handler(Looper.getMainLooper());
    private PowerManager.WakeLock cpu;
    private WifiManager.WifiLock wifi;
    private boolean restored, stopping;
    private long lastNotification;
    private final Runnable idleStop = () -> { if (!stopping && engine != null && !engine.wanted() && !downloads.busy() && !app.generating) stopSelf(); };

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
            }
            switch (action) {
                case "download": downloads.enqueue(command.getString("id"), ""); break;
                case "pauseDownload": downloads.pause(command.getString("id")); break;
                case "resumeDownload": {
                    String id = command.getString("id"); downloads.enqueue(id, app.store.download(id).optString("uri")); break;
                }
                case "load": engine.load(command.getString("id")); break;
                case "stopEngine": chat.cancel(); engine.stop(); break;
                case "stopAll": app.finishCommand(command, null); stopAll(); return START_NOT_STICKY;
                case "send": chat.send(command.getString("text")); break;
                case "cancelChat": chat.cancel(); break;
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
                try { engine.load(id); } catch (Exception error) { app.error(error.getMessage()); }
            }
        });
    }
    public void activityChanged() {
        main.post(() -> {
            if (stopping) return;
            main.removeCallbacks(idleStop); updateNotification(); app.emit();
            if (!engine.wanted() && !downloads.busy() && !app.generating) main.postDelayed(idleStop, 1800);
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
            } else if (app.generating) text = "正在本地生成回复 · 后台继续运行";
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
        if (reload && app.generating) throw new IllegalStateException("请先停止当前回复，再修改此模型的加载参数");
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
        if (reload && app.generating) throw new IllegalStateException("请先停止生成，再修改服务监听参数");
        SharedPreferences.Editor edit = app.prefs.edit().putInt("port", port).putString("source", source).putString("theme", theme).putBoolean("lan", lan);
        if (value.has("boot")) edit.putBoolean("boot", value.getBoolean("boot"));
        if (value.has("autoLoad")) edit.putBoolean("autoLoad", value.getBoolean("autoLoad"));
        edit.apply();
        if (reload && engine.wanted()) { String id = app.engineModel; engine.stop(); engine.load(id); }
        app.emit();
    }
    private void stopAll() {
        stopping = true; main.removeCallbacks(idleStop); app.prefs.edit().putBoolean("desiredRunning", false).apply();
        chat.cancel(); downloads.pauseAll(); engine.stop(); stopSelf();
    }
    @Override public void onDestroy() {
        stopping = true; main.removeCallbacksAndMessages(null);
        if (chat != null) chat.close(); if (downloads != null) downloads.close(); if (engine != null) engine.close();
        if (cpu != null && cpu.isHeld()) cpu.release(); if (wifi != null && wifi.isHeld()) wifi.release();
        if (!app.engineState.equals("error")) app.engineState = "stopped";
        app.engineStarted = 0; app.emit(); stopForeground(STOP_FOREGROUND_REMOVE); super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
