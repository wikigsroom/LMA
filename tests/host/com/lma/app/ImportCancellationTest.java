package com.lma.app;

import android.net.Uri;
import com.lma.app.core.*;
import java.io.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.json.*;

/** Production legacy-model/media import owners with explicit host provider ports. */
public final class ImportCancellationTest {
    private static final List<String> checks = new ArrayList<>();
    private static void check(boolean ok, String message) { if (!ok) throw new AssertionError(message); checks.add(message); }
    private interface Condition { boolean test() throws Exception; }
    private static void await(Condition condition) throws Exception {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(4);
        while (!condition.test() && System.nanoTime() < end) Thread.sleep(10);
        if (!condition.test()) throw new AssertionError("Import owner did not release its queue");
    }
    private static final class Provider {
        final CountDownLatch blocked = new CountDownLatch(1), released = new CountDownLatch(1);
        final byte[] bytes; final boolean opening;
        final AtomicInteger cancelled = new AtomicInteger(), closes = new AtomicInteger();
        Provider(byte[] bytes, boolean opening) { this.bytes = bytes; this.opening = opening; }
        private void waitForCancel() throws IOException {
            blocked.countDown();
            try { if (!released.await(15, TimeUnit.SECONDS)) throw new IOException("Host provider timeout"); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new IOException(e); }
        }
        InputStream readingStream() {
            return new InputStream() {
                boolean first = true, closed;
                public int read() throws IOException { throw new IOException("Bulk reads required"); }
                public int read(byte[] out, int offset, int length) throws IOException {
                    if (first) { first = false; int n = Math.min(64, length); System.arraycopy(bytes, 0, out, offset, n); return n; }
                    waitForCancel(); throw new IOException("Provider read cancelled");
                }
                public void close() { if (!closed) { closed = true; closes.incrementAndGet(); released.countDown(); } }
            };
        }
        BundleTransfers.Input source() {
            return new BundleTransfers.Input() {
                public InputStream open() throws Exception {
                    if (!opening) return readingStream();
                    waitForCancel();
                    return new ByteArrayInputStream(bytes) { public void close() { closes.incrementAndGet(); } };
                }
                public void cancel() { Provider.this.cancel(); }
            };
        }
        public void cancel() { cancelled.incrementAndGet(); released.countDown(); }
    }
    private static String checksum(byte[] data) throws Exception { return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(data)); }
    private static void legacy(LmaApp app, byte[] data, boolean opening, boolean stop) throws Exception {
        String prefix = "legacy_" + opening + "_" + stop, blockedUri = "content://host/" + prefix, nextUri = blockedUri + "/next";
        Provider provider = new Provider(data, opening); AtomicInteger nextOpened = new AtomicInteger();
        DocumentInput.providers.put(blockedUri, provider.source());
        DocumentInput.providers.put(nextUri, () -> { nextOpened.incrementAndGet(); return new ByteArrayInputStream(data); });
        String one = app.store.addCustom(prefix, "", checksum(data), true), two = app.store.addCustom(prefix + "_next", "", checksum(data), true);
        Downloads downloads = new Downloads(new LmaService(), app);
        try {
            downloads.enqueue(one, blockedUri); check(provider.blocked.await(3, TimeUnit.SECONDS), prefix + " reaches provider wait");
            downloads.enqueue(two, nextUri);
            if (stop) downloads.close(); else downloads.pause(one);
            await(() -> !downloads.busy());
            check(provider.closes.get() == 1 && (!opening || provider.cancelled.get() == 1), prefix + " cancels opening/reading and closes its resource once");
            check(!app.store.installed(one) && app.store.download(one).getString("state").equals("paused"), prefix + " keeps partial bytes uninstalled and durable pause");
            check(nextOpened.get() == (stop ? 0 : 1) && app.store.installed(two) == !stop, prefix + " observes explicit queued-work ownership");
            DocumentInput.providers.put(blockedUri, () -> new ByteArrayInputStream(data));
            Downloads recovery = stop ? new Downloads(new LmaService(), app) : downloads;
            try { recovery.enqueue(one, blockedUri); await(() -> !recovery.busy()); check(Arrays.equals(Files.readAllBytes(app.store.modelFile(one).toPath()), data), prefix + " explicit recovery verifies complete GGUF bytes"); }
            finally { if (stop) recovery.close(); }
        } finally { provider.cancel(); downloads.close(); DocumentInput.providers.remove(blockedUri); DocumentInput.providers.remove(nextUri); }
    }
    private static byte[] wav() {
        ByteBuffer b = ByteBuffer.allocate(44 + 640).order(ByteOrder.LITTLE_ENDIAN);
        b.put("RIFF".getBytes(StandardCharsets.US_ASCII)).putInt(b.capacity() - 8).put("WAVEfmt ".getBytes(StandardCharsets.US_ASCII));
        b.putInt(16).putShort((short)1).putShort((short)1).putInt(16000).putInt(32000).putShort((short)2).putShort((short)16);
        b.put("data".getBytes(StandardCharsets.US_ASCII)).putInt(640); while (b.hasRemaining()) b.putShort((short)100); return b.array();
    }
    private static void media(LmaApp app, File folder, boolean opening, boolean stop) throws Exception {
        app.artifacts = new ArtifactStore(folder, file -> WaveFile.inspect(file));
        byte[] data = wav(); String prefix = "media_" + opening + "_" + stop, uri = "content://host/" + prefix, next = uri + "/next";
        Provider provider = new Provider(data, opening); AtomicInteger queued = new AtomicInteger();
        DocumentInput.providers.put(uri, provider.source()); DocumentInput.providers.put(next, () -> { queued.incrementAndGet(); return new ByteArrayInputStream(data); });
        InputImports imports = new InputImports(app, () -> {});
        try {
            imports.add(Uri.parse(uri), prefix + ".wav"); check(provider.blocked.await(3, TimeUnit.SECONDS), prefix + " reaches provider wait");
            imports.add(Uri.parse(next), "queued.wav");
            if (stop) imports.close(); else imports.cancel();
            await(() -> !imports.busy());
            check(provider.closes.get() == 1 && (!opening || provider.cancelled.get() == 1), prefix + " closes pending provider ownership once");
            check(app.artifacts.snapshot().length() == 0 && queued.get() == 0 && app.lastError.isEmpty(), prefix + " cancels queued inputs without publishing or reporting failure");
            File[] partial = new File(folder, "staging").listFiles(); check(partial != null && partial.length == 0, prefix + " removes cancelled private staging");
            InputImports recovery = stop ? new InputImports(app, () -> {}) : imports;
            try { recovery.add(Uri.parse(next), "selected.wav"); await(() -> !recovery.busy()); check(app.artifacts.snapshot().length() == 1 && queued.get() == 1, prefix + " explicit recovery publishes a validated WAV"); }
            finally { if (stop) recovery.close(); }
        } finally { provider.cancel(); imports.close(); DocumentInput.providers.remove(uri); DocumentInput.providers.remove(next); }
    }
    public static List<String> run(LmaApp app, byte[] gguf, File root) throws Exception {
        for (boolean opening : new boolean[]{true, false}) for (boolean stop : new boolean[]{false, true}) {
            legacy(app, gguf, opening, stop);
            media(app, new File(root, "media_" + opening + "_" + stop), opening, stop);
        }
        return new ArrayList<>(checks);
    }
}
