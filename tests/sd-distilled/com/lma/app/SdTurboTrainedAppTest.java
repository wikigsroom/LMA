package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Complete trained SD-Turbo user-selection/import and unchanged production binding; Windows HOST only. */
public final class SdTurboTrainedAppTest {
    static int passed,networkCalls;
    static void check(boolean ok,String why){if(!ok)throw new AssertionError(why);passed++;}
    interface Checked{void run()throws Exception;}
    static String failure(Checked run)throws Exception{try{run.run();}catch(Exception e){passed++;return e.getMessage();}throw new AssertionError("Expected failure");}
    static JSONObject read(File f)throws Exception{return SdTrainedAppTest.read(f);}
    static String persisted(JSONObject v)throws Exception{return SdTrainedAppTest.persisted(v);}
    static JSONObject request(ModelBundle b,JSONObject p,String prompt)throws Exception{
        return new JSONObject().put("type","image.generate").put("bundleId",b.id).put("parameters",DataFiles.copy(p))
            .put("input",new JSONObject().put("prompt",prompt)).put("adapters",new JSONArray());
    }
    public static void main(String[] args)throws Exception{
        File root=new File(args[0]);root.mkdirs();JSONObject reference=read(new File(args[1]));
        RecipeCatalogue recipes=new RecipeCatalogue(read(new File(args[2])));
        JSONObject selected=reference.getJSONArray("components").getJSONObject(0);
        ModelBundle base=recipes.compose(reference.getString("recipeId"),new JSONObject().put("model",selected));
        check(base.id.startsWith("hfb_")&&!base.json().getBoolean("catalogue"),"HF selection owns an independent model identity");
        check(!base.json().getJSONObject("uncensored").getBoolean("declared")&&base.json().getJSONObject("evidence").getInt("physicalDeviceTests")==0,"No unverified content or phone labels");
        check(base.pipeline.equals("sd21_turbo")&&base.architecture.equals("sd21")&&base.components.size()==2,"One complete checkpoint plus external vocabulary");
        check(base.tags().getString("engine").equals("engine:sd_cpp")&&base.tasks.equals(Collections.singleton("image")),"Image task and foundation tags remain independent");
        LmaApp app=new LmaApp(new File(root,"files"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        app.bundles.declare(base);check(!app.bundles.plan(base.id).getBoolean("installed"),"Metadata selection installs nothing");
        JSONArray catalogue=read(new File(args[3])).getJSONArray("bundles");ModelBundle peer=null;
        for(int i=0;i<catalogue.length();i++)if(catalogue.getJSONObject(i).getString("id").equals("sd15_ss_q4_0_r031b5f5"))peer=new ModelBundle(catalogue.getJSONObject(i));
        check(peer!=null,"Existing peer metadata remains available");app.bundles.declare(peer);
        app.bundles.saveSettings(peer.id,new JSONObject().put("steps",19).put("cfg",6.5));
        JSONObject peerBefore=app.bundles.settings(peer.id);
        List<String> errors=Collections.synchronizedList(new ArrayList<>());long importedBytes=0;
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(c,offset,observer)->{networkCalls++;throw new IOException("Offline selected local import");},
            new BundleTransfers.Listener(){public void changed(){}public void installed(String id){}public void failed(String id,String e){errors.add(e);}})){
            check(!transfers.busy()&&networkCalls==0,"Construction starts no transfer");
            Map<String,BundleTransfers.Input> files=new HashMap<>();
            for(ModelBundle.Component c:base.components){
                File source=new File(c.role.equals("model")?args[4]:args[5]);
                check(source.isFile()&&source.length()==c.bytes,"Explicit whole component exists");
                check(c.sha256.equals(reference.getJSONArray("components").getJSONObject(c.role.equals("model")?0:1).getString("sha256")),"Fixed full component identity preserved");
                files.put(c.role,()->new FileInputStream(source));importedBytes+=c.bytes;
            }
            transfers.importFiles(base.id,files);check(transfers.awaitIdle(3600,TimeUnit.SECONDS),"Full selected import reaches terminal state");
            check(errors.isEmpty()&&networkCalls==0&&app.bundles.plan(base.id).getBoolean("installed"),"Actual full-file SHA import completes offline");
        }
        check(importedBytes==2024269995L&&new File(app.getFilesDir(),"bundles/objects").listFiles().length==2,"Exactly two complete user-owned objects");
        JSONObject bounded=app.bundles.saveSettings(base.id,new JSONObject().put("steps",999).put("cfg",999).put("threads",999).put("width",99999)).getJSONObject("values");
        check(bounded.getInt("steps")==4&&bounded.getDouble("cfg")==1&&bounded.getInt("threads")==64&&bounded.getInt("width")==2048,"Editable distilled model values clamp to declared limits");
        app.bundles.saveSettings(base.id,new JSONObject().put("width",512).put("height",512).put("threads",6).put("seed",42).put("steps",4));
        check(persisted(peerBefore).equals(persisted(app.bundles.settings(peer.id))),"Peer model settings remain independent");
        SdEngine engine=new SdEngine(app,new File(args[6]),new JSONObject().put("engine","sd_cpp"));
        JSONObject saved=app.bundles.settings(base.id).getJSONObject("values"),before=DataFiles.copy(saved);
        JSONObject negative=request(base,saved,"negative prompt rejection");negative.getJSONObject("input").put("negativePrompt","blur");
        failure(()->engine.prepare(base,negative));check(SdTrainedAppTest.children==0,"Negative prompt rejects before native launch");
        JSONObject exaggerated=request(base,new JSONObject(saved.toString()).put("steps",999).put("cfg",7).put("sampler","euler").put("scheduler","karras"),"clamp");
        JSONObject plan=engine.prepare(base,exaggerated).getJSONObject("diffusionPlan"),effective=plan.getJSONObject("parameters");
        check(effective.getInt("steps")==4&&effective.getDouble("cfg")==1&&effective.getString("sampler").equals("euler_a")&&effective.getString("scheduler").equals("discrete"),"Production request freezes the signed SD-Turbo sampling policy");
        check(plan.getJSONArray("adjustments").length()==4&&persisted(saved).equals(persisted(before)),"Request adjustments do not overwrite saved settings");
        JSONArray runs=new JSONArray();Map<String,String> hashes=new HashMap<>();
        String prompt="A small red fox sitting beside a blue ceramic teapot on a wooden table, clean composition";
        for(String name:Arrays.asList("one-step","four-step","empty-prompt","cancel-stage-entry","recovery")){
            int steps=name.equals("one-step")?1:4;boolean invalid=name.equals("empty-prompt"),cancel=name.equals("cancel-stage-entry");
            JSONObject source=request(base,new JSONObject(saved.toString()).put("steps",steps),invalid?"":prompt),prepared=engine.prepare(base,source);
            int prior=SdTrainedAppTest.children;long start=System.nanoTime();System.err.println("Start actual SD-Turbo Java/native: "+name);
            try(BundleStore.Selection leases=app.bundles.acquireAll(ModelSelection.ids(prepared))){
                SdTrainedAppTest.Context context=new SdTrainedAppTest.Context(leases,prepared,new File(root,name),cancel);
                prepared.getJSONObject("parameters").put("threads",64);source.getJSONObject("input").put("prompt","changed caller");
                check(context.request().getJSONObject("parameters").getInt("threads")==6,"Execution owns an immutable per-model snapshot");
                failure(()->app.bundles.remove(base.id,false));
                JSONObject run=new JSONObject().put("name",name).put("steps",steps);
                if(invalid||cancel){
                    String error=failure(()->engine.generate(context));check(context.child!=null&&!context.child.isAlive(),"Error/cancellation releases actual native child");
                    check(context.folder.listFiles((d,n)->n.endsWith(".png")).length==0,"No partial output survives error/cancellation");
                    if(invalid)check(error.equals("Invalid prompt or output"),"Actual native error returns through production bridge");
                    else check(context.cancelled,"Java cancellation occurs at explicit generating-stage entry");
                    run.put("cancelled",cancel).put("expected_error",error);
                }else{
                    File image=engine.generate(context);String hash=SdTrainedAppTest.sha(image);hashes.put(name,hash);
                    check(image.length()>10000&&context.child!=null&&!context.child.isAlive(),"Actual trained PNG exits cleanly");
                    run.put("output",image.getPath()).put("bytes",image.length()).put("sha256",hash);
                }
                check(SdTrainedAppTest.children==prior+1&&app.nativeProcess==null,"Each task releases exactly one real child");
                check(context.folder.listFiles((d,n)->n.endsWith(".json")).length==0,"Private request removed on every terminal path");
                JSONObject actual=context.execution.getJSONObject("effectiveParameters");
                check(actual.getInt("threads")==6&&actual.getInt("steps")==steps&&actual.getDouble("cfg")==1&&actual.getString("sampler").equals("euler_a")&&actual.getString("scheduler").equals("discrete"),"Recorded execution retains effective distilled settings");
                runs.put(run.put("execution",context.execution).put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9));
            }
            System.err.println("Finished actual SD-Turbo Java/native: "+name);
        }
        check(!hashes.get("one-step").equals(hashes.get("four-step"))&&hashes.get("four-step").equals(hashes.get("recovery")),"Step selection changes actual output and recovery reproduces four-step bytes");
        BundleStore restored=new BundleStore(new File(app.getFilesDir(),"bundles"));
        check(restored.plan(base.id).getBoolean("installed")&&!restored.plan(peer.id).getBoolean("installed"),"Restart retains only explicitly imported model");
        check(persisted(restored.settings(base.id)).equals(persisted(app.bundles.settings(base.id)))&&persisted(restored.settings(peer.id)).equals(persisted(peerBefore)),"Restart preserves both independent profiles");
        check(SdTrainedAppTest.children==5&&networkCalls==0,"Five real children, zero import transport calls");
        JSONObject result=new JSONObject().put("passed",passed).put("binding_checks",SdTrainedAppTest.passed).put("actual_host_children",SdTrainedAppTest.children).put("network_calls",networkCalls)
            .put("imported_objects",2).put("imported_unique_bytes",importedBytes).put("runs",runs).put("launches",SdTrainedAppTest.launches)
            .put("production_hf_selection",base.json()).put("host_java_production_binding",true).put("android_application_executed",false).put("android_saf_tested",false)
            .put("android_background_tested",false).put("image_quality_accepted",false).put("java_cancel_at_sampler_step_tested",false)
            .put("host_metadata_port","windows_atomic_replace_functional_only").put("host_metadata_fsync",false).put("metadata_power_loss_durability_tested",false).put("android_atomicfile_tested",false);
        Files.write(new File(root,"java-results.json").toPath(),result.toString(2).getBytes("UTF-8"));System.out.println(result);
    }
}
