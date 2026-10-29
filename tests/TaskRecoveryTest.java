package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Production stores and HTTP, with a genuinely halted host child; no Android/model execution. */
public final class TaskRecoveryTest {
    private static final List<String> checks = new ArrayList<>();
    private static final byte[] PNG = Base64.getDecoder().decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lWQAAAAASUVORK5CYII=");
    private static void check(boolean condition, String message) { if (!condition) throw new AssertionError(message); checks.add(message); }
    private interface Op { void run() throws Exception; }
    private static void reject(Op op, String message) throws Exception { try { op.run(); } catch (IllegalArgumentException | IllegalStateException | IOException | JSONException expected) { checks.add(message); return; } throw new AssertionError(message); }
    private static JSONObject request(String prompt) { return new JSONObject().put("bundleId", "recovery_fixture").put("type", "image.generate").put("input", new JSONObject().put("prompt", prompt)).put("parameters", new JSONObject().put("seed", 7)).put("allowUnmeasured", true); }
    private static ArtifactStore outputs(File root) throws Exception { return new ArtifactStore(new File(root, "outputs"), file -> new JSONObject().put("mime", "image/png").put("width", 1).put("height", 1).put("hostInspectorFixture", true)); }
    private static JSONObject publish(ArtifactStore outputs, JSONObject job, JSONObject provenanceRequest) throws Exception {
        File file = outputs.staging(job.getString("id"), "png"); Files.write(file.toPath(), PNG);
        JSONObject provenance = new JSONObject().put("execution", "same_android_phone").put("hostFixture", true).put("request", provenanceRequest).put("bundle", new JSONObject().put("id", provenanceRequest.getString("bundleId")));
        return outputs.commit(job.getString("id"), file, provenance, () -> {});
    }
    private static void crash(File root) throws Exception {
        JobStore jobs = new JobStore(new File(root, "jobs")); ArtifactStore artifacts = outputs(root);
        JSONObject job = jobs.submit(request("Committed output, then real host process halt"), "crash");
        JSONObject active = jobs.claimNext(); jobs.progress(job.getString("id"), active.getString("token"), "saving", null);
        JSONObject artifact = publish(artifacts, job, job.getJSONObject("request"));
        File abandoned = artifacts.staging(job.getString("id"), "rgb"); Files.write(abandoned.toPath(), new byte[]{1,2,3,4,5});
        Path orphan = root.toPath().resolve("outputs/media/artifact_" + UUID.randomUUID().toString().replace("-", "") + ".png"); Files.write(orphan, new byte[]{6,7,8});
        Files.write(root.toPath().resolve("outputs/media/user-note.keep"), new byte[]{9}); Files.write(root.toPath().resolve("outputs/staging/user-note.keep"), new byte[]{10});
        InputUploads uploads = new InputUploads(new File(root, "uploads"), artifacts);
        JSONObject upload = uploads.create(new JSONObject().put("name", "retained.png").put("bytes", PNG.length).put("sha256", artifact.getString("sha256"))); uploads.append(upload.getString("id"), 0, Arrays.copyOf(PNG, 8));
        TaskDrafts drafts = new TaskDrafts(new File(root, "drafts")); drafts.save(request("Preserve this independent draft"), 0);
        Files.createDirectories(root.toPath().resolve("model-data")); Files.write(root.toPath().resolve("model-data/fixture.keep"), new byte[]{11,12,13});
        JSONObject cancelled = jobs.submit(request("Do not revive a cancelled task"), "cancelled"); jobs.cancel(cancelled.getString("id")); JSONObject cancelledOutput = publish(artifacts, cancelled, cancelled.getJSONObject("request"));
        Files.write(root.toPath().resolve("crash-receipt.json"), new JSONObject().put("jobId", job.getString("id")).put("artifactId", artifact.getString("id")).put("cancelledId", cancelled.getString("id")).put("cancelledArtifact", cancelledOutput.getString("id")).put("uploadId", upload.getString("id")).put("orphan", orphan.getFileName().toString()).put("staging", abandoned.getName()).toString().getBytes(StandardCharsets.UTF_8));
        Runtime.getRuntime().halt(37);
    }
    private static JSONObject recovery(File root) throws Exception {
        Files.createDirectories(root.toPath());
        Process child = new ProcessBuilder(Paths.get(System.getProperty("java.home"), "bin", "java.exe").toString(), "-cp", System.getProperty("java.class.path"), TaskRecoveryTest.class.getName(), "crash", root.toString()).redirectErrorStream(true).redirectOutput(new File(root, "crash-child.log")).start();
        try { check(child.waitFor(15, TimeUnit.SECONDS) && child.exitValue() == 37, "A real host child halts after durable artifact publication and before task completion"); }
        finally { if (child.isAlive()) { child.destroyForcibly(); child.waitFor(5, TimeUnit.SECONDS); } }
        JSONObject receipt = new JSONObject(new String(Files.readAllBytes(root.toPath().resolve("crash-receipt.json")), StandardCharsets.UTF_8));
        String id = receipt.getString("jobId"), output = receipt.getString("artifactId");
        JobStore jobs = new JobStore(new File(root, "jobs")); ArtifactStore artifacts = outputs(root); InputUploads uploads = new InputUploads(new File(root, "uploads"), artifacts);
        check(jobs.get(id).getString("state").equals("interrupted") && jobs.get(id).getJSONArray("artifacts").length() == 0, "Restart first reconciles the crashed task as interrupted");
        String digest = artifacts.get(output).getString("sha256"); long sequence = jobs.events(0, "").getLong("cursor");
        JSONObject result = artifacts.reconcile(jobs), restored = jobs.get(id);
        check(result.getInt("recoveredOutputs") == 1 && restored.getJSONArray("artifacts").getString(0).equals(output), "Committed output is relinked to the exact interrupted task");
        check(restored.getString("state").equals("interrupted") && !restored.getJSONObject("outputRecovery").getBoolean("executionResumed"), "Recovering a saved output never promotes the task to successful execution");
        check(DataFiles.sha256(artifacts.file(output)).equals(digest) && Arrays.equals(Files.readAllBytes(artifacts.file(output).toPath()), PNG), "Recovery preserves the actual committed output bytes and digest");
        check(jobs.events(sequence, id).getJSONArray("events").getJSONObject(0).getString("kind").equals("output_recovered"), "Recovery has a durable task event");
        check(jobs.get(receipt.getString("cancelledId")).getString("state").equals("cancelled") && jobs.get(receipt.getString("cancelledId")).getJSONArray("artifacts").length() == 0, "Cancelled tasks remain cancelled and are never revived");
        check(artifacts.file(receipt.getString("cancelledArtifact")).isFile(), "An indexed output is preserved even when its task has no link");
        check(!Files.exists(root.toPath().resolve("outputs/staging/" + receipt.getString("staging"))) && !Files.exists(root.toPath().resolve("outputs/media/" + receipt.getString("orphan"))), "Owned uncommitted staging and moved-but-unindexed output files are reclaimed");
        check(result.getInt("discardedStagingFiles") == 1 && result.getInt("discardedUncommittedFiles") == 1 && result.getLong("reclaimedBytes") == 8, "Cleanup reports the actual reclaimed file count and bytes");
        check(Files.exists(root.toPath().resolve("outputs/media/user-note.keep")) && Files.exists(root.toPath().resolve("outputs/staging/user-note.keep")), "Unexpected private entries are preserved instead of broadly deleted");
        check(uploads.get(receipt.getString("uploadId")).getLong("received") == 8, "A resumable API input upload survives output cleanup");
        check(new TaskDrafts(new File(root, "drafts")).get("recovery_fixture").getJSONObject("request").getJSONObject("input").getString("prompt").contains("independent"), "Independent drafts survive restart reconciliation");
        check(Arrays.equals(Files.readAllBytes(root.toPath().resolve("model-data/fixture.keep")), new byte[]{11,12,13}), "Model data outside output storage remains unchanged");
        long after = jobs.events(0, "").getLong("cursor"); JSONObject again = artifacts.reconcile(jobs);
        check(again.getInt("recoveredOutputs") == 0 && again.getLong("reclaimedBytes") == 0 && jobs.events(0, "").getLong("cursor") == after, "Repeated reconciliation neither duplicates outputs/events nor rewrites task state");
        check(new JobStore(new File(root, "jobs")).get(id).getJSONArray("artifacts").getString(0).equals(output), "Recovered links survive a second independent store restart");
        JSONObject queued = jobs.submit(request("Keep queued"), "queued"); JSONObject plan = jobs.historyPlan();
        JSONObject later = jobs.submit(request("Finishes after review"), "later"); jobs.cancel(later.getString("id"));
        String before = DataFiles.canonical(jobs.snapshot()); JSONObject forged = DataFiles.copy(plan); forged.remove("capacity"); forged.remove("count"); forged.put("review", "wrong");
        reject(() -> jobs.clearHistory(forged), "A changed confirmation fingerprint rejects the entire cleanup"); check(DataFiles.canonical(jobs.snapshot()).equals(before), "Rejected cleanup leaves all task records unchanged");
        JSONObject activeSelection = new JSONObject().put("ids", new JSONArray().put(id).put(queued.getString("id"))).put("review", plan.getString("review"));
        reject(() -> jobs.clearHistory(activeSelection), "A mixed terminal/queued selection is rejected atomically");
        JSONObject selection = new JSONObject().put("ids", plan.getJSONArray("ids")).put("review", plan.getString("review")); JSONObject cleared = jobs.clearHistory(selection);
        check(cleared.getInt("removed") == 2 && jobs.snapshot().length() == 2, "Only the two reviewed terminal records are removed");
        check(jobs.get(queued.getString("id")).getString("state").equals("queued") && jobs.get(later.getString("id")).getString("state").equals("cancelled"), "Pending tasks and tasks finishing after review are both retained");
        check(artifacts.file(output).isFile() && new TaskDrafts(new File(root, "drafts")).summaries().length() == 1, "History cleanup keeps result files and drafts independent");
        reject(() -> jobs.clearHistory(selection), "A stale cleanup is a state conflict rather than a wider deletion");
        JSONObject next = jobs.historyPlan(); jobs.remove(later.getString("id"));
        reject(() -> jobs.clearHistory(new JSONObject().put("ids", next.getJSONArray("ids")).put("review", next.getString("review"))), "Concurrent deletion requires reviewing the selection again");
        JSONObject empty = jobs.historyPlan(); long end = jobs.events(0, "").getLong("cursor");
        check(jobs.clearHistory(new JSONObject().put("ids", empty.getJSONArray("ids")).put("review", empty.getString("review"))).getInt("removed") == 0 && jobs.events(0, "").getLong("cursor") == end, "Empty cleanup performs no task-state mutation");
        return result;
    }
    private static void guards(File root) throws Exception {
        JobStore jobs = new JobStore(new File(root, "jobs")); ArtifactStore artifacts = outputs(root);
        JSONObject job = jobs.submit(request("Original immutable request"), "mismatch"), active = jobs.claimNext();
        JSONObject wrong = request("Changed request must not be linked"); JSONObject output = publish(artifacts, job, wrong);
        reject(() -> artifacts.reconcile(jobs), "Reconciliation refuses to run against an active task store");
        JobStore restarted = new JobStore(new File(root, "jobs")); JSONObject result = artifacts.reconcile(restarted);
        check(result.getInt("rejectedBindings") == 1 && restarted.get(job.getString("id")).getJSONArray("artifacts").length() == 0, "A complete output with mismatched provenance is preserved without a task link");
        check(artifacts.file(output.getString("id")).isFile(), "A rejected binding never deletes an indexed result");
        Files.delete(artifacts.file(output.getString("id")).toPath()); JSONObject missing = artifacts.reconcile(restarted);
        check(missing.getInt("missingOutputs") == 1 && artifacts.snapshot().getJSONObject(0).getBoolean("available") == false, "Missing result bytes remain explicit unavailable records");
        JobStore full = new JobStore(new File(root, "full")); String first = "";
        for (int i=0;i<256;i++) { JSONObject item = full.submit(request("History " + i), "history-"+i); if(i==0)first=item.getString("id"); full.cancel(item.getString("id")); }
        check(full.capacity().getInt("history") == 256 && full.capacity().getInt("terminal") == 256, "The actual bounded history reaches its advertised capacity");
        reject(full::requireCapacity, "Admission reports a full task history before new execution");
        reject(() -> full.submit(request("Overflow"), "overflow"), "The final queue commit independently enforces capacity");
        check(full.submit(request("History 0"), "history-0").getString("id").equals(first), "Existing idempotent submissions remain readable when history is full");
        JSONObject plan = full.historyPlan(); full.clearHistory(new JSONObject().put("ids", plan.getJSONArray("ids")).put("review", plan.getString("review")));
        check(full.submit(request("After cleanup"), "fresh").getString("state").equals("queued"), "Reviewed cleanup restores usable task capacity");
        JobStore pending = new JobStore(new File(root, "pending")); for(int i=0;i<64;i++)pending.submit(request("Pending " + i), "p-"+i);
        reject(pending::requireCapacity, "Pending queue capacity is distinguished from terminal history");
        check(pending.historyPlan().getInt("count") == 0 && pending.capacity().getInt("pending") == 64, "History cleanup offers no active task records");
        check(pending.claimNext() != null, "Already accepted queued work can still start at queue capacity");
    }
    private static JSONObject http(int port, String method, String path, JSONObject payload, String key, int expected) throws Exception {
        HttpURLConnection client = (HttpURLConnection)new URL("http://127.0.0.1:"+port+path).openConnection();
        try { client.setRequestMethod(method); client.setConnectTimeout(3000); client.setReadTimeout(5000); client.setRequestProperty("Authorization", "Bearer "+key);
            if(payload!=null) {client.setDoOutput(true);client.setRequestProperty("Content-Type","application/json");try(OutputStream out=client.getOutputStream()){out.write(payload.toString().getBytes(StandardCharsets.UTF_8));}}
            int code=client.getResponseCode();check(code==expected,"Actual history HTTP "+method+" returns "+expected); try(InputStream in=code<400?client.getInputStream():client.getErrorStream()){return new JSONObject(new String(in.readAllBytes(),StandardCharsets.UTF_8));}
        } finally {client.disconnect();}
    }
    private static void api(File root) throws Exception {
        JobStore jobs=new JobStore(new File(root,"jobs"));ArtifactStore artifacts=outputs(root);int[] notified={0};
        JSONObject terminal=jobs.submit(request("Clean via HTTP"),"http-terminal");jobs.cancel(terminal.getString("id"));JSONObject queued=jobs.submit(request("Retain via HTTP"),"http-queued");
        LocalApi.Runtime runtime=new LocalApi.Runtime(){
            public String apiKey(){return "recovery-fixture-key";} public JSONObject health(){return new JSONObject();} public JSONArray models(){return new JSONArray();} public JSONArray engines(){return new JSONArray();}
            public JobStore jobs(){return jobs;} public ArtifactStore artifacts(){return artifacts;} public void jobsChanged(){notified[0]++;}
            public JSONObject submit(JSONObject r,String key)throws Exception{return jobs.submit(r,key);} public void cancel(String id)throws Exception{jobs.cancel(id);} public LocalHttp.Response text(String path,JSONObject input)throws Exception{throw new IOException("No text execution in this fixture");}
        };
        try(LocalHttp server=new LocalHttp("127.0.0.1",0,new LocalApi(runtime))) {int port=server.port();String key=runtime.apiKey();
            http(port,"GET","/v1/jobs/history",null,"invalid",401);JSONObject plan=http(port,"GET","/v1/jobs/history",null,key,200);
            check(plan.getInt("count")==1&&notified[0]==0,"Reading the cleanup plan neither mutates stores nor notifies the App");
            http(port,"POST","/v1/jobs/history/clear",new JSONObject().put("ids",plan.getJSONArray("ids")).put("review","changed"),key,409);
            check(jobs.snapshot().length()==2&&notified[0]==0,"Rejected HTTP cleanup preserves records and emits no success notification");
            JSONObject selection=new JSONObject().put("ids",plan.getJSONArray("ids")).put("review",plan.getString("review"));
            check(http(port,"POST","/v1/jobs/history/clear",selection,key,200).getInt("removed")==1&&notified[0]==1,"Committed HTTP cleanup refreshes the same native App store once");
            check(jobs.get(queued.getString("id")).getString("state").equals("queued"),"HTTP cleanup retains pending requests");
            http(port,"GET","/v1/jobs/history/clear",null,key,405);http(port,"POST","/v1/jobs/history",new JSONObject(),key,405);
        }
    }
    public static void main(String[] args) throws Exception {
        if(args.length==2&&args[0].equals("crash")){crash(new File(args[1]));return;}
        File root=new File(args[0]);JSONObject recovered=recovery(new File(root,"crash"));guards(new File(root,"guards"));api(new File(root,"api"));
        System.out.println(new JSONObject().put("passed",true).put("count",checks.size()).put("checks",new JSONArray(checks)).put("actual_process_interruption",true).put("actual_persistence_io",true).put("actual_socket_io",true).put("recovery",recovered).put("android_execution_tested",false).put("model_inference_tested",false));
    }
}
