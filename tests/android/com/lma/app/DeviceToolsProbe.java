package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.webkit.WebView;
import android.view.View;
import android.view.ViewGroup;
import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Physical WebView runtime controls. Credentials return only to the private host runner in memory. */
public final class DeviceToolsProbe extends Instrumentation {
    private LmaApp app; private WebView web; private String mode, selected;
    private final JSONArray checks = new JSONArray();
    private interface Condition { boolean get() throws Exception; }
    private void until(Condition condition, String description) throws Exception {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(120);
        while (System.nanoTime() < deadline) { if (condition.get()) return; Thread.sleep(100); }
        throw new IOException("Physical runtime check timed out: " + description);
    }
    private WebView find(View v) { if (v instanceof WebView) return (WebView)v; if (v instanceof ViewGroup) { ViewGroup g = (ViewGroup)v; for (int i = 0; i < g.getChildCount(); i++) { WebView w = find(g.getChildAt(i)); if (w != null) return w; } } return null; }
    private Object js(String source) throws Exception {
        CountDownLatch done = new CountDownLatch(1); String[] value = {null};
        runOnMainSync(() -> web.evaluateJavascript(source, result -> { value[0] = result; done.countDown(); }));
        if (!done.await(10, TimeUnit.SECONDS)) throw new IOException("WebView callback timed out");
        return new JSONTokener(value[0]).nextValue();
    }
    private void check(String name, String condition) throws Exception { if (!Boolean.TRUE.equals(js(condition))) throw new IOException("Physical runtime assertion failed: " + name); checks.put(name); }
    private JSONObject inventory() throws Exception {
        return new JSONObject(String.valueOf(js("(function(){var s=JSON.parse(Android.getSnapshot());return JSON.stringify({models:s.models.filter(function(m){return m.installed}).map(function(m){return {id:m.id,bytes:m.installedBytes}}),bundles:s.bundles.filter(function(m){return m.installed}).map(function(m){return {id:m.id,bytes:m.installedBytes}}),sessions:s.chat.sessions.length});})()")));
    }
    private void command(String action, String id) throws Exception {
        String requestId = "physical-tools-" + System.nanoTime(); JSONObject fields = new JSONObject().put("action", action).put("id", id).put("requestId", requestId);
        js("Android.dispatch(" + JSONObject.quote(fields.toString()) + ")");
        until(() -> { JSONArray all = app.snapshot().getJSONArray("commandResults"); for (int i = 0; i < all.length(); i++) { JSONObject r = all.getJSONObject(i); if (requestId.equals(r.optString("requestId"))) { if (!r.getBoolean("ok")) throw new IOException("Runtime command rejected"); return true; } } return false; }, action);
    }
    @Override public void onCreate(Bundle args) { super.onCreate(args); mode = args.getString("mode", "inspect"); selected = args.getString("model", "m15"); start(); }
    @Override public void onStart() {
        JSONObject result = new JSONObject();
        try {
            app = (LmaApp)getTargetContext().getApplicationContext();
            Activity activity = startActivitySync(new Intent(getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            runOnMainSync(() -> web = find(activity.getWindow().getDecorView()));
            until(() -> web != null && Boolean.TRUE.equals(js("Boolean(window.LMA&&window.Android)")), "native page");
            JSONObject before = inventory();
            if (mode.equals("load")) { command("load", selected); until(() -> app.engineState.equals("ready"), "resident load"); checks.put("Explicitly selected installed model loads without download"); }
            else if (mode.equals("unload")) {
                until(() -> app.engineState.equals("ready") && app.engineModel.equals(selected), "ready resident before UI unload");
                if (!app.engineState.equals("ready") || !app.engineModel.equals(selected)) throw new IOException("Select a ready installed test model before unload");
                js("document.querySelector('#runtimeAction').click()");
                check("Global runtime control names the loaded model", "document.querySelector('#modalTitle').textContent==='运行中的模型'&&document.querySelector('#modal [data-action=stopTextModel]').dataset.id===" + JSONObject.quote(selected));
                js("document.querySelector('#modal [data-action=stopTextModel]').click()");
                check("Unload confirmation preserves the target and explains file retention", "document.querySelector('#modal [data-command=stopEngine]').dataset.id===" + JSONObject.quote(selected) + "&&document.querySelector('#modalContent').textContent.includes('已下载文件')");
                js("document.querySelector('#modal .modal-actions [data-action=closeModal]').click()");
                check("Cancelling unload keeps the model ready", "JSON.parse(Android.getSnapshot()).engine.state==='ready'");
                js("document.querySelector('#runtimeAction').click();document.querySelector('#modal [data-action=stopTextModel]').click();document.querySelector('#modal [data-command=stopEngine]').click()");
                until(() -> app.engineState.equals("stopped") && (app.nativeProcess == null || !app.nativeProcess.isAlive()) && !app.textRequestBusy, "native process release");
                checks.put("Confirmed UI unload releases the actual native process and all text requests");
                if (app.apiHost == null || !app.apiHost.ready()) throw new IOException("Unload unexpectedly stopped the API listener");
                checks.put("Public API listener remains available after model unload");
            } else if (mode.equals("startApi")) command("startApi", "");
            else if (!mode.equals("inspect") && !mode.equals("identity") && !mode.equals("trace") && !mode.equals("clipboard")) throw new IOException("Unknown physical runtime mode");
            if (mode.equals("trace")) result.put("toolDiagnostics", app.apiHost == null ? new JSONArray() : app.apiHost.toolDiagnostics());
            if (mode.equals("clipboard")) {
                android.content.ClipboardManager clipboard = (android.content.ClipboardManager)app.getSystemService(android.content.Context.CLIPBOARD_SERVICE);
                // Only used immediately after an explicit DSH "copy URL" action; private host output.
                result.put("copiedUrl", clipboard.hasPrimaryClip() ? clipboard.getPrimaryClip().getItemAt(0).coerceToText(app).toString() : "");
            }
            if (mode.equals("identity")) {
                java.io.File weight = app.store.modelFile(selected);
                result.put("weightIdentity", new JSONObject().put("id", selected).put("bytes", weight.length()).put("sha256", com.lma.app.core.DataFiles.sha256(weight)).put("metadata", GgufMetadata.read(weight)));
            }
            JSONObject after = inventory();
            if (!before.toString().equals(after.toString())) throw new IOException("Runtime operation changed installed assets or chat history");
            checks.put("Installed asset identities, sizes and conversation history are preserved");
            JSONObject snapshot = app.snapshot();
            result.put("status", "passed").put("version", getTargetContext().getPackageManager().getPackageInfo("com.lma.app", 0).versionName).put("versionCode", getTargetContext().getPackageManager().getPackageInfo("com.lma.app", 0).getLongVersionCode()).put("before", before).put("after", after).put("engine", snapshot.getJSONObject("engine")).put("checks", checks)
                .put("apiKey", app.prefs.getString("apiKey", "")).put("port", app.prefs.getInt("port", 52187)).put("settings", app.settings(selected));
        } catch (Throwable error) { try { result.put("status", "failed").put("error", error.getClass().getSimpleName() + ": " + error.getMessage()); } catch (Exception ignored) {} }
        Bundle output = new Bundle(); output.putString("lma_tools", result.toString()); finish(Activity.RESULT_OK, output);
    }
}
