package com.lma.app.core;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/** Bounded shutdown; callers retain process/asset ownership if the OS has not reaped it. */
public final class ProcessControl {
    private ProcessControl() {}
    public static void stop(Process process) throws IOException {
        if (process == null || !process.isAlive()) return;
        boolean interrupted = Thread.interrupted();
        try {
            process.destroy();
            if (!waitFor(process, 3000)) { process.destroyForcibly(); if (!waitFor(process, 3000)) throw new IOException("旧引擎进程尚未退出，执行槽继续保留，请等待系统回收"); }
        } catch (InterruptedException error) {
            interrupted = true; process.destroyForcibly();
            try { if (!waitFor(process, 3000)) throw new IOException("旧引擎进程尚未退出，执行槽继续保留", error); }
            catch (InterruptedException again) { throw new IOException("等待旧引擎退出时再次中断", again); }
        } finally { if (interrupted) Thread.currentThread().interrupt(); }
    }
    private static boolean waitFor(Process process, long millis) throws InterruptedException { return process.waitFor(millis, TimeUnit.MILLISECONDS); }
}
