package android.os;
/** Host disk-space adapter only; no Android framework behavior is claimed. */
public final class StatFs {
    private final java.io.File path;
    public StatFs(String path) { this.path = new java.io.File(path); }
    public long getAvailableBytes() { return path.getUsableSpace(); }
}
