package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Actual production Java -> native trained worker, using a host filesystem Application port. */
public final class NanoTrainedAppTest {
    static int passed, children, networkCalls;
    static final JSONArray launches = new JSONArray();
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); passed++; }
    interface Checked { void run() throws Exception; }
    static void rejects(Checked run, String reason) throws Exception { try { run.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(reason); }
    static String sha(File path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = new FileInputStream(path)) { byte[] bytes = new byte[1024*1024]; int n; while ((n=stream.read(bytes))!=-1) digest.update(bytes,0,n); }
        return Protocol.hex(digest.digest());
    }
    static final class Context implements LocalEngine.Context {
        final BundleStore.Lease lease; final JSONObject request; final File folder; final boolean cancel;
        final JSONArray progress = new JSONArray(); volatile boolean cancelled; Process child; JSONObject execution;
        Context(BundleStore.Lease lease, JSONObject request, File folder, boolean cancel) { this.lease=lease;this.request=DataFiles.copy(request);this.folder=folder;this.cancel=cancel;folder.mkdirs(); }
        public BundleStore.Lease model() { return lease; }
        public JSONObject request() { return DataFiles.copy(request); }
        public File output(String suffix) { return new File(folder,UUID.randomUUID()+"."+suffix); }
        public void check() throws IOException { if(cancelled) throw new IOException("Requested cancellation after actual synthesis progress"); }
        public void progress(String stage,Double fraction) throws Exception {
            progress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));
            if(cancel && stage.equals("synthesizing") && fraction!=null && fraction>0) cancelled=true;
        }
        public void process(Process process) { child=process; }
        public void execution(JSONObject details) { execution=DataFiles.copy(details); }
    }
    static JSONObject request(String id,JSONObject parameters,String prompt) throws Exception {
        return new JSONObject().put("type","speech.synthesize").put("bundleId",id).put("input",new JSONObject().put("prompt",prompt)).put("parameters",DataFiles.copy(parameters));
    }
    static JSONArray workspaces(File files) { File[] paths=new File(files,"engine-work").listFiles();return new JSONArray(paths==null?Collections.emptyList():Arrays.asList(paths)); }
    public static void main(String[] args) throws Exception {
        File root=new File(args[0]),assets=new File(args[1]),binary=new File(args[3]);root.mkdirs();
        JSONObject manifest=new JSONObject(new String(Files.readAllBytes(Paths.get(args[2])),"UTF-8"));
        ModelBundle bundle=new ModelBundle(manifest);MossNanoSpec.validate(bundle,"speech.synthesize");
        check(bundle.components.size()==11 && bundle.tasks.equals(Collections.singleton("audio")),"Exact user recipe has all eleven audio components");
        check(!manifest.getBoolean("catalogue"),"Imported recipe is not a preinstalled or verified-built-in entry");
        check(bundle.tags().getString("engine").equals("engine:moss_nano_ort") && bundle.tags().getJSONArray("task").getString(0).equals("task:audio"),"Task and foundation tags are independent");
        LmaApp app=new LmaApp(new File(root,"files"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        app.bundles.declare(bundle);check(!app.bundles.plan(bundle.id).getBoolean("installed"),"Declaration does not install assets");
        JSONObject plan=app.bundles.plan(bundle.id);check(plan.getLong("totalBytes")==717414286L,"Download plan discloses all eleven components and exact total bytes");
        Map<String,BundleTransfers.Input> selected=new HashMap<>();
        for(ModelBundle.Component c:bundle.components) {
            File source=new File(assets,c.importPath);check(source.isFile() && source.length()==c.bytes,"Selected component exists with exact length");
            selected.put(c.role,()->new FileInputStream(source));
        }
        final List<String> errors=Collections.synchronizedList(new ArrayList<>());
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(component,offset,observer)->{networkCalls++;throw new IOException("Network is forbidden during explicit local import");},new BundleTransfers.Listener(){
            public void changed(){} public void installed(String id){} public void failed(String id,String error){errors.add(error);}
        })) {
            check(networkCalls==0 && !transfers.busy(),"Constructing transfer manager starts no network or download");
            transfers.importFiles(bundle.id,selected);check(transfers.awaitIdle(180,TimeUnit.SECONDS),"Actual full-weight import reaches terminal state");
            check(errors.isEmpty() && app.bundles.plan(bundle.id).getBoolean("installed") && networkCalls==0,"Verified local import installs every asset without fallback downloads");
        }
        JSONObject settings=app.bundles.saveSettings(bundle.id,new JSONObject().put("speaker",999).put("maxFrames",999999).put("maxInputTokens",999999).put("threads",999));
        JSONObject clamped=settings.getJSONObject("values");
        check(clamped.getInt("speaker")==17 && clamped.getInt("maxFrames")==1500 && clamped.getInt("maxInputTokens")==2048 && clamped.getInt("threads")==16,"Per-model editable settings clamp to model voice count and explicit engine guards");
        JSONObject second=DataFiles.copy(manifest).put("id",bundle.id+"_independent");app.bundles.declare(new ModelBundle(second));
        check(app.bundles.settings(second.getString("id")).getJSONObject("values").getInt("speaker")==0,"Independent model record does not inherit another model's settings");
        app.bundles.saveSettings(bundle.id,new JSONObject().put("speaker",0).put("maxFrames",375).put("maxInputTokens",1024).put("threads",4).put("seed",1234));
        JSONObject parameters=app.bundles.settings(bundle.id).getJSONObject("values");
        MossNanoEngine engine=new MossNanoEngine(app,binary,new JSONObject().put("engine","moss_nano_ort"),builder->{
            JSONObject command=new JSONObject(new String(Files.readAllBytes(Paths.get(builder.command().get(1))),"UTF-8"));
            launches.put(command);children++;return builder.start();
        });
        JSONObject normalized=engine.prepare(bundle,request(bundle.id,new JSONObject(parameters.toString()).put("speaker",999),"test"));
        check(normalized.getJSONObject("parameters").getInt("speaker")==17 && normalized.getJSONArray("adjustments").length()>0,"Production engine re-reads downloaded voice metadata before submission");
        JSONArray runs=new JSONArray();String expected=args[4],first="";
        for(String name:new String[]{"initial-a","cancel-after-progress","recovery-a"}) {
            boolean cancel=name.equals("cancel-after-progress");File folder=new File(root,name);long start=System.nanoTime();
            try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
                check(lease.integrity().length()==11,"Actual worker lease retains complete component integrity receipts");
                Context context=new Context(lease,request(bundle.id,parameters,"今天的天空很蓝，我们一起去公园散步。"),folder,cancel);
                if(cancel) {
                    rejects(()->engine.generate(context),"Production NativeWorker cancels actual neural synthesis");
                    check(context.cancelled && context.child!=null && !context.child.isAlive(),"Cancellation was observed after synthesis progress and owned child exited");
                    check(folder.listFiles((dir,file)->file.endsWith(".wav")).length==0,"Cancelled generation leaves no completed WAV");
                } else {
                    File output=engine.generate(context);String hash=sha(output);
                    check(output.length()>44 && hash.equals(expected),"Actual Java-bound trained output matches independent production-source host WAV bytes");
                    check(context.execution!=null && context.execution.getString("finishReason").equals("stop") && context.execution.getInt("sampleRate")==48000,"Production engine publishes actual execution provenance");
                    if(first.isEmpty())first=hash;else check(hash.equals(first),"Actual Java-bound recovery is byte-identical after cancellation");
                    check(context.child!=null && !context.child.isAlive(),"Completed native worker exits");
                    runs.put(new JSONObject().put("name",name).put("output",output.getPath()).put("bytes",output.length()).put("sha256",hash).put("execution",context.execution).put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9));
                }
                check(app.nativeProcess==null && workspaces(app.getFilesDir()).length()==0,"Production Java clears process ownership and hardlink workspace after child exit");
                if(cancel)runs.put(new JSONObject().put("name",name).put("cancelled",true).put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9));
            }
        }
        check(children==3 && networkCalls==0,"Three actual native children run without network execution or download");
        BundleStore restored=new BundleStore(new File(app.getFilesDir(),"bundles"));
        check(restored.plan(bundle.id).getBoolean("installed") && restored.settings(bundle.id).getJSONObject("values").getInt("threads")==4,"Restored model retains installed assets and independent settings");
        JSONObject result=new JSONObject().put("passed",passed).put("actual_host_children",children).put("network_calls",networkCalls).put("imported_components",11).put("imported_bytes",717414286L)
            .put("runs",runs).put("launches",launches).put("same_wav_as_direct_production_worker",true).put("host_java_production_binding",true)
            .put("android_application_executed",false).put("android_saf_tested",false).put("android_background_tested",false).put("speech_quality_accepted",false);
        Files.write(new File(root,"java-results.json").toPath(),result.toString(2).getBytes("UTF-8"));System.out.println(result);
    }
}
