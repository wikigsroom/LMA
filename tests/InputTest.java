package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** Actual private-file/WAV/storage/HTTP tests. Synthetic PCM is data, not a model output. */
public final class InputTest {
    private static final List<String> checks = new ArrayList<>();
    private static final String KEY = "lma_INPUT_HOST_TEST_ONLY";
    private static void check(boolean value, String label) { if (!value) throw new AssertionError(label); checks.add(label); }
    private interface Work { void run() throws Exception; }
    private static void rejected(Work work, String label) throws Exception { try { work.run(); } catch (Exception expected) { checks.add(label); return; } throw new AssertionError(label); }
    private static String hash(byte[] bytes) throws Exception { return Protocol.hex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
    private static byte[] wave(int samples) {
        ByteBuffer out = ByteBuffer.allocate(44 + samples * 2).order(ByteOrder.LITTLE_ENDIAN);
        out.put("RIFF".getBytes(StandardCharsets.US_ASCII)).putInt(out.capacity() - 8).put("WAVEfmt ".getBytes(StandardCharsets.US_ASCII)).putInt(16).putShort((short)1).putShort((short)1).putInt(16000).putInt(32000).putShort((short)2).putShort((short)16).put("data".getBytes(StandardCharsets.US_ASCII)).putInt(samples * 2);
        while (out.hasRemaining()) out.putShort((short)(out.position() % 300)); return out.array();
    }
    private static JSONObject reference(String id) { return new JSONObject().put("role", "reference_audio").put("artifactId", id); }
    private static JSONObject task(String id) { return new JSONObject().put("bundleId", "input_fixture").put("type", "speech.synthesize").put("input", new JSONObject().put("prompt", "Synthetic host contract").put("artifacts", new JSONArray().put(reference(id)))); }
    private static InputSpec spec(boolean required, String mime, long bytes, long duration) throws Exception {
        return new InputSpec(new JSONObject().put("reference_audio", new JSONObject().put("label", "Reference audio").put("required", required).put("mimes", new JSONArray().put(mime)).put("maxBytes", bytes).put("maxDurationMs", duration)));
    }
    private static final class Reply {
        final int status; final byte[] data;
        Reply(int status, byte[] data) { this.status = status; this.data = data; }
        JSONObject json() { return new JSONObject(new String(data, StandardCharsets.UTF_8)); }
    }
    private static Reply request(int port, String method, String path, byte[] bytes, String mime, String key, Map<String,String> headers) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL("http://127.0.0.1:" + port + path).openConnection();
        c.setConnectTimeout(2000); c.setReadTimeout(5000); c.setRequestMethod(method);
        if (key != null) c.setRequestProperty("Authorization", "Bearer " + key);
        for (Map.Entry<String,String> h : headers.entrySet()) c.setRequestProperty(h.getKey(), h.getValue());
        if (bytes != null) { c.setDoOutput(true); c.setRequestProperty("Content-Type", mime); c.setFixedLengthStreamingMode(bytes.length); try (OutputStream out = c.getOutputStream()) { out.write(bytes); } }
        try {
            int status = c.getResponseCode(); InputStream stream = status >= 400 ? c.getErrorStream() : c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream();
            if (stream != null) try (InputStream in = stream) { byte[] buffer = new byte[8192]; int n; while ((n = in.read(buffer)) != -1) out.write(buffer,0,n); }
            return new Reply(status, out.toByteArray());
        } finally { c.disconnect(); }
    }
    private static Reply json(int port, String method, String path, JSONObject body) throws Exception { return request(port, method, path, body == null ? null : body.toString().getBytes(StandardCharsets.UTF_8), "application/json", KEY, Collections.emptyMap()); }
    private static JSONObject declaration(byte[] bytes) throws Exception { return new JSONObject().put("name", "reference.wav").put("bytes", bytes.length).put("sha256", hash(bytes)); }
    private static void core(Path root) throws Exception {
        Path input = root.resolve("synthetic.wav"); byte[] bytes = wave(8000); Files.write(input,bytes);
        JSONObject media = WaveFile.inspect(input.toFile());
        check(media.getInt("durationMs") == 500 && media.getInt("samples") == 8000 && media.getInt("sampleRate") == 16000, "Actual WAV validation derives duration and samples from PCM bytes");
        byte[] broken = bytes.clone(); broken[4] ^= 1; Files.write(input,broken); rejected(() -> WaveFile.inspect(input.toFile()), "Truncated/incorrect RIFF lengths are rejected");
        broken = bytes.clone(); broken[32] = 4; Files.write(input,broken); rejected(() -> WaveFile.inspect(input.toFile()), "Inconsistent PCM alignment is rejected");
        broken = bytes.clone(); broken[28] ^= 4; Files.write(input,broken); rejected(() -> WaveFile.inspect(input.toFile()), "Inconsistent PCM byte rate is rejected");
        Files.write(input, wave(0)); rejected(() -> WaveFile.inspect(input.toFile()), "Empty PCM is rejected"); Files.write(input, bytes);
        ArtifactStore artifacts = new ArtifactStore(root.resolve("artifacts").toFile(), WaveFile::inspect);
        AtomicReference<JobStore> jobs = new AtomicReference<>(new JobStore(root.resolve("jobs").toFile())); artifacts.references(id -> jobs.get().referencesArtifact(id));
        JSONObject artifact = artifacts.importStream(new ByteArrayInputStream(bytes), "测试参考.wav", () -> {}); String id = artifact.getString("id");
        check(artifact.getJSONObject("origin").getString("kind").equals("imported") && artifact.getString("jobId").isEmpty(), "Imported media is explicitly distinct from generated model output");
        check(artifact.getString("sha256").equals(hash(bytes)) && Arrays.equals(Files.readAllBytes(artifacts.file(id).toPath()),bytes), "Import copies exact bytes privately and computes their actual SHA256");
        check(artifact.getJSONObject("origin").getString("name").equals("测试参考.wav") && !artifact.toString().contains("content://"), "Imported provenance preserves a display name without Android URI/path disclosure");
        rejected(() -> artifacts.importStream(new ByteArrayInputStream(new byte[]{1,2,3}), "invalid.wav", () -> {}), "An extension cannot make malformed input media valid");
        rejected(() -> artifacts.importStream(new ByteArrayInputStream(new byte[0]), "empty.wav", () -> {}), "Empty local files never enter the media library");
        rejected(() -> artifacts.importStream(new ByteArrayInputStream(bytes), "../escape.wav", () -> {}), "Input filenames cannot escape private storage");
        int count = artifacts.snapshot().length();
        rejected(() -> artifacts.importStream(new ByteArrayInputStream(bytes), "cancelled.wav", () -> { throw new IOException("fixture cancellation"); }), "Cancelling import prevents artifact publication");
        check(artifacts.snapshot().length() == count && root.resolve("artifacts/staging").toFile().list().length == 0, "Failed/cancelled imports clean private staging without deleting existing media");
        JSONObject raw = TaskInput.validate(task(id)); InputSpec spec = spec(true, "audio/wav", 1024 * 1024, 1000);
        JSONObject pinned = InputSelection.prepare(artifacts, spec, raw);
        check(pinned.getJSONArray("inputReceipts").getJSONObject(0).getString("sha256").equals(hash(bytes)), "Task submission pins actual input digest, metadata and byte count");
        rejected(() -> InputSelection.prepare(artifacts, InputSpec.promptOnly(), raw), "Prompt-only engines reject media roles instead of ignoring inputs");
        rejected(() -> InputSelection.prepare(artifacts, spec(true,"image/png",1024*1024,1000),raw), "Input MIME must match the signed engine role");
        rejected(() -> InputSelection.prepare(artifacts, spec(true,"audio/wav",8,1000),raw), "Each recipe enforces its own input byte bound");
        rejected(() -> InputSelection.prepare(artifacts, spec(true,"audio/wav",1024*1024,100),raw), "Each recipe enforces actual input duration limits");
        rejected(() -> InputSelection.prepare(artifacts,spec,new JSONObject().put("input",new JSONObject().put("prompt","missing"))), "Required local input roles cannot be omitted");
        rejected(() -> TaskInput.validate(task(id).put("input",new JSONObject().put("prompt","p").put("image","https://example.invalid/image.png"))), "Task inputs cannot ask the phone to fetch a URL");
        rejected(() -> TaskInput.validate(task(id).put("input",new JSONObject().put("prompt","p").put("artifacts",new JSONArray().put(reference(id)).put(reference(id))))), "Duplicate input roles are rejected");
        rejected(() -> TaskInput.validate(task(id).put("input",new JSONObject().put("prompt","p").put("artifacts",new JSONArray().put(reference(id).put("path","/private/file"))))), "Clients cannot inject filesystem paths into input references");
        rejected(() -> TaskInput.validate(task(id).put("inputReceipts",new JSONArray())), "Clients cannot supply trusted input receipts");
        JSONObject job; synchronized(artifacts) { job = jobs.get().submit(pinned, "input-key"); }
        String jobId = job.getString("id"); check(jobs.get().referencesArtifact(id) && artifacts.snapshot().getJSONObject(0).getBoolean("inUse"), "Queued tasks protect all selected media before execution");
        rejected(() -> artifacts.remove(id), "Queued input cannot be deleted");
        jobs.set(new JobStore(root.resolve("jobs").toFile())); check(jobs.get().referencesArtifact(id), "Queued media references survive process/storage restart");
        rejected(() -> artifacts.remove(id), "Restarted queued references still block deletion");
        try (InputSelection.Selection inputs = InputSelection.acquire(artifacts,spec,pinned,()->{})) {
            check(Arrays.equals(Files.readAllBytes(inputs.file("reference_audio").toPath()),bytes), "Engine context resolves a role to only the pinned private file");
            jobs.get().cancel(jobId); rejected(() -> artifacts.remove(id), "An execution lease protects media even after cancellation becomes terminal");
        }
        check(!jobs.get().referencesArtifact(id), "Terminal history retains provenance without permanently pinning input storage");
        byte[] changed = bytes.clone(); changed[changed.length-1] ^= 1; Files.write(artifacts.file(id).toPath(),changed);
        rejected(() -> InputSelection.acquire(artifacts,spec,pinned,()->{}), "Same-size media tampering fails full digest revalidation before engine start");
        artifacts.remove(id); check(artifacts.snapshot().length() == 0, "Failed input validation releases all leases so unreferenced bytes can be deleted");
        rejected(() -> InputSelection.prepare(artifacts,spec,raw), "Retry with deleted media fails locally instead of downloading/replacing it");
        ArtifactStore after = new ArtifactStore(root.resolve("artifacts").toFile(),WaveFile::inspect); check(after.snapshot().length() == 0, "Explicit input deletion is durable");
    }
    private static void http(Path root) throws Exception {
        ArtifactStore artifacts = new ArtifactStore(root.resolve("artifacts").toFile(),WaveFile::inspect); JobStore jobs = new JobStore(root.resolve("jobs").toFile()); artifacts.references(jobs::referencesArtifact);
        AtomicReference<InputUploads> uploads = new AtomicReference<>(new InputUploads(root.resolve("uploads").toFile(),artifacts));
        InputSpec spec = spec(true,"audio/wav",2*1024*1024,30000);
        LocalApi.Runtime runtime = new LocalApi.Runtime() {
            @Override public String apiKey() { return KEY; }
            @Override public JSONObject health() { return new JSONObject().put("fixture",true); }
            @Override public JSONArray models() { return new JSONArray(); }
            @Override public JSONArray engines() { return new JSONArray(); }
            @Override public JobStore jobs() { return jobs; }
            @Override public ArtifactStore artifacts() { return artifacts; }
            @Override public InputUploads uploads() { return uploads.get(); }
            @Override public JSONObject submit(JSONObject request,String key) throws Exception { synchronized(artifacts) { return jobs.submit(InputSelection.prepare(artifacts,spec,request),key); } }
            @Override public void cancel(String id) throws Exception { jobs.cancel(id); }
            @Override public LocalHttp.Response text(String path,JSONObject request) throws Exception { return LocalApi.error(409,"fixture_only","No inference fixture"); }
        };
        byte[] bytes = wave(320000); JSONObject declaration = declaration(bytes);
        try (LocalHttp server = new LocalHttp("127.0.0.1",0,new LocalApi(runtime))) {
            int port = server.port();
            check(request(port,"POST","/v1/uploads",declaration.toString().getBytes(StandardCharsets.UTF_8),"application/json",null,Collections.emptyMap()).status == 401, "Creating an input upload requires the same Bearer authentication as inference");
            check(request(port,"POST","/v1/uploads",declaration.toString().getBytes(StandardCharsets.UTF_8),"application/json",KEY,Collections.singletonMap("Origin","https://example.invalid")).status == 403, "Browser origins cannot upload credentialed local media");
            check(json(port,"POST","/v1/uploads",DataFiles.copy(declaration).put("url","https://example.invalid/reference.wav")).status == 400, "Upload declarations never accept URLs or fetch remote files");
            check(json(port,"POST","/v1/uploads",DataFiles.copy(declaration).put("bytes",ArtifactStore.MAX_INPUT_BYTES+1)).status == 400, "Oversized declarations are rejected before allocating input storage");
            check(json(port,"POST","/v1/uploads",DataFiles.copy(declaration).put("bytes",1.5)).status == 400, "Fractional byte counts are rejected");
            check(json(port,"POST","/v1/uploads",DataFiles.copy(declaration).put("sha256","not-a-digest")).status == 400, "A valid expected SHA256 is required for API uploads");
            Reply created = json(port,"POST","/v1/uploads",declaration); String id = created.json().getString("id"), path = "/v1/uploads/"+id;
            check(created.status == 202 && !created.json().has("part") && created.json().getLong("received") == 0, "Creating a session exposes only its ID and committed offset, never a private path");
            check(json(port,"POST",path+"/complete",new JSONObject()).status == 409, "Incomplete uploads cannot be published");
            byte[] first = Arrays.copyOfRange(bytes,0,InputUploads.CHUNK_BYTES);
            check(request(port,"PUT",path,first,"text/plain",KEY,Collections.singletonMap("Upload-Offset","0")).status == 415, "Input chunks require the exact binary content type");
            check(request(port,"PUT",path,first,"application/octet-stream",KEY,Collections.singletonMap("Upload-Offset","1")).status == 409, "Out-of-order upload offsets are rejected");
            check(request(port,"PUT",path,new byte[InputUploads.CHUNK_BYTES+1],"application/octet-stream",KEY,Collections.singletonMap("Upload-Offset","0")).status == 413, "HTTP chunk buffering remains bounded at 256 KiB");
            Reply appended = request(port,"PUT",path,first,"application/octet-stream",KEY,Collections.singletonMap("Upload-Offset","0"));
            check(appended.status == 200 && appended.json().getInt("received") == first.length, "An authenticated binary chunk commits a durable byte offset");
            check(request(port,"PUT",path,first,"application/octet-stream",KEY,Collections.singletonMap("Upload-Offset","0")).json().getInt("received") == first.length, "A lost-response retry with identical bytes is idempotent");
            byte[] wrong = first.clone(); wrong[0] ^= 1;
            check(request(port,"PUT",path,wrong,"application/octet-stream",KEY,Collections.singletonMap("Upload-Offset","0")).status == 409, "A conflicting retried chunk cannot silently replace committed bytes");
            JSONObject privateIndex = new JSONObject(new String(Files.readAllBytes(root.resolve("uploads/uploads.json")),StandardCharsets.UTF_8));
            File part = artifacts.inputPart(id,privateIndex.getJSONObject("uploads").getJSONObject(id).getString("part"));
            try (FileOutputStream tail = new FileOutputStream(part,true)) { tail.write(new byte[]{9,9,9}); }
            File orphanDocument = artifacts.staging("input_" + String.join("",Collections.nCopies(32,"a")),"input"), orphanUpload = artifacts.staging("upload_" + String.join("",Collections.nCopies(32,"b")),"input");
            Files.write(orphanDocument.toPath(), new byte[]{1}); Files.write(orphanUpload.toPath(), new byte[]{2});
            uploads.set(new InputUploads(root.resolve("uploads").toFile(),artifacts));
            check(part.length() == first.length && json(port,"GET",path,null).json().getInt("received") == first.length, "Restart truncates uncommitted bytes and resumes at the durable offset");
            check(!orphanDocument.exists() && !orphanUpload.exists() && part.isFile(), "Startup removes only unregistered interrupted document/upload staging and preserves registered partial files");
            for (int offset=first.length;offset<bytes.length;offset+=InputUploads.CHUNK_BYTES) {
                byte[] chunk = Arrays.copyOfRange(bytes,offset,Math.min(bytes.length,offset+InputUploads.CHUNK_BYTES));
                Reply next = request(port,"PUT",path,chunk,"application/octet-stream",KEY,Collections.singletonMap("Upload-Offset",String.valueOf(offset)));
                if(next.status != 200) throw new AssertionError("Continuation failed "+next.status);
            }
            byte[] beforeCompletion = Files.readAllBytes(root.resolve("uploads/uploads.json"));
            Reply completed = json(port,"POST",path+"/complete",new JSONObject()); String artifactId = completed.json().getString("id");
            check(completed.status == 200 && completed.json().getString("sha256").equals(hash(bytes)) && completed.json().getJSONObject("metadata").getInt("durationMs")==20000, "Completion validates the entire SHA256 and actual PCM media before atomic publication");
            check(json(port,"POST",path+"/complete",new JSONObject()).json().getString("id").equals(artifactId) && artifacts.snapshot().length()==1, "Repeated completion returns the same immutable artifact without duplicate media");
            Files.write(root.resolve("uploads/uploads.json"),beforeCompletion); uploads.set(new InputUploads(root.resolve("uploads").toFile(),artifacts));
            check(json(port,"GET",path,null).json().getString("state").equals("completed") && json(port,"POST",path+"/complete",new JSONObject()).json().getString("id").equals(artifactId), "Restart reconciles a committed artifact after an interrupted session-metadata update");
            check(request(port,"GET","/v1/artifacts/"+artifactId+"/content",null,null,KEY,Collections.singletonMap("Range","bytes=0-43")).data.length==44, "Imported inputs reuse authenticated Range/HEAD media transfers");
            Reply job=json(port,"POST","/v1/jobs",task(artifactId)); String jobId=job.json().getString("id");
            check(job.status==202 && job.json().getJSONObject("request").getJSONArray("inputReceipts").getJSONObject(0).getString("sha256").equals(hash(bytes)), "API task submission freezes the same checked local input receipt");
            check(json(port,"DELETE","/v1/artifacts/"+artifactId,null).status==409, "API deletion respects persisted queued input references");
            json(port,"POST","/v1/jobs/"+jobId+"/cancel",new JSONObject());
            Reply retry=json(port,"POST","/v1/jobs/"+jobId+"/retry",new JSONObject());
            check(retry.status==202 && !retry.json().getString("id").equals(jobId) && retry.json().getJSONObject("request").getJSONArray("inputReceipts").length()==1, "Retry creates a new task and recomputes trusted input receipts");
            json(port,"POST","/v1/jobs/"+retry.json().getString("id")+"/cancel",new JSONObject());
            check(json(port,"DELETE",path,null).status==200 && artifacts.snapshot().length()==1, "Deleting a completed upload session keeps explicitly imported library media");
            check(json(port,"DELETE","/v1/artifacts/"+artifactId,null).status==200, "Unreferenced input deletion works after all consuming tasks finish/cancel");
            check(json(port,"POST","/v1/jobs/"+jobId+"/retry",new JSONObject()).status==400, "Retry with deleted input fails without implicit recreation/download");
            JSONObject bad=DataFiles.copy(declaration).put("sha256",hash(new byte[]{1})); String badId=json(port,"POST","/v1/uploads",bad).json().getString("id");
            for(int offset=0;offset<bytes.length;offset+=InputUploads.CHUNK_BYTES) uploads.get().append(badId,offset,Arrays.copyOfRange(bytes,offset,Math.min(bytes.length,offset+InputUploads.CHUNK_BYTES)));
            check(json(port,"POST","/v1/uploads/"+badId+"/complete",new JSONObject()).status==503 && artifacts.snapshot().length()==0, "Whole-file digest mismatch never publishes an imported artifact");
            json(port,"DELETE","/v1/uploads/"+badId,null);
            List<String> pending=new ArrayList<>(); for(int i=0;i<4;i++) pending.add(uploads.get().create(declaration).getString("id"));
            check(json(port,"POST","/v1/uploads",declaration).status==409, "Concurrent upload sessions have a hard bound");
            for(String pendingId:pending) uploads.get().remove(pendingId);
            check(uploads.get().snapshot().length()==0 && root.resolve("artifacts/staging").toFile().list().length==0, "Cancelling input uploads removes only their own private partial files");
            check(json(port,"GET","/v1/uploads/upload_missing",null).status==404, "Unknown upload IDs produce a structured not-found response");
        }
    }
    public static void main(String[] args) throws Exception {
        Path root=Paths.get(args[0]); Files.createDirectories(root.resolve("core")); Files.createDirectories(root.resolve("http")); core(root.resolve("core")); http(root.resolve("http"));
        System.out.println(new JSONObject().put("passed",checks.size()).put("checks",new JSONArray(checks)).put("actual_socket_io",true).put("actual_private_file_io",true).put("production_wav_validation",true).put("android_execution_tested",false).put("model_inference_tested",false).put("automatic_model_downloads",false));
    }
}
