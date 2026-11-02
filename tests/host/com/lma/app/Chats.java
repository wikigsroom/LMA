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
    private final Map<String,JSONObject> plans=new HashMap<>(),outbox=new HashMap<>();
    public void parts(String id,JSONArray values){for(JSONObject row:rows)if(row.getString("id").equals(id))row.put("parts",values);}
    public String messageSession(String id){for(JSONObject row:rows)if(row.getString("id").equals(id))return row.getString("session");throw new IllegalArgumentException();}
    public void saveTools(JSONObject plan){plans.put(plan.getString("id"),new JSONObject(plan.toString()));}
    public JSONObject tools(String id){return new JSONObject(plans.get(id).toString());}
    public JSONArray activeTools(){JSONArray out=new JSONArray();for(JSONObject p:plans.values())if(Arrays.asList("approved","waiting","ready").contains(p.getString("state")))out.put(new JSONObject(p.toString()));return out;}
    public boolean userAfter(String id){boolean seen=false;for(JSONObject row:rows){if(seen&&row.getString("role").equals("user"))return true;if(row.getString("id").equals(id))seen=true;}return false;}
    public JSONObject intent(String session,String prompt,JSONObject request,String key,String source,String parent){return intent(session,prompt,request,key,source);}
    public JSONObject intent(String session,String prompt,JSONObject request,String key,String source){if(outbox.containsKey(key))return outbox.get(key);JSONObject r=new JSONObject().put("id",key).put("session",session).put("request",request);outbox.put(key,r);return r;}
    public JSONArray activeIntents(){return new JSONArray();}
    public void link(String key,JSONObject job){}public void reject(String key,String error){}
    public synchronized JSONArray history(String session, int context) {
        List<ChatHistory.Message> input = new ArrayList<>();
        for (JSONObject row : rows) if (row.getString("session").equals(session)) input.add(new ChatHistory.Message(row.getString("role"), row.getString("content"), row.getString("status")));
        JSONArray output = new JSONArray();
        for (ChatHistory.Message m : ChatHistory.select(input, Math.max(0, context - 768), 16)) output.put(new JSONObject().put("role", m.role).put("content", m.content));
        return output;
    }
}
