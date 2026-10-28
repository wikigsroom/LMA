package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Real production Java process/lease/input contracts; child WAVs here are structural fixtures. */
public final class SoulxTest {
    private static int passed;
    interface Action { void run() throws Exception; }
    static void check(boolean yes, String label) { if (!yes) throw new AssertionError(label); passed++; }
    static void rejects(Action action, String label) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(label); }
    static byte[] wave(int rate, int samples) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream(); DataOutputStream out = new DataOutputStream(bytes);
        out.writeBytes("RIFF"); out.writeInt(Integer.reverseBytes(36+samples*2)); out.writeBytes("WAVEfmt "); out.writeInt(Integer.reverseBytes(16)); out.writeShort(Short.reverseBytes((short)1)); out.writeShort(Short.reverseBytes((short)1)); out.writeInt(Integer.reverseBytes(rate)); out.writeInt(Integer.reverseBytes(rate*2)); out.writeShort(Short.reverseBytes((short)2)); out.writeShort(Short.reverseBytes((short)16)); out.writeBytes("data"); out.writeInt(Integer.reverseBytes(samples*2)); out.write(new byte[samples*2]); return bytes.toByteArray();
    }
    static void child(String file) throws Exception {
        JSONObject c = new JSONObject(new String(Files.readAllBytes(Paths.get(file)), "UTF-8")); Path workspace = Paths.get(c.getString("workspace"));
        for (String name : SoulxSpec.files().values()) if (!Files.isRegularFile(workspace.resolve("models/"+name))) throw new IOException("Missing explicit model asset");
        for (int i=1; i<=SoulxSpec.references(c.getJSONObject("input")); i++) if (!Files.isRegularFile(workspace.resolve("inputs/reference_s"+i+".wav"))) throw new IOException("Missing bound reference");
        String text = c.getJSONObject("input").getString("prompt");
        if (text.equals("fixture-wait")) { System.out.println("{\"event\":\"stage\",\"stage\":\"fixture_wait\"}"); System.out.flush(); Thread.sleep(60000); }
        if (text.equals("fixture-error")) { System.out.println("{\"event\":\"error\",\"message\":\"fixture error\"}"); System.exit(4); }
        Files.write(Paths.get(c.getString("output")+".receipt"),c.toString().getBytes("UTF-8"));
        Files.write(Paths.get(c.getString("output")),text.equals("fixture-json") ? "NOT_AUDIO".getBytes("UTF-8") : wave(text.equals("fixture-rate") ? 16000 : 24000,text.equals("fixture-duration") ? 24000*121 : 24000));
        System.out.println("{\"event\":\"execution\",\"details\":{\"hostFixture\":true}}"); System.out.println(new JSONObject().put("event","complete").put("output",c.getString("output")));
    }
    static JSONObject input(String id) { return new JSONObject().put("prompt","[S1] First.\n[S2] Second.").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_s1").put("artifactId",id)).put(new JSONObject().put("role","reference_s2").put("artifactId",id))).put("transcripts",new JSONObject().put("reference_s1","First reference.").put("reference_s2","Second reference.")); }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("child")) { child(args[1]); return; }
        File root = new File(args[0]); root.mkdirs(); RecipeCatalogue recipes = new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")));
        JSONObject template = recipes.template(SoulxSpec.PIPELINE), definition = DataFiles.copy(template.getJSONObject("definition")); JSONArray components = new JSONArray(); Map<String,File> files = new HashMap<>();
        for (Map.Entry<String,String> entry : SoulxSpec.files().entrySet()) {
            String role = entry.getKey(),name = entry.getValue(),format = role.equals("language") ? "gguf" : role.equals("hift_source") ? "bin" : role.endsWith("_data") ? "onnx_data" : "onnx";
            File f = new File(root,name); Files.write(f.toPath(),role.equals("hift_source") ? new byte[40] : ("NOT_A_MODEL_"+role).getBytes("UTF-8")); files.put(role,f);
            components.put(new JSONObject().put("role",role).put("path",name).put("format",format).put("bytes",f.length()).put("sha256",DataFiles.sha256(f)));
        }
        String id = "soulx_fixture"; ModelBundle b = new ModelBundle(definition.put("schema",ModelBundle.SCHEMA).put("id",id).put("modelId",id).put("recipeId",SoulxSpec.PIPELINE).put("name","NOT A MODEL").put("components",components)); SoulxSpec.validate(b,"speech.synthesize");check(components.length()==14,"all fourteen explicit assets");
        for (String field : Arrays.asList("engine","backend","pipeline","architecture")) rejects(()->SoulxSpec.validate(new ModelBundle(b.json().put(field,"other")),"speech.synthesize"),"wrong route");
        rejects(()->SoulxSpec.validate(b,"audio.generate"),"wrong task");
        for (int i=0;i<14;i++) { JSONArray missing = new JSONArray(); for(int j=0;j<14;j++)if(i!=j)missing.put(components.getJSONObject(j)); rejects(()->SoulxSpec.validate(new ModelBundle(b.json().put("components",missing)),"speech.synthesize"),"missing component"); }
        JSONObject fields = SoulxSpec.schema().getJSONObject("fields"), declared = definition.getJSONObject("parameters").getJSONObject("fields"); check(fields.keySet().equals(declared.keySet()),"parameter sets agree");
        for (String key : fields.keySet()) {
            JSONObject a=fields.getJSONObject(key),d=declared.getJSONObject(key); check(a.getString("type").equals(d.getString("type")) && (a.getString("type").equals("boolean") ? a.getBoolean("default")==d.getBoolean("default") : a.getDouble("default")==d.getDouble("default")),"schema type/default agrees");
            if(a.getString("type").equals("boolean")) { rejects(()->SoulxSpec.parameters(new JSONObject().put(key,"true")),"boolean cannot be a string"); continue; }
            check(a.getDouble("minimum")==d.getDouble("minimum") && a.getDouble("maximum")==d.getDouble("maximum"),"schema bounds agree");
            JSONObject low=SoulxSpec.parameters(new JSONObject().put(key,-9999999L)).getJSONObject("values"),high=SoulxSpec.parameters(new JSONObject().put(key,9999999999L)).getJSONObject("values");
            check(low.getDouble(key)>=a.getDouble("minimum") && high.getDouble(key)<=a.getDouble("maximum"),"bounded editable values");
            check(DataFiles.canonical(a.optJSONObject("maximumFrom")==null?new JSONObject():a.getJSONObject("maximumFrom")).equals(DataFiles.canonical(d.optJSONObject("maximumFrom")==null?new JSONObject():d.getJSONObject("maximumFrom"))),"dependent bounds agree");
        }
        JSONObject p=SoulxSpec.parameters(new JSONObject().put("context",256).put("maxNewTokens",3000).put("minNewTokens",2999).put("temperature",0).put("useRas",true)).getJSONObject("values");
        check(p.getInt("maxNewTokens")==192 && p.getInt("minNewTokens")==191 && p.getInt("historyThreshold")==256 && !p.getBoolean("useRas"),"context/output/greedy guards agree");
        rejects(()->SoulxSpec.parameters(new JSONObject().put("unknown",1)),"no ignored parameters");
        ArtifactStore artifacts = new ArtifactStore(new File(root,"artifacts"),WaveFile::inspect); JSONObject artifact = artifacts.importStream(new ByteArrayInputStream(wave(24000,24000)),"reference.wav",()->{}); String aid=artifact.getString("id");
        JSONObject request=new JSONObject().put("bundleId",id).put("type","speech.synthesize").put("input",input(aid)).put("parameters",new JSONObject()).put("allowUnmeasured",true);
        TaskInput.validate(request);check(SoulxSpec.turns(request.getJSONObject("input")).length()==2,"multispeaker parsed");
        for(String text:Arrays.asList("[S3] Missing.","[S0] Wrong.","[S1] First. [S2] Other.","[S1] First.\nNo tag.","<|task_podcast|>")) { JSONObject bad=DataFiles.copy(request.getJSONObject("input")).put("prompt",text);rejects(()->SoulxSpec.turns(bad),"bad utterance protocol"); }
        JSONObject pinned=InputSelection.prepare(artifacts,SoulxSpec.inputs(),TaskInput.validate(request));String fingerprint=TaskInput.fingerprint(pinned);request.getJSONObject("input").getJSONObject("transcripts").put("reference_s1","Edited later.");
        check(pinned.getJSONObject("input").getJSONObject("transcripts").getString("reference_s1").equals("First reference.") && TaskInput.fingerprint(pinned).equals(fingerprint),"transcript snapshot immutable");
        JSONObject bad=DataFiles.copy(pinned);bad.getJSONObject("input").remove("transcripts");rejects(()->InputSelection.acquire(artifacts,SoulxSpec.inputs(),bad,()->{}),"missing frozen transcript");
        JSONObject dangling=DataFiles.copy(pinned);dangling.getJSONObject("input").getJSONObject("transcripts").put("reference_s3","Dangling.");rejects(()->InputSelection.acquire(artifacts,SoulxSpec.inputs(),dangling,()->{}),"dangling transcript");
        JSONObject legacy=DataFiles.copy(pinned);rejects(()->InputSelection.prepare(artifacts,InputSpec.promptOnly(),legacy),"prompt-only rejects paired input");
        for(Object value:Arrays.asList("", " ", "a\0b", 12, JSONObject.NULL)) { JSONObject malformed=DataFiles.copy(request);malformed.getJSONObject("input").getJSONObject("transcripts").put("reference_s1",value);rejects(()->TaskInput.validate(malformed),"transcript shape bound"); }
        LmaApp app=new LmaApp(new File(root,"app"));app.bundles=new BundleStore(new File(app.getFilesDir(),"bundles"));app.bundles.declare(b);check(!app.bundles.record(id).getBoolean("installed"),"declare never downloads");String token=app.bundles.request(id);
        for(ModelBundle.Component component:b.components) { Files.copy(files.get(component.role).toPath(),app.bundles.partial(component.objectId).toPath(),StandardCopyOption.REPLACE_EXISTING);app.bundles.accept(id,token,component,app.bundles.partial(component.objectId)); }app.bundles.install(id,token);
        File binary=new File(System.getProperty("java.home"),"bin/java.exe"); AtomicInteger launches=new AtomicInteger();NativeWorker.Launcher launcher=builder->{launches.incrementAndGet();return new ProcessBuilder(binary.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),SoulxTest.class.getName(),"child",builder.command().get(1)).redirectErrorStream(true).start();};
        SoulxEngine engine=new SoulxEngine(app,binary,new JSONObject().put("engine","soulx_native"),launcher);JSONObject frozen=engine.prepare(b,pinned);check(pinned.getJSONObject("parameters").length()==0 && frozen.getJSONObject("parameters").getInt("context")==4096,"defaults do not save model profile");
        final boolean[] cancel={false};final Process[] child={null};JSONObject execution=new JSONObject();
        try(BundleStore.Lease lease=app.bundles.acquire(id);InputSelection.Selection selected=InputSelection.acquire(artifacts,SoulxSpec.inputs(),frozen,()->{})) {
            LocalEngine.Context c=new LocalEngine.Context() { public JSONObject request(){return DataFiles.copy(frozen);}public BundleStore.Lease model(){return lease;}public File input(String role)throws Exception{return selected.file(role);}public File output(String ext){return new File(root,"out."+ext);}public void check()throws Exception{if(cancel[0])throw new IOException("fixture cancellation");}public void process(Process p){child[0]=p;}public void progress(String stage,Double fraction){if(stage.equals("fixture_wait")){cancel[0]=true;child[0].destroyForcibly();}}public void execution(JSONObject x){execution.put("details",x);} };
            File output=engine.generate(c);JSONObject receipt=new JSONObject(new String(Files.readAllBytes(Paths.get(output.getPath()+".receipt")),"UTF-8"));check(WaveFile.inspect(output).getInt("sampleRate")==24000 && execution.getJSONObject("details").getBoolean("hostFixture"),"actual child/WAV protocol");
            check(receipt.getJSONObject("parameters").getInt("seed")>=0 && receipt.getJSONObject("input").getJSONObject("transcripts").getString("reference_s1").equals("First reference."),"seed and immutable transcripts forwarded");
            for(String text:Arrays.asList("fixture-json","fixture-rate","fixture-duration","fixture-error","fixture-wait")) { frozen.getJSONObject("input").put("prompt",text); rejects(()->engine.generate(c),"worker error/cancel/invalid output");cancel[0]=false;check(app.nativeProcess==null && new File(app.getFilesDir(),"engine-work").list().length==0,"child and workspace released"); }
            frozen.getJSONObject("parameters").put("maxNewTokens",4000);int before=launches.get();rejects(()->engine.generate(c),"tampered parameter snapshot");check(launches.get()==before,"invalid snapshot launches no worker");
        }
        for(File file:files.values())check(file.isFile(),"original explicit model assets preserved");
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",launches.get()).put("production_soulx_binding",true).put("model_inference",false).put("structural_wav_fixture",true));
    }
}
