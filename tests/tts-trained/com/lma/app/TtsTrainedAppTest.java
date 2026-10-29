package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Production Java and real trained worker, with an explicit host Application filesystem port. */
public final class TtsTrainedAppTest {
    static int passed, children, networkCalls;
    static final JSONArray launches = new JSONArray();
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); passed++; }
    interface Checked { void run() throws Exception; }
    static String failure(Checked run) throws Exception {
        try { run.run(); } catch (IOException expected) { passed++; return expected.getMessage(); }
        throw new AssertionError("Expected actual worker failure");
    }
    static String sha(File path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = new FileInputStream(path)) {
            byte[] bytes = new byte[1024*1024]; int n;
            while ((n=stream.read(bytes))!=-1) digest.update(bytes,0,n);
        }
        return Protocol.hex(digest.digest());
    }
    static final class Context implements LocalEngine.Context {
        final BundleStore.Lease lease; final JSONObject request; final File folder; final boolean cancel;
        final JSONArray progress = new JSONArray(); volatile boolean cancelled; Process child; JSONObject execution;
        Context(BundleStore.Lease lease, JSONObject request, File folder, boolean cancel) {
            this.lease=lease; this.request=DataFiles.copy(request); this.folder=folder; this.cancel=cancel; folder.mkdirs();
        }
        public BundleStore.Lease model() { return lease; }
        public JSONObject request() { return DataFiles.copy(request); }
        public File output(String suffix) { return new File(folder,UUID.randomUUID()+"."+suffix); }
        public void check() throws IOException { if(cancelled) throw new IOException("Requested cancellation after partial actual synthesis"); }
        public void progress(String stage,Double fraction) throws Exception {
            progress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));
            if(cancel && stage.equals("synthesizing") && fraction!=null && fraction>0 && fraction<1 && child!=null && child.isAlive()) {
                cancelled=true; child.destroy();
            }
        }
        public void process(Process process) {
            child=process; children++;
            try {
                File[] requests=folder.listFiles((dir,name)->name.endsWith(".json"));
                TtsTrainedAppTest.check(requests!=null && requests.length==1,"One private request file belongs to actual child");
                launches.put(new JSONObject(new String(Files.readAllBytes(requests[0].toPath()),"UTF-8")));
            } catch(Exception e) { process.destroyForcibly(); throw new RuntimeException(e); }
        }
        public void execution(JSONObject details) { execution=DataFiles.copy(details); }
    }
    static JSONObject request(String id,JSONObject parameters,String prompt) throws Exception {
        return new JSONObject().put("type","speech.synthesize").put("bundleId",id)
            .put("input",new JSONObject().put("prompt",prompt)).put("parameters",DataFiles.copy(parameters));
    }
    public static void main(String[] args) throws Exception {
        File root=new File(args[0]),assets=new File(args[1]),binary=new File(args[3]); root.mkdirs();
        JSONArray catalogue=new JSONObject(new String(Files.readAllBytes(Paths.get(args[2])),"UTF-8")).getJSONArray("bundles");
        List<ModelBundle> bundles=new ArrayList<>();
        for(int i=0;i<catalogue.length();i++) {
            ModelBundle bundle=new ModelBundle(catalogue.getJSONObject(i));
            if(bundle.engine.equals("sherpa_tts")) { TtsSpec.validate(bundle,"speech.synthesize"); bundles.add(bundle); }
        }
        check(bundles.size()==3,"All three frozen speech recipes are covered");
        LmaApp app=new LmaApp(new File(root,"files")); app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        final List<String> errors=Collections.synchronizedList(new ArrayList<>());
        long importedBytes=0; int references=0; Set<String> objects=new HashSet<>();
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(component,offset,observer)->{
            networkCalls++; throw new IOException("No network during explicitly selected local import");
        },new BundleTransfers.Listener(){
            public void changed(){} public void installed(String id){} public void failed(String id,String error){errors.add(error);}
        })) {
            check(networkCalls==0 && !transfers.busy(),"Transfer manager construction starts no download");
            for(ModelBundle bundle:bundles) {
                app.bundles.declare(bundle);
                check(!app.bundles.plan(bundle.id).getBoolean("installed"),"Metadata declaration installs no model data");
                check(bundle.tasks.equals(Collections.singleton("audio")) && bundle.tags().getString("engine").equals("engine:sherpa_tts"),"Task and foundation tags are independent");
                Map<String,BundleTransfers.Input> selected=new HashMap<>(); long planned=0;
                for(ModelBundle.Component component:bundle.components) {
                    File source=new File(new File(assets,component.sha256),component.path);
                    check(source.isFile() && source.length()==component.bytes,"Explicitly selected source has the pinned length");
                    selected.put(component.role,()->new FileInputStream(source)); planned+=component.bytes; references++;
                    if(objects.add(component.sha256)) importedBytes+=component.bytes;
                }
                check(app.bundles.plan(bundle.id).getLong("totalBytes")==planned,"Plan discloses full required asset size");
                transfers.importFiles(bundle.id,selected);
                check(transfers.awaitIdle(180,TimeUnit.SECONDS),"Full trained local import reaches terminal state");
                check(errors.isEmpty() && app.bundles.plan(bundle.id).getBoolean("installed") && networkCalls==0,"All selected assets pass production import checks without network");
            }
        }
        check(references==11 && objects.size()==9,"Three bundles share only the identical lexicon content object");
        check(new File(app.getFilesDir(),"bundles/objects").listFiles().length==9,"Shared lexicon is not stored three times");
        Map<String,JSONObject> saved=new HashMap<>(); int index=0;
        for(ModelBundle bundle:bundles) {
            JSONObject clamped=app.bundles.saveSettings(bundle.id,new JSONObject().put("speaker",999999).put("threads",999)
                .put("speed",99).put("maxAudioSeconds",99999)).getJSONObject("values");
            check(clamped.getInt("speaker")== (bundle.pipeline.equals("kokoro")?53:0) && clamped.getInt("threads")==16
                && clamped.getDouble("speed")==3 && clamped.getInt("maxAudioSeconds")==600,"Editable settings clamp to this model's declared limits");
            JSONObject wanted=new JSONObject().put("threads",4).put("speaker",0).put("speed",1+index*.1).put("silenceScale",1).put("maxAudioSeconds",180);
            if(!bundle.pipeline.equals("kokoro"))wanted.put("noiseScale",.667);
            if(bundle.pipeline.equals("piper_vits"))wanted.put("noiseScaleW",.8);
            JSONObject values=app.bundles.saveSettings(bundle.id,wanted).getJSONObject("values"); saved.put(bundle.id,values); index++;
        }
        for(ModelBundle bundle:bundles)check(app.bundles.settings(bundle.id).getJSONObject("values").toString().equals(saved.get(bundle.id).toString()),"Other models' saves do not change this model's parameters");
        SherpaEngine engine=new SherpaEngine(app,binary,new JSONObject().put("engine","sherpa_tts")); JSONArray runs=new JSONArray();
        for(ModelBundle bundle:bundles) {
            JSONObject parameters=saved.get(bundle.id);
            JSONObject prepared=engine.prepare(bundle,request(bundle.id,new JSONObject(parameters.toString()).put("threads",999),"Hello world."));
            check(prepared.getJSONObject("parameters").getInt("threads")==16 && prepared.getJSONArray("adjustments").length()>0,"Production prepare records parameter adjustments");
            for(String name:new String[]{"initial-a","cancel-after-progress","duration-limit","recovery-a"}) {
                boolean cancel=name.equals("cancel-after-progress"),limited=name.equals("duration-limit");
                File folder=new File(root,bundle.pipeline+"-"+name); long start=System.nanoTime();
                JSONObject job=request(bundle.id,parameters,cancel?String.join(" ",Collections.nCopies(12,"Hello world. The sun is shining.")):"Hello world. The sun is shining.");
                if(limited)job.getJSONObject("parameters").put("maxAudioSeconds",1);
                try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
                    check(lease.integrity().length()==bundle.components.size(),"Lease binds every trained component receipt");
                    Context context=new Context(lease,job,folder,cancel);
                    job.getJSONObject("parameters").put("speed",3); job.getJSONObject("input").put("prompt","Mutated caller text");
                    check(context.request().getJSONObject("parameters").getDouble("speed")==parameters.getDouble("speed"),"Queued request owns an immutable selected-model snapshot");
                    JSONObject run=new JSONObject().put("name",name).put("bundle_id",bundle.id).put("pipeline",bundle.pipeline);
                    if(cancel || limited) {
                        String message=failure(()->engine.generate(context));
                        check(context.child!=null && !context.child.isAlive(),"Failed/cancelled actual child exits");
                        check(folder.listFiles((dir,file)->file.endsWith(".wav")).length==0,"No partial WAV is accepted on failure or cancellation");
                        if(cancel)check(context.cancelled,"Cancellation follows actual partial neural synthesis, before completion");
                        else check(message.equals("Audio exceeded the selected duration limit; no partial output was accepted"),"Actual native duration error reaches production Java");
                        run.put("cancelled",cancel).put("expected_error",message);
                    } else {
                        File output=engine.generate(context);
                        check(output.length()>44,"Actual Java-bound trained worker writes a nonempty WAV");
                        check(context.child!=null && !context.child.isAlive(),"Successful actual child exits");
                        check(context.execution!=null && context.execution.has("audio") && context.execution.has("effectiveParameters"),"Both real execution events survive the shared Java bridge");
                        JSONObject effective=context.execution.getJSONObject("effectiveParameters");
                        // The pinned C API takes float speed; require that exact conversion, not a broad tolerance.
                        check(effective.getDouble("speed")==(double)(float)parameters.getDouble("speed") && effective.getInt("threads")==4,"Actual worker consumes this model's saved parameters at its declared float precision");
                        check(context.execution.getInt("speakerCount")== (bundle.pipeline.equals("kokoro")?54:1),"Actual model voice count reaches the application context");
                        run.put("output",output.getPath()).put("bytes",output.length()).put("sha256",sha(output)).put("execution",context.execution);
                    }
                    check(app.nativeProcess==null,"Production bridge releases native process ownership");
                    check(folder.listFiles((dir,file)->file.endsWith(".json")).length==0,"Private request is removed on every terminal path");
                    runs.put(run.put("progress",context.progress).put("seconds",(System.nanoTime()-start)/1e9));
                }
            }
        }
        check(children==12 && networkCalls==0,"Twelve actual native jobs use zero network calls");
        BundleStore restored=new BundleStore(new File(app.getFilesDir(),"bundles"));
        for(ModelBundle bundle:bundles)check(restored.plan(bundle.id).getBoolean("installed")
            && restored.settings(bundle.id).getJSONObject("values").toString().equals(saved.get(bundle.id).toString()),"Restart preserves each installed model and its independent parameters");
        JSONObject result=new JSONObject().put("passed",passed).put("actual_host_children",children).put("network_calls",networkCalls)
            .put("imported_component_references",references).put("imported_objects",objects.size()).put("imported_bytes",importedBytes)
            .put("runs",runs).put("launches",launches).put("host_java_production_binding",true).put("seed_control_available",false)
            .put("android_application_executed",false).put("android_saf_tested",false).put("android_background_tested",false).put("speech_quality_accepted",false);
        Files.write(new File(root,"java-results.json").toPath(),result.toString(2).getBytes("UTF-8"));System.out.println(result);
    }
}
