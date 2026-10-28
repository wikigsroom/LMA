package android.os;

/** Controlled host thermal input only. */
public final class PowerManager {
    public static final int THERMAL_STATUS_SEVERE = 3;
    public volatile int status;
    public int getCurrentThermalStatus() { return status; }
}
