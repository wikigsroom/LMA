package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Actual host children and structural WAVs, never neural model/audio quality evidence. */
public final class OpenMossTest {
    private static int passed;
    private interface Action {void run() throws Exception;}
    private static void check(boolean v,String why) {if(!v)throw new AssertionError(why);passed++;}
    private static void rejects(Action a,String why) throws Exception {try{a.run();}catch(Exception ok){passed++;return;}throw new AssertionError(why);}
    private static byte[] wave(int rate,int channels,int format,int bits,int frames) throws Exception {
        int size=bits/8*channels*frames;java.nio.ByteBuffer b=java.nio.ByteBuffer.allocate(44+size).order(java.nio.ByteOrder.LITTLE_ENDIAN);
        b.put("RIFF".getBytes("US-ASCII")).putInt(36+size).put("WAVEfmt ".getBytes("US-ASCII")).putInt(16).putShort((short)format).putShort((short)channels).putInt(rate).putInt(rate*channels*bits/8).putShort((short)(channels*bits/8)).putShort((short)bits).put("data".getBytes("US-ASCII")).putInt(size);return b.array();
    }
    private static void child(String path) throws Exception {
        JSONObject c=new JSONObject(new String(Files.readAllBytes(Paths.get(path)),"UTF-8"));String prompt=c.getJSONObject("input").getString("prompt");boolean sound=c.getString("type").equals("audio.generate");Path work=Paths.get(c.getString("workspace"));
        if(!Files.isRegularFile(work.resolve("models/model.gguf")) || !Files.isRegularFile(work.resolve("models/model.extras.gguf")))throw new IOException("Missing explicit model/extras hardlinks");
        if(c.has("referenceAudio"))OpenMossSpec.reference(new File(c.getString("referenceAudio")));
        if(prompt.equals("fixture-error")){System.out.println(new JSONObject().put("event","error").put("message","explicit fixture failure"));System.exit(3);}
        Files.write(Paths.get(c.getString("output")+".receipt"),c.toString().getBytes("UTF-8"));
        Files.write(Paths.get(c.getString("output")),prompt.equals("fixture-json")?"NOT_AUDIO".getBytes("UTF-8"):wave(48000,sound?1:2,1,16,48000));
        System.out.println(new JSONObject().put("event","progress").put("stage","fixture_protocol").put("step",1).put("steps",2));
        System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("hostFixture",true)));
        System.out.println(new JSONObject().put("event","complete").put("output",c.getString("output")));
    }
    public static void main(String[] args) throws Exception {
        if(args.length==2 && args[0].equals("child")){child(args[1]);return;}
        File root=new File(args[0]);root.mkdirs();RecipeCatalogue recipes=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")));AtomicInteger launches=new AtomicInteger();
        File binary=new File(System.getProperty("java.home"),"bin/java.exe");
        NativeWorker.Launcher launcher=b->{launches.incrementAndGet();return new ProcessBuilder(binary.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-cp",System.getProperty("java.class.path"),OpenMossTest.class.getName(),"child",b.command().get(1)).redirectErrorStream(true).start();};
        for(boolean sound:new boolean[]{false,true}) {
            String id=sound?"moss_soundeffect_v2_cpu_v1":"moss_local_v15_cpu_v1",type=sound?"audio.generate":"speech.synthesize";JSONObject template=recipes.template(id),raw=DataFiles.copy(template.getJSONObject("definition"));JSONArray components=new JSONArray();Map<String,File> files=new LinkedHashMap<>();
            check(template.getJSONArray("requirements").length()==2,"Exactly two explicit GGUF components");
            for(String role:Arrays.asList("backbone","extras")){File f=new File(root,id+role+".gguf");Files.write(f.toPath(),("NOT_A_MODEL_"+id+role).getBytes("UTF-8"));files.put(role,f);components.put(new JSONObject().put("role",role).put("path",role+".gguf").put("format","gguf").put("bytes",f.length()).put("sha256",DataFiles.sha256(f)));}
            ModelBundle bundle=new ModelBundle(raw.put("schema",ModelBundle.SCHEMA).put("id",id).put("modelId",id).put("recipeId",id).put("name","NOT A MODEL").put("components",components));OpenMossSpec.validate(bundle,type);check(true,"Exact engine contract accepted");
            for(String key:Arrays.asList("engine","pipeline","architecture","backend"))rejects(()->OpenMossSpec.validate(new ModelBundle(bundle.json().put(key,"other")),type),"Other architecture/backend rejected");
            rejects(()->OpenMossSpec.validate(bundle,sound?"speech.synthesize":"audio.generate"),"Task cannot cross family boundary");rejects(()->OpenMossSpec.validate(new ModelBundle(bundle.json().put("components",new JSONArray().put(components.getJSONObject(0)))),type),"Missing extras rejected");
            JSONObject limits=OpenMossSpec.schema(sound).getJSONObject("fields"),declared=template.getJSONObject("definition").getJSONObject("parameters").getJSONObject("fields");check(limits.keySet().equals(declared.keySet()),"Recipe and Java parameters match");
            for(String key:limits.keySet()) {
                JSONObject a=limits.getJSONObject(key),b=declared.getJSONObject(key);check(a.getString("type").equals(b.getString("type")) && a.getDouble("default")==b.getDouble("default") && a.getDouble("maximum")==b.getDouble("maximum") && a.getDouble("minimum")==b.getDouble("minimum"),"Editable defaults and bounds agree");
                check(OpenMossSpec.parameters(bundle,new JSONObject().put(key,a.getDouble("maximum")+100)).getJSONObject("values").getDouble(key)==a.getDouble("maximum"),"High bound clamps");check(OpenMossSpec.parameters(bundle,new JSONObject().put(key,a.getDouble("minimum")-100)).getJSONObject("values").getDouble(key)==a.getDouble("minimum"),"Low bound clamps");
            }
            File reference=new File(root,"reference.wav");Files.write(reference.toPath(),wave(48000,2,1,16,48000));OpenMossSpec.reference(reference);check(true,"Stereo PCM16 reference parsed");
            JSONObject inputRules=OpenMossSpec.inputs(bundle).json().getJSONObject("roles");check(sound?inputRules.length()==0:!inputRules.getJSONObject("reference_audio").getBoolean("required"),"Only Local offers optional reference");
            LmaApp app=new LmaApp(new File(root,id));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));app.bundles.declare(bundle);check(!app.bundles.record(id).getBoolean("installed"),"Catalogue declaration never downloads models");String token=app.bundles.request(id);
            for(ModelBundle.Component component:bundle.components){Files.copy(files.get(component.role).toPath(),app.bundles.partial(component.objectId).toPath(),StandardCopyOption.REPLACE_EXISTING);app.bundles.accept(id,token,component,app.bundles.partial(component.objectId));}app.bundles.install(id,token);
            OpenMossEngine engine=new OpenMossEngine(app,binary,new JSONObject().put("engine","openmoss_native"),launcher);JSONObject request=new JSONObject().put("bundleId",id).put("type",type).put("input",new JSONObject().put("prompt","fixture-wave")).put("parameters",new JSONObject()).put("allowUnmeasured",true),frozen=engine.prepare(bundle,request);
            JSONObject negative=DataFiles.copy(request);negative.getJSONObject("input").put("negativePrompt","negative fixture");if(sound)check(engine.prepare(bundle,negative).getJSONObject("input").getString("negativePrompt").equals("negative fixture"),"SoundEffect keeps negative prompt");else rejects(()->engine.prepare(bundle,negative),"Local does not silently ignore negative prompt");
            if(sound){JSONObject ignored=DataFiles.copy(negative);ignored.getJSONObject("parameters").put("cfgScale",1);rejects(()->engine.prepare(bundle,ignored),"CFG=1 cannot silently ignore a supplied negative prompt");}
            if(!sound)frozen.getJSONObject("input").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_audio").put("artifactId","fixture_reference")));
            AtomicInteger progress=new AtomicInteger();JSONObject execution=new JSONObject();File staging=new File(root,id+"-outputs");staging.mkdirs();
            try(BundleStore.Lease lease=app.bundles.acquire(id)) {
                LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return frozen;}public File input(String role){return reference;}public File output(String suffix){return new File(staging,UUID.randomUUID()+"."+suffix);}public void check(){}public void process(Process p){}public void progress(String s,Double f){progress.incrementAndGet();}public void execution(JSONObject v)throws Exception{execution.put("details",v);}};
                File out=engine.generate(context);JSONObject receipt=new JSONObject(new String(Files.readAllBytes(Paths.get(out.getPath()+".receipt")),"UTF-8"));check(WaveFile.inspect(out).getInt("channels")== (sound?1:2),"Production binding validates correct output channels");check(receipt.getJSONObject("parameters").getLong("seed")>=0,"Concrete seed reaches actual child");check(receipt.has("referenceAudio")==!sound,"Only explicit reference reaches child");check(receipt.getString("pipeline").equals(id),"Specific pipeline reaches child");check(progress.get()>0 && execution.getJSONObject("details").getBoolean("hostFixture"),"Shared protocol records progress and receipt");
                frozen.getJSONObject("input").put("prompt","fixture-json");rejects(()->engine.generate(context),"Non-audio output rejected");frozen.getJSONObject("input").put("prompt","fixture-error");rejects(()->engine.generate(context),"Actual child failure propagates");frozen.getJSONObject("parameters").put("threads",999);int before=launches.get();rejects(()->engine.generate(context),"Tampered snapshot rejected");check(before==launches.get(),"Invalid snapshot creates no child");
            }
            check(app.nativeProcess==null && new File(app.getFilesDir(),"engine-work").list().length==0,"Child ownership/workspace cleaned after success and failure");check(reference.isFile() && files.get("backbone").isFile() && files.get("extras").isFile(),"Original user assets preserved");
        }
        File bad=new File(root,"bad.wav");for(int[] f:new int[][]{{24000,2,1,16,48000},{48000,1,1,16,48000},{48000,2,1,32,48000},{48000,2,1,16,47999},{48000,2,1,16,480001}}){Files.write(bad.toPath(),wave(f[0],f[1],f[2],f[3],f[4]));rejects(()->OpenMossSpec.reference(bad),"Reference format/duration mismatch rejected");}
        Files.write(bad.toPath(),wave(48000,2,3,32,48000));OpenMossSpec.reference(bad);check(true,"Float32 stereo reference accepted");
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",launches.get()).put("production_openmoss_binding",true).put("model_inference",false).put("structural_wav_fixture",true));
    }
}
