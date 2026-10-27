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
    private JSONObject profiles, metadata, bindings;
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
            profiles = state.optJSONObject("profiles"); metadata = state.optJSONObject("metadata"); bindings = state.optJSONObject("bindings");
        } catch (Exception ignored) {}
        if (custom == null) custom = new JSONArray();
        if (downloads == null) downloads = new JSONObject();
        if (profiles == null) profiles = new JSONObject();
        if (metadata == null) metadata = new JSONObject();
        if (bindings == null) bindings = new JSONObject();
        try {
            // Freeze legacy global preferences into every existing model exactly once.
            JSONObject legacy = ModelSettings.defaults();
            legacy.put("threads", app.prefs.getInt("threads", legacy.getInt("threads"))).put("context", app.prefs.getInt("context", 2048)).put("maxTokens", app.prefs.getInt("maxTokens", 512))
                    .put("temperature", (double) app.prefs.getFloat("temperature", 0.7f)).put("reasoning", app.prefs.getString("reasoning", "off")).put("systemPrompt", app.prefs.getString("systemPrompt", ModelSettings.SYSTEM));
            for (int pass = 0; pass < 2; pass++) {
                JSONArray source = pass == 0 ? catalogue : custom;
                for (int i = 0; i < source.length(); i++) { String id = source.getJSONObject(i).getString("id"); if (!profiles.has(id)) profiles.put(id, ModelSettings.normalize(legacy, new JSONObject(), new JSONObject())); }
            }
            save();
            for (String key : ModelSettings.KEYS) app.prefs.edit().remove(key).apply();
        } catch (Exception error) { app.log("模型配置迁移失败：" + error.getMessage()); }
        // An interrupted transfer is explicitly resumable, never silently considered complete.
        for (java.util.Iterator<String> keys = downloads.keys(); keys.hasNext();) {
            JSONObject d = downloads.optJSONObject(keys.next());
            if (d != null && (d.optString("state").equals("queued") || d.optString("state").equals("downloading") || d.optString("state").equals("verifying"))) {
                try { d.put("state", "paused").put("interrupted", true).put("error", "上次下载已中断，可以继续"); } catch (Exception ignored) {}
            }
            if (d != null && d.optString("state").equals("pausing")) { try { d.put("state", "paused").put("interrupted", false); } catch (Exception ignored) {} }
        }
    }
    private File legacyFile(String id) { return new File(directory, Protocol.safeId(id) + ".gguf"); }
    public synchronized String bundleId(String id) { return bindings.optString(Protocol.safeId(id)); }
    public synchronized String legacyId(String bundleId) {
        for (java.util.Iterator<String> it = bindings.keys(); it.hasNext();) { String id = it.next(); if (bindings.optString(id).equals(bundleId)) return id; }
        return "";
    }
    public synchronized File modelFile(String id) {
        String bundleId = bundleId(id);
        if (!bundleId.isEmpty() && app.bundles != null) try { return app.bundles.object(app.bundles.bundle(bundleId).component("text_gguf").objectId); }
        catch (Exception error) { throw new IllegalStateException("统一模型资产暂不可用；文件已保留", error); }
        return legacyFile(id);
    }
    public synchronized boolean installed(String id) throws Exception {
        String bundleId = bundleId(id);
        if (!bundleId.isEmpty()) return app.bundles != null && app.bundles.plan(bundleId).getBoolean("installed");
        File file = legacyFile(id); return file.isFile() && file.length() >= 24;
    }
    public synchronized com.lma.app.core.BundleStore.Lease acquireBundle(String id) throws Exception {
        String bundleId = bundleId(id); return bundleId.isEmpty() ? null : app.bundles.acquire(bundleId);
    }
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
                m.put("taskTags", new JSONArray().put("text"));
                m.put("baseSupportTags", new JSONArray().put("engine:llama_text").put("pipeline:llama_text").put("format:gguf").put("backend:cpu"));
                String id = m.getString("id");
                File file = modelFile(id);
                boolean installed = installed(id); String bound = bundleId(id);
                m.put("installed", installed).put("bundleId", bound);
                m.put("installedBytes", installed ? file.length() : 0);
                JSONObject transfer = download(id);
                if (!bound.isEmpty() && app.bundles != null) {
                    JSONObject record = app.bundles.record(bound), current = record.optJSONObject("transfer");
                    if (current != null) { transfer = new JSONObject(current.toString()); String status = transfer.optString("state"); transfer.put("state", status.equals("installed") ? "done" : status.equals("failed") ? "error" : status.equals("installing") ? "verifying" : status).put("total", app.bundles.plan(bound).getLong("totalBytes")); }
                }
                if (!bound.isEmpty() && installed) {
                    String digest = app.bundles.bundle(bound).component("text_gguf").sha256;
                    transfer.put("sha256", digest).put("verification", digest.equals(m.optString("sha256")) ? "publisher-sha256" : "format-and-transfer");
                }
                m.put("download", transfer);
                m.put("partialBytes", partFile(id).isFile() ? partFile(id).length() : 0);
                m.put("config", config(id));
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
    public synchronized String addHub(JSONObject candidate) throws Exception {
        JSONObject repository = new JSONObject().put("id", candidate.getString("repository")).put("revision", candidate.getString("revision"))
                .put("uncensored", candidate.getJSONObject("uncensored"));
        JSONObject entry = new JSONObject().put("path", candidate.getString("filename")).put("size", candidate.getLong("bytes"))
                .put("lfs", new JSONObject().put("oid", candidate.optString("sha256")));
        JSONObject checked = HubClient.selected(repository, HubClient.file(repository, entry));
        if (!checked.getString("id").equals(candidate.getString("id")) || !checked.getString("url").equals(candidate.getString("url"))) throw new IllegalArgumentException("HF 文件信息不一致，请重新选择");
        String id = checked.getString("id");
        for (int i = 0; i < custom.length(); i++) if (custom.getJSONObject(i).getString("id").equals(id)) return id;
        custom.put(checked); save(); return id;
    }
    public synchronized JSONObject config(String id) throws Exception {
        model(id);
        JSONObject info = metadata.optJSONObject(id); if (info == null) info = new JSONObject();
        JSONObject saved = profiles.optJSONObject(id); if (saved == null) saved = ModelSettings.defaults();
        String bound = bundleId(id);
        if (!bound.isEmpty() && app.bundles != null) saved = app.bundles.settings(bound).getJSONObject("values");
        JSONObject values = ModelSettings.normalize(saved, new JSONObject(), info);
        JSONObject limits = ModelSettings.limits(info, values.getInt("context"));
        if (!bound.isEmpty() && app.bundles != null) {
            JSONObject fields = app.bundles.parameters(bound).json().getJSONObject("fields"); int declared = limits.getInt("contextMax");
            limits.put("contextMetadataMax", info.optInt("contextLength")).put("contextMax", Math.min(declared, fields.getJSONObject("context").getInt("maximum")))
                .put("contextLimitSource", limits.getInt("contextMax") < declared ? "application_or_recipe" : limits.getBoolean("contextKnown") ? "gguf_metadata" : "application_guard")
                .put("outputGuardMax", fields.getJSONObject("maxTokens").getInt("maximum")).put("threadsMax", Math.min(limits.getInt("threadsMax"), fields.getJSONObject("threads").getInt("maximum")))
                .put("temperatureMax", Math.min(limits.getDouble("temperatureMax"), fields.getJSONObject("temperature").getDouble("maximum")));
        }
        return new JSONObject().put("values", values).put("limits", limits).put("metadata", new JSONObject(info.toString()));
    }
    public synchronized JSONObject previewConfig(String id, JSONObject changes) throws Exception {
        JSONObject config = config(id); String bound = bundleId(id);
        if (!bound.isEmpty() && app.bundles != null) return app.bundles.parameters(bound).normalize(config.getJSONObject("values"), changes).getJSONObject("values");
        return ModelSettings.normalize(config.getJSONObject("values"), changes, config.getJSONObject("metadata"));
    }
    public synchronized JSONObject saveConfig(String id, JSONObject changes) throws Exception { return saveConfig(id, changes, null); }
    public synchronized JSONObject saveConfig(String id, JSONObject changes, com.lma.app.core.BundleStore.Lease owner) throws Exception {
        JSONObject values = previewConfig(id, changes); String bound = bundleId(id);
        if (!bound.isEmpty() && app.bundles != null) {
            if (owner != null && !owner.bundle.id.equals(bound)) throw new IllegalArgumentException("模型配置租约与所选模型不一致");
            values = (owner == null ? app.bundles.saveSettings(bound, values) : owner.saveDefaults(values)).getJSONObject("values");
        }
        profiles.put(id, values); save(); return config(id);
    }
    public synchronized JSONObject inspectModel(String id) throws Exception {
        model(id); File file = modelFile(id);
        if (!installed(id)) throw new IllegalStateException("请先下载或导入模型，再编辑其参数");
        JSONObject cached = metadata.optJSONObject(id);
        if (cached == null || cached.optLong("fileBytes") != file.length() || cached.optLong("modified") != file.lastModified()) {
            JSONObject info;
            try { info = GgufMetadata.read(file); }
            catch (Exception error) { info = new JSONObject().put("source", "unknown").put("contextLength", 0).put("error", "无法读取模型约束：" + error.getMessage()); }
            info.put("fileBytes", file.length()).put("modified", file.lastModified()); metadata.put(id, info);
            profiles.put(id, ModelSettings.normalize(config(id).getJSONObject("values"), new JSONObject(), info)); save();
        }
        return config(id);
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
        String bound = bundleId(id);
        if (!bound.isEmpty() && app.bundles != null) app.bundles.remove(bound, false, app.jobs);
        File file = legacyFile(id), partial = partFile(id), rejected = new File(directory, Protocol.safeId(id) + ".rejected");
        if (file.exists() && !file.delete()) throw new java.io.IOException("无法删除模型文件");
        if (partial.exists() && !partial.delete()) throw new java.io.IOException("无法删除未完成的下载");
        if (rejected.exists() && !rejected.delete()) throw new java.io.IOException("无法删除未通过校验的文件");
        downloads.remove(id);
        metadata.remove(id);
        if (id.startsWith("custom_") || id.startsWith("hf_")) { profiles.remove(id); bindings.remove(id); }
        if (id.startsWith("custom_") || id.startsWith("hf_")) for (int i = 0; i < custom.length(); i++) if (custom.getJSONObject(i).getString("id").equals(id)) { custom.remove(i); break; }
        if (app.prefs.getString("selectedModel", "").equals(id)) app.prefs.edit().remove("selectedModel").putBoolean("desiredRunning", false).apply();
        if (app.engineModel.equals(id)) app.engineModel = "";
        save(); app.emit();
    }
    private boolean legacyBusy(String id) {
        return app.engineModel.equals(id) && (!app.engineState.equals("stopped") && !app.engineState.equals("error") || app.nativeProcess != null && app.nativeProcess.isAlive());
    }
    public JSONArray migrateExisting(com.lma.app.core.RecipeCatalogue recipes, com.lma.app.core.DataFiles.Check check) throws Exception {
        JSONArray candidates = new JSONArray(), outcomes = new JSONArray();
        synchronized (this) {
            for (int pass = 0; pass < 2; pass++) { JSONArray source = pass == 0 ? catalogue : custom;
                for (int i = 0; i < source.length(); i++) { String id = source.getJSONObject(i).getString("id"); if (bundleId(id).isEmpty() && legacyFile(id).isFile() && !legacyBusy(id)) candidates.put(id); }
            }
        }
        JSONObject template = recipes.template("text_gguf_cpu_v1");
        for (int i = 0; i < candidates.length(); i++) {
            check.run(); String id = candidates.getString(i); java.util.concurrent.locks.ReentrantLock lock = transferLock(id); lock.lockInterruptibly();
            try {
                synchronized (this) { if (!bundleId(id).isEmpty() || legacyBusy(id)) continue; }
                File source = legacyFile(id); if (!source.isFile()) continue;
                JSONObject original = model(id); long bytes = source.length(), modified = source.lastModified();
                JSONObject info = GgufMetadata.read(source); check.run();
                String digest = original.optString("sha256");
                if (digest.isEmpty()) digest = com.lma.app.core.DataFiles.sha256(source, check);
                String identity = Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest((id + ":" + digest).getBytes(java.nio.charset.StandardCharsets.UTF_8)));
                String targetId = "legacy_" + identity;
                JSONObject component = new JSONObject().put("role", "text_gguf").put("path", id + ".gguf").put("format", "gguf").put("bytes", bytes).put("sha256", digest);
                String url = original.optString("url");
                if (!url.isEmpty()) {
                    java.net.URL parsed = new java.net.URL(url);
                    if (parsed.getHost().equalsIgnoreCase("huggingface.co") || parsed.getHost().equalsIgnoreCase("hf-mirror.com")) {
                        String[] parts = parsed.getPath().split("/", 6);
                        if (parts.length == 6 && parts[3].equals("resolve") && parts[4].matches("[a-fA-F0-9]{40,64}")) component.put("path", java.net.URLDecoder.decode(parts[5].replace("+", "%2B"), "UTF-8")).put("repository", parts[1] + "/" + parts[2]).put("revision", parts[4]).put("url", url);
                    } else component.put("url", url);
                }
                JSONObject manifest = new JSONObject(template.getJSONObject("definition").toString()).put("schema", com.lma.app.core.ModelBundle.SCHEMA)
                    .put("id", targetId).put("modelId", id).put("recipeId", template.getString("id")).put("name", original.getString("name"))
                    .put("components", new JSONArray().put(component)).put("migration", new JSONObject().put("source", "legacy_text_store").put("legacyId", id))
                    .put("description", original.optString("description")).put("license", original.opt("license") == null ? "unknown" : original.get("license"));
                if (original.has("uncensored")) manifest.put("uncensored", new JSONObject(original.getJSONObject("uncensored").toString()));
                JSONObject values = config(id).getJSONObject("values");
                app.bundles.adoptLocal(new com.lma.app.core.ModelBundle(manifest), java.util.Collections.singletonMap("text_gguf", source), values, check);
                synchronized (app.requestGate) { synchronized (this) {
                    check.run(); if (legacyBusy(id)) throw new java.io.IOException("模型正在运行，停止后再迁移；原文件已保留");
                    if (!source.isFile() || source.length() != bytes || source.lastModified() != modified) throw new java.io.IOException("旧模型在迁移期间发生变化，原记录已保留");
                    // User edits made while hashing remain authoritative until this binding is committed.
                    JSONObject latest = ModelSettings.normalize(config(id).getJSONObject("values"), new JSONObject(), info); latest = app.bundles.saveSettings(targetId, latest).getJSONObject("values");
                    JSONObject before = bindings, oldMetadata = metadata, oldProfiles = profiles;
                    bindings = new JSONObject(bindings.toString()); bindings.put(id, targetId);
                    metadata = new JSONObject(metadata.toString()); metadata.put(id, info.put("fileBytes", bytes).put("modified", modelFile(id).lastModified()));
                    profiles = new JSONObject(profiles.toString()); profiles.put(id, latest);
                    try { save(); } catch (Exception error) { bindings = before; metadata = oldMetadata; profiles = oldProfiles; throw error; }
                    // Content is retained in verified CAS storage. A reader of the old name may still be active.
                    source.delete();
                } }
                outcomes.put(new JSONObject().put("id", id).put("bundleId", targetId).put("state", "migrated")); app.emit();
            } catch (java.io.InterruptedIOException cancelled) { throw cancelled; }
              catch (Exception error) { check.run(); outcomes.put(new JSONObject().put("id", id).put("state", "failed").put("error", error.getMessage() == null ? "本地迁移失败，原文件保留" : error.getMessage())); }
            finally { lock.unlock(); }
        }
        return outcomes;
    }
    private void save() throws Exception {
        JSONObject state = new JSONObject(); state.put("custom", custom); state.put("downloads", downloads); state.put("profiles", profiles); state.put("metadata", metadata); state.put("bindings", bindings);
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
