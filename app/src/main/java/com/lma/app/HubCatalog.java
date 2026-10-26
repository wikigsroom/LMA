package com.lma.app;

import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONArray;
import org.json.JSONObject;

/** Application-owned metadata requests; browsing never starts the inference foreground service. */
public final class HubCatalog implements AutoCloseable {
    public interface ClientFactory { HubClient create(); }
    private final LmaApp app;
    private final ClientFactory factory;
    private final ExecutorService searchWorker = Executors.newSingleThreadExecutor();
    private final ExecutorService fileWorker = Executors.newSingleThreadExecutor();
    private long searchGeneration, fileGeneration;
    private String query = "", format = "gguf", sort = "downloads", cursor = "", fileCursor = "";
    private final ArrayList<String> history = new ArrayList<>(), fileHistory = new ArrayList<>();
    private JSONObject search = emptySearch(), files = emptyFiles();
    public HubCatalog(LmaApp app) { this(app, () -> new HubClient(app.prefs.getString("source", "auto"), app.prefs.getString("hfToken", ""))); }
    public HubCatalog(LmaApp app, ClientFactory factory) { this.app = app; this.factory = factory; }
    private static JSONObject emptySearch() {
        JSONObject value = new JSONObject();
        try { value.put("items", new JSONArray()).put("next", "").put("previous", false).put("page", 1).put("searching", false).put("error", "").put("initialized", false).put("query", "").put("format", "gguf").put("sort", "downloads"); } catch (Exception ignored) {}
        return value;
    }
    private static JSONObject emptyFiles() {
        JSONObject value = new JSONObject();
        try { value.put("items", new JSONArray()).put("next", "").put("previous", false).put("page", 1).put("loading", false).put("error", ""); } catch (Exception ignored) {}
        return value;
    }
    public synchronized JSONObject snapshot() throws Exception {
        JSONObject copy = new JSONObject(search.toString()); copy.put("files", new JSONObject(files.toString())); return copy;
    }
    private HubClient client() { return factory.create(); }
    @Override public void close() { searchWorker.shutdownNow(); fileWorker.shutdownNow(); }
    public void dispatch(JSONObject command) throws Exception {
        switch (command.getString("action")) {
            case "hubSearch": search(command, "new"); return;
            case "hubPage": search(command, command.optString("direction")); return;
            case "hubFiles": files(command, "new"); return;
            case "hubFilePage": files(command, command.optString("direction")); return;
            case "hubToken": {
                String token = command.optString("token").trim();
                if (!token.isEmpty() && (!token.startsWith("hf_") || !token.matches("[A-Za-z0-9_]{6,512}"))) throw new IllegalArgumentException("请填写有效的 hf_ 访问令牌，或留空清除");
                app.prefs.edit().putString("hfToken", token).apply(); app.finishCommand(command, null); return;
            }
            default: throw new IllegalArgumentException("未知 HF 操作");
        }
    }
    private synchronized void search(JSONObject command, String direction) throws Exception {
        if (direction.equals("new")) {
            query = HubClient.query(command.optString("query"));
            format = command.optString("format", "gguf"); sort = command.optString("sort", "downloads");
            if (!format.equals("all") && !format.equals("gguf")) throw new IllegalArgumentException("未知格式筛选");
            if (!sort.equals("downloads") && !sort.equals("likes") && !sort.equals("lastModified")) throw new IllegalArgumentException("未知排序方式");
            history.clear(); cursor = "";
        } else {
            if (search.optBoolean("searching")) throw new IllegalStateException("正在获取列表，请稍候");
            if (direction.equals("next") && !search.optString("next").isEmpty()) { history.add(cursor); cursor = search.getString("next"); }
            else if (direction.equals("previous") && !history.isEmpty()) cursor = history.remove(history.size() - 1);
            else if (!direction.equals("retry")) throw new IllegalArgumentException("没有可用的分页");
        }
        final long generation = ++searchGeneration;
        final String q = query, f = format, s = sort, page = cursor;
        search.put("query", q).put("format", f).put("sort", s).put("items", new JSONArray()).put("next", "").put("previous", !history.isEmpty()).put("page", history.size() + 1).put("searching", true).put("initialized", true).put("error", "");
        app.emit();
        searchWorker.execute(() -> {
            try {
                synchronized (this) { if (generation != searchGeneration) { app.finishCommand(command, null); return; } }
                JSONObject result = client().search(q, f, s, page);
                synchronized (this) { if (generation == searchGeneration) search.put("items", result.getJSONArray("items")).put("next", result.getString("next")).put("origin", result.optString("origin")).put("searching", false); }
                app.finishCommand(command, null);
            } catch (Exception error) { completeError(command, generation, true, error); }
        });
    }
    private synchronized void files(JSONObject command, String direction) throws Exception {
        final String id;
        if (direction.equals("new")) {
            id = HubClient.repositoryId(command.getString("repository"));
            fileCursor = ""; fileHistory.clear(); files = emptyFiles();
            files.put("repository", new JSONObject().put("id", id));
        } else {
            if (files.optBoolean("loading")) throw new IllegalStateException("正在获取文件，请稍候");
            id = files.getJSONObject("repository").getString("id");
            if (direction.equals("next") && !files.optString("next").isEmpty()) { fileHistory.add(fileCursor); fileCursor = files.getString("next"); }
            else if (direction.equals("previous") && !fileHistory.isEmpty()) fileCursor = fileHistory.remove(fileHistory.size() - 1);
            else if (!direction.equals("retry")) throw new IllegalArgumentException("没有可用的文件分页");
        }
        final long generation = ++fileGeneration;
        final String page = fileCursor;
        final JSONObject existing = new JSONObject(files.getJSONObject("repository").toString());
        files.put("items", new JSONArray()).put("next", "").put("page", fileHistory.size() + 1).put("previous", !fileHistory.isEmpty()).put("loading", true).put("error", "");
        app.emit();
        fileWorker.execute(() -> {
            try {
                synchronized (this) { if (generation != fileGeneration) { app.finishCommand(command, null); return; } }
                HubClient client = client();
                JSONObject repository = existing.optString("revision").isEmpty() ? client.repository(id) : existing;
                JSONObject result = client.files(repository, page);
                synchronized (this) { if (generation == fileGeneration) files.put("repository", repository).put("items", result.getJSONArray("items")).put("next", result.getString("next")).put("origin", result.optString("origin")).put("loading", false); }
                app.finishCommand(command, null);
            } catch (Exception error) { completeError(command, generation, false, error); }
        });
    }
    private void completeError(JSONObject command, long generation, boolean isSearch, Exception error) {
        synchronized (this) {
            try {
                if (generation == (isSearch ? searchGeneration : fileGeneration)) (isSearch ? search : files).put(isSearch ? "searching" : "loading", false).put("error", error.getMessage() == null ? "HF 请求失败" : error.getMessage());
            } catch (Exception ignored) {}
        }
        // Errors live in their own search/file panel; they do not interrupt a running conversation.
        app.finishCommand(command, error, false);
    }
    public synchronized JSONObject selected(JSONObject command) throws Exception {
        JSONObject repository = files.optJSONObject("repository");
        if (files.optBoolean("loading") || repository == null || !repository.optString("id").equals(command.optString("repository")) || !repository.optString("revision").equals(command.optString("revision"))) throw new IllegalStateException("仓库已变化，请重新选择文件");
        JSONArray entries = files.getJSONArray("items");
        for (int i = 0; i < entries.length(); i++) {
            JSONObject entry = entries.getJSONObject(i);
            if (entry.getString("path").equals(command.optString("path"))) return HubClient.selected(repository, entry);
        }
        throw new IllegalArgumentException("文件不在当前仓库页面，请刷新后重试");
    }
}
