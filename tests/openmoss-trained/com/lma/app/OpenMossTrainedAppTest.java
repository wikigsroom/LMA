package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Real complete weights and production Java/native bridge; filesystem port is HOST only. */
public final class OpenMossTrainedAppTest {
    static int passed,children,networkCalls;
    static final JSONArray launches=new JSONArray();
    static void check(boolean ok,String why){if(!ok)throw new AssertionError(why);passed++;}
    interface Checked{void run()throws Exception;}
    static String failure(Checked run)throws Exception{try{run.run();}catch(IOException e){passed++;return e.getMessage();}throw new AssertionError("Expected failure");}
    static String sha(File file)throws Exception{
        MessageDigest d=MessageDigest.getInstance("SHA-256");
        try(InputStream in=new FileInputStream(file)){byte[] b=new byte[1024*1024];int n;while((n=in.read(b))!=-1)d.update(b,0,n);}
        return Protocol.hex(d.digest());
    }
    static final class Context implements LocalEngine.Context{
        final BundleStore.Lease lease;final JSONObject request;final File folder,reference;final boolean cancel;
        final JSONArray progress=new JSONArray();boolean cancelled;Process child;JSONObject execution;
        Context(BundleStore.Lease lease,JSONObject request,File folder,File reference,boolean cancel){
            this.lease=lease;this.request=DataFiles.copy(request);this.folder=folder;this.reference=reference;this.cancel=cancel;folder.mkdirs();
        }
        public BundleStore.Lease model(){return lease;}
        public JSONObject request(){return DataFiles.copy(request);}
        public File input(String role)throws Exception{OpenMossTrainedAppTest.check(role.equals("reference_audio")&&reference!=null,"Only explicitly selected reference is read");return reference;}
        public File output(String suffix){return new File(folder,UUID.randomUUID()+"."+suffix);}
        public void check()throws IOException{if(cancelled)throw new IOException("Requested cancellation after actual sampled step 16");}
        public void progress(String stage,Double fraction)throws Exception{progress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));if(cancel&&stage.equals("generating_speech")&&fraction!=null&&fraction>=16.0/375&&fraction<1&&child!=null&&child.isAlive()){cancelled=true;child.destroy();}}
        public void process(Process process)throws Exception{
            child=process;children++;
            File[] files=folder.listFiles((dir,name)->name.endsWith(".json"));OpenMossTrainedAppTest.check(files!=null&&files.length==1,"One private request belongs to the actual child");
            JSONObject command=new JSONObject(new String(Files.readAllBytes(files[0].toPath()),"UTF-8"));
            File work=new File(command.getString("workspace"));
            OpenMossTrainedAppTest.check(Files.isSameFile(new File(work,"models/model.gguf").toPath(),lease.file("backbone").toPath()),"Talker execution filename hardlinks the leased trained object");
            OpenMossTrainedAppTest.check(Files.isSameFile(new File(work,"models/model.extras.gguf").toPath(),lease.file("extras").toPath()),"Codec execution filename hardlinks the leased trained object");
            if(command.has("referenceAudios"))OpenMossTrainedAppTest.check(command.getJSONArray("referenceAudios").length()==1&&Files.isSameFile(Paths.get(command.getJSONArray("referenceAudios").getString(0)),reference.toPath()),"Selected reference is hardlinked without copying");
            launches.put(command);
        }
        public void execution(JSONObject details)throws Exception{
            execution=DataFiles.copy(details);
        }
    }
    static JSONObject request(String id,JSONObject parameters,String prompt)throws Exception{
        return new JSONObject().put("type","speech.synthesize").put("bundleId",id).put("input",new JSONObject().put("prompt",prompt)).put("parameters",DataFiles.copy(parameters));
    }
    public static void main(String[] args)throws Exception{
        File root=new File(args[0]),assets=new File(args[1]),binary=new File(args[3]),reference=new File(args[4]);root.mkdirs();
        boolean adoptExisting=args.length>6&&args[6].equals("existing_local");
        boolean skipReference=args.length>7&&args[7].equals("skip_reference");
        JSONArray originalJobs=new JSONObject(new String(Files.readAllBytes(Paths.get(args[5])),"UTF-8")).getJSONArray("jobs");
        JSONObject directEnglish=null,directReference=null;
        for(int i=0;i<originalJobs.length();i++){JSONObject j=originalJobs.getJSONObject(i);if(j.getString("name").equals("english"))directEnglish=j;if(j.getString("name").equals("reference"))directReference=j;}
        check(directEnglish!=null&&directReference!=null,"Original real synthesis cases exist, including their separate completion gates");
        JSONArray list=new JSONObject(new String(Files.readAllBytes(Paths.get(args[2])),"UTF-8")).getJSONArray("bundles");
        ModelBundle selected=null,other=null;
        for(int i=0;i<list.length();i++){ModelBundle b=new ModelBundle(list.getJSONObject(i));if(b.id.equals("moss_tts_v15_q8_bf16_cpu_catalogue_v1"))selected=b;else if(b.id.equals("kokoro82_en_v1_rf7b96bb"))other=b;}
        final ModelBundle bundle=selected;check(bundle!=null&&other!=null,"Frozen MOSS and an independent model exist");OpenMossSpec.validate(bundle,"speech.synthesize");OpenMossSpec.reference(bundle,reference);
        LmaApp app=new LmaApp(new File(root,"files"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        List<String> errors=Collections.synchronizedList(new ArrayList<>());long importedBytes=0;
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(c,offset,observer)->{networkCalls++;throw new IOException("No network in explicit local import");},
            new BundleTransfers.Listener(){public void changed(){}public void installed(String id){}public void failed(String id,String error){errors.add(error);}})){
            check(networkCalls==0&&!transfers.busy(),"Construction starts no transfer");app.bundles.declare(bundle);app.bundles.declare(other);
            check(!app.bundles.plan(bundle.id).getBoolean("installed"),"Declaration starts no model download or installation");
            check(bundle.tasks.equals(Collections.singleton("audio"))&&bundle.tags().getString("engine").equals("engine:openmoss_native"),"Task and dependency tags are independent");
            Map<String,BundleTransfers.Input> files=new HashMap<>();Map<String,File> existing=new LinkedHashMap<>();
            for(ModelBundle.Component c:bundle.components){File file=new File(new File(assets,c.sha256),c.path);check(file.isFile()&&file.length()==c.bytes,"User-selected component has pinned size");files.put(c.role,()->new FileInputStream(file));existing.put(c.role,file);importedBytes+=c.bytes;}
            check(importedBytes==13430589376L&&app.bundles.plan(bundle.id).getLong("totalBytes")==importedBytes,"Complete download plan includes both full trained GGUFs");
            if(adoptExisting){
                app.bundles.adoptLocal(bundle,existing,new JSONObject(),()->{});
                for(ModelBundle.Component c:bundle.components){check(Files.isSameFile(existing.get(c.role).toPath(),app.bundles.object(c.objectId).toPath()),"Explicit existing-local adoption preserves original full files without copying");}
                check(!transfers.busy(),"Adoption starts no background download or stream import");
            }else{
                transfers.importFiles(bundle.id,files);check(transfers.awaitIdle(900,TimeUnit.SECONDS),"Explicit full import reaches terminal state");
            }
            check(errors.isEmpty()&&app.bundles.plan(bundle.id).getBoolean("installed")&&networkCalls==0,"Both complete assets pass selected production registration without network");
        }
        check(new File(app.getFilesDir(),"bundles/objects").listFiles().length==2,"Exactly two immutable content objects imported");
        JSONObject clamped=app.bundles.saveSettings(bundle.id,new JSONObject().put("threads",999).put("maxInputTokens",99999).put("maxNewTokens",99999).put("audioTopK",9999).put("textTemperature",99)).getJSONObject("values");
        check(clamped.getInt("threads")==32&&clamped.getInt("maxInputTokens")==2048&&clamped.getInt("maxNewTokens")==1500&&clamped.getInt("audioTopK")==1024&&clamped.getDouble("textTemperature")==3,"Editable numeric settings clamp to this recipe's limits");
        JSONObject defaults=OpenMossSpec.parameters(bundle,new JSONObject()).getJSONObject("values").put("threads",4).put("seed",1234).put("language","English");
        JSONObject parameters=app.bundles.saveSettings(bundle.id,defaults).getJSONObject("values");
        app.bundles.saveSettings(other.id,new JSONObject().put("threads",2).put("speed",1.1));
        check(app.bundles.settings(bundle.id).getJSONObject("values").toString().equals(parameters.toString()),"Other model settings do not change MOSS parameters");
        check(!app.bundles.plan(other.id).getBoolean("installed"),"Saving unrelated model settings downloads no weights");
        OpenMossEngine engine=new OpenMossEngine(app,binary,new JSONObject().put("engine","openmoss_native"));
        JSONObject prepared=engine.prepare(bundle,request(bundle.id,new JSONObject(parameters.toString()).put("threads",999),"你好。"));
        check(prepared.getJSONObject("parameters").getInt("threads")==32&&prepared.getJSONArray("adjustments").length()>0,"Production prepare records clamping");
        JSONArray runs=new JSONArray();
        String[] cases=skipReference?new String[]{"initial-a","cancel-after-step16","token-budget","recovery-a"}:new String[]{"initial-a","reference-a","cancel-after-step16","token-budget","recovery-a"};
        for(String name:cases){
            boolean cancel=name.equals("cancel-after-step16"),limited=name.equals("token-budget"),ref=name.equals("reference-a");
            File folder=new File(root,name);long start=System.nanoTime();JSONObject job=request(bundle.id,parameters,"Hello world.");
            if(ref)job.getJSONObject("input").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_audio").put("artifactId","explicit_trained_kokoro_reference")));
            if(limited)job.getJSONObject("parameters").put("maxInputTokens",1);
            try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)){
                check(lease.integrity().length()==2,"Lease binds both full component receipts");Context context=new Context(lease,job,folder,ref?reference:null,cancel);
                job.getJSONObject("parameters").put("threads",32);job.getJSONObject("input").put("prompt","Mutated caller text");
                check(context.request().getJSONObject("parameters").getInt("threads")==4,"Queued request keeps immutable model parameter snapshot");
                JSONObject run=new JSONObject().put("name",name).put("bundle_id",bundle.id).put("pipeline",bundle.pipeline);
                if(cancel||limited){
                    String message=failure(()->engine.generate(context));check(context.child!=null&&!context.child.isAlive(),"Cancelled or failed actual child exited");
                    check(folder.listFiles((d,n)->n.endsWith(".wav")).length==0,"No partial output accepted on cancellation/error");
                    if(cancel)check(context.cancelled,"Cancellation follows actual sampled step16");else check(message.equals("Formatted prompt and generation exceed the selected context budget"),"Real BPE token-budget error reaches Java");
                    run.put("cancelled",cancel).put("expected_error",message);
                }else{
                    File output=engine.generate(context);check(output.length()>44&&context.child!=null&&!context.child.isAlive(),"Real trained synthesis exits with a WAV");
                    JSONObject execution=context.execution;JSONObject expected=ref?directReference:directEnglish;JSONObject expectedExecution=expected.getJSONObject("execution");
                    check(execution.getInt("sampleRate")==24000&&execution.getInt("audioSamples")>0&&execution.getString("stopReason").equals(expectedExecution.getString("stopReason"))&&execution.getBoolean("truncated")==expectedExecution.getBoolean("truncated"),"Actual completion or truncation is faithfully preserved by Java, without changing the separate natural-EOS gate");
                    check(execution.getInt("referenceSpeakers")== (ref?1:0),"Actual optional reference mode is recorded");
                    check(execution.getJSONObject("effectiveParameters").getInt("threads")==4,"Private snapshot reaches actual inference");
                    check(execution.getJSONObject("effectiveParameters").getLong("seed")==1234,"Actual selected seed is recorded");
                    run.put("output",output.getPath()).put("bytes",output.length()).put("sha256",sha(output));
                    check(sha(output).equals(expected.getJSONObject("audio").getString("sha256")),"Unmodified production Java/native speech matches the exact direct request WAV");
                }
                check(app.nativeProcess==null,"Production bridge releases process ownership");
                check(folder.listFiles((d,n)->n.endsWith(".json")).length==0,"Private request removed on every terminal path");
                check(new File(app.getFilesDir(),"engine-work").list().length==0,"Execution hardlinks removed after child exit");
                runs.put(run.put("execution",context.execution).put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9));
            }
        }
        check(children==(skipReference?4:5)&&networkCalls==0,"Every explicitly scoped real native job uses zero network calls");BundleStore restored=new BundleStore(new File(app.getFilesDir(),"bundles"));
        check(restored.plan(bundle.id).getBoolean("installed")&&restored.settings(bundle.id).getJSONObject("values").toString().equals(parameters.toString()),"Restart retains model and independent settings");
        JSONObject result=new JSONObject().put("passed",passed).put("actual_host_children",children).put("network_calls",networkCalls).put("registered_objects",2).put("selected_asset_bytes",importedBytes)
            .put("asset_registration_mode",adoptExisting?"explicit_existing_local_full_sha_adoption":"explicit_full_stream_import").put("full_stream_import_tested",!adoptExisting).put("copied_import_bytes",adoptExisting?0:importedBytes)
            .put("runs",runs).put("launches",launches).put("host_java_production_binding",true).put("reference_sha256",sha(reference)).put("reference_case_executed",!skipReference)
            .put("android_application_executed",false).put("android_saf_tested",false).put("android_background_tested",false).put("speech_quality_accepted",false);
        Files.write(new File(root,"java-results.json").toPath(),result.toString(2).getBytes("UTF-8"));System.out.println(result);
    }
}
