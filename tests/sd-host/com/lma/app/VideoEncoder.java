package com.lma.app;
import java.io.*;
/** Explicit host port: these checks never encode Android video. */
public final class VideoEncoder {
    public interface Check { void run() throws IOException; }
    public static void encode(File raw, File output, Check check) throws Exception { throw new IOException("Android MediaCodec is outside this host test"); }
}
