package com.lma.app.core;

import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.lang.reflect.Proxy;

/** Actual LMA HTTP/parser/output guard, synthetic native bytes; never loads a model or executes a client tool. */
public final class DshClientFixture {
    private static final JSONObject SETTINGS = new JSONObject().put("context", 131072).put("maxTokens", 2048).put("temperature", 0.6);
    public static void main(String[] args) throws Exception {
        final Path output = Paths.get(args[0]).toAbsolutePath();
        final JSONObject cases = new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])), StandardCharsets.UTF_8));
        Files.createDirectories(output);
        ThreadLocal<String> activeCase = new ThreadLocal<>();
        LocalApi.Runtime runtime = (LocalApi.Runtime)Proxy.newProxyInstance(LocalApi.Runtime.class.getClassLoader(), new Class<?>[]{LocalApi.Runtime.class}, (proxy, method, parameters) -> {
            if (method.getName().equals("apiKey")) return "fixture-not-a-secret";
            if (!method.getName().equals("text")) throw new UnsupportedOperationException("Fixture runtime operation unavailable: " + method.getName());
            String id = activeCase.get();
            JSONObject input = (JSONObject)parameters[1], request = TextRequest.normalize((String)parameters[0], input, "m15", SETTINGS);
            // These are synthetic histories/tool definitions, kept in ignored build output only.
            Files.write(output.resolve(id + "-request.json"), input.toString().getBytes(StandardCharsets.UTF_8));
            Files.write(output.resolve(id + "-normalized.json"), request.toString().getBytes(StandardCharsets.UTF_8));
            JSONObject fixture = cases.getJSONObject(id);
            return new LocalHttp.Response(200, "text/event-stream; charset=utf-8", -1, new LocalHttp.Body() {
                @Override public void write(OutputStream out) throws Exception {
                    int delay = fixture.optInt("comment_delay_ms");
                    for (int elapsed = 0; elapsed < delay; elapsed += 20) {
                        ToolReply.write(out, ": lma keepalive\n\n".getBytes(StandardCharsets.UTF_8));
                        Thread.sleep(Math.min(20, delay - elapsed));
                    }
                    byte[] bytes = fixture.getString("sse").getBytes(StandardCharsets.UTF_8);
                    InputStream source = new ByteArrayInputStream(bytes) {
                        @Override public synchronized int read(byte[] b, int off, int len) { return super.read(b, off, Math.min(3, len)); }
                    };
                    try { new ToolReply(request).stream(source, out); }
                    catch (Exception error) {
                        JSONObject detail = new JSONObject().put("message", LocalApi.safeMessage(error.getMessage())).put("type", "lma_local_error").put("code", "invalid_model_output").put("param", JSONObject.NULL);
                        ToolReply.write(out, ("data: " + new JSONObject().put("error", detail) + "\n\n").getBytes(StandardCharsets.UTF_8));
                    }
                }
            }).header("X-Request-ID", "lma-client-fixture-" + id).header("X-LMA-Max-Tokens", String.valueOf(request.getInt("max_tokens")));
        });
        LocalApi api = new LocalApi(runtime);
        try (LocalHttp server = new LocalHttp("127.0.0.1", 0, r -> {
            String id = r.header("x-lma-fixture-case");
            if (!id.matches("[a-z0-9_-]{1,80}") || !cases.has(id)) return LocalApi.error(400, "fixture_case", "Unknown fixture case");
            activeCase.set(id);
            try { return api.handle(r); }
            finally { activeCase.remove(); }
        })) {
            System.out.println(new JSONObject().put("port", server.port()).put("model_inference_tested", false));
            System.out.flush();
            // The parent closes stdin in finally; LocalHttp closes every socket and worker.
            while (System.in.read() != -1) { }
        }
    }
}
