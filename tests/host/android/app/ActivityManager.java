package android.app;

/** Host resource input, never an Android memory measurement. */
public final class ActivityManager {
    public final MemoryInfo values = new MemoryInfo();
    public static final class MemoryInfo {
        public long totalMem = 8L * 1024 * 1024 * 1024, availMem = 6L * 1024 * 1024 * 1024;
        public boolean lowMemory;
    }
    public void getMemoryInfo(MemoryInfo target) { target.totalMem = values.totalMem; target.availMem = values.availMem; target.lowMemory = values.lowMemory; }
}
