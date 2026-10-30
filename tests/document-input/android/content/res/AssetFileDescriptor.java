package android.content.res;

import java.io.InputStream;
import java.io.IOException;

/** Host descriptor ownership port only. */
public abstract class AssetFileDescriptor implements AutoCloseable {
    public abstract InputStream createInputStream() throws IOException;
    @Override public abstract void close() throws IOException;
}
