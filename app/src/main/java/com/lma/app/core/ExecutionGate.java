package com.lma.app.core;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.concurrent.*;
import org.json.JSONArray;
import org.json.JSONObject;

/** One fair, cancellable execution slot for signed local engines, chat and HTTP replies. */
public final class ExecutionGate {
    public interface Check { void run() throws Exception; }
    private final Deque<Ticket> waiting = new ArrayDeque<>();
    private Ticket active;
    private long sequence;
    private ResourceWatch.Probe resourceProbe;
    private Runnable resourceChanged;
    private ScheduledExecutorService resourceTimer;
    private long resourceGeneration;
    private JSONObject lastResourceStop;

    /** Service-owned observer. Pending tickets and idle resident models are not executing work. */
    public synchronized void monitorResources(ResourceWatch.Probe probe, Runnable changed) {
        stopResourceMonitor(); resourceProbe = java.util.Objects.requireNonNull(probe); resourceChanged = changed;
        resourceTimer = Executors.newSingleThreadScheduledExecutor(r -> { Thread t = new Thread(r,"LMA-resource-monitor"); t.setDaemon(true); return t; });
        resourceTimer.scheduleWithFixedDelay(this::pollResources, 0, ResourceWatch.INTERVAL_MILLIS, TimeUnit.MILLISECONDS);
    }
    public synchronized void stopResourceMonitor() {
        resourceGeneration++; resourceProbe = null; resourceChanged = null;
        if (resourceTimer != null) { resourceTimer.shutdownNow(); resourceTimer = null; }
    }
    /** Also callable by deterministic host controls; identity is rechecked after the OS probe returns. */
    public void pollResources() {
        Ticket candidate; ResourceWatch.Probe probe; long generation;
        synchronized (this) { candidate = active; probe = resourceProbe; generation = resourceGeneration; if (candidate == null || candidate.deferred || candidate.resources.finished() || probe == null) return; }
        ResourceWatch.Sample sample = null;
        try { sample = probe.sample(); } catch (Exception unavailable) { /* Preserve unknown status without inventing a measurement. */ }
        Process stopped = null; Stop listener = null; Runnable changed = null; String message = "";
        synchronized (this) {
            if (active != candidate || candidate.released || candidate.deferred || candidate.resources.finished() || generation != resourceGeneration) return;
            if (sample == null) candidate.resources.unavailable(); else candidate.resources.observe(sample);
            changed = resourceChanged;
            if (!candidate.stopDelivered && !candidate.resources.failure().isEmpty()) {
                candidate.stopDelivered = true; candidate.stopInFlight = true; stopped = candidate.watched; listener = candidate.stopListener; message = candidate.resources.failure();
                try { lastResourceStop = candidate.json(); } catch (Exception ignored) {} changed = resourceChanged;
            }
        }
        if (!message.isEmpty()) try { stopOwned(stopped, listener, message); }
        finally { synchronized (this) { candidate.stopInFlight = false; if (candidate.releaseRequested) candidate.release(); } }
        if (changed != null) try { changed.run(); } catch (Exception ignored) {}
    }
    public interface Stop { void stopped(String message); }
    private static void stopOwned(Process process, Stop listener, String message) {
        if (listener != null) try { listener.stopped(message); } catch (Exception ignored) {}
        if (process == null) return;
        process.destroy();
        Thread reaper = new Thread(() -> { try { ProcessControl.stop(process); } catch (IOException ignored) {} }, "LMA-resource-stop"); reaper.setDaemon(true); reaper.start();
    }

    public synchronized Ticket enqueue(String kind, String model) throws IOException {
        if (!java.util.Arrays.asList("load", "chat", "api", "job").contains(kind)) throw new IllegalArgumentException("Unknown execution kind");
        if (waiting.size() >= 128) throw new IOException("本机执行队列已满，请稍后重试");
        Ticket ticket = new Ticket(++sequence, kind, model == null ? "" : model);
        waiting.addLast(ticket); notifyAll(); return ticket;
    }
    public synchronized Ticket enqueueIfIdle(String kind, String model) throws IOException {
        return active == null && waiting.isEmpty() ? enqueue(kind, model) : null;
    }
    public synchronized JSONObject snapshot() throws Exception {
        JSONArray pending = new JSONArray();
        for (Ticket ticket : waiting) pending.put(ticket.json());
        return new JSONObject().put("policy", "single_engine_fifo").put("active", active == null ? JSONObject.NULL : active.json())
                .put("waiting", pending).put("waitingCount", pending.length()).put("resourceMonitoringEnabled", resourceProbe != null)
                .put("lastResourceStop", lastResourceStop == null ? JSONObject.NULL : new JSONObject(lastResourceStop.toString()));
    }
    public final class Ticket implements AutoCloseable {
        private final long id, created = System.currentTimeMillis();
        private final String kind, model;
        private boolean released, deferred;
        private final ResourceWatch resources = new ResourceWatch();
        private Process watched;
        private Stop stopListener;
        private boolean stopDelivered, stopInFlight, releaseRequested;
        private Ticket(long id, String kind, String model) { this.id = id; this.kind = kind; this.model = model; }
        private JSONObject json() throws Exception {
            return new JSONObject().put("id", id).put("kind", kind).put("modelId", model).put("createdAt", created)
                    .put("state", deferred ? "reaping" : active == this ? "active" : "waiting").put("runtimeResources", resources.json(resourceProbe != null));
        }
        public void await(Check check) throws Exception {
            try {
                while (true) {
                    check.run();
                    synchronized (ExecutionGate.this) {
                        if (released) throw new IOException("本机执行请求已取消");
                        if (active == this) return;
                        if (active == null && waiting.peekFirst() == this) { waiting.removeFirst(); active = this; resources.start(); return; }
                        ExecutionGate.this.wait(100);
                    }
                }
            } catch (Exception error) { close(); throw error; }
        }
        public void checkOwner() throws IOException {
            synchronized (ExecutionGate.this) { if (released || active != this) throw new IOException("本机执行槽已失效"); if (!resources.failure().isEmpty()) throw new IOException(resources.failure()); }
        }
        public void watchProcess(Process process) throws IOException { watchProcess(process, null); }
        public void watchProcess(Process process, Stop listener) throws IOException {
            String failure; boolean invalid;
            synchronized (ExecutionGate.this) {
                invalid = released || active != this || deferred;
                if (!invalid) { watched = process; stopListener = listener; }
                failure = invalid ? "本机执行槽已失效" : resources.failure();
            }
            if (!failure.isEmpty()) { stopOwned(process, invalid ? null : listener, failure); throw new IOException(failure); }
        }
        public JSONObject runtimeResources() throws Exception { synchronized (ExecutionGate.this) { return resources.json(resourceProbe != null); } }
        public String resourceFailure() { synchronized (ExecutionGate.this) { return resources.failure(); } }
        public void finishResourceMonitoring() throws IOException { synchronized (ExecutionGate.this) { checkOwner(); resources.finish(); } }
        public JSONObject endResourceMonitoring() throws Exception { synchronized (ExecutionGate.this) { resources.finish(); return resources.json(resourceProbe != null); } }
        /** A slow/unreapable child keeps the slot and input leases until actual process exit. */
        public void releaseAfter(Process process, Runnable cleanup) {
            synchronized (ExecutionGate.this) {
                if (released || deferred) throw new IllegalStateException("Execution release already scheduled");
                deferred = true;
            }
            Runnable release = () -> { try { cleanup.run(); } finally { synchronized (ExecutionGate.this) { deferred = false; release(); } } };
            if (process == null || !process.isAlive()) { release.run(); return; }
            Thread reaper = new Thread(() -> {
                boolean interrupted = false;
                while (process.isAlive()) try { process.waitFor(); } catch (InterruptedException error) { interrupted = true; }
                release.run(); if (interrupted) Thread.currentThread().interrupt();
            }, "LMA-execution-reaper"); reaper.setDaemon(true); reaper.start();
        }
        private void release() {
            if (released) return;
            if (stopInFlight) { releaseRequested = true; return; }
            if (!resources.failure().isEmpty() && watched != null && watched.isAlive()) { releaseAfter(watched, () -> {}); return; }
            resources.finish(); released = true; watched = null; stopListener = null; waiting.remove(this); if (active == this) active = null; ExecutionGate.this.notifyAll();
        }
        @Override public void close() { synchronized (ExecutionGate.this) { if (!deferred) release(); } }
    }
}
