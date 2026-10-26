package com.lma.app;

import android.app.Application;
import android.content.Intent;
import android.content.SharedPreferences;
import android.app.ActivityManager;
import android.os.PowerManager;
import android.os.StatFs;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.NetworkInterface;
import java.net.InetAddress;
import java.net.Inet4Address;
import java.security.SecureRandom;
import java.util.Collections;
import com.lma.app.core.Protocol;

public final class LmaApp extends Application {
    public static final String UPDATE = "com.lma.app.STATE_CHANGED";
    public Store store;
    public Chats chats;
    public SharedPreferences prefs;
    private final JSONArray logs = new JSONArray();
    public volatile String lastError = "";
    public volatile String engineState = "stopped";
    public volatile String engineDetail = "选择并下载一个模型，开始本地运行";
    public volatile String engineModel = "";
    public volatile boolean generating = false;
    public volatile long engineStarted = 0;
    public volatile long emittedAt = 0;
    public final Object nativeProcessLock = new Object();
    public volatile Process nativeProcess;
    public volatile JSONObject commandResult = new JSONObject();
    private final JSONArray commandResults = new JSONArray();
    public volatile long errorSequence;

    @Override public void onCreate() {
        super.onCreate();
        prefs = getSharedPreferences("lma", MODE_PRIVATE);
        engineModel = prefs.getString("selectedModel", "");
        if (prefs.getString("apiKey", "").isEmpty()) {
            byte[] random = new byte[24]; new SecureRandom().nextBytes(random);
            prefs.edit().putString("apiKey", "lma_" + Protocol.hex(random)).apply();
        }
        store = new Store(this);
        chats = new Chats(this);
    }

    public void emit() {
        sendBroadcast(new Intent(UPDATE).setPackage(getPackageName()));
    }
    public void error(String message) { lastError = message == null ? "操作失败" : message; errorSequence++; log(lastError); emit(); }
    public synchronized void finishCommand(JSONObject command, Exception error) {
        if (error != null) error(error.getMessage());
        try {
            if (!command.optString("requestId").isEmpty()) {
                commandResult = new JSONObject().put("requestId", command.optString("requestId")).put("action", command.optString("action")).put("ok", error == null).put("error", error == null ? "" : lastError);
                commandResults.put(commandResult); while (commandResults.length() > 24) commandResults.remove(0);
            }
        }
        catch (Exception ignored) {}
        emit();
    }
    public synchronized void log(String message) {
        if (message == null) return;
        String key = prefs.getString("apiKey", "");
        if (!key.isEmpty()) message = message.replace(key, "[hidden]");
        try {
            JSONObject item = new JSONObject(); item.put("time", System.currentTimeMillis()); item.put("text", message.length() > 1200 ? message.substring(0, 1200) : message);
            logs.put(item);
            while (logs.length() > 160) logs.remove(0);
        } catch (Exception ignored) {}
    }
    public JSONObject settings() throws Exception {
        JSONObject value = new JSONObject();
        value.put("lan", prefs.getBoolean("lan", false));
        value.put("port", prefs.getInt("port", 8080));
        value.put("threads", prefs.getInt("threads", 4));
        value.put("context", prefs.getInt("context", 2048));
        value.put("maxTokens", prefs.getInt("maxTokens", 512));
        value.put("temperature", (double) prefs.getFloat("temperature", 0.7f));
        value.put("source", prefs.getString("source", "auto"));
        value.put("boot", prefs.getBoolean("boot", false));
        value.put("autoLoad", prefs.getBoolean("autoLoad", true));
        value.put("theme", prefs.getString("theme", "system"));
        value.put("reasoning", prefs.getString("reasoning", "off"));
        value.put("systemPrompt", prefs.getString("systemPrompt", "你是一个有帮助的本地助手。请优先使用用户的语言，准确、清楚地回答。"));
        value.put("apiKey", prefs.getString("apiKey", ""));
        return value;
    }
    public JSONObject snapshot() {
        JSONObject value = new JSONObject();
        try {
            value.put("app", "LMA"); value.put("version", "0.1.2"); value.put("runtime", "llama.cpp v0.4.1 · CPU");
            value.put("models", store.snapshot()); value.put("settings", settings());
            JSONObject engine = new JSONObject(); engine.put("state", engineState); engine.put("detail", engineDetail);
            engine.put("modelId", engineModel); engine.put("startedAt", engineStarted); engine.put("generating", generating);
            engine.put("localUrl", "http://127.0.0.1:" + prefs.getInt("port", 8080) + "/v1");
            engine.put("addresses", addresses()); value.put("engine", engine);
            ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
            ((ActivityManager) getSystemService(ACTIVITY_SERVICE)).getMemoryInfo(memory);
            JSONObject device = new JSONObject(); device.put("name", android.os.Build.MODEL);
            device.put("android", android.os.Build.VERSION.RELEASE); device.put("totalMemory", memory.totalMem);
            device.put("availableMemory", memory.availMem); device.put("freeStorage", new StatFs(getFilesDir().getPath()).getAvailableBytes());
            device.put("batteryExempt", ((PowerManager) getSystemService(POWER_SERVICE)).isIgnoringBatteryOptimizations(getPackageName()));
            value.put("device", device); value.put("chat", chats.snapshot()); value.put("error", lastError);
            value.put("commandResult", commandResult); value.put("errorSequence", errorSequence);
            synchronized (this) { value.put("logs", new JSONArray(logs.toString())); value.put("commandResults", new JSONArray(commandResults.toString())); }
        } catch (Exception error) { log("状态读取失败：" + error.getMessage()); }
        return value;
    }
    private JSONArray addresses() {
        JSONArray result = new JSONArray();
        try {
            for (NetworkInterface network : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!network.isUp() || network.isLoopback()) continue;
                for (InetAddress address : Collections.list(network.getInetAddresses())) {
                    if (address instanceof Inet4Address && !address.isLoopbackAddress() && address.isSiteLocalAddress())
                        result.put("http://" + address.getHostAddress() + ":" + prefs.getInt("port", 8080) + "/v1");
                }
            }
        } catch (Exception ignored) {}
        return result;
    }
}
