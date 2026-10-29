package android.util;

import java.io.*;
import java.nio.file.*;

/** Windows functional metadata port; no Android AtomicFile or power-loss durability test. */
public final class AtomicFile {
    private final File base, pending;
    public AtomicFile(File base) { this.base = base; this.pending = new File(base + ".pending"); }
    public FileInputStream openRead() throws IOException { return new FileInputStream(base); }
    public FileOutputStream startWrite() throws IOException { return new FileOutputStream(pending); }
    public void finishWrite(FileOutputStream stream) throws IOException {
        // This port checks close/atomic replace/ordinary restart, not media flush.
        // Production Android AtomicFile and complete model-file sync are unchanged.
        stream.close();
        // A single replace avoids the Windows delete-then-move sharing window.
        // Bounded sharing retries preserve the previous committed file on failure.
        for (int attempt = 0; ; attempt++) {
            try {
                Files.move(pending.toPath(), base.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
                return;
            } catch (FileSystemException busy) {
                if (attempt >= 19 || !pending.isFile()) throw busy;
                try { Thread.sleep(50); }
                catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); throw new IOException("Metadata replacement interrupted", interrupted); }
            }
        }
    }
    public void failWrite(FileOutputStream stream) { try { stream.close(); } catch (IOException ignored) {} pending.delete(); }
}
