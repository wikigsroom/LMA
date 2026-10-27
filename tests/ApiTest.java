package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Actual production API/socket/storage paths with explicit execution fixtures; no model inference. */
public final class ApiTest {
    private static final List<String> checks = new ArrayList<>();
    private static final String KEY = "host-api-test-secret";
    private static final AtomicInteger textClosed = new AtomicInteger();
    private static void check(boolean condition, String label) { if (!condition) throw new AssertionError(label); checks.add(label); }
    private static final class Reply {
        final int status; final byte[] bytes; final String range; final String mime;
        Reply(int status, byte[] bytes, String range, String mime) { this.status = status; this.bytes = bytes; this.range = range; this.mime = mime; }
        JSONObject json() { return new JSONObject(new String(bytes, StandardCharsets.UTF_8)); }
    }
    private static Reply request(int port, String method, String path, String payload, String key, Map<String, String> headers) throws Exception {
        HttpURLConnection connection = connect(port, method, path, payload, key, headers);
        try {
            int status = connection.getResponseCode(); InputStream in = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            ByteArrayOutputStream out = new ByteArrayOutputStream(); if (in != null) try (InputStream owned = in) { byte[] buffer = new byte[1024]; int n; while ((n = in.read(buffer)) >= 0) out.write(buffer, 0, n); }
            return new Reply(status, out.toByteArray(), connection.getHeaderField("Content-Range"), connection.getContentType());
        } finally { connection.disconnect(); }
    }
    private static HttpURLConnection connect(int port, String method, String path, String payload, String key, Map<String, String> headers) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        connection.setConnectTimeout(2000); connection.setReadTimeout(5000); connection.setRequestMethod(method);
        if (key != null) connection.setRequestProperty("Authorization", "Bearer " + key);
        for (Map.Entry<String, String> header : headers.entrySet()) connection.setRequestProperty(header.getKey(), header.getValue());
        if (payload != null) {
            byte[] bytes = payload.getBytes(StandardCharsets.UTF_8); connection.setDoOutput(true); connection.setRequestProperty("Content-Type", "application/json; charset=utf-8"); connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
        }
        return connection;
    }
    private static Reply request(int port, String method, String path, String payload) throws Exception { return request(port, method, path, payload, KEY, Collections.emptyMap()); }
    private static int raw(int port, String wire) throws Exception {
        try (Socket socket = new Socket("127.0.0.1", port)) {
            socket.setSoTimeout(3000); socket.getOutputStream().write(wire.getBytes(StandardCharsets.US_ASCII)); socket.getOutputStream().flush(); socket.shutdownOutput();
            String line = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.US_ASCII)).readLine();
            return line == null ? 0 : Integer.parseInt(line.split(" ")[1]);
        }
    }
    private static JSONObject task(String prompt) { return new JSONObject().put("bundleId", "fixture_bundle").put("type", "image.generate").put("input", new JSONObject().put("prompt", prompt)).put("parameters", new JSONObject()); }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); JobStore jobs = new JobStore(new File(root, "jobs"));
        ArtifactStore artifacts = new ArtifactStore(new File(root, "artifacts"), file -> new JSONObject().put("mime", "image/png").put("fixture", true));
        AtomicInteger submissions = new AtomicInteger();
        LocalApi.Runtime runtime = new LocalApi.Runtime() {
            @Override public String apiKey() { return KEY; }
            @Override public JSONObject health() { return new JSONObject().put("status", "ok").put("fixture", true); }
            @Override public JSONArray models() { return new JSONArray(); }
            @Override public JSONArray engines() { return new JSONArray(); }
            @Override public JobStore jobs() { return jobs; }
            @Override public ArtifactStore artifacts() { return artifacts; }
            @Override public JSONObject submit(JSONObject request, String key) throws Exception { submissions.incrementAndGet(); return jobs.submit(request, key); }
            @Override public void cancel(String id) throws Exception { jobs.cancel(id); }
            @Override public LocalHttp.Response text(String path, JSONObject request) throws Exception {
                JSONObject settings = new JSONObject().put("maxTokens", 123).put("context", 1024).put("temperature", 0.4);
                JSONObject normalized = TextRequest.normalize(path, request, "fixture_text", settings);
                if (!normalized.optBoolean("stream")) return LocalApi.json(200, normalized);
                return new LocalHttp.Response(200, "text/event-stream", -1, new LocalHttp.Body() {
                    @Override public void write(OutputStream out) throws Exception { out.write("data: {\"fixture\":\"首段\"}\n\n".getBytes(StandardCharsets.UTF_8)); out.flush(); Thread.sleep(50); out.write("data: [DONE]\n\n".getBytes(StandardCharsets.UTF_8)); out.flush(); }
                    @Override public void close() { textClosed.incrementAndGet(); }
                });
            }
        };
        LocalHttp server = new LocalHttp("127.0.0.1", 0, new LocalApi(runtime, 1000)); int port = server.port();
        try {
            Reply noKey = request(port, "GET", "/health", null, null, Collections.emptyMap());
            check(noKey.status == 401 && noKey.json().getJSONObject("error").getString("code").equals("invalid_api_key"), "Every health/API request requires a Bearer key");
            check(request(port, "GET", "/v1/models", null, "wrong", Collections.emptyMap()).status == 401, "Wrong keys cannot list models");
            check(request(port, "GET", "/health", null).json().getString("status").equals("ok"), "A zero-model gateway starts without downloading or loading assets");
            check(request(port, "GET", "/v1/models", null).json().getJSONArray("data").length() == 0, "The API can represent an empty local library");
            check(request(port, "GET", "/v1/engines", null).json().getJSONArray("data").length() == 0, "Only registered engine metadata is exposed");
            check(request(port, "GET", "/unknown", null).status == 404, "Unknown endpoints return a structured 404");
            check(request(port, "POST", "/health", "{}").status == 405, "Read-only endpoints reject mutations");
            check(raw(port, "GET /health HTTP/1.1\r\nHost: localhost\r\nOrigin: https://example.invalid\r\nAuthorization: Bearer " + KEY + "\r\n\r\n") == 403, "Authenticated browser origins are rejected without credentialed CORS");
            check(raw(port, "GET http://elsewhere/health HTTP/1.1\r\nHost: localhost\r\n\r\n") == 400, "The listener is not an HTTP forward proxy");
            check(raw(port, "POST /v1/jobs HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\n") == 400, "Duplicate framing headers cannot smuggle requests");
            check(raw(port, "POST /v1/jobs HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1\r\nTransfer-Encoding: chunked\r\n\r\n") == 501, "Unsupported chunked request bodies are rejected before body parsing");
            check(raw(port, "POST /v1/jobs HTTP/1.1\r\nHost: localhost\r\nContent-Length: 99999999\r\n\r\n") == 413, "Oversized bodies are rejected before allocation");
            check(raw(port, "POST /v1/jobs HTTP/1.1\r\nHost: localhost\r\n\r\n") == 411, "POST requests require an explicit bounded length");
            check(raw(port, "POST /v1/jobs HTTP/1.1\r\nHost: localhost\r\nContent-Length: 3\r\n\r\na") == 400, "Truncated request bodies never reach execution");
            check(raw(port, "GET /health HTTP/1.1\r\nHost: localhost\r\nX-Fill: " + String.join("", Collections.nCopies(17000, "x")) + "\r\n\r\n") == 431, "Header memory is bounded at 16 KiB");
            check(raw(port, "GET /health HTTP/1.1\nHost: localhost\n\n") == 400, "Ambiguous bare-LF header framing is rejected");
            check(raw(port, "GET /v1/events?after=1&after=2 HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer " + KEY + "\r\n\r\n") == 400, "Duplicate query parameters are rejected");
            check(request(port, "POST", "/v1/jobs", "{oops").status == 400 && submissions.get() == 0, "Malformed JSON is not submitted");
            check(request(port, "POST", "/v1/jobs", "{}{}").status == 400 && submissions.get() == 0, "Trailing JSON values cannot change the submitted object");
            check(request(port, "POST", "/v1/jobs", String.join("", Collections.nCopies(40, "["))).status == 400, "Deeply nested JSON is rejected before recursive parsing");
            check(raw(port, "POST /v1/jobs HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer " + KEY + "\r\nContent-Length: 2\r\nContent-Type: text/plain\r\n\r\n{}") == 415, "Mutation bodies require JSON content type");
            check(request(port, "POST", "/v1/jobs", task("fixture").put("allowUnmeasured", "true").toString()).status == 400, "A string cannot impersonate explicit consent to an unmeasured recipe");
            check(request(port, "POST", "/v1/jobs", task("fixture").put("parameters", "ignored settings").toString()).status == 400, "Malformed parameter objects fail instead of silently using defaults");
            check(request(port, "POST", "/v1/jobs", task("fixture").put("input", new JSONObject().put("prompt", 123)).toString()).status == 400, "Task prompts require actual text values");
            check(request(port, "POST", "/v1/jobs", task("fixture").put("input", new JSONObject().put("prompt", "fixture").put("negativePrompt", true)).toString()).status == 400, "Negative prompts cannot silently coerce other JSON types");
            check(request(port, "POST", "/v1/jobs", task("fixture").put("input", new JSONObject().put("prompt", "fixture").put("image_url", "https://example.invalid/input.png")).toString()).status == 400 && submissions.get() == 0, "Unsupported media inputs never reach execution or trigger a download");
            JSONObject payload = task("<script>fixture only</script> 中文"); Map<String, String> idem = Collections.singletonMap("Idempotency-Key", "one");
            Reply submitted = request(port, "POST", "/v1/jobs", payload.toString(), KEY, idem); String id = submitted.json().getString("id");
            check(submitted.status == 202 && submitted.json().getString("state").equals("queued"), "Submission acknowledges a durable queued job, not a fake result");
            check(request(port, "POST", "/v1/jobs", payload.toString(), KEY, idem).json().getString("id").equals(id), "Identical idempotent submissions retain one job identity");
            check(request(port, "POST", "/v1/jobs", task("different").toString(), KEY, idem).status == 409, "A reused idempotency key cannot change its request");
            check(jobs.lookup("one").getString("id").equals(id), "The real durable job store can recover an idempotency key");
            check(request(port, "GET", "/v1/jobs", null).json().getJSONArray("data").getJSONObject(0).getJSONObject("request").has("inputSummary"), "Job listings return bounded summaries instead of full prompts");
            Reply details = request(port, "GET", "/v1/jobs/" + id, null);
            check(details.mime.startsWith("application/json") && details.json().getJSONObject("request").getJSONObject("input").getString("prompt").equals(payload.getJSONObject("input").getString("prompt")), "Task details preserve escaped text as JSON");
            check(!details.json().has("token"), "Private execution ownership tokens never enter API responses");
            check(request(port, "GET", "/v1/jobs/job_missing", null).status == 404, "Missing task IDs return 404");
            check(request(port, "DELETE", "/v1/jobs/" + id, null).status == 409, "An active/queued job cannot be deleted before cancellation");
            Reply events = request(port, "GET", "/v1/jobs/" + id + "/events?after=0", null);
            long cursor = events.json().getLong("cursor"); check(events.json().getJSONArray("events").length() == 1, "JSON events expose durable monotonic cursor data");
            check(request(port, "GET", "/v1/events?after=NaN", null).status == 400, "Invalid event cursors are rejected");
            check(request(port, "POST", "/v1/jobs/" + id + "/cancel", "{}").json().getString("state").equals("cancelled"), "API cancellation mutates the same persistent job store");
            Map<String, String> sse = new HashMap<>(); sse.put("Accept", "text/event-stream"); sse.put("Last-Event-ID", String.valueOf(cursor));
            Reply streamed = request(port, "GET", "/v1/jobs/" + id + "/events", null, KEY, sse);
            String eventText = new String(streamed.bytes, StandardCharsets.UTF_8);
            check(streamed.mime.startsWith("text/event-stream") && eventText.contains("cancelled") && !eventText.contains("\"kind\":\"queued\""), "SSE resumes after Last-Event-ID and stops after a terminal job");
            check(request(port, "GET", "/v1/events?after=999", null, KEY, sse).status == 400, "Conflicting event cursor sources are rejected");
            Reply retry = request(port, "POST", "/v1/jobs/" + id + "/retry", "{}");
            check(retry.status == 202 && !retry.json().getString("id").equals(id), "Retry creates a new job instead of rewriting history");
            check(request(port, "POST", "/v1/jobs/" + retry.json().getString("id") + "/retry", "{}").status == 409, "A live job cannot be retried concurrently");
            File staged = artifacts.staging(id, "png"); byte[] content = "EXPLICIT TEST BYTES; NOT MODEL OUTPUT".getBytes(StandardCharsets.UTF_8); Files.write(staged.toPath(), content);
            JSONObject artifact = artifacts.commit(id, staged, new JSONObject().put("testFixture", true), () -> {}); String artifactId = artifact.getString("id");
            check(request(port, "GET", "/v1/artifacts", null).json().getJSONArray("data").length() == 1, "Artifact listings use the actual private result store");
            check(request(port, "GET", "/v1/artifacts/" + artifactId, null).json().getJSONObject("provenance").getBoolean("testFixture"), "Artifact details expose their original provenance");
            Reply full = request(port, "GET", "/v1/artifacts/" + artifactId + "/content", null);
            check(Arrays.equals(full.bytes, content), "Authenticated artifact downloads preserve exact original bytes");
            Reply partial = request(port, "GET", "/v1/artifacts/" + artifactId + "/content", null, KEY, Collections.singletonMap("Range", "bytes=2-8"));
            check(partial.status == 206 && Arrays.equals(partial.bytes, Arrays.copyOfRange(content, 2, 9)) && partial.range.equals("bytes 2-8/" + content.length), "Range downloads return bounded exact data and Content-Range");
            Reply suffix = request(port, "GET", "/v1/artifacts/" + artifactId + "/content", null, KEY, Collections.singletonMap("Range", "bytes=-4"));
            check(suffix.status == 206 && Arrays.equals(suffix.bytes, Arrays.copyOfRange(content, content.length - 4, content.length)), "Suffix ranges support media clients without loading the whole artifact");
            Reply invalidRange = request(port, "GET", "/v1/artifacts/" + artifactId + "/content", null, KEY, Collections.singletonMap("Range", "bytes=999-"));
            check(invalidRange.status == 416 && invalidRange.range.equals("bytes */" + content.length), "Unsatisfiable artifact ranges return 416 with the object size");
            check(request(port, "HEAD", "/v1/artifacts/" + artifactId + "/content", null).bytes.length == 0, "HEAD returns metadata without sending media bytes");
            check(request(port, "DELETE", "/v1/artifacts/" + artifactId, null).json().getBoolean("deleted"), "Completed reads and HEAD release deletion leases");
            check(request(port, "GET", "/v1/artifacts/" + artifactId, null).status == 404, "Deleted artifact metadata is no longer available");
            check(request(port, "GET", "/v1/artifacts/../../other/content", null).status >= 400, "Artifact paths cannot escape the private ID-based store");
            JSONObject chat = new JSONObject().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", "fixture"))).put("max_tokens", 999999).put("temperature", 99);
            JSONObject normalized = request(port, "POST", "/v1/chat/completions", chat.toString()).json();
            check(normalized.getInt("max_tokens") == 123 && normalized.getDouble("temperature") == 2, "External text requests clamp to the selected profile and sampling bounds");
            JSONObject defaults = request(port, "POST", "/v1/chat/completions", new JSONObject().put("messages", chat.getJSONArray("messages")).toString()).json();
            check(defaults.getInt("max_tokens") == 123 && defaults.getDouble("temperature") == 0.4 && defaults.getJSONArray("messages").length() == 1, "Saved text defaults apply without injecting the App system prompt");
            check(request(port, "POST", "/v1/chat/completions", new JSONObject(chat.toString()).put("model", "not_loaded").toString()).status == 409, "The API never silently loads or downloads a different requested text model");
            check(request(port, "POST", "/v1/chat/completions", new JSONObject(chat.toString()).put("tools", new JSONArray()).toString()).status == 400, "Unsupported text fields fail explicitly");
            JSONObject remote = new JSONObject(chat.toString()).put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", new JSONArray().put(new JSONObject().put("type", "image_url").put("image_url", "https://example.invalid/image.png")))));
            check(request(port, "POST", "/v1/chat/completions", remote.toString()).status == 400, "The text endpoint cannot fetch remote image/audio inputs");
            check(request(port, "POST", "/v1/chat/completions", new JSONObject(chat.toString()).put("n", 2).toString()).status == 400, "Multi-slot text generation is rejected");
            check(request(port, "POST", "/v1/chat/completions", new JSONObject(chat.toString()).put("stream", "true").toString()).status == 400, "String values cannot impersonate boolean generation flags");
            JSONObject completion = request(port, "POST", "/v1/completions", new JSONObject().put("prompt", "fixture").toString()).json();
            check(completion.getString("prompt").equals("fixture"), "Plain text completion requests use the same model profile");
            Reply textStream = request(port, "POST", "/v1/chat/completions", new JSONObject(chat.toString()).put("stream", true).toString());
            check(new String(textStream.bytes, StandardCharsets.UTF_8).contains("首段") && new String(textStream.bytes, StandardCharsets.UTF_8).contains("[DONE]"), "Streaming transport preserves UTF-8 and the original SSE frames");
            long deadline = System.currentTimeMillis() + 2000; while (textClosed.get() == 0 && System.currentTimeMillis() < deadline) Thread.sleep(10);
            check(textClosed.get() == 1, "Streaming completion closes its source and releases execution ownership");
            try (ServerSocket occupied = new ServerSocket(port, 1, InetAddress.getByName("127.0.0.1"))) { throw new AssertionError("Port unexpectedly reusable while listening"); }
            catch (BindException expected) { check(true, "A second listener cannot silently take the public API port"); }
            check(request(port, "DELETE", "/v1/jobs/" + id, null).json().getBoolean("deleted"), "Terminal history can be independently deleted");
            HttpURLConnection streamOne = connect(port, "GET", "/v1/events", null, KEY, Collections.singletonMap("Accept", "text/event-stream"));
            HttpURLConnection streamTwo = connect(port, "GET", "/v1/events", null, KEY, Collections.singletonMap("Accept", "text/event-stream"));
            try {
                check(streamOne.getResponseCode() == 200 && streamTwo.getResponseCode() == 200, "Two live event streams can coexist with control requests");
                check(request(port, "GET", "/v1/events", null, KEY, Collections.singletonMap("Accept", "text/event-stream")).status == 503, "Bounded event streams leave worker capacity for cancellation and polling");
            } finally { streamOne.disconnect(); streamTwo.disconnect(); }
        } finally { server.close(); }
        try (LocalHttp replacement = new LocalHttp("127.0.0.1", port, new LocalApi(runtime))) {
            check(request(port, "GET", "/health", null).status == 200, "Closing the gateway releases its port for a clean foreground-service restart");
        }
        System.out.println(new JSONObject().put("passed", checks.size()).put("checks", new JSONArray(checks)).put("actual_socket_io", true).put("execution", "explicit host fixtures; not Android or model inference").put("physical_device", false));
    }
}
