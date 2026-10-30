package com.lma.app;

import com.lma.app.core.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Complete actual production import/lease/generate/publish/restart on native Windows, not Android. */
public final class Flux2TrainedAppTest {
    static int passed, children, networkCalls;
    static ArtifactStore artifacts;
    static final JSONArray launches = new JSONArray();
    static final String PROMPT = "A small red toy robot standing beside a blue ceramic teapot on a wooden table, studio photograph, soft daylight, clean background";
    static void check(boolean value, String reason) { if (!value) throw new AssertionError(reason); passed++; }
    interface Checked { void run() throws Exception; }
    static String failure(Checked action) throws Exception {
        try { action.run(); } catch (Exception expected) { passed++; return expected.getMessage(); }
        throw new AssertionError("Expected local rejection");
    }
    static JSONObject read(File path) throws Exception { return new JSONObject(new String(Files.readAllBytes(path.toPath()), "UTF-8")); }
    static JSONObject request(ModelBundle bundle, JSONObject values) throws Exception {
        return new JSONObject().put("type", "image.generate").put("bundleId", bundle.id)
            .put("parameters", DataFiles.copy(values)).put("input", new JSONObject().put("prompt", PROMPT).put("negativePrompt", ""))
            .put("adapters", new JSONArray());
    }
    static final class Context implements LocalEngine.Context {
        final BundleStore.Lease lease; final JSONObject frozen; final boolean cancel;
        final String jobId = "job_"+UUID.randomUUID().toString().replace("-", "");
        final JSONArray progress = new JSONArray(); JSONObject execution; Process child; boolean cancelled;
        Context(BundleStore.Lease lease, JSONObject value, boolean cancel) { this.lease=lease; frozen=DataFiles.copy(value); this.cancel=cancel; }
        public BundleStore.Lease model() { return lease; }
        public JSONObject request() { return DataFiles.copy(frozen); }
        public File output(String suffix) throws IOException { return artifacts.staging(jobId, suffix); }
        public void check() throws IOException { if (cancelled) throw new IOException("Requested cancellation after an actual completed sampling step"); }
        public void process(Process process) { child=process; }
        public void execution(JSONObject details) { execution=DataFiles.copy(details); }
        public void progress(String stage, Double fraction) {
            progress.put(new JSONObject().put("stage",stage).put("fraction",fraction==null?JSONObject.NULL:fraction));
            // The direct raw worker trace distinguishes four sampler steps from loading/VAE totals.
            if(cancel && stage.equals("generating") && fraction!=null && fraction==0.25 && child!=null && child.isAlive()) {
                cancelled=true; child.destroy();
            }
        }
    }
    public static void main(String[] args) throws Exception {
        File root=new File(args[0]), originals=new File(args[1]), binary=new File(args[4]); root.mkdirs();
        JSONObject reference=read(new File(args[2])); ModelBundle catalogue=new ModelBundle(reference);
        RecipeCatalogue recipes=new RecipeCatalogue(read(new File(args[3])));
        JSONObject selections=new JSONObject(); Map<String,File> sources=new LinkedHashMap<>();
        long total=0;
        for(ModelBundle.Component c:catalogue.components) {
            selections.put(c.role,new JSONObject().put("role",c.role).put("format",c.format).put("repository",c.repository)
                .put("revision",c.revision).put("path",c.path).put("bytes",c.bytes).put("sha256",c.sha256).put("url",c.url));
            File source=new File(new File(originals,c.sha256),new File(c.path).getName());
            check(source.isFile() && source.length()==c.bytes,"Every complete selected component exists"); sources.put(c.role,source); total+=c.bytes;
        }
        ModelBundle bundle=recipes.compose(reference.getString("recipeId"),selections);
        check(bundle.id.startsWith("hfb_") && !bundle.id.equals(catalogue.id),"HF composition keeps independent immutable identity");
        check(bundle.pipeline.equals("flux2_klein_4b") && bundle.architecture.equals("flux2_klein") && bundle.components.size()==4,"Exact distilled 4B architecture and all components");
        check(!bundle.json().getBoolean("catalogue") && !bundle.json().getJSONObject("uncensored").getBoolean("declared"),"HF composition does not invent content/trust labels");
        check(bundle.json().getJSONObject("evidence").getInt("physicalDeviceTests")==0 && bundle.tasks.equals(Collections.singleton("image")),"Image tag and unverified phone status");
        LmaApp app=new LmaApp(new File(root,"files")); app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        app.bundles.declare(catalogue); app.bundles.declare(bundle);
        check(!app.bundles.plan(bundle.id).getBoolean("installed") && !app.bundles.plan(catalogue.id).getBoolean("installed"),"Both metadata paths download nothing");
        app.bundles.saveSettings(catalogue.id,new JSONObject().put("width",768).put("steps",2));
        JSONObject peerBefore=app.bundles.settings(catalogue.id);
        List<String> errors=Collections.synchronizedList(new ArrayList<>());
        try(BundleTransfers transfers=new BundleTransfers(app.bundles,(c,offset,observer)->{networkCalls++;throw new IOException("Offline explicit local import");},
            new BundleTransfers.Listener(){ public void changed(){} public void installed(String id){} public void failed(String id,String error){errors.add(error);} })) {
            check(!transfers.busy() && networkCalls==0,"Constructing transfer manager starts no download");
            Map<String,BundleTransfers.Input> files=new LinkedHashMap<>();
            for(ModelBundle.Component c:bundle.components)files.put(c.role,()->new FileInputStream(sources.get(c.role)));
            transfers.importFiles(bundle.id,files);
            check(transfers.awaitIdle(3600,TimeUnit.SECONDS) && errors.isEmpty(),"Full-file offline import completes");
            check(networkCalls==0 && app.bundles.plan(bundle.id).getBoolean("installed"),"Explicit import verifies whole SHA and installs only selected profile");
        }
        check(total==5127452603L && new File(app.getFilesDir(),"bundles/objects").listFiles().length==4,"Four complete user-owned objects; no partial substitutes");
        JSONObject bounded=app.bundles.saveSettings(bundle.id,new JSONObject().put("width",99999).put("steps",999).put("cfg",99).put("threads",999).put("flowShift",999)).getJSONObject("values");
        check(bounded.getInt("width")==2048 && bounded.getInt("steps")==4 && bounded.getDouble("cfg")==1 && bounded.getInt("threads")==64 && bounded.getDouble("flowShift")==32,"Editable model settings clamp to declared ceilings");
        JSONObject settings=app.bundles.saveSettings(bundle.id,new JSONObject().put("width",512).put("height",512).put("steps",4).put("threads",6).put("seed",42).put("flowShift",0)).getJSONObject("values");
        check(DataFiles.canonical(peerBefore).equals(DataFiles.canonical(app.bundles.settings(catalogue.id))),"Other model settings remain independent");
        app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        check(app.bundles.plan(bundle.id).getBoolean("installed") && !app.bundles.plan(catalogue.id).getBoolean("installed"),"Restart retains explicit installation without activating peer");
        artifacts=new ArtifactStore(new File(root,"artifacts"),file->{
            java.awt.image.BufferedImage image=javax.imageio.ImageIO.read(file);
            if(image==null)throw new IOException("Cannot inspect actual generated image");
            return new JSONObject().put("mime","image/png").put("width",image.getWidth()).put("height",image.getHeight());
        });
        SdEngine engine=new SdEngine(app,binary,new JSONObject().put("engine","sd_cpp"),(builder)->{
            try {
                JSONObject command=read(new File(builder.command().get(1))); launches.put(command);
                check(command.getString("pipeline").equals("flux2_klein_4b") && command.getString("architecture").equals("flux2_klein"),"Native command retains exact architecture");
                check(command.getString("samplingProfile").equals("flux2_klein") && command.getJSONArray("loras").length()==0,"Distilled route has no implicit adapter");
                for(ModelBundle.Component c:bundle.components) {
                    File actual=new File(command.getJSONObject("components").getString(c.role));
                    check(actual.isFile() && actual.length()==c.bytes,"Every native role uses an installed complete component");
                    check(actual.getCanonicalPath().startsWith(new File(app.getFilesDir(),"bundles/objects").getCanonicalPath()+File.separator),"Native model path belongs to private immutable object store");
                }
                check(builder.environment().get("LMA_VOCAB_QWEN_MERGES").equals(command.getJSONObject("components").getString("qwen_merges")),"Native external vocabulary uses the selected leased component");
            } catch(Exception error) { throw new IOException(error); }
            children++; return builder.start();
        });
        JSONObject invalid=request(bundle,settings); invalid.getJSONObject("input").put("negativePrompt","blur");
        failure(()->engine.prepare(bundle,invalid)); check(children==0,"Negative prompt rejects before native launch");
        JSONArray runs=new JSONArray(); List<String> hashes=new ArrayList<>();
        for(String name:new String[]{"a","cancel-sampling","recovery-a"}) {
            boolean cancel=name.equals("cancel-sampling"); JSONObject wanted=request(bundle,settings),planned=engine.prepare(bundle,wanted);
            try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
                check(lease.integrity().length()==4,"Actual lease protects every model component");
                failure(()->app.bundles.remove(bundle.id,false));
                Context context=new Context(lease,planned,cancel);
                wanted.getJSONObject("input").put("prompt","Caller mutation must never change submitted job");
                planned.getJSONObject("diffusionPlan").getJSONObject("parameters").put("steps",1);
                check(failure(()->app.bundles.saveSettings(bundle.id,new JSONObject().put("steps",1))).contains("in use"),"Active model settings remain protected by the execution lease");
                check(context.request().getJSONObject("input").getString("prompt").equals(PROMPT) && context.request().getJSONObject("diffusionPlan").getJSONObject("parameters").getInt("steps")==4,"Job owns immutable prompt and four-step plan despite later edits");
                System.out.println("Execute actual Java/native FLUX.2-klein: "+name); System.out.flush();
                JSONObject run=new JSONObject().put("name",name);
                if(cancel) {
                    String error=failure(()->engine.generate(context));
                    check(context.cancelled && context.child!=null && !context.child.isAlive() && error.contains("Requested cancellation"),"Java cancellation follows a completed real sampler step and terminates child");
                    check(artifacts.snapshot().length()==1,"Cancelled job publishes no artifact"); run.put("cancelled",true);
                } else {
                    File generated=engine.generate(context); check(generated.isFile() && generated.length()>33,"Actual trained pipeline returns PNG");
                    JSONObject provenance=context.request().put("execution",context.execution);
                    JSONObject published=artifacts.commit(context.jobId,generated,provenance,()->{}); File result=artifacts.file(published.getString("id"));
                    check(published.getJSONObject("provenance").getString("bundleId").equals(bundle.id),"Committed real image retains immutable model identity");
                    check(published.getJSONObject("provenance").getJSONObject("execution").getJSONObject("effectiveParameters").getInt("steps")==4,"Committed provenance retains actual effective parameters");
                    String hash=DataFiles.sha256(result);hashes.add(hash);
                    run.put("artifact",published).put("output",result.getPath()).put("sha256",hash).put("bytes",result.length());
                }
                check(app.nativeProcess==null && context.child!=null && !context.child.isAlive(),"Every terminal job releases actual native child");
                check(context.execution.getJSONObject("effectiveParameters").getInt("steps")==4 && context.execution.getString("samplingProfile").equals("flux2_klein"),"Actual execution metadata retains distilled plan");
                runs.put(run.put("progress",context.progress).put("execution",context.execution));
            }
            app.bundles.saveSettings(bundle.id,new JSONObject().put("steps",1));
            check(app.bundles.settings(bundle.id).getJSONObject("values").getInt("steps")==1,"Model becomes editable after the actual child and lease finish");
        }
        check(hashes.size()==2 && hashes.get(0).equals(hashes.get(1)),"Recovery exactly reproduces actual deterministic PNG bytes");
        try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
            JSONObject bad=engine.prepare(bundle,request(bundle,settings));bad.getJSONObject("diffusionPlan").getJSONObject("parameters").put("steps",2);
            int before=children; failure(()->engine.generate(new Context(lease,bad,false)));check(children==before,"Tampered immutable plan rejects before launch");
        }
        for(ModelBundle.Component c:bundle.components)check(DataFiles.sha256(sources.get(c.role)).equals(c.sha256),"Original complete user component remains unchanged");
        check(children==3 && networkCalls==0,"Exactly three actual children and zero network transports");
        app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));
        check(app.bundles.settings(bundle.id).getJSONObject("values").getInt("steps")==1,"Latest independent model edit survives restart while prior jobs retain four steps");
        check(DataFiles.canonical(peerBefore).equals(DataFiles.canonical(app.bundles.settings(catalogue.id))),"Peer profile survives execution and restart");
        artifacts=new ArtifactStore(new File(root,"artifacts"),file->{throw new IOException("Restart reads committed metadata without re-decoding");});
        for(int i=0;i<runs.length();i++)if(runs.getJSONObject(i).has("artifact"))check(artifacts.file(runs.getJSONObject(i).getJSONObject("artifact").getString("id")).isFile(),"Restart preserves actual completed result");
        app.bundles.remove(bundle.id,false); check(!app.bundles.plan(bundle.id).getBoolean("installed"),"Explicit model deletion removes local installation");
        check(artifacts.snapshot().length()==2 && app.bundles.settings(bundle.id).getJSONObject("values").getInt("steps")==1,"Removing model preserves generated results and chosen settings");
        check(!app.bundles.plan(catalogue.id).getBoolean("installed"),"No deletion/restart path downloads or installs catalogue peer");
        JSONObject report=new JSONObject().put("passed",passed).put("actual_host_children",children).put("network_calls",networkCalls)
            .put("imported_objects",4).put("imported_bytes",total).put("bundle",bundle.json()).put("runs",runs).put("launches",launches)
            .put("production_java_native_host_executed",true).put("physical_android",false).put("android_saf_tested",false)
            .put("android_background_accepted",false).put("image_quality_accepted",false).put("complete_release_accepted",false);
        Files.write(new File(root,"java-results.json").toPath(),report.toString(2).getBytes("UTF-8"));
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",children));
    }
}
