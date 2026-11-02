package com.lma.app.core;

import android.util.AtomicFile;
import org.json.*;
import java.io.*;
import java.util.*;

/** Small, versioned internal sequences; no user code, plugins, arbitrary graph or remote workers. */
public final class WorkflowStore {
    private final AtomicFile file; private JSONObject state;
    private volatile Set<String> references=Collections.emptySet();
    public WorkflowStore(File directory) throws Exception {
        if(!directory.isDirectory()&&!directory.mkdirs()) throw new IOException("无法创建计划存储"); file=new AtomicFile(new File(directory,"workflows.json"));
        try { state=DataFiles.read(file,2*1024*1024); } catch(FileNotFoundException missing) { state=new JSONObject().put("schema","lma.workflows/1").put("chains",new JSONObject()); }
        if(!state.getString("schema").equals("lma.workflows/1")) throw new IOException("未知的计划存储版本"); refresh();
    }
    public boolean referencesArtifact(String id) { return references.contains(id); }
    private void refresh() throws Exception {
        Set<String> result=new HashSet<>(); JSONObject chains=state.getJSONObject("chains");
        for(Iterator<String> it=chains.keys();it.hasNext();) { JSONObject c=chains.getJSONObject(it.next()); if(c.optBoolean("removed")) continue; JSONArray steps=c.getJSONArray("steps");
            for(int i=0;i<steps.length();i++) { JSONObject input=steps.getJSONObject(i).getJSONObject("request").optJSONObject("input"); JSONArray refs=input==null?null:input.optJSONArray("artifacts"); if(refs!=null) for(int j=0;j<refs.length();j++) result.add(refs.getJSONObject(j).getString("artifactId")); JSONArray outputs=steps.getJSONObject(i).optJSONArray("artifacts"); if(outputs!=null) for(int j=0;j<outputs.length();j++) result.add(outputs.getString(j)); }
        } references=Collections.unmodifiableSet(result);
    }
    private void persist(JSONObject next) throws Exception { DataFiles.write(file,next,2*1024*1024); state=next; refresh(); }
    public synchronized JSONArray snapshot() throws Exception { JSONArray out=new JSONArray(); JSONObject chains=state.getJSONObject("chains");for(Iterator<String> it=chains.keys();it.hasNext();) { JSONObject c=chains.getJSONObject(it.next()); if(!c.optBoolean("removed")) out.put(DataFiles.copy(c)); } return out; }
    public synchronized JSONObject get(String id) throws Exception { return DataFiles.copy(state.getJSONObject("chains").getJSONObject(id)); }
    public synchronized JSONObject create(JSONObject draft,String session,String key) throws Exception {
        return create(draft,session,key,TaskInput.fingerprint(draft));
    }
    public synchronized JSONObject existing(String key,String sourceHash) throws Exception {
        ModelBundle.key(key);JSONObject old=state.getJSONObject("chains").optJSONObject(key);if(old==null)return null;
        if(!old.getString("draftHash").equals(sourceHash))throw new IllegalArgumentException("计划编号冲突");return DataFiles.copy(old);
    }
    public synchronized JSONObject create(JSONObject draft,String session,String key,String sourceHash) throws Exception {
        JSONObject previous=existing(key,sourceHash);if(previous!=null)return previous;JSONObject chains=state.getJSONObject("chains");
        if(chains.length()>=128) throw new IllegalArgumentException("计划记录已满，请明确清理结束的计划");
        JSONArray steps=draft.getJSONArray("steps"); if(steps.length()<1||steps.length()>8) throw new IllegalArgumentException("计划只允许 1–8 步");
        JSONArray frozen=new JSONArray();
        for(int i=0;i<steps.length();i++) {
            JSONObject source=steps.getJSONObject(i); JSONObject request=draftRequest(source); if(!request.getString("type").equals("media.compose"))request.put("allowUnmeasured",source.getJSONObject("request").optBoolean("allowUnmeasured",false)); JSONArray depends=source.optJSONArray("dependsOn"); if(depends==null) depends=new JSONArray(); Set<Integer> unique=new HashSet<>();
            for(int j=0;j<depends.length();j++) { int at=depends.getInt(j); if(at<0||at>=i||!unique.add(at)) throw new IllegalArgumentException("依赖必须指向前面的唯一步骤"); }
            JSONArray bindings=source.optJSONArray("bindings"); if(bindings==null) bindings=new JSONArray();
            for(int j=0;j<bindings.length();j++) { JSONObject bind=bindings.getJSONObject(j); int from=bind.getInt("step"); if(!unique.contains(from)) throw new IllegalArgumentException("素材绑定必须声明依赖步骤"); if(bind.optInt("output",0)<0||bind.optInt("output",0)>7) throw new IllegalArgumentException("结果编号无效"); String role=bind.getString("role"); if(!role.equals("prompt")) InputSpec.key(role); }
            frozen.put(new JSONObject().put("index",i).put("request",request).put("dependsOn",depends).put("bindings",bindings).put("state","ready").put("jobId","").put("attempt",0).put("artifacts",new JSONArray()));
        }
        JSONObject chain=new JSONObject().put("id",key).put("session",session).put("template",draft.optString("template","custom")).put("draftHash",sourceHash).put("steps",frozen).put("state","ready").put("createdAt",System.currentTimeMillis());
        JSONObject next=DataFiles.copy(state); next.getJSONObject("chains").put(key,chain); persist(next); return DataFiles.copy(chain);
    }
    /** Validate the future input shape with inert placeholders, never resolve or execute them. */
    public static JSONObject draftRequest(JSONObject step)throws Exception{
        JSONObject original=step.getJSONObject("request"),request=DataFiles.copy(original),input=request.getJSONObject("input");JSONArray bindings=step.optJSONArray("bindings"),refs=input.optJSONArray("artifacts");if(refs==null)refs=new JSONArray();Set<String> roles=new HashSet<>();for(int i=0;i<refs.length();i++)roles.add(refs.getJSONObject(i).getString("role"));
        if(bindings!=null)for(int i=0;i<bindings.length();i++){String role=bindings.getJSONObject(i).getString("role");if(role.equals("prompt"))continue;if(!roles.add(role))throw new IllegalArgumentException("同一输入角色不能同时绑定两份素材");refs.put(new JSONObject().put("role",role).put("artifactId","binding_placeholder_"+i));}
        if(refs.length()>0)input.put("artifacts",refs);if(!input.has("prompt"))input.put("prompt","");request=TaskRequests.draft(request);
        if(original.getJSONObject("input").has("artifacts"))request.getJSONObject("input").put("artifacts",original.getJSONObject("input").getJSONArray("artifacts"));else request.getJSONObject("input").remove("artifacts");return request;
    }
    public synchronized void update(JSONObject chain) throws Exception { JSONObject next=DataFiles.copy(state); if(!next.getJSONObject("chains").has(chain.getString("id"))) throw new IllegalArgumentException("计划不存在"); next.getJSONObject("chains").put(chain.getString("id"),DataFiles.copy(chain)); persist(next); }
    public synchronized void cancel(String id) throws Exception { JSONObject c=get(id);if(Arrays.asList("succeeded","cancelled").contains(c.getString("state")))return;c.put("cancelRequested",true).put("state","cancelling");update(c); }
    public synchronized void retry(String id,int step) throws Exception {
        JSONObject c=get(id); if(c.optBoolean("cancelRequested")) throw new IllegalArgumentException("已取消计划请复制为新计划"); JSONArray steps=c.getJSONArray("steps"); JSONObject item=steps.getJSONObject(step);
        if(!Arrays.asList("failed","interrupted","cancelled","rejected").contains(item.getString("state"))) throw new IllegalArgumentException("只重试失败或中断步骤");
        JSONArray attempts=item.optJSONArray("attempts");if(attempts==null)attempts=new JSONArray();attempts.put(new JSONObject().put("jobId",item.optString("jobId")).put("state",item.getString("state")).put("error",item.optString("error")).put("artifacts",item.getJSONArray("artifacts")));item.put("attempts",attempts);
        item.put("state","ready").put("jobId","").put("attempt",item.getInt("attempt")+1).put("artifacts",new JSONArray()).remove("error");
        for(int i=step+1;i<steps.length();i++) if(steps.getJSONObject(i).getString("state").equals("blocked")) steps.getJSONObject(i).put("state","ready"); c.put("state","ready");update(c);
    }
    public synchronized void remove(String id) throws Exception { JSONObject c=get(id); if(!Arrays.asList("succeeded","failed","cancelled","blocked").contains(c.getString("state"))) throw new IllegalArgumentException("请先取消活动计划");c.put("removed",true);update(c); }
}
