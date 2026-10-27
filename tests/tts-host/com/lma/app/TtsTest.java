package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Production TTS contracts and worker lifecycle on host processes; zero Android/model inference. */
public final class TtsTest {
    static int passed;
    interface Checked { void run() throws Exception; }
    static void check(boolean v, String m) { if (!v) throw new AssertionError(m); passed++; }
    static void rejects(Checked c, String m) throws Exception { try { c.run(); } catch (Exception e) { passed++; return; } throw new AssertionError(m); }
    static JSONObject component(String role, String format) throws Exception {
        return new JSONObject().put("role", role).put("path", role + "." + format).put("bytes", 1).put("format", format).put("sha256", String.join("", Collections.nCopies(64,"a")));
    }
    static JSONObject bundle(String pipeline) throws Exception {
        JSONArray components = new JSONArray().put(component("model", "onnx")).put(component("tokens", "text")).put(component("lexicon", "text"));
        if (pipeline.equals("kokoro")) components.put(component("voices", "bin"));
        if (pipeline.equals("matcha")) components.put(component("vocoder", "onnx"));
        return new JSONObject().put("schema", ModelBundle.SCHEMA).put("id", pipeline).put("modelId", pipeline).put("recipeId", pipeline).put("name", "Contract fixture")
            .put("engine", "sherpa_tts").put("architecture", pipeline).put("pipeline", pipeline).put("backend", "cpu").put("tasks", new JSONArray().put("audio")).put("components", components);
    }
    static class Context implements LocalEngine.Context {
        final File folder; final AtomicBoolean cancelled = new AtomicBoolean(); final CountDownLatch started = new CountDownLatch(1);
        JSONObject execution; Process child; int progresses;
        Context(File folder) { this.folder = folder; folder.mkdirs(); }
        public BundleStore.Lease model() { return null; }
        public JSONObject request() { return new JSONObject(); }
        public File output(String suffix) { return new File(folder, UUID.randomUUID()+"."+suffix); }
        public void check() throws IOException { if (cancelled.get()) throw new IOException("Fixture cancellation"); }
        public void progress(String stage, Double value) { progresses++; started.countDown(); }
        public void process(Process child) { this.child = child; }
        public void execution(JSONObject value) { execution = DataFiles.copy(value); }
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]); root.mkdirs(); LmaApp app = new LmaApp(root);
        for (String pipeline : Arrays.asList("kokoro", "piper_vits", "matcha")) {
            TtsSpec.validate(new ModelBundle(bundle(pipeline)), "speech.synthesize"); check(true, "Complete TTS components accepted");
            JSONObject missing = bundle(pipeline); missing.getJSONArray("components").remove(2);
            rejects(() -> TtsSpec.validate(new ModelBundle(missing), "speech.synthesize"), "Lexicon is mandatory");
            rejects(() -> TtsSpec.validate(new ModelBundle(bundle(pipeline)), "audio.generate"), "Speech pipeline is not generic music generation");
        }
        JSONObject extra = bundle("piper_vits"); extra.getJSONArray("components").put(component("voices","bin"));
        rejects(() -> TtsSpec.validate(new ModelBundle(extra), "speech.synthesize"), "No unrelated voice table");
        JSONObject wrong = bundle("kokoro"); wrong.getJSONArray("components").getJSONObject(0).put("format","gguf");
        rejects(() -> TtsSpec.validate(new ModelBundle(wrong), "speech.synthesize"), "ONNX format required");
        JSONObject multilingual = bundle("kokoro"); multilingual.getJSONArray("components").put(component("lexicon_2","text"));
        TtsSpec.validate(new ModelBundle(multilingual),"speech.synthesize"); check(true,"Explicit second language lexicon accepted");
        JSONObject values = TtsSpec.parameters(new JSONObject().put("threads",1000).put("speed",20).put("speaker",999999).put("maxAudioSeconds",9999),"kokoro");
        check(values.getInt("threads")==16 && values.getDouble("speed")==3 && values.getInt("speaker")==65535 && values.getInt("maxAudioSeconds")==600,"Independent native application bounds clamp imported schemas");
        rejects(() -> TtsSpec.parameters(new JSONObject().put("remote_url","https://example.com"),"kokoro"),"Unknown parameters rejected");
        rejects(() -> TtsSpec.parameters(new JSONObject().put("noiseScaleW",1),"matcha"),"No unsupported pipeline parameters");
        check(TtsSpec.text(new JSONObject().put("prompt","Hello world.")).equals("Hello world."),"Plain speech input accepted");
        rejects(() -> TtsSpec.text(new JSONObject().put("prompt","a\u0000b")),"No embedded text terminator");
        rejects(() -> TtsSpec.text(new JSONObject().put("prompt",String.join("",Collections.nCopies(4001,"x")))),"Bounded speech text");
        rejects(() -> TtsSpec.text(new JSONObject().put("prompt","hello").put("negativePrompt","music")),"No silently ignored negative speech prompt");
        JSONObject catalogue = new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")); int candidates=0;
        for (int i=0;i<catalogue.getJSONArray("bundles").length();i++) {
            ModelBundle b=new ModelBundle(catalogue.getJSONArray("bundles").getJSONObject(i));
            if (!b.engine.equals("sherpa_tts")) continue;
            TtsSpec.validate(b,"speech.synthesize"); TtsSpec.parameters(b.parameters().normalize(new JSONObject(),new JSONObject()).getJSONObject("values"),b.pipeline); candidates++;
        }
        check(candidates==3,"Three production TTS candidate manifests satisfy runtime contracts");
        NativeWorker.Launcher launcher = builder -> {
            check(builder.command().size()==2 && builder.command().get(1).endsWith(".json"),"User prompt stays out of argv");
            check(builder.environment().get("LD_LIBRARY_PATH").equals(root.getPath()),"Private native dependency path");
            return new ProcessBuilder(Paths.get(System.getProperty("java.home"),"bin","java.exe").toString(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),"com.lma.app.WorkerFixture",builder.command().get(1)).start();
        };
        for (String mode : Arrays.asList("ok","error","missing","wrong","duplicate","long","exit")) {
            Context context = new Context(new File(root,mode)); File output=context.output("fixture");
            JSONObject command=new JSONObject().put("fixture",mode).put("output",output.getPath());
            Checked run=() -> NativeWorker.run(app,new File(root,"owned-worker"),context,command,output,Collections.emptyMap(),launcher);
            if (mode.equals("ok")) { run.run(); check(context.execution.has("audio") && context.execution.has("effectiveParameters"),"Multiple execution events retain effective parameters and waveform facts"); check(context.progresses>=2,"Stages and progress forwarded"); }
            else rejects(run,"Invalid/incomplete fixture protocol cannot commit output: "+mode);
            check(app.nativeProcess==null && context.child!=null && !context.child.isAlive(),"Worker process ownership released");
            check(Arrays.stream(context.folder.listFiles()).noneMatch(f -> f.getName().endsWith(".json")),"Private input removed on every completion path");
        }
        Context cancelled=new Context(new File(root,"cancel")); File output=cancelled.output("fixture"); ExecutorService thread=Executors.newSingleThreadExecutor();
        Future<?> active=thread.submit(() -> { try { NativeWorker.run(app,new File(root,"owned-worker"),cancelled,new JSONObject().put("fixture","wait").put("output",output.getPath()),output,Collections.emptyMap(),launcher); throw new AssertionError("Cancellation became success"); } catch (IOException expected) {} catch(Exception e) { throw new RuntimeException(e); } });
        try { check(cancelled.started.await(10,TimeUnit.SECONDS),"Owned fixture process starts"); cancelled.cancelled.set(true); cancelled.child.destroy(); active.get(10,TimeUnit.SECONDS); check(app.nativeProcess==null && !cancelled.child.isAlive(),"Cancellation releases owned child before next job"); }
        finally { if (cancelled.child!=null) cancelled.child.destroyForcibly(); thread.shutdownNow(); }
        Context stopped=new Context(new File(root,"pre-cancel")); stopped.cancelled.set(true);
        rejects(() -> NativeWorker.run(app,new File(root,"owned-worker"),stopped,new JSONObject(),stopped.output("fixture"),Collections.emptyMap(),launcher),"Cancelled job never launches a child");
        check(stopped.child==null,"No process created for stale job");
        System.out.println(new JSONObject().put("passed",passed).put("physical_device",false).put("model_inference",false).put("actual_host_child_processes",true).put("fixture_output_is_audio",false));
    }
}
