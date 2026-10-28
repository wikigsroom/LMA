package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Real host child/file protocol tests. Static WAV fixtures are never model-generated audio. */
public final class QwenTtsTest {
    private static int passed;
    private interface Action { void run() throws Exception; }
    private static void check(boolean ok,String name) { if(!ok) throw new AssertionError(name);passed++; }
    private static void rejects(Action action,String name) throws Exception { try{action.run();}catch(Exception expected){passed++;return;}throw new AssertionError(name); }
    private static JSONObject request(ModelBundle bundle) throws Exception { return new JSONObject().put("bundleId",bundle.id).put("type","speech.synthesize").put("input",new JSONObject().put("prompt","fixture-wave")).put("parameters",QwenTtsSpec.parameters(new JSONObject()).getJSONObject("values")).put("allowUnmeasured",true); }
    private static byte[] wave(int rate,int channels,int format,int bits,int samples) throws Exception {
        int bytes=bits/8*channels*samples; java.nio.ByteBuffer b=java.nio.ByteBuffer.allocate(44+bytes).order(java.nio.ByteOrder.LITTLE_ENDIAN);
        b.put("RIFF".getBytes("US-ASCII")).putInt(36+bytes).put("WAVEfmt ".getBytes("US-ASCII")).putInt(16).putShort((short)format).putShort((short)channels).putInt(rate).putInt(rate*channels*bits/8).putShort((short)(channels*bits/8)).putShort((short)bits).put("data".getBytes("US-ASCII")).putInt(bytes);return b.array();
    }
    private static void child(String path) throws Exception {
        JSONObject command=new JSONObject(new String(Files.readAllBytes(Paths.get(path)),"UTF-8")); String prompt=command.getJSONObject("input").getString("prompt");
        if(prompt.equals("fixture-error")){System.out.println(new JSONObject().put("event","error").put("message","explicit fixture failure"));System.exit(3);}
        Path root=Paths.get(command.getString("workspace"));
        if(!Files.isRegularFile(root.resolve("models/qwen-talker-0.6b-base.gguf")) || !Files.isRegularFile(root.resolve("models/qwen-tokenizer-12hz.gguf"))) throw new IOException("Missing selected component hardlink");
        if(command.has("referenceAudio")) QwenTtsSpec.reference(new File(command.getString("referenceAudio")));
        JSONObject receipt=new JSONObject().put("fixture","PROTOCOL_NOT_MODEL_INFERENCE").put("command",command);
        Files.write(Paths.get(command.getString("output")+".receipt"),receipt.toString().getBytes("UTF-8"));
        Files.write(Paths.get(command.getString("output")),prompt.equals("fixture-json")?receipt.toString().getBytes("UTF-8"):wave(24000,1,1,16,24000));
        System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("hostFixture",true).put("effectiveParameters",command.getJSONObject("parameters"))));
        System.out.println(new JSONObject().put("event","stage").put("stage","fixture_protocol"));
        System.out.println(new JSONObject().put("event","complete").put("output",command.getString("output")));
    }
    public static void main(String[] args) throws Exception {
        if(args.length==2 && args[0].equals("child")){child(args[1]);return;}
        File root=new File(args[0]);root.mkdirs();RecipeCatalogue recipes=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")));
        JSONObject template=recipes.template("qwen3_tts_06b_base_cpu_v1");check(template.getJSONArray("requirements").length()==2,"Two explicit physical GGUF components");
        JSONObject raw=DataFiles.copy(template.getJSONObject("definition"));JSONArray components=new JSONArray();Map<String,File> files=new LinkedHashMap<>();
        for(String role:Arrays.asList("talker","audio_codec")){File file=new File(root,role+".gguf");Files.write(file.toPath(),("NOT_A_MODEL_"+role).getBytes("UTF-8"));files.put(role,file);components.put(new JSONObject().put("role",role).put("path",role+".gguf").put("format","gguf").put("bytes",file.length()).put("sha256",DataFiles.sha256(file)));}
        ModelBundle bundle=new ModelBundle(raw.put("schema",ModelBundle.SCHEMA).put("id","qwen_fixture").put("modelId","qwen_fixture").put("recipeId",template.getString("id")).put("name","Not a model").put("components",components));
        QwenTtsSpec.validate(bundle,"speech.synthesize");check(true,"Exact Base data contract");
        for(String key:Arrays.asList("engine","architecture","pipeline","backend")) rejects(()->QwenTtsSpec.validate(new ModelBundle(bundle.json().put(key,"other")),"speech.synthesize"),"Other architecture/backend rejected");
        rejects(()->QwenTtsSpec.validate(bundle,"audio.generate"),"TTS is not sound generation");rejects(()->QwenTtsSpec.validate(new ModelBundle(bundle.json().put("components",new JSONArray().put(components.getJSONObject(0)))),"speech.synthesize"),"Missing codec rejected");
        JSONObject wrong=bundle.json();wrong.getJSONArray("components").getJSONObject(0).put("format","onnx");rejects(()->QwenTtsSpec.validate(new ModelBundle(wrong),"speech.synthesize"),"Wrong physical format rejected");
        JSONObject limits=QwenTtsSpec.schema().getJSONObject("fields");
        for(String key:Arrays.asList("threads","maxInputTokens","maxAudioTokens","temperature","topP","topK","repetitionPenalty","seed")) {
            JSONObject f=limits.getJSONObject(key);JSONObject high=QwenTtsSpec.parameters(new JSONObject().put(key,f.getDouble("maximum")+100)),low=QwenTtsSpec.parameters(new JSONObject().put(key,f.getDouble("minimum")-100));
            check(high.getJSONObject("values").getDouble(key)==f.getDouble("maximum"),"High bound clamped for "+key);check(low.getJSONObject("values").getDouble(key)==f.getDouble("minimum"),"Low bound clamped for "+key);
        }
        check(QwenTtsSpec.parameters(new JSONObject().put("language","zh")).getJSONObject("values").getString("language").equals("zh"),"Language persisted");
        File reference=new File(root,"reference.wav");Files.write(reference.toPath(),wave(24000,1,1,16,24000));QwenTtsSpec.reference(reference);check(true,"Actual PCM16 reference parsed");
        for(int[] f:new int[][]{{16000,1,1,16,24000},{24000,2,1,16,24000},{24000,1,1,32,24000},{24000,1,1,16,23999},{24000,1,1,16,720001}}){File bad=new File(root,"bad.wav");Files.write(bad.toPath(),wave(f[0],f[1],f[2],f[3],f[4]));rejects(()->QwenTtsSpec.reference(bad),"Invalid reference format/duration rejected");}
        File floats=new File(root,"float.wav");Files.write(floats.toPath(),wave(24000,1,3,32,24000));QwenTtsSpec.reference(floats);check(WaveFile.inspect(floats).getInt("formatCode")==3,"Float input distinguished from PCM32");
        check(!QwenTtsSpec.inputs().json().getJSONObject("roles").getJSONObject("reference_audio").getBoolean("required"),"Reference is optional; no preset voice data");
        LmaApp app=new LmaApp(new File(root,"app"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));app.bundles.declare(bundle);
        check(!app.bundles.record(bundle.id).getBoolean("installed"),"Declaring a recipe does not install model data");String token=app.bundles.request(bundle.id);
        for(ModelBundle.Component c:bundle.components){Files.copy(files.get(c.role).toPath(),app.bundles.partial(c.objectId).toPath(),StandardCopyOption.REPLACE_EXISTING);app.bundles.accept(bundle.id,token,c,app.bundles.partial(c.objectId));}app.bundles.install(bundle.id,token);
        File binary=new File(System.getProperty("java.home"),"bin/java.exe");AtomicInteger launches=new AtomicInteger(),progress=new AtomicInteger();
        NativeWorker.Launcher launcher=builder->{launches.incrementAndGet();return new ProcessBuilder(binary.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),QwenTtsTest.class.getName(),"child",builder.command().get(1)).redirectErrorStream(true).start();};
        QwenTtsEngine engine=new QwenTtsEngine(app,binary,new JSONObject().put("engine","qwen_tts_native"),launcher);JSONObject frozen=engine.prepare(bundle,request(bundle));
        JSONObject negative=request(bundle);negative.getJSONObject("input").put("negativePrompt","not speech");rejects(()->engine.prepare(bundle,negative),"Negative prompt rejected");
        JSONObject execution=new JSONObject();File staging=new File(root,"staging");staging.mkdirs();
        try(BundleStore.Lease lease=app.bundles.acquire(bundle.id)){
            LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return frozen;}public File input(String role){return reference;}public File output(String suffix){return new File(staging,UUID.randomUUID()+"."+suffix);}public void check(){}public void process(Process process){}public void progress(String stage,Double fraction){progress.incrementAndGet();}public void execution(JSONObject value)throws Exception{execution.put("details",value);}};
            // Include a real selected local WAV. The child writes a structural WAV fixture only.
            frozen.getJSONObject("input").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_audio").put("artifactId","fixture_input")));
            File output=engine.generate(context);JSONObject receipt=new JSONObject(new String(Files.readAllBytes(Paths.get(output.getPath()+".receipt")),"UTF-8"));JSONObject command=receipt.getJSONObject("command");
            check(WaveFile.inspect(output).getLong("samples")==24000,"Production binding accepts structurally valid WAV fixture");
            check(command.getJSONObject("parameters").getLong("seed")>=0,"Actual seed reaches child");check(command.has("referenceAudio"),"Explicit local reference reaches child");check(command.getString("pipeline").equals("qwen3_tts_06b_base"),"Exact pipeline reaches child");
            check(progress.get()>0 && execution.getJSONObject("details").getBoolean("hostFixture"),"Shared event channel works");check(app.nativeProcess==null && new File(app.getFilesDir(),"engine-work").list().length==0,"Child ownership and workspace released");
            frozen.getJSONObject("input").put("prompt","fixture-json");rejects(()->engine.generate(context),"JSON cannot masquerade as generated audio");
            frozen.getJSONObject("input").put("prompt","fixture-error");rejects(()->engine.generate(context),"Actual child failure propagates");
            frozen.getJSONObject("parameters").put("threads",999);rejects(()->engine.generate(context),"Outdated or tampered parameter snapshot rejected before launch");check(launches.get()==3,"Rejected snapshot does not create a child");
            check(app.nativeProcess==null && new File(app.getFilesDir(),"engine-work").list().length==0,"Failure cleanup preserves originals");
        }
        check(files.get("talker").isFile() && reference.isFile(),"User model/reference data preserved");
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",launches.get()).put("production_qwen_binding",true).put("model_inference",false).put("generated_audio_outputs",false).put("structural_wav_fixture",true));
    }
}
