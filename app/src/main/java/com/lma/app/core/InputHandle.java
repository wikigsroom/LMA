package com.lma.app.core;

import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStream;

/** Owns one opening or readable input at a time; cancellation also covers late opens. */
public final class InputHandle implements AutoCloseable {
    public interface Source {
        InputStream open() throws Exception;
        default void cancel() {}
    }
    private boolean cancelled;
    private Source opening;
    private Tracked active;

    public InputStream open(Source source) throws Exception {
        if (source == null) throw new IllegalArgumentException("Missing local input source");
        synchronized (this) {
            if (cancelled) throw new IOException("Local input was cancelled");
            if (opening != null || active != null) throw new IOException("Another input is still active");
            opening = source;
        }
        InputStream stream = null;
        try {
            stream = source.open();
            if (stream == null) throw new IOException("Cannot read selected input");
            synchronized (this) {
                if (cancelled) throw new IOException("Local input was cancelled");
                active = new Tracked(stream);
                opening = null;
                stream = null; // The tracked stream now owns the returned resource.
                return active;
            }
        } finally {
            synchronized (this) { if (opening == source) opening = null; }
            closeQuietly(stream);
        }
    }

    private final class Tracked extends FilterInputStream {
        private boolean closed;
        Tracked(InputStream stream) { super(stream); }
        @Override public void close() throws IOException {
            synchronized (InputHandle.this) {
                if (closed) return;
                closed = true;
                if (active == this) active = null;
            }
            in.close();
        }
    }
    private static void closeQuietly(InputStream stream) {
        if (stream != null) try { stream.close(); } catch (Exception ignored) {}
    }
    @Override public void close() {
        Source source; InputStream stream;
        synchronized (this) {
            cancelled = true;
            source = opening; opening = null;
            stream = active; active = null;
        }
        // Provider callbacks and close may wait for the reader; never hold our monitor.
        if (source != null) try { source.cancel(); } catch (Exception ignored) {}
        closeQuietly(stream);
    }
}
