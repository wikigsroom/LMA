package com.lma.app;

import android.app.ActivityManager;
import android.os.Build;
import android.os.PowerManager;
import com.lma.app.core.ResourceWatch;

/** Public Android system status; no root, hidden temperature API or device claim from compilation. */
public final class DeviceResourceProbe implements ResourceWatch.Probe {
    private final LmaApp app;
    public DeviceResourceProbe(LmaApp app) { this.app = app; }
    @Override public ResourceWatch.Sample sample() {
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo();
        ((ActivityManager)app.getSystemService(LmaApp.ACTIVITY_SERVICE)).getMemoryInfo(memory);
        int thermal = Build.VERSION.SDK_INT >= 29 ? ((PowerManager)app.getSystemService(LmaApp.POWER_SERVICE)).getCurrentThermalStatus() : -1;
        return new ResourceWatch.Sample(memory.availMem, app.getFilesDir().getUsableSpace(), memory.lowMemory, thermal);
    }
}
