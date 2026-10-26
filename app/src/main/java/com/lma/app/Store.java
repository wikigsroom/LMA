package com.lma.app;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import com.lma.app.core.Protocol;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.UUID;

/** Catalogue and durable download state. Model filenames are never supplied by a URL. */
public final class Store {
    private final LmaApp app;
    private final File directory;
    private final JSONArray catalogue;
    private JSONArray custom;
    private JSONObject downloads;
    private final AtomicFile stateFile;
    private final java.util.concurrent.ConcurrentHashMap<String, java.util.concurrent.locks.ReentrantLock> transferLocks = new java.util.concurrent.ConcurrentHashMap<>();

    public Store(LmaApp app) {
        this.app = app;
        directory = new File(app.getFilesDir(), "models"); directory.mkdirs();
        stateFile = new AtomicFile(new File(app.getFilesDir(), "models-state.json"));
        JSONArray initial;
        try (InputStream in = app.getAssets().open("models.json")) { initial = new JSONObject(read(in, 2 * 1024 * 1024)).getJSONArray("models"); }
        catch (Exception error) { initial = new JSONArray(); app.log("模型目录读取失败：" + error.getMessage()); }
        catalogue = initial;
        try (FileInputStream in = stateFile.openRead()) {
            JSONObject state = new JSONObject(read(in, 4 * 1024 * 1024));
            custom = state.optJSONArray("custom"); downloads = state.optJSONObject("downloads");
        } catch (Exception ignored) {}
        if (custom == null) custom = new JSONArray();
        if (downloads == null) downloads = new JSONObject();
        // An interrupted transfer is explicitly resumable, never silently considered complete.
        for (java.util.Iterator<String> keys = downloads.keys(); keys.hasNext();) {
            JSONObject d = downloads.optJSONObject(keys.next());
            if (d != null && (d.optString("state").equals("downloading") || d.optString("state").equals("verifying"))) {
                try { d.put("state", "paused").put("interrupted", true).put("error", "上次下载已中断，可以继续"); } catch (Exception ignored) {}
            }
            if (d != null && d.optString("state").equals("pausing")) { try { d.put("state", "paused").put("interrupted", false); } catch (Exception ignored) {} }
        }
    }
    public File modelFile(String id) { return new File(directory, Protocol.safeId(id) + ".gguf"); }
    public File partFile(String id) { return new File(directory, Protocol.safeId(id) + ".part"); }
    public java.util.concurrent.locks.ReentrantLock transferLock(String id) { return transferLocks.computeIfAbsent(Protocol.safeId(id), key -> new java.util.concurrent.locks.ReentrantLock()); }
    public synchronized JSONObject model(String id) throws Exception {
        Protocol.safeId(id);
        for (int i = 0; i < catalogue.length(); i++) if (catalogue.getJSONObject(i).getString("id").equals(id)) return new JSONObject(catalogue.getJSONObject(i).toString());
        for (int i = 0; i < custom.length(); i++) if (custom.getJSONObject(i).getString("id").equals(id)) return new JSONObject(custom.getJSONObject(i).toString());
        throw new IllegalArgumentException("找不到这个模型");
    }
    public synchronized JSONObject download(String id) {
        JSONObject d = downloads.optJSONObject(Protocol.safeId(id));
        try { return d == null ? new JSONObject() : new JSONObject(d.toString()); } catch (Exception error) { return new JSONObject(); }
    }
    public synchronized void updateDownload(String id, JSONObject record, boolean persist) {
        try { model(id); downloads.put(Protocol.safeId(id), new JSONObject(record.toString())); if (persist) save(); }
        catch (Exception error) { app.log("下载记录写入失败：" + error.getMessage()); }
    }
    public synchronized JSONArray snapshot() throws Exception {
        JSONArray result = new JSONArray();
        for (int pass = 0; pass < 2; pass++) {
            JSONArray source = pass == 0 ? catalogue : custom;
            for (int i = 0; i < source.length(); i++) {
                JSONObject m = new JSONObject(source.getJSONObject(i).toString());
                String id = m.getString("id");
                File file = modelFile(id);
                m.put("installed", file.isFile() && file.length() >= 24);
                m.put("installedBytes", file.isFile() ? file.length() : 0);
                m.put("download", download(id));
                m.put("partialBytes", partFile(id).isFile() ? partFile(id).length() : 0);
                result.put(m);
            }
        }
        return result;
    }
    public synchronized String addCustom(String name, String url, String hash, boolean imported) throws Exception {
        name = name.trim(); if (name.isEmpty() || name.length() > 160) throw new IllegalArgumentException("模型名称需要 1–160 个字符");
        if (!imported) {
            java.net.URL parsed = new java.net.URL(url);
            if (!parsed.getProtocol().equals("https") || parsed.getHost().isEmpty() || parsed.getUserInfo() != null)
                throw new IllegalArgumentException("请使用 HTTPS 的 GGUF 下载链接");
        }
        if (!hash.isEmpty() && !Protocol.isSha256(hash)) throw new IllegalArgumentException("SHA256 应为 64 位十六进制字符串");
        String id = "custom_" + UUID.randomUUID().toString().replace("-", "");
        JSONObject m = new JSONObject(); m.put("id", id); m.put("name", name); m.put("family", "自定义");
        m.put("url", url); m.put("sha256", hash.toLowerCase(java.util.Locale.ROOT)); m.put("bytes", 0);
        m.put("quant", "GGUF"); m.put("tier", "custom"); m.put("description", imported ? "从设备导入的 GGUF 模型" : "自定义 GGUF，兼容性取决于模型架构");
        m.put("tags", new JSONArray().put("自定义")); m.put("imported", imported); m.put("recommended", false);
        custom.put(m); save(); return id;
    }
    public synchronized void remove(String id) throws Exception {
        java.util.concurrent.locks.ReentrantLock lock = transferLock(id);
        if (!lock.tryLock()) throw new IllegalStateException("下载或导入正在结束，请稍后再删除");
        try { removeLocked(id); } finally { lock.unlock(); }
    }
    private void removeLocked(String id) throws Exception {
        JSONObject model = model(id);
        if (app.engineModel.equals(id) && !app.engineState.equals("stopped") && !app.engineState.equals("error"))
            throw new IllegalStateException("请先停止当前模型，再删除文件");
        File file = modelFile(id), partial = partFile(id), rejected = new File(directory, Protocol.safeId(id) + ".rejected");
        if (file.exists() && !file.delete()) throw new java.io.IOException("无法删除模型文件");
        if (partial.exists() && !partial.delete()) throw new java.io.IOException("无法删除未完成的下载");
        if (rejected.exists() && !rejected.delete()) throw new java.io.IOException("无法删除未通过校验的文件");
        downloads.remove(id);
        if (id.startsWith("custom_")) for (int i = 0; i < custom.length(); i++) if (custom.getJSONObject(i).getString("id").equals(id)) { custom.remove(i); break; }
        if (app.prefs.getString("selectedModel", "").equals(id)) app.prefs.edit().remove("selectedModel").putBoolean("desiredRunning", false).apply();
        save(); app.emit();
    }
    private void save() throws Exception {
        JSONObject state = new JSONObject(); state.put("custom", custom); state.put("downloads", downloads);
        FileOutputStream stream = null;
        try { stream = stateFile.startWrite(); stream.write(state.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8)); stateFile.finishWrite(stream); }
        catch (Exception error) { if (stream != null) stateFile.failWrite(stream); throw error; }
    }
    public static String read(InputStream source, int maxBytes) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] buffer = new byte[8192]; int count;
        while ((count = source.read(buffer)) != -1) { if (bytes.size() + count > maxBytes) throw new java.io.IOException("数据过大"); bytes.write(buffer, 0, count); }
        return new String(bytes.toByteArray(), java.nio.charset.StandardCharsets.UTF_8);
    }
}
