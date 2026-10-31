package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;

/** Real production contracts and stores with synthetic data, never trained-model execution. */
public final class ExpansionTest {
    static int count;
    interface Attempt { void run() throws Exception; }
    static void check(boolean v) { if(!v)throw new AssertionError("Expansion check "+(count+1));count++; }
    static void rejects(Attempt fn) throws Exception { try { fn.run(); }catch(Exception expected){count++;return;}throw new AssertionError("Expected rejection "+(count+1)); }
    static JSONObject read(File file)throws Exception{return new JSONObject(new String(Files.readAllBytes(file.toPath()),"UTF-8"));}
    static JSONObject geometry()throws Exception {
        return new JSONObject("{\"asset\":{\"version\":\"2.0\"},\"buffers\":[{\"byteLength\":48}],\"bufferViews\":[{\"buffer\":0,\"byteOffset\":0,\"byteLength\":36},{\"buffer\":0,\"byteOffset\":36,\"byteLength\":12}],\"accessors\":[{\"bufferView\":0,\"componentType\":5126,\"count\":3,\"type\":\"VEC3\"},{\"bufferView\":1,\"componentType\":5125,\"count\":3,\"type\":\"SCALAR\"}],\"meshes\":[{\"primitives\":[{\"attributes\":{\"POSITION\":0},\"indices\":1}]}],\"nodes\":[{\"mesh\":0}],\"scenes\":[{\"nodes\":[0]}],\"scene\":0}");
    }
    static void glb(File file,JSONObject json)throws Exception {
        byte[] raw=json.toString().getBytes("UTF-8");int padding=(4-raw.length%4)%4,length=raw.length+padding;
        ByteBuffer b=ByteBuffer.allocate(28+length+48).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(0x46546c67).putInt(2).putInt(b.capacity()).putInt(length).putInt(0x4e4f534a).put(raw);
        for(int i=0;i<padding;i++)b.put((byte)' ');
        b.putInt(48).putInt(0x004e4942);
        for(float x:new float[]{-1,-1,0,1,-1,0,0,1,0})b.putFloat(x);
        b.putInt(0).putInt(1).putInt(2);Files.write(file.toPath(),b.array());
    }
    static void wav(File file)throws Exception {
        ByteBuffer b=ByteBuffer.allocate(48044).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(0x46464952).putInt(48036).putInt(0x45564157).putInt(0x20746d66).putInt(16).putShort((short)1).putShort((short)1)
         .putInt(24000).putInt(48000).putShort((short)2).putShort((short)16).putInt(0x61746164).putInt(48000);Files.write(file.toPath(),b.array());
    }
    public static final class Worker {
        public static void main(String[] args)throws Exception {
            JSONObject c=read(new File(args[0])), paths=c.getJSONObject("components");
            for(Iterator<String> it=paths.keys();it.hasNext();)if(!new File(paths.getString(it.next())).isFile())throw new IOException("Missing linked component");
            if(c.getString("pipeline").equals("omnivoice") && paths.has("audio_codec") && !new File(c.getString("workspace"),"audio_tokenizer/model.safetensors").isFile())throw new IOException("Codec layout missing");
            File output=new File(c.getString("output"));if(c.getString("type").equals("mesh.generate"))glb(output,geometry());else wav(output);
            System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("fixture",true).put("modelInference",false)));
            System.out.println(new JSONObject().put("event","complete").put("output",output.getPath()));
        }
    }
    public static void main(String[] args)throws Exception {
        File root=new File(args[0]),run=new File(args[1]);run.mkdirs();
        JSONArray bundles=read(new File(root,"catalogue/expansion-bundles.json")).getJSONArray("bundles");check(bundles.length()==11);
        File executable=new File(System.getProperty("java.home"),"bin/java.exe");LmaApp app=new LmaApp(new File(run,"app"));
        for(int i=0;i<bundles.length();i++) {
            JSONObject raw=bundles.getJSONObject(i);ModelBundle b=new ModelBundle(raw);boolean mesh=b.engine.equals("trellis_native"), audio=b.engine.equals("audio_cpp");
            String type=mesh?"mesh.generate":"speech.synthesize";
            if(mesh||audio) {
                ExpansionEngine engine=new ExpansionEngine(app,executable,new JSONObject().put("engine",b.engine));engine.validate(b,type);check(true);
                JSONObject normalized=engine.schema(b).normalize(new JSONObject(),new JSONObject()).getJSONObject("values");
                check(normalized.getInt("threads")==2);check(engine.inputs(b,type).json().getInt("version")==1);
                if(mesh){MeshSpec.assets(b,normalized);check(true);}
                JSONObject wrong=DataFiles.copy(raw).put("backend","cuda");rejects(()->engine.validate(new ModelBundle(wrong),type));
                JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);rejects(()->engine.validate(new ModelBundle(missing),type));
                JSONObject wide=DataFiles.copy(raw);wide.getJSONObject("parameters").getJSONObject("fields").getJSONObject("threads").put("maximum",9999).put("default",9999);
                check(engine.schema(new ModelBundle(wide)).normalize(new JSONObject(),new JSONObject()).getJSONObject("values").getInt("threads")==16);
                rejects(()->engine.validate(b,"image.generate"));
            }else {TtsSpec.validate(b,type);check(true);}
            BundleStore store=new BundleStore(new File(run,"declare-"+i));store.declare(b);check(!store.plan(b.id).getBoolean("installed"));check(store.snapshot().length()==1);
        }
        check(AudioCppSpec.parameters("f5_v1",new JSONObject().put("steps",999)).getJSONObject("values").getInt("steps")==64);
        check(AudioCppSpec.parameters("omnivoice",new JSONObject().put("durationSeconds",30).put("maxAudioSeconds",2)).getJSONObject("values").getInt("durationSeconds")==2);
        rejects(()->AudioCppSpec.parameters("omnivoice",new JSONObject().put("remote_url","https://example.invalid")));
        check(!MeshSpec.parameters("pixal3d",new JSONObject().put("texture",true).put("resolution",512)).getJSONObject("values").getBoolean("texture"));
        check(MeshSpec.parameters("trellis2",new JSONObject().put("resolution",768)).getJSONObject("values").getInt("resolution")==512);
        for(String family:Arrays.asList("f5_v1","omnivoice")){JSONObject p=AudioCppSpec.parameters(family,new JSONObject()).getJSONObject("values");check(p.getInt("steps")==32);check(p.getDouble("speed")==1);}
        JSONObject req=new JSONObject().put("bundleId","mesh_test").put("type","mesh.generate").put("input",new JSONObject().put("prompt","Generate a 3D asset from the selected local image.").put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_image").put("artifactId","input_test"))));
        check(TaskRequests.generation("mesh.generate"));TaskInput.validate(req);check(true);check(TaskRequests.replay(req).getString("type").equals("mesh.generate"));
        TaskDrafts drafts=new TaskDrafts(new File(run,"drafts"));drafts.save(req,0);check(new TaskDrafts(new File(run,"drafts")).summaries().length()==1);
        File valid=new File(run,"fixture.glb");glb(valid,geometry());JSONObject meta=GlbFile.inspect(valid);check(meta.getLong("triangles")==1);check(meta.getLong("vertices")==3);check(meta.getBoolean("selfContained"));
        byte[] good=Files.readAllBytes(valid.toPath());
        for(int length:new int[]{0,8,20,good.length-1}){Files.write(valid.toPath(),Arrays.copyOf(good,length));rejects(()->GlbFile.inspect(valid));}
        for(String error:Arrays.asList("bufferUri","imageUri","viewBounds","accessorBounds","stride","indicesType","positionType","primitiveMode","primitiveExtension","emptyMesh","version","sparse","textureMime")) {
            JSONObject v=geometry();
            if(error.equals("bufferUri"))v.getJSONArray("buffers").getJSONObject(0).put("uri","https://example.invalid/weights");
            if(error.equals("imageUri"))v.put("images",new JSONArray().put(new JSONObject().put("bufferView",0).put("uri","file:///private").put("mimeType","image/png")));
            if(error.equals("viewBounds"))v.getJSONArray("bufferViews").getJSONObject(0).put("byteOffset",100);
            if(error.equals("accessorBounds"))v.getJSONArray("accessors").getJSONObject(0).put("count",1000000);
            if(error.equals("stride"))v.getJSONArray("bufferViews").getJSONObject(0).put("byteStride",3);
            if(error.equals("indicesType"))v.getJSONArray("accessors").getJSONObject(1).put("componentType",5126);
            if(error.equals("positionType"))v.getJSONArray("accessors").getJSONObject(0).put("type","VEC2");
            if(error.equals("primitiveMode"))v.getJSONArray("meshes").getJSONObject(0).getJSONArray("primitives").getJSONObject(0).put("mode",1);
            if(error.equals("primitiveExtension"))v.getJSONArray("meshes").getJSONObject(0).getJSONArray("primitives").getJSONObject(0).put("extensions",new JSONObject());
            if(error.equals("emptyMesh"))v.put("meshes",new JSONArray());
            if(error.equals("version"))v.getJSONObject("asset").put("version","1.0");
            if(error.equals("sparse"))v.getJSONArray("accessors").getJSONObject(0).put("sparse",new JSONObject());
            if(error.equals("textureMime"))v.put("images",new JSONArray().put(new JSONObject().put("bufferView",0).put("mimeType","text/html")));
            glb(valid,v);rejects(()->GlbFile.inspect(valid));
        }
        glb(valid,geometry());
        ArtifactStore artifacts=new ArtifactStore(new File(run,"artifacts"),GlbFile::inspect);String job="job_"+String.join("",Collections.nCopies(32,"a"));File part=artifacts.staging(job,"glb");Files.copy(valid.toPath(),part.toPath());
        JSONObject record=artifacts.commit(job,part,new JSONObject().put("execution","same_android_phone"),()->{});check(record.getString("filename").endsWith(".glb"));check(artifacts.get(record.getString("id")).getJSONObject("metadata").getInt("triangles")==1);
        check(new ArtifactStore(new File(run,"artifacts"),GlbFile::inspect).file(record.getString("id")).exists());
        JSONObject wave=AudioCppSpec.inputs("f5_v1").json();check(wave.getJSONObject("roles").getJSONObject("reference_audio").getBoolean("required"));check(!AudioCppSpec.inputs("omnivoice").json().getJSONObject("roles").getJSONObject("reference_audio").getBoolean("required"));
        for(String variant:Arrays.asList("f5_v1","omnivoice","omnivoice_raw","trellis2","pixal3d")) {
            String pipeline=variant.equals("omnivoice_raw")?"omnivoice":variant;
            JSONObject raw=null;for(int i=0;i<bundles.length();i++)if(bundles.getJSONObject(i).getString("pipeline").equals(pipeline) && (!variant.equals("omnivoice_raw") || bundles.getJSONObject(i).getJSONArray("components").length()>1)){raw=DataFiles.copy(bundles.getJSONObject(i));break;}
            raw.put("id","fixture_"+variant);Map<String,File> files=new LinkedHashMap<>();
            for(int i=0;i<raw.getJSONArray("components").length();i++) {
                JSONObject c=raw.getJSONArray("components").getJSONObject(i);File file=new File(run,"component-"+i);Files.write(file.toPath(),new byte[]{(byte)i});
                c.remove("gitBlobSha1");c.remove("url");c.put("sha256",DataFiles.sha256(file)).put("bytes",1);files.put(c.getString("role"),file);
            }
            ModelBundle model=new ModelBundle(raw);BundleStore store=new BundleStore(new File(run,"engine-"+variant));store.adoptLocal(model,files,new JSONObject(),()->{});
            try(BundleStore.Lease lease=store.acquire(model.id)) {
                final boolean mesh=pipeline.equals("trellis2")||pipeline.equals("pixal3d");File reference=new File(run,pipeline+".wav");wav(reference);
                ExpansionEngine engine=new ExpansionEngine(app,executable,new JSONObject().put("engine",model.engine),builder-> {
                    check(builder.command().get(0).equals(executable.getPath()));
                    return new ProcessBuilder(executable.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();
                });
                JSONObject input=new JSONObject().put("prompt","Fixture prompt");if(pipeline.equals("f5_v1"))input.put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_audio"))).put("transcripts",new JSONObject().put("reference_audio","Fixture reference"));
                JSONObject request=new JSONObject().put("type",mesh?"mesh.generate":"speech.synthesize").put("input",input).put("parameters",engine.schema(model).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                final Process[] process={null};
                File output=engine.generate(new LocalEngine.Context() {
                    public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}
                    public File input(String role){return reference;}public File output(String suffix){return new File(run,UUID.randomUUID()+"."+suffix);}
                    public void check(){}public void progress(String stage,Double fraction){}public void process(Process value){process[0]=value;}
                    public void execution(JSONObject details){ExpansionTest.check(details.getBoolean("fixture"));}
                });
                check(output.isFile());check(process[0]!=null&&!process[0].isAlive());check(app.nativeProcess==null);
                check(new File(app.getFilesDir(),"engine-work").list().length==0);
                check((mesh?GlbFile.inspect(output):WaveFile.inspect(output)).has("mime"));
            }
        }
        MultiViewTest.run(root,run);
        System.out.println(new JSONObject().put("passed",count).put("model_inference",false).put("physical_device",false).put("complete_model_downloads",0).put("synthetic_glb",true).put("actual_host_child_processes",true));
    }
}
