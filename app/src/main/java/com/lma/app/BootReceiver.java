package com.lma.app;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action) && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) return;
        LmaApp app = (LmaApp) context.getApplicationContext();
        if (!app.prefs.getBoolean("boot", false)) return;
        boolean jobs = app.prefs.getBoolean("desiredJobs", false), api = app.prefs.getBoolean("desiredApi", false);
        if (!jobs && !api && !app.prefs.getBoolean("desiredRunning", false)) return;
        String id = app.prefs.getString("selectedModel", "");
        if (!jobs && !api && (id.isEmpty() || !app.store.modelFile(id).isFile())) return;
        try { context.startForegroundService(new Intent(context, LmaService.class)); }
        catch (Exception error) { app.log("系统未允许开机恢复，请打开 LMA：" + error.getMessage()); }
    }
}
