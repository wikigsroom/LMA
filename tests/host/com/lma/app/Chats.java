package com.lma.app;
import java.util.*;
import org.json.*;
import com.lma.app.core.ChatHistory;
/** In-memory persistence port. SQLite integration is checked separately and still needs Android. */
public final class Chats {
    private final LmaApp app;
    public final List<JSONObject> rows = new ArrayList<>();
    private String selected = "";
    public Chats(LmaApp app) { this.app = app; }
    public synchronized String session() { return selected; }
    public synchronized String create(String model) { selected = UUID.randomUUID().toString(); return selected; }
    public synchronized String append(String session, String role, String content, String status) {
        String id = UUID.randomUUID().toString(); rows.add(new JSONObject().put("id", id).put("session", session).put("role", role).put("content", content).put("status", status)); return id;
    }
    public synchronized void update(String id, String text, String reasoning, String status, String error, int tokens, long elapsed) {
        for (JSONObject row : rows) if (row.getString("id").equals(id)) row.put("content", text).put("reasoning", reasoning).put("status", status).put("error", error).put("tokens", tokens).put("elapsed", elapsed);
    }
    public synchronized JSONObject last() { return new JSONObject(rows.get(rows.size() - 1).toString()); }
    public synchronized JSONArray history(String session, int context) {
        List<ChatHistory.Message> input = new ArrayList<>();
        for (JSONObject row : rows) if (row.getString("session").equals(session)) input.add(new ChatHistory.Message(row.getString("role"), row.getString("content"), row.getString("status")));
        JSONArray output = new JSONArray();
        for (ChatHistory.Message m : ChatHistory.select(input, Math.max(0, context - 768), 16)) output.put(new JSONObject().put("role", m.role).put("content", m.content));
        return output;
    }
}
