package com.lma.app;

import com.sun.net.httpserver.HttpServer;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** A real host child and authenticated HTTP server returning literal test text, never model output. */
public final class TextServerFixture {
    public static void main(String[] args) throws Exception {
        String mode = args[0], record = args[1];
        if (mode.equals("exit")) return;
        Map<String, String> options = new HashMap<>();
        for (int i = 2; i < args.length - 1; i++) if (args[i].equals("--port") || args[i].equals("--alias")) options.put(args[i], args[++i]);
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", Integer.parseInt(options.get("--port"))), 1);
        server.setExecutor(Executors.newCachedThreadPool());
        server.createContext("/", exchange -> {
            try {
                if (!("Bearer " + System.getenv("LLAMA_API_KEY")).equals(exchange.getRequestHeaders().getFirst("Authorization"))) { exchange.sendResponseHeaders(401, -1); return; }
                String path = exchange.getRequestURI().getPath(), body;
                if (path.equals("/health")) body = "{\"status\":\"ok\"}";
                else if (path.equals("/v1/models")) body = new JSONObject().put("data", new org.json.JSONArray().put(new JSONObject().put("id", mode.equals("wrong-alias") ? "another-model" : options.get("--alias")))).toString();
                else if (path.equals("/v1/chat/completions")) {
                    ByteArrayOutputStream request = new ByteArrayOutputStream(); byte[] buffer = new byte[2048]; int n;
                    try (InputStream in = exchange.getRequestBody()) { while ((n = in.read(buffer)) != -1) { if (request.size() > 131072) throw new IOException("fixture request too large"); request.write(buffer, 0, n); } }
                    Files.write(Paths.get(record), request.toByteArray());
                    if (mode.equals("redirect")) { exchange.getResponseHeaders().set("Location", "https://example.invalid/no-inference"); exchange.sendResponseHeaders(302, -1); return; }
                    if (!mode.equals("missing-mime")) exchange.getResponseHeaders().set("Content-Type", "text/event-stream; charset=utf-8");
                    exchange.sendResponseHeaders(200, 0);
                    if (mode.equals("wait")) { while (true) Thread.sleep(100); }
                    body = mode.equals("error") ? "data: {\"error\":{\"message\":\"fixture-only-error\"}}\n\n" :
                        "data: {\"choices\":[{\"index\":0,\"delta\":{\"role\":\"assistant\"},\"finish_reason\":null}]}\n\n" +
                        "data: {\"choices\":[{\"index\":0,\"delta\":{\"reasoning_content\":\"literal reasoning fixture\"},\"finish_reason\":null}]}\n\n" +
                        "data: {\"choices\":[{\"index\":0,\"delta\":{\"content\":\"本机 HTTP 测试 <script>fixture</script>\"},\"finish_reason\":null}]}\n\n" +
                        "data: {\"choices\":[{\"index\":0,\"delta\":{},\"finish_reason\":\"stop\"}]}\n\n" +
                        "data: {\"choices\":[],\"usage\":{\"prompt_tokens\":10,\"completion_tokens\":7,\"total_tokens\":17}}\n\n" + (mode.equals("truncated") ? "" : "data: [DONE]\n\n");
                    byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
                    try (OutputStream out = exchange.getResponseBody()) { for (int at = 0; at < bytes.length; at += 7) { out.write(bytes, at, Math.min(7, bytes.length - at)); out.flush(); } }
                    return;
                } else { exchange.sendResponseHeaders(404, -1); return; }
                byte[] bytes = body.getBytes(StandardCharsets.UTF_8); exchange.getResponseHeaders().set("Content-Type", "application/json"); exchange.sendResponseHeaders(200, bytes.length); exchange.getResponseBody().write(bytes);
            } catch (Exception ignored) {} finally { exchange.close(); }
        });
        server.start(); new CountDownLatch(1).await();
    }
}
