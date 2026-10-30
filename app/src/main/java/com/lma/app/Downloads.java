package com.lma.app;

import android.net.Uri;
import android.os.StatFs;
import com.lma.app.core.Protocol;
import com.lma.app.core.InputHandle;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.security.MessageDigest;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class Downloads {
    private final LmaService owner;
    private final LmaApp app;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ConcurrentHashMap<String, Job> jobs = new ConcurrentHashMap<>();
    private volatile String activeId = "";
    private volatile boolean closed;
    private static final long RESERVE = 64L * 1024 * 1024;
    private static final long MAX_MODEL = 12L * 1024 * 1024 * 1024;

    private static final class Job {
        String id, uri; volatile boolean cancelled, started; volatile HttpURLConnection connection;
        final InputHandle input = new InputHandle();
        Job(String id, String uri) { this.id = id; this.uri = uri; }
    }
    public Downloads(LmaService owner, LmaApp app) { this.owner = owner; this.app = app; }
    public boolean busy() { return !jobs.isEmpty(); }
    public boolean busy(String id) { return jobs.containsKey(id); }
    public String activeId() { return activeId; }
    public synchronized void enqueue(String id, String uri) throws Exception {
        if (closed) throw new IllegalStateException("下载服务正在停止，请稍后重试");
        app.store.model(id);
        if (app.store.installed(id)) return;
        if (!app.store.bundleId(id).isEmpty()) throw new IllegalStateException("此模型已纳入共用资产库，请通过模型包传输管理");
        if (jobs.containsKey(id)) return;
        Job job = new Job(id, uri == null ? "" : uri); jobs.put(id, job);
        JSONObject record = app.store.download(id); record.put("state", "queued").put("error", "").put("uri", job.uri).put("interrupted", false);
        app.store.updateDownload(id, record, true); app.emit();
        executor.execute(() -> perform(job)); owner.activityChanged();
    }
    /** Retained for callers upgrading from older code; restoration never starts model downloads. */
    public void resumeInterrupted() { /* User must explicitly choose resumeDownload. */ }
    public void pause(String id) {
        Job job;
        synchronized (this) {
            job = jobs.get(id);
            if (job == null) return;
            job.cancelled = true;
            try {
                JSONObject record = app.store.download(id);
                record.put("state", job.started ? "pausing" : "paused").put("speed", 0).put("interrupted", false).put("error", "");
                app.store.updateDownload(id, record, true);
            } catch (Exception error) { app.log("暂停记录失败：" + error.getMessage()); }
            if (!job.started) jobs.remove(id, job);
        }
        job.input.close();
        if (job.connection != null) job.connection.disconnect();
        app.emit(); owner.activityChanged();
    }
    public void pauseAll() { for (String id : jobs.keySet()) pause(id); }
    public void close() { synchronized (this) { closed = true; } pauseAll(); executor.shutdown(); }

    private void perform(Job job) {
        synchronized (this) {
            if (job.cancelled || jobs.get(job.id) != job) return;
            job.started = true; activeId = job.id;
        }
        // A replacement Service can start before the old transfer worker has unwound.
        java.util.concurrent.locks.ReentrantLock lock = app.store.transferLock(job.id);
        lock.lock(); try { performLocked(job); } finally { lock.unlock(); }
    }
    private void performLocked(Job job) {
        activeId = job.id;
        JSONObject state = app.store.download(job.id);
        File partial = app.store.partFile(job.id);
        try {
            check(job);
            JSONObject model = app.store.model(job.id);
            long expected = model.optLong("bytes"), offset = job.uri.isEmpty() ? partial.length() : 0;
            long available = new StatFs(partial.getParent()).getAvailableBytes();
            if (expected > 0 && available < Math.max(0, expected - offset) + RESERVE) throw new IOException("可用空间不足，请释放空间后继续");
            state.put("state", "downloading").put("error", "").put("received", offset).put("total", expected);
            update(job, state, true);
            InputStream input;
            long total;
            if (!job.uri.isEmpty()) {
                input = job.input.open(new DocumentInput(app.getContentResolver(), Uri.parse(job.uri))); total = 0;
            } else {
                String url = model.getString("url");
                String hfToken = app.prefs.getString("hfToken", "");
                String[] sources = Net.modelSources(url, hfToken.isEmpty() ? app.prefs.getString("source", "auto") : "official");
                HttpURLConnection connection = Net.downloadCandidates(sources, offset, state.optString("etag"), opened -> { job.connection = opened; check(job); }, hfToken);
                check(job);
                int status = connection.getResponseCode();
                if (status == 206) {
                    long[] range = Protocol.parseContentRange(connection.getHeaderField("Content-Range"), offset); total = range[2];
                    String priorTag = state.optString("etag"), actualTag = connection.getHeaderField("ETag");
                    if (offset > 0 && !priorTag.isEmpty() && !priorTag.startsWith("W/") && actualTag != null && !priorTag.equals(actualTag))
                        throw new IOException("下载源文件版本已变化，请删除未完成文件后重新下载");
                } else if (status == 200) { offset = 0; total = connection.getContentLengthLong(); }
                else if (status == 416 && offset > 0 && connection.getHeaderField("Content-Range") != null && connection.getHeaderField("Content-Range").equals("bytes */" + offset)) {
                    total = offset; input = new java.io.ByteArrayInputStream(new byte[0]);
                    state.put("total", total); verifyAndInstall(job, model, state, partial); return;
                } else { throw new IOException("下载源返回 HTTP " + status + "，请稍后重试或切换下载源"); }
                if (total > MAX_MODEL) throw new IOException("这个文件超出当前支持的下载大小");
                if (total > 0 && new StatFs(partial.getParent()).getAvailableBytes() < total - offset + RESERVE)
                    throw new IOException("可用空间不足，完整文件需要 " + (total / (1024 * 1024)) + " MB");
                String etag = connection.getHeaderField("ETag"); state.put("etag", etag == null ? "" : etag);
                input = job.input.open(connection::getInputStream);
            }
            state.put("total", Math.max(0, total));
            long lastUpdate = 0, lastPersist = 0, startAt = System.currentTimeMillis(), initial = offset;
            try (InputStream in = input; FileOutputStream out = new FileOutputStream(partial, offset > 0)) {
                byte[] buffer = new byte[256 * 1024]; int count;
                while ((count = in.read(buffer)) != -1) {
                    check(job); out.write(buffer, 0, count); offset += count;
                    if (offset > MAX_MODEL) throw new IOException("文件超出大小限制");
                    long now = System.currentTimeMillis();
                    if (now - lastUpdate > 350) {
                        if (new StatFs(partial.getParent()).getAvailableBytes() < RESERVE) throw new IOException("存储空间不足，下载已保留，可以释放空间后继续");
                        state.put("received", offset).put("speed", (offset - initial) * 1000 / Math.max(1, now - startAt));
                        boolean persist = now - lastPersist > 2500; update(job, state, persist); lastUpdate = now; if (persist) lastPersist = now;
                    }
                }
                out.getFD().sync();
            }
            check(job);
            if (total > 0 && offset != total) throw new IOException("下载连接提前结束，已保留进度，请继续下载");
            state.put("received", offset).put("total", offset);
            verifyAndInstall(job, model, state, partial);
        } catch (Exception error) {
            try { state.put("state", job.cancelled ? "paused" : "error").put("received", partial.length()).put("speed", 0).put("interrupted", false)
                    .put("error", job.cancelled ? "" : friendly(error)); update(job, state, true); }
            catch (Exception ignored) {}
            if (!job.cancelled) app.log("下载未完成：" + friendly(error));
        } finally {
            job.input.close();
            if (job.connection != null) job.connection.disconnect();
            synchronized (this) {
                // pause() can return from disconnect after the worker's catch has already
                // written "paused". Finalize under the same lock so "pausing" cannot win.
                if (job.cancelled) {
                    try {
                        File installed = app.store.modelFile(job.id);
                        state.put("state", installed.isFile() ? "done" : "paused").put("received", installed.isFile() ? installed.length() : partial.length()).put("speed", 0).put("interrupted", false).put("error", "");
                        update(job, state, true);
                    } catch (Exception error) { app.log("暂停状态保存失败：" + error.getMessage()); }
                }
                jobs.remove(job.id, job); activeId = "";
            }
            app.emit(); owner.activityChanged();
        }
    }
    private void verifyAndInstall(Job job, JSONObject model, JSONObject state, File partial) throws Exception {
        check(job); state.put("state", "verifying").put("speed", 0); update(job, state, true);
        if (partial.length() < 24) { reject(job, partial, state); throw new IOException("文件不是完整的 GGUF 模型，请重新下载或导入"); }
        MessageDigest hash = MessageDigest.getInstance("SHA-256");
        try (FileInputStream in = new FileInputStream(partial)) {
            byte[] magic = new byte[4]; if (in.read(magic) != 4 || magic[0] != 'G' || magic[1] != 'G' || magic[2] != 'U' || magic[3] != 'F')
                throw new InvalidModelException("下载内容不是 GGUF；请检查文件链接后重新添加");
            hash.update(magic); byte[] buffer = new byte[1024 * 1024]; int count;
            while ((count = in.read(buffer)) != -1) { check(job); hash.update(buffer, 0, count); }
        } catch (InvalidModelException error) { reject(job, partial, state); throw error; }
        String actual = Protocol.hex(hash.digest()), expected = model.optString("sha256");
        if (!expected.isEmpty() && !actual.equalsIgnoreCase(expected)) {
            reject(job, partial, state);
            throw new IOException("SHA256 与发布者不一致，文件未安装；请重试下载");
        }
        check(job);
        File complete = app.store.modelFile(job.id);
        if (!partial.renameTo(complete)) throw new IOException("无法保存模型文件，请检查存储空间");
        state.put("state", "done").put("received", complete.length()).put("total", complete.length()).put("sha256", actual)
                .put("verification", expected.isEmpty() ? "format-and-transfer" : "publisher-sha256").put("error", "").put("interrupted", false);
        update(job, state, true); app.store.inspectModel(job.id); app.log("模型已准备：" + model.optString("name")); owner.modelInstalled(job.id);
    }
    private static final class InvalidModelException extends IOException { InvalidModelException(String message) { super(message); } }
    private void reject(Job job, File partial, JSONObject state) throws Exception {
        File rejected = new File(partial.getParentFile(), job.id + ".rejected");
        if (rejected.exists() && !rejected.delete()) throw new IOException("无法替换未通过校验的文件，请先删除该模型");
        if (partial.exists() && !partial.renameTo(rejected) && !partial.delete()) throw new IOException("无法移除损坏文件，请先删除该模型");
        state.put("received", 0).put("etag", "");
    }
    private void check(Job job) throws IOException { if (job.cancelled || Thread.currentThread().isInterrupted()) throw new IOException("下载已暂停"); }
    private void update(Job job, JSONObject state, boolean persist) { app.store.updateDownload(job.id, state, persist); app.emit(); owner.updateNotification(); }
    private String friendly(Exception error) {
        if (error instanceof java.net.SocketTimeoutException) return "连接超时，已保留下载进度；请继续或切换下载源";
        if (error instanceof java.net.UnknownHostException) return "无法连接下载源，请检查网络或切换下载源";
        return error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
    }
}
