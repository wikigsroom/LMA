package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import java.lang.reflect.Field;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

/** Test-only, opt-in capture of explicitly marked acceptance requests, never arbitrary chats. */
public final class DeviceM04Diagnostics extends Instrumentation {
    private String marker;
    @Override public void onCreate(Bundle args) {
        super.onCreate(args);
        marker = args.getString("marker", "");
        if (!marker.matches("LMA-M04-[A-Z][0-9]+")) throw new IllegalArgumentException("Owned acceptance marker required");
        start();
    }
    @Override public void onStart() {
        JSONObject result = new JSONObject();
        ArrayList<File> privateFiles = new ArrayList<>();
        try {
            LmaApp app = (LmaApp)getTargetContext().getApplicationContext();
            startActivitySync(new Intent(getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            getTargetContext().startActivity(new Intent().setClassName("app.dsh.mobile", "app.dsh.mobile.MainActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            File stop = new File(app.getExternalFilesDir(null), "lma-m04-diag-stop-" + marker);
            if (stop.exists()) throw new IllegalStateException("Use a fresh acceptance marker");
            File credentials = new File(app.getExternalFilesDir(null), "lma-m04-diag-credentials-" + marker + ".json");
            if (credentials.exists()) throw new IllegalStateException("Remove old owned diagnostic credentials before reuse");
            privateFiles.add(credentials);
            long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.HOURS.toNanos(4);
            Map<Object, Boolean> observed = new IdentityHashMap<>();
            while (System.nanoTime() < deadline && !stop.exists()) {
                JSONObject captured = null;
                ApiHost host = app.apiHost;
                if (host != null) {
                    Field pendingField = ApiHost.class.getDeclaredField("textCalls"); pendingField.setAccessible(true);
                    synchronized (app.requestGate) {
                        Map<?, ?> pending = (Map<?, ?>)pendingField.get(host);
                        for (Object call : pending.values()) {
                            if (observed.containsKey(call)) continue;
                            Field field = call.getClass().getDeclaredField("request"); field.setAccessible(true);
                            JSONObject request = (JSONObject)field.get(call);
                            if (!request.optString("model").equals("m04")) continue;
                            if (request.optJSONArray("tools") == null || request.getJSONArray("tools").length() < 41 || app.nativePort < 1) continue;
                            JSONArray messages = request.optJSONArray("messages");
                            if (messages == null) continue;
                            boolean owned = false;
                            for (int i = 0; i < messages.length(); i++) {
                                JSONObject m = messages.getJSONObject(i);
                                owned |= m.optString("role").equals("user") && m.optString("content").contains(marker);
                            }
                            if (owned) { captured = new JSONObject(request.toString()); observed.put(call, Boolean.TRUE); break; }
                        }
                    }
                }
                if (captured != null) {
                    // No prompts or credentials enter instrumentation/logcat output.
                    // The explicitly authorized host copies these temporary app-owned
                    // files privately before requesting diagnostic shutdown.
                    writePrivate(credentials, new JSONObject().put("apiKey", app.prefs.getString("apiKey", ""))
                        .put("nativeKey", app.nativeApiKey));
                    File snapshot = new File(app.getExternalFilesDir(null), "lma-m04-diag-" + marker + "-" + observed.size() + ".json");
                    if (snapshot.exists()) throw new IllegalStateException("Use a fresh diagnostic snapshot name");
                    privateFiles.add(snapshot);
                    JSONObject observation = new JSONObject().put("request", captured).put("marker", marker)
                        .put("publicPort", app.prefs.getInt("port", 52187)).put("nativePort", app.nativePort)
                        .put("settings", app.settings("m04")).put("status", "captured");
                    writePrivate(snapshot, observation);
                    Bundle event = new Bundle(); event.putString("lma_m04", new JSONObject().put("status", "captured")
                        .put("marker", marker).put("file", snapshot.getName()).put("tools", captured.getJSONArray("tools").length()).toString());
                    sendStatus(Activity.RESULT_OK, event);
                    if (observed.size() >= 32) throw new IllegalStateException("Owned diagnostic request limit reached");
                }
                Thread.sleep(100);
            }
            while (app.textRequestBusy) Thread.sleep(250);
            stop.delete();
            result.put("status", "finished").put("ownedRequests", observed.size());
        } catch (Throwable error) {
            try { result.put("status", "failed").put("error", error.getClass().getSimpleName() + ": " + error.getMessage()); } catch (Exception ignored) { }
        } finally {
            for (File file : privateFiles) file.delete();
        }
        Bundle out = new Bundle(); out.putString("lma_m04", result.toString()); finish(Activity.RESULT_OK, out);
    }
    private static void writePrivate(File file, JSONObject data) throws Exception {
        try (FileOutputStream out = new FileOutputStream(file)) { out.write(data.toString().getBytes(StandardCharsets.UTF_8)); }
    }
}
