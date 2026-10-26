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
                case "import": {
                    String id = app.store.addCustom(command.getString("name"), "", "", true);
                    downloads.enqueue(id, command.getString("uri")); break;
                }
                case "saveSettings": saveSettings(command.getJSONObject("settings")); break;
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
    private void saveSettings(JSONObject value) throws Exception {
        int port = value.optInt("port", app.prefs.getInt("port", 8080));
        int threads = value.optInt("threads", app.prefs.getInt("threads", 4));
        int context = value.optInt("context", app.prefs.getInt("context", 2048));
        int maxTokens = value.optInt("maxTokens", app.prefs.getInt("maxTokens", 512));
        double temperature = value.optDouble("temperature", app.prefs.getFloat("temperature", 0.7f));
        String source = value.optString("source", app.prefs.getString("source", "auto"));
        String theme = value.optString("theme", app.prefs.getString("theme", "system"));
        String reasoning = value.optString("reasoning", app.prefs.getString("reasoning", "off"));
        String system = value.optString("systemPrompt", app.settings().getString("systemPrompt"));
        boolean lan = value.optBoolean("lan", app.prefs.getBoolean("lan", false));
        if (port < 1024 || port > 65535 || threads < 1 || threads > 12 || context < 512 || context > 8192 || maxTokens < 32 || maxTokens > 4096 || !Double.isFinite(temperature) || temperature < 0 || temperature > 2)
            throw new IllegalArgumentException("参数超出范围，请检查端口、线程和上下文");
        if (!source.equals("auto") && !source.equals("huggingface") && !source.equals("mirror")) throw new IllegalArgumentException("未知下载源");
        if (!theme.equals("system") && !theme.equals("light") && !theme.equals("dark")) throw new IllegalArgumentException("未知主题");
        if (!reasoning.equals("off") && !reasoning.equals("auto") && !reasoning.equals("on")) throw new IllegalArgumentException("未知思考模式");
        if (system.length() > 4000) throw new IllegalArgumentException("系统提示词过长");
        boolean reload = port != app.prefs.getInt("port", 8080) || threads != app.prefs.getInt("threads", 4) || context != app.prefs.getInt("context", 2048) || lan != app.prefs.getBoolean("lan", false) || !reasoning.equals(app.prefs.getString("reasoning", "off"));
        if (reload && app.generating) throw new IllegalStateException("请先停止生成，再修改模型运行参数");
        SharedPreferences.Editor edit = app.prefs.edit().putInt("port", port).putInt("threads", threads).putInt("context", context).putInt("maxTokens", maxTokens).putFloat("temperature", (float) temperature)
                .putString("source", source).putString("theme", theme).putString("reasoning", reasoning).putString("systemPrompt", system).putBoolean("lan", lan);
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
