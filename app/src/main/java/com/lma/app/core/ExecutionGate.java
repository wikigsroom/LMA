package com.lma.app.core;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.Deque;
import org.json.JSONArray;
import org.json.JSONObject;

/** One fair, cancellable execution slot for signed local engines, chat and HTTP replies. */
public final class ExecutionGate {
    public interface Check { void run() throws Exception; }
    private final Deque<Ticket> waiting = new ArrayDeque<>();
    private Ticket active;
    private long sequence;

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
                .put("waiting", pending).put("waitingCount", pending.length());
    }
    public final class Ticket implements AutoCloseable {
        private final long id, created = System.currentTimeMillis();
        private final String kind, model;
        private boolean released, deferred;
        private Ticket(long id, String kind, String model) { this.id = id; this.kind = kind; this.model = model; }
        private JSONObject json() throws Exception {
            return new JSONObject().put("id", id).put("kind", kind).put("modelId", model).put("createdAt", created)
                    .put("state", deferred ? "reaping" : active == this ? "active" : "waiting");
        }
        public void await(Check check) throws Exception {
            try {
                while (true) {
                    check.run();
                    synchronized (ExecutionGate.this) {
                        if (released) throw new IOException("本机执行请求已取消");
                        if (active == this) return;
                        if (active == null && waiting.peekFirst() == this) { waiting.removeFirst(); active = this; return; }
                        ExecutionGate.this.wait(100);
                    }
                }
            } catch (Exception error) { close(); throw error; }
        }
        public void checkOwner() throws IOException {
            synchronized (ExecutionGate.this) { if (released || active != this) throw new IOException("本机执行槽已失效"); }
        }
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
        private void release() { if (released) return; released = true; waiting.remove(this); if (active == this) active = null; ExecutionGate.this.notifyAll(); }
        @Override public void close() { synchronized (ExecutionGate.this) { if (!deferred) release(); } }
    }
}
