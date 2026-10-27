package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.ReentrantLock;

/** Resumable, user-triggered bundle transfers. Never starts work during restoration. */
public final class BundleTransfers implements AutoCloseable {
    public interface Observer { void opened(HttpURLConnection connection) throws IOException; }
    public interface Network { HttpURLConnection open(ModelBundle.Component component, long offset, Observer observer) throws Exception; }
    public interface Listener { void changed(); void installed(String bundleId); void failed(String bundleId, String message); }
    public interface Input { InputStream open() throws Exception; }
    private static final long RESERVE = 64L * 1024 * 1024;
    private final BundleStore store;
    private final Network network;
    private final Listener listener;
    private final ExecutorService executor = Executors.newSingleThreadExecutor(r -> new Thread(r, "LMA-bundle-transfers"));
    private final ConcurrentHashMap<String, Transfer> jobs = new ConcurrentHashMap<>();
    private volatile boolean closed;
    private static final class Transfer {
        final String id, token; final Map<String, Input> imports;
        volatile boolean paused; volatile HttpURLConnection connection;
        Transfer(String id, String token, Map<String, Input> imports) { this.id = id; this.token = token; this.imports = imports; }
    }
    public BundleTransfers(BundleStore store, Network network, Listener listener) { this.store = store; this.network = network; this.listener = listener; }
    public synchronized void download(String id) throws Exception { enqueue(id, Collections.emptyMap()); }
    public synchronized void importFiles(String id, Map<String, Input> files) throws Exception {
        ModelBundle bundle = store.bundle(id);
        for (String role : files.keySet()) bundle.component(role);
        enqueue(id, new HashMap<>(files));
    }
    private void enqueue(String id, Map<String, Input> imports) throws Exception {
        if (closed) throw new IllegalStateException("Bundle transfers are stopping");
        if (jobs.containsKey(id)) return;
        String token = store.request(id); if (token.isEmpty()) return;
        Transfer job = new Transfer(id, token, imports); jobs.put(id, job);
        executor.execute(() -> perform(job)); listener.changed();
    }
    public synchronized void pause(String id) throws Exception {
        Transfer job = jobs.get(id); store.pause(id);
        if (job != null) { job.paused = true; if (job.connection != null) job.connection.disconnect(); }
        listener.changed();
    }
    public boolean busy() { return !jobs.isEmpty(); }
    public boolean busy(String id) { return jobs.containsKey(id); }
    public boolean awaitIdle(long timeout, TimeUnit unit) throws InterruptedException {
        long until = System.nanoTime() + unit.toNanos(timeout);
        while (busy() && System.nanoTime() < until) Thread.sleep(10);
        return !busy();
    }
    private void check(Transfer job) throws IOException { if (closed || job.paused) throw new IOException("Transfer paused"); store.check(job.id, job.token); }
    private void perform(Transfer job) {
        try {
            ModelBundle bundle = store.bundle(job.id); JSONObject plan = store.plan(job.id);
            if (plan.getLong("availableBytes") < plan.getLong("remainingBytes") + RESERVE) throw new IOException("Insufficient storage for complete bundle and reserve");
            for (ModelBundle.Component component : bundle.components) {
                check(job); ReentrantLock lock = store.componentLock(component.sha256);
                while (!lock.tryLock(200, TimeUnit.MILLISECONDS)) check(job);
                try {
                    check(job);
                    if (store.hasObject(component)) continue;
                    File object = store.object(component.sha256);
                    if (object.isFile() && object.length() == component.bytes) {
                        try { store.accept(job.id, job.token, component, object); continue; }
                        catch (IOException error) { check(job); if (!object.delete()) throw new IOException("Cannot replace corrupted component", error); }
                    }
                    File partial = store.partial(component.sha256);
                    Input imported = job.imports.get(component.role);
                    if (imported != null) {
                        try (InputStream in = imported.open()) {
                            if (in == null) throw new IOException("Cannot read imported component");
                            copy(job, component, in, partial, 0);
                        }
                    } else if (partial.length() != component.bytes) download(job, component, partial);
                    check(job); store.progress(job.id, job.token, "verifying", component.role, component.bytes, ""); listener.changed();
                    store.accept(job.id, job.token, component, partial);
                } finally { lock.unlock(); }
            }
            check(job); store.progress(job.id, job.token, "installing", "", 0, ""); store.install(job.id, job.token); listener.installed(job.id);
        } catch (Exception error) {
            if (!closed && !job.paused) {
                try { store.progress(job.id, job.token, "failed", "", 0, error.getMessage() == null ? error.toString() : error.getMessage()); listener.failed(job.id, error.getMessage()); }
                catch (Exception superseded) { /* A newer user operation owns this bundle. */ }
            }
        } finally {
            if (job.connection != null) job.connection.disconnect();
            jobs.remove(job.id, job); listener.changed();
        }
    }
    private void download(Transfer job, ModelBundle.Component component, File partial) throws Exception {
        if (component.url.isEmpty()) throw new IOException("Import the required component: " + component.role);
        long offset = partial.length(); if (offset > component.bytes) { if (!partial.delete()) throw new IOException("Cannot reset oversized partial component"); offset = 0; }
        HttpURLConnection connection = network.open(component, offset, opened -> { job.connection = opened; check(job); });
        job.connection = connection;
        try {
            check(job); int status = connection.getResponseCode();
            if (status == 206) {
                long[] range = Protocol.parseContentRange(connection.getHeaderField("Content-Range"), offset);
                if (range[2] != component.bytes || range[1] != component.bytes - 1) throw new IOException("Component range/size mismatch");
            } else if (status == 200) offset = 0;
            else throw new IOException("Component download returned HTTP " + status);
            long length = connection.getContentLengthLong();
            if (length >= 0 && length != component.bytes - offset) throw new IOException("Component Content-Length mismatch");
            try (InputStream in = connection.getInputStream()) { copy(job, component, in, partial, offset); }
        } finally { connection.disconnect(); job.connection = null; }
    }
    private void copy(Transfer job, ModelBundle.Component c, InputStream in, File partial, long offset) throws Exception {
        store.progress(job.id, job.token, "downloading", c.role, offset, ""); listener.changed();
        try (FileOutputStream out = new FileOutputStream(partial, offset > 0)) {
            long received = offset, last = System.nanoTime(); byte[] buffer = new byte[128 * 1024]; int count;
            while ((count = in.read(buffer)) != -1) {
                check(job);
                if (received > c.bytes - count) { out.getFD().sync(); throw new IOException("Component exceeds pinned size"); }
                if (partial.getParentFile().getUsableSpace() < RESERVE + count) throw new IOException("Storage reserve exhausted");
                out.write(buffer, 0, count); received += count;
                if (System.nanoTime() - last > 500_000_000L) { last = System.nanoTime(); store.progress(job.id, job.token, "downloading", c.role, received, ""); listener.changed(); }
            }
            check(job); out.getFD().sync();
            if (received != c.bytes) throw new IOException("Component download is incomplete; resume to continue");
        }
    }
    @Override public synchronized void close() {
        closed = true;
        for (Transfer job : jobs.values()) { job.paused = true; if (job.connection != null) job.connection.disconnect(); try { store.pause(job.id); } catch (Exception ignored) {} }
        executor.shutdown();
    }
}
