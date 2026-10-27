package com.lma.app;

import java.io.*;
import java.net.URI;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.json.JSONObject;
import android.net.Uri;

/** Test-only framework ports; Store/Downloads/Net/EngineHost/ChatRunner are production files. */
public final class LmaApp {
    public static final String VERSION = "0.3.0-dev.5";
    public String apiState = "stopped", apiDetail = "";
    public com.lma.app.core.BundleStore bundles;
    public com.lma.app.core.JobStore jobs;
    public com.lma.app.core.ArtifactStore artifacts;
    public LocalJobs jobHost;
    public LocalEngines localEngines = new LocalEngines();
    public final Preferences prefs = new Preferences();
    public final Store store;
    public final Chats chats;
    private final File files, assets, libraries;
    public volatile String engineState = "stopped", engineDetail = "", engineModel = "", lastError = "";
    public volatile boolean generating, textRequestBusy;
    public volatile int nativePort;
    public volatile String nativeApiKey = "";
    public final Object requestGate = new Object();
    public volatile long engineStarted;
    public final Object nativeProcessLock = new Object();
    public volatile Process nativeProcess;
    public final List<String> logs = Collections.synchronizedList(new ArrayList<>());
    public final List<JSONObject> commands = Collections.synchronizedList(new ArrayList<>());
    public LmaApp(File files, File assets, File libraries) {
        this.files = files; this.assets = assets; this.libraries = libraries; files.mkdirs();
        prefs.edit().putString("apiKey", "lma_HOST_TEST_KEY").putInt("port", 8080).putInt("threads", 4).putInt("context", 2048)
            .putInt("maxTokens", 512).putFloat("temperature", 0.7f).putString("reasoning", "off").putString("systemPrompt", "Test system prompt").apply();
        store = new Store(this); chats = new Chats(this);
        try { bundles = new com.lma.app.core.BundleStore(new File(files, "bundles")); jobs = new com.lma.app.core.JobStore(new File(files, "jobs")); artifacts = new com.lma.app.core.ArtifactStore(new File(files, "artifacts"), file -> { throw new IOException("No host model outputs"); }); }
        catch (Exception error) { throw new RuntimeException(error); }
    }
    public File getFilesDir() { return files; }
    public Assets getAssets() { return new Assets(); }
    public final class Assets { public InputStream open(String name) throws IOException { return new FileInputStream(new File(assets, name)); } }
    public Info getApplicationInfo() { return new Info(); }
    public final class Info { public final String nativeLibraryDir = libraries.getAbsolutePath(); }
    public Resolver getContentResolver() { return new Resolver(); }
    public static final class Resolver { public InputStream openInputStream(Uri uri) throws Exception { return new FileInputStream(new File(new URI(uri.toString()))); } }
    public void emit() {}
    public void log(String message) { logs.add(message); }
    public void error(String message) { lastError = message; log(message); }
    public void finishCommand(JSONObject command, Exception error) { finishCommand(command, error, true); }
    public void finishCommand(JSONObject command, Exception error, boolean globalError) {
        if (error != null && globalError) error(error.getMessage());
        commands.add(new JSONObject().put("requestId", command.optString("requestId")).put("ok", error == null));
    }
    public JSONObject settings() throws Exception { return settings(engineModel); }
    public JSONObject settings(String modelId) throws Exception {
        JSONObject value = modelId.isEmpty() ? ModelSettings.defaults() : store.config(modelId).getJSONObject("values");
        return value.put("apiKey", prefs.getString("apiKey", "")).put("lan", prefs.getBoolean("lan", false)).put("port", prefs.getInt("port", 8080));
    }
    public static final class Preferences {
        private final Map<String, Object> values = new ConcurrentHashMap<>();
        public String getString(String key, String fallback) { Object v = values.get(key); return v instanceof String ? (String) v : fallback; }
        public boolean getBoolean(String key, boolean fallback) { Object v = values.get(key); return v instanceof Boolean ? (Boolean) v : fallback; }
        public int getInt(String key, int fallback) { Object v = values.get(key); return v instanceof Integer ? (Integer) v : fallback; }
        public float getFloat(String key, float fallback) { Object v = values.get(key); return v instanceof Float ? (Float) v : fallback; }
        public Editor edit() { return new Editor(); }
        public final class Editor {
            private final Map<String, Object> updates = new HashMap<>();
            public Editor putString(String key, String value) { updates.put(key, value); return this; }
            public Editor putBoolean(String key, boolean value) { updates.put(key, value); return this; }
            public Editor putInt(String key, int value) { updates.put(key, value); return this; }
            public Editor putFloat(String key, float value) { updates.put(key, value); return this; }
            public Editor remove(String key) { updates.put(key, null); return this; }
            public void apply() { for (Map.Entry<String, Object> e : updates.entrySet()) { if (e.getValue() == null) values.remove(e.getKey()); else values.put(e.getKey(), e.getValue()); } }
        }
    }
}
