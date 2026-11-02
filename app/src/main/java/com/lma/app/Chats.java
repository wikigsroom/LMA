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
        super(app, "lma-chats.db", null, 2); this.app = app;
        ContentValues interrupted = new ContentValues(); interrupted.put("status", "interrupted");
        interrupted.put("error", "上次生成已中断，已收到的内容保存在这里");
        getWritableDatabase().update("messages", interrupted, "status=?", new String[]{"generating"});
        ContentValues planInterrupted=new ContentValues();planInterrupted.put("state","interrupted");getWritableDatabase().update("chat_tools",planInterrupted,"state=?",new String[]{"continuing"});
        refreshReferences();
    }
    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE sessions(id TEXT PRIMARY KEY,title TEXT NOT NULL,model TEXT NOT NULL,updated INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE messages(id TEXT PRIMARY KEY,session TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,reasoning TEXT NOT NULL,status TEXT NOT NULL,error TEXT NOT NULL,created INTEGER NOT NULL,tokens INTEGER NOT NULL,elapsed INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX messages_session ON messages(session,created)");
        upgradeParts(db);
    }
    // SQLiteOpenHelper wraps upgrades in a transaction: any failed statement rolls back v1 intact.
    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) { if (oldVersion < 2) upgradeParts(db); }
    private void upgradeParts(SQLiteDatabase db) {
        db.execSQL("ALTER TABLE messages ADD COLUMN parts TEXT NOT NULL DEFAULT '[]'");
        db.execSQL("ALTER TABLE messages ADD COLUMN parent TEXT NOT NULL DEFAULT ''");
        db.execSQL("CREATE TABLE chat_outbox(id TEXT PRIMARY KEY,session TEXT NOT NULL,message TEXT NOT NULL,request TEXT NOT NULL,job TEXT NOT NULL DEFAULT '',state TEXT NOT NULL,error TEXT NOT NULL DEFAULT '',created INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX chat_outbox_state ON chat_outbox(state)");
        db.execSQL("CREATE TABLE chat_refs(session TEXT NOT NULL,message TEXT NOT NULL,artifact TEXT NOT NULL,PRIMARY KEY(session,message,artifact))");
        db.execSQL("CREATE TABLE chat_tools(id TEXT PRIMARY KEY,session TEXT NOT NULL,payload TEXT NOT NULL,state TEXT NOT NULL)");
        // Older text stays in its original columns, read as a text block without re-encoding bytes.
    }
    private volatile java.util.Set<String> pinned = java.util.Collections.emptySet();
    public boolean referencesArtifact(String id) { return pinned.contains(id); }
    private void refreshReferences() {
        java.util.Set<String> next = new java.util.HashSet<>();
        try (Cursor c=getReadableDatabase().rawQuery("SELECT DISTINCT artifact FROM chat_refs",null)) { while(c.moveToNext()) next.add(c.getString(0)); }
        pinned=java.util.Collections.unmodifiableSet(next);
    }
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
        result.put("sessions", sessions);
        JSONObject page = page(selected, Long.MAX_VALUE, 60);
        result.put("messages", page.getJSONArray("messages")).put("page", page.getJSONObject("page"));
        return result;
    }
    public synchronized JSONObject page(String session, long before, int limit) throws Exception {
        limit=Math.max(1,Math.min(80,limit)); JSONArray result=new JSONArray(); long cursor=0;
        try(Cursor c=getReadableDatabase().rawQuery("SELECT rowid,* FROM (SELECT rowid,* FROM messages WHERE session=? AND rowid<? ORDER BY rowid DESC LIMIT ?) ORDER BY rowid",new String[]{session,String.valueOf(before),String.valueOf(limit)})) {
            while(c.moveToNext()) {
                long row=c.getLong(c.getColumnIndexOrThrow("rowid")); if(cursor==0) cursor=row;
                JSONObject m=new JSONObject();
                for(String name:new String[]{"id","role","content","reasoning","status","error","parent"}) m.put(name,c.getString(c.getColumnIndexOrThrow(name)));
                JSONArray parts=new JSONArray(c.getString(c.getColumnIndexOrThrow("parts")));
                if(!m.getString("content").isEmpty()) { JSONArray withText=new JSONArray().put(new JSONObject().put("type","text").put("text",m.getString("content"))); for(int i=0;i<parts.length();i++) withText.put(parts.get(i)); parts=withText; }
                m.put("parts",parts).put("cursor",row).put("created",c.getLong(c.getColumnIndexOrThrow("created"))).put("tokens",c.getInt(c.getColumnIndexOrThrow("tokens"))).put("elapsed",c.getLong(c.getColumnIndexOrThrow("elapsed"))); result.put(m);
            }
        }
        boolean more=false;
        if(cursor>0) try(Cursor c=getReadableDatabase().rawQuery("SELECT 1 FROM messages WHERE session=? AND rowid<? LIMIT 1",new String[]{session,String.valueOf(cursor)})) { more=c.moveToFirst(); }
        return new JSONObject().put("sessionId",session).put("messages",result).put("page",new JSONObject().put("before",cursor).put("hasMore",more));
    }
    public synchronized JSONObject sessionPage(long before, int limit) throws Exception {
        if(before<=0)before=Long.MAX_VALUE;JSONArray rows=new JSONArray(); long next=before;
        try(Cursor c=getReadableDatabase().rawQuery("SELECT rowid,id,title,model,updated FROM sessions WHERE rowid<? ORDER BY rowid DESC LIMIT ?",new String[]{String.valueOf(before),String.valueOf(Math.max(1,Math.min(80,limit)))})) {
            while(c.moveToNext()) { next=c.getLong(0); rows.put(new JSONObject().put("cursor",next).put("id",c.getString(1)).put("title",c.getString(2)).put("modelId",c.getString(3)).put("updated",c.getLong(4))); }
        }
        return new JSONObject().put("sessions",rows).put("before",next).put("hasMore",rows.length()==Math.max(1,Math.min(80,limit)));
    }
    public synchronized void parts(String message, JSONArray parts) throws Exception {
        if(parts.length()>32 || parts.toString().length()>64000) throw new IllegalArgumentException("消息内容块超过限制");
        SQLiteDatabase db=getWritableDatabase(); db.beginTransaction();
        try {
            String session; try(Cursor c=db.rawQuery("SELECT session FROM messages WHERE id=?",new String[]{message})) { if(!c.moveToFirst()) throw new IllegalArgumentException("消息不存在"); session=c.getString(0); }
            ContentValues row=new ContentValues(); row.put("parts",parts.toString()); db.update("messages",row,"id=?",new String[]{message});
            db.delete("chat_refs","message=?",new String[]{message});
            for(int i=0;i<parts.length();i++) { JSONObject part=parts.getJSONObject(i); if(part.optString("type").equals("artifact_ref")) { com.lma.app.core.ModelBundle.key(part.getString("artifactId")); ContentValues ref=new ContentValues(); ref.put("session",session); ref.put("message",message); ref.put("artifact",part.getString("artifactId")); db.insertWithOnConflict("chat_refs",null,ref,SQLiteDatabase.CONFLICT_IGNORE); } }
            db.setTransactionSuccessful();
        } finally { db.endTransaction(); }
        refreshReferences();
    }
    public synchronized JSONObject intent(String session, String prompt, JSONObject request, String key, String source) throws Exception {return intent(session,prompt,request,key,source,"");}
    public synchronized JSONObject intent(String session, String prompt, JSONObject request, String key, String source,String parent) throws Exception {
        com.lma.app.core.ModelBundle.key(key);
        try(Cursor c=getReadableDatabase().rawQuery("SELECT * FROM chat_outbox WHERE id=?",new String[]{key})) { if(c.moveToFirst()) { JSONObject old=intentRow(c); if(!com.lma.app.core.DataFiles.canonical(old.getJSONObject("request")).equals(com.lma.app.core.DataFiles.canonical(request))) throw new IllegalArgumentException("调用编号已经用于不同请求"); return old; } }
        SQLiteDatabase db=getWritableDatabase(); db.beginTransaction();
        try {
            if(session.isEmpty()) session=create(app.engineModel);
            String user=source.equals("tool")?"":append(session,"user",prompt,"done"); JSONArray refs=new JSONArray();
            JSONArray selected=request.optJSONObject("input")==null?null:request.getJSONObject("input").optJSONArray("artifacts");
            if(selected!=null) for(int i=0;i<selected.length();i++) refs.put(new JSONObject().put("type","artifact_ref").put("artifactId",selected.getJSONObject(i).getString("artifactId")).put("use",selected.getJSONObject(i).getString("role")));
            if(!user.isEmpty())parts(user,refs);
            String message=append(session,"assistant","","queued");ContentValues lineage=new ContentValues();lineage.put("parent",parent);db.update("messages",lineage,"id=?",new String[]{message});
            parts(message,new JSONArray().put(new JSONObject().put("type","job_ref").put("requestKey",key).put("jobId","").put("source",source)));
            ContentValues row=new ContentValues(); row.put("id",key);row.put("session",session);row.put("message",message);row.put("request",request.toString());row.put("state","pending");row.put("created",System.currentTimeMillis());db.insertOrThrow("chat_outbox",null,row);
            db.setTransactionSuccessful();
        } finally { db.endTransaction(); refreshReferences(); }
        return findIntent(key);
    }
    private JSONObject intentRow(Cursor c) throws Exception {
        JSONObject row=new JSONObject(); for(String n:new String[]{"id","session","message","job","state","error"}) row.put(n,c.getString(c.getColumnIndexOrThrow(n)));
        try(Cursor parent=getReadableDatabase().rawQuery("SELECT parent FROM messages WHERE id=?",new String[]{row.getString("message")})){if(parent.moveToFirst())row.put("parentJobId",parent.getString(0));}return row.put("request",new JSONObject(c.getString(c.getColumnIndexOrThrow("request"))));
    }
    public synchronized JSONObject findIntent(String key) throws Exception { try(Cursor c=getReadableDatabase().rawQuery("SELECT * FROM chat_outbox WHERE id=?",new String[]{key})) { if(!c.moveToFirst()) throw new IllegalArgumentException("提交意图不存在"); return intentRow(c); } }
    public synchronized JSONArray activeIntents() throws Exception { JSONArray result=new JSONArray(); try(Cursor c=getReadableDatabase().rawQuery("SELECT * FROM chat_outbox WHERE state IN ('pending','linked') ORDER BY created LIMIT 64",null)) { while(c.moveToNext()) result.put(intentRow(c)); } return result; }
    public synchronized void link(String key, JSONObject job) throws Exception {
        SQLiteDatabase db=getWritableDatabase();db.beginTransaction();
        try {
        JSONObject intent=findIntent(key); String state=job.getString("state"); boolean end=java.util.Arrays.asList("succeeded","failed","cancelled","interrupted").contains(state);
        ContentValues row=new ContentValues(); row.put("job",job.getString("id")); row.put("state",end?"done":"linked"); row.put("error",job.optString("error"));
        getWritableDatabase().update("chat_outbox",row,"id=?",new String[]{key});
        JSONArray parts=new JSONArray().put(new JSONObject().put("type","job_ref").put("jobId",job.getString("id")).put("requestKey",key));
        JSONArray artifacts=job.optJSONArray("artifacts"); if(artifacts!=null) for(int i=0;i<artifacts.length();i++) parts.put(new JSONObject().put("type","artifact_ref").put("artifactId",artifacts.getString(i)).put("use","result"));
        parts(intent.getString("message"),parts); update(intent.getString("message"),"","",state,job.optString("error"),0,0);
        db.setTransactionSuccessful();
        }finally{db.endTransaction();refreshReferences();}
    }
    public synchronized void reject(String key,String error) throws Exception {
        SQLiteDatabase db=getWritableDatabase();db.beginTransaction();try{
        JSONObject intent=findIntent(key); ContentValues row=new ContentValues();row.put("state","rejected");row.put("error",error);getWritableDatabase().update("chat_outbox",row,"id=?",new String[]{key});
        parts(intent.getString("message"),new JSONArray().put(new JSONObject().put("type","draft").put("request",intent.getJSONObject("request")).put("requestKey",key)));
        update(intent.getString("message"),"","","error",error,0,0);
        db.setTransactionSuccessful();}finally{db.endTransaction();refreshReferences();}
    }
    public synchronized String messageSession(String id) {try(Cursor c=getReadableDatabase().rawQuery("SELECT session FROM messages WHERE id=?",new String[]{id})){if(!c.moveToFirst())throw new IllegalArgumentException("消息不存在");return c.getString(0);}}
    public synchronized boolean latestAssistant(String id) {String session=messageSession(id);try(Cursor c=getReadableDatabase().rawQuery("SELECT id FROM messages WHERE session=? ORDER BY rowid DESC LIMIT 1",new String[]{session})){return c.moveToFirst()&&c.getString(0).equals(id);}}
    public synchronized boolean userAfter(String id) {try(Cursor c=getReadableDatabase().rawQuery("SELECT 1 FROM messages WHERE session=(SELECT session FROM messages WHERE id=?) AND role='user' AND rowid>(SELECT rowid FROM messages WHERE id=?) LIMIT 1",new String[]{id,id})){return c.moveToFirst();}}
    public synchronized void saveTools(JSONObject plan) throws Exception {ContentValues row=new ContentValues();row.put("id",plan.getString("id"));row.put("session",plan.getString("session"));row.put("payload",plan.toString());row.put("state",plan.getString("state"));getWritableDatabase().insertWithOnConflict("chat_tools",null,row,SQLiteDatabase.CONFLICT_REPLACE);}
    public synchronized JSONObject tools(String id) throws Exception {try(Cursor c=getReadableDatabase().rawQuery("SELECT payload,state FROM chat_tools WHERE id=?",new String[]{id})){if(!c.moveToFirst())throw new IllegalArgumentException("工具计划不存在");return new JSONObject(c.getString(0)).put("state",c.getString(1));}}
    public synchronized JSONArray activeTools() throws Exception {JSONArray result=new JSONArray();try(Cursor c=getReadableDatabase().rawQuery("SELECT payload,state FROM chat_tools WHERE state IN ('approved','waiting','ready') LIMIT 16",null)){while(c.moveToNext())result.put(new JSONObject(c.getString(0)).put("state",c.getString(1)));}return result;}
    public synchronized void removeSession(String id) {
        getWritableDatabase().beginTransaction();
        try { getWritableDatabase().delete("chat_tools","session=?",new String[]{id});getWritableDatabase().delete("chat_refs","session=?",new String[]{id}); getWritableDatabase().delete("chat_outbox","session=?",new String[]{id}); getWritableDatabase().delete("messages", "session=?", new String[]{id}); getWritableDatabase().delete("sessions", "id=?", new String[]{id}); getWritableDatabase().setTransactionSuccessful(); }
        finally { getWritableDatabase().endTransaction(); }
        refreshReferences(); if (session().equals(id)) app.prefs.edit().remove("session").apply(); app.emit();
    }
}
