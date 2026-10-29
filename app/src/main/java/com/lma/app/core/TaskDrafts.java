package com.lma.app.core;

import android.util.AtomicFile;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileNotFoundException;

/** Explicit per-model drafts, independent of installed weights, jobs and model settings. */
public final class TaskDrafts {
    private static final int LIMIT = 8 * 1024 * 1024;
    private final AtomicFile file;
    private JSONObject state;
    public TaskDrafts(File directory) throws Exception {
        if (!directory.isDirectory() && !directory.mkdirs()) throw new java.io.IOException("Cannot create draft storage");
        file = new AtomicFile(new File(directory, "drafts.json"));
        try { state = DataFiles.read(file, LIMIT); }
        catch (FileNotFoundException absent) { state = new JSONObject().put("schema", "lma.task-drafts/1").put("nextRevision", 1L).put("drafts", new JSONObject()); }
        if (!"lma.task-drafts/1".equals(state.getString("schema")) || state.getLong("nextRevision") < 1) throw new java.io.IOException("Invalid draft storage; original data retained");
        JSONObject entries = state.getJSONObject("drafts");
        if (entries.length() > 128) throw new java.io.IOException("Draft storage exceeds its limit");
        for (java.util.Iterator<String> keys = entries.keys(); keys.hasNext();) {
            String id = keys.next();
            JSONObject draft = entries.getJSONObject(id), request = TaskRequests.draft(draft.getJSONObject("request"));
            if (!id.equals(request.getString("bundleId")) || draft.getLong("revision") < 1 || draft.getLong("revision") >= state.getLong("nextRevision")) throw new java.io.IOException("Invalid draft identity or revision");
        }
    }
    public synchronized JSONObject get(String id) throws Exception {
        ModelBundle.key(id); JSONObject draft = state.getJSONObject("drafts").optJSONObject(id);
        if (draft == null) throw new IllegalArgumentException("Unknown task draft");
        return DataFiles.copy(draft);
    }
    public synchronized JSONArray summaries() throws Exception {
        JSONArray result = new JSONArray(); JSONObject entries = state.getJSONObject("drafts");
        for (java.util.Iterator<String> keys = entries.keys(); keys.hasNext();) {
            String id = keys.next();
            JSONObject draft = entries.getJSONObject(id), request = draft.getJSONObject("request");
            String prompt = request.getJSONObject("input").getString("prompt");
            result.put(new JSONObject().put("bundleId", id).put("type", request.getString("type")).put("savedAt", draft.getLong("savedAt")).put("revision", draft.getLong("revision")).put("inputSummary", prompt.length() > 200 ? prompt.substring(0, 200) + "…" : prompt));
        }
        return result;
    }
    public synchronized JSONObject save(JSONObject input, long expectedRevision) throws Exception {
        JSONObject request = TaskRequests.draft(input); String id = request.getString("bundleId");
        checkRevision(id, expectedRevision);
        if (!state.getJSONObject("drafts").has(id) && state.getJSONObject("drafts").length() >= 128) throw new IllegalStateException("Draft history is full; remove an old draft first");
        JSONObject next = DataFiles.copy(state); long revision = next.getLong("nextRevision");
        if (revision >= 9007199254740991L) throw new IllegalStateException("Draft revision limit reached");
        JSONObject draft = new JSONObject().put("bundleId", id).put("revision", revision).put("savedAt", System.currentTimeMillis()).put("request", request);
        next.getJSONObject("drafts").put(id, draft); next.put("nextRevision", revision + 1);
        DataFiles.write(file, next, LIMIT); state = next; return DataFiles.copy(draft);
    }
    public synchronized void remove(String id, long expectedRevision) throws Exception {
        ModelBundle.key(id); checkRevision(id, expectedRevision);
        JSONObject next = DataFiles.copy(state); next.getJSONObject("drafts").remove(id);
        DataFiles.write(file, next, LIMIT); state = next;
    }
    private void checkRevision(String id, long expected) throws Exception {
        JSONObject previous = state.getJSONObject("drafts").optJSONObject(id);
        if (expected < 0 || expected != (previous == null ? 0 : previous.getLong("revision"))) throw new IllegalStateException("Draft changed in another editor; reopen it before saving or deleting");
    }
    public static long revision(JSONObject input) throws Exception {
        Object value = input.get("expectedRevision");
        if (!(value instanceof Number)) throw new IllegalArgumentException("expectedRevision must be an integer");
        double number = ((Number) value).doubleValue();
        if (!Double.isFinite(number) || number < 0 || number > 9007199254740991L || number != Math.rint(number)) throw new IllegalArgumentException("Invalid expectedRevision");
        return ((Number) value).longValue();
    }
}
