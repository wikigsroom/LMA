package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.util.*;

/** Real production import/schema/adapter/child-lifetime contracts, no learned weights. */
final class SpatialTest {
    static void check(boolean b){ExpansionTest.check(b);}
    static void reject(ExpansionTest.Attempt a)throws Exception{ExpansionTest.rejects(a);}
    static JSONObject config(String pipeline)throws Exception {
        boolean u=SpatialSpec.ultra(pipeline);
        return new JSONObject().put("schema","lma.spatial-shape-export/1").put("pipeline",pipeline).put("dtype","float32").put("opset",17)
            .put("source",new JSONObject().put("repository",u?"PKU-YuanGroup/UltraShape-1.0":"Tencent-Hunyuan/Hunyuan3D-2.1")
                .put("revision",u?"5e8dcef05df101ab00ab6cd5fdd0ed0c74fbca66":"82920d643c0dc2f7bfd7255f45f62d386edfe60c"))
            .put("latentChannels",4).put("decoderWidth",16).put("imageSize",28).put("processorSize",32).put("encoderTokens",5).put("encoderWidth",8)
            .put("maxTokens",512).put("voxelResolution",128).put("scheduleShift",1).put("borderRatio",.15).put("boxExtent",1.01);
    }
    public static final class Worker {
        public static void main(String[] args)throws Exception {
            JSONObject c=ExpansionTest.read(new File(args[0]));String pipeline=c.getString("pipeline");
            File workspace=new File(c.getString("workspace")),output=new File(c.getString("output"));
            if(!output.getParentFile().equals(workspace.getParentFile()))throw new IOException("Output escaped private workspace");
            for(Iterator<String> it=c.getJSONObject("components").keys();it.hasNext();){String role=it.next();File file=new File(c.getJSONObject("components").getString(role));
                if(!file.isFile()||!file.getParentFile().equals(workspace)||!file.getName().equals(SpatialSpec.layout().get(role)))throw new IOException("Wrong selected component path");}
            SpatialSpec.readConfig(pipeline,new File(workspace,"spatial-config.json"));
            RfShapeSpec.reference(new File(c.getString("referenceImage")));
            if(SpatialSpec.ultra(pipeline))SpatialSpec.coarse(new File(c.getString("coarseMesh")));
            System.out.println("{\"event\":\"execution\",\"details\":{\"fixture\":true}}");
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture failed\"}");System.exit(7);}
            if(c.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            ExpansionTest.glb(output,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",output.getPath()));
        }
    }
    static void run(File root,File run)throws Exception {
        JSONArray templates=ExpansionTest.read(new File(root,"app/src/main/assets/recipe-templates.json")).getJSONArray("templates");
        File image=new File(run,"spatial.png"),coarse=new File(run,"coarse.glb"),exe=new File(System.getProperty("java.home"),"bin/java.exe");
        MultiViewTest.png(image,256,256,6);ExpansionTest.glb(coarse,ExpansionTest.geometry());
        ArtifactStore artifacts=new ArtifactStore(new File(run,"spatial-inputs"),GlbFile::inspect);
        JSONObject imported;try(InputStream in=new FileInputStream(coarse)){imported=artifacts.importStream(in,"coarse.glb",()->{});}
        check(imported.getJSONObject("metadata").getString("mime").equals(GlbFile.MIME));check(imported.getString("filename").endsWith(".glb"));
        check(imported.getJSONObject("origin").getString("kind").equals("imported"));
        int families=0;
        for(int i=0;i<templates.length();i++){
            JSONObject t=templates.getJSONObject(i);if(!t.getJSONObject("definition").getString("engine").equals("spatial_ort"))continue;families++;
            JSONObject raw=DataFiles.copy(t.getJSONObject("definition")).put("schema","lma.model-bundle/2").put("id","fixture_spatial_"+families)
                .put("modelId","fixture_spatial_"+families).put("recipeId",t.getString("id")).put("name","SPATIAL PROGRAM FIXTURE");
            String pipeline=raw.getString("pipeline");boolean ultra=SpatialSpec.ultra(pipeline);JSONObject cfg=config(pipeline);
            Map<String,File> files=new LinkedHashMap<>();JSONArray components=new JSONArray();int n=0;
            for(Map.Entry<String,String> item:SpatialSpec.layout().entrySet()){
                File f=new File(run,"spatial-component-"+families+"-"+(n++));String role=item.getKey();
                Files.write(f.toPath(),role.equals("config")?cfg.toString().getBytes("UTF-8"):new byte[]{(byte)n});files.put(role,f);
                components.put(new JSONObject().put("role",role).put("path",item.getValue()).put("format",role.equals("config")?"json":role.endsWith("_data")?"onnx_data":"onnx")
                    .put("bytes",f.length()).put("sha256",DataFiles.sha256(f)).put("url",""));
            }
            raw.put("components",components);ModelBundle b=new ModelBundle(raw);SpatialSpec.validate(b,"mesh.generate");check(true);
            BundleStore store=new BundleStore(new File(run,"spatial-store-"+families));store.declare(b);check(!store.plan(b.id).getBoolean("installed"));
            for(String key:new String[]{"engine","architecture","pipeline","backend"}){JSONObject wrong=DataFiles.copy(raw).put(key,"other");reject(()->SpatialSpec.validate(new ModelBundle(wrong),"mesh.generate"));}
            JSONObject wrong=DataFiles.copy(raw);wrong.getJSONArray("components").getJSONObject(0).put("path","other.json");reject(()->SpatialSpec.validate(new ModelBundle(wrong),"mesh.generate"));
            JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);reject(()->SpatialSpec.validate(new ModelBundle(missing),"mesh.generate"));
            for(String key:new String[]{"latentChannels","decoderWidth","imageSize","processorSize","encoderTokens","encoderWidth","maxTokens","voxelResolution"}){
                JSONObject bad=DataFiles.copy(cfg).put(key,0);reject(()->SpatialSpec.checkConfig(pipeline,bad));
                final JSONObject fractional=DataFiles.copy(cfg).put(key,1.5);reject(()->SpatialSpec.checkConfig(pipeline,fractional));
            }
            JSONObject pin=DataFiles.copy(cfg);pin.getJSONObject("source").put("revision",String.join("",Collections.nCopies(40,"0")));reject(()->SpatialSpec.checkConfig(pipeline,pin));
            JSONObject input=new JSONObject().put("prompt",SpatialSpec.PROMPT);JSONArray receipts=new JSONArray().put(new JSONObject().put("role","reference_image").put("bytes",29).put("metadata",new JSONObject().put("mime","image/png").put("width",256).put("height",256)));
            if(ultra){reject(()->SpatialSpec.inputs(pipeline).validate(receipts,input));receipts.put(new JSONObject().put("role","coarse_mesh").put("bytes",coarse.length()).put("metadata",GlbFile.inspect(coarse)));}
            SpatialSpec.inputs(pipeline).validate(receipts,input);check(true);
            reject(()->SpatialSpec.inputs(pipeline).validate(receipts,new JSONObject().put("prompt",SpatialSpec.PROMPT).put("negativePrompt","not accepted")));
            store.adoptLocal(b,files,new JSONObject(),()->{});LmaApp app=new LmaApp(new File(run,"spatial-app-"+families));app.bundles=store;
            ExpansionEngine base=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"));
            check(base.schema(b).json().getJSONObject("fields").getJSONObject("tokens").getInt("maximum")==512);
            JSONObject normal=base.schema(b).normalize(new JSONObject(),new JSONObject().put("tokens",32768).put("steps",999).put("grid",999)).getJSONObject("values");
            check(normal.getInt("tokens")==512);check(normal.getInt("steps")==100);check(normal.getInt("grid")==256);
            reject(()->base.schema(b).normalize(new JSONObject(),new JSONObject().put("remote_url","https://example.invalid")));
            try(BundleStore.Lease lease=store.acquire(b.id)){
                for(int mode=0;mode<3;mode++){
                    final int variant=mode;final long started=System.nanoTime();final Process[] child={null};
                    ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"),builder->{
                        child[0]=new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                    JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",SpatialSpec.PROMPT).put("fixtureFail",mode==1).put("fixtureSlow",mode==2))
                        .put("parameters",engine.schema(b).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                    File output=new File(run,"spatial-result-"+families+"-"+mode+".glb");
                    LocalEngine.Context ctx=new LocalEngine.Context(){
                        public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return role.equals("coarse_mesh")?coarse:image;}
                        public File output(String suffix){return output;}public void check()throws Exception{if(variant==2&&System.nanoTime()-started>500000000L)throw new IOException("Fixture cancellation");}
                        public void process(Process p){}public void progress(String s,Double d){}public void execution(JSONObject details){SpatialTest.check(details.getBoolean("fixture"));}
                    };
                    if(mode==0){engine.generate(ctx);check(output.isFile());check(GlbFile.inspect(output).getInt("triangles")==1);}
                    else{reject(()->engine.generate(ctx));check(!output.exists());}
                    check(child[0]!=null&&!child[0].isAlive());check(new File(app.getFilesDir(),"engine-work").list().length==0);check(app.nativeProcess==null);
                }
            }
        }
        check(families==2);
    }
}
