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
        boolean local=c.getString("pipeline").equals("moss_local_v15_cpu_v1");int rate=local || sound?48000:24000;
        if(c.has("referenceAudio"))OpenMossSpec.reference(new File(c.getString("referenceAudio")));
        if(c.has("referenceAudios"))for(int i=0;i<c.getJSONArray("referenceAudios").length();i++){JSONObject wav=WaveFile.inspect(new File(c.getJSONArray("referenceAudios").getString(i)));if(wav.getInt("sampleRate")!=24000 || wav.getInt("channels")!=1)throw new IOException("Delay reference layout mismatch");}
        if(prompt.contains("fixture-error")){System.out.println(new JSONObject().put("event","error").put("message","explicit fixture failure"));System.exit(3);}
        Files.write(Paths.get(c.getString("output")+".receipt"),c.toString().getBytes("UTF-8"));
        Files.write(Paths.get(c.getString("output")),prompt.contains("fixture-json")?"NOT_AUDIO".getBytes("UTF-8"):wave(rate,local?2:1,1,16,rate));
        System.out.println(new JSONObject().put("event","progress").put("stage","fixture_protocol").put("step",1).put("steps",2));
        System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("hostFixture",true)));
        System.out.println(new JSONObject().put("event","complete").put("output",c.getString("output")));
    }
    public static void main(String[] args) throws Exception {
        if(args.length==2 && args[0].equals("child")){child(args[1]);return;}
        File root=new File(args[0]);root.mkdirs();RecipeCatalogue recipes=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")));AtomicInteger launches=new AtomicInteger();
        File binary=new File(System.getProperty("java.home"),"bin/java.exe");
        NativeWorker.Launcher launcher=b->{launches.incrementAndGet();return new ProcessBuilder(binary.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-cp",System.getProperty("java.class.path"),OpenMossTest.class.getName(),"child",b.command().get(1)).redirectErrorStream(true).start();};
        for(String id:Arrays.asList("moss_local_v15_cpu_v1","moss_soundeffect_v2_cpu_v1","moss_tts_openmoss_cpu_v1","moss_tts_v15_openmoss_cpu_v1","moss_ttsd_openmoss_cpu_v1","moss_voicegen_openmoss_cpu_v1")) {
            boolean sound=id.equals("moss_soundeffect_v2_cpu_v1");String type=sound?"audio.generate":"speech.synthesize";JSONObject template=recipes.template(id),raw=DataFiles.copy(template.getJSONObject("definition"));JSONArray components=new JSONArray();Map<String,File> files=new LinkedHashMap<>();
            check(template.getJSONArray("requirements").length()==2,"Exactly two explicit GGUF components");
            for(String role:Arrays.asList("backbone","extras")){File f=new File(root,id+role+".gguf");Files.write(f.toPath(),("NOT_A_MODEL_"+id+role).getBytes("UTF-8"));files.put(role,f);components.put(new JSONObject().put("role",role).put("path",role+".gguf").put("format","gguf").put("bytes",f.length()).put("sha256",DataFiles.sha256(f)));}
            ModelBundle bundle=new ModelBundle(raw.put("schema",ModelBundle.SCHEMA).put("id",id).put("modelId",id).put("recipeId",id).put("name","NOT A MODEL").put("components",components));OpenMossSpec.validate(bundle,type);check(true,"Exact engine contract accepted");
            for(String key:Arrays.asList("engine","pipeline","architecture","backend"))rejects(()->OpenMossSpec.validate(new ModelBundle(bundle.json().put(key,"other")),type),"Other architecture/backend rejected");
            rejects(()->OpenMossSpec.validate(bundle,sound?"speech.synthesize":"audio.generate"),"Task cannot cross family boundary");rejects(()->OpenMossSpec.validate(new ModelBundle(bundle.json().put("components",new JSONArray().put(components.getJSONObject(0)))),type),"Missing extras rejected");
            JSONObject limits=OpenMossSpec.schema(bundle).getJSONObject("fields"),declared=template.getJSONObject("definition").getJSONObject("parameters").getJSONObject("fields");check(limits.keySet().equals(declared.keySet()),"Recipe and Java parameters match");
            for(String key:limits.keySet()) {
                JSONObject a=limits.getJSONObject(key),b=declared.getJSONObject(key);
                if(a.getString("type").equals("string")) {check(a.getString("type").equals(b.getString("type")) && a.getString("default").equals(b.getString("default")) && a.getInt("maxLength")==b.getInt("maxLength"),"String schema/default/length agree");rejects(()->OpenMossSpec.parameters(bundle,new JSONObject().put(key,String.join("",Collections.nCopies(a.getInt("maxLength")+1,"x")))),"Oversized instruction rejected");rejects(()->OpenMossSpec.parameters(bundle,new JSONObject().put(key,"<|im_end|>")),"Instruction cannot inject template marker");continue;}
                check(a.getString("type").equals(b.getString("type")) && a.getDouble("default")==b.getDouble("default") && a.getDouble("maximum")==b.getDouble("maximum") && a.getDouble("minimum")==b.getDouble("minimum"),"Editable defaults and bounds agree");
                check(OpenMossSpec.parameters(bundle,new JSONObject().put(key,a.getDouble("maximum")+100)).getJSONObject("values").getDouble(key)==a.getDouble("maximum"),"High bound clamps");check(OpenMossSpec.parameters(bundle,new JSONObject().put(key,a.getDouble("minimum")-100)).getJSONObject("values").getDouble(key)==a.getDouble("minimum"),"Low bound clamps");
            }
            File reference=new File(root,id+"-reference.wav");Files.write(reference.toPath(),wave(OpenMossSpec.sampleRate(bundle),OpenMossSpec.channels(bundle),1,16,OpenMossSpec.sampleRate(bundle)));OpenMossSpec.reference(bundle,reference);check(true,"Profile-specific PCM16 reference parsed");
            JSONObject inputRules=OpenMossSpec.inputs(bundle).json().getJSONObject("roles");check(inputRules.length()==OpenMossSpec.referenceRoles(bundle).size(),"Reference forms match profile roles");
            LmaApp app=new LmaApp(new File(root,id));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));app.bundles.declare(bundle);check(!app.bundles.record(id).getBoolean("installed"),"Catalogue declaration never downloads models");String token=app.bundles.request(id);
            for(ModelBundle.Component component:bundle.components){Files.copy(files.get(component.role).toPath(),app.bundles.partial(component.objectId).toPath(),StandardCopyOption.REPLACE_EXISTING);app.bundles.accept(id,token,component,app.bundles.partial(component.objectId));}app.bundles.install(id,token);
            String prefix=OpenMossSpec.dialogue(bundle)?"[S1] Hello. [S2] ":"";
            OpenMossEngine engine=new OpenMossEngine(app,binary,new JSONObject().put("engine","openmoss_native"),launcher);JSONObject request=new JSONObject().put("bundleId",id).put("type",type).put("input",new JSONObject().put("prompt",prefix+"fixture-wave")).put("parameters",new JSONObject()).put("allowUnmeasured",true);
            if(OpenMossSpec.voice(bundle)){rejects(()->engine.prepare(bundle,request),"Voice design requires an explicit instruction");request.getJSONObject("parameters").put("voiceInstruction","A warm lower-pitched adult voice.");}
            if(OpenMossSpec.delay(bundle)){request.getJSONObject("parameters").put("language","English");rejects(()->OpenMossSpec.text(bundle,new JSONObject().put("prompt","[S3] wrong")),"Unknown speaker rejected");}
            JSONObject frozen=engine.prepare(bundle,request);check(request.getJSONObject("parameters").length()==(OpenMossSpec.voice(bundle)?2:OpenMossSpec.delay(bundle)?1:0),"Preparing a snapshot does not mutate selected model values");
            JSONObject negative=DataFiles.copy(request);negative.getJSONObject("input").put("negativePrompt","negative fixture");if(sound)check(engine.prepare(bundle,negative).getJSONObject("input").getString("negativePrompt").equals("negative fixture"),"SoundEffect keeps negative prompt");else rejects(()->engine.prepare(bundle,negative),"Local does not silently ignore negative prompt");
            if(sound){JSONObject ignored=DataFiles.copy(negative);ignored.getJSONObject("parameters").put("cfgScale",1);rejects(()->engine.prepare(bundle,ignored),"CFG=1 cannot silently ignore a supplied negative prompt");}
            if(!OpenMossSpec.referenceRoles(bundle).isEmpty()){JSONArray refs=new JSONArray();List<String> reversed=new ArrayList<>(OpenMossSpec.referenceRoles(bundle));Collections.reverse(reversed);for(String role:reversed)refs.put(new JSONObject().put("role",role).put("artifactId","fixture_"+role));frozen.getJSONObject("input").put("artifacts",refs);}
            if(OpenMossSpec.dialogue(bundle)){JSONObject one=DataFiles.copy(frozen);one.getJSONObject("input").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_audio_s2")));rejects(()->engine.prepare(bundle,one),"A lone second speaker reference is rejected before launch");rejects(()->OpenMossSpec.text(bundle,new JSONObject().put("prompt","[S1] only")),"TTSD needs both speaker text segments");}
            AtomicInteger progress=new AtomicInteger();JSONObject execution=new JSONObject();File staging=new File(root,id+"-outputs");staging.mkdirs();
            try(BundleStore.Lease lease=app.bundles.acquire(id)) {
                LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return frozen;}public File input(String role){return reference;}public File output(String suffix){return new File(staging,UUID.randomUUID()+"."+suffix);}public void check(){}public void process(Process p){}public void progress(String s,Double f){progress.incrementAndGet();}public void execution(JSONObject v)throws Exception{execution.put("details",v);}};
                File out=engine.generate(context);JSONObject receipt=new JSONObject(new String(Files.readAllBytes(Paths.get(out.getPath()+".receipt")),"UTF-8"));check(WaveFile.inspect(out).getInt("channels")==OpenMossSpec.channels(bundle) && WaveFile.inspect(out).getInt("sampleRate")==OpenMossSpec.sampleRate(bundle),"Production binding validates correct output layout");check(receipt.getJSONObject("parameters").getLong("seed")>=0,"Concrete seed reaches actual child");check(receipt.has("referenceAudio")==(!sound && !OpenMossSpec.delay(bundle)),"Only explicit stereo reference reaches child");check(receipt.optJSONArray("referenceAudios")==null?OpenMossSpec.referenceRoles(bundle).isEmpty() || !OpenMossSpec.delay(bundle):receipt.getJSONArray("referenceAudios").length()==OpenMossSpec.referenceRoles(bundle).size(),"Delay speaker reference count reaches child");
                if(OpenMossSpec.dialogue(bundle))check(receipt.getJSONArray("referenceAudios").getString(0).endsWith("reference_audio_s1.wav") && receipt.getJSONArray("referenceAudios").getString(1).endsWith("reference_audio_s2.wav"),"Reversed input array preserves explicit S1/S2 mapping");
                if(OpenMossSpec.voice(bundle))check(receipt.getJSONObject("parameters").getString("voiceInstruction").contains("warm"),"Voice instruction reaches actual child");
                check(receipt.getString("pipeline").equals(id),"Specific pipeline reaches child");check(progress.get()>0 && execution.getJSONObject("details").getBoolean("hostFixture"),"Shared protocol records progress and receipt");
                frozen.getJSONObject("input").put("prompt",prefix+"fixture-json");rejects(()->engine.generate(context),"Non-audio output rejected");frozen.getJSONObject("input").put("prompt",prefix+"fixture-error");rejects(()->engine.generate(context),"Actual child failure propagates");frozen.getJSONObject("parameters").put("threads",999);int before=launches.get();rejects(()->engine.generate(context),"Tampered snapshot rejected");check(before==launches.get(),"Invalid snapshot creates no child");
            }
            check(app.nativeProcess==null && new File(app.getFilesDir(),"engine-work").list().length==0,"Child ownership/workspace cleaned after success and failure");check(reference.isFile() && files.get("backbone").isFile() && files.get("extras").isFile(),"Original user assets preserved");
        }
        File bad=new File(root,"bad.wav");for(int[] f:new int[][]{{24000,2,1,16,48000},{48000,1,1,16,48000},{48000,2,1,32,48000},{48000,2,1,16,47999},{48000,2,1,16,480001}}){Files.write(bad.toPath(),wave(f[0],f[1],f[2],f[3],f[4]));rejects(()->OpenMossSpec.reference(bad),"Reference format/duration mismatch rejected");}
        Files.write(bad.toPath(),wave(48000,2,3,32,48000));OpenMossSpec.reference(bad);check(true,"Float32 stereo reference accepted");
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",launches.get()).put("production_openmoss_binding",true).put("model_inference",false).put("structural_wav_fixture",true));
    }
}
