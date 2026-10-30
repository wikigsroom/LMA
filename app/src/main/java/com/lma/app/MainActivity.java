package com.lma.app;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.OpenableColumns;
import android.provider.Settings;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.ByteArrayInputStream;
import com.lma.app.core.ArtifactStore;
import com.lma.app.core.ByteRange;
import java.nio.charset.StandardCharsets;

public final class MainActivity extends Activity {
    private static final String ORIGIN = "https://appassets.androidplatform.net";
    private static final int IMPORT = 7, EXPORT_LOGS = 8, IMPORT_BUNDLE = 9, EXPORT_ARTIFACT = 10, IMPORT_BUNDLE_FOLDER = 11, IMPORT_INPUT = 12;
    private String exportArtifactId = "", folderBundleId = "";
    private boolean exportMetadata;
    private WebView web;
    private LmaApp app;
    private final Handler main = new Handler(Looper.getMainLooper());
    private boolean registered, loaded;
    private Object backCallback;
    private final Runnable render = () -> { if (loaded && web != null) web.evaluateJavascript("window.LMA&&window.LMA.receive(" + JSONObject.quote(app.snapshot().toString()) + ")", null); };
    private final BroadcastReceiver receiver = new BroadcastReceiver() { @Override public void onReceive(Context context, Intent intent) { scheduleRender(); } };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved); app = (LmaApp) getApplication();
        if (saved != null) { exportArtifactId = saved.getString("exportArtifactId", ""); folderBundleId = saved.getString("folderBundleId", ""); exportMetadata = saved.getBoolean("exportMetadata", false); }
        if (Build.VERSION.SDK_INT >= 33) {
            backCallback = Api33Back.register(this, this::handleBack);
        }
        getWindow().setStatusBarColor(Color.rgb(245, 247, 250)); getWindow().setNavigationBarColor(Color.rgb(245, 247, 250));
        FrameLayout root = new FrameLayout(this);
        web = new WebView(this); web.setBackgroundColor(Color.rgb(245, 247, 250));
        web.getSettings().setJavaScriptEnabled(true); web.getSettings().setDomStorageEnabled(false);
        web.getSettings().setAllowFileAccess(false); web.getSettings().setAllowContentAccess(false);
        web.getSettings().setJavaScriptCanOpenWindowsAutomatically(false); web.getSettings().setSupportMultipleWindows(false);
        web.getSettings().setTextZoom(Math.round(getResources().getConfiguration().fontScale * 100));
        web.addJavascriptInterface(new Bridge(), "Android");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) { return !trusted(request.getUrl()); }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!trusted(uri)) return response(403, "Forbidden");
                String path = uri.getPath();
                if (path != null && path.startsWith("/artifacts/")) return artifactResponse(request, path.substring(11));
                if (path != null && path.startsWith("/audio-streams/")) return audioResponse(request, path.substring(15));
                if (path == null || !path.startsWith("/assets/") || path.contains("..")) return response(404, "Not found");
                String asset = path.substring(8);
                try {
                    String mime = asset.endsWith(".js") ? "application/javascript" : asset.endsWith(".css") ? "text/css" : asset.endsWith(".svg") ? "image/svg+xml" : asset.endsWith(".json") ? "application/json" : "text/html";
                    return new WebResourceResponse(mime, "UTF-8", 200, "OK", java.util.Collections.singletonMap("Cache-Control", "no-cache"), getAssets().open(asset));
                } catch (Exception error) { return response(404, "Not found"); }
            }
            @Override public void onPageFinished(WebView view, String url) { loaded = true; scheduleRender(); }
        });
        root.addView(web, new FrameLayout.LayoutParams(-1, -1)); setContentView(root);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            root.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.displayCutout());
                android.graphics.Insets keyboard = insets.getInsets(android.view.WindowInsets.Type.ime());
                view.setPadding(bars.left, bars.top, bars.right, Math.max(bars.bottom, keyboard.bottom)); return insets;
            });
        }
        web.loadUrl(ORIGIN + "/assets/index.html");
        if (app.prefs.getBoolean("desiredRunning", false) || app.prefs.getBoolean("desiredJobs", false) || app.prefs.getBoolean("desiredApi", false)) service(new JSONObject());
    }
    @Override public void onSaveInstanceState(Bundle saved) {
        saved.putString("exportArtifactId", exportArtifactId); saved.putString("folderBundleId", folderBundleId); saved.putBoolean("exportMetadata", exportMetadata); super.onSaveInstanceState(saved);
    }
    private WebResourceResponse artifactResponse(WebResourceRequest request, String id) {
        try {
            if (app.artifacts == null || !request.getMethod().equals("GET") && !request.getMethod().equals("HEAD")) return response(405, "Method not allowed");
            JSONObject artifact = app.artifacts.get(id); long size = artifact.getLong("bytes"); String header = null;
            for (java.util.Map.Entry<String, String> entry : request.getRequestHeaders().entrySet()) if (entry.getKey().equalsIgnoreCase("Range")) header = entry.getValue();
            ByteRange range;
            try { range = ByteRange.parse(header, size); }
            catch (java.io.IOException invalid) { return new WebResourceResponse("text/plain", "UTF-8", 416, "Range Not Satisfiable", java.util.Collections.singletonMap("Content-Range", "bytes */" + size), new ByteArrayInputStream(new byte[0])); }
            java.util.Map<String, String> headers = new java.util.HashMap<>(); headers.put("Cache-Control", "no-store"); headers.put("Accept-Ranges", "bytes"); headers.put("Content-Length", String.valueOf(range.length)); headers.put("X-Content-Type-Options", "nosniff");
            if (range.partial) headers.put("Content-Range", range.contentRange(size));
            java.io.InputStream stream = request.getMethod().equals("HEAD") ? new ByteArrayInputStream(new byte[0]) : app.artifacts.open(id, range);
            return new WebResourceResponse(artifact.getJSONObject("metadata").getString("mime"), null, range.partial ? 206 : 200, range.partial ? "Partial Content" : "OK", headers, stream);
        } catch (Exception error) { return response(404, "Result unavailable"); }
    }
    private boolean trusted(Uri uri) { return "https".equals(uri.getScheme()) && "appassets.androidplatform.net".equals(uri.getHost()); }
    private WebResourceResponse audioResponse(WebResourceRequest request, String path) {
        try {
            if (!request.getMethod().equals("GET") || app.audioStreams == null) return response(405, "Method not allowed");
            String[] parts = path.split("/", -1); if (parts.length < 1 || parts.length > 2) return response(404, "Not found");
            app.jobs.get(parts[0]); byte[] bytes; String mime;
            if (parts.length == 1) { String after = request.getUrl().getQueryParameter("after"); if (after != null && !after.matches("[0-9]{1,4}")) return response(400, "Invalid cursor"); bytes = app.audioStreams.get(parts[0], after == null ? 0 : Integer.parseInt(after)).toString().getBytes(StandardCharsets.UTF_8); mime = "application/json"; }
            else { if (!parts[1].matches("[0-9]{1,4}")) return response(404, "Not found"); bytes = app.audioStreams.read(parts[0], Integer.parseInt(parts[1])); mime = "application/octet-stream"; }
            java.util.Map<String,String> headers = new java.util.HashMap<>(); headers.put("Cache-Control", "no-store"); headers.put("X-Content-Type-Options", "nosniff"); headers.put("Content-Length", String.valueOf(bytes.length));
            return new WebResourceResponse(mime, null, 200, "OK", headers, new ByteArrayInputStream(bytes));
        } catch (Exception error) { return response(404, "Audio preview expired or not started"); }
    }
    private WebResourceResponse response(int status, String message) { return new WebResourceResponse("text/plain", "UTF-8", status, message, null, new ByteArrayInputStream(message.getBytes(StandardCharsets.UTF_8))); }
    private void scheduleRender() { main.removeCallbacks(render); main.postDelayed(render, 60); }
    @Override public void onStart() {
        super.onStart(); IntentFilter filter = new IntentFilter(LmaApp.UPDATE);
        if (Build.VERSION.SDK_INT >= 33) registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED); else registerLegacyReceiver(filter);
        registered = true;
    }
    // Only used on API 28-32, before RECEIVER_NOT_EXPORTED was added.
    @android.annotation.SuppressLint("UnspecifiedRegisterReceiverFlag")
    private void registerLegacyReceiver(IntentFilter filter) { registerReceiver(receiver, filter); }
    @Override public void onResume() { super.onResume(); if (web != null) web.onResume(); scheduleRender(); }
    @Override public void onPause() { if (web != null) web.onPause(); super.onPause(); }
    @Override public void onStop() { if (registered) { unregisterReceiver(receiver); registered = false; } main.removeCallbacks(render); super.onStop(); }
    @Override public void onDestroy() { main.removeCallbacksAndMessages(null); if (Build.VERSION.SDK_INT >= 33 && backCallback != null) Api33Back.unregister(this, backCallback); if (web != null) { web.removeJavascriptInterface("Android"); web.destroy(); web = null; } super.onDestroy(); }
    @Override public void onBackPressed() { handleBack(); }
    private void handleBack() { if (web != null) web.evaluateJavascript("window.LMA?window.LMA.back():false", handled -> { if (!"true".equals(handled)) moveTaskToBack(true); }); }
    // Isolate API 33 class references from the Android 9 Activity's field types.
    @android.annotation.TargetApi(33)
    private static final class Api33Back {
        static Object register(Activity activity, Runnable handler) {
            android.window.OnBackInvokedCallback callback = handler::run;
            activity.getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT, callback); return callback;
        }
        static void unregister(Activity activity, Object callback) { activity.getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback((android.window.OnBackInvokedCallback) callback); }
    }
    private void service(JSONObject command) {
        main.post(() -> {
            try {
                if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED && !app.prefs.getBoolean("notificationAsked", false)) {
                    app.prefs.edit().putBoolean("notificationAsked", true).apply();
                    requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 33);
                }
                startForegroundService(new Intent(this, LmaService.class).putExtra("command", command.toString()));
            } catch (Exception error) { app.finishCommand(command, new IllegalStateException("无法启动后台服务：" + error.getMessage(), error)); }
        });
    }
    public final class Bridge {
        @JavascriptInterface public void theme(boolean dark) {
            main.post(() -> {
                int color = dark ? Color.rgb(18, 26, 41) : Color.rgb(245, 247, 250);
                getWindow().setStatusBarColor(color); getWindow().setNavigationBarColor(color);
                int flags = getWindow().getDecorView().getSystemUiVisibility();
                int light = android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                getWindow().getDecorView().setSystemUiVisibility(dark ? flags & ~light : flags | light);
                if (web != null) web.setBackgroundColor(color);
            });
        }
        @JavascriptInterface public String getSnapshot() { return app.snapshot().toString(); }
        @JavascriptInterface public void dispatch(String raw) {
            JSONObject command = new JSONObject();
            try {
                if (raw.length() > 70000) throw new IllegalArgumentException("操作数据过长");
                command = new JSONObject(raw); String action = command.getString("action");
                switch (action) {
                    case "inspectModel": app.store.inspectModel(command.getString("id")); app.emit(); break;
                    case "saveTaskDraft": if (app.taskDrafts == null) throw new IllegalStateException("草稿存储不可用"); command.put("result", app.taskDrafts.save(command.getJSONObject("request"), com.lma.app.core.TaskDrafts.revision(command))); app.emit(); break;
                    case "deleteTaskDraft": if (app.taskDrafts == null) throw new IllegalStateException("草稿存储不可用"); app.taskDrafts.remove(command.getString("id"), com.lma.app.core.TaskDrafts.revision(command)); app.emit(); break;
                    case "inspectTaskDraft": if (app.taskDrafts == null) throw new IllegalStateException("草稿存储不可用"); command.put("result", app.taskDrafts.get(command.getString("id"))); break;
                    case "editTask": if (app.jobs == null) throw new IllegalStateException(app.bundleStoreError); command.put("result", com.lma.app.core.TaskRequests.editable(app.jobs.get(command.getString("id")).getJSONObject("request"))); break;
                    case "editArtifact": if (app.artifacts == null) throw new IllegalStateException(app.bundleStoreError); command.put("result", com.lma.app.core.TaskRequests.fromArtifact(app.artifacts.get(command.getString("id")))); break;
                    case "preflightTask": command.put("result", LocalJobs.preflight(app, command.getJSONObject("request"))); break;
                    case "planTaskHistory": if (app.jobs == null) throw new IllegalStateException(app.bundleStoreError); command.put("result", app.jobs.historyPlan()); break;
                    case "clearTaskHistory": if (app.jobs == null) throw new IllegalStateException(app.bundleStoreError); command.put("result", app.jobs.clearHistory(command.getJSONObject("selection"))); app.emit(); break;
                    case "inspectTask": if (app.jobs == null) throw new IllegalStateException(app.bundleStoreError); command.put("result", app.jobs.get(command.getString("id"))); break;
                    case "inspectArtifact": if (app.artifacts == null) throw new IllegalStateException(app.bundleStoreError); command.put("result", app.artifacts.get(command.getString("id"))); break;
                    case "inputPicker": main.post(() -> startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").putExtra(Intent.EXTRA_MIME_TYPES, new String[]{"image/png", "image/jpeg", "audio/wav", "audio/x-wav", "video/mp4"}).addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION), IMPORT_INPUT)); break;
                    case "bundleManifestPicker": main.post(() -> startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION), IMPORT_BUNDLE)); break;
                    case "bundleFolderPicker": {
                        if (app.bundles == null) throw new IllegalStateException(app.bundleStoreError);
                        String id = command.getString("id"); app.bundles.bundle(id);
                        main.post(() -> { folderBundleId = id; startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION), IMPORT_BUNDLE_FOLDER); }); break;
                    }
                    case "exportArtifact": case "exportArtifactMetadata": {
                        if (app.artifacts == null) throw new IllegalStateException(app.bundleStoreError);
                        String id = command.getString("id"); JSONObject artifact = app.artifacts.get(id); boolean metadata = action.equals("exportArtifactMetadata");
                        String name = metadata ? id + ".json" : artifact.getString("filename"), mime = metadata ? "application/json" : artifact.getJSONObject("metadata").getString("mime");
                        main.post(() -> { exportArtifactId = id; exportMetadata = metadata; startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType(mime).putExtra(Intent.EXTRA_TITLE, name), EXPORT_ARTIFACT); }); break;
                    }
                    case "hubRecipeStart": case "hubRecipeTemplate": case "hubRecipeBind": case "hubRecipeDeclare": case "hubRecipeReview": case "hubRecipeApply": case "hubRecipeCancelReview": case "hubSearch": case "hubPage": case "hubFiles": case "hubFilePage": case "hubToken": app.hub.dispatch(command); return;
                    case "hubDownload": command.put("model", app.hub.selected(command)).put("action", "addHubModel"); service(command); return;
                    case "dismissError": app.lastError = ""; app.emit(); break;
                    case "newChat": if (app.generating) throw new IllegalStateException("请先停止当前回复"); app.chats.create(app.engineModel); app.emit(); break;
                    case "selectSession": if (app.generating) throw new IllegalStateException("请先停止当前回复"); app.chats.select(command.getString("id")); break;
                    case "deleteSession": if (app.generating) throw new IllegalStateException("请先停止当前回复"); app.chats.removeSession(command.getString("id")); break;
                    case "importPicker": main.post(() -> startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION), IMPORT)); break;
                    case "battery": main.post(() -> { try { startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + getPackageName()))); } catch (Exception error) { startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)); } }); break;
                    case "exportLogs": main.post(() -> startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("text/plain").putExtra(Intent.EXTRA_TITLE, "LMA-runtime-log.txt"), EXPORT_LOGS)); break;
                    default: service(command); return;
                }
                app.finishCommand(command, null);
            } catch (Exception error) { app.finishCommand(command, error); }
        }
        @JavascriptInterface public void copy(String text) {
            main.post(() -> { ((ClipboardManager) getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("LMA", text)); Toast.makeText(MainActivity.this, "已复制", Toast.LENGTH_SHORT).show(); });
        }
        @JavascriptInterface public void openLink(String value) {
            main.post(() -> { try { Uri uri = Uri.parse(value); if ("https".equals(uri.getScheme())) startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception error) { app.error("无法打开链接"); } });
        }
    }
    @Override public void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (result != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (request == IMPORT_INPUT) {
            if (!"content".equals(uri.getScheme())) { app.error("请从系统文件选择器选择素材"); return; }
            try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); } catch (Exception ignored) {}
            String name = "local-input";
            try (Cursor cursor = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) { if (cursor != null && cursor.moveToFirst()) name = cursor.getString(0); } catch (Exception ignored) {}
            try { service(new JSONObject().put("action", "importInput").put("uri", uri.toString()).put("name", name)); } catch (Exception error) { app.error(error.getMessage()); }
        } else if (request == IMPORT_BUNDLE) {
            new Thread(() -> {
                try (java.io.InputStream in = getContentResolver().openInputStream(uri)) {
                    if (in == null) throw new java.io.IOException("无法读取模型包清单");
                    JSONObject manifest = new JSONObject(Store.read(in, 512 * 1024));
                    new com.lma.app.core.ModelBundle(manifest);
                    service(new JSONObject().put("action", "declareBundle").put("manifest", manifest));
                } catch (Exception error) { app.error("模型包清单无效：" + error.getMessage()); }
            }, "LMA-bundle-manifest").start();
        } else if (request == IMPORT_BUNDLE_FOLDER) {
            String id = folderBundleId; folderBundleId = "";
            try { getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION); } catch (Exception ignored) {}
            new Thread(() -> {
                try {
                    JSONObject uris = BundleDocuments.components(getContentResolver(), uri, app.bundles.bundle(id));
                    service(new JSONObject().put("action", "importBundle").put("id", id).put("uris", uris));
                } catch (Exception error) { app.error("导入未开始：" + error.getMessage()); }
            }, "LMA-bundle-folder").start();
        } else if (request == EXPORT_ARTIFACT) {
            String id = exportArtifactId; boolean metadata = exportMetadata; exportArtifactId = "";
            new Thread(() -> {
                try (java.io.OutputStream out = getContentResolver().openOutputStream(uri)) {
                    if (out == null) throw new java.io.IOException("无法写入导出位置");
                    if (metadata) out.write(app.artifacts.get(id).toString(2).getBytes(StandardCharsets.UTF_8));
                    else try (ArtifactStore.Lease lease = app.artifacts.acquire(id); java.io.InputStream in = new java.io.FileInputStream(lease.file)) {
                        byte[] buffer = new byte[256 * 1024]; int n; while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
                    }
                    main.post(() -> Toast.makeText(this, "生成结果已导出", Toast.LENGTH_SHORT).show());
                } catch (Exception error) { app.error("导出失败：" + error.getMessage()); }
            }, "LMA-artifact-export").start();
        } else if (request == IMPORT) {
            try {
                if ((data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION) != 0)
                    getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } catch (Exception ignored) {}
            try {
                String name = "导入模型";
                try (Cursor cursor = getContentResolver().query(uri, new String[]{OpenableColumns.DISPLAY_NAME}, null, null, null)) { if (cursor != null && cursor.moveToFirst()) name = cursor.getString(0); }
                if (!name.toLowerCase(java.util.Locale.ROOT).endsWith(".gguf")) throw new IllegalArgumentException("请选择 .gguf 模型文件");
                service(new JSONObject().put("action", "import").put("name", name.substring(0, name.length() - 5)).put("uri", uri.toString()));
            } catch (Exception error) { app.error(error.getMessage()); }
        } else if (request == EXPORT_LOGS) {
            new Thread(() -> {
                try (java.io.OutputStream out = getContentResolver().openOutputStream(uri)) {
                    JSONObject log = new JSONObject(); JSONObject state = app.snapshot(); log.put("app", "LMA " + LmaApp.VERSION).put("device", state.optJSONObject("device")).put("engine", state.optJSONObject("engine")).put("logs", state.optJSONArray("logs"));
                    if (out == null) throw new java.io.IOException("无法写入文件"); out.write(log.toString(2).getBytes(StandardCharsets.UTF_8));
                    main.post(() -> Toast.makeText(this, "日志已导出", Toast.LENGTH_SHORT).show());
                } catch (Exception error) { app.error("导出失败：" + error.getMessage()); }
            }, "LMA-log-export").start();
        }
    }
}
