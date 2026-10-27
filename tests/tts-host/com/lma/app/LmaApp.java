package com.lma.app;
import java.io.File;
/** Explicit host filesystem/process port, not an Android Application or a model runtime. */
public final class LmaApp {
    public final Object nativeProcessLock = new Object();
    public volatile Process nativeProcess;
    private final File files;
    public LmaApp(File files) { this.files = files; files.mkdirs(); }
    public File getFilesDir() { return files; }
}
