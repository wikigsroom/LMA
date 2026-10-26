import com.lma.app.core.Protocol;
import java.io.ByteArrayInputStream;
import java.io.FilterInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** No Android stubs: exercise real framing, partial network reads and range corruption. */
public final class ProtocolTest {
    private static int passed;
    private interface Checked { void run() throws Exception; }
    private static void check(boolean condition, String name) { if (!condition) throw new AssertionError(name); passed++; }
    private static void rejects(Checked call, String name) throws Exception {
        try { call.run(); } catch (IOException | IllegalArgumentException expected) { passed++; return; }
        throw new AssertionError("Expected rejection: " + name);
    }
    public static void main(String[] args) throws Exception {
        String transcript = "\uFEFF: heartbeat\r\nevent: message\r\ndata: {\"text\":\"你好🙂\"}\r\n\r\ndata: first\ndata: second\n\ndata:\n\ndata: [DONE]\n\n";
        FilterInputStream singleByteNetwork = new FilterInputStream(new ByteArrayInputStream(transcript.getBytes(StandardCharsets.UTF_8))) {
            @Override public int read(byte[] b, int offset, int length) throws IOException { return super.read(b, offset, Math.min(length, 1)); }
        };
        List<String> events = new ArrayList<>();
        Protocol.readSse(new InputStreamReader(singleByteNetwork, StandardCharsets.UTF_8), data -> { events.add(data); return !data.equals("[DONE]"); });
        check(events.equals(Arrays.asList("{\"text\":\"你好🙂\"}", "first\nsecond", "", "[DONE]")), "UTF-8 and multiline SSE survive one-byte reads");
        List<String> cancelled = new ArrayList<>();
        Protocol.readSse(new StringReader("data: one\n\ndata: two\n\n"), data -> { cancelled.add(data); return false; });
        check(cancelled.equals(Arrays.asList("one")), "Cancellation never dispatches a second chunk");
        rejects(() -> Protocol.readSse(new StringReader("data: broken\n"), data -> true), "Truncated event");
        rejects(() -> Protocol.readSse(new StringReader("data: broken"), data -> true), "Truncated final line");
        char[] excessive = new char[4 * 1024 * 1024 + 1]; Arrays.fill(excessive, 'x');
        rejects(() -> Protocol.readSse(new StringReader("data:" + new String(excessive) + "\n\n"), data -> true), "Bounded event size");
        check(Arrays.equals(Protocol.parseContentRange("bytes 1024-2047/4096", 1024), new long[]{1024, 2047, 4096}), "Resume exact offset");
        check(Arrays.equals(Protocol.parseContentRange("bytes 0-0/1", 0), new long[]{0, 0, 1}), "Single-byte file range");
        rejects(() -> Protocol.parseContentRange("bytes 0-2047/4096", 1024), "Wrong resume start must never append");
        rejects(() -> Protocol.parseContentRange("bytes 2048-1024/4096", 2048), "Reversed range");
        rejects(() -> Protocol.parseContentRange("bytes 1024-4096/4096", 1024), "End exceeds complete file");
        rejects(() -> Protocol.parseContentRange("bytes 0-1/999999999999999999999999", 0), "Integer overflow");
        rejects(() -> Protocol.parseContentRange("bytes 10-20/*", 10), "Unverifiable total");
        rejects(() -> Protocol.parseContentRange(null, 10), "Missing range header");
        for (String bad : Arrays.asList("../secret", "..", "a/b", "a\\b", "", "a%2fb", "name.gguf", "a\n")) rejects(() -> Protocol.safeId(bad), "File traversal: " + bad);
        check(Protocol.safeId("custom_abc-123").equals("custom_abc-123"), "Valid custom identifier");
        check(Protocol.hex(new byte[]{0, 15, 16, -1}).equals("000f10ff"), "Unsigned SHA hex encoding");
        check(Protocol.isSha256("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"), "Publisher SHA format");
        check(!Protocol.isSha256("abc") && !Protocol.isSha256(null), "Invalid SHA format");
        System.out.println("Protocol checks passed: " + passed);
    }
}
