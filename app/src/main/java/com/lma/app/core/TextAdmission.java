package com.lma.app.core;

import org.json.JSONObject;

/** Bounded admission is separate from the shared one-engine execution lease. */
public final class TextAdmission {
    public static final int MAX_REQUESTS = 9, MAX_BYTES = 16 * 1024 * 1024;
    private int requests, bytes;
    public synchronized Lease acquire(int size) throws LocalHttp.Failure {
        if (size < 0 || requests >= MAX_REQUESTS || size > MAX_BYTES - bytes) throw new LocalHttp.Failure(429, "text_queue_full", "The local text queue or its 16 MiB request budget is full");
        requests++; bytes += size; return new Lease(size);
    }
    public synchronized JSONObject snapshot() throws Exception { return new JSONObject().put("requests", requests).put("requestBytes", bytes).put("maxRequests", MAX_REQUESTS).put("maxRequestBytes", MAX_BYTES).put("parallelDecoding", 1); }
    public final class Lease implements AutoCloseable {
        private final int size; private boolean closed;
        private Lease(int size) { this.size = size; }
        @Override public void close() { synchronized (TextAdmission.this) { if (!closed) { closed = true; requests--; bytes -= size; } } }
    }
}
