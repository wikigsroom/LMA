package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.json.*;

/** Production preparation/association/generation on Windows; Android ports are explicit. */
public final class LcmTrainedAppTest {
    static int checks, preparationChildren;
    interface Action { void run() throws Exception; }
    static void check(boolean ok,String message){checks++;if(!ok)throw new AssertionError(message);}
    static void rejects(Action action,String message)throws Exception{try{action.run();}catch(Exception expected){checks++;return;}throw new AssertionError(message);}
    static JSONObject read(File file)throws Exception{return SdTrainedAppTest.read(file);}
    static JSONObject select(JSONArray values,String key,String id)throws Exception{for(int i=0;i<values.length();i++)if(values.getJSONObject(i).getString(key).equals(id))return values.getJSONObject(i);throw new IOException("Missing selected identity");}
    static JSONObject request(ModelBundle model,JSONObject parameters,String prompt)throws Exception{return new JSONObject().put("type","image.generate").put("bundleId",model.id).put("input",new JSONObject().put("prompt",prompt).put("negativePrompt","")).put("parameters",DataFiles.copy(parameters)).put("adapters",new JSONArray());}
    public static void main(String[] args)throws Exception{
        File root=new File(args[0]);root.mkdirs();JSONArray catalogue=read(new File(args[1])).getJSONArray("bundles");
        ModelBundle source=new ModelBundle(select(catalogue,"id","lcm_dreamshaper_source_ra85df6a"));
        ModelBundle runtime=new ModelBundle(select(catalogue,"id","lcm_dreamshaper_guidance85_runtime_v1"));
        PreparationPlan preparation=new PreparationPlan(select(read(new File(args[2])).getJSONArray("plans"),"id","lcm_dreamshaper_guidance85_v1"));
        AssemblyPlan assembly=new AssemblyPlan(select(read(new File(args[3])).getJSONArray("plans"),"id","lcm_dreamshaper_guidance85_association_v1"),preparation,runtime);
        check(preparation.matches(source),"Catalogue plan binds the complete selected source");
        check(!runtime.json().getJSONObject("evidence").getBoolean("pixelEquivalencePassed"),"Known failed pixel gate remains visible");
        check(!runtime.json().getJSONObject("evidence").getBoolean("imageQualityAccepted"),"App plumbing does not promote image quality");
        File original=new File(args[4]),base=new File(args[5]),merges=new File(args[6]),preparer=new File(args[7]),worker=new File(args[8]);
        long sourceTime=original.lastModified(),baseTime=base.lastModified();
        LmaApp app=new LmaApp(new File(root,"files"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        JobStore jobs=new JobStore(new File(root,"jobs"));
        app.bundles.declare(source);app.bundles.declare(runtime);
        check(!app.bundles.plan(source.id).getBoolean("installed")&&!app.bundles.plan(runtime.id).getBoolean("installed"),"Declarations transfer no bytes");
        app.bundles.adoptLocal(source,Collections.singletonMap("checkpoint",original),new JSONObject(),()->{});
        check(app.bundles.plan(source.id).getBoolean("installed"),"Explicit whole-source local adoption verifies SHA");
        JSONObject submitted=jobs.submit(new JSONObject().put("type","model.prepare").put("bundleId",source.id).put("preparationId",preparation.id).put("planFingerprint",preparation.fingerprint),"lcm-prepare"),active=jobs.claimNext();
        check(submitted.getString("id").equals(active.getString("id")),"Preparation uses the shared persistent queue");
        final String preparationJob=active.getString("id"),preparationToken=active.getString("token");JSONArray preparationProgress=new JSONArray();JSONObject prepared,associated;
        try(PreparedAssets assets=new PreparedAssets(new File(root,"prepared"))){
            try(BundleStore.Lease lease=app.bundles.acquire(source.id);PreparedAssets.Session session=assets.begin(preparationJob)){
                rejects(()->app.bundles.remove(source.id,false,jobs),"Queued/leased source cannot be removed");
                NativePreparation.run(preparation,lease.file("checkpoint"),Collections.singletonMap("lcm_condition_prepare",preparer),session,new NativePreparation.Context(){
                    public void check()throws IOException{jobs.check(preparationJob,preparationToken);}
                    public void progress(String stage,Double fraction)throws Exception{check();jobs.progress(preparationJob,preparationToken,stage,fraction);preparationProgress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));}
                    public Process start(ProcessBuilder builder)throws Exception{
                        JSONObject command=read(new File(builder.command().get(1)));
                        LcmTrainedAppTest.check(command.getLong("max_output_bytes")==5696,"Native output budget equals the declared stage output, not disk reserve");
                        LcmTrainedAppTest.check(Files.isSameFile(Paths.get(command.getString("checkpoint")),lease.file("checkpoint").toPath()),"Converter reads only the private leased source");
                        preparationChildren++;return builder.start();
                    }
                    public File graphs(PreparationPlan.Stage stage)throws Exception{throw new IOException("LCM has no external graph dependency");}
                });
                check(session.directory.listFiles((d,n)->n.startsWith("request-")).length==0,"Private converter request is removed");
                prepared=session.commit(preparation,source.id,()->jobs.check(preparationJob,preparationToken));
                jobs.finishPreparation(preparationJob,preparationToken,prepared,"");
                check(jobs.get(preparationJob).getString("state").equals("succeeded"),"Verified prepared component commits atomically");
            }
            check(assets.snapshot(source.id).length()==1&&!app.bundles.plan(runtime.id).getBoolean("installed"),"Preparation starts neither association nor dependency transfer");
            try(PreparedAssets.Lease lease=assets.acquire(prepared.getString("id"),()->{})){LcmCondition.verify(runtime,lease.file("condition_bias"));}
            JSONObject associationRequest=new JSONObject().put("type","model.assemble").put("bundleId",runtime.id).put("preparedAssetsId",prepared.getString("id")).put("assemblyId",assembly.id).put("assemblyFingerprint",assembly.fingerprint);
            JSONObject queued=jobs.submit(TaskInput.validate(associationRequest).put("assemblySourceFingerprint",TaskInput.fingerprint(prepared)),"lcm-associate"),claimed=jobs.claimNext();
            check(queued.getString("id").equals(claimed.getString("id")),"Association is a separate explicit queued action");
            String assemblyJob=claimed.getString("id"),assemblyToken=claimed.getString("token");
            associated=PreparedModelAssembly.run(assembly,assets,app.bundles,claimed.getJSONObject("request"),assemblyJob,new PreparedModelAssembly.Context(){public void check()throws IOException{jobs.check(assemblyJob,assemblyToken);}public void progress(String stage)throws Exception{check();jobs.progress(assemblyJob,assemblyToken,stage,null);}});
            jobs.finishAssembly(assemblyJob,assemblyToken,associated,"");
            check(!associated.getBoolean("installed")&&associated.getLong("remainingBytes")==2135199851L,"Association leaves complete base and vocabulary dependencies missing");
            check(app.bundles.record(runtime.id).getJSONObject("transfer").getString("state").equals("paused"),"Missing dependencies are paused without background download");
            rejects(()->app.bundles.acquire(runtime.id),"Partial runtime cannot generate");
            Map<String,File> dependencies=new LinkedHashMap<>();dependencies.put("model",base);dependencies.put("clip_merges",merges);
            app.bundles.adoptAvailableLocal(runtime,dependencies,new JSONObject(),()->{});
            check(app.bundles.plan(runtime.id).getBoolean("installed"),"User-selected dependencies complete the runtime only after full verification");
            try(PreparedAssets.Lease from=assets.acquire(prepared.getString("id"),()->{});BundleStore.Lease to=app.bundles.acquire(runtime.id)){
                check(Files.isSameFile(from.file("condition_bias").toPath(),to.file("condition_bias").toPath()),"Association retains independent hardlink owners without duplicate learned bytes");
            }
            JSONObject clamped=app.bundles.saveSettings(runtime.id,new JSONObject().put("steps",999).put("cfg",999).put("width",99999)).getJSONObject("values");
            check(clamped.getInt("steps")==8&&clamped.getDouble("cfg")==1&&clamped.getInt("width")==2048,"Editable settings clamp to this model's own limits");
            app.bundles.saveSettings(runtime.id,new JSONObject().put("steps",4).put("width",512).put("height",512).put("seed",42).put("threads",6));
            SdEngine engine=new SdEngine(app,worker,new JSONObject().put("engine","sd_cpp"));JSONObject saved=app.bundles.settings(runtime.id).getJSONObject("values");
            JSONObject bad=request(runtime,saved,"invalid negative");bad.getJSONObject("input").put("negativePrompt","blur");rejects(()->engine.prepare(runtime,bad),"LCM negative conditioning fails before native launch");
            ModelBundle lora=new ModelBundle(select(catalogue,"id","sd15_ss_q4_0_r031b5f5").put("id","fixture_lora").put("pipeline","lora").put("architecture","sd15").put("components",new JSONArray().put(new JSONObject().put("role","lora").put("path","lora.gguf").put("format","gguf").put("bytes",1).put("sha256",String.join("",Collections.nCopies(64,"a"))))));
            JSONObject withLora=request(runtime,saved,"unsupported adapter").put("adapters",new JSONArray().put(new JSONObject().put("bundleId",lora.id).put("scale",1.)));
            rejects(()->SdSpec.prepare(runtime,Collections.singletonList(lora),withLora),"Fixed condition never silently accepts an unverified time-embedding LoRA");
            JSONArray runs=new JSONArray();Map<String,String> images=new HashMap<>();String prompt="A small red fox sitting beside a blue ceramic teapot on a wooden table, clean composition";
            for(String name:Arrays.asList("native-prepared","empty-prompt","cancel-stage-entry","recovery")){
                boolean cancel=name.equals("cancel-stage-entry"),invalid=name.equals("empty-prompt");JSONObject preparedRequest=engine.prepare(runtime,request(runtime,saved,invalid?"":prompt));
                long start=System.nanoTime();System.err.println("Start LCM App pipeline generation: "+name);JSONObject run=new JSONObject().put("name",name);
                try(BundleStore.Selection lease=app.bundles.acquireAll(ModelSelection.ids(preparedRequest))){
                    SdTrainedAppTest.Context context=new SdTrainedAppTest.Context(lease,preparedRequest,new File(root,name),cancel);preparedRequest.getJSONObject("parameters").put("steps",8);
                    check(context.request().getJSONObject("parameters").getInt("steps")==4,"Queued generation retains an immutable model-settings snapshot");
                    if(cancel||invalid){rejects(()->engine.generate(context),"Expected native error or Java cancellation");check(context.child!=null&&!context.child.isAlive(),"Failed task releases the actual native child");check(context.folder.listFiles((d,n)->n.endsWith(".png")).length==0,"Failed task retains no partial image");run.put("expected_failure",true).put("cancelled",cancel);}
                    else{File image=engine.generate(context);String hash=SdTrainedAppTest.sha(image);images.put(name,hash);check(image.length()>10000&&context.child!=null&&!context.child.isAlive(),"Actual trained PNG is complete and child exits");run.put("output",image.getPath()).put("bytes",image.length()).put("sha256",hash);}
                    check(context.folder.listFiles((d,n)->n.endsWith(".json")).length==0&&app.nativeProcess==null,"Terminal generation removes private commands and process ownership");
                    run.put("execution",context.execution).put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9);
                }
                runs.put(run);System.err.println("Finished LCM App pipeline generation: "+name);
            }
            check(images.get("native-prepared").equals(images.get("recovery")),"Explicit retry after cancellation reproduces trained output");
            assets.remove(prepared.getString("id"),jobs);check(app.bundles.plan(runtime.id).getBoolean("installed"),"Deleting independent prepared data preserves the runtime model");
            BundleStore restored=new BundleStore(new File(app.getFilesDir(),"bundles"));check(restored.plan(source.id).getBoolean("installed")&&restored.plan(runtime.id).getBoolean("installed"),"Restart retains selected source and runtime independently");
            check(DataFiles.canonical(restored.settings(runtime.id)).equals(DataFiles.canonical(app.bundles.settings(runtime.id))),"Restart retains model-scoped editable settings");
            check(preparationChildren==1&&SdTrainedAppTest.children==4,"One actual full-source converter and four actual generation children");
            check(original.lastModified()==sourceTime&&base.lastModified()==baseTime,"Preparation and generation preserve original source/base timestamps");
            JSONObject result=new JSONObject().put("passed",checks).put("binding_checks",SdTrainedAppTest.passed).put("preparation_children",preparationChildren).put("generation_children",SdTrainedAppTest.children).put("network_calls",0)
                .put("prepared",prepared).put("association",associated).put("preparation_progress",preparationProgress).put("runs",runs).put("launches",SdTrainedAppTest.launches)
                .put("production_java_native_host_executed",true).put("android_application_executed",false).put("android_saf_tested",false).put("image_quality_accepted",false).put("pixel_equivalence_passed",false)
                .put("host_metadata_port","windows_atomic_replace_functional_only").put("android_atomicfile_tested",false);
            Files.write(new File(root,"java-results.json").toPath(),result.toString(2).getBytes("UTF-8"));System.out.println(result);
        }
    }
}
