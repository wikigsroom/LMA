package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Production import/settings/workspace/worker pipeline; explicit Windows filesystem port only. */
public final class MnnEditTrainedAppTest {
    static int passed, children, networkCalls;
    static final JSONArray launches = new JSONArray();
    static final JSONArray runtimeConfigs = new JSONArray();
    static final String PROMPT = MnnSpec.EDIT_PROMPT;
    static ArtifactStore artifacts;
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); passed++; }
    interface Checked { void run() throws Exception; }
    static String failure(Checked action) throws Exception {
        try { action.run(); } catch (Exception expected) { passed++; return expected.getMessage(); }
        throw new AssertionError("Expected local rejection");
    }
    static final class Context implements LocalEngine.Context {
        final BundleStore.Lease lease; final JSONObject frozen; final File folder; final boolean cancel;
        final InputSelection.Selection inputs; final String jobId = "job_"+UUID.randomUUID().toString().replace("-", "");
        final JSONArray progress = new JSONArray(); JSONObject execution; Process child; boolean cancelled;
        Context(BundleStore.Lease lease, JSONObject request, File folder, boolean cancel, InputSelection.Selection inputs) {
            this.inputs=inputs; this.lease=lease; this.frozen=DataFiles.copy(request); this.folder=folder; this.cancel=cancel; folder.mkdirs();
        }
        public BundleStore.Lease model() { return lease; }
        public JSONObject request() { return DataFiles.copy(frozen); }
        public File input(String role) throws IOException { return inputs.file(role); }
        public File output(String suffix) throws IOException { return artifacts.staging(jobId,suffix); }
        public void check() throws IOException { if(cancelled)throw new IOException("Requested cancellation after a completed real sampling step"); }
        public void process(Process value) { child=value; }
        public void progress(String stage, Double fraction) throws Exception {
            progress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));
            if(cancel && stage.equals("sampling") && fraction!=null && fraction>0 && fraction<1 && child!=null && child.isAlive()) {
                cancelled=true; child.destroy();
            }
        }
        public void execution(JSONObject details) { execution=DataFiles.copy(details); }
    }
    static JSONObject request(ModelBundle bundle, JSONObject parameters) throws Exception {
        return new JSONObject().put("bundleId",bundle.id).put("type","image.generate")
            .put("input",new JSONObject().put("prompt",PROMPT).put("negativePrompt",""))
            .put("parameters",DataFiles.copy(parameters));
    }
    public static void main(String[] args) throws Exception {
        File root=new File(args[0]), originals=new File(args[1]), binary=new File(args[4]); root.mkdirs();
        JSONObject lock=new JSONObject(new String(Files.readAllBytes(Paths.get(args[2])),"UTF-8"));
        RecipeCatalogue recipes=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[3])),"UTF-8")));
        JSONObject bindings=new JSONObject(); Map<String,File> sources=new HashMap<>(); long total=0;
        JSONArray components=lock.getJSONArray("components");
        for(int i=0;i<components.length();i++) {
            JSONObject component=DataFiles.copy(components.getJSONObject(i)); String role=component.getString("role");
            File source=new File(originals,component.getString("path")); sources.put(role,source);
            check(source.isFile() && source.length()==component.getLong("bytes") && DataFiles.sha256(source).equals(component.getString("sha256")),"Whole selected trained component verified");
            component.put("format",role.equals("llm_config")?"json":role.equals("tokenizer")?"text":role.endsWith("_data")?"mnn_data":"mnn");
            bindings.put(role,component); total+=source.length();
        }
        ModelBundle bundle=recipes.compose("sana_edit_mnn_cpu_v1",bindings); MnnSpec.validate(bundle,"image.generate");
        check(bundle.components.size()==15 && bundle.tasks.contains("image"),"All fifteen real user components compose a peer image model");
        LmaApp app=new LmaApp(new File(root,"app")); app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles")); app.bundles.declare(bundle);
        check(!app.bundles.plan(bundle.id).getBoolean("installed") && networkCalls==0,"Declaration installs or downloads no assets");
        final List<String> errors=Collections.synchronizedList(new ArrayList<>());
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(component,offset,observer)->{
            networkCalls++;throw new IOException("No network is permitted during selected local import or inference");
        },new BundleTransfers.Listener(){
            public void changed() {} public void installed(String id) {} public void failed(String id,String message) { errors.add(message); }
        })) {
            Map<String,BundleTransfers.Input> selected=new LinkedHashMap<>();
            for(ModelBundle.Component component:bundle.components)selected.put(component.role,()->new FileInputStream(sources.get(component.role)));
            check(app.bundles.plan(bundle.id).getLong("totalBytes")==total,"Full download/import plan discloses every required byte");
            transfers.importFiles(bundle.id,selected);
            check(transfers.awaitIdle(180,TimeUnit.SECONDS) && errors.isEmpty(),"Production local import completes full SHA verification");
        }
        check(app.bundles.plan(bundle.id).getBoolean("installed") && networkCalls==0,"All trained components install without network");
        JSONObject clamped=app.bundles.saveSettings(bundle.id,new JSONObject().put("width",99999).put("height",511)
            .put("steps",999).put("threads",999).put("maxInputTokens",99999)).getJSONObject("values");
        check(clamped.getInt("width")==512 && clamped.getInt("height")==512 && clamped.getInt("steps")==50 && clamped.getInt("threads")==32 && clamped.getInt("maxInputTokens")==1792,"Per-model editable parameters clamp to declared bounds");
        JSONObject settings=app.bundles.saveSettings(bundle.id,new JSONObject().put("width",512).put("height",512).put("steps",10)
            .put("threads",4).put("maxInputTokens",512).put("seed",42)).getJSONObject("values");
        app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        check(app.bundles.plan(bundle.id).getBoolean("installed") && DataFiles.canonical(app.bundles.settings(bundle.id).getJSONObject("values")).equals(DataFiles.canonical(settings)),"Restart preserves real installed components and independent model settings");
        MnnEngine engine=new MnnEngine(app,binary,new JSONObject().put("engine","mnn_diffusion"),builder->{
            try {
                JSONObject command=new JSONObject(new String(Files.readAllBytes(Paths.get(builder.command().get(1))),"UTF-8"));launches.put(command);
                File workspace=new File(command.getString("workspace"));
                JSONObject config=new JSONObject(new String(Files.readAllBytes(new File(workspace,"llm/config.json").toPath()),"UTF-8"));
                JSONObject metadata=new JSONObject(new String(Files.readAllBytes(new File(workspace,"llm/llm_config.json").toPath()),"UTF-8"));
                check(config.getString("backend_type").equals("cpu") && config.getInt("thread_num")==4 && !config.getBoolean("use_mmap"),"Actual worker receives controlled CPU configuration");
                check(metadata.length()==5 && !metadata.has("base_dir") && !metadata.has("chat_template"),"Only approved actual model metadata enters the runtime");
                runtimeConfigs.put(new JSONObject().put("config",config).put("metadata",metadata));
            }
            catch(Exception error) { throw new IOException(error); }
            children++; return builder.start();
        });
        artifacts=new ArtifactStore(new File(root,"artifacts"), file->{
            java.awt.image.BufferedImage image=javax.imageio.ImageIO.read(file);
            if(image==null)throw new IOException("Cannot inspect actual PNG");
            return new JSONObject().put("mime","image/png").put("width",image.getWidth()).put("height",image.getHeight());
        });
        JSONObject source;
        try(InputStream in=new FileInputStream(args[5])) { source=artifacts.importStream(in,"astronaut.png",()->{}); }
        check(source.getString("sha256").equals(DataFiles.sha256(new File(args[5]))),"Actual user photo is imported with whole-file integrity");
        failure(()->InputSelection.prepare(artifacts,engine.inputs(bundle,"image.generate"),request(bundle,settings)));
        JSONObject invalid=request(bundle,settings);invalid.getJSONObject("input").put("prompt","unsupported instruction");
        failure(()->engine.prepare(bundle,invalid));
        JSONArray runs=new JSONArray();
        for(String name:new String[]{"a","cancel-sampling","recovery-a"}) {
            boolean cancel=name.equals("cancel-sampling"); JSONObject wanted=request(bundle,settings);
            wanted.getJSONObject("input").put("artifacts",new JSONArray().put(new JSONObject().put("role","source_image").put("artifactId",source.getString("id"))));
            wanted=InputSelection.prepare(artifacts,engine.inputs(bundle,"image.generate"),wanted);
            JSONObject planned=engine.prepare(bundle,wanted); File folder=new File(root,name); long start=System.nanoTime();
            try(BundleStore.Lease lease=app.bundles.acquire(bundle.id); InputSelection.Selection selected=InputSelection.acquire(artifacts,engine.inputs(bundle,"image.generate"),planned,()->{})) {
                failure(()->artifacts.remove(source.getString("id")));
                check(lease.integrity().length()==15,"Real lease protects every selected component");
                Context context=new Context(lease,planned,folder,cancel,selected);
                wanted.getJSONObject("input").put("prompt","Caller mutation must not enter the frozen job");
                check(context.request().getJSONObject("input").getString("prompt").equals(PROMPT) && context.input("source_image").isFile(),"Frozen prompt and leased source survive caller mutation");
                planned.getJSONObject("parameters").put("steps",1);
                check(context.request().getJSONObject("diffusionPlan").getJSONObject("parameters").getInt("steps")==10,"Submitted job owns immutable sampling parameters");
                JSONObject run=new JSONObject().put("name",name);
                System.out.println("Execute actual production Java Sana pipeline: "+name); System.out.flush();
                if(cancel) {
                    String error=failure(()->engine.generate(context));
                    check(context.cancelled && context.child!=null && !context.child.isAlive() && error.contains("Requested cancellation"),"Cancellation follows an actual completed sampling step and terminates its child");
                    check(folder.listFiles((dir,file)->file.endsWith(".png")).length==0,"Cancelled actual computation publishes no PNG");
                    run.put("cancelled",true);
                } else {
                    File output=engine.generate(context);
                    check(output.isFile() && output.length()>33,"Production Java returns an actual trained image");
                    check(context.progress.length()>2 && context.execution.getJSONObject("effectiveParameters").getInt("steps")==10,"Real progress and frozen execution parameters reach Java");
                    JSONObject published=artifacts.commit(context.jobId,output,context.request(),()->{});
                    File result=artifacts.file(published.getString("id"));
                    check(published.getJSONObject("provenance").getJSONArray("inputReceipts").getJSONObject(0).getString("sha256").equals(source.getString("sha256")),"Published actual result preserves immutable source provenance");
                    run.put("artifact",published).put("output",result.getPath()).put("sha256",DataFiles.sha256(result)).put("bytes",result.length());
                }
                check(app.nativeProcess==null && (context.child==null || !context.child.isAlive()),"Actual child exits and releases native process ownership");
                check(new File(app.getFilesDir(),"engine-work").list().length==0,"Actual child exit removes private hardlinks and sanitized runtime files");
                run.put("seconds",(System.nanoTime()-start)/1e9).put("progress",context.progress).put("execution",context.execution);runs.put(run);
            }
        }
        try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
            JSONObject bad=engine.prepare(bundle,request(bundle,settings));bad.getJSONObject("diffusionPlan").getJSONObject("parameters").put("steps",2);
            int before=children;failure(()->engine.generate(new Context(lease,bad,new File(root,"tampered"),false,null)));
            check(children==before,"Changed frozen plan is rejected before launching a worker");
            check(DataFiles.sha256(lease.file("llm_config")).equals(bundle.component("llm_config").sha256),"Runtime sanitization never modifies installed model metadata");
        }
        for(ModelBundle.Component component:bundle.components)check(DataFiles.sha256(sources.get(component.role)).equals(component.sha256),"Original user-selected trained asset remains unchanged");
        check(children==3 && networkCalls==0,"Exactly three real native children; zero asset requests or external inference");
        artifacts=new ArtifactStore(new File(root,"artifacts"),file->{throw new IOException("Restart must read committed records without re-decoding");});
        for(int i=0;i<runs.length();i++)if(runs.getJSONObject(i).has("artifact"))check(artifacts.file(runs.getJSONObject(i).getJSONObject("artifact").getString("id")).isFile(),"Restart preserves completed actual image results");
        artifacts.remove(source.getString("id"));check(artifacts.snapshot().length()==2,"Unleased user input can be removed while generated results remain managed");
        JSONObject report=new JSONObject().put("passed",passed).put("actual_host_children",children).put("network_calls",networkCalls)
            .put("imported_objects",15).put("imported_bytes",total).put("bundle",bundle.json()).put("runs",runs).put("launches",launches).put("runtime_configs",runtimeConfigs)
            .put("production_java_native_host_executed",true).put("physical_android",false).put("image_quality_accepted",false).put("complete_release_accepted",false);
        Files.write(new File(root,"java-results.json").toPath(),report.toString(2).getBytes("UTF-8"));
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",children));
    }
}
