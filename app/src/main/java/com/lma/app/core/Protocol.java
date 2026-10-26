package com.lma.app.core;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Shared, platform-independent streaming and HTTP range validation. */
public final class Protocol {
    private Protocol() {}
    public interface EventConsumer { boolean accept(String data) throws IOException; }

    public static void readSse(Reader source, EventConsumer consumer) throws IOException {
        BufferedReader reader = source instanceof BufferedReader ? (BufferedReader) source : new BufferedReader(source);
        StringBuilder data = new StringBuilder();
        String line;
        boolean first = true;
        while ((line = reader.readLine()) != null) {
            if (first && line.startsWith("\uFEFF")) line = line.substring(1);
            first = false;
            if (line.isEmpty()) {
                if (data.length() > 0) {
                    data.setLength(data.length() - 1);
                    if (!consumer.accept(data.toString())) return;
                    data.setLength(0);
                }
            } else if (line.startsWith("data:")) {
                String value = line.substring(5);
                if (value.startsWith(" ")) value = value.substring(1);
                data.append(value).append('\n');
                if (data.length() > 4 * 1024 * 1024) throw new IOException("SSE event is too large");
            }
        }
        // SSE events are dispatched at a blank line. A half-delivered event is not success.
        if (data.length() > 0) throw new IOException("SSE stream ended inside an event");
    }

    public static long[] parseContentRange(String value, long requestedOffset) throws IOException {
        if (value == null) throw new IOException("Missing Content-Range for resumed download");
        Matcher matcher = Pattern.compile("bytes ([0-9]+)-([0-9]+)/([0-9]+)").matcher(value.trim());
        if (!matcher.matches()) throw new IOException("Invalid Content-Range");
        try {
            long start = Long.parseLong(matcher.group(1));
            long end = Long.parseLong(matcher.group(2));
            long total = Long.parseLong(matcher.group(3));
            if (start != requestedOffset || start > end || end >= total) throw new IOException("Download range does not match saved data");
            return new long[]{start, end, total};
        } catch (NumberFormatException error) { throw new IOException("Content-Range overflow", error); }
    }

    public static String safeId(String value) {
        if (value == null || !value.matches("[A-Za-z0-9_-]{1,80}")) throw new IllegalArgumentException("Invalid model identifier");
        return value;
    }

    public static boolean isSha256(String value) { return value != null && value.matches("[a-fA-F0-9]{64}"); }

    public static String hex(byte[] bytes) {
        char[] out = new char[bytes.length * 2];
        char[] digits = "0123456789abcdef".toCharArray();
        for (int i = 0; i < bytes.length; i++) { out[i * 2] = digits[(bytes[i] & 255) >>> 4]; out[i * 2 + 1] = digits[bytes[i] & 15]; }
        return new String(out);
    }
}
