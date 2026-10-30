package com.lma.app;

import android.content.ContentResolver;
import android.content.res.AssetFileDescriptor;
import android.net.Uri;
import android.os.CancellationSignal;
import com.lma.app.core.InputHandle;
import java.io.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** Actual production DocumentInput and InputHandle; explicit Android framework ports. */
public final class DocumentInputTest {
    private static int passed;
    private static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
        passed++;
    }
    private static final class Descriptor extends AssetFileDescriptor {
        final AtomicInteger closes = new AtomicInteger();
        boolean fail;
        Runnable creating;
        public InputStream createInputStream() throws IOException {
            if (fail) throw new IOException("Provider stream creation failed");
            if (creating != null) creating.run();
            return new ByteArrayInputStream(new byte[] {7, 8}) {
                @Override public void close() { closes.incrementAndGet(); }
            };
        }
        public void close() { closes.incrementAndGet(); }
    }
    private static final class Resolver extends ContentResolver {
        final AtomicInteger calls = new AtomicInteger();
        final CountDownLatch entered = new CountDownLatch(1), released = new CountDownLatch(1);
        Descriptor descriptor = new Descriptor();
        boolean block;
        CancellationSignal signal;
        public AssetFileDescriptor openAssetFileDescriptor(Uri uri, String mode, CancellationSignal value) throws Exception {
            if (!uri.toString().equals("content://selected/input") || !mode.equals("r") || value == null)
                throw new AssertionError("Provider contract changed");
            signal = value;
            calls.incrementAndGet();
            value.onCancel(released::countDown);
            entered.countDown();
            if (block && !released.await(5, TimeUnit.SECONDS)) throw new IOException("Fixture deadline");
            return descriptor;
        }
    }
    private static DocumentInput input(Resolver resolver) {
        return new DocumentInput(resolver, Uri.parse("content://selected/input"));
    }
    private static void rejected(DocumentInput input, String message) throws Exception {
        try { input.open(); throw new AssertionError(message); }
        catch (IOException | IllegalStateException expected) { passed++; }
    }
    public static void main(String[] args) throws Exception {
        Resolver normal = new Resolver();
        InputHandle handle = new InputHandle();
        InputStream stream = handle.open(input(normal));
        check(stream.read() == 7 && stream.read() == 8, "Selected document bytes");
        check(normal.calls.get() == 1 && !normal.signal.isCanceled(), "Read-only cancellable provider open");
        handle.close(); stream.close(); handle.close();
        check(normal.descriptor.closes.get() == 1, "Active stream closes exactly once");

        Resolver before = new Resolver(); DocumentInput canceled = input(before); canceled.cancel();
        rejected(canceled, "Canceled source must not open");
        check(before.calls.get() == 0, "Cancel before provider access");

        Resolver empty = new Resolver(); empty.descriptor = null;
        rejected(input(empty), "Null descriptor must fail");

        Resolver failure = new Resolver(); failure.descriptor.fail = true;
        rejected(input(failure), "Stream creation must fail");
        check(failure.descriptor.closes.get() == 1, "Failed stream creation releases descriptor");

        Resolver pending = new Resolver(); pending.block = true;
        InputHandle opening = new InputHandle();
        AtomicReference<Throwable> error = new AtomicReference<>();
        Thread worker = new Thread(() -> {
            try { opening.open(input(pending)); error.set(new AssertionError("Canceled open returned a stream")); }
            catch (Exception expected) { error.set(expected); }
        }, "lma-document-open-test");
        worker.start();
        try {
            check(pending.entered.await(2, TimeUnit.SECONDS), "Provider opening reached");
            opening.close(); worker.join(2000);
            check(!worker.isAlive(), "Cancellation releases the opening worker");
            check(pending.signal.isCanceled(), "Cancellation reaches the provider signal");
            check(error.get() instanceof IllegalStateException, "Canceled result is rejected");
            check(pending.descriptor.closes.get() == 1, "Late descriptor closes exactly once");
        } finally {
            pending.released.countDown(); opening.close(); worker.join(2000);
        }

        Resolver during = new Resolver(); DocumentInput racing = input(during);
        during.descriptor.creating = racing::cancel;
        rejected(racing, "Cancel during stream creation must reject the stream");
        check(during.descriptor.closes.get() == 1, "Late stream is released");
        System.out.println("{\"passed\":" + passed + ",\"cases\":6,\"production_document_input\":true,\"android_device\":false,\"model_inference\":false}");
    }
}
