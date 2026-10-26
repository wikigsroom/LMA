package com.lma.app;

import android.content.ContentValues;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.UUID;
import com.lma.app.core.ChatHistory;

/** Generation belongs to the service; the UI only reads persisted messages. */
public final class Chats extends SQLiteOpenHelper {
    private final LmaApp app;
    public Chats(LmaApp app) {
        super(app, "lma-chats.db", null, 1); this.app = app;
        ContentValues interrupted = new ContentValues(); interrupted.put("status", "interrupted");
        interrupted.put("error", "上次生成已中断，已收到的内容保存在这里");
        getWritableDatabase().update("messages", interrupted, "status=?", new String[]{"generating"});
    }
    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE sessions(id TEXT PRIMARY KEY,title TEXT NOT NULL,model TEXT NOT NULL,updated INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE messages(id TEXT PRIMARY KEY,session TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,reasoning TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL,created INTEGER NOT NULL,tokens INTEGER NOT NULL,elapsed INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX messages_session ON messages(session,created)");
    }
    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}
    public synchronized String create(String model) {
        String id = UUID.randomUUID().toString(); ContentValues row = new ContentValues(); row.put("id", id); row.put("title", "新对话"); row.put("model", model); row.put("updated", System.currentTimeMillis());
        getWritableDatabase().insertOrThrow("sessions", null, row); app.prefs.edit().putString("session", id).apply(); return id;
    }
    public synchronized void select(String id) {
        try (Cursor c = getReadableDatabase().rawQuery("SELECT id FROM sessions WHERE id=?", new String[]{id})) {
            if (!c.moveToFirst()) throw new IllegalArgumentException("找不到这段对话");
        }
        app.prefs.edit().putString("session", id).apply(); app.emit();
    }
    public synchronized String session() { return app.prefs.getString("session", ""); }
    public synchronized String append(String session, String role, String content, String status) {
        String id = UUID.randomUUID().toString(); ContentValues row = new ContentValues(); row.put("id", id); row.put("session", session); row.put("role", role); row.put("content", content); row.put("reasoning", ""); row.put("status", status); row.put("error", ""); row.put("created", System.currentTimeMillis()); row.put("tokens", 0); row.put("elapsed", 0);
        getWritableDatabase().insertOrThrow("messages", null, row);
        ContentValues update = new ContentValues(); update.put("updated", System.currentTimeMillis());
        if (role.equals("user")) update.put("title", content.length() > 28 ? content.substring(0, 28) + "…" : content);
        getWritableDatabase().update("sessions", update, "id=?", new String[]{session}); return id;
    }
    public synchronized void update(String id, String text, String reasoning, String status, String error, int tokens, long elapsed) {
        ContentValues row = new ContentValues(); row.put("content", text); row.put("reasoning", reasoning); row.put("status", status); row.put("error", error); row.put("tokens", tokens); row.put("elapsed", elapsed);
        getWritableDatabase().update("messages", row, "id=?", new String[]{id});
    }
    public synchronized JSONArray history(String session, int context) throws Exception {
        java.util.List<ChatHistory.Message> chronological = new java.util.ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery("SELECT role,content,status FROM (SELECT rowid,role,content,status,created FROM messages WHERE session=? ORDER BY created DESC,rowid DESC LIMIT 32) ORDER BY created,rowid", new String[]{session})) {
            while (c.moveToNext()) chronological.add(new ChatHistory.Message(c.getString(0), c.getString(1), c.getString(2)));
        }
        JSONArray result = new JSONArray();
        for (ChatHistory.Message message : ChatHistory.select(chronological, Math.max(0, context - 768), 16))
            result.put(new JSONObject().put("role", message.role).put("content", message.content));
        return result;
    }
    public synchronized JSONObject snapshot() throws Exception {
        JSONObject result = new JSONObject(); String selected = session(); result.put("sessionId", selected);
        JSONArray sessions = new JSONArray();
        try (Cursor c = getReadableDatabase().rawQuery("SELECT id,title,model,updated FROM sessions ORDER BY updated DESC LIMIT 40", null)) {
            while (c.moveToNext()) { JSONObject s = new JSONObject(); s.put("id", c.getString(0)); s.put("title", c.getString(1)); s.put("modelId", c.getString(2)); s.put("updated", c.getLong(3)); sessions.put(s); }
        }
        result.put("sessions", sessions); JSONArray messages = new JSONArray();
        try (Cursor c = getReadableDatabase().rawQuery("SELECT * FROM (SELECT rowid,* FROM messages WHERE session=? ORDER BY created DESC,rowid DESC LIMIT 80) ORDER BY created,rowid", new String[]{selected})) {
            while (c.moveToNext()) { JSONObject m = new JSONObject();
                for (String name : new String[]{"id", "role", "content", "reasoning", "status", "error"}) m.put(name, c.getString(c.getColumnIndexOrThrow(name)));
                m.put("tokens", c.getInt(c.getColumnIndexOrThrow("tokens"))); m.put("elapsed", c.getLong(c.getColumnIndexOrThrow("elapsed"))); messages.put(m);
            }
        }
        result.put("messages", messages); return result;
    }
    public synchronized void removeSession(String id) {
        getWritableDatabase().beginTransaction();
        try { getWritableDatabase().delete("messages", "session=?", new String[]{id}); getWritableDatabase().delete("sessions", "id=?", new String[]{id}); getWritableDatabase().setTransactionSuccessful(); }
        finally { getWritableDatabase().endTransaction(); }
        if (session().equals(id)) app.prefs.edit().remove("session").apply(); app.emit();
    }
}
