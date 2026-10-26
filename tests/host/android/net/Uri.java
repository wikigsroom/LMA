package android.net;
/** Host test adapter only; this file is never included in the APK. */
public final class Uri {
    private final String value;
    private Uri(String value) { this.value = value; }
    public static Uri parse(String value) { return new Uri(value); }
    @Override public String toString() { return value; }
}
