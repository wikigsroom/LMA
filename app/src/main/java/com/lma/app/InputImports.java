package com.lma.app;

import android.net.Uri;
import org.json.JSONObject;
import java.io.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Foreground-service-owned copies of explicitly chosen Android documents; never fetches URLs. */
public final class InputImports implements AutoCloseable {
    private final LmaApp app;
    private final Runnable changed;
    private final ThreadPoolExecutor worker = new ThreadPoolExecutor(1, 1, 30, TimeUnit.SECONDS, new ArrayBlockingQueue<>(4), r -> new Thread(r, "LMA-input-import"));
    private final AtomicInteger pending = new AtomicInteger();
    private final AtomicLong generation = new AtomicLong();
    private volatile boolean closed;
    private volatile InputStream active;
    private volatile String activeName = "";
    public InputImports(LmaApp app, Runnable changed) { this.app = app; this.changed = changed; }
    public boolean busy() { return pending.get() > 0; }
    public JSONObject snapshot() throws Exception { return new JSONObject().put("busy", busy()).put("pending", pending.get()).put("name", activeName); }
    public void add(Uri uri, String name) throws Exception {
        if (closed) throw new IllegalStateException("Input import service is stopping");
        if (!"content".equals(uri.getScheme())) throw new IllegalArgumentException("Choose input media through the Android document picker");
        com.lma.app.core.ArtifactStore.inputName(name); long token = generation.get(); pending.incrementAndGet();
        try {
            worker.execute(() -> {
                try {
                    check(token); activeName = name; changed.run();
                    try (InputStream in = app.getContentResolver().openInputStream(uri)) {
                        active = in; check(token);
                        app.artifacts.importStream(in, name, () -> check(token));
                    }
                } catch (Exception error) { if (!closed && generation.get() == token) app.error("素材导入失败：" + error.getMessage()); }
                finally { active = null; activeName = ""; pending.decrementAndGet(); changed.run(); }
            });
        } catch (RejectedExecutionException error) { pending.decrementAndGet(); throw new IllegalStateException("素材导入队列已满，请等待当前导入完成", error); }
        changed.run();
    }
    private void check(long token) throws IOException { if (closed || token != generation.get() || Thread.currentThread().isInterrupted()) throw new IOException("Local input import was cancelled"); }
    public void cancel() { generation.incrementAndGet(); InputStream stream = active; if (stream != null) try { stream.close(); } catch (IOException ignored) {} }
    @Override public void close() { closed = true; cancel(); worker.shutdown(); }
}
