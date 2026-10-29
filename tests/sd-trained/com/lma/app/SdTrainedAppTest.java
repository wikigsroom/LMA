package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Full user-owned weights with unchanged production Java/native code; HOST filesystem only. */
public final class SdTrainedAppTest {
    static int passed,children,networkCalls;
    static final JSONArray launches=new JSONArray();
    static void check(boolean ok,String why){if(!ok)throw new AssertionError(why);passed++;}
    interface Checked{void run()throws Exception;}
    static String failure(Checked run)throws Exception{try{run.run();}catch(Exception e){passed++;return e.getMessage();}throw new AssertionError("Expected failure");}
    static String sha(File file)throws Exception{
        MessageDigest d=MessageDigest.getInstance("SHA-256");
        try(InputStream in=new FileInputStream(file)){byte[] b=new byte[1024*1024];int n;while((n=in.read(b))!=-1)d.update(b,0,n);}
        return Protocol.hex(d.digest());
    }
    static JSONObject read(File path)throws Exception{return new JSONObject(new String(Files.readAllBytes(path.toPath()),"UTF-8"));}
    static String persisted(JSONObject value)throws Exception{return DataFiles.canonical(DataFiles.copy(value));}
    static final class Context implements LocalEngine.Context{
        final BundleStore.Selection leases;final JSONObject request;final File folder;final boolean cancel;
        final JSONArray progress=new JSONArray();boolean cancelled;Process child;JSONObject execution;
        Context(BundleStore.Selection leases,JSONObject request,File folder,boolean cancel){this.leases=leases;this.request=DataFiles.copy(request);this.folder=folder;this.cancel=cancel;folder.mkdirs();}
        public BundleStore.Lease model(){return leases.models.get(0);}
        public List<BundleStore.Lease> adapters(){return leases.models.subList(1,leases.models.size());}
        public JSONObject request(){return DataFiles.copy(request);}
        public File output(String suffix){return new File(folder,UUID.randomUUID()+"."+suffix);}
        public void check()throws IOException{if(cancelled)throw new IOException("Requested cancellation at native generating-stage entry");}
        public void progress(String stage,Double fraction)throws Exception{
            progress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));
            // This Java control tests stage-entry cancellation, not a claimed sampler step.
            // The separate direct native test cancels after actual sampler step 1.
            if(cancel&&stage.equals("generating")&&fraction==null&&child!=null&&child.isAlive()){cancelled=true;child.destroy();}
        }
        public void process(Process process)throws Exception{
            child=process;children++;
            File[] files=folder.listFiles((dir,name)->name.endsWith(".json"));SdTrainedAppTest.check(files!=null&&files.length==1,"One private request belongs to this actual child");
            JSONObject command=read(files[0]),components=command.getJSONObject("components");
            for(ModelBundle.Component c:model().bundle.components)SdTrainedAppTest.check(Files.isSameFile(Paths.get(components.getString(c.role)),model().file(c.role).toPath()),"Base components use leased immutable objects");
            JSONArray loras=command.getJSONArray("loras");SdTrainedAppTest.check(loras.length()==adapters().size(),"Every ordered adapter reaches native command");
            for(int i=0;i<loras.length();i++){
                SdTrainedAppTest.check(Files.isSameFile(Paths.get(loras.getJSONObject(i).getString("path")),adapters().get(i).file("lora").toPath()),"Each adapter uses its own leased object");
                SdTrainedAppTest.check(loras.getJSONObject(i).getDouble("scale")==request.getJSONArray("adapters").getJSONObject(i).getDouble("scale"),"Adapter scale snapshot reaches native code");
            }
            launches.put(command);
        }
        public void execution(JSONObject details){execution=DataFiles.copy(details);}
    }
    static JSONObject request(ModelBundle base,JSONObject parameters,ModelBundle lcm,ModelBundle style,String prompt)throws Exception{
        return new JSONObject().put("type","image.generate").put("bundleId",base.id).put("input",new JSONObject().put("prompt",prompt))
            .put("parameters",DataFiles.copy(parameters)).put("adapters",new JSONArray()
                .put(new JSONObject().put("bundleId",lcm.id).put("scale",1.))
                .put(new JSONObject().put("bundleId",style.id).put("scale",base.architecture.equals("sd15")?.9:1.2)));
    }
    public static void main(String[] args)throws Exception{
        File root=new File(args[0]),assetRoot=new File(args[1]),manifestRoot=new File(args[2]),binary=new File(args[4]);root.mkdirs();
        JSONObject lock=read(new File(args[6]));
        Map<String,File> sources=new HashMap<>();
        for(int i=0;i<lock.getJSONArray("assets").length();i++){
            JSONObject item=lock.getJSONArray("assets").getJSONObject(i);sources.put(item.getString("sha256"),new File(assetRoot,item.getString("sha256")+"/"+item.getString("path")));
        }
        Map<String,ModelBundle> models=new LinkedHashMap<>();JSONArray catalogue=read(new File(args[3])).getJSONArray("bundles");
        for(int i=0;i<catalogue.length();i++){JSONObject b=catalogue.getJSONObject(i);if(b.getString("id").equals("sd15_ss_q4_0_r031b5f5"))models.put("sd15_base",new ModelBundle(b));}
        RecipeCatalogue recipes=new RecipeCatalogue(read(new File(args[7])));JSONArray composed=new JSONArray();
        for(String key:Arrays.asList("sdxl_base_q4_0","sd15_style_pixelart","sdxl_style_pixelart","sd15_lcm_lora","sdxl_lcm_lora")){
            JSONObject reference=read(new File(manifestRoot,key+".json")),selected=reference.getJSONArray("components").getJSONObject(0);
            String role=selected.getString("role");
            // Follow the production HF selector's composition path; JSON references are not a UI import feature.
            ModelBundle b=recipes.compose(reference.getString("recipeId"),new JSONObject().put(role,DataFiles.copy(selected)));
            check(b.id.startsWith("hfb_")&&!b.id.equals(reference.getString("id")),"Production HF composition assigns its own immutable selection identity");
            check(!b.json().getBoolean("catalogue")&&!b.json().getJSONObject("uncensored").getBoolean("declared"),"Selecting a real file promotes neither catalogue trust nor uncensored status");
            check(b.json().getJSONObject("evidence").getInt("physicalDeviceTests")==0,"HF composition keeps phone evidence unset");
            for(int i=0;i<reference.getJSONArray("components").length();i++){
                JSONObject c=reference.getJSONArray("components").getJSONObject(i);ModelBundle.Component actual=b.component(c.getString("role"));
                check(actual.bytes==c.getLong("bytes")&&actual.sha256.equals(c.getString("sha256"))&&actual.url.equals(c.getString("url")),"Actual selected component and fixed vocabulary keep complete pinned identities");
                check(actual.importPath.equals(actual.role+"/"+actual.path),"Production selection exposes role-separated import paths for same-named assets");
            }
            composed.put(new JSONObject().put("asset",key).put("bundle_id",b.id).put("recipe_id",b.recipeId).put("components",b.json().getJSONArray("components")));
            models.put(key,b);
        }
        check(models.size()==6,"Both bases and all four independent adapters declared");
        for(ModelBundle.Component c:models.get("sd15_base").components)sources.put(c.sha256,new File(args[5],new File(c.path).getName()));
        LmaApp app=new LmaApp(new File(root,"files"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        List<String> errors=Collections.synchronizedList(new ArrayList<>());Map<String,Long> objects=new HashMap<>();
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(c,offset,observer)->{networkCalls++;throw new IOException("No network in selected local import");},
            new BundleTransfers.Listener(){public void changed(){}public void installed(String id){}public void failed(String id,String error){errors.add(error);}})){
            check(networkCalls==0&&!transfers.busy(),"Construction starts no download");
            for(ModelBundle b:models.values()){
                app.bundles.declare(b);check(!app.bundles.plan(b.id).getBoolean("installed"),"Declaring metadata installs no model");
                check(b.tasks.equals(Collections.singleton("image"))&&b.tags().getString("engine").equals("engine:sd_cpp"),"Image and engine tags stay independent of install state");
                Map<String,BundleTransfers.Input> files=new HashMap<>();
                for(ModelBundle.Component c:b.components){File file=sources.get(c.sha256);check(file!=null&&file.isFile()&&file.length()==c.bytes,"Explicitly selected full component has pinned size");files.put(c.role,()->new FileInputStream(file));objects.put(c.sha256,c.bytes);}
                transfers.importFiles(b.id,files);check(transfers.awaitIdle(3600,TimeUnit.SECONDS),"Explicit full import reaches terminal state within the bounded host I/O deadline");
                check(errors.isEmpty()&&app.bundles.plan(b.id).getBoolean("installed")&&networkCalls==0,"Production import verifies complete weights with zero network");
                System.err.println("Full production import completed: "+b.id);
            }
        }
        long bytes=0;for(long size:objects.values())bytes+=size;
        check(objects.size()==7&&bytes==4891569203L,"Exactly seven unique full objects including shared CLIP merges");
        check(new File(app.getFilesDir(),"bundles/objects").listFiles().length==7,"Shared vocabulary is not duplicated");
        ModelBundle sd15=models.get("sd15_base"),sdxl=models.get("sdxl_base_q4_0");
        JSONObject bounded=app.bundles.saveSettings(sdxl.id,new JSONObject().put("threads",999).put("steps",9999).put("width",99999)).getJSONObject("values");
        check(bounded.getInt("threads")==64&&bounded.getInt("steps")==200&&bounded.getInt("width")==2048,"Editable SDXL values clamp to its actual declared application guards");
        for(String family:Arrays.asList("sd15","sdxl")){
            ModelBundle base=family.equals("sd15")?sd15:sdxl;
            app.bundles.saveSettings(base.id,new JSONObject().put("threads",6).put("steps",8).put("width",512).put("height",512).put("seed",42).put("cfg",7.));
            ModelBundle style=models.get(family+"_style_pixelart"),lcm=models.get(family+"_lcm_lora");
            check(app.bundles.saveSettings(style.id,new JSONObject().put("scale",999)).getJSONObject("values").getDouble("scale")==4,"Independent style scale clamps to its own maximum");
            app.bundles.saveSettings(style.id,new JSONObject().put("scale",family.equals("sd15")?.9:1.2));
            check(app.bundles.saveSettings(lcm.id,new JSONObject().put("scale",999)).getJSONObject("values").getDouble("scale")==2,"Independent LCM scale clamps to its own maximum");
            app.bundles.saveSettings(lcm.id,new JSONObject().put("scale",1.));
        }
        SdEngine engine=new SdEngine(app,binary,new JSONObject().put("engine","sd_cpp"));
        for(String family:Arrays.asList("sd15","sdxl")){
            ModelBundle base=family.equals("sd15")?sd15:sdxl,style=models.get(family+"_style_pixelart"),lcm=models.get(family+"_lcm_lora");
            ModelBundle wrong=models.get((family.equals("sd15")?"sdxl":"sd15")+"_style_pixelart");
            JSONObject saved=app.bundles.settings(base.id).getJSONObject("values"),before=DataFiles.copy(saved);
            failure(()->engine.prepare(base,request(base,saved,lcm,wrong,"incompatible adapter")));check(children==0,"Both incompatible base families reject before any native process");
            JSONObject negative=request(base,saved,lcm,style,"negative conditioning");negative.getJSONObject("input").put("negativePrompt","blur");
            failure(()->engine.prepare(base,negative));
            JSONObject zero=request(base,saved,lcm,style,"disabled LCM source");zero.getJSONArray("adapters").getJSONObject(0).put("scale",0.);
            failure(()->engine.prepare(base,zero));
            JSONObject planned=engine.prepare(base,request(base,saved,lcm,style,"immutable plan")),p=planned.getJSONObject("diffusionPlan").getJSONObject("parameters");
            check(p.getString("sampler").equals("lcm")&&p.getString("scheduler").equals("lcm")&&p.getDouble("cfg")==1&&p.getInt("steps")==8,"Explicit LCM adapter freezes matching native sampling");
            check(planned.getJSONObject("diffusionPlan").getJSONArray("adjustments").length()>=3,"Actual sampling adjustments are retained");
            check(persisted(app.bundles.settings(base.id).getJSONObject("values")).equals(persisted(before)),"LCM plan does not overwrite saved base settings");
        }
        JSONArray runs=new JSONArray();Map<String,String> hashes=new HashMap<>();String prompt="A small red fox sitting beside a blue ceramic teapot on a wooden table, pixel art, PixArFK, clean composition";
        for(String family:Arrays.asList("sd15","sdxl")){
            ModelBundle base=family.equals("sd15")?sd15:sdxl,style=models.get(family+"_style_pixelart"),lcm=models.get(family+"_lcm_lora");
            JSONObject saved=app.bundles.settings(base.id).getJSONObject("values");
            for(String suffix:Arrays.asList("initial","empty-prompt","cancel-stage-entry","recovery")){
                boolean cancel=suffix.equals("cancel-stage-entry"),invalid=suffix.equals("empty-prompt");String name=family+"-"+suffix;
                JSONObject request=request(base,new JSONObject(saved.toString()).put("steps",4),lcm,style,invalid?"":prompt);
                JSONObject prepared=engine.prepare(base,request);int prior=children;long start=System.nanoTime();
                System.err.println("Start actual production Java/native case: "+name);
                try(BundleStore.Selection leases=app.bundles.acquireAll(ModelSelection.ids(prepared))){
                    Context context=new Context(leases,prepared,new File(root,name),cancel);
                    prepared.getJSONObject("parameters").put("threads",64);request.getJSONObject("input").put("prompt","mutated caller");
                    check(context.request().getJSONObject("parameters").getInt("threads")==6,"Queued request owns immutable per-model settings");
                    failure(()->app.bundles.remove(base.id,false));failure(()->app.bundles.remove(style.id,false));failure(()->app.bundles.remove(lcm.id,false));
                    JSONObject run=new JSONObject().put("name",name).put("family",family).put("bundle_id",base.id);
                    if(invalid||cancel){
                        String message=failure(()->engine.generate(context));check(context.child!=null&&!context.child.isAlive(),"Failed or cancelled actual native child exits");
                        check(context.folder.listFiles((d,n)->n.endsWith(".png")).length==0,"No partial PNG accepted after failure/cancellation");
                        if(invalid)check(message.equals("Invalid prompt or output"),"Actual native prompt validation reaches production Java");
                        else check(context.cancelled,"Java cancellation uses explicitly reported native stage entry");
                        run.put("cancelled",cancel).put("expected_error",message);
                    }else{
                        File output=engine.generate(context);check(output.length()>10000&&context.child!=null&&!context.child.isAlive(),"Real complete weights produce PNG through unchanged Java bridge");
                        String hash=sha(output);hashes.put(name,hash);run.put("output",output.getPath()).put("bytes",output.length()).put("sha256",hash);
                    }
                    check(children==prior+1&&app.nativeProcess==null,"Every accepted task owns and releases exactly one real child");
                    check(context.folder.listFiles((d,n)->n.endsWith(".json")).length==0,"Private native request removed on every terminal path");
                    JSONObject actual=context.execution.getJSONObject("effectiveParameters");
                    check(actual.getInt("threads")==6&&actual.getInt("steps")==4&&actual.getDouble("cfg")==1&&actual.getString("sampler").equals("lcm")&&actual.getString("scheduler").equals("lcm"),"Execution records effective snapshot rather than saved standard defaults");
                    runs.put(run.put("execution",context.execution).put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9));
                    System.err.println("Finished actual production Java/native case: "+name);
                }
            }
            check(hashes.get(family+"-initial").equals(hashes.get(family+"-recovery")),"Recovery after error/cancellation reproduces the original PNG bytes");
        }
        check(children==8&&networkCalls==0,"Eight actual native children use zero network calls");
        BundleStore restored=new BundleStore(new File(app.getFilesDir(),"bundles"));
        for(ModelBundle b:models.values())check(restored.plan(b.id).getBoolean("installed")&&persisted(restored.settings(b.id)).equals(persisted(app.bundles.settings(b.id))),"Restart retains every full model and independent settings without transfers");
        JSONObject result=new JSONObject().put("passed",passed).put("actual_host_children",children).put("network_calls",networkCalls).put("imported_objects",objects.size()).put("imported_unique_bytes",bytes)
            .put("runs",runs).put("launches",launches).put("host_java_production_binding",true).put("production_hf_recipes_composed",composed).put("android_application_executed",false).put("android_saf_tested",false)
            .put("android_background_tested",false).put("image_quality_accepted",false).put("java_cancel_at_sampler_step_tested",false)
            .put("host_metadata_port","windows_atomic_replace_functional_only").put("host_metadata_fsync",false)
            .put("metadata_power_loss_durability_tested",false).put("android_atomicfile_tested",false);
        Files.write(new File(root,"java-results.json").toPath(),result.toString(2).getBytes("UTF-8"));System.out.println(result);
    }
}
