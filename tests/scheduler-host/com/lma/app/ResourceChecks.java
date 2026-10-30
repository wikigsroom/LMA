package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Production resource ownership with controlled OS signals and real host children; no phone evidence. */
public final class ResourceChecks {
    private static int passed;
    private static void check(boolean value, String message) { if (!value) throw new AssertionError(message); passed++; }
    private interface Condition { boolean get() throws Exception; }
    private static void until(Condition test) throws Exception {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(12);
        while (System.nanoTime() < end) { if (test.get()) return; Thread.sleep(10); }
        throw new AssertionError("Resource control timed out");
    }
    private static ResourceWatch.Sample sample(int thermal, boolean low, long storage) { return new ResourceWatch.Sample(123, storage, low, thermal); }
    private static ResourceWatch.Sample safe() { return sample(-1, false, ResourceWatch.STORAGE_FLOOR_BYTES); }
    private static Process child() throws Exception {
        return new ProcessBuilder(Paths.get(System.getProperty("java.home"), "bin", "java.exe").toString(), "-cp", System.getProperty("java.class.path"), ResourceChecks.class.getName(), "worker").start();
    }
    public static void main(String[] args) throws Exception { System.out.println("ready"); System.out.flush(); while (System.in.read() >= 0) {} }
    public static int gate() throws Exception {
        int before = passed;
        ResourceWatch watch = new ResourceWatch(); check(watch.json(true).getLong("startedAt") == 0, "Waiting time is not runtime");
        watch.observe(safe()); JSONObject normal = watch.json(true);
        check(watch.failure().isEmpty() && normal.getLong("minimumAvailableRamBytes") == 123, "Allocated model RAM is not double-charged against entry estimate");
        check(!normal.getBoolean("thermalKnown") && normal.getInt("maximumThermalStatus") == -1, "Missing Android thermal signal remains unknown");
        check(normal.getLong("minimumAvailableStorageBytes") == ResourceWatch.STORAGE_FLOOR_BYTES, "Storage floor is inclusive");
        watch.observe(sample(2, false, ResourceWatch.STORAGE_FLOOR_BYTES + 10)); check(watch.failure().isEmpty(), "Moderate thermal status does not stop work");
        watch.observe(sample(3, false, ResourceWatch.STORAGE_FLOOR_BYTES));
        check(watch.json(true).getString("stopCode").equals("severe_thermal") && watch.finished(), "Severe thermal signal ends observations");
        watch.observe(sample(6, true, 0)); watch.unavailable(); check(watch.json(true).getLong("samples") == 3, "Stopped reports cannot mutate from late observations");
        ResourceWatch low = new ResourceWatch(); low.observe(sample(-1, true, ResourceWatch.STORAGE_FLOOR_BYTES));
        check(low.json(true).getString("stopCode").equals("system_low_memory"), "OS low-memory signal stops work");
        ResourceWatch disk = new ResourceWatch(); disk.observe(sample(-1, false, ResourceWatch.STORAGE_FLOOR_BYTES - 1));
        check(disk.json(true).getString("stopCode").equals("storage_floor"), "Disk reserve has an exact boundary");
        ResourceWatch unavailable = new ResourceWatch(); unavailable.unavailable();
        check(unavailable.json(true).isNull("minimumAvailableRamBytes") && unavailable.json(true).getInt("probeErrors") == 1, "Probe failures never invent system values");
        ExecutionGate gate = new ExecutionGate(); AtomicReference<ResourceWatch.Sample> input = new AtomicReference<>(safe());
        ExecutorService executor = Executors.newCachedThreadPool(); List<Process> children = new ArrayList<>();
        try {
            gate.monitorResources(input::get, () -> {});
            for (String kind : Arrays.asList("load", "chat", "api", "job")) {
                Process process = child(); children.add(process); new BufferedReader(new InputStreamReader(process.getInputStream())).readLine();
                ExecutionGate.Ticket ticket = gate.enqueue(kind, "model"); ticket.await(() -> {}); AtomicBoolean notified = new AtomicBoolean();
                ticket.watchProcess(process, reason -> { notified.set(true); check(process.isAlive(), "Resource callback precedes child termination"); });
                gate.pollResources(); input.set(sample(3, false, ResourceWatch.STORAGE_FLOOR_BYTES)); gate.pollResources();
                check(notified.get() && ticket.resourceFailure().contains("高温"), "Shared execution kind records its own stop cause: " + kind);
                try { ticket.checkOwner(); throw new AssertionError("Stopped owner accepted"); } catch (IOException expected) { check(expected.getMessage().contains("高温"), "Owner check preserves resource reason"); }
                ticket.close(); until(() -> !process.isAlive() && gate.snapshot().isNull("active")); input.set(safe());
            }
            check(gate.snapshot().getJSONObject("lastResourceStop").getJSONObject("runtimeResources").getString("stopCode").equals("severe_thermal"), "Last stop survives ticket release for UI/API");
            gate.stopResourceMonitor();
            ExecutionGate.Ticket old = gate.enqueue("job", "old"); old.await(() -> {});
            CountDownLatch entered = new CountDownLatch(1), release = new CountDownLatch(1);
            gate.monitorResources(() -> { entered.countDown(); release.await(); return sample(6, true, 0); }, null);
            check(entered.await(5, TimeUnit.SECONDS), "Slow OS probe begins outside the gate lock"); old.close();
            ExecutionGate.Ticket next = gate.enqueue("api", "next"); next.await(() -> {}); release.countDown();
            // A deterministic extra poll waits for the old probe's thread to release its result.
            gate.stopResourceMonitor(); gate.monitorResources(input::get, null); gate.pollResources();
            check(next.resourceFailure().isEmpty(), "Old probe identity and monitor generation cannot stop the next owner");
            next.finishResourceMonitoring(); input.set(sample(6, true, 0)); gate.pollResources();
            check(next.resourceFailure().isEmpty(), "Published success cannot acquire a late resource failure"); next.close(); input.set(safe());
            ExecutionGate.Ticket late = gate.enqueue("job", "late-child"); late.await(() -> {}); input.set(sample(3, false, ResourceWatch.STORAGE_FLOOR_BYTES)); gate.pollResources();
            Process lateChild = child(); children.add(lateChild);
            try { late.watchProcess(lateChild); throw new AssertionError("Child bound after resource stop"); } catch (IOException expected) { check(expected.getMessage().contains("高温"), "A stage launched across a stop race is immediately rejected"); }
            late.close(); until(() -> !lateChild.isAlive() && gate.snapshot().isNull("active")); input.set(safe());
            ExecutionGate.Ticket delivery = gate.enqueue("chat", "callback-race"); delivery.await(() -> {}); Process owned = child(); children.add(owned);
            CountDownLatch callback = new CountDownLatch(1), leave = new CountDownLatch(1);
            delivery.watchProcess(owned, reason -> { callback.countDown(); try { leave.await(); } catch (InterruptedException error) { Thread.currentThread().interrupt(); } });
            input.set(sample(3, false, ResourceWatch.STORAGE_FLOOR_BYTES)); Future<?> poll = executor.submit(gate::pollResources);
            check(callback.await(5, TimeUnit.SECONDS), "Stop delivery is observable before close"); delivery.close();
            check(!gate.snapshot().isNull("active"), "Closing during stop delivery cannot expose the process to a new owner");
            leave.countDown(); poll.get(5, TimeUnit.SECONDS); until(() -> !owned.isAlive() && gate.snapshot().isNull("active"));
            check(gate.snapshot().getInt("waitingCount") == 0, "Resource stops release all queue ownership after actual exit");
        } finally { gate.stopResourceMonitor(); executor.shutdownNow(); for (Process process : children) { process.destroyForcibly(); process.waitFor(5, TimeUnit.SECONDS); } }
        return passed - before;
    }
    private static JSONObject image(String name) { return new JSONObject().put("bundleId", "image_fixture").put("type", "image.generate").put("allowUnmeasured", true).put("input", new JSONObject().put("prompt", name)); }
    private static JSONObject text(String prompt) { return new JSONObject().put("stream", true).put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", prompt))); }
    public static int runtime(LmaApp app, EngineHost engine, LocalJobs jobs, ChatRunner chat, ApiHost api, Path work, String alias) throws Exception {
        int before = passed; AtomicReference<ResourceWatch.Sample> input = new AtomicReference<>(safe());
        ResourceWatch.Sample os = new DeviceResourceProbe(app).sample();
        check(os.availableRam == app.memory.values.availMem && os.availableStorage > 0, "Production Android probe consumes public memory and app-volume storage signals without assuming free space is static");
        app.memory.values.lowMemory = true; app.power.status = 4;
        ResourceWatch.Sample critical = new DeviceResourceProbe(app).sample();
        check(critical.lowMemory && critical.thermalStatus == 4, "Production Android probe forwards OS low-memory and thermal states");
        app.memory.values.lowMemory = false; app.power.status = 0;
        app.execution.monitorResources(input::get, () -> {});
        try {
            JSONObject stopped = jobs.submit(image("resource-stop"), "resource-stop");
            until(() -> Files.exists(work.resolve("resource-stop.started"))); app.execution.pollResources();
            input.set(sample(-1, true, ResourceWatch.STORAGE_FLOOR_BYTES)); app.execution.pollResources();
            until(() -> app.jobs.get(stopped.getString("id")).getString("state").equals("failed") && !jobs.busy());
            JSONObject failed = app.jobs.get(stopped.getString("id"));
            check(failed.getString("error").contains("内存") && failed.getJSONArray("artifacts").length() == 0, "Blocked production child fails with exact resource cause and no output");
            check(failed.getJSONObject("runtimeResources").getString("stopCode").equals("system_low_memory"), "Terminal task atomically persists bounded system report");
            JobStore reopened = new JobStore(new File(app.getFilesDir(), "jobs"));
            check(DataFiles.canonical(failed).equals(DataFiles.canonical(reopened.get(failed.getString("id")))), "Stopped task and immutable request survive reopening");
            input.set(safe()); until(engine::ready); Files.write(work.resolve("resource-stop.release"), new byte[]{1});
            JSONObject retry = jobs.retry(stopped.getString("id"), "resource-retry");
            until(() -> app.jobs.get(retry.getString("id")).getString("state").equals("succeeded") && !jobs.busy());
            JSONObject success = app.jobs.get(retry.getString("id"));
            check(!success.getString("id").equals(stopped.getString("id")) && success.getJSONObject("runtimeResources").getString("status").equals("ended"), "Explicit retry creates a fresh task and resource report");
            JSONObject output = app.artifacts.get(success.getJSONArray("artifacts").getString(0));
            check(output.getJSONObject("provenance").has("runtimeResources"), "Success publishes its frozen resource report with provenance");
            until(engine::ready); chat.send("stop"); until(() -> app.generating && app.chats.last().optString("content").length() > 0);
            input.set(sample(3, false, ResourceWatch.STORAGE_FLOOR_BYTES)); app.execution.pollResources(); until(() -> !app.generating);
            JSONObject partial = app.chats.last();
            check(partial.getString("status").equals("error") && partial.getString("error").contains("高温") && !partial.getString("content").isEmpty(), "Chat preserves partial reply and exact stop reason");
            check(!engine.wanted() && !app.prefs.getBoolean("desiredRunning", true), "Resource stop disables automatic text recovery");
            input.set(safe()); engine.load(alias); until(engine::ready);
            try (LocalHttp.Response response = api.text("/v1/chat/completions", text("stop"))) {
                input.set(sample(-1, false, 0)); app.execution.pollResources();
                try { response.body.write(new ByteArrayOutputStream()); throw new AssertionError("API resource stop returned success"); }
                catch (IOException expected) { check(expected.getMessage().contains("存储"), "API stream propagates resource error instead of successful EOF"); }
            }
            until(() -> app.execution.snapshot().isNull("active"));
            check(api.health().getJSONObject("scheduler").getJSONObject("lastResourceStop").getString("kind").equals("api"), "Authenticated API health exposes the latest resource stop");
            check(!engine.wanted() && app.store.installed(alias) && app.store.config(alias).getJSONObject("values").getInt("maxTokens") == 37, "API stop preserves local model and per-model defaults");
        } finally { input.set(safe()); app.execution.stopResourceMonitor(); }
        engine.load(alias); until(engine::ready);
        return passed - before;
    }
}
