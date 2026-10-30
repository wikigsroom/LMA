package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Production transfers against blocking local providers, not Android or model inference. */
public final class BundlePauseTest {
    private static int passed;
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
        passed++;
    }
    private static byte[] bytes(int seed) {
        byte[] result = new byte[256 * 1024];
        new Random(seed).nextBytes(result);
        return result;
    }
    private static ModelBundle bundle(String id, byte[] data) throws Exception {
        JSONObject component = new JSONObject().put("role", "model").put("path", "model.bin")
            .put("format", "fixture_data").put("bytes", data.length)
            .put("sha256", Protocol.hex(MessageDigest.getInstance("SHA-256").digest(data)));
        return new ModelBundle(new JSONObject().put("schema", ModelBundle.SCHEMA).put("id", id)
            .put("modelId", id).put("recipeId", "fixture_recipe_v1").put("name", id)
            .put("engine", "fixture_engine").put("architecture", "fixture_arch")
            .put("pipeline", "fixture_pipeline").put("backend", "cpu")
            .put("tasks", new JSONArray().put("image"))
            .put("parameters", new JSONObject().put("fields", new JSONObject()))
            .put("components", new JSONArray().put(component)));
    }
    private static final class BlockedInput extends InputStream {
        final CountDownLatch reading = new CountDownLatch(1), released = new CountDownLatch(1);
        final byte[] data;
        volatile boolean closed;
        int reads;
        BlockedInput(byte[] data) { this.data = data; }
        @Override public int read() throws IOException { throw new IOException("Use bulk read"); }
        @Override public int read(byte[] out, int offset, int length) throws IOException {
            if (closed) throw new IOException("Provider closed");
            if (reads++ == 0) {
                int count = Math.min(8192, length);
                System.arraycopy(data, 0, out, offset, count);
                return count;
            }
            reading.countDown();
            try {
                if (!released.await(20, TimeUnit.SECONDS)) throw new IOException("Fixture timeout");
            } catch (InterruptedException error) {
                Thread.currentThread().interrupt(); throw new IOException(error);
            }
            throw new IOException("Provider closed during blocked read");
        }
        @Override public void close() { closed = true; released.countDown(); }
    }
    private static final class BlockedOpen implements BundleTransfers.Input {
        final CountDownLatch opening = new CountDownLatch(1), released = new CountDownLatch(1);
        final AtomicInteger cancellations = new AtomicInteger();
        volatile boolean streamClosed;
        public InputStream open() throws Exception {
            opening.countDown();
            if (!released.await(20, TimeUnit.SECONDS)) throw new IOException("Opening fixture timeout");
            // A provider may still return a descriptor after accepting cancellation.
            return new ByteArrayInputStream(bytes(46)) {
                @Override public void close() throws IOException { streamClosed = true; super.close(); }
            };
        }
        public void cancel() { cancellations.incrementAndGet(); released.countDown(); }
    }
    private static BundleTransfers transfers(BundleStore store, AtomicInteger installed, AtomicInteger failures) {
        return new BundleTransfers(store, (component, offset, observer) -> {
            throw new IOException("No network in local import contract");
        }, new BundleTransfers.Listener() {
            public void changed() {}
            public void installed(String id) { installed.incrementAndGet(); }
            public void failed(String id, String message) { failures.incrementAndGet(); }
        });
    }
    private static void pausedRead(File root) throws Exception {
        byte[] first = bytes(42), second = bytes(43);
        BundleStore store = new BundleStore(root);
        ModelBundle one = bundle("blocked_one", first), two = bundle("queued_two", second);
        store.declare(one); store.declare(two);
        AtomicInteger installed = new AtomicInteger(), failures = new AtomicInteger();
        BlockedInput input = new BlockedInput(first);
        try (BundleTransfers transfers = transfers(store, installed, failures)) {
            try {
                transfers.importFiles(one.id, Collections.singletonMap("model", () -> input));
                check(input.reading.await(3, TimeUnit.SECONDS), "The real transfer reaches a blocked provider read");
                transfers.importFiles(two.id, Collections.singletonMap("model", () -> new ByteArrayInputStream(second)));
                transfers.pause(one.id);
                check(transfers.awaitIdle(3, TimeUnit.SECONDS), "Pause must release the blocked read and let the next user-selected import run");
                check(input.closed, "Pause closes the active provider stream");
                check(store.record(one.id).getJSONObject("transfer").getString("state").equals("paused"), "Paused state remains durable");
                check(!store.plan(one.id).getBoolean("installed"), "A partial import never becomes installed");
                File partial = store.partial(one.components.get(0).objectId);
                check(Arrays.equals(Files.readAllBytes(partial.toPath()), Arrays.copyOf(first, 8192)), "Pause retains exactly the already-copied bytes");
                check(store.plan(two.id).getBoolean("installed") && installed.get() == 1 && failures.get() == 0,
                    "The queued independent bundle installs without reporting pause as a failure");
                transfers.importFiles(one.id, Collections.singletonMap("model", () -> new ByteArrayInputStream(first)));
                check(transfers.awaitIdle(3, TimeUnit.SECONDS) && store.plan(one.id).getBoolean("installed"), "Explicitly selected import can restart and finish after pause");
                check(Arrays.equals(Files.readAllBytes(store.object(one.components.get(0).objectId).toPath()), first), "The restarted import preserves complete file integrity");
            } finally { input.close(); }
        }
    }
    private static void closedRead(File root) throws Exception {
        byte[] first = bytes(44), second = bytes(45);
        BundleStore store = new BundleStore(root);
        ModelBundle one = bundle("close_active", first), two = bundle("close_queued", second);
        store.declare(one); store.declare(two);
        AtomicInteger installed = new AtomicInteger(), failures = new AtomicInteger(), opened = new AtomicInteger();
        BlockedInput input = new BlockedInput(first);
        BundleTransfers transfers = transfers(store, installed, failures);
        try {
            transfers.importFiles(one.id, Collections.singletonMap("model", () -> input));
            check(input.reading.await(3, TimeUnit.SECONDS), "Shutdown case reaches the actual blocked read");
            transfers.importFiles(two.id, Collections.singletonMap("model", () -> { opened.incrementAndGet(); return new ByteArrayInputStream(second); }));
            transfers.close();
            check(transfers.awaitIdle(3, TimeUnit.SECONDS) && input.closed, "Shutdown closes the stream and drains transfer ownership");
            check(opened.get() == 0 && installed.get() == 0 && failures.get() == 0, "Shutdown never opens queued imports or reports user cancellation as failure");
            check(store.record(one.id).getJSONObject("transfer").getString("state").equals("paused")
                && store.record(two.id).getJSONObject("transfer").getString("state").equals("paused"), "Both active and queued imports remain explicitly paused");
        } finally { input.close(); transfers.close(); }
    }
    private static void pausedOpen(File root) throws Exception {
        byte[] first = bytes(46), second = bytes(47);
        BundleStore store = new BundleStore(root);
        ModelBundle one = bundle("opening_one", first), two = bundle("after_open", second);
        store.declare(one); store.declare(two);
        AtomicInteger installed = new AtomicInteger(), failures = new AtomicInteger();
        BlockedOpen input = new BlockedOpen();
        try (BundleTransfers transfers = transfers(store, installed, failures)) {
            try {
                transfers.importFiles(one.id, Collections.singletonMap("model", input));
                check(input.opening.await(3, TimeUnit.SECONDS), "Transfer reaches a real blocked provider open");
                transfers.importFiles(two.id, Collections.singletonMap("model", () -> new ByteArrayInputStream(second)));
                transfers.pause(one.id);
                check(transfers.awaitIdle(3, TimeUnit.SECONDS), "Pause must cancel a pending provider open and release the queue");
                check(input.cancellations.get() == 1 && input.streamClosed, "Cancel reaches the opener and closes a late returned stream");
                check(!store.plan(one.id).getBoolean("installed") && store.plan(two.id).getBoolean("installed"), "Only the next explicit import installs");
                check(store.record(one.id).getJSONObject("transfer").getString("state").equals("paused") && failures.get() == 0, "Opening cancellation stays paused without a failure");
            } finally { input.cancel(); }
        }
    }
    private static void closedOpen(File root) throws Exception {
        BundleStore store = new BundleStore(root);
        ModelBundle one = bundle("closing_open", bytes(46)), two = bundle("closing_wait", bytes(48));
        store.declare(one); store.declare(two);
        AtomicInteger installed = new AtomicInteger(), failures = new AtomicInteger(), opened = new AtomicInteger();
        BlockedOpen input = new BlockedOpen();
        BundleTransfers transfers = transfers(store, installed, failures);
        try {
            transfers.importFiles(one.id, Collections.singletonMap("model", input));
            check(input.opening.await(3, TimeUnit.SECONDS), "Shutdown reaches a pending provider open");
            transfers.importFiles(two.id, Collections.singletonMap("model", () -> { opened.incrementAndGet(); return new ByteArrayInputStream(bytes(48)); }));
            transfers.close();
            check(transfers.awaitIdle(3, TimeUnit.SECONDS) && input.cancellations.get() == 1 && input.streamClosed, "Shutdown cancels opening and closes late descriptors");
            check(opened.get() == 0 && installed.get() == 0 && failures.get() == 0, "Shutdown starts no queued provider and publishes no partial model");
            check(store.record(one.id).getJSONObject("transfer").getString("state").equals("paused") && store.record(two.id).getJSONObject("transfer").getString("state").equals("paused"), "Both records remain paused after opening cancellation");
        } finally { input.cancel(); transfers.close(); }
    }
    public static int run(File root) throws Exception {
        int before = passed;
        pausedRead(new File(root, "pause"));
        closedRead(new File(root, "shutdown"));
        pausedOpen(new File(root, "opening-pause"));
        closedOpen(new File(root, "opening-shutdown"));
        return passed - before;
    }
    public static void main(String[] args) throws Exception {
        run(new File(args[0]));
        System.out.println(new JSONObject().put("passed", passed).put("blocked_provider_cases", 4)
            .put("network_requests", 0).put("model_inference", false).put("physical_android", false));
    }
}
