package com.lma.app;

import com.lma.app.core.Protocol;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.json.JSONArray;
import org.json.JSONObject;

/** HF discovery is independent of the offline recommendation list. No model code is executed. */
public final class HubClient {
    public static final String ORIGIN = "https://huggingface.co";
    public static final long MAX_FILE = 12L * 1024 * 1024 * 1024;
    private static final Pattern REPO = Pattern.compile("[A-Za-z0-9][A-Za-z0-9_.-]{0,95}/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}");
    private static final Pattern NEXT = Pattern.compile("<([^>]+)>\\s*;\\s*rel=\"next\"");
    private static final Pattern QUANT = Pattern.compile("(?i)(?:IQ|TQ|Q)[0-9]+(?:_[A-Z0-9]+)*|BF16|F16|F32|MXFP4");
    public interface Transport { Response get(String address, String source, String token) throws Exception; }
    public static final class Response {
        public final String body, link, origin;
        public Response(String body, String link, String origin) { this.body = body; this.link = link; this.origin = origin; }
    }
    private final String source, token;
    private final Transport transport;
    public HubClient(String source, String token) { this(source, token, HubClient::request); }
    public HubClient(String source, String token, Transport transport) { this.source = source; this.token = token; this.transport = transport; }
    private static Response request(String address, String source, String token) throws Exception {
        String[] candidates = token.isEmpty() ? Net.modelSources(address, source) : new String[]{address};
        HttpURLConnection connection = Net.downloadCandidates(candidates, 0, "", opened -> {
            if (Thread.currentThread().isInterrupted()) throw new IOException("搜索已取消");
        }, token);
        try {
            int status = connection.getResponseCode();
            if (status == 401 || status == 403) throw new IOException("仓库需要访问授权；可在设置中保存 HF 令牌，并先在 HF 接受模型许可");
            if (status == 404) throw new IOException("未找到仓库或当前身份没有权限，请检查仓库名");
            if (status == 429) throw new IOException("HF 请求过于频繁，请稍后重试");
            if (status != 200) throw new IOException("HF 返回 HTTP " + status + "，可重试或切换下载源");
            try (InputStream input = connection.getInputStream()) {
                return new Response(Store.read(input, 8 * 1024 * 1024), connection.getHeaderField("Link"), connection.getURL().getHost());
            }
        } finally { connection.disconnect(); }
    }
    private static String encode(String value) throws Exception { return URLEncoder.encode(value, "UTF-8").replace("+", "%20"); }
    public static String repositoryId(String value) {
        if (value == null || !REPO.matcher(value).matches() || value.contains("..")) throw new IllegalArgumentException("请使用 owner/model 格式的 HF 仓库名");
        return value;
    }
    public static String query(String value) throws Exception {
        String text = value.trim();
        if (text.length() > 240) throw new IllegalArgumentException("搜索内容过长");
        if (text.startsWith("https://")) {
            URI uri = new URI(text);
            if (uri.getUserInfo() != null || uri.getPort() != -1 || !("huggingface.co".equals(uri.getHost()) || "hf.co".equals(uri.getHost()) || "hf-mirror.com".equals(uri.getHost())))
                throw new IllegalArgumentException("请输入 HF 模型仓库链接");
            String[] parts = uri.getPath().split("/");
            if (parts.length < 3) throw new IllegalArgumentException("链接中没有模型仓库名");
            return repositoryId(parts[1] + "/" + parts[2]);
        }
        return text;
    }
    private static String next(String link, String prefix) throws Exception {
        if (link == null) return "";
        Matcher found = NEXT.matcher(link);
        return found.find() ? validPage(found.group(1), prefix) : "";
    }
    public static String validPage(String address, String prefix) throws Exception {
        if (address.length() > 16000) throw new IOException("分页链接过长");
        URI uri = new URI(address);
        if (!"https".equals(uri.getScheme()) || uri.getUserInfo() != null || uri.getPort() != -1 || uri.getFragment() != null ||
                !("huggingface.co".equals(uri.getHost()) || "hf-mirror.com".equals(uri.getHost())) || !prefix.equals(uri.getPath()))
            throw new IOException("HF 返回了无效的分页链接");
        return ORIGIN + uri.getRawPath() + (uri.getRawQuery() == null ? "" : "?" + uri.getRawQuery());
    }
    public static JSONObject uncensored(String id, JSONArray tags) throws Exception {
        StringBuilder text = new StringBuilder(id.toLowerCase(Locale.ROOT));
        if (tags != null) for (int i = 0; i < Math.min(tags.length(), 200); i++) text.append(' ').append(tags.optString(i).toLowerCase(Locale.ROOT));
        boolean detected = Pattern.compile("uncensored|abliterat|(?:^|[/ _-])dolphin[0-9._ -]").matcher(text).find();
        return new JSONObject().put("declared", false).put("detected", detected).put("basis", "repository-metadata")
                .put("summary", "根据仓库名称或标签识别，未逐项核对作者声明或测量拒答率").put("refusalRateTested", false);
    }
    public static JSONObject model(JSONObject data) throws Exception {
        String id = repositoryId(data.optString("id", data.optString("modelId")));
        JSONArray tags = data.optJSONArray("tags"); if (tags == null) tags = new JSONArray();
        JSONObject card = data.optJSONObject("cardData");
        return new JSONObject().put("id", id).put("downloads", data.optLong("downloads")).put("likes", data.optLong("likes"))
                .put("task", data.optString("pipeline_tag")).put("taskTags", outputTasks(data.optString("pipeline_tag"))).put("taskEvidence", "hf_metadata")
                .put("library", data.optString("library_name"))
                .put("gated", data.has("gated") && !"false".equals(String.valueOf(data.opt("gated"))) && !data.isNull("gated"))
                .put("revision", data.optString("sha")).put("license", card == null ? "" : card.optString("license"))
                .put("uncensored", uncensored(id, tags)).put("sourceUrl", ORIGIN + "/" + id);
    }
    public static JSONArray outputTasks(String task) {
        JSONArray tags = new JSONArray();
        switch (task) {
            case "text-generation": case "text2text-generation": case "image-text-to-text": case "conversational": tags.put("text"); break;
            case "text-to-image": case "image-to-image": tags.put("image"); break;
            case "text-to-video": case "image-to-video": case "video-to-video": tags.put("video"); break;
            case "text-to-audio": case "text-to-speech": case "audio-to-audio": tags.put("audio"); break;
            default: break;
        }
        return tags;
    }
    public JSONObject search(String search, String format, String sort, String cursor) throws Exception {
        String text = query(search);
        if (!format.equals("gguf") && !format.equals("all")) throw new IllegalArgumentException("未知格式筛选");
        if (!sort.equals("downloads") && !sort.equals("likes") && !sort.equals("lastModified")) throw new IllegalArgumentException("未知排序方式");
        if (cursor.isEmpty() && REPO.matcher(text).matches()) {
            Response response = transport.get(ORIGIN + "/api/models/" + repositoryId(text), source, token);
            return new JSONObject().put("items", new JSONArray().put(model(new JSONObject(response.body)))).put("next", "").put("origin", response.origin);
        }
        String address = cursor.isEmpty() ? ORIGIN + "/api/models?limit=24&full=true&sort=" + sort + "&direction=-1&search=" + encode(text) + (format.equals("gguf") ? "&filter=gguf" : "") : validPage(cursor, "/api/models");
        Response response = transport.get(address, source, token);
        JSONArray raw = new JSONArray(response.body), items = new JSONArray();
        for (int i = 0; i < raw.length(); i++) { try { items.put(model(raw.getJSONObject(i))); } catch (IllegalArgumentException ignored) {} }
        return new JSONObject().put("items", items).put("next", next(response.link, "/api/models")).put("origin", response.origin);
    }
    public JSONObject repository(String id) throws Exception {
        Response response = transport.get(ORIGIN + "/api/models/" + repositoryId(id), source, token);
        JSONObject result = model(new JSONObject(response.body));
        if (!result.getString("revision").matches("[a-f0-9]{40}")) throw new IOException("仓库没有可固定的提交版本");
        return result;
    }
    public JSONObject files(JSONObject repository, String cursor) throws Exception {
        String id = repositoryId(repository.getString("id")), revision = repository.getString("revision");
        if (!revision.matches("[a-f0-9]{40}")) throw new IOException("无效的仓库提交");
        String prefix = "/api/models/" + id + "/tree/" + revision;
        String address = cursor.isEmpty() ? ORIGIN + prefix + "?recursive=true&limit=100" : validPage(cursor, prefix);
        Response response = transport.get(address, source, token);
        JSONArray raw = new JSONArray(response.body), files = new JSONArray(), assets = new JSONArray();
        for (int i = 0; i < raw.length(); i++) {
            JSONObject entry = raw.getJSONObject(i);
            String path = entry.optString("path");
            if (entry.optString("type").equals("file")) try { assets.put(asset(repository, entry)); } catch (IllegalArgumentException ignored) {}
            if (!entry.optString("type").equals("file") || !path.toLowerCase(Locale.ROOT).endsWith(".gguf")) continue;
            try { files.put(file(repository, entry)); } catch (IllegalArgumentException ignored) {}
        }
        return new JSONObject().put("items", files).put("assets", assets).put("next", next(response.link, prefix)).put("origin", response.origin);
    }
    public static JSONObject file(JSONObject repository, JSONObject entry) throws Exception {
        String id = repositoryId(repository.getString("id")), revision = repository.getString("revision"), path = entry.getString("path");
        if (!revision.matches("[a-f0-9]{40}") || path.length() > 1000 || path.startsWith("/") || path.contains("\\") || path.contains("\0") || path.matches(".*[\\r\\n].*")) throw new IllegalArgumentException("无效的模型文件路径");
        StringBuilder encoded = new StringBuilder();
        for (String part : path.split("/", -1)) { if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IllegalArgumentException("无效的文件路径"); if (encoded.length() > 0) encoded.append('/'); encoded.append(encode(part)); }
        String lower = path.toLowerCase(Locale.ROOT), blocked = "", task = repository.optString("task");
        if (!lower.endsWith(".gguf")) throw new IllegalArgumentException("请选择 GGUF 文件");
        if (lower.contains("mmproj") || lower.contains("projector")) blocked = "视觉投影文件不能单独作为文本模型加载";
        if (lower.matches(".*-[0-9]{5}-of-[0-9]{5}\\.gguf")) blocked = "当前版本需要单文件 GGUF；此文件属于分片模型";
        if (!task.isEmpty() && !task.equals("text-generation") && !task.equals("conversational") && !task.equals("image-text-to-text")) blocked = "当前引擎接口用于文本对话，未接入此任务类型";
        long bytes = entry.optLong("size");
        if (bytes <= 0) blocked = "文件大小尚不可用，请刷新仓库";
        if (bytes > MAX_FILE) blocked = "文件超过当前单文件 12 GiB 上限";
        JSONObject lfs = entry.optJSONObject("lfs");
        String hash = lfs == null ? "" : lfs.optString("oid", lfs.optString("sha256"));
        if (hash.startsWith("sha256:")) hash = hash.substring(7);
        if (!hash.isEmpty() && !Protocol.isSha256(hash)) throw new IllegalArgumentException("HF 文件哈希格式无效");
        Matcher quant = QUANT.matcher(path); String quantization = quant.find() ? quant.group().toUpperCase(Locale.ROOT) : "GGUF";
        return new JSONObject().put("path", path).put("bytes", bytes).put("sha256", hash).put("quant", quantization)
                .put("url", ORIGIN + "/" + id + "/resolve/" + revision + "/" + encoded).put("blocked", blocked);
    }
    /** Data-file metadata only. Browsing never reads weights, tokenizers or vocabulary content. */
    public static JSONObject asset(JSONObject repository, JSONObject entry) throws Exception {
        String id = repositoryId(repository.getString("id")), revision = repository.getString("revision"), path = entry.getString("path");
        if (!revision.matches("[a-f0-9]{40}") || path.isEmpty() || path.length() > 1000 || path.indexOf('\\') >= 0 || path.chars().anyMatch(c -> c < 32 || c == 127)) throw new IllegalArgumentException("Invalid HF component identity");
        StringBuilder encoded = new StringBuilder();
        for (String part : path.split("/", -1)) { if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IllegalArgumentException("Invalid HF component path"); if (encoded.length() > 0) encoded.append('/'); encoded.append(encode(part)); }
        String lower = path.toLowerCase(Locale.ROOT), format = "unknown", blocked = "";
        for (String extension : new String[]{"gguf", "safetensors", "onnx", "bin", "json", "fst", "far", "tflite"}) if (lower.endsWith("." + extension)) format = extension;
        if (lower.endsWith(".txt") || lower.endsWith(".vocab")) format = "text";
        if (lower.endsWith(".model")) format = "sentencepiece";
        if (lower.endsWith(".data")) format = "onnx_data";
        if (lower.endsWith(".mnn")) format = "mnn";
        if (lower.endsWith(".mnn.weight")) format = "mnn_data";
        if (format.equals("unknown")) blocked = "此文件不是当前配方接入的组件格式";
        Object declaredSize = entry.opt("size"); long bytes = declaredSize instanceof Number ? ((Number) declaredSize).longValue() : 0;
        if (!(declaredSize instanceof Number) || ((Number) declaredSize).doubleValue() != bytes || bytes < 1 || bytes > 128L * 1024 * 1024 * 1024) blocked = "组件大小未声明或超出存储范围";
        JSONObject lfs = entry.optJSONObject("lfs"); String sha = "", git = "";
        if (lfs != null) {
            sha = lfs.optString("oid", lfs.optString("sha256")); if (sha.startsWith("sha256:")) sha = sha.substring(7);
            if (!Protocol.isSha256(sha)) { sha = ""; blocked = "大文件缺少可固定的 SHA256"; }
            if (lfs.has("size") && lfs.getLong("size") != bytes) blocked = "组件大小与 LFS 元数据不一致";
        } else if (entry.has("lfs") && !entry.isNull("lfs")) {
            blocked = "LFS 元数据格式无效，不能校验指针文件代替实际内容";
        } else {
            git = entry.optString("oid", entry.optString("blobId"));
            if (!git.matches("[a-f0-9]{40}")) { git = ""; blocked = "普通 Git 文件缺少可固定的 blob 校验值"; }
        }
        JSONObject result = new JSONObject().put("path", path).put("repository", id).put("revision", revision).put("format", format).put("bytes", bytes)
                .put("url", ORIGIN + "/" + id + "/resolve/" + revision + "/" + encoded).put("blocked", blocked);
        result.put("uncensored", repository.getJSONObject("uncensored"));
        if (!sha.isEmpty()) result.put("sha256", sha); if (!git.isEmpty()) result.put("gitBlobSha1", git);
        return result;
    }
    public static JSONObject selected(JSONObject repository, JSONObject file) throws Exception {
        if (!file.optString("blocked").isEmpty()) throw new IllegalArgumentException(file.getString("blocked"));
        String repo = repositoryId(repository.getString("id")), revision = repository.getString("revision"), path = file.getString("path");
        String identity = repo + "\n" + revision + "\n" + path;
        String id = "hf_" + Protocol.hex(MessageDigest.getInstance("SHA-256").digest(identity.getBytes(StandardCharsets.UTF_8))).substring(0, 40);
        return new JSONObject().put("id", id).put("name", repo.substring(repo.indexOf('/') + 1) + " · " + file.getString("quant"))
                .put("repository", repo).put("revision", revision).put("filename", path).put("url", file.getString("url"))
                .put("bytes", file.getLong("bytes")).put("sha256", file.optString("sha256")).put("quant", file.getString("quant"))
                .put("sourceUrl", ORIGIN + "/" + repo).put("family", "Hugging Face").put("tier", "hub").put("recommended", false)
                .put("hub", true).put("deviceTested", false).put("uncensored", repository.getJSONObject("uncensored"))
                .put("tags", new JSONArray().put("HF")).put("description", "HF 仓库的固定版本 GGUF；架构与运行内存需加载时检查");
    }
}
