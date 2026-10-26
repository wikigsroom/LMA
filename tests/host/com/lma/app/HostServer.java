package com.lma.app;

import com.sun.net.httpserver.*;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.concurrent.*;
import org.json.*;
import java.util.*;

/** Real child process implementing only a test protocol, never language-model inference. */
public final class HostServer {
    private interface Handler { void handle(Exchange exchange) throws IOException; }
    private static final class Exchange {
        private final Socket socket;
        private final Headers request = new Headers(), response = new Headers();
        private final byte[] body;
        final String path;
        Exchange(Socket socket) throws IOException {
            this.socket = socket; InputStream in = socket.getInputStream();
            String first = line(in); path = first.split(" ")[1]; String header;
            while (!(header = line(in)).isEmpty()) { int colon = header.indexOf(':'); if (colon > 0) request.set(header.substring(0, colon), header.substring(colon + 1).trim()); }
            String size = request.getFirst("Content-Length"); int count = size == null ? 0 : Integer.parseInt(size);
            if (count > 1000000) throw new IOException("Request too large");
            body = new byte[count]; int offset = 0;
            while (offset < count) { int n = in.read(body, offset, count - offset); if (n < 0) throw new EOFException(); offset += n; }
        }
        private static String line(InputStream in) throws IOException {
            ByteArrayOutputStream out = new ByteArrayOutputStream(); int value;
            while ((value = in.read()) != -1 && value != '\n') { if (value != '\r') out.write(value); if (out.size() > 65536) throw new IOException("Header too large"); }
            if (value < 0 && out.size() == 0) throw new EOFException();
            return new String(out.toByteArray(), StandardCharsets.US_ASCII);
        }
        Headers getRequestHeaders() { return request; }
        Headers getResponseHeaders() { return response; }
        InputStream getRequestBody() { return new ByteArrayInputStream(body); }
        OutputStream getResponseBody() throws IOException { return socket.getOutputStream(); }
        void sendResponseHeaders(int code, long length) throws IOException {
            StringBuilder h = new StringBuilder("HTTP/1.1 " + code + " Fixture\r\nConnection: close\r\n");
            if (length > 0) h.append("Content-Length: ").append(length).append("\r\n");
            for (Map.Entry<String, List<String>> item : response.entrySet()) for (String value : item.getValue()) h.append(item.getKey()).append(": ").append(value).append("\r\n");
            getResponseBody().write(h.append("\r\n").toString().getBytes(StandardCharsets.US_ASCII));
        }
        void close() { try { socket.close(); } catch (IOException ignored) {} }
    }
    private static final class Server {
        final ServerSocket socket = new ServerSocket();
        final ExecutorService executor = Executors.newCachedThreadPool();
        final Map<String, Handler> handlers = new ConcurrentHashMap<>();
        final Set<Socket> clients = ConcurrentHashMap.newKeySet();
        Server(int port) throws IOException {
            // Model llama.cpp's reusable listening socket on the Windows host.
            socket.setReuseAddress(true); socket.bind(new InetSocketAddress("127.0.0.1", port));
        }
        void createContext(String path, Handler handler) { handlers.put(path, handler); }
        void start() { executor.submit(() -> {
            while (!socket.isClosed()) try {
                Socket client = socket.accept(); clients.add(client); client.setSoTimeout(15000);
                executor.submit(() -> { try { Exchange x = new Exchange(client); Handler h = handlers.get(x.path); if (h == null) respond(x, 404, "missing"); else h.handle(x); }
                    catch (Exception ignored) {} finally { clients.remove(client); try { client.close(); } catch (IOException ignored) {} } });
            } catch (IOException ignored) {}
        }); }
        void stop(int ignored) { try { socket.close(); for (Socket client : clients) client.close(); } catch (IOException ignoredError) {} executor.shutdownNow(); }
    }
    private static void respond(Exchange exchange, int code, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8); exchange.sendResponseHeaders(code, bytes.length);
        try (OutputStream out = exchange.getResponseBody()) { out.write(bytes); }
    }
    private static String read(InputStream stream) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); byte[] b = new byte[1024]; int n;
        while ((n = stream.read(b)) >= 0) { out.write(b, 0, n); if (out.size() > 1000000) throw new IOException("too large"); }
        return new String(out.toByteArray(), StandardCharsets.UTF_8);
    }
    private static void event(OutputStream out, String value) throws IOException {
        byte[] bytes = ("data: " + value + "\n\n").getBytes(StandardCharsets.UTF_8);
        for (byte b : bytes) out.write(b); out.flush();
    }
    public static void main(String[] args) throws Exception {
        int port = 8080; String alias = "model";
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].equals("--port")) port = Integer.parseInt(args[i + 1]);
            if (args[i].equals("--alias")) alias = args[i + 1];
        }
        String behavior = System.getenv("LMA_HOST_BEHAVIOR");
        if (Arrays.asList(args).contains("--occupy")) {
            try (ServerSocket occupied = new ServerSocket(port)) { System.out.println("exclusive port occupied"); System.out.flush(); Thread.sleep(60000); }
            return;
        }
        if ("crash".equals(behavior)) { System.err.println("Host fixture intentional exit"); System.exit(17); }
        String key = System.getenv("LLAMA_API_KEY"), model = "wrong-alias".equals(behavior) ? "foreign-model" : alias;
        Server server = new Server(port);
        server.createContext("/health", exchange -> respond(exchange, 200, "{\"status\":\"ok\"}"));
        server.createContext("/v1/models", exchange -> {
            if (!("Bearer " + key).equals(exchange.getRequestHeaders().getFirst("Authorization"))) { respond(exchange, 401, "{\"error\":{\"message\":\"Unauthorized\"}}"); return; }
            respond(exchange, 200, new JSONObject().put("data", new JSONArray().put(new JSONObject().put("id", model))).toString());
        });
        server.createContext("/v1/chat/completions", exchange -> {
            try {
                if (!("Bearer " + key).equals(exchange.getRequestHeaders().getFirst("Authorization"))) { respond(exchange, 401, "{\"error\":\"Unauthorized\"}"); return; }
                JSONObject payload = new JSONObject(read(exchange.getRequestBody())); JSONArray messages = payload.getJSONArray("messages");
                String prompt = messages.getJSONObject(messages.length() - 1).getString("content");
                for (int i = 1; i < messages.length(); i++) if (messages.getJSONObject(i).getString("role").equals("user") && messages.getJSONObject(i - 1).getString("role").equals("user")) {
                    respond(exchange, 400, "{\"error\":{\"message\":\"Consecutive user roles rejected by strict template\"}}"); return;
                }
                String path = System.getenv("LMA_HOST_LAST_REQUEST");
                if (path != null) Files.write(Paths.get(path), payload.toString().getBytes(StandardCharsets.UTF_8));
                if (prompt.equals("json-error")) { respond(exchange, 400, "{\"error\":{\"message\":\"Prompt is too long\"}}"); return; }
                if (prompt.equals("long-prefill")) Thread.sleep(8000);
                exchange.getResponseHeaders().set("Content-Type", "text/event-stream; charset=utf-8"); exchange.sendResponseHeaders(200, 0);
                try (OutputStream out = exchange.getResponseBody()) {
                    event(out, "{\"choices\":[{\"delta\":{\"reasoning_content\":\"思考片段\"}}]}");
                    event(out, "{\"choices\":[{\"delta\":{\"content\":\"你好🙂\"}}]}");
                    if (prompt.equals("broken")) { out.write("data: {\"choices\":".getBytes(StandardCharsets.UTF_8)); return; }
                    if (prompt.equals("sse-error")) { event(out, "{\"error\":{\"message\":\"Fixture streaming error\"}}"); return; }
                    if (prompt.equals("stop")) for (int i = 0; i < 300; i++) { event(out, "{\"choices\":[{\"delta\":{\"content\":\"片段\"}}]}"); Thread.sleep(20); }
                    event(out, "{\"choices\":[{\"delta\":{},\"finish_reason\":\"stop\"}],\"usage\":{\"completion_tokens\":7}}");
                    event(out, "[DONE]");
                }
            } catch (Exception ignored) { exchange.close(); }
        });
        Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
        server.start(); System.out.println("Host protocol fixture listening on " + port);
    }
}
