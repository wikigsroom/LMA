package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import org.json.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.security.MessageDigest;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Runs only when installed and invoked on a physical phone; never a host fixture. */
public final class DeviceAcceptance extends Instrumentation {
    private Bundle options;
    private LmaApp app;
    private WebView web;
    private final JSONArray checks = new JSONArray();
    private interface Condition { boolean value() throws Exception; }
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments); options = arguments == null ? new Bundle() : arguments; start(); }
    private void require(boolean value, String message) { if (!value) throw new AssertionError(message); }
    private void waitFor(Condition condition, long timeout, String label) throws Exception {
        long deadline = System.currentTimeMillis() + timeout;
        while (System.currentTimeMillis() < deadline) { if (condition.value()) return; Thread.sleep(100); }
        throw new IOException("Timed out: " + label);
    }
    private void pass(String value) { checks.put(value); Bundle status = new Bundle(); status.putString("stage", value); sendStatus(1, status); }
    private WebView findWeb(View view) {
        if (view instanceof WebView) return (WebView) view;
        if (view instanceof ViewGroup) { ViewGroup group = (ViewGroup) view; for (int i = 0; i < group.getChildCount(); i++) { WebView found = findWeb(group.getChildAt(i)); if (found != null) return found; } }
        return null;
    }
    private String js(String source) throws Exception {
        CountDownLatch done = new CountDownLatch(1); String[] value = {null};
        runOnMainSync(() -> web.evaluateJavascript(source, result -> { value[0] = result; done.countDown(); }));
        if (!done.await(5, TimeUnit.SECONDS)) throw new IOException("WebView callback timed out");
        return value[0];
    }
    private void command(String action, JSONObject fields) throws Exception {
        String id = "device-" + System.nanoTime(); fields.put("action", action).put("requestId", id);
        js("window.Android.dispatch(" + JSONObject.quote(fields.toString()) + ")");
        waitFor(() -> {
            JSONArray results = app.snapshot().getJSONArray("commandResults");
            for (int i = 0; i < results.length(); i++) { JSONObject r = results.getJSONObject(i); if (id.equals(r.optString("requestId"))) { require(r.getBoolean("ok"), r.optString("error")); return true; } }
            return false;
        }, 30000, action + " acknowledgement");
    }
    private void sqlite() throws Exception {
        require(!app.generating, "Stop an active reply before running acceptance");
        String prior = app.chats.session(), session = app.chats.create("m01");
        try {
            app.chats.append(session, "user", "cancelled turn", "done"); app.chats.append(session, "assistant", "", "stopped");
            app.chats.append(session, "user", "useful turn", "done"); String reply = app.chats.append(session, "assistant", "partial reply", "generating");
            Chats reopened = new Chats(app);
            try {
                JSONArray history = reopened.history(session, 2048);
                require(history.length() == 2 && history.getJSONObject(1).getString("content").equals("partial reply"), "Interrupted turn was not restored from Android SQLite");
                JSONObject snapshot = reopened.snapshot();
                require(snapshot.getJSONArray("messages").getJSONObject(3).getString("status").equals("interrupted"), "In-flight message was not marked interrupted");
            } finally { reopened.close(); }
            app.chats.update(reply, "partial reply", "", "stopped", "", 0, 1);
        } finally { app.chats.removeSession(session); if (prior.isEmpty()) app.prefs.edit().remove("session").apply(); else app.chats.select(prior); }
        pass("Android SQLite persistence and interrupted chat history");
    }
    private void model(String id, JSONObject result) throws Exception {
        JSONObject model = app.store.model(id); long started = System.currentTimeMillis();
        if (!app.store.modelFile(id).isFile()) {
            command("download", new JSONObject().put("id", id));
            waitFor(() -> {
                JSONObject d = app.store.download(id);
                if (d.optString("state").equals("error")) throw new IOException(d.optString("error"));
                return app.store.modelFile(id).isFile();
            }, 2100000, "real model download");
        }
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new FileInputStream(app.store.modelFile(id))) { byte[] b = new byte[1024 * 1024]; int n; while ((n = in.read(b)) != -1) digest.update(b, 0, n); }
        String actual = com.lma.app.core.Protocol.hex(digest.digest());
        require(actual.equals(model.getString("sha256")), "Installed model SHA256 differs from the pinned catalogue");
        result.put("model", id).put("modelSha256", actual).put("downloadOrVerifyMs", System.currentTimeMillis() - started);
        pass("Real model file matches pinned publisher SHA256");
        command("load", new JSONObject().put("id", id));
        waitFor(() -> { if (app.engineState.equals("error")) throw new IOException(app.engineDetail); return app.engineState.equals("ready"); }, 310000, "native ARM model loading");
        HttpURLConnection api = Net.local(app, "/v1/models");
        try { require(api.getResponseCode() == 200 && Store.read(api.getInputStream(), 65536).contains("\"" + id + "\""), "Native API model alias missing"); }
        finally { api.disconnect(); }
        pass("Actual ARM native server health and authenticated model alias");
        command("newChat", new JSONObject()); command("send", new JSONObject().put("text", "请用中文介绍如何在手机上运行本地语言模型。"));
        waitFor(() -> !app.generating, 300000, "real model reply");
        JSONArray messages = app.chats.snapshot().getJSONArray("messages"); JSONObject reply = messages.getJSONObject(messages.length() - 1);
        require(reply.optString("status").equals("done") && !reply.optString("content").trim().isEmpty(), "Real model did not produce a completed textual reply: " + reply.optString("error"));
        result.put("replyTokens", reply.optInt("tokens")).put("replyElapsedMs", reply.optLong("elapsed"));
        pass("Actual model reply persisted through production ChatRunner");
        // Secret exists only in the trusted host runner's captured output/memory.
        result.put("apiKey", app.prefs.getString("apiKey", "")).put("port", app.prefs.getInt("port", 8080));
    }
    @Override public void onStart() {
        JSONObject result = new JSONObject(); Bundle output = new Bundle(); int code = Activity.RESULT_CANCELED;
        try {
            app = (LmaApp) getTargetContext().getApplicationContext();
            Activity activity = startActivitySync(new Intent(getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            runOnMainSync(() -> web = findWeb(activity.getWindow().getDecorView()));
            require(web != null, "Main Activity has no WebView");
            waitFor(() -> "true".equals(js("Boolean(window.LMA&&window.Android&&document.querySelectorAll('.model-card').length)")), 30000, "offline UI and native bridge");
            require(app.snapshot().getJSONArray("models").length() >= 14, "Curated models missing"); pass("Installed Android UI and native JavaScript bridge");
            File binary = new File(app.getApplicationInfo().nativeLibraryDir, "libllama-server.so");
            require(binary.isFile() && binary.canExecute(), "Installed native executable unavailable"); pass("Extracted native executable permissions");
            sqlite();
            String system = app.settings().getString("systemPrompt");
            command("saveSettings", new JSONObject().put("settings", new JSONObject().put("source", app.settings().getString("source"))));
            require(system.equals(app.settings().getString("systemPrompt")), "Partial settings update lost the system prompt"); pass("Real foreground service command acknowledgement");
            String selected = options.getString("model", ""); if (!selected.isEmpty()) model(selected, result);
            result.put("status", "passed").put("checks", checks).put("physicalDevice", true).put("backgroundEnduranceTested", false);
            code = Activity.RESULT_OK;
        } catch (Throwable error) {
            try { result.put("status", "failed").put("checks", checks).put("error", String.valueOf(error)); } catch (JSONException ignored) {}
        } finally {
            output.putString("lma_result", result.toString()); finish(code, output);
        }
    }
}
