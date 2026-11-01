package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

/** Authenticated data-only API. The Android adapter shares the UI's actual stores and executor. */
public final class LocalApi implements LocalHttp.Handler {
    public interface Runtime {
        String apiKey();
        JSONObject health() throws Exception;
        JSONArray models() throws Exception;
        default JSONObject catalogue() throws Exception { return new JSONObject().put("object", "list").put("data", models()); }
        default JSONObject model(String id) throws Exception {
            ModelBundle.key(id); JSONArray models = models();
            for (int i = 0; i < models.length(); i++) if (models.getJSONObject(i).getString("id").equals(id)) return models.getJSONObject(i);
            throw new LocalHttp.Failure(404, "lma_model_unavailable", "Unknown published local model");
        }
        default JSONObject capabilities() throws Exception { throw new LocalHttp.Failure(503, "lma_capabilities_unavailable", "Local capabilities are not ready"); }

        default ApiSubmissions submissions() throws Exception { throw new IOException("API submission storage is unavailable"); }
        default JSONObject freezePublic(JSONObject request) throws Exception { return TaskInput.validate(request); }
        default String adapter(String id) throws Exception { throw new LocalHttp.Failure(404, "lma_adapter_unavailable", "Unknown installed local adapter"); }
        JSONArray engines() throws Exception;
        JobStore jobs() throws Exception;
        ArtifactStore artifacts() throws Exception;
        default AudioStreams audioStreams() throws Exception { throw new IOException("Audio previews are unavailable"); }
        default TaskDrafts drafts() throws Exception { throw new IllegalStateException("Task drafts are unavailable"); }
        default void draftsChanged() {}
        default void jobsChanged() {}
        default InputUploads uploads() throws Exception { throw new IllegalStateException("Input uploads are unavailable"); }
        default JSONObject preflight(JSONObject request) throws Exception { throw new IllegalStateException("Task preflight is unavailable"); }
        JSONObject submit(JSONObject request, String idempotencyKey) throws Exception;
        void cancel(String id) throws Exception;
        LocalHttp.Response text(String path, JSONObject request) throws Exception;
    }
    private final Runtime runtime;
    private final OpenAiFacade facade;
    private final Semaphore events = new Semaphore(2), media = new Semaphore(3);
    private final long eventLifetimeMillis;
    public LocalApi(Runtime runtime) { this(runtime, 120000); }
    public LocalApi(Runtime runtime, long eventLifetimeMillis) {
        if (eventLifetimeMillis < 1 || eventLifetimeMillis > 120000) throw new IllegalArgumentException("Invalid event stream lifetime");
        this.runtime = runtime; this.eventLifetimeMillis = eventLifetimeMillis; this.facade = new OpenAiFacade(runtime, media);
    }
    @Override public LocalHttp.Response handle(LocalHttp.Request request) throws Exception {
        try {
            String key = runtime.apiKey();
            if (key.isEmpty() || !MessageDigest.isEqual(("Bearer " + key).getBytes(StandardCharsets.UTF_8), request.header("authorization").getBytes(StandardCharsets.UTF_8)))
                return error(401, "invalid_api_key", "A valid LMA Bearer key is required").header("WWW-Authenticate", "Bearer realm=\"LMA\"");
            // Browser UI uses its native bridge. No credentialed CORS or multipart upload routes.
            if (request.headers.containsKey("origin")) throw new LocalHttp.Failure(403, "browser_origin_rejected", "Use a native API client; browser origins are not enabled");
            return route(request);
        } catch (LocalHttp.Failure error) { return error(error.status, error.code, error.getMessage()); }
        catch (IllegalArgumentException | org.json.JSONException error) { return error(400, "invalid_request", safe(error)); }
        catch (IllegalStateException error) { return error(409, "local_state_conflict", safe(error)); }
        catch (IOException error) { return error(503, "local_resource_unavailable", safe(error)); }
        catch (Exception error) { return error(500, "local_execution_error", "The local operation failed; inspect the App status"); }
    }
    private LocalHttp.Response route(LocalHttp.Request r) throws Exception {
        String path = r.path;
        if (path.equals("/health")) { method(r, "GET", "HEAD"); noBody(r); return json(200, runtime.health()); }
        if (path.equals("/v1/models")) { method(r, "GET", "HEAD"); noBody(r); return cached(r, runtime.catalogue()); }
        if (path.startsWith("/v1/models/")) { method(r, "GET", "HEAD"); noBody(r); return cached(r, runtime.model(id(path.substring("/v1/models/".length())))); }
        if (path.equals("/v1/capabilities") || path.equals("/v1/lma/capabilities")) { method(r, "GET", "HEAD"); noBody(r); return cached(r, runtime.capabilities()); }
        if (path.equals("/v1/idempotency/lookup")) { method(r, "POST"); JSONObject input = body(r); if (input.length() != 1) throw new IllegalArgumentException("Only the key field is accepted"); JSONObject found = runtime.jobs().lookup(input.getString("key")); return json(200, new JSONObject().put("found", found != null).put("job", found == null ? JSONObject.NULL : found)); }
        if (path.equals("/v1/images/generations") || path.equals("/v1/audio/speech")) { method(r, "POST"); return facade.generate(path, body(r), r.header("idempotency-key")); }
        if (path.equals("/v1/images/edits")) throw new LocalHttp.Failure(400, "lma_image_edit_unavailable", "No installed adapter advertises the OpenAI multipart image-edit profile; use declared local input roles with /v1/lma/jobs");
        if (path.startsWith("/v1/lma/")) return facade.route(r, this);
        if (path.equals("/v1/engines")) { method(r, "GET", "HEAD"); noBody(r); return list(runtime.engines()); }
        if (path.equals("/v1/chat/completions") || path.equals("/v1/completions")) { method(r, "POST"); return runtime.text(path, body(r)); }
        if (path.equals("/v1/drafts")) {
            method(r, "GET", "HEAD", "POST");
            if (r.method.equals("POST")) { JSONObject input = body(r), saved = runtime.drafts().save(input.getJSONObject("request"), TaskDrafts.revision(input)); runtime.draftsChanged(); return json(200, saved); }
            noBody(r); return list(runtime.drafts().summaries());
        }
        if (path.startsWith("/v1/drafts/")) {
            String[] parts = path.substring("/v1/drafts/".length()).split("/", -1); String id = id(parts[0]);
            JSONObject draft;
            try { draft = runtime.drafts().get(id); } catch (IllegalArgumentException absent) { throw new LocalHttp.Failure(404, "draft_not_found", "Unknown task draft"); }
            if (parts.length == 1) { method(r, "GET", "HEAD"); noBody(r); return json(200, draft); }
            if (parts.length == 2 && parts[1].equals("delete")) { method(r, "POST"); runtime.drafts().remove(id, TaskDrafts.revision(body(r))); runtime.draftsChanged(); return json(200, new JSONObject().put("deleted", true).put("bundleId", id)); }
        }
        if (path.equals("/v1/jobs/preflight")) { method(r, "POST"); return json(200, runtime.preflight(body(r))); }
        if (path.equals("/v1/jobs/history")) { method(r, "GET", "HEAD"); noBody(r); return json(200, runtime.jobs().historyPlan()); }
        if (path.equals("/v1/jobs/history/clear")) { method(r, "POST"); JSONObject result = runtime.jobs().clearHistory(body(r)); runtime.jobsChanged(); return json(200, result); }
        if (path.equals("/v1/jobs")) {
            method(r, "GET", "HEAD", "POST");
            if (r.method.equals("POST")) return json(202, runtime.submit(TaskInput.validate(body(r)), r.header("idempotency-key")));
            noBody(r); return list(runtime.jobs().summaries());
        }
        if (path.equals("/v1/events")) { method(r, "GET"); noBody(r); return eventResponse(r, r.query("job_id")); }
        if (path.startsWith("/v1/jobs/")) {
            String[] parts = path.substring("/v1/jobs/".length()).split("/", -1); String id = id(parts[0]);
            JSONObject job = job(id);
            if (parts.length >= 2 && parts[1].equals("audio")) {
                method(r, "GET", "HEAD"); noBody(r);
                if (parts.length == 2) { String after = r.query("after"); if (!after.isEmpty() && !after.matches("[0-9]{1,4}")) throw new IllegalArgumentException("Use a numeric audio cursor"); return json(200, runtime.audioStreams().get(id, after.isEmpty() ? 0 : Integer.parseInt(after))); }
                if (parts.length == 3 && parts[2].matches("[0-9]{1,4}")) { byte[] pcm = runtime.audioStreams().read(id, Integer.parseInt(parts[2])); return LocalHttp.Response.bytes(200, "application/octet-stream", pcm).header("Cache-Control", "no-store").header("X-Audio-Format", "pcm_s16le"); }
                throw new LocalHttp.Failure(404, "audio_chunk_not_found", "Unknown audio preview chunk");
            }
            if (parts.length == 1) {
                method(r, "GET", "HEAD", "DELETE"); noBody(r);
                if (r.method.equals("DELETE")) { runtime.jobs().remove(id); runtime.jobsChanged(); return json(200, new JSONObject().put("deleted", true).put("id", id)); }
                return json(200, job);
            }
            if (parts.length == 2 && parts[1].equals("request")) { method(r, "GET", "HEAD"); noBody(r); return json(200, TaskRequests.editable(job.getJSONObject("request"))); }
            if (parts.length == 2 && parts[1].equals("events")) { method(r, "GET"); noBody(r); return eventResponse(r, id); }
            if (parts.length == 2 && parts[1].equals("cancel")) {
                method(r, "POST"); emptyOrObject(r); runtime.cancel(id); return json(200, runtime.jobs().get(id));
            }
            if (parts.length == 2 && parts[1].equals("retry")) {
                method(r, "POST"); emptyOrObject(r);
                if (!Arrays.asList("failed", "cancelled", "interrupted").contains(job.getString("state"))) throw new IllegalStateException("Only failed, cancelled or interrupted jobs may be retried");
                JSONObject original = TaskRequests.replay(job.getJSONObject("request"));
                return json(202, runtime.submit(original, r.header("idempotency-key")));
            }
        }
        if (path.equals("/v1/uploads")) {
            method(r, "GET", "HEAD", "POST");
            if (r.method.equals("POST")) return json(202, runtime.uploads().create(body(r)));
            noBody(r); return list(runtime.uploads().snapshot());
        }
        if (path.startsWith("/v1/uploads/")) {
            String[] parts = path.substring("/v1/uploads/".length()).split("/", -1); String id = id(parts[0]);
            try { runtime.uploads().get(id); } catch (IllegalArgumentException absent) { throw new LocalHttp.Failure(404, "upload_not_found", "Unknown input upload ID"); }
            if (parts.length == 1) {
                method(r, "GET", "HEAD", "DELETE", "PUT");
                if (r.method.equals("PUT")) {
                    if (!r.header("content-type").equalsIgnoreCase("application/octet-stream")) throw new LocalHttp.Failure(415, "binary_required", "Use application/octet-stream for an input chunk");
                    String offset = r.header("upload-offset");
                    if (!offset.matches("[0-9]{1,10}")) throw new IllegalArgumentException("Use a numeric Upload-Offset equal to received");
                    return json(200, runtime.uploads().append(id, Long.parseLong(offset), r.body));
                }
                noBody(r);
                if (r.method.equals("DELETE")) { runtime.uploads().remove(id); return json(200, new JSONObject().put("deleted", true).put("id", id)); }
                return json(200, runtime.uploads().get(id));
            }
            if (parts.length == 2 && parts[1].equals("complete")) {
                method(r, "POST"); emptyOrObject(r);
                JSONObject artifact = runtime.uploads().complete(id, () -> { if (Thread.currentThread().isInterrupted()) throw new IOException("Input upload finalization was stopped"); });
                return json(200, artifact);
            }
        }
        if (path.equals("/v1/artifacts")) { method(r, "GET", "HEAD"); noBody(r); return list(runtime.artifacts().snapshot()); }
        if (path.startsWith("/v1/artifacts/")) {
            String[] parts = path.substring("/v1/artifacts/".length()).split("/", -1); String id = id(parts[0]);
            JSONObject artifact = artifact(id);
            if (parts.length == 1) {
                method(r, "GET", "HEAD", "DELETE"); noBody(r);
                if (r.method.equals("DELETE")) { runtime.artifacts().remove(id); return json(200, new JSONObject().put("deleted", true).put("id", id)); }
                return json(200, artifact);
            }
            if (parts.length == 2 && parts[1].equals("request")) { method(r, "GET", "HEAD"); noBody(r); return json(200, TaskRequests.fromArtifact(artifact)); }
            if (parts.length == 2 && parts[1].equals("content")) { method(r, "GET", "HEAD"); noBody(r); return content(r, artifact); }
        }
        throw new LocalHttp.Failure(404, "unknown_endpoint", "Unknown local API endpoint");
    }
    private static LocalHttp.Response cached(LocalHttp.Request request, JSONObject value) throws Exception {
        String etag = "\"" + ApiCatalogue.hash(value) + "\"", condition = request.header("if-none-match"); boolean match = false;
        for (String candidate : condition.split(",")) { candidate = candidate.trim(); if (candidate.startsWith("W/")) candidate = candidate.substring(2); if (candidate.equals("*") || candidate.equals(etag)) match = true; }
        return (match ? LocalHttp.Response.bytes(304, "application/json", new byte[0]) : json(200, value)).header("ETag", etag).header("Cache-Control", "private, no-cache");
    }
    private JSONObject job(String id) throws Exception {
        try { return runtime.jobs().get(id); }
        catch (IllegalArgumentException missing) { throw new LocalHttp.Failure(404, "job_not_found", "Unknown task ID"); }
    }
    private JSONObject artifact(String id) throws Exception {
        try { return runtime.artifacts().get(id); }
        catch (IllegalArgumentException missing) { throw new LocalHttp.Failure(404, "artifact_not_found", "Unknown artifact ID"); }
    }
    LocalHttp.Response content(LocalHttp.Request request, JSONObject artifact) throws Exception {
        long bytes = artifact.getLong("bytes"); ByteRange range;
        String etag = "\"" + artifact.getString("sha256") + "\"";
        if (request.header("if-none-match").equals(etag)) return LocalHttp.Response.bytes(304, artifact.getJSONObject("metadata").getString("mime"), new byte[0]).header("ETag", etag);
        String requestedRange = request.header("range"), ifRange = request.header("if-range");
        if (!ifRange.isEmpty() && !ifRange.equals(etag)) requestedRange = "";
        try { range = ByteRange.parse(requestedRange, bytes); }
        catch (IOException error) { return error(416, "invalid_range", "Request one satisfiable byte range").header("Content-Range", "bytes */" + bytes); }
        String id = artifact.getString("id");
        if (!media.tryAcquire()) throw new LocalHttp.Failure(503, "too_many_artifact_readers", "At most three concurrent artifact transfers are allowed");
        InputStream in;
        try { in = runtime.artifacts().open(id, range); }
        catch (Exception error) { media.release(); throw error; }
        LocalHttp.Response response = LocalHttp.Response.stream(range.partial ? 206 : 200, artifact.getJSONObject("metadata").getString("mime"), range.length, new FilterInputStream(in) {
            private boolean closed;
            @Override public void close() throws IOException { if (!closed) { closed = true; try { super.close(); } finally { media.release(); } } }
        }).header("Accept-Ranges", "bytes").header("ETag", "\"" + artifact.getString("sha256") + "\"");
        if (range.partial) response.header("Content-Range", range.contentRange(bytes));
        return response;
    }
    LocalHttp.Response eventResponse(LocalHttp.Request request, String jobId) throws Exception {
        if (!jobId.isEmpty()) job(jobId);
        String query = request.query("after"), header = request.header("last-event-id");
        long after = cursor(query.isEmpty() ? header : query);
        if (!header.isEmpty() && !query.isEmpty() && after != cursor(header)) throw new IllegalArgumentException("after and Last-Event-ID disagree");
        if (!request.header("accept").contains("text/event-stream")) return json(200, runtime.jobs().events(after, jobId));
        if (!events.tryAcquire()) throw new LocalHttp.Failure(503, "too_many_event_streams", "At most two concurrent event streams are allowed; use JSON polling");
        return new LocalHttp.Response(200, "text/event-stream; charset=utf-8", -1, new LocalHttp.Body() {
            private boolean closed;
            @Override public void write(OutputStream out) throws Exception {
                long current = after, started = System.nanoTime(), heartbeat = 0;
                while (System.nanoTime() - started < TimeUnit.MILLISECONDS.toNanos(eventLifetimeMillis)) {
                    JSONObject update = runtime.jobs().events(current, jobId); JSONArray data = update.getJSONArray("events");
                    if (update.getBoolean("truncated")) frame(out, "event: reset\ndata: " + new JSONObject().put("truncated", true).put("cursor", update.getLong("cursor")) + "\n\n");
                    for (int i = 0; i < data.length(); i++) {
                        JSONObject event = data.getJSONObject(i);
                        frame(out, "id: " + event.getLong("sequence") + "\nevent: job\ndata: " + event + "\n\n");
                    }
                    current = update.getLong("cursor");
                    if (System.nanoTime() - heartbeat > TimeUnit.SECONDS.toNanos(10)) { frame(out, ": heartbeat\n\n"); heartbeat = System.nanoTime(); }
                    if (!jobId.isEmpty() && Arrays.asList("succeeded", "failed", "cancelled", "interrupted").contains(job(jobId).getString("state"))) return;
                    Thread.sleep(250);
                }
            }
            @Override public void close() { if (!closed) { closed = true; events.release(); } }
        }).header("X-Accel-Buffering", "no");
    }
    private static void frame(OutputStream out, String frame) throws IOException { out.write(frame.getBytes(StandardCharsets.UTF_8)); out.flush(); }
    private static long cursor(String value) {
        if (value.isEmpty()) return 0;
        if (!value.matches("[0-9]{1,18}")) throw new IllegalArgumentException("Invalid event cursor"); return Long.parseLong(value);
    }
    static String id(String id) { ModelBundle.key(id); return id; }
    static void method(LocalHttp.Request r, String... methods) throws LocalHttp.Failure {
        if (!Arrays.asList(methods).contains(r.method)) throw new LocalHttp.Failure(405, "method_not_allowed", "This endpoint does not accept " + r.method);
    }
    static void noBody(LocalHttp.Request request) throws LocalHttp.Failure { if (request.body.length != 0) throw new LocalHttp.Failure(400, "unexpected_body", "This request must have an empty body"); }
    static void emptyOrObject(LocalHttp.Request request) throws Exception { if (request.body.length > 0 && body(request).length() != 0) throw new IllegalArgumentException("This action only accepts an empty JSON object"); }
    public static JSONObject body(LocalHttp.Request request) throws Exception {
        if (!request.header("content-type").toLowerCase(Locale.ROOT).matches("application/json(?:\\s*;\\s*charset=utf-8)?")) throw new LocalHttp.Failure(415, "json_required", "Use Content-Type: application/json; charset=utf-8");
        String text = request.utf8(); int depth = 0; boolean quoted = false, escape = false;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (quoted) { if (escape) escape = false; else if (c == '\\') escape = true; else if (c == '"') quoted = false; }
            else if (c == '"') quoted = true;
            else if (c == '{' || c == '[') { if (++depth > 32) throw new IllegalArgumentException("JSON nesting exceeds 32 levels"); }
            else if (c == '}' || c == ']') depth--;
        }
        org.json.JSONTokener tokener = new org.json.JSONTokener(text);
        Object parsed = tokener.nextValue();
        if (!(parsed instanceof JSONObject) || tokener.nextClean() != 0) throw new IllegalArgumentException("Use one JSON object without trailing content");
        return (JSONObject) parsed;
    }
    private static LocalHttp.Response list(JSONArray data) throws org.json.JSONException { return json(200, new JSONObject().put("object", "list").put("data", data)); }
    public static LocalHttp.Response json(int status, JSONObject data) { return LocalHttp.Response.bytes(status, "application/json; charset=utf-8", data.toString().getBytes(StandardCharsets.UTF_8)); }
    public static LocalHttp.Response error(int status, String code, String message) throws org.json.JSONException { return json(status, new JSONObject().put("error", new JSONObject().put("code", code).put("message", message).put("param", JSONObject.NULL).put("type", "lma_local_error"))); }
    private static String safe(Exception error) { String message = error.getMessage(); return message == null ? "Invalid local operation" : OpenAiFacade.safe(message); }
}
