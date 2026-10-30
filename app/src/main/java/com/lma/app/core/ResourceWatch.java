package com.lma.app.core;

import org.json.JSONObject;

/** Bounded observations of shared system resources, never a model-memory benchmark. */
public final class ResourceWatch {
    public static final long INTERVAL_MILLIS = 2000, STORAGE_FLOOR_BYTES = 64L * 1024 * 1024;
    public interface Probe { Sample sample() throws Exception; }
    public static final class Sample {
        public final long availableRam, availableStorage;
        public final int thermalStatus;
        public final boolean lowMemory;
        public Sample(long ram, long storage, boolean lowMemory, int thermalStatus) {
            if (ram < 0 || storage < 0 || thermalStatus < -1 || thermalStatus > 6) throw new IllegalArgumentException("Invalid system resource sample");
            this.availableRam = ram; this.availableStorage = storage; this.lowMemory = lowMemory; this.thermalStatus = thermalStatus;
        }
    }
    private long startedAt;
    private long samples, errors, minimumRam = Long.MAX_VALUE, minimumStorage = Long.MAX_VALUE, lastAt, endedAt;
    private int maximumThermal = -1;
    private String stopCode = "", stopMessage = "";
    public void start() { if (startedAt == 0) startedAt = System.currentTimeMillis(); }
    public void observe(Sample sample) {
        if (endedAt != 0 || !stopCode.isEmpty()) return;
        start();
        samples++; lastAt = System.currentTimeMillis(); minimumRam = Math.min(minimumRam, sample.availableRam); minimumStorage = Math.min(minimumStorage, sample.availableStorage);
        maximumThermal = Math.max(maximumThermal, sample.thermalStatus);
        if (sample.thermalStatus >= 3) stop("severe_thermal", "手机处于严重高温状态，已停止本次执行；请降温后明确重试，参数和模型文件保留");
        else if (sample.lowMemory) stop("system_low_memory", "系统报告可用内存过低，已停止本次执行；请释放内存后明确重试，参数和模型文件保留");
        else if (sample.availableStorage < STORAGE_FLOOR_BYTES) stop("storage_floor", "可用存储低于运行保留空间，已停止本次执行；请清理空间后明确重试，参数和模型文件保留");
    }
    private void stop(String code, String message) { stopCode = code; stopMessage = message; finish(); }
    public void unavailable() { if (endedAt == 0) errors++; }
    public void finish() { if (endedAt == 0) endedAt = System.currentTimeMillis(); }
    public String failure() { return stopMessage; }
    public boolean finished() { return endedAt != 0; }
    public JSONObject json(boolean enabled) throws Exception {
        return new JSONObject().put("enabled", enabled).put("status", !stopCode.isEmpty() ? "stopped" : endedAt != 0 ? "ended" : startedAt == 0 ? "waiting" : samples == 0 ? "awaiting_sample" : "monitoring")
                .put("startedAt", startedAt).put("lastSampleAt", lastAt).put("endedAt", endedAt).put("samples", samples).put("probeErrors", errors)
                .put("sampleIntervalMs", INTERVAL_MILLIS).put("storageFloorBytes", STORAGE_FLOOR_BYTES).put("thermalStopAt", 3)
                .put("minimumAvailableRamBytes", samples == 0 ? JSONObject.NULL : minimumRam).put("minimumAvailableStorageBytes", samples == 0 ? JSONObject.NULL : minimumStorage)
                .put("maximumThermalStatus", maximumThermal).put("thermalKnown", maximumThermal >= 0).put("stopCode", stopCode).put("message", stopMessage)
                .put("scope", "shared_system_availability_not_model_peak_memory");
    }
}
