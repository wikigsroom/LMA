package android.os;

/** Explicit host port; validates ownership, not Android Binder/provider behavior. */
public final class CancellationSignal {
    private volatile boolean canceled;
    private Runnable listener;
    public void throwIfCanceled() { if (canceled) throw new IllegalStateException("Canceled"); }
    public boolean isCanceled() { return canceled; }
    public void cancel() {
        Runnable callback;
        synchronized (this) { if (canceled) return; canceled = true; callback = listener; }
        if (callback != null) callback.run();
    }
    public void onCancel(Runnable callback) {
        synchronized (this) { listener = callback; if (!canceled) return; }
        callback.run();
    }
}
