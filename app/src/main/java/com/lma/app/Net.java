package com.lma.app;

import java.io.InputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONObject;

public final class Net {
    private Net() {}
    public interface ConnectionObserver { void opened(HttpURLConnection connection) throws IOException; }
    public static HttpURLConnection local(LmaApp app, String path) throws IOException {
        int port = app.prefs.getInt("port", 8080);
        HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        connection.setConnectTimeout(3000); connection.setReadTimeout(300000); connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("Authorization", "Bearer " + app.prefs.getString("apiKey", ""));
        connection.setRequestProperty("Accept", "application/json"); return connection;
    }
    public static HttpURLConnection engine(LmaApp app, String path) throws IOException {
        int port = app.nativePort; String key = app.nativeApiKey;
        if (port < 1 || key.isEmpty() || !path.startsWith("/") || path.startsWith("//")) throw new IOException("本机文本引擎未启动");
        HttpURLConnection connection = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        connection.setConnectTimeout(3000); connection.setReadTimeout(300000); connection.setInstanceFollowRedirects(false);
        connection.setRequestProperty("Authorization", "Bearer " + key);
        connection.setRequestProperty("Accept", "application/json"); return connection;
    }
    public static String errorBody(HttpURLConnection connection) {
        try (InputStream in = connection.getErrorStream()) {
            if (in == null) return "HTTP " + connection.getResponseCode();
            String raw = Store.read(in, 128 * 1024);
            try {
                JSONObject data = new JSONObject(raw); Object error = data.opt("error");
                if (error instanceof JSONObject) return ((JSONObject) error).optString("message", raw);
                return error == null ? raw : String.valueOf(error);
            } catch (Exception ignored) { return raw; }
        } catch (Exception error) { return "接口请求失败"; }
    }
    public static HttpURLConnection download(String address, long offset, String etag) throws Exception {
        return download(address, offset, etag, connection -> {});
    }
    public static HttpURLConnection download(String address, long offset, String etag, ConnectionObserver observer) throws Exception {
        return download(address, offset, etag, observer, 20000, 30000, "");
    }
    public static String[] modelSources(String address, String source) {
        if (!address.startsWith("https://huggingface.co/")) return new String[]{address};
        String mirror = "https://hf-mirror.com/" + address.substring("https://huggingface.co/".length());
        if (source.equals("mirror")) return new String[]{mirror};
        return source.equals("auto") ? new String[]{address, mirror} : new String[]{address};
    }
    static HttpURLConnection downloadCandidates(String[] addresses, long offset, String etag, ConnectionObserver observer) throws Exception {
        return downloadCandidates(addresses, offset, etag, observer, "");
    }
    static HttpURLConnection downloadCandidates(String[] addresses, long offset, String etag, ConnectionObserver observer, String token) throws Exception {
        for (int i = 0; i < addresses.length; i++) {
            boolean last = i == addresses.length - 1;
            try {
                HttpURLConnection connection = download(addresses[i], offset, etag, observer, last ? 20000 : 8000, last ? 30000 : 10000, token);
                int status = connection.getResponseCode();
                if (last || status == 200 || status == 206 || status == 416) { connection.setReadTimeout(30000); return connection; }
                connection.disconnect();
            } catch (Exception error) { if (last) throw error; }
        }
        throw new IOException("没有可用下载源");
    }
    static boolean acceptsHubToken(URL url) {
        return "https".equals(url.getProtocol()) && "huggingface.co".equalsIgnoreCase(url.getHost()) && url.getUserInfo() == null && (url.getPort() == -1 || url.getPort() == 443);
    }
    private static HttpURLConnection download(String address, long offset, String etag, ConnectionObserver observer, int connectTimeout, int readTimeout, String token) throws Exception {
        URL url = new URL(address);
        for (int redirect = 0; redirect < 9; redirect++) {
            if (!url.getProtocol().equals("https") || url.getUserInfo() != null) throw new IOException("下载地址必须使用 HTTPS");
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(connectTimeout); connection.setReadTimeout(readTimeout); connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("User-Agent", "LMA-Android/0.3.0-dev.3"); connection.setRequestProperty("Accept-Encoding", "identity");
            // Re-evaluate for every redirect. HF credentials never travel to mirrors, CDNs or custom hosts.
            if (!token.isEmpty() && acceptsHubToken(url)) connection.setRequestProperty("Authorization", "Bearer " + token);
            if (offset > 0) {
                connection.setRequestProperty("Range", "bytes=" + offset + "-");
                if (!etag.isEmpty() && !etag.startsWith("W/")) connection.setRequestProperty("If-Range", etag);
            }
            int status;
            try { observer.opened(connection); status = connection.getResponseCode(); }
            catch (IOException error) { connection.disconnect(); throw error; }
            if (status == 301 || status == 302 || status == 303 || status == 307 || status == 308) {
                String location = connection.getHeaderField("Location"); connection.disconnect();
                if (location == null) throw new IOException("下载源没有返回有效地址");
                url = new URL(url, location); continue;
            }
            return connection;
        }
        throw new IOException("下载地址重定向过多");
    }
}
