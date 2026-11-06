package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

/** Protocol, real streaming bytes and bounded concurrent sockets; no model execution. */
public final class OpenAiToolsTest {
    private static final List<String> checks = new ArrayList<>();
    private static final JSONObject SETTINGS = new JSONObject().put("context", 8192).put("maxTokens", 2048).put("temperature", 0.6);
    interface Action { void run() throws Exception; }
    static void check(boolean ok, String label) { if (!ok) throw new AssertionError(label); checks.add(label); }
    static void rejects(Action action, String label) throws Exception { try { action.run(); throw new AssertionError(label); } catch (IllegalArgumentException | IOException expected) { checks.add(label); } }
    static JSONObject base() { return new JSONObject().put("model", "m15").put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", "Use the supplied client tool"))); }
    static JSONObject function(String name, boolean strict) { return new JSONObject().put("type", "function").put("function", new JSONObject().put("name", name).put("strict", strict).put("parameters", new JSONObject("{\"type\":\"object\",\"properties\":{\"city\":{\"type\":\"string\",\"enum\":[\"台北\",\"Paris\"]}},\"required\":[\"city\"],\"additionalProperties\":false}"))); }
    static JSONObject normalize(JSONObject request) throws Exception { return TextRequest.normalize("/v1/chat/completions", request, "m15", SETTINGS); }
    static JSONObject call(String id, String name, String arguments) { return new JSONObject().put("id", id).put("type", "function").put("function", new JSONObject().put("name", name).put("arguments", arguments)); }
    static JSONObject completion(JSONArray calls, String finish) { return new JSONObject().put("id", "chatcmpl-fixture").put("object", "chat.completion").put("choices", new JSONArray().put(new JSONObject().put("index", 0).put("finish_reason", finish).put("message", new JSONObject().put("role", "assistant").put("content", JSONObject.NULL).put("tool_calls", calls)))); }
    static InputStream input(String text) { byte[] bytes = text.getBytes(StandardCharsets.UTF_8); return new ByteArrayInputStream(bytes) { @Override public synchronized int read(byte[] b, int off, int len) { return super.read(b, off, Math.min(3, len)); } }; }
    static String event(JSONObject delta, String finish) { return "data: " + new JSONObject().put("id", "chatcmpl-fixture").put("object", "chat.completion.chunk").put("choices", new JSONArray().put(new JSONObject().put("index", 0).put("delta", delta).put("finish_reason", finish == null ? JSONObject.NULL : finish))) + "\n\n"; }
    static String toolStream(String id, String name, String arguments) {
        StringBuilder out = new StringBuilder(event(new JSONObject().put("role", "assistant"), null));
        out.append(event(new JSONObject().put("tool_calls", new JSONArray().put(call(id, name, "").put("index", 0))), null));
        for (int i = 0; i < arguments.length(); i++) out.append(event(new JSONObject().put("tool_calls", new JSONArray().put(new JSONObject().put("index", 0).put("function", new JSONObject().put("arguments", arguments.substring(i, i + 1))))), null));
        return out.append(event(new JSONObject(), "tool_calls")).append("data: {\"choices\":[],\"usage\":{\"prompt_tokens\":20,\"completion_tokens\":8,\"total_tokens\":28}}\n\ndata: [DONE]\n\n").toString();
    }
    static byte[] response(ToolReply guard, String text) throws Exception { return guard.complete(input(text)); }
    static String stream(ToolReply guard, String text) throws Exception { ByteArrayOutputStream out = new ByteArrayOutputStream(); guard.stream(input(text), out); return new String(out.toByteArray(), StandardCharsets.UTF_8); }
    public static void main(String[] args) throws Exception {
        JSONObject request = base().put("tools", new JSONArray().put(function("weather", true))).put("store", false).put("parallel_tool_calls", false);
        JSONObject normalized = normalize(request); check(!normalized.has("store") && !request.isNull("store"), "store:false is consumed without mutating the caller request");
        check(normalized.getString("tool_choice").equals("auto") && !normalized.getBoolean("parallel_tool_calls"), "Auto tools and parallel false retain their meaning");
        for (String choice : Arrays.asList("none", "auto", "required")) check(normalize(new JSONObject(request.toString()).put("tool_choice", choice)).getString("tool_choice").equals(choice), "Tool choice " + choice + " is supported");
        JSONObject named = base().put("tools", new JSONArray().put(function("weather", false)).put(function("other", false))).put("tool_choice", new JSONObject("{\"type\":\"function\",\"function\":{\"name\":\"other\"}}"));
        JSONObject forced = normalize(named);
        check(forced.getJSONArray("tools").length() == 2 && NativeToolRequest.selected(forced).equals("other"), "Named choice retains the complete public tool list and selection");
        JSONObject wire = NativeToolRequest.adapt(forced);
        check(wire.getString("tool_choice").equals("required") && wire.getJSONArray("tools").length() == 1 && wire.getJSONObject("chat_template_kwargs").getJSONArray("tools").length() == 2, "Native grammar selects one function while template context retains every declaration");
        check(named.getJSONArray("tools").length() == 2 && forced.getJSONArray("tools").length() == 2, "Private native adaptation never mutates either public request");
        JSONArray completeTools = new JSONArray(); for (int i = 0; i < 41; i++) completeTools.put(function("fixture_" + i, false));
        JSONObject fullNamed = normalize(base().put("tools", completeTools).put("tool_choice", new JSONObject().put("type", "function").put("function", new JSONObject().put("name", "fixture_40"))));
        check(NativeToolRequest.adapt(fullNamed).getJSONObject("chat_template_kwargs").getJSONArray("tools").length() == 41 && fullNamed.getJSONArray("tools").length() == 41, "All 41 declarations survive named-function adaptation");
        rejects(() -> response(new ToolReply(forced), completion(new JSONArray().put(call("wrong_named", "weather", "{}")), "tool_calls").toString()), "A declared but nonselected function is rejected for named choice");
        ByteArrayOutputStream namedOutput = new ByteArrayOutputStream();
        rejects(() -> new ToolReply(forced).stream(input(toolStream("wrong_named_stream", "weather", "{}")), namedOutput), "Named streaming rejects a wrong function even without strict arguments");
        check(!new String(namedOutput.toByteArray(), StandardCharsets.UTF_8).contains("wrong_named_stream"), "Invalid named tool fragments never reach the client executor");
        rejects(() -> normalize(base().put("chat_template_kwargs", new JSONObject().put("tools", completeTools))), "Clients cannot override private template context");
        rejects(() -> normalize(base().put("store", true)), "Unsupported stored-completion semantics fail explicitly");
        rejects(() -> normalize(base().put("tool_choice", "required")), "Required choice without definitions is invalid");
        rejects(() -> normalize(new JSONObject(named.toString()).put("tool_choice", new JSONObject("{\"type\":\"function\",\"function\":{\"name\":\"missing\"}}"))), "Named selection must refer to a declared function");
        try { normalize(base().put("unsupported_fixture", 1)); throw new AssertionError(); } catch (RequestError error) { check(error.param.equals("unsupported_fixture"), "Unknown fields identify the offending parameter"); }
        JSONObject optional = base().put("temperature", JSONObject.NULL).put("stream", JSONObject.NULL).put("metadata", new JSONObject().put("source", "fixture")).put("user", "fixture");
        check(normalize(optional).getDouble("temperature") == 0.6 && !normalize(optional).has("metadata"), "Nullable optional fields and nonpersistent caller hints are accepted");
        JSONArray history = base().getJSONArray("messages"); history.put(new JSONObject().put("role", "assistant").put("content", JSONObject.NULL).put("tool_calls", new JSONArray().put(call("call_a", "weather", "{\"city\":\"台北\"}")))); history.put(new JSONObject().put("role", "tool").put("tool_call_id", "call_a").put("content", "晴天"));
        check(normalize(base().put("messages", history)).getJSONArray("messages").getJSONObject(1).isNull("content"), "Assistant null content and client-owned tool results round-trip structurally");
        JSONArray parallel = new JSONArray().put(new JSONObject().put("role", "user").put("content", "compare"))
            .put(new JSONObject().put("role", "assistant").put("content", JSONObject.NULL).put("tool_calls",new JSONArray().put(call("parallel_a", "weather", "{}" )).put(call("parallel_b", "weather", "{}"))))
            .put(new JSONObject().put("role", "tool").put("tool_call_id", "parallel_b").put("content", "second result"))
            .put(new JSONObject().put("role", "tool").put("tool_call_id", "parallel_a").put("content", "first result"));
        JSONObject unordered = normalize(base().put("messages", parallel)), ordered = NativeToolRequest.adapt(unordered);
        check(ordered.getJSONArray("messages").getJSONObject(2).getString("content").equals("first result") && ordered.getJSONArray("messages").getJSONObject(3).getString("content").equals("second result"), "Native rendering orders parallel results by their actual call IDs");
        check(unordered.getJSONArray("messages").getJSONObject(2).getString("tool_call_id").equals("parallel_b"), "Parallel result adaptation preserves the original public history");
        JSONObject missing = new JSONObject(base().put("messages", history).toString()); missing.getJSONArray("messages").remove(2);
        rejects(() -> normalize(missing), "Missing tool results are rejected before generation");
        JSONObject orphan = new JSONObject(base().put("messages", history).toString()); orphan.getJSONArray("messages").getJSONObject(2).put("tool_call_id", "orphan");
        rejects(() -> normalize(orphan), "Orphan tool-call IDs are rejected");
        JSONObject repeated = new JSONObject(base().put("messages", history).toString()); repeated.getJSONArray("messages").put(repeated.getJSONArray("messages").getJSONObject(2));
        rejects(() -> normalize(repeated), "Duplicate tool results are rejected");
        JSONArray blocks = new JSONArray().put(new JSONObject().put("type", "text").put("text", "hello"));
        check(normalize(base().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", blocks)))).getJSONArray("messages").length() == 1, "Plain text content parts are accepted");
        rejects(() -> normalize(base().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", new JSONArray().put(new JSONObject().put("type", "image_url").put("image_url", "https://example.invalid/")))))), "The text tool route never fetches media URLs");
        JSONArray many = new JSONArray(); for (int i = 0; i < 129; i++) many.put(new JSONObject().put("role", i % 2 == 0 ? "user" : "assistant").put("content", "x"));
        check(normalize(base().put("messages", many)).getJSONArray("messages").length() == 129, "Valid short histories can exceed the former 128-message limit");
        while (many.length() < 1025) many.put(new JSONObject().put("role", "user").put("content", "x"));
        rejects(() -> normalize(base().put("messages", many)), "Message count remains bounded at 1024");
        char[] chars = new char[64001]; Arrays.fill(chars, 'x');
        check(normalize(base().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", new String(chars))))).has("messages"), "Long messages are governed by bytes and context rather than the former 64000-unit cap");
        JSONObject schema = new JSONObject("{\"type\":\"object\",\"properties\":{\"city\":{\"type\":\"string\",\"enum\":[\"台北\"]},\"n\":{\"type\":\"integer\",\"minimum\":1,\"maximum\":3},\"nested\":{\"type\":\"array\",\"items\":{\"type\":\"boolean\"},\"minItems\":1}},\"required\":[\"city\",\"n\",\"nested\"],\"additionalProperties\":false}");
        JsonSchema.check(schema, "fixture"); JsonSchema.validate(schema, new JSONObject("{\"city\":\"台北\",\"n\":2,\"nested\":[true]}")); check(true, "Nested object/array/number/string schema constraints accept valid arguments");
        for (String bad : Arrays.asList("{\"city\":\"Paris\",\"n\":2,\"nested\":[true]}", "{\"city\":\"台北\",\"n\":9,\"nested\":[true]}", "{\"city\":\"台北\",\"n\":2}", "{\"city\":\"台北\",\"n\":2,\"nested\":[1]}", "{\"city\":\"台北\",\"n\":2,\"nested\":[true],\"extra\":1}")) rejects(() -> JsonSchema.validate(schema, new JSONObject(bad)), "Strict schema rejects invalid arguments case " + checks.size());
        JSONObject refs = new JSONObject("{\"$defs\":{\"v\":{\"type\":\"string\",\"enum\":[\"yes\"]}},\"type\":\"object\",\"properties\":{\"v\":{\"$ref\":\"#/$defs/v\"}},\"required\":[\"v\"]}");
        JsonSchema.check(refs, "fixture"); JsonSchema.validate(refs, new JSONObject().put("v", "yes")); check(true, "Document-local schema definitions are resolved");
        rejects(() -> JsonSchema.check(new JSONObject().put("$ref", "https://example.invalid/schema"), "fixture"), "Schema references never fetch remote documents");
        rejects(() -> JsonSchema.check(new JSONObject().put("pattern", "(a+)+$"), "fixture"), "Unbounded nested regex repetition is rejected");
        ToolReply guard = new ToolReply(normalized); String arguments = "{\"city\":\"台北\"}";
        check(response(guard, completion(new JSONArray().put(call("call_1", "weather", arguments)), "tool_calls").toString()).length > 0, "Tool-only nonstream responses permit null assistant content");
        String streamed = stream(guard, toolStream("call_1", "weather", arguments));
        check(streamed.contains("[DONE]") && streamed.contains("usage") && streamed.contains("tool_calls"), "Strict streamed tool calls survive three-byte UTF-8 reads, usage-only chunks and DONE");
        check(streamed.contains("call_1") && streamed.contains("weather"), "Tool-call IDs and function names survive streaming");
        ByteArrayOutputStream withheld = new ByteArrayOutputStream();
        rejects(() -> guard.stream(input(toolStream("call_bad", "weather", "{\"city\":\"not-in-enum\"}")), withheld), "Strict output rejects native string-enum violations");
        check(!new String(withheld.toByteArray(), StandardCharsets.UTF_8).contains("tool_calls"), "Invalid strict calls are withheld before any executable tool delta reaches the client");
        for (String nonJson : Arrays.asList("{'city':'台北'}", "{city:\"台北\"}", "{\"city\":\"台北\",}", "{\"city\":\"台北\"} false")) rejects(() -> response(guard, completion(new JSONArray().put(call("bad_json", "weather", nonJson)), "tool_calls").toString()), "Strict calls reject nonstandard or trailing JSON case " + checks.size());
        JSONObject repeatedNameRequest = normalize(base().put("tools", new JSONArray().put(function("abab", true))));
        String splitName = toolStream("split_name", "abab", arguments).replace("\"name\":\"abab\"", "\"name\":\"ab\"");
        int nameEnd = splitName.indexOf("\n\n", splitName.indexOf("split_name")) + 2;
        splitName = splitName.substring(0, nameEnd) + event(new JSONObject().put("tool_calls", new JSONArray().put(new JSONObject().put("index", 0).put("function", new JSONObject().put("name", "ab")))), null) + splitName.substring(nameEnd);
        check(stream(new ToolReply(repeatedNameRequest), splitName).contains("[DONE]"), "Repeated equal function-name fragments concatenate without losing a segment");
        rejects(() -> response(guard, completion(new JSONArray().put(call("call_1", "missing", arguments)), "tool_calls").toString()), "Hallucinated undeclared functions are rejected");
        rejects(() -> stream(guard, toolStream("call_1", "weather", arguments).replace("data: [DONE]\n\n", "")), "Interrupted streams cannot claim successful completion");
        JSONObject two = completion(new JSONArray().put(call("a", "weather", arguments)).put(call("b", "weather", arguments)), "tool_calls");
        rejects(() -> response(guard, two.toString()), "parallel_tool_calls:false forbids a second native call");
        check(response(new ToolReply(normalize(new JSONObject(request.toString()).put("parallel_tool_calls", true))), two.toString()).length > 0, "Parallel native function calls are supported when enabled");
        JSONObject noCalls = completion(new JSONArray(), "stop");
        rejects(() -> response(new ToolReply(normalize(new JSONObject(request.toString()).put("tool_choice", "required"))), noCalls.toString()), "Required choice cannot silently turn into a plain answer");
        TextAdmission admission = new TextAdmission(); List<TextAdmission.Lease> leases = new ArrayList<>();
        for (int i = 0; i < TextAdmission.MAX_REQUESTS; i++) leases.add(admission.acquire(1));
        rejects(() -> admission.acquire(1), "Text admission has a bounded request count");
        for (TextAdmission.Lease lease : leases) { lease.close(); lease.close(); }
        check(admission.snapshot().getInt("requests") == 0, "Text admission release is idempotent");
        try (TextAdmission.Lease lease = admission.acquire(TextAdmission.MAX_BYTES)) { rejects(() -> admission.acquire(1), "Text admission also enforces total request bytes"); }
        sockets();
        System.out.println(new JSONObject().put("passed", checks.size()).put("checks", new JSONArray(checks)).put("actual_socket_io", true).put("model_inference_tested", false).put("physical_device", false));
    }
    static HttpURLConnection connect(int port, String path) throws Exception { HttpURLConnection c = (HttpURLConnection)new URL("http://127.0.0.1:" + port + path).openConnection(); c.setReadTimeout(10000); c.setConnectTimeout(2000); return c; }
    static void sockets() throws Exception {
        CountDownLatch entered = new CountDownLatch(9), release = new CountDownLatch(1); ExecutorService clients = Executors.newFixedThreadPool(9); List<Future<Integer>> futures = new ArrayList<>();
        try (LocalHttp server = new LocalHttp("127.0.0.1", 0, r -> {
            if (r.path.equals("/v1/chat/completions")) { if (r.query("hold").equals("yes")) { entered.countDown(); release.await(); } return LocalApi.json(200, new JSONObject().put("bytes", r.body.length)); }
            return LocalApi.json(200, new JSONObject().put("ok", true));
        })) {
            for (int i = 0; i < 9; i++) futures.add(clients.submit(() -> { HttpURLConnection c = connect(server.port(), "/v1/chat/completions?hold=yes"); try { c.setRequestMethod("POST"); c.setDoOutput(true); c.setFixedLengthStreamingMode(2); try (OutputStream out = c.getOutputStream()) { out.write("{}".getBytes(StandardCharsets.UTF_8)); } return c.getResponseCode(); } finally { c.disconnect(); } }));
            check(entered.await(5, TimeUnit.SECONDS), "Nine concurrent text sockets enter their dedicated bounded pool");
            HttpURLConnection health = connect(server.port(), "/health"); try { check(health.getResponseCode() == 200, "Control requests remain available while all text workers wait"); } finally { health.disconnect(); }
            HttpURLConnection overflow = connect(server.port(), "/v1/chat/completions"); try { overflow.setRequestMethod("POST"); overflow.setDoOutput(true); overflow.setFixedLengthStreamingMode(2); try (OutputStream out = overflow.getOutputStream()) { out.write("{}".getBytes(StandardCharsets.UTF_8)); } check(overflow.getResponseCode() == 429 && "1".equals(overflow.getHeaderField("Retry-After")), "Text pool overflow returns structured retryable 429"); } finally { overflow.disconnect(); }
            release.countDown(); for (Future<Integer> future : futures) check(future.get(5, TimeUnit.SECONDS) == 200, "Admitted concurrent text socket completes");
            byte[] large = new byte[300000]; Arrays.fill(large, (byte)' '); HttpURLConnection body = connect(server.port(), "/v1/chat/completions"); try { body.setRequestMethod("POST"); body.setDoOutput(true); body.setFixedLengthStreamingMode(large.length); try (OutputStream out = body.getOutputStream()) { out.write(large); } check(body.getResponseCode() == 200, "Text transport accepts bodies larger than the former 256 KiB cap"); } finally { body.disconnect(); }
            HttpURLConnection upload = connect(server.port(), "/v1/uploads/fixture"); try { upload.setRequestMethod("PUT"); upload.setDoOutput(true); upload.setFixedLengthStreamingMode(large.length); try (OutputStream out = upload.getOutputStream()) { out.write(large); } check(upload.getResponseCode() == 413, "Binary upload chunk limits remain independent of text capacity"); } finally { upload.disconnect(); }
        } finally { release.countDown(); clients.shutdownNow(); }
    }
}
