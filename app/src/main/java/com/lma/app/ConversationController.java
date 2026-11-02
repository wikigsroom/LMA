package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Outbox reconciliation links chat cards to the original service queue. Never owns another inference executor. */
public final class ConversationController implements AutoCloseable {
    private final LmaApp app; private final LmaService owner;
    private final ScheduledExecutorService worker=Executors.newSingleThreadScheduledExecutor(r->new Thread(r,"LMA-conversations"));
    private final AtomicBoolean scheduled=new AtomicBoolean(); private volatile boolean closed;
    private final Map<String,String> observed=new HashMap<>();
    public ConversationController(LmaApp app,LmaService owner){this.app=app;this.owner=owner;wake();}
    public JSONObject submit(JSONObject command) throws Exception {
        JSONObject request=TaskInput.validate(command.getJSONObject("request"));String key=command.optString("idempotencyKey");if(key.isEmpty())throw new IllegalArgumentException("缺少稳定提交编号，请保留草稿后重试");
        String parent=command.optString("parentJobId");if(!parent.isEmpty())app.jobs.get(parent);JSONObject intent=app.chats.intent(app.chats.session(),command.optString("text",request.getJSONObject("input").optString("prompt")),request,key,"manual",parent);wake();app.emit();return intent;
    }
    public JSONObject chain(JSONObject command) throws Exception {
        String sourceHash=TaskInput.fingerprint(command.getJSONObject("draft")),key=command.getString("idempotencyKey");JSONObject old=app.workflows.existing(key,sourceHash);if(old!=null)return old;
        String session=app.chats.session();if(session.isEmpty())session=app.chats.create(app.engineModel);
        JSONObject draft=DataFiles.copy(command.getJSONObject("draft"));JSONArray steps=draft.getJSONArray("steps");for(int i=0;i<steps.length();i++) {JSONObject request=steps.getJSONObject(i).getJSONObject("request");if(request.getString("type").equals("media.compose"))continue;String id=request.getString("bundleId");app.localEngines.require(app.bundles.bundle(id),request.getString("type"));if(!app.bundles.plan(id).getBoolean("installed"))throw new IllegalArgumentException("请先明确安装计划所选模型；保存计划不会下载");request.put("parameters",app.bundles.parameters(id).normalize(app.bundles.settings(id).getJSONObject("values"),request.optJSONObject("parameters")==null?new JSONObject():request.getJSONObject("parameters")).getJSONObject("values"));}
        JSONObject result=app.workflows.create(draft,session,key,sourceHash);wake();app.emit();return result;
    }
    public void wake(){if(closed||!scheduled.compareAndSet(false,true))return;worker.schedule(this::pump,100,TimeUnit.MILLISECONDS);}
    private void pump(){boolean again=false,changed=false;
        try {
            if(closed||app.jobHost==null)return;
            JSONArray intents=app.chats.activeIntents();
            for(int i=0;i<intents.length();i++) {
                JSONObject intent=intents.getJSONObject(i);String key=intent.getString("id");
                try {
                    JSONObject job=app.jobs.lookup(key);
                    if(job==null)job=app.jobHost.submit(intent.getJSONObject("request"),key);
                    if(!intent.optString("parentJobId").isEmpty())job=app.jobs.relate(job.getString("id"),intent.getString("parentJobId"));
                    String signature=job.getString("state")+":"+job.optJSONArray("artifacts")+":"+job.optString("error");
                    if(!signature.equals(observed.get(key))){app.chats.link(key,job);observed.put(key,signature);changed=true;}
                    if(!terminal(job.getString("state")))again=true;
                }catch(Exception e){app.chats.reject(key,message(e));changed=true;}
            }
            JSONArray chains=app.workflows.snapshot();
            for(int i=0;i<chains.length();i++) {JSONObject chain=chains.getJSONObject(i);if(Arrays.asList("succeeded","failed","cancelled","blocked").contains(chain.getString("state")))continue;boolean modified=advance(chain);if(modified){app.workflows.update(chain);changed=true;}if(!Arrays.asList("succeeded","failed","cancelled","blocked").contains(chain.getString("state")))again=true;}
            if(owner.chat.reconcileTools()) {again=true;changed=true;}
        }catch(Exception error){app.log("会话对账尚未完成："+message(error));}
        finally{scheduled.set(false);if(changed)app.emit();if(again&&!closed&&scheduled.compareAndSet(false,true))worker.schedule(this::pump,700,TimeUnit.MILLISECONDS);}
    }
    private boolean advance(JSONObject chain) throws Exception {
        return WorkflowRunner.advance(chain,new WorkflowRunner.Host(){
            @Override public JSONObject lookup(String key)throws Exception{return app.jobs.lookup(key);}
            @Override public JSONObject get(String id)throws Exception{return app.jobs.get(id);}
            @Override public void cancel(String id)throws Exception{app.jobHost.cancel(id);}
            @Override public JSONObject admit(String session,JSONObject request,String key)throws Exception{
                JSONObject intent=app.chats.intent(session,request.getJSONObject("input").optString("prompt"),request,key,"template");
                JSONObject job=app.jobs.lookup(key);if(job==null)job=app.jobHost.submit(intent.getJSONObject("request"),key);app.chats.link(key,job);return job;
            }
            @Override public String readText(String artifact)throws Exception{
                JSONObject meta=app.artifacts.get(artifact);if(!meta.getJSONObject("metadata").getString("mime").equals("text/plain"))throw new IllegalArgumentException("旁白步骤必须输出文字");
                try(ArtifactStore.Lease lease=app.artifacts.acquire(artifact);java.io.InputStream in=new java.io.FileInputStream(lease.file)){return Store.read(in,16000);}
            }
        });
    }
    public static boolean terminal(String state){return Arrays.asList("succeeded","failed","cancelled","interrupted").contains(state);}
    private static String message(Exception e){return e.getMessage()==null?"本机处理失败，请查看任务记录":e.getMessage();}
    @Override public void close(){closed=true;worker.shutdown();}
}
