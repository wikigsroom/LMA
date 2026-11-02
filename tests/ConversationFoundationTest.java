package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Production state machines and real PCM bytes. No trained models or virtualized Android. */
public final class ConversationFoundationTest {
    private static int checks;
    private static void ok(boolean condition,String message){checks++;if(!condition)throw new AssertionError(message);}
    private interface Run{void run()throws Exception;}
    private static void reject(Run run,String message)throws Exception{boolean failed=false;try{run.run();}catch(Exception expected){failed=true;}ok(failed,message);}
    private static JSONObject req(String type,String model)throws Exception{return new JSONObject().put("type",type).put("bundleId",model).put("input",new JSONObject().put("prompt","fixture prompt")).put("parameters",new JSONObject()).put("allowUnmeasured",true);}
    private static JSONObject delta(int index,String id,String name,String args)throws Exception{JSONObject d=new JSONObject().put("index",index);if(id!=null)d.put("id",id);return d.put("function",new JSONObject().put("name",name).put("arguments",args));}
    private static final class Jobs implements WorkflowRunner.Host {
        final Map<String,JSONObject> jobs=new LinkedHashMap<>();int admitted,cancelled;boolean crash;
        public JSONObject lookup(String key){return jobs.get(key);}
        public JSONObject get(String id){for(JSONObject j:jobs.values())if(j.getString("id").equals(id))return j;throw new IllegalArgumentException("missing");}
        public JSONObject admit(String session,JSONObject request,String key)throws Exception{JSONObject j=new JSONObject().put("id","job_"+(++admitted)).put("state","queued").put("request",request).put("artifacts",new JSONArray());jobs.put(key,j);if(crash){crash=false;throw new AssertionError("simulated process death after queue commit");}return j;}
        public void cancel(String id){cancelled++;get(id).put("state","cancelled");}
        public String readText(String artifact){return "narration from "+artifact;}
        void finish(String id,String state)throws Exception{get(id).put("state",state).put("artifacts",state.equals("succeeded")?new JSONArray().put("artifact_"+id):new JSONArray());}
    }
    private static JSONObject draft()throws Exception{return new JSONObject().put("template","W02").put("steps",new JSONArray().put(new JSONObject().put("request",req("image.generate","image_model"))).put(new JSONObject().put("request",req("video.generate","video_model")).put("dependsOn",new JSONArray().put(0)).put("bindings",new JSONArray().put(new JSONObject().put("step",0).put("output",0).put("role","image")))));}
    private static File wav(File root,String name,int channels,int rate,short value,int count)throws Exception{File f=new File(root,name);try(DataOutputStream out=new DataOutputStream(new FileOutputStream(f))){out.writeBytes("RIFF");out.writeInt(Integer.reverseBytes(36+count*channels*2));out.writeBytes("WAVEfmt ");out.writeInt(Integer.reverseBytes(16));out.writeShort(Short.reverseBytes((short)1));out.writeShort(Short.reverseBytes((short)channels));out.writeInt(Integer.reverseBytes(rate));out.writeInt(Integer.reverseBytes(rate*channels*2));out.writeShort(Short.reverseBytes((short)(channels*2)));out.writeShort(Short.reverseBytes((short)16));out.writeBytes("data");out.writeInt(Integer.reverseBytes(count*channels*2));for(int i=0;i<count*channels;i++)out.writeShort(Short.reverseBytes(value));}return f;}
    public static void main(String[] args)throws Exception{
        File root=new File(args[0]);root.mkdirs();
        ToolCalls stream=new ToolCalls();stream.accept(new JSONArray().put(delta(0,"call_a","image_","{\"bundleId\":\"im")));stream.accept(new JSONArray().put(delta(0,null,"generate","age_model\",\"input\":{\"prompt\":\"hi\"}}")));JSONArray calls=stream.finish(0);
        ok(calls.length()==1,"one fragmented call");ok(calls.getJSONObject(0).getString("operation").equals("image.generate"),"whitelisted operation");ok(ToolCalls.request(calls.getJSONObject(0),true).getString("bundleId").equals("image_model"),"exact arguments survive fragments");
        reject(()->stream.finish(8),"step budget cannot reset");
        ToolCalls duplicate=new ToolCalls();duplicate.accept(new JSONArray().put(delta(0,"same","task_status","{\"id\":\"job_a\"}")).put(delta(1,"same","asset_select","{\"id\":\"artifact_a\"}")));reject(()->duplicate.finish(0),"duplicate IDs cannot execute");
        ToolCalls unknown=new ToolCalls();unknown.accept(new JSONArray().put(delta(0,"unknown","download_model","{}")));reject(()->unknown.finish(0),"download is not a tool");
        for(String name:new String[]{"shell","delete_file","remote_infer","network_fetch","eval"}){ToolCalls t=new ToolCalls();t.accept(new JSONArray().put(delta(0,"bad",name,"{}")));reject(()->t.finish(0),"no implicit privilege "+name);}
        ToolCalls broken=new ToolCalls();broken.accept(new JSONArray().put(delta(0,"bad_json","image_generate","{broken")));reject(()->broken.finish(0),"malformed JSON cannot execute");
        ToolCalls oversized=new ToolCalls();reject(()->oversized.accept(new JSONArray().put(delta(8,"over","image_generate","{}"))),"ninth streamed call blocked");
        JSONObject privilege=DataFiles.copy(calls.getJSONObject(0));privilege.getJSONObject("parsed").put("allowUnmeasured",true);reject(()->ToolCalls.request(privilege,false),"model cannot grant consent");
        JSONObject path=DataFiles.copy(calls.getJSONObject(0));path.getJSONObject("parsed").getJSONObject("input").put("path","C:/private");reject(()->ToolCalls.request(path,true),"raw paths rejected");
        for(String bad:new String[]{"{x:1}","{'x':1}","{\"x\":1,}","{\"x\":1} trailing","{\"x\":1,\"x\":2}","{\"x\":NaN}"})reject(()->StrictJson.object(bad),"strict JSON "+bad);
        ok(ToolCalls.canRepair(0)&&!ToolCalls.canRepair(1)&&!ToolCalls.canRepair(-1),"one-repair budget enforced");
        ok(new ToolCalls().finish(0).length()==0,"plain text alone executes nothing");ok(ToolCalls.definitions().length()==8,"complete controlled tools");
        File storePath=new File(root,"chains");WorkflowStore store=new WorkflowStore(storePath);JSONObject original=draft(),chain=store.create(original,"session_a","chain_a");Jobs jobs=new Jobs();
        ok(chain.getJSONArray("steps").length()==2,"two-step chain");ok(chain.getJSONArray("steps").getJSONObject(0).getJSONObject("request").getBoolean("allowUnmeasured"),"explicit user consent preserved");
        WorkflowRunner.advance(chain,jobs);store.update(chain);ok(jobs.admitted==1,"only first dependency-ready job admitted");WorkflowRunner.advance(chain,jobs);ok(jobs.admitted==1,"polling cannot duplicate generation");
        jobs.finish("job_1","succeeded");WorkflowRunner.advance(chain,jobs);WorkflowRunner.advance(chain,jobs);store.update(chain);ok(jobs.admitted==2,"dependent task admitted after real success");ok(jobs.get("job_2").getJSONObject("request").getJSONObject("input").getJSONArray("artifacts").getJSONObject(0).getString("artifactId").equals("artifact_job_1"),"actual artifact identity bound");
        jobs.finish("job_2","failed");WorkflowRunner.advance(chain,jobs);store.update(chain);ok(chain.getString("state").equals("blocked"),"failure is not success");store.retry("chain_a",1);chain=store.get("chain_a");WorkflowRunner.advance(chain,jobs);store.update(chain);ok(jobs.admitted==3,"explicit retry creates one fresh attempt");ok(chain.getJSONArray("steps").getJSONObject(0).getString("jobId").equals("job_1"),"successful predecessor never recalculated");
        jobs.finish("job_3","succeeded");WorkflowRunner.advance(chain,jobs);store.update(chain);ok(chain.getString("state").equals("succeeded"),"chain completes truthfully");
        WorkflowStore reopened=new WorkflowStore(storePath);ok(reopened.get("chain_a").getString("state").equals("succeeded"),"process restart retains chain");ok(reopened.referencesArtifact("artifact_job_1"),"saved chain protects sources");
        JSONObject before=store.get("chain_a");ok(store.create(original,"session_a","chain_a").getString("id").equals("chain_a"),"chain idempotency");JSONObject conflict=draft();conflict.put("template","different");reject(()->store.create(conflict,"session_a","chain_a"),"same key cannot change request");
        JSONObject cyclic=draft();cyclic.getJSONArray("steps").getJSONObject(0).put("dependsOn",new JSONArray().put(1));reject(()->store.create(cyclic,"s","cycle"),"forward/cyclic dependency rejected");
        JSONObject badBinding=draft();badBinding.getJSONArray("steps").getJSONObject(1).getJSONArray("bindings").getJSONObject(0).put("step",1);reject(()->store.create(badBinding,"s","bad_binding"),"undeclared input dependency rejected");
        JSONObject many=draft();for(int i=0;i<7;i++)many.getJSONArray("steps").put(new JSONObject().put("request",req("image.generate","image_model")));reject(()->store.create(many,"s","too_many"),"ninth plan step rejected");
        JSONObject crashChain=store.create(draft(),"s","crash_chain");Jobs crashJobs=new Jobs();crashJobs.crash=true;try{WorkflowRunner.advance(crashChain,crashJobs);}catch(AssertionError death){}crashChain=new WorkflowStore(storePath).get("crash_chain");WorkflowRunner.advance(crashChain,crashJobs);ok(crashJobs.admitted==1,"queue-commit/process-death window cannot duplicate");ok(crashChain.getJSONArray("steps").getJSONObject(0).getString("jobId").equals("job_1"),"recovery attaches original task");
        JSONObject cancelChain=store.create(draft(),"s","cancel_chain");Jobs cancelJobs=new Jobs();WorkflowRunner.advance(cancelChain,cancelJobs);cancelChain.put("cancelRequested",true);WorkflowRunner.advance(cancelChain,cancelJobs);WorkflowRunner.advance(cancelChain,cancelJobs);ok(cancelJobs.admitted==1&&cancelJobs.cancelled==1,"parent cancellation reaches active job and prevents next admission");ok(cancelChain.getString("state").equals("cancelled"),"cancel completion acknowledged");
        JSONObject failChain=store.create(draft(),"s","fail_chain");Jobs failJobs=new Jobs();WorkflowRunner.advance(failChain,failJobs);failJobs.finish("job_1","failed");WorkflowRunner.advance(failChain,failJobs);WorkflowRunner.advance(failChain,failJobs);ok(failJobs.admitted==1,"failed dependency blocks child");ok(failChain.getJSONArray("steps").getJSONObject(1).getString("state").equals("blocked"),"dependency error visible");
        JSONObject composition=new JSONObject().put("type","media.compose").put("bundleId",CompositionSpec.ID).put("input",new JSONObject().put("artifacts",new JSONArray().put(new JSONObject().put("role","visual").put("artifactId","picture_a")).put(new JSONObject().put("role","voice").put("artifactId","speech_a"))));
        JSONObject edit=CompositionSpec.validate(composition);ok(edit.getJSONObject("parameters").getDouble("durationSeconds")>5,"explicit real edit duration");ok(!edit.has("allowUnmeasured"),"editing needs no trained model consent");
        for(double invalid:new double[]{0,5,61,Double.POSITIVE_INFINITY}){reject(()->{JSONObject bad=DataFiles.copy(composition);bad.put("parameters",new JSONObject().put("durationSeconds",invalid));CompositionSpec.validate(bad);},"duration contract "+invalid);}
        JSONObject wrong=DataFiles.copy(composition);wrong.getJSONObject("input").put("url","https://remote/example");reject(()->CompositionSpec.validate(wrong),"no external media fetch");
        File a=wav(root,"positive.wav",1,22050,(short)20000,22050),negative=wav(root,"negative.wav",2,44100,(short)-20000,44100);
        try(PcmMixer mix=new PcmMixer()){mix.add(a,1);ok(Math.abs(mix.sample(0)-20000)<2,"real PCM decode");ok(Math.abs(mix.sample(22050)-20000)<2,"linear rate conversion");ok(mix.sample(44101)==0,"short audio silence-padded rather than looped");mix.add(negative,1);ok(Math.abs(mix.sample(100))<3,"two-track signed mixing and stereo downmix");}
        try(PcmMixer mix=new PcmMixer()){mix.add(a,2);ok(mix.sample(0)==32767,"positive saturation");reject(()->mix.add(a,-1),"negative gain rejected");}
        File invalid=new File(root,"corrupt.wav");try(FileOutputStream out=new FileOutputStream(invalid)){out.write(new byte[50]);}try(PcmMixer mix=new PcmMixer()){reject(()->mix.add(invalid,1),"corrupt WAV rejected");}
        for(String[] error:new String[][]{{"empty_structure","empty_structure"},{"SHA256 mismatch","integrity_mismatch"},{"OOM","out_of_memory"},{"unsupported backend","unsupported_operation"},{"损坏 MP4","invalid_media"}})ok(TaskFailures.describe(error[0]).getString("code").equals(error[1]),"actionable category "+error[1]);
        System.out.println(new JSONObject().put("passed",true).put("assertions",checks).put("complete_trained_model_runs",0).put("physical_device_tests",0).put("scope","production workflow/tool/PCM contracts; not Android codec or model output").toString());
    }
}
