package android.util;
import java.io.*;
import java.nio.file.*;
/** Filesystem adapter for testing production Store JSON; not an Android AtomicFile test. */
public final class AtomicFile {
    private final File base, pending;
    public AtomicFile(File base) { this.base = base; this.pending = new File(base + ".pending"); }
    public FileInputStream openRead() throws IOException { return new FileInputStream(base); }
    public FileOutputStream startWrite() throws IOException { return new FileOutputStream(pending); }
    public void finishWrite(FileOutputStream stream) throws IOException { stream.getFD().sync(); stream.close(); Files.move(pending.toPath(), base.toPath(), StandardCopyOption.REPLACE_EXISTING); }
    public void failWrite(FileOutputStream stream) { try { stream.close(); } catch (IOException ignored) {} pending.delete(); }
}
