package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Actual child protocol with structural silent WAV fixtures; no neural audio inference. */
public final class StableAudioTest {
    private static int passed;
    interface Action {void run() throws Exception;}
    static void check(boolean value,String label){if(!value)throw new AssertionError(label);passed++;}
    static void rejects(Action action,String label)throws Exception{try{action.run();}catch(Exception expected){passed++;return;}throw new AssertionError(label);}
    static byte[] wave(int rate,int channels,int seconds)throws Exception{
        ByteArrayOutputStream b=new ByteArrayOutputStream();DataOutputStream o=new DataOutputStream(b);int length=rate*channels*2*seconds;o.writeBytes("RIFF");o.writeInt(Integer.reverseBytes(36+length));o.writeBytes("WAVEfmt ");o.writeInt(Integer.reverseBytes(16));o.writeShort(Short.reverseBytes((short)1));o.writeShort(Short.reverseBytes((short)channels));o.writeInt(Integer.reverseBytes(rate));o.writeInt(Integer.reverseBytes(rate*channels*2));o.writeShort(Short.reverseBytes((short)(channels*2)));o.writeShort(Short.reverseBytes((short)16));o.writeBytes("data");o.writeInt(Integer.reverseBytes(length));o.write(new byte[length]);return b.toByteArray();
    }
    static void child(String file)throws Exception{
        JSONObject c=new JSONObject(new String(Files.readAllBytes(Paths.get(file)),"UTF-8"));Path workspace=Paths.get(c.getString("workspace"));
        for(String role:Arrays.asList("conditioner","diffusion_model","audio_decoder","tokenizer"))if(!Files.isRegularFile(workspace.resolve("models/"+role+(role.equals("tokenizer")?".model":".tflite"))))throw new IOException("Missing explicit component");
        String prompt=c.getJSONObject("input").getString("prompt");
        if(prompt.equals("fixture-wait")){System.out.println("{\"event\":\"stage\",\"stage\":\"fixture_wait\"}");System.out.flush();Thread.sleep(60000);}
        if(prompt.equals("fixture-error")){System.out.println("{\"event\":\"error\",\"message\":\"fixture error\"}");System.exit(4);}
        Files.write(Paths.get(c.getString("output")+".receipt"),c.toString().getBytes("UTF-8"));
        Files.write(Paths.get(c.getString("output")),prompt.equals("fixture-json")?"NOT_AUDIO".getBytes("UTF-8"):wave(prompt.equals("fixture-rate")?24000:44100,2,prompt.equals("fixture-duration")?1:c.getJSONObject("parameters").getInt("seconds")));
        System.out.println("{\"event\":\"progress\",\"stage\":\"fixture_protocol\",\"step\":1,\"steps\":2}");System.out.println("{\"event\":\"execution\",\"details\":{\"hostFixture\":true}}");System.out.println(new JSONObject().put("event","complete").put("output",c.getString("output")));
    }
    public static void main(String[] args)throws Exception{
        if(args[0].equals("child")){child(args[1]);return;}
        File root=new File(args[0]);root.mkdirs();RecipeCatalogue recipes=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")));String id=StableAudioSpec.PIPELINE;
        JSONObject t=recipes.template(id),definition=DataFiles.copy(t.getJSONObject("definition"));JSONArray components=new JSONArray();Map<String,File> files=new HashMap<>();
        for(String role:Arrays.asList("conditioner","diffusion_model","audio_decoder","tokenizer")){
            String format=role.equals("tokenizer")?"sentencepiece":"tflite",path=role+(role.equals("tokenizer")?".model":".tflite");File f=new File(root,path);Files.write(f.toPath(),("NOT_A_MODEL_"+role).getBytes("UTF-8"));files.put(role,f);components.put(new JSONObject().put("role",role).put("path",path).put("format",format).put("bytes",f.length()).put("sha256",DataFiles.sha256(f)));
        }
        ModelBundle b=new ModelBundle(definition.put("schema",ModelBundle.SCHEMA).put("id",id).put("modelId",id).put("recipeId",id).put("name","NOT A MODEL").put("components",components));StableAudioSpec.validate(b,"audio.generate");check(true,"matching recipe");
        for(String key:Arrays.asList("engine","backend","pipeline","architecture"))rejects(()->StableAudioSpec.validate(new ModelBundle(b.json().put(key,"other")),"audio.generate"),"wrong route");
        rejects(()->StableAudioSpec.validate(b,"speech.synthesize"),"wrong task");rejects(()->StableAudioSpec.validate(new ModelBundle(b.json().put("components",new JSONArray().put(components.getJSONObject(0)))),"audio.generate"),"missing dependencies");
        JSONObject nativeFields=StableAudioSpec.schema().getJSONObject("fields"),declared=definition.getJSONObject("parameters").getJSONObject("fields");check(nativeFields.keySet().equals(declared.keySet()),"schema fields agree");
        for(String key:nativeFields.keySet()){
            JSONObject a=nativeFields.getJSONObject(key),d=declared.getJSONObject(key);check(a.getString("type").equals(d.getString("type")) && a.getDouble("default")==d.getDouble("default") && a.getDouble("minimum")==d.getDouble("minimum") && a.getDouble("maximum")==d.getDouble("maximum"),"schema matches");
            check(StableAudioSpec.parameters(new JSONObject().put(key,9999999999L)).getJSONObject("values").getDouble(key)==a.getDouble("maximum"),"upper clamp");check(StableAudioSpec.parameters(new JSONObject().put(key,-999L)).getJSONObject("values").getDouble(key)==a.getDouble("minimum"),"lower clamp");
        }
        for(JSONObject bad:Arrays.asList(new JSONObject().put("prompt",""),new JSONObject().put("prompt"," \n"),new JSONObject().put("prompt","a\0b"),new JSONObject().put("prompt","rain").put("negativePrompt","noise"),new JSONObject().put("prompt","rain").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_audio")))))rejects(()->StableAudioSpec.text(bad),"unsupported text/conditioning");
        rejects(()->StableAudioSpec.parameters(new JSONObject().put("cfgScale",7)),"no ignored CFG");
        LmaApp app=new LmaApp(new File(root,"app"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));app.bundles.declare(b);check(!app.bundles.record(id).getBoolean("installed"),"declare never downloads");String token=app.bundles.request(id);
        for(ModelBundle.Component component:b.components){Files.copy(files.get(component.role).toPath(),app.bundles.partial(component.objectId).toPath(),StandardCopyOption.REPLACE_EXISTING);app.bundles.accept(id,token,component,app.bundles.partial(component.objectId));}app.bundles.install(id,token);
        File binary=new File(System.getProperty("java.home"),"bin/java.exe");AtomicInteger launches=new AtomicInteger();NativeWorker.Launcher launcher=builder->{launches.incrementAndGet();return new ProcessBuilder(binary.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),StableAudioTest.class.getName(),"child",builder.command().get(1)).redirectErrorStream(true).start();};
        StableAudioEngine engine=new StableAudioEngine(app,binary,new JSONObject().put("engine","stable_audio_litert"),launcher);
        JSONObject request=new JSONObject().put("bundleId",id).put("type","audio.generate").put("input",new JSONObject().put("prompt","fixture-wave")).put("parameters",new JSONObject()).put("allowUnmeasured",true),frozen=engine.prepare(b,request);
        check(request.getJSONObject("parameters").length()==0 && frozen.getJSONObject("parameters").getInt("seconds")==5,"task defaults do not save settings");check(engine.inputs(b,"audio.generate").json().getJSONObject("roles").length()==0,"no reference field");
        final boolean[] cancel={false};final Process[] child={null};JSONObject execution=new JSONObject();AtomicInteger events=new AtomicInteger();
        try(BundleStore.Lease lease=app.bundles.acquire(id)){
            LocalEngine.Context c=new LocalEngine.Context(){public JSONObject request(){return DataFiles.copy(frozen);}public BundleStore.Lease model(){return lease;}public File output(String ext){return new File(root,"out."+ext);}public void check()throws Exception{if(cancel[0])throw new IOException("fixture cancelled");}public void process(Process process){child[0]=process;}public void progress(String stage,Double fraction){events.incrementAndGet();if(stage.equals("fixture_wait")){cancel[0]=true;child[0].destroyForcibly();}}public void execution(JSONObject value){execution.put("details",value);}};
            File out=engine.generate(c);JSONObject receipt=new JSONObject(new String(Files.readAllBytes(Paths.get(out.getPath()+".receipt")),"UTF-8"));check(WaveFile.inspect(out).getLong("samples")==5*44100 && WaveFile.inspect(out).getInt("channels")==2,"matching output WAV");check(receipt.getString("pipeline").equals(id) && receipt.getJSONObject("parameters").getLong("seed")>=0,"concrete seed forwarded");check(events.get()>0 && execution.getJSONObject("details").getBoolean("hostFixture"),"protocol events delivered");
            for(String text:Arrays.asList("fixture-json","fixture-error","fixture-rate","fixture-duration","fixture-wait")){frozen.getJSONObject("input").put("prompt",text);rejects(()->engine.generate(c),"invalid output/error/cancel");cancel[0]=false;check(app.nativeProcess==null && new File(app.getFilesDir(),"engine-work").list().length==0,"child and workspace released");}
            frozen.getJSONObject("parameters").put("seconds",12);int before=launches.get();rejects(()->engine.generate(c),"tampered snapshot rejected");check(launches.get()==before,"bad snapshot spawns no child");
        }
        for(File file:files.values())check(file.isFile(),"explicit assets preserved");
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",launches.get()).put("production_stable_audio_binding",true).put("model_inference",false).put("structural_wav_fixture",true));
    }
}
