package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Actual production contracts, hardlinks, asset leases and owned host children; no TTS inference. */
public final class MossNanoTest {
    static int passed;
    interface Checked { void run() throws Exception; }
    static void check(boolean v, String reason) { if (!v) throw new AssertionError(reason); passed++; }
    static void rejects(Checked run, String reason) throws Exception { try { run.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(reason); }
    static class Context implements LocalEngine.Context {
        final BundleStore.Lease lease; final JSONObject request; final File root;
        final CountDownLatch started = new CountDownLatch(1); final AtomicBoolean cancelled = new AtomicBoolean(); Process child; JSONObject execution;
        Context(BundleStore.Lease lease, JSONObject request, File root) { this.lease = lease; this.request = request; this.root = root; root.mkdirs(); }
        public BundleStore.Lease model() { return lease; }
        public JSONObject request() { return DataFiles.copy(request); }
        public File output(String suffix) { return new File(root, UUID.randomUUID()+"."+suffix); }
        public void check() throws IOException { if (cancelled.get()) throw new IOException("Host fixture cancelled"); }
        public void progress(String stage, Double value) { started.countDown(); }
        public void process(Process p) { child = p; }
        public void execution(JSONObject value) { execution = value; }
    }
    static JSONObject request(String prompt) throws Exception { return new JSONObject().put("type","speech.synthesize").put("bundleId","nano_fixture").put("input",new JSONObject().put("prompt",prompt)).put("parameters",new JSONObject()); }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); root.mkdirs();
        JSONObject templates = new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")), definition = null;
        JSONArray list = templates.getJSONArray("templates");
        for (int i=0;i<list.length();i++) if (list.getJSONObject(i).getString("id").equals("moss_nano_cpu_v1")) definition=list.getJSONObject(i).getJSONObject("definition");
        check(definition!=null,"Signed App offers an explicit Nano component recipe");
        LinkedHashMap<String,byte[]> contents = new LinkedHashMap<>(); JSONArray files = new JSONArray();
        String[] roles={"manifest","tts_meta","codec_meta","text_tokenizer","tts_prefill","tts_decode","tts_local","codec_decode","tts_data_1","codec_data_1"};
        for (String role:roles) {
            String format = role.endsWith("meta") || role.equals("manifest") ? "json" : role.equals("text_tokenizer") ? "sentencepiece" : role.contains("data_") ? "onnx_data" : "onnx";
            String extension = format.equals("sentencepiece") ? "model" : format.equals("onnx_data") ? "data" : format;
            String name=role.contains("data_") ? "weights.data" : role+"."+extension;
            byte[] data=(role.equals("manifest") ? "{\"builtin_voices\":[{\"voice\":\"fixture A\"},{\"voice\":\"fixture B\"}]}" : "Host asset fixture: "+role).getBytes("UTF-8");
            contents.put(role,data); String hash=Protocol.hex(java.security.MessageDigest.getInstance("SHA-256").digest(data));
            files.put(new JSONObject().put("role",role).put("path",role+"/"+name).put("format",format).put("bytes",data.length).put("sha256",hash));
        }
        JSONObject source=DataFiles.copy(definition).put("schema",ModelBundle.SCHEMA).put("id","nano_fixture").put("modelId","nano_fixture").put("recipeId","nano_fixture").put("name","MOSS host protocol fixture").put("components",files);
        ModelBundle bundle = new ModelBundle(source); MossNanoSpec.validate(bundle,"speech.synthesize"); check(true,"Complete selected Nano components accepted");
        for (int i=0;i<8;i++) { JSONObject missing=DataFiles.copy(source);missing.getJSONArray("components").remove(i);rejects(() -> MossNanoSpec.validate(new ModelBundle(missing),"speech.synthesize"),"Every core role is required"); }
        for (String key:Arrays.asList("pipeline","architecture","backend","engine")) { JSONObject wrong=DataFiles.copy(source).put(key,"other");rejects(() -> MossNanoSpec.validate(new ModelBundle(wrong),"speech.synthesize"),"Do not route other MOSS architectures or backends here"); }
        rejects(() -> MossNanoSpec.validate(bundle,"audio.generate"),"Nano speech is not music generation");
        JSONObject badFormat=DataFiles.copy(source);badFormat.getJSONArray("components").getJSONObject(3).put("format","bin");rejects(() -> MossNanoSpec.validate(new ModelBundle(badFormat),"speech.synthesize"),"SentencePiece format is explicit");
        JSONObject alias=DataFiles.copy(source);alias.getJSONArray("components").getJSONObject(1).put("path","other/manifest.json");rejects(() -> MossNanoSpec.validate(new ModelBundle(alias),"speech.synthesize"),"No graph workspace filename aliases");
        JSONObject huge=DataFiles.copy(source);huge.getJSONArray("components").getJSONObject(4).put("bytes",129L*1024*1024);rejects(() -> MossNanoSpec.validate(new ModelBundle(huge),"speech.synthesize"),"Bound graph size separately from external weights");
        JSONObject effective=MossNanoSpec.parameters(new JSONObject().put("speaker",999).put("maxFrames",99999).put("threads",100).put("maxInputTokens",99999).put("seed",-1),2);
        check(effective.getJSONObject("values").getInt("speaker")==1 && effective.getJSONObject("values").getInt("maxFrames")==1500 && effective.getJSONObject("values").getInt("threads")==16 && effective.getJSONObject("values").getInt("maxInputTokens")==2048 && effective.getJSONObject("values").getInt("seed")==0,"Actual voice count and independent application guards clamp values");
        check(effective.getJSONArray("adjustments").length()==5,"Every numeric adjustment is disclosed");
        rejects(() -> MossNanoSpec.parameters(new JSONObject().put("temperature",0.1),2),"Do not pretend embedded ONNX sampling constants are editable");
        rejects(() -> MossNanoSpec.voices(new JSONObject().put("builtin_voices",new JSONArray())),"No implicit voice download");
        File work = new File(root,"engine-work"), original=new File(root,"verified-source"); Files.write(original.toPath(),new byte[]{1,2,3,4});
        EngineWorkspace.recover(work); File directory;
        try (EngineWorkspace workspace=new EngineWorkspace(work,()->{})) {
            directory=workspace.directory(); File link=workspace.link("tts","weights.data",original);
            check(Files.isSameFile(link.toPath(),original.toPath()),"A real hardlink preserves data without copying weights");
            check(Arrays.equals(Files.readAllBytes(link.toPath()),new byte[]{1,2,3,4}),"Link resolves the actual selected bytes");
            rejects(() -> workspace.link("tts","WEIGHTS.data",original),"Case aliases cannot overwrite another component");
            for (String invalid:Arrays.asList("../x","a/b","a\\b","x:","NUL","COM1.txt","a.","")) rejects(() -> workspace.link("tts",invalid,original),"Refuse nonportable or escaping filenames");
            rejects(() -> workspace.link("../other","x.data",original),"Group stays inside the private workspace");
        }
        check(!directory.exists() && original.isFile(),"Normal cleanup removes only temporary links");
        EngineWorkspace orphan=new EngineWorkspace(work,()->{}); orphan.link("codec","weights.data",original); EngineWorkspace.recover(work);
        check(!orphan.directory().exists() && original.length()==4,"Startup recovery removes abandoned links while preserving model objects");
        rejects(() -> new EngineWorkspace(work,()->{throw new IOException("Pre-cancelled");}),"Cancelled jobs do not create a workspace");
        check(work.list().length==0,"No partial workspace after cancelled construction");
        AtomicInteger checks = new AtomicInteger();
        rejects(() -> { try (EngineWorkspace interrupted=new EngineWorkspace(work,()->{if(checks.incrementAndGet()==3) throw new IOException("Cancelled after link");})) { interrupted.link("tts","weights.data",original); } },"Cancellation after linking propagates");
        check(work.list().length==0 && original.isFile(),"Partial-link cancellation cleanup preserves assets");
        LmaApp app = new LmaApp(root); app.bundles = new BundleStore(new File(root,"assets")); app.bundles.declare(bundle);
        check(!app.bundles.plan(bundle.id).getBoolean("installed") && !app.bundles.snapshot().getJSONObject(0).has("transfer"),"Recipe registration never downloads or installs assets");
        String token=app.bundles.request(bundle.id);
        for (ModelBundle.Component c:bundle.components) { Files.write(app.bundles.partial(c.objectId).toPath(),contents.get(c.role));app.bundles.accept(bundle.id,token,c,app.bundles.partial(c.objectId)); }
        app.bundles.install(bundle.id,token); check(app.bundles.plan(bundle.id).getBoolean("installed"),"Only an explicitly selected complete verified bundle installs");
        AtomicReference<Path> lastWorkspace=new AtomicReference<>();
        NativeWorker.Launcher launcher=builder -> {
            try {
                check(builder.command().size()==2,"New user text stays out of process arguments");
                JSONObject command=new JSONObject(new String(Files.readAllBytes(Paths.get(builder.command().get(1))),"UTF-8"));
                Path dir=Paths.get(command.getString("workspace"));lastWorkspace.set(dir);
                for (ModelBundle.Component c:bundle.components) {
                    Path path=Paths.get(command.getJSONObject("components").getString(c.role));
                    check(path.getParent().equals(dir.resolve(MossNanoSpec.group(c.role))) && path.getFileName().toString().equals(MossNanoSpec.filename(c)),"Every selected role retains its filename and namespace");
                    check(Files.isSameFile(path,app.bundles.object(c.objectId).toPath()),"Engine receives the actual leased object through a hardlink");
                }
                return new ProcessBuilder(Paths.get(System.getProperty("java.home"),"bin","java.exe").toString(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),"com.lma.app.MossFixture",builder.command().get(1)).start();
            } catch (IOException error) { throw error; } catch(Exception error) { throw new IOException(error); }
        };
        File executable=Paths.get(System.getProperty("java.home"),"bin","java.exe").toFile();
        MossNanoEngine engine=new MossNanoEngine(app,executable,new JSONObject().put("engine","moss_nano_ort"),launcher);
        engine.validate(bundle,"speech.synthesize");
        JSONObject values=request("Hello, a new sentence.");values.getJSONObject("parameters").put("speaker",127);
        JSONObject prepared=engine.prepare(bundle,values);
        check(prepared.getJSONObject("parameters").getInt("speaker")==1 && prepared.getJSONArray("adjustments").length()==1,"Task preparation clamps against the actual downloaded voice count");
        check(values.getJSONObject("parameters").getInt("speaker")==127,"Preparation does not mutate the caller or another model's settings");
        JSONObject negative=request("hello");negative.getJSONObject("input").put("negativePrompt","noise");rejects(() -> engine.prepare(bundle,negative),"Unsupported speech fields cannot be silently ignored");
        for (String mode:Arrays.asList("fixture success","fixture fail")) {
            try (BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
                Context context=new Context(lease,engine.prepare(bundle,request(mode)),new File(root,mode.replace(' ','-')));
                if (mode.endsWith("success")) { File result=engine.generate(context);check(result.length()==3 && context.execution.getBoolean("hostFixture"),"Owned child protocol returns only explicitly labeled fixture output"); }
                else rejects(() -> engine.generate(context),"Worker failure cannot complete generation");
                check(!Files.exists(lastWorkspace.get()) && app.nativeProcess==null && !context.child.isAlive(),"Every completion path releases its worker and temporary links");
                for (ModelBundle.Component c:bundle.components) check(app.bundles.hasObject(c),"Cleanup never changes selected model bytes");
            }
        }
        try (BundleStore.Lease lease=app.bundles.acquire(bundle.id)) {
            Context context=new Context(lease,engine.prepare(bundle,request("fixture wait")),new File(root,"cancel"));ExecutorService thread=Executors.newSingleThreadExecutor();
            Future<?> active=thread.submit(() -> { try { engine.generate(context);throw new AssertionError("Cancelled child completed"); } catch(IOException expected) {} catch(Exception e) { throw new RuntimeException(e); } });
            try {
                check(context.started.await(10,TimeUnit.SECONDS),"Actual host child reaches its owned generation stage");
                rejects(() -> app.bundles.remove(bundle.id,true),"Running worker's lease protects all components");
                context.cancelled.set(true);context.child.destroy();active.get(10,TimeUnit.SECONDS);
                check(!Files.exists(lastWorkspace.get()) && app.nativeProcess==null && !context.child.isAlive(),"Cancellation waits for worker exit and removes its links");
            } finally { if(context.child!=null) context.child.destroyForcibly();thread.shutdownNow(); }
        }
        app.bundles.remove(bundle.id,true);check(!app.bundles.plan(bundle.id).getBoolean("installed") && executable.isFile(),"Deleting model data leaves the foundation executable available");
        System.out.println(new JSONObject().put("passed",passed).put("physical_device",false).put("model_inference",false).put("actual_host_hardlinks",true).put("actual_host_child_processes",true).put("fixture_output_is_audio",false));
    }
}
