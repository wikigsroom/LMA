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
    private void capture(String name) throws Exception {
        if (!options.getString("media", "").equals("true")) return;
        Thread.sleep(700);
        android.graphics.Bitmap image = getUiAutomation().takeScreenshot();
        require(image != null, "Physical screen capture unavailable");
        File directory = new File(getTargetContext().getExternalFilesDir(null), "acceptance-media");
        require(directory.isDirectory() || directory.mkdirs(), "Cannot create acceptance media directory");
        try (FileOutputStream output = new FileOutputStream(new File(directory, name + ".png"))) {
            require(image.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, output), "Physical screenshot failed");
        } finally { image.recycle(); }
    }
    private void navigation() throws Exception {
        String order = js("JSON.stringify(Array.from(document.querySelectorAll('#page-models .model-card[data-model]')).map(function(x){return x.dataset.model;}))");
        require(new JSONArray(new JSONTokener(order).nextValue().toString()).toString().equals("[\"m08\",\"m06\",\"m01\"]"), "Recommended model order changed: " + order);
        require("true".equals(js("document.querySelectorAll('#modelList .model-card').length===14")), "Expected fourteen optional recommendations");
        pass("Fourteen recommendations preserve m08 / m06 / m01 prefix"); capture("01-recommended");
        for (String task : new String[]{"image", "video", "audio", "3d"}) {
            int expected = task.equals("video") ? 2 : 3;
            js("document.querySelector('[data-task=\"" + task + "\"]').click();document.getElementById('page-models').scrollTop=0");
            waitFor(() -> "true".equals(js("document.querySelectorAll('#modelList [data-recommended-task=\"" + task + "\"]').length===" + expected)), 5000, "recommendation category " + task);
            require("true".equals(js("document.querySelector('[data-task=\"" + task + "\"] .recommendation-count').textContent==='" + expected + "'")), "Recommendation count differs for " + task);
            pass("Physical recommended category: " + task); capture("02-recommended-" + task);
        }
        js("document.querySelector('[data-task=any]').click()");
        js("document.querySelector('[data-filter=all]').click();var s=document.getElementById('catalogueSource');s.value='registered';s.dispatchEvent(new Event('change',{bubbles:true}));");
        waitFor(() -> "true".equals(js("document.querySelectorAll('#page-models .model-card').length>3")), 15000, "all registered model cards");
        pass("All registered models render on physical WebView"); capture("02-all");
        js("document.querySelector('[data-filter=local]').click()");
        waitFor(() -> "true".equals(js("document.querySelector('[data-filter=local]').getAttribute('aria-pressed')==='true'")), 5000, "local models filter");
        pass("Local model management filter responds"); capture("03-local");
        for (String page : new String[]{"chat", "tasks", "server", "settings"}) {
            js("document.querySelector('.bottom-nav [data-tab=" + page + "]').click()");
            waitFor(() -> "true".equals(js("!document.getElementById('page-" + page + "').hidden")), 5000, "navigation " + page);
            pass("Physical navigation: " + page); capture("04-" + page);
        }
        js("document.querySelector('.bottom-nav [data-tab=models]').click();document.querySelector('[data-filter=recommended]').click()");
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
            waitFor(() -> "true".equals(js("Boolean(window.LMA&&window.Android)")), 15000, "offline scripts and native bridge");
            JSONObject initialState = app.snapshot();
            require(initialState.has("engine") && initialState.has("device"), "Native UI state is incomplete");
            require(initialState.getJSONArray("bundles").length() >= 82 && initialState.getJSONObject("device").getLong("totalMemory") > 0, "Full catalogue or physical memory missing from native state");
            pass("Complete catalogue and physical device state");
            waitFor(() -> "true".equals(js("Boolean(document.querySelectorAll('.model-card').length)")), 30000, "offline model catalogue");
            require(app.snapshot().getJSONArray("models").length() >= 14, "Curated models missing"); pass("Installed Android UI and native JavaScript bridge");
            File binary = new File(app.getApplicationInfo().nativeLibraryDir, "libllama-server.so");
            require(binary.isFile() && binary.canExecute(), "Installed native executable unavailable"); pass("Extracted native executable permissions");
            sqlite();
            String system = app.settings().getString("systemPrompt");
            command("saveSettings", new JSONObject().put("settings", new JSONObject().put("source", app.settings().getString("source"))));
            require(system.equals(app.settings().getString("systemPrompt")), "Partial settings update lost the system prompt"); pass("Real foreground service command acknowledgement");
            navigation();
            if (options.getString("programApi", "").equals("true")) {
                command("startApi", new JSONObject());
                require(app.apiHost != null && app.apiHost.ready(), "Foreground API did not start");
                result.put("apiKey", app.prefs.getString("apiKey", "")).put("port", app.prefs.getInt("port", 8080));
                pass("Zero-model foreground API listener starts without downloading weights");
            }
            String selected = options.getString("model", ""); if (!selected.isEmpty()) model(selected, result);
            result.put("status", "passed").put("checks", checks).put("physicalDevice", true).put("backgroundEnduranceTested", false);
            code = Activity.RESULT_OK;
        } catch (Throwable error) {
            try {
                result.put("status", "failed").put("checks", checks).put("error", String.valueOf(error));
                if (app != null) {
                    JSONObject snapshot = app.snapshot();
                    result.put("snapshotKeys", snapshot.names()).put("snapshotModelCount", snapshot.optJSONArray("models") == null ? -1 : snapshot.getJSONArray("models").length());
                    java.lang.reflect.Field field = LmaApp.class.getDeclaredField("logs");
                    field.setAccessible(true);
                    JSONArray tail = new JSONArray();
                    synchronized (app) {
                        JSONArray logs = (JSONArray) field.get(app);
                        for (int i = Math.max(0, logs.length() - 5); i < logs.length(); i++) tail.put(logs.getJSONObject(i).optString("text"));
                    }
                    result.put("nativeLogTail", tail);
                }
                if (web != null) result.put("uiDiagnostics", js("(function(){return {ready:document.readyState,bridge:typeof window.Android,lma:typeof window.LMA,cards:document.querySelectorAll('.model-card').length,runtimeDetail:document.getElementById('runtimeDetail')&&document.getElementById('runtimeDetail').textContent};})()"));
            } catch (Exception diagnosticError) {
                try { result.put("diagnosticError", String.valueOf(diagnosticError)); } catch (JSONException ignored) {}
            }
        } finally {
            output.putString("lma_result", result.toString()); finish(code, output);
        }
    }
}
