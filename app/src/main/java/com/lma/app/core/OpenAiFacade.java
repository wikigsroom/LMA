package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

/** Whole-file OpenAI image/speech subset and explicit, phone-local multimodal extensions. */
final class OpenAiFacade {
    private final LocalApi.Runtime runtime;
    private final Semaphore waits = new Semaphore(3), media;
    private final long waitMillis;
    OpenAiFacade(LocalApi.Runtime runtime, Semaphore media) { this(runtime, media, 120000); }
    OpenAiFacade(LocalApi.Runtime runtime, Semaphore media, long waitMillis) { this.runtime = runtime; this.media = media; this.waitMillis = waitMillis; }
    private ApiSubmissions.Submitter submitter(String endpoint) {
        return new ApiSubmissions.Submitter() {
            @Override public JSONObject freeze(JSONObject original) throws Exception {
                JSONObject mapped = endpoint.equals("/v1/images/generations") ? OpenAiRequests.image(original) : endpoint.equals("/v1/audio/speech") ? OpenAiRequests.speech(original, runtime) : original;
                return runtime.freezePublic(OpenAiRequests.nativeTask(mapped, runtime));
            }
            @Override public JSONObject lookup(String key) throws Exception { return runtime.jobs().lookup(key); }
            @Override public JSONObject submit(JSONObject frozen, String key) throws Exception { return runtime.submit(frozen, key); }
            @Override public JSONObject get(String id) throws Exception { return runtime.jobs().get(id); }
        };
    }
    LocalHttp.Response generate(String endpoint, JSONObject input, String key) throws Exception {
        if (!waits.tryAcquire()) throw new LocalHttp.Failure(503, "lma_sync_waiters_full", "Three synchronous requests are already waiting; use the async job interface");
        try {
            JSONObject job = runtime.submissions().submit(endpoint, key, input, submitter(endpoint)); String id = job.getString("id");
            long deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(waitMillis);
            while (!terminal(job.optString("state"))) {
                if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Synchronous wait stopped; the accepted task remains queryable");
                if (System.nanoTime() >= deadline) return error(504, "lma_wait_timeout", "The task continues on the phone. Query this job or retry with the same Idempotency-Key", id);
                Thread.sleep(200); job = runtime.jobs().get(id);
            }
            if (!job.getString("state").equals("succeeded")) return error(job.getString("state").equals("cancelled") ? 409 : 503, "lma_generation_" + job.getString("state"), safe(job.optString("error", "Local generation did not complete")), id);
            JSONArray outputs = job.getJSONArray("artifacts");
            if (outputs.length() != 1) return error(503, "lma_output_invalid", "Exactly one valid completed artifact is required", id);
            JSONObject artifact = runtime.artifacts().get(outputs.getString(0)); String mime = artifact.getJSONObject("metadata").getString("mime");
            if (!media.tryAcquire()) throw new LocalHttp.Failure(503, "too_many_artifact_readers", "At most three media transfers may run concurrently");
            InputStream stream;
            try { stream = runtime.artifacts().open(artifact.getString("id"), ByteRange.parse("", artifact.getLong("bytes"))); }
            catch (Exception error) { media.release(); throw error; }
            if (endpoint.equals("/v1/images/generations")) {
                byte[] bytes;
                try (InputStream owned = stream) {
                    if (!mime.equals("image/png") || artifact.getLong("bytes") > 16L * 1024 * 1024) return error(503, "lma_output_invalid", "The image facade requires a bounded PNG artifact", id);
                    ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] buffer = new byte[16384]; int size;
                    while ((size = owned.read(buffer)) != -1) { if (out.size() + size > 16 * 1024 * 1024) throw new IOException("Image artifact exceeds the facade limit"); out.write(buffer, 0, size); }
                    bytes = out.toByteArray();
                } finally { media.release(); }
                if (bytes.length < 24 || bytes[0] != (byte) 137 || bytes[1] != 'P' || bytes[2] != 'N' || bytes[3] != 'G') return error(503, "lma_output_invalid", "The completed artifact is not a valid PNG", id);
                JSONObject response = new JSONObject().put("created", job.getLong("createdAt") / 1000).put("data", new JSONArray().put(new JSONObject().put("b64_json", Base64.getEncoder().encodeToString(bytes))))
                        .put("x_lma", new JSONObject().put("job_id", id).put("effective_parameters", ApiCatalogue.publicParameters(job.getJSONObject("request").getJSONObject("parameters"))).put("adjustments", adjustments(job.getJSONObject("request").optJSONArray("adjustments"))));
                return LocalApi.json(200, response).header("X-LMA-Job-ID", id);
            }
            if (!mime.equals("audio/wav")) { try { stream.close(); } finally { media.release(); } return error(503, "lma_output_invalid", "The speech facade requires a real WAV artifact", id); }
            InputStream owned = stream;
            return LocalHttp.Response.stream(200, "audio/wav", artifact.getLong("bytes"), new FilterInputStream(owned) {
                private boolean closed;
                @Override public void close() throws IOException { if (!closed) { closed = true; try { super.close(); } finally { media.release(); } } }
            }).header("X-LMA-Job-ID", id);
        } finally { waits.release(); }
    }
    LocalHttp.Response route(LocalHttp.Request r, LocalApi api) throws Exception {
        String path = r.path.substring("/v1/lma".length());
        if (path.equals("/jobs/preflight")) {
            LocalApi.method(r, "POST"); JSONObject input = OpenAiRequests.nativeTask(LocalApi.body(r), runtime);
            JSONObject report = runtime.preflight(input); report.put("model", modelFor(input.getString("bundleId")));
            if (report.has("effectiveParameters")) report.put("effectiveParameters", ApiCatalogue.publicParameters(report.getJSONObject("effectiveParameters")));
            if (report.has("issues")) report.put("issues", redact(report.getJSONArray("issues")));
            if (report.has("warnings")) report.put("warnings", redact(report.getJSONArray("warnings")));
            return LocalApi.json(200, report);
        }
        if (path.equals("/jobs")) {
            LocalApi.method(r, "GET", "HEAD", "POST");
            if (r.method.equals("POST")) {
                JSONObject original = LocalApi.body(r), job = runtime.submissions().submit(r.path, r.header("idempotency-key"), original, submitter(r.path));
                return LocalApi.json(202, publicJob(job)).header("X-LMA-Job-ID", job.getString("id"));
            }
            LocalApi.noBody(r); JSONArray source = runtime.jobs().snapshot(), result = new JSONArray();
            for (int i = 0; i < source.length(); i++) if (TaskRequests.generation(source.getJSONObject(i).getJSONObject("request").getString("type"))) result.put(publicJob(source.getJSONObject(i)));
            return list(result);
        }
        if (path.startsWith("/jobs/")) {
            String[] parts = path.substring(6).split("/", -1); String id = LocalApi.id(parts[0]); JSONObject job = job(id);
            if (parts.length == 1) {
                LocalApi.method(r, "GET", "HEAD", "DELETE"); LocalApi.noBody(r);
                if (r.method.equals("DELETE")) { runtime.jobs().remove(id); runtime.jobsChanged(); return deleted(id); }
                return LocalApi.json(200, publicJob(job));
            }
            if (parts.length == 2 && parts[1].equals("cancel")) { LocalApi.method(r, "POST"); LocalApi.emptyOrObject(r); runtime.cancel(id); return LocalApi.json(200, publicJob(runtime.jobs().get(id))); }
            if (parts.length == 2 && parts[1].equals("retry")) {
                LocalApi.method(r, "POST"); LocalApi.emptyOrObject(r);
                if (!Arrays.asList("failed", "cancelled", "interrupted").contains(job.getString("state"))) throw new IllegalStateException("Only failed, cancelled or interrupted tasks may be retried");
                final JSONObject frozen = TaskRequests.replay(job.getJSONObject("request")); final ApiSubmissions.Submitter delegate = submitter(r.path);
                JSONObject original = new JSONObject().put("model", runtime.submissions().modelForJob(id, modelFor(frozen.getString("bundleId")))).put("retry_job", id);
                JSONObject retried = runtime.submissions().submit(r.path, r.header("idempotency-key"), original, new ApiSubmissions.Submitter() {
                    @Override public JSONObject freeze(JSONObject ignored) { return DataFiles.copy(frozen); }
                    @Override public JSONObject lookup(String key) throws Exception { return delegate.lookup(key); }
                    @Override public JSONObject submit(JSONObject request, String key) throws Exception { return delegate.submit(request, key); }
                    @Override public JSONObject get(String id) throws Exception { return delegate.get(id); }
                });
                return LocalApi.json(202, publicJob(retried)).header("X-LMA-Job-ID", retried.getString("id"));
            }
            if (parts.length == 2 && parts[1].equals("events")) { LocalApi.method(r, "GET"); LocalApi.noBody(r); return api.eventResponse(r, id); }
            if (parts.length >= 2 && parts[1].equals("audio")) {
                LocalApi.method(r, "GET", "HEAD"); LocalApi.noBody(r);
                if (parts.length == 2) { String after = r.query("after"); if (!after.isEmpty() && !after.matches("[0-9]{1,4}")) throw new IllegalArgumentException("Invalid audio cursor"); return LocalApi.json(200, runtime.audioStreams().get(id, after.isEmpty() ? 0 : Integer.parseInt(after))); }
                if (parts.length == 3 && parts[2].matches("[0-9]{1,4}")) return LocalHttp.Response.bytes(200, "application/octet-stream", runtime.audioStreams().read(id, Integer.parseInt(parts[2]))).header("X-Audio-Format", "pcm_s16le");
            }
        }
        if (path.equals("/uploads")) {
            LocalApi.method(r, "GET", "HEAD", "POST");
            if (r.method.equals("POST")) { JSONObject input = LocalApi.body(r); OpenAiRequests.fields(input, "model", "name", "bytes", "sha256"); runtime.model(input.getString("model")); input.remove("model"); return LocalApi.json(202, upload(runtime.uploads().create(input))); }
            LocalApi.noBody(r); JSONArray source = runtime.uploads().snapshot(), result = new JSONArray(); for (int i = 0; i < source.length(); i++) result.put(upload(source.getJSONObject(i))); return list(result);
        }
        if (path.startsWith("/uploads/")) {
            String[] parts = path.substring(9).split("/", -1); String id = LocalApi.id(parts[0]); try { runtime.uploads().get(id); } catch (IllegalArgumentException absent) { throw new LocalHttp.Failure(404, "upload_not_found", "Unknown input upload"); }
            if (parts.length == 1) {
                LocalApi.method(r, "GET", "HEAD", "PUT", "DELETE");
                if (r.method.equals("PUT")) {
                    if (!r.header("content-type").equalsIgnoreCase("application/octet-stream")) throw new LocalHttp.Failure(415, "binary_required", "Use application/octet-stream");
                    if (!r.header("upload-offset").matches("[0-9]{1,10}")) throw new IllegalArgumentException("Invalid Upload-Offset");
                    return LocalApi.json(200, upload(runtime.uploads().append(id, Long.parseLong(r.header("upload-offset")), r.body)));
                }
                LocalApi.noBody(r); if (r.method.equals("DELETE")) { runtime.uploads().remove(id); return deleted(id); } return LocalApi.json(200, upload(runtime.uploads().get(id)));
            }
            if (parts.length == 2 && parts[1].equals("complete")) { LocalApi.method(r, "POST"); LocalApi.emptyOrObject(r); JSONObject artifact = runtime.uploads().complete(id, () -> { if (Thread.currentThread().isInterrupted()) throw new IOException("Input finalization stopped"); }); return LocalApi.json(200, publicArtifact(artifact)); }
        }
        if (path.equals("/artifacts")) { LocalApi.method(r, "GET", "HEAD"); LocalApi.noBody(r); JSONArray source = runtime.artifacts().snapshot(), result = new JSONArray(); for (int i = 0; i < source.length(); i++) result.put(publicArtifact(source.getJSONObject(i))); return list(result); }
        if (path.startsWith("/artifacts/")) {
            String[] parts = path.substring(11).split("/", -1); String id = LocalApi.id(parts[0]); JSONObject artifact; try { artifact = runtime.artifacts().get(id); } catch (IllegalArgumentException absent) { throw new LocalHttp.Failure(404, "artifact_not_found", "Unknown artifact"); }
            if (parts.length == 1) { LocalApi.method(r, "GET", "HEAD", "DELETE"); LocalApi.noBody(r); if (r.method.equals("DELETE")) { runtime.artifacts().remove(id); return deleted(id); } return LocalApi.json(200, publicArtifact(artifact)); }
            if (parts.length == 2 && parts[1].equals("content")) { LocalApi.method(r, "GET", "HEAD"); LocalApi.noBody(r); return api.content(r, artifact); }
        }
        throw new LocalHttp.Failure(404, "unknown_endpoint", "Unknown LMA extension endpoint");
    }
    private JSONObject job(String id) throws Exception {
        JSONObject job;
        try { job = runtime.jobs().get(id); } catch (IllegalArgumentException missing) { throw new LocalHttp.Failure(404, "job_not_found", "Unknown generation task"); }
        if (!TaskRequests.generation(job.getJSONObject("request").getString("type"))) throw new LocalHttp.Failure(404, "job_not_found", "Not a published generation task"); return job;
    }
    private String modelFor(String bundle) throws Exception {
        JSONArray models = runtime.models(); for (int i = 0; i < models.length(); i++) if (models.getJSONObject(i).optString("bundle_id").equals(bundle)) return models.getJSONObject(i).getString("id"); return bundle;
    }
    JSONObject publicJob(JSONObject job) throws Exception {
        JSONObject request = job.getJSONObject("request"); JSONArray source = job.optJSONArray("artifacts"), outputs = new JSONArray();
        if (source != null) for (int i = 0; i < source.length(); i++) { try { outputs.put(publicArtifact(runtime.artifacts().get(source.getString(i)))); } catch (IllegalArgumentException removed) { /* A removed output must not be fabricated. */ } }
        JSONObject result = new JSONObject().put("id", job.getString("id")).put("object", "lma.job").put("model", runtime.submissions().modelForJob(job.getString("id"), modelFor(request.getString("bundleId"))))
                .put("type", request.getString("type")).put("state", job.getString("state")).put("stage", job.optString("stage")).put("progress", job.has("progress") ? job.get("progress") : JSONObject.NULL).put("outputs", outputs)
                .put("effective_parameters", ApiCatalogue.publicParameters(request.optJSONObject("parameters") == null ? new JSONObject() : request.getJSONObject("parameters"))).put("adjustments", adjustments(request.optJSONArray("adjustments")));
        String error = job.optString("error"); return result.put("error", error.isEmpty() ? JSONObject.NULL : detail("lma_generation_" + job.getString("state"), safe(error)));
    }
    private static JSONObject publicArtifact(JSONObject artifact) throws Exception {
        JSONObject metadata = artifact.getJSONObject("metadata"), dimensions = new JSONObject();
        for (String key : Arrays.asList("width", "height", "frames", "fps", "durationMs", "sampleRate", "channels", "vertices", "triangles")) if (metadata.has(key)) dimensions.put(key, metadata.get(key));
        return new JSONObject().put("id", artifact.getString("id")).put("object", "lma.artifact").put("mime", metadata.getString("mime")).put("bytes", artifact.getLong("bytes")).put("sha256", artifact.getString("sha256")).put("metadata", dimensions).put("content_path", "/v1/lma/artifacts/" + artifact.getString("id") + "/content");
    }
    private static JSONObject upload(JSONObject item) throws Exception { JSONObject result = new JSONObject().put("id", item.getString("id")).put("object", "lma.upload").put("bytes", item.getLong("bytes")).put("received", item.getLong("received")).put("state", item.getString("state")); if (item.has("artifactId")) result.put("artifact_id", item.getString("artifactId")); return result; }
    private static JSONArray adjustments(JSONArray source) throws Exception {
        JSONArray result = new JSONArray(); if (source != null) for (int i = 0; i < source.length(); i++) { JSONObject item = source.getJSONObject(i); if (ApiCatalogue.publicField(item.optString("field", item.optString("key")))) result.put(item); } return result;
    }
    private static JSONArray redact(JSONArray source) throws Exception { JSONArray result = new JSONArray(); for (int i = 0; i < source.length(); i++) { JSONObject item = DataFiles.copy(source.getJSONObject(i)); if (item.has("message")) item.put("message", safe(item.getString("message"))); result.put(item); } return result; }
    private static boolean terminal(String state) { return Arrays.asList("succeeded", "failed", "cancelled", "interrupted").contains(state); }
    private static JSONObject detail(String code, String message) throws Exception { return new JSONObject().put("message", message).put("type", "local_execution_error").put("param", JSONObject.NULL).put("code", code); }
    private static LocalHttp.Response error(int status, String code, String message, String id) throws Exception { return LocalApi.json(status, new JSONObject().put("error", detail(code, message)).put("x_lma", new JSONObject().put("job_id", id))).header("X-LMA-Job-ID", id); }
    static String safe(String message) { String value = message.replaceAll("(?:/(?:data|sdcard|storage|system|apex)/|[A-Za-z]:[\\\\/])[^\\s\\\"]+", "[local file]"); return value.substring(0, Math.min(800, value.length())); }
    private static LocalHttp.Response list(JSONArray values) throws Exception { return LocalApi.json(200, new JSONObject().put("object", "list").put("data", values)); }
    private static LocalHttp.Response deleted(String id) throws Exception { return LocalApi.json(200, new JSONObject().put("id", id).put("deleted", true)); }
}
