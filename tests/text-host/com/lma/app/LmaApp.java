package com.lma.app;
import java.io.File;
/** Explicit host filesystem/process port; no Android or inference is emulated. */
public final class LmaApp {
    public final Object nativeProcessLock = new Object();
    public volatile Process nativeProcess;
    public com.lma.app.core.BundleStore bundles;
    public static final class Info { public String nativeLibraryDir; }
    private final File root;
    private final Info info = new Info();
    public LmaApp(File root) { this.root = root; root.mkdirs(); info.nativeLibraryDir = root.getPath(); }
    public File getFilesDir() { return root; }
    public Info getApplicationInfo() { return info; }
}
