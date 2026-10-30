package com.lma.app;

import com.sun.net.httpserver.*;
import com.lma.app.core.*;
import java.io.*;
import java.net.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import javax.net.ssl.*;
import org.json.*;

/** Runs production backend Java against real HTTPS sockets and real child processes. */
public final class BackendTest {
    private static final List<String> passed = new ArrayList<>();
    private static final List<Downloads> transfers = new ArrayList<>();
    private static final List<ApiHost> gateways = new ArrayList<>();
    private static final List<EngineHost> engines = new ArrayList<>();
    private static final List<ChatRunner> chats = new ArrayList<>();
    private static final List<LmaApp> applications = new ArrayList<>();
    private static Path root, work, assets, libraries;
    private static HttpsServer https;
    private static LocalHttp redirectTrap;
    private static final AtomicInteger inferenceRedirects = new AtomicInteger();
    private static SSLServerSocket truncatedServer;
    private static ExecutorService httpWorkers;
    private static String base;
    private static String truncatedUrl;
    private static byte[] payload;
    private static String hash;
    private static final AtomicBoolean shorten = new AtomicBoolean(true);
    private static final AtomicReference<String> receivedRange = new AtomicReference<>();
    private static final AtomicReference<String> receivedAuthorization = new AtomicReference<>();
    private interface Checked { void run() throws Exception; }
    private interface Condition { boolean value() throws Exception; }
    private static void check(boolean condition, String name) { if (!condition) throw new AssertionError(name); passed.add(name); System.out.println("PASS " + name); }
    private static void waitFor(Condition condition, long timeout, String name) throws Exception {
        long deadline = System.currentTimeMillis() + timeout;
        while (System.currentTimeMillis() < deadline) { if (condition.value()) return; Thread.sleep(25); }
        throw new AssertionError("Timed out: " + name);
    }
    private static void rejects(Checked operation, String name) throws Exception {
        try { operation.run(); } catch (Exception expected) { check(true, name); return; }
        throw new AssertionError("Not rejected: " + name);
    }
    private static LmaApp app(String name) { LmaApp value = new LmaApp(work.resolve(name).toFile(), assets.toFile(), libraries.toFile()); applications.add(value); return value; }
    private static String add(LmaApp app, String endpoint, String checksum) throws Exception { return app.store.addCustom(endpoint, base + endpoint, checksum, false); }
    private static Downloads downloads(LmaApp app) { Downloads d = new Downloads(new LmaService(), app); transfers.add(d); return d; }
    private static void done(Downloads downloads, String name) throws Exception { waitFor(() -> !downloads.busy(), 40000, name); }
    private static void sameFile(LmaApp app, String id, String name) throws Exception { check(Arrays.equals(Files.readAllBytes(app.store.modelFile(id).toPath()), payload), name); }
    private static void httpsServer(Path keyStore) throws Exception {
        KeyStore keys = KeyStore.getInstance("PKCS12"); try (InputStream in = Files.newInputStream(keyStore)) { keys.load(in, "lma-host-tests".toCharArray()); }
        KeyManagerFactory km = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm()); km.init(keys, "lma-host-tests".toCharArray());
        TrustManagerFactory tm = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()); tm.init(keys);
        SSLContext ssl = SSLContext.getInstance("TLS"); ssl.init(km.getKeyManagers(), tm.getTrustManagers(), null);
        // Only this isolated test JVM trusts the generated loopback certificate.
        HttpsURLConnection.setDefaultSSLSocketFactory(ssl.getSocketFactory());
        https = HttpsServer.create(new InetSocketAddress("127.0.0.1", 0), 0); https.setHttpsConfigurator(new HttpsConfigurator(ssl));
        httpWorkers = Executors.newCachedThreadPool(); https.setExecutor(httpWorkers);
        payload = new byte[512 * 1024]; new Random(42).nextBytes(payload);
        ByteBuffer.wrap(payload).order(ByteOrder.LITTLE_ENDIAN).put(new byte[]{'G','G','U','F'}).putInt(3).putLong(0).putLong(0);
        hash = Protocol.hex(MessageDigest.getInstance("SHA-256").digest(payload));
        // HttpsServer cannot reliably abort a fixed-length TLS response. A raw TLS
        // socket closes the actual transport after fewer bytes than Content-Length.
        truncatedServer = (SSLServerSocket) ssl.getServerSocketFactory().createServerSocket(0, 8, InetAddress.getByName("127.0.0.1"));
        truncatedUrl = "https://127.0.0.1:" + truncatedServer.getLocalPort() + "/short";
        httpWorkers.submit(() -> {
            while (!truncatedServer.isClosed()) {
                try (SSLSocket socket = (SSLSocket) truncatedServer.accept()) {
                    socket.setSoTimeout(5000);
                    BufferedReader reader = new BufferedReader(new InputStreamReader(socket.getInputStream(), StandardCharsets.US_ASCII));
                    String line; int start = 0;
                    while ((line = reader.readLine()) != null && !line.isEmpty()) {
                        if (line.toLowerCase(Locale.ROOT).startsWith("range: bytes=")) start = Integer.parseInt(line.substring(13, line.length() - 1).trim());
                    }
                    OutputStream out = socket.getOutputStream();
                    String headers = "HTTP/1.1 " + (start > 0 ? "206 Partial Content" : "200 OK") + "\r\nContent-Length: " + (payload.length - start)
                        + "\r\nETag: \"fixture-v1\"\r\nConnection: close\r\n" + (start > 0 ? "Content-Range: bytes " + start + "-" + (payload.length - 1) + "/" + payload.length + "\r\n" : "") + "\r\n";
                    out.write(headers.getBytes(StandardCharsets.US_ASCII));
                    int count = shorten.getAndSet(false) ? 65536 : payload.length - start;
                    out.write(payload, start, count); out.flush();
                } catch (Exception error) { if (!truncatedServer.isClosed()) error.printStackTrace(); }
            }
        });
        https.createContext("/", exchange -> {
            try {
                String path = exchange.getRequestURI().getPath();
                receivedAuthorization.set(exchange.getRequestHeaders().getFirst("Authorization"));
                if (path.equals("/unavailable")) { exchange.sendResponseHeaders(503, -1); exchange.close(); return; }
                if (path.equals("/redirect") || path.equals("/downgrade")) {
                    exchange.getResponseHeaders().set("Location", path.equals("/downgrade") ? "http://127.0.0.1/file" : "/file"); exchange.sendResponseHeaders(302, -1); exchange.close(); return;
                }
                if (path.equals("/stall")) Thread.sleep(5000);
                if (path.equals("/html")) { byte[] body = "<html>Not a model download</html>".getBytes(StandardCharsets.UTF_8); exchange.sendResponseHeaders(200, body.length); exchange.getResponseBody().write(body); exchange.close(); return; }
                String range = exchange.getRequestHeaders().getFirst("Range"); receivedRange.set(range);
                int start = range == null ? 0 : Integer.parseInt(range.substring(6, range.length() - 1));
                if (path.equals("/restart")) start = 0;
                if (start == payload.length) { exchange.getResponseHeaders().set("Content-Range", "bytes */" + payload.length); exchange.sendResponseHeaders(416, -1); exchange.close(); return; }
                exchange.getResponseHeaders().set("ETag", path.equals("/etag-change") ? "\"different\"" : "\"fixture-v1\"");
                if (path.equals("/short")) exchange.getResponseHeaders().set("Connection", "close");
                int status = start > 0 ? 206 : 200;
                if (status == 206) exchange.getResponseHeaders().set("Content-Range", "bytes " + (path.equals("/wrong-range") ? 0 : start) + "-" + (payload.length - 1) + "/" + payload.length);
                exchange.sendResponseHeaders(status, path.equals("/chunked") ? 0 : payload.length - start);
                int end = path.equals("/short") && shorten.getAndSet(false) ? start + 65536 : payload.length;
                try (OutputStream out = exchange.getResponseBody()) {
                    for (int position = start; position < end; position += 4096) {
                        out.write(payload, position, Math.min(4096, end - position)); out.flush();
                        if (path.equals("/slow")) Thread.sleep(12);
                    }
                }
            } catch (Exception ignored) { exchange.close(); }
        });
        https.start(); base = "https://127.0.0.1:" + https.getAddress().getPort();
    }
    private static void testDownloads() throws Exception {
        LmaApp app = app("downloads"); Downloads d = downloads(app);
        HttpURLConnection fallback = Net.downloadCandidates(new String[]{base + "/unavailable", base + "/file"}, 0, "", connection -> {});
        byte[] received; try (InputStream in = fallback.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) { byte[] b = new byte[8192]; int n; while ((n = in.read(b)) >= 0) out.write(b, 0, n); received = out.toByteArray(); } finally { fallback.disconnect(); }
        check(Arrays.equals(received, payload), "Unavailable first source falls back over real HTTPS with exact bytes");
        HttpURLConnection privateToken = Net.downloadCandidates(new String[]{base + "/redirect"}, 0, "", connection -> {}, "hf_TEST_ONLY");
        try (InputStream ignored = privateToken.getInputStream()) { check(privateToken.getResponseCode() == 200 && receivedAuthorization.get() == null, "HF credentials stay absent across real HTTPS redirects on custom hosts"); } finally { privateToken.disconnect(); }
        String pinned = "https://huggingface.co/author/repo/resolve/0123456789/model.gguf";
        check(Arrays.equals(Net.modelSources(pinned, "auto"), new String[]{pinned, pinned.replace("huggingface.co", "hf-mirror.com")}), "Automatic mirror preserves pinned model path");
        check(Net.modelSources("https://other.example/model.gguf", "auto").length == 1, "Custom hosts never rewrite to the mirror");
        String id = add(app, "/file", hash); d.enqueue(id, ""); done(d, "Full HTTPS transfer"); sameFile(app, id, "HTTPS model bytes and publisher SHA match");
        check(app.store.download(id).getString("verification").equals("publisher-sha256"), "Publisher verification recorded");
        id = add(app, "/redirect", hash); d.enqueue(id, ""); done(d, "HTTPS redirect"); sameFile(app, id, "Relative HTTPS redirect downloads correctly");
        id = add(app, "/file?resume", hash); Files.write(app.store.partFile(id).toPath(), Arrays.copyOf(payload, 65536));
        d.enqueue(id, ""); done(d, "Range resume"); sameFile(app, id, "206 range resume produces exact bytes"); check("bytes=65536-".equals(receivedRange.get()), "Saved file length sent as Range offset");
        id = add(app, "/restart", hash); Files.write(app.store.partFile(id).toPath(), Arrays.copyOf(payload, 8192));
        d.enqueue(id, ""); done(d, "200 restart"); sameFile(app, id, "Server ignoring Range restarts instead of appending");
        id = add(app, "/file?complete", hash); Files.write(app.store.partFile(id).toPath(), payload);
        d.enqueue(id, ""); done(d, "416 complete"); sameFile(app, id, "416 verifies complete partial file");
        id = add(app, "/wrong-range", hash); Files.write(app.store.partFile(id).toPath(), Arrays.copyOf(payload, 8192));
        d.enqueue(id, ""); done(d, "Wrong range"); check(!app.store.modelFile(id).exists() && app.store.partFile(id).length() == 8192 && app.store.download(id).getString("state").equals("error"), "Wrong resume offset rejected without altering saved bytes");
        id = add(app, "/etag-change", hash); Files.write(app.store.partFile(id).toPath(), Arrays.copyOf(payload, 8192));
        app.store.updateDownload(id, new JSONObject().put("etag", "\"fixture-v1\""), true);
        d.enqueue(id, ""); done(d, "Changed ETag"); check(!app.store.modelFile(id).exists() && app.store.partFile(id).length() == 8192, "Changed entity cannot be appended to old bytes");
        id = app.store.addCustom("Truncated", truncatedUrl, hash, false); d.enqueue(id, ""); done(d, "Truncated transfer");
        check(app.store.download(id).getString("state").equals("error") && app.store.partFile(id).length() > 0, "Premature network EOF preserves progress and records failure");
        d.enqueue(id, ""); done(d, "Resume truncated transfer"); sameFile(app, id, "Interrupted HTTPS transfer resumes to exact publisher hash");
        id = add(app, "/chunked", hash); d.enqueue(id, ""); done(d, "Chunked transfer"); sameFile(app, id, "Unknown Content-Length validates final SHA");
        id = add(app, "/html", ""); d.enqueue(id, ""); done(d, "HTML rejection");
        check(!app.store.modelFile(id).exists() && !app.store.partFile(id).exists(), "HTML response rejected and never installed");
        File rejected = new File(app.store.partFile(id).getParentFile(), id + ".rejected"); check(rejected.exists(), "Rejected bytes quarantined"); app.store.remove(id); check(!rejected.exists(), "Delete cleans rejected bytes");
        id = add(app, "/file?bad-hash", String.join("", Collections.nCopies(64, "0"))); d.enqueue(id, ""); done(d, "Bad SHA rejection");
        check(!app.store.modelFile(id).exists() && !app.store.partFile(id).exists(), "Mismatched publisher SHA never installs or resumes corrupt data");
        id = add(app, "/downgrade", ""); d.enqueue(id, ""); done(d, "Downgrade rejection"); check(app.store.download(id).getString("state").equals("error"), "HTTPS-to-HTTP redirect rejected");
        rejects(() -> app.store.addCustom("bad", "http://example.com/model.gguf", "", false), "Custom model must use HTTPS");
        rejects(() -> app.store.addCustom("bad", base + "/file", "not-sha256", false), "Invalid expected SHA rejected");
        String slow = add(app, "/slow", hash), queued = add(app, "/file?queued", hash); d.enqueue(slow, "");
        waitFor(() -> app.store.download(slow).optString("state").equals("downloading"), 3000, "Slow transfer starts");
        d.enqueue(queued, ""); d.pause(queued); check(app.store.download(queued).getString("state").equals("paused") && !d.busy(queued), "Pause queued task takes effect before active download completes");
        app.store.remove(queued); rejects(() -> app.store.remove(slow), "Cannot delete bytes while a transfer owns the file");
        d.pause(slow); done(d, "Pause active transfer"); check(app.store.download(slow).getString("state").equals("paused"), "Active cancellation ends in durable paused state");
        d.enqueue(slow, ""); done(d, "Resume paused transfer"); sameFile(app, slow, "Pause and resume retain complete data integrity");
        check(!app.store.modelFile(queued).exists() && app.store.download(queued).length() == 0, "Cancelled queued worker cannot recreate deleted entry");
        String reopen = add(app, "/slow?restart-service", hash); d.enqueue(reopen, "");
        waitFor(() -> app.store.partFile(reopen).length() > 0, 3000, "Service handover starts"); d.close();
        Downloads replacement = downloads(app); replacement.enqueue(reopen, ""); done(replacement, "Replacement transfer"); sameFile(app, reopen, "Rapid Service replacement serializes file writers");
        Path imported = work.resolve("import-fixture.gguf"); Files.write(imported, payload);
        id = app.store.addCustom("Imported", "", hash, true); replacement.enqueue(id, imported.toUri().toString()); done(replacement, "Local import"); sameFile(app, id, "Local document stream imports with SHA verification");
        String interrupted = add(app, "/file?persisted", hash); app.store.updateDownload(interrupted, new JSONObject().put("state", "downloading"), true);
        Store reopened = new Store(app); check(reopened.download(interrupted).getString("state").equals("paused") && reopened.download(interrupted).getBoolean("interrupted"), "Reopened Store marks unfinished transfer as resumable");
    }
    private static int freePort() throws IOException { try (ServerSocket socket = new ServerSocket(0)) { return socket.getLocalPort(); } }
    private static EngineHost engine(LmaService service, LmaApp app, String mode, AtomicInteger launches) {
        EngineHost host = new EngineHost(service, app, builder -> {
            launches.incrementAndGet();
            Files.write(work.resolve("last-engine-argv.json"), new JSONArray(builder.command()).toString().getBytes(StandardCharsets.UTF_8));
            List<String> command = new ArrayList<>(); command.add(Paths.get(System.getProperty("java.home"), "bin", "java.exe").toString());
            command.add("-Dsun.net.useExclusiveBind=false"); command.add("-Dfile.encoding=UTF-8"); command.add("-Dstdout.encoding=UTF-8"); command.add("-Dstderr.encoding=UTF-8");
            command.add("-cp"); command.add(System.getProperty("java.class.path")); command.add("com.lma.app.HostServer"); command.addAll(builder.command().subList(1, builder.command().size()));
            ProcessBuilder fixture = new ProcessBuilder(command).redirectErrorStream(true); fixture.directory(root.toFile()); fixture.environment().putAll(builder.environment());
            fixture.environment().put("LMA_HOST_REDIRECT_URL", "http://127.0.0.1:" + redirectTrap.port() + "/unowned");
            fixture.environment().put("LMA_HOST_BEHAVIOR", mode); fixture.environment().put("LMA_HOST_LAST_REQUEST", work.resolve("last-request.json").toString());
            return fixture.start();
        });
        service.engine = host; engines.add(host); return host;
    }
    private static void model(LmaApp app, String id) throws Exception { Files.write(app.store.modelFile(id).toPath(), payload); }
    private static void testProcessesAndChat() throws Exception {
        redirectTrap = new LocalHttp("127.0.0.1", 0, request -> { inferenceRedirects.incrementAndGet(); return LocalApi.json(200, new JSONObject().put("fixture", true)); });
        LmaApp app = app("engine"); LmaService owner = new LmaService(); AtomicInteger launches = new AtomicInteger();
        app.prefs.edit().putInt("port", freePort()).apply();
        ApiHost gateway = new ApiHost(owner, app); gateways.add(gateway); gateway.start();
        HttpURLConnection emptyModels = Net.local(app, "/v1/models");
        try { check(emptyModels.getResponseCode() == 200 && new JSONObject(Store.read(emptyModels.getInputStream(), 65536)).getJSONArray("data").length() == 0 && app.nativeProcess == null, "Production gateway starts with zero installed weights and no engine process"); } finally { emptyModels.disconnect(); }
        model(app, "m08"); model(app, "m01");
        app.store.saveConfig("m08", new JSONObject().put("context", 1536).put("threads", 2).put("maxTokens", 321).put("temperature", 1.1).put("systemPrompt", "model eight prompt"));
        app.store.saveConfig("m01", new JSONObject().put("context", 777).put("threads", 1).put("reasoning", "auto"));
        EngineHost host = engine(owner, app, "normal", launches); host.load("m08");
        waitFor(host::ready, 10000, "Child process ready"); check(app.engineModel.equals("m08"), "Real child process passes health, authenticated models and alias checks");
        List<Object> argv = new JSONArray(new String(Files.readAllBytes(work.resolve("last-engine-argv.json")), StandardCharsets.UTF_8)).toList();
        check(argv.get(argv.indexOf("-c") + 1).equals("1536") && argv.get(argv.indexOf("-t") + 1).equals("2"), "EngineHost starts the child with the chosen model's context and thread settings");
        HttpURLConnection unauthorized = (HttpURLConnection) new URL("http://127.0.0.1:" + app.nativePort + "/v1/models").openConnection();
        check(unauthorized.getResponseCode() == 401, "Private native endpoint rejects missing API key"); unauthorized.disconnect();
        check(app.nativePort != app.prefs.getInt("port", 0) && !app.nativeApiKey.equals(app.prefs.getString("apiKey", "")) && argv.get(argv.indexOf("--host") + 1).equals("127.0.0.1"), "Native text uses a separate loopback port and per-process secret");
        HttpURLConnection publicModels = Net.local(app, "/v1/models");
        try { check(publicModels.getResponseCode() == 200 && new JSONObject(Store.read(publicModels.getInputStream(), 65536)).getJSONArray("data").length() == 2, "Production Android adapter serves installed model metadata through the public gateway"); } finally { publicModels.disconnect(); }
        HttpURLConnection redirected = Net.local(app, "/v1/chat/completions"); redirected.setRequestMethod("POST"); redirected.setDoOutput(true); redirected.setRequestProperty("Content-Type", "application/json");
        byte[] redirectBody = new JSONObject().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", "redirect"))).put("stream", true).toString().getBytes(StandardCharsets.UTF_8);
        redirected.setFixedLengthStreamingMode(redirectBody.length); try (OutputStream out = redirected.getOutputStream()) { out.write(redirectBody); }
        try { check(redirected.getResponseCode() == 502 && inferenceRedirects.get() == 0, "Native inference redirects are rejected without contacting another endpoint"); } finally { redirected.disconnect(); }
        HttpURLConnection publicChat = Net.local(app, "/v1/chat/completions"); publicChat.setRequestMethod("POST"); publicChat.setDoOutput(true); publicChat.setRequestProperty("Content-Type", "application/json");
        byte[] publicBody = new JSONObject().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", "stop"))).put("stream", true).put("max_tokens", 99999).toString().getBytes(StandardCharsets.UTF_8);
        publicChat.setFixedLengthStreamingMode(publicBody.length); try (OutputStream out = publicChat.getOutputStream()) { out.write(publicBody); }
        check(publicChat.getResponseCode() == 200 && publicChat.getHeaderField("X-LMA-Max-Tokens").equals("321"), "Production gateway applies the loaded profile's output ceiling before proxying");
        try (BufferedReader stream = new BufferedReader(new InputStreamReader(publicChat.getInputStream(), StandardCharsets.UTF_8))) {
            check(stream.readLine().startsWith("data:") && app.textRequestBusy, "Public streaming requests retain the shared execution lease");
            ChatRunner blocked = new ChatRunner(owner, app); chats.add(blocked);
            rejects(() -> blocked.send("duplicate"), "App chat cannot bypass an active external text request");
            rejects(() -> host.load("m01"), "Model loading cannot bypass an active external text request");
            JSONObject forwarded = new JSONObject(new String(Files.readAllBytes(work.resolve("last-request.json")), StandardCharsets.UTF_8));
            check(forwarded.getInt("max_tokens") == 321 && forwarded.getJSONArray("messages").length() == 1 && forwarded.getDouble("temperature") == 1.1, "Gateway proxy uses model defaults without injecting the App system prompt");
            gateway.cancelText();
        } finally { publicChat.disconnect(); }
        waitFor(() -> !app.textRequestBusy, 4000, "External text lease release"); check(!app.textRequestBusy, "Cancelling the proxy releases native connection ownership");
        gateway.stop(); check(!gateway.ready() && !app.prefs.getBoolean("desiredApi", true) && host.ready(), "Stopping the public API preserves the independent loaded engine and clears only API restoration");
        gateway.start(); check(gateway.ready() && host.ready(), "Restarting the API does not reload or replace model assets");
        host.load("m01"); waitFor(() -> host.ready() && app.engineModel.equals("m01"), 10000, "Model switch"); check(launches.get() == 2, "Model switch retires old child and loads selected alias");
        argv = new JSONArray(new String(Files.readAllBytes(work.resolve("last-engine-argv.json")), StandardCharsets.UTF_8)).toList();
        check(argv.get(argv.indexOf("-c") + 1).equals("777") && argv.get(argv.indexOf("--reasoning") + 1).equals("auto"), "Switching model replaces load parameters with that model's saved profile");
        host.load("m08"); host.load("m01"); host.load("m08");
        waitFor(() -> host.ready() && app.engineModel.equals("m08"), 10000, "Rapid model replacement");
        check(app.nativeProcess.isAlive(), "Stale launches and exit watchers cannot stop the newest requested model");
        ChatRunner chat = new ChatRunner(owner, app); chats.add(chat); chat.send("normal"); waitFor(() -> !app.generating, 5000, "Normal chat");
        JSONObject reply = app.chats.last(); check(reply.getString("status").equals("done") && reply.getString("content").equals("你好🙂") && reply.getInt("tokens") == 7, "Production ChatRunner parses real HTTP UTF-8 SSE and usage");
        JSONObject sent = new JSONObject(new String(Files.readAllBytes(work.resolve("last-request.json")), StandardCharsets.UTF_8));
        check(sent.getInt("max_tokens") == 321 && sent.getDouble("temperature") == 1.1 && sent.getJSONArray("messages").getJSONObject(0).getString("content").equals("model eight prompt"), "Production ChatRunner sends the active model's output limit, temperature and system prompt");
        app.store.saveConfig("m01", new JSONObject().put("maxTokens", 11).put("temperature", 0.1));
        chat.send("normal"); waitFor(() -> !app.generating, 5000, "Inactive profile edit");
        sent = new JSONObject(new String(Files.readAllBytes(work.resolve("last-request.json")), StandardCharsets.UTF_8));
        check(sent.getInt("max_tokens") == 321 && sent.getDouble("temperature") == 1.1, "Editing another model cannot change the active model's generation parameters");
        check(reply.getString("reasoning").equals("思考片段"), "Reasoning stream persisted separately");
        chat.send("broken"); waitFor(() -> !app.generating, 5000, "Truncated SSE");
        reply = app.chats.last(); check(reply.getString("status").equals("error") && reply.getString("content").equals("你好🙂"), "Truncated SSE records error and retains completed chunks");
        chat.send("normal"); waitFor(() -> !app.generating, 5000, "Continue after error"); check(app.chats.last().getString("status").equals("done"), "Strict alternating template accepts chat after interrupted reply");
        chat.send("sse-error"); waitFor(() -> !app.generating, 5000, "SSE error"); check(app.chats.last().getString("status").equals("error") && app.chats.last().getString("content").contains("你好"), "Server SSE error retains partial text");
        chat.send("json-error"); waitFor(() -> !app.generating, 5000, "JSON error"); check(app.chats.last().getString("error").contains("Prompt is too long"), "HTTP JSON failure shown as readable message");
        chat.send("stop"); waitFor(() -> app.chats.last().optString("content").contains("片段"), 4000, "Partial reply before cancel");
        rejects(() -> chat.send("duplicate"), "Concurrent chat requests rejected"); rejects(() -> host.load("m08"), "Model switch rejected during active chat");
        chat.cancel(); waitFor(() -> !app.generating, 4000, "Cancel stream"); check(app.chats.last().getString("status").equals("stopped") && app.chats.last().getString("content").contains("片段"), "Active HTTP cancellation preserves partial reply");
        chat.send("long-prefill"); chat.cancel(); waitFor(() -> !app.generating, 4000, "Cancel before stream headers"); check(app.chats.last().getString("status").equals("stopped"), "Immediate cancellation finishes before first token");
        Process previous = app.nativeProcess; previous.destroyForcibly(); waitFor(() -> app.nativeProcess != previous && host.ready(), 12000, "Crash recovery"); check(launches.get() >= 3, "Unexpected real child exit restarts the engine");
        host.close(); EngineHost replacement = engine(owner, app, "normal", launches); replacement.load("m08"); waitFor(replacement::ready, 10000, "New Service engine"); check(replacement.ready(), "New Service waits for previous process before reusing port");
        replacement.stop(); waitFor(() -> !app.nativeProcess.isAlive(), 5000, "Explicit stop"); check(!app.prefs.getBoolean("desiredRunning", true) && !replacement.ready(), "Explicit stop disables automatic restoration and terminates child");
        Thread.sleep(1800); check(!replacement.ready(), "Explicit stop does not trigger crash recovery");
        app.prefs.edit().putInt("port", freePort()).apply();
        Process occupied = new ProcessBuilder(Paths.get(System.getProperty("java.home"), "bin", "java.exe").toString(), "-Dsun.net.useExclusiveBind=true", "-cp", System.getProperty("java.class.path"), "com.lma.app.HostServer", "--port", String.valueOf(app.prefs.getInt("port", 0)), "--occupy").redirectErrorStream(true).start();
        try {
            String signal = new BufferedReader(new InputStreamReader(occupied.getInputStream(), StandardCharsets.UTF_8)).readLine();
            if (!"exclusive port occupied".equals(signal)) throw new IOException("Exclusive port fixture did not start: " + signal);
            replacement.load("m08"); waitFor(replacement::ready, 10000, "Private native port"); check(replacement.ready(), "An occupied public port cannot redirect the private native engine");
            rejects(() -> gateway.configure(app.prefs.getInt("port", 0), false), "Public gateway reports port conflicts independently of engine readiness");
        } finally { occupied.destroyForcibly(); occupied.waitFor(); }
        replacement.close();
        app.prefs.edit().putInt("port", freePort()).apply(); EngineHost wrong = engine(owner, app, "wrong-alias", launches); wrong.load("m08");
        waitFor(() -> {
            HttpURLConnection connection = null;
            try { connection = Net.engine(app, "/v1/models"); connection.setReadTimeout(1000); return connection.getResponseCode() == 200 && Store.read(connection.getInputStream(), 65536).contains("foreign-model"); }
            catch (IOException ignored) { return false; } finally { if (connection != null) connection.disconnect(); }
        }, 10000, "Wrong alias fixture responds");
        check(!wrong.ready(), "Healthy endpoint with wrong model alias cannot mark engine ready"); wrong.close();
        app.prefs.edit().putInt("port", freePort()).apply(); AtomicInteger crashes = new AtomicInteger(); EngineHost crashing = engine(owner, app, "crash", crashes); crashing.load("m08");
        waitFor(() -> app.engineState.equals("error") && !crashing.wanted(), 25000, "Bounded crash recovery"); check(crashes.get() == 4 && !app.prefs.getBoolean("desiredRunning", true), "Repeated crash stops after three retries");
    }
    private static void testHistory() {
        List<ChatHistory.Message> input = Arrays.asList(new ChatHistory.Message("user", "orphan", "done"), new ChatHistory.Message("assistant", "", "stopped"), new ChatHistory.Message("user", "good", "done"), new ChatHistory.Message("assistant", "partial", "interrupted"));
        List<ChatHistory.Message> history = ChatHistory.select(input, 100, 16);
        check(history.size() == 2 && history.get(0).content.equals("good") && history.get(1).content.equals("partial"), "History drops empty failed turns and retains useful interrupted pairs");
        check(ChatHistory.select(input, 3, 16).isEmpty(), "History never includes a turn beyond its character budget");
        check(ChatHistory.select(input, 100, 1).isEmpty(), "History never cuts a conversational pair in half");
    }
    public static void main(String[] args) throws Exception {
        root = Paths.get(args[0]).toAbsolutePath(); work = root.resolve("build/backend-tests/run"); Files.createDirectories(work);
        assets = root.resolve("app/src/main/assets"); libraries = root.resolve("app/src/main/jniLibs/arm64-v8a");
        try {
            httpsServer(root.resolve("build/backend-tests/loopback.p12")); passed.addAll(ModelSettingsTest.run(work, assets, libraries)); testHistory(); testDownloads();
            passed.addAll(ImportCancellationTest.run(app("import-cancellation"), payload, work.resolve("import-cancellation-artifacts").toFile())); testProcessesAndChat();
            JSONObject result = new JSONObject().put("passed", passed.size()).put("checks", new JSONArray(passed)).put("real_https_sockets", true).put("real_child_processes", true)
                .put("production_backend_classes", new JSONArray(Arrays.asList("Store", "Downloads", "Net", "EngineHost", "ChatRunner", "ChatHistory", "Protocol", "ModelSettings", "GgufMetadata")))
                .put("android_framework_adapters", true).put("physical_device", false).put("model_inference", false);
            Files.write(root.resolve("build/backend-tests/results.json"), result.toString(2).getBytes(StandardCharsets.UTF_8));
            System.out.println("Backend checks passed: " + passed.size());
        } catch (Throwable failure) {
            for (LmaApp app : applications) { System.err.println("STATE " + app.engineState + " / " + app.engineDetail); for (String line : app.logs) System.err.println(line); }
            throw failure;
        } finally {
            if (redirectTrap != null) redirectTrap.close(); for (ApiHost api : gateways) api.close(); for (ChatRunner c : chats) c.close(); for (Downloads d : transfers) d.close(); for (EngineHost e : engines) e.close();
            if (truncatedServer != null) truncatedServer.close();
            if (https != null) https.stop(0); if (httpWorkers != null) httpWorkers.shutdownNow();
        }
    }
}
