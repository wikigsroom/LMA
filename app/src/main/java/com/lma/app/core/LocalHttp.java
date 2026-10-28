package com.lma.app.core;

import java.io.*;
import java.net.*;
import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.util.*;
import java.util.concurrent.*;

/** Bounded HTTP/1.x transport for the local API; one request per connection, bounded JSON or input-media chunks. */
public final class LocalHttp implements AutoCloseable {
    public static final int MAX_BODY = 256 * 1024;
    private static final int MAX_HEADERS = 16 * 1024;
    private final ServerSocket listener;
    private final Handler handler;
    private final ThreadPoolExecutor workers;
    private final ScheduledExecutorService watchdog;
    private final Set<Client> clients = ConcurrentHashMap.newKeySet();
    private final Thread acceptor;
    private volatile boolean closed;

    public interface Handler { Response handle(Request request) throws Exception; }
    public interface Body extends AutoCloseable {
        void write(OutputStream out) throws Exception;
        @Override default void close() throws Exception {}
    }
    public static final class Failure extends IOException {
        public final int status;
        public final String code;
        public Failure(int status, String code, String message) { super(message); this.status = status; this.code = code; }
    }
    public static final class Request {
        public final String method, path;
        public final Map<String, String> headers, query;
        public final byte[] body;
        private Request(String method, String path, Map<String, String> headers, Map<String, String> query, byte[] body) {
            this.method = method; this.path = path; this.headers = Collections.unmodifiableMap(headers);
            this.query = Collections.unmodifiableMap(query); this.body = body;
        }
        public String header(String name) { String value = headers.get(name.toLowerCase(Locale.ROOT)); return value == null ? "" : value; }
        public String query(String name) { String value = query.get(name); return value == null ? "" : value; }
        public String utf8() throws Failure {
            try { return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(body)).toString(); }
            catch (CharacterCodingException error) { throw new Failure(400, "invalid_utf8", "The JSON body must use valid UTF-8"); }
        }
    }
    public static final class Response implements AutoCloseable {
        public final int status;
        public final String mime;
        public final long length;
        public final Body body;
        public final Map<String, String> headers = new LinkedHashMap<>();
        public Response(int status, String mime, long length, Body body) {
            if (status < 200 || status > 599 || length < -1 || mime == null || mime.chars().anyMatch(c -> c < 32 || c > 126)) throw new IllegalArgumentException("Invalid HTTP response");
            this.status = status; this.mime = mime; this.length = length; this.body = body;
        }
        public Response header(String key, String value) {
            if (!key.matches("[A-Za-z0-9-]+") || value.chars().anyMatch(c -> c < 32 || c > 126)) throw new IllegalArgumentException("Invalid response header");
            if (Arrays.asList("content-length", "connection", "transfer-encoding", "content-type").contains(key.toLowerCase(Locale.ROOT))) throw new IllegalArgumentException("Reserved response header");
            headers.put(key, value); return this;
        }
        @Override public void close() throws Exception { if (body != null) body.close(); }
        public static Response bytes(int status, String mime, byte[] bytes) {
            return new Response(status, mime, bytes.length, out -> out.write(bytes));
        }
        public static Response stream(int status, String mime, long length, InputStream in) {
            return new Response(status, mime, length, new Body() {
                @Override public void write(OutputStream out) throws IOException {
                    byte[] buffer = new byte[16384]; long remaining = length;
                    while (remaining != 0) {
                        int count = in.read(buffer, 0, remaining < 0 ? buffer.length : (int) Math.min(buffer.length, remaining));
                        if (count < 0) { if (remaining > 0) throw new EOFException("Incomplete response body"); break; }
                        if (count == 0) continue;
                        out.write(buffer, 0, count); out.flush(); if (remaining > 0) remaining -= count;
                    }
                }
                @Override public void close() throws IOException { in.close(); }
            });
        }
    }
    private static final class Client {
        final Socket socket;
        final long started = System.nanoTime();
        volatile long writing;
        volatile boolean parsed;
        volatile Thread handlerThread;
        Client(Socket socket) { this.socket = socket; }
        void close() { try { socket.close(); } catch (IOException ignored) {} Thread thread = handlerThread; if (thread != null && thread != Thread.currentThread()) thread.interrupt(); }
    }
    public LocalHttp(String host, int port, Handler handler) throws IOException {
        this.handler = handler;
        listener = new ServerSocket(); listener.setReuseAddress(true);
        try { listener.bind(new InetSocketAddress(host, port), 32); }
        catch (IOException error) { listener.close(); throw error; }
        workers = new ThreadPoolExecutor(0, 12, 30, TimeUnit.SECONDS, new SynchronousQueue<>(), runnable -> {
            Thread thread = new Thread(runnable, "LMA-api-client"); thread.setDaemon(true); return thread;
        });
        watchdog = Executors.newSingleThreadScheduledExecutor(runnable -> { Thread thread = new Thread(runnable, "LMA-api-timeouts"); thread.setDaemon(true); return thread; });
        watchdog.scheduleWithFixedDelay(() -> {
            long now = System.nanoTime();
            for (Client client : clients) if (!client.parsed && now - client.started > TimeUnit.SECONDS.toNanos(15) || now - client.started > TimeUnit.HOURS.toNanos(2) || client.writing != 0 && now - client.writing > TimeUnit.SECONDS.toNanos(30)) client.close();
        }, 1, 1, TimeUnit.SECONDS);
        acceptor = new Thread(this::accept, "LMA-api-listener"); acceptor.setDaemon(true); acceptor.start();
    }
    public int port() { return listener.getLocalPort(); }
    private void accept() {
        while (!closed) {
            Client client = null;
            try {
                Socket socket = listener.accept(); client = new Client(socket); clients.add(client);
                socket.setSoTimeout(15000); socket.setTcpNoDelay(true); Client accepted = client;
                workers.execute(() -> serve(accepted));
            } catch (IOException | RejectedExecutionException error) {
                if (client != null) { clients.remove(client); client.close(); }
            }
        }
    }
    private void serve(Client client) {
        client.handlerThread = Thread.currentThread();
        try (Socket socket = client.socket) {
            Request request;
            try { request = read(socket.getInputStream()); client.parsed = true; }
            catch (SocketTimeoutException error) { send(client, null, plain(408, "Request timeout")); return; }
            catch (Failure error) { send(client, null, plain(error.status, error.getMessage())); return; }
            Response response;
            try { response = handler.handle(request); }
            catch (Failure error) { response = plain(error.status, error.getMessage()); }
            catch (Exception error) { response = plain(500, "Local API request failed"); }
            send(client, request, response);
        } catch (Exception ignored) {
            // Disconnected clients must release response leases without logging credentials/prompts.
        } finally { clients.remove(client); client.close(); }
    }
    private static Response plain(int status, String text) { return Response.bytes(status, "text/plain; charset=utf-8", text.getBytes(StandardCharsets.UTF_8)); }
    private static void send(Client client, Request request, Response response) throws Exception {
        try (Response owned = response) {
            OutputStream raw = client.socket.getOutputStream();
            OutputStream out = new FilterOutputStream(raw) {
                @Override public void write(int value) throws IOException { client.writing = System.nanoTime(); try { raw.write(value); } finally { client.writing = 0; } }
                @Override public void write(byte[] value, int offset, int length) throws IOException { client.writing = System.nanoTime(); try { raw.write(value, offset, length); } finally { client.writing = 0; } }
            };
            StringBuilder head = new StringBuilder("HTTP/1.1 ").append(response.status).append(' ').append(reason(response.status)).append("\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nContent-Type: ").append(response.mime).append("\r\n");
            if (response.length >= 0) head.append("Content-Length: ").append(response.length).append("\r\n");
            for (Map.Entry<String, String> entry : response.headers.entrySet()) head.append(entry.getKey()).append(": ").append(entry.getValue()).append("\r\n");
            head.append("\r\n"); out.write(head.toString().getBytes(StandardCharsets.US_ASCII)); out.flush();
            if ((request == null || !request.method.equals("HEAD")) && response.body != null) { response.body.write(out); out.flush(); }
        }
    }
    private static Request read(InputStream raw) throws IOException {
        BufferedInputStream in = new BufferedInputStream(raw, 8192); int[] budget = {MAX_HEADERS};
        String start = line(in, budget); String[] parts = start.split(" ", -1);
        if (parts.length != 3 || !parts[0].matches("[A-Z]+") || !Arrays.asList("HTTP/1.0", "HTTP/1.1").contains(parts[2])) throw new Failure(400, "invalid_request", "Invalid HTTP request line");
        String target = parts[1];
        if (!target.startsWith("/") || target.startsWith("//") || target.contains("#") || target.contains("\\") || target.chars().anyMatch(c -> c <= 32 || c >= 127)) throw new Failure(400, "invalid_target", "Use an origin-form request target");
        Map<String, String> headers = new LinkedHashMap<>();
        for (int count = 0;; count++) {
            String line = line(in, budget); if (line.isEmpty()) break;
            int colon = line.indexOf(':');
            if (count >= 64 || colon < 1 || !line.substring(0, colon).matches("[!#$%&'*+.^_`|~0-9A-Za-z-]+")) throw new Failure(400, "invalid_header", "Invalid HTTP header");
            String key = line.substring(0, colon).toLowerCase(Locale.ROOT), value = line.substring(colon + 1).trim();
            if (value.chars().anyMatch(c -> c < 32 && c != 9 || c == 127) || headers.put(key, value) != null) throw new Failure(400, "duplicate_header", "Duplicate or invalid HTTP header");
        }
        if (parts[2].equals("HTTP/1.1") && (!headers.containsKey("host") || headers.get("host").isEmpty())) throw new Failure(400, "missing_host", "HTTP/1.1 requires Host");
        if (headers.containsKey("transfer-encoding")) throw new Failure(501, "unsupported_transfer", "Use Content-Length; chunked request bodies are not supported");
        if (headers.containsKey("expect")) throw new Failure(417, "unsupported_expect", "Expect is not supported");
        int length = 0;
        if (headers.containsKey("content-length")) {
            String value = headers.get("content-length");
            if (!value.matches("[0-9]{1,10}")) throw new Failure(400, "invalid_length", "Invalid Content-Length");
            long size = Long.parseLong(value); if (size > MAX_BODY) throw new Failure(413, "body_too_large", "Request body exceeds 256 KiB"); length = (int) size;
        } else if (parts[0].equals("POST") || parts[0].equals("PUT")) throw new Failure(411, "missing_length", "Content-Length is required");
        byte[] body = new byte[length]; int offset = 0;
        while (offset < body.length) { int size = in.read(body, offset, body.length - offset); if (size < 0) throw new Failure(400, "incomplete_body", "Incomplete request body"); offset += size; }
        int question = target.indexOf('?'); String path = question < 0 ? target : target.substring(0, question);
        Map<String, String> query = new LinkedHashMap<>();
        if (question >= 0 && question + 1 < target.length()) {
            for (String pair : target.substring(question + 1).split("&", -1)) {
                int equal = pair.indexOf('='); String key = decode(equal < 0 ? pair : pair.substring(0, equal)), value = decode(equal < 0 ? "" : pair.substring(equal + 1));
                if (key.isEmpty() || query.size() >= 16 || query.put(key, value) != null) throw new Failure(400, "invalid_query", "Duplicate or invalid query parameter");
            }
        }
        return new Request(parts[0], path, headers, query, body);
    }
    private static String decode(String value) throws Failure {
        try { String decoded = URLDecoder.decode(value, "UTF-8"); if (decoded.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException(); return decoded; }
        catch (Exception error) { throw new Failure(400, "invalid_query", "Invalid query encoding"); }
    }
    private static String line(InputStream in, int[] remaining) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        while (true) {
            if (--remaining[0] < 0) throw new Failure(431, "headers_too_large", "Request headers exceed 16 KiB");
            int value = in.read(); if (value < 0) throw new EOFException();
            if (value == 13) { if (--remaining[0] < 0 || in.read() != 10) throw new Failure(400, "invalid_header", "Use CRLF line endings"); return new String(bytes.toByteArray(), StandardCharsets.US_ASCII); }
            if (value < 32 || value >= 127) throw new Failure(400, "invalid_header", "Invalid request line/header encoding");
            bytes.write(value);
        }
    }
    private static String reason(int status) {
        switch (status) {
            case 200: return "OK"; case 202: return "Accepted"; case 204: return "No Content"; case 206: return "Partial Content";
            case 400: return "Bad Request"; case 401: return "Unauthorized"; case 404: return "Not Found"; case 405: return "Method Not Allowed";
            case 408: return "Request Timeout"; case 409: return "Conflict"; case 411: return "Length Required"; case 413: return "Content Too Large";
            case 416: return "Range Not Satisfiable"; case 417: return "Expectation Failed"; case 431: return "Request Header Fields Too Large";
            case 501: return "Not Implemented"; case 503: return "Service Unavailable"; default: return "Local API";
        }
    }
    @Override public void close() {
        closed = true; try { listener.close(); } catch (IOException ignored) {}
        for (Client client : clients) client.close(); workers.shutdownNow(); watchdog.shutdownNow();
    }
}
