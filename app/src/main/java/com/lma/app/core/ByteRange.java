package com.lma.app.core;

import java.io.IOException;

/** One bounded RFC 9110 byte range for private media preview and API downloads. */
public final class ByteRange {
    public final long start, length;
    public final boolean partial;
    private ByteRange(long start, long length, boolean partial) { this.start = start; this.length = length; this.partial = partial; }
    public static ByteRange parse(String value, long size) throws IOException {
        if (size < 1) throw new IOException("Empty result");
        if (value == null || value.isEmpty()) return new ByteRange(0, size, false);
        if (!value.matches("bytes=(?:[0-9]+-[0-9]*|-[0-9]+)")) throw new IOException("Only one byte range is supported");
        String[] parts = value.substring(6).split("-", -1);
        try {
            long start, end;
            if (parts[0].isEmpty()) {
                long count = Long.parseLong(parts[1]);
                if (count < 1) throw new IOException("Empty suffix range");
                start = size - Math.min(count, size); end = size - 1;
            } else {
                start = Long.parseLong(parts[0]); end = parts[1].isEmpty() ? size - 1 : Math.min(size - 1, Long.parseLong(parts[1]));
            }
            if (start < 0 || start >= size || end < start) throw new IOException("Range is outside the result");
            return new ByteRange(start, end - start + 1, true);
        } catch (NumberFormatException invalid) { throw new IOException("Invalid byte range", invalid); }
    }
    public String contentRange(long size) { return "bytes " + start + "-" + (start + length - 1) + "/" + size; }
}
