package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.util.*;

/** Production model/asset/parameter/worker lifecycle; child outputs a fixture. */
final class MaterialTest {
    static void check(boolean value){ExpansionTest.check(value);}
    static void reject(ExpansionTest.Attempt action)throws Exception{ExpansionTest.rejects(action);}
    static JSONObject config()throws Exception{return new JSONObject().put("schema","lma.material-export/1").put("pipeline","hunyuan3d_21_paint").put("dtype","float32").put("opset",17)
        .put("source",new JSONObject().put("repository","Tencent-Hunyuan/Hunyuan3D-2.1").put("revision","82920d643c0dc2f7bfd7255f45f62d386edfe60c"))
        .put("views",6).put("imageSize",64).put("dinoSize",28).put("dinoResize",32).put("dinoWidth",1536).put("dinoTokens",5).put("vaeScaling",.18215).put("upscaleFactor",4)
        .put("scheduler","UniPCMultistepScheduler").put("timestepSpacing","trailing");}
    public static final class Worker {
        public static void main(String[] args)throws Exception {
            JSONObject c=ExpansionTest.read(new File(args[0]));File workspace=new File(c.getString("workspace"));
            MaterialSpec.checkConfig(ExpansionTest.read(new File(workspace,"material-config.json")));
            MaterialSpec.sourceMesh(new File(c.getString("sourceMesh")));RfShapeSpec.reference(new File(c.getString("referenceImage")));
            for(Iterator<String> it=c.getJSONObject("components").keys();it.hasNext();){String role=it.next();File f=new File(c.getJSONObject("components").getString(role));
                if(!f.getParentFile().equals(workspace)||!f.getName().equals(MaterialSpec.layout().get(role)))throw new IOException("Wrong material component staging");}
            System.out.println("{\"event\":\"execution\",\"details\":{\"fixture\":true}}");
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture failure\"}");System.exit(7);}
            if(c.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            File out=new File(c.getString("output"));ExpansionTest.glb(out,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",out.getPath()));
        }
    }
    static void run(File root,File run)throws Exception {
        JSONArray templates=ExpansionTest.read(new File(root,"app/src/main/assets/recipe-templates.json")).getJSONArray("templates");JSONObject t=null;int matches=0;
        for(int i=0;i<templates.length();i++)if(MaterialSpec.matches(templates.getJSONObject(i).getJSONObject("definition").getString("pipeline"))){matches++;t=templates.getJSONObject(i);}
        check(matches==1);JSONObject raw=DataFiles.copy(t.getJSONObject("definition")).put("schema","lma.model-bundle/2").put("id","material_fixture").put("modelId","material_fixture").put("recipeId",t.getString("id")).put("name","MATERIAL PROGRAM FIXTURE");
        Map<String,File> files=new LinkedHashMap<>();JSONArray components=new JSONArray();int index=0;
        for(Map.Entry<String,String> item:MaterialSpec.layout().entrySet()){
            File f=new File(run,"material-component-"+index++);String role=item.getKey();Files.write(f.toPath(),role.equals("config")?config().toString().getBytes("UTF-8"):new byte[]{1});files.put(role,f);
            components.put(new JSONObject().put("role",role).put("path",item.getValue()).put("format",role.equals("config")||role.equals("sampler")?"json":role.endsWith("_data")?"onnx_data":"onnx").put("bytes",f.length()).put("sha256",DataFiles.sha256(f)).put("url",""));
        }
        raw.put("components",components);ModelBundle bundle=new ModelBundle(raw);SpatialSpec.validate(bundle,"mesh.generate");check(true);
        for(String key:new String[]{"architecture","engine","pipeline","backend"}){JSONObject bad=DataFiles.copy(raw).put(key,"invalid");reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));}
        for(String key:new String[]{"views","imageSize","dinoSize","dinoResize","dinoWidth","dinoTokens","upscaleFactor"}){
            JSONObject bad=config().put(key,0);reject(()->MaterialSpec.checkConfig(bad));JSONObject fraction=config().put(key,1.5);reject(()->MaterialSpec.checkConfig(fraction));
        }
        for(String key:new String[]{"schema","scheduler","timestepSpacing"}){JSONObject bad=config().put(key,"invalid");reject(()->MaterialSpec.checkConfig(bad));}
        JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);reject(()->MaterialSpec.validate(new ModelBundle(missing),"mesh.generate"));
        File image=new File(run,"material.png"),mesh=new File(run,"material-source.glb"),exe=new File(System.getProperty("java.home"),"bin/java.exe");MultiViewTest.png(image,256,256,6);ExpansionTest.glb(mesh,ExpansionTest.geometry());
        JSONObject input=new JSONObject().put("prompt",SpatialSpec.PROMPT);JSONArray receipts=new JSONArray().put(new JSONObject().put("role","reference_image").put("bytes",29).put("metadata",new JSONObject().put("mime","image/png").put("width",256).put("height",256)));
        reject(()->MaterialSpec.inputs().validate(receipts,input));receipts.put(new JSONObject().put("role","source_mesh").put("bytes",mesh.length()).put("metadata",GlbFile.inspect(mesh)));MaterialSpec.inputs().validate(receipts,input);check(true);
        BundleStore store=new BundleStore(new File(run,"material-store"));store.declare(bundle);check(!store.plan(bundle.id).getBoolean("installed"));store.adoptLocal(bundle,files,new JSONObject(),()->{});
        LmaApp app=new LmaApp(new File(run,"material-app"));app.bundles=store;ExpansionEngine base=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"));
        JSONObject values=base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("steps",999).put("atlas",99999).put("guidance",999)).getJSONObject("values");check(values.getInt("steps")==100);check(values.getInt("atlas")==4096);check(values.getInt("guidance")==15);
        reject(()->base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("remote_url","https://example.invalid")));
        check(base.inputs(bundle,"mesh.generate").json().toString().contains("source_mesh"));
        try(BundleStore.Lease lease=store.acquire(bundle.id)){
            for(int mode=0;mode<3;mode++){
                final int variant=mode;final long started=System.nanoTime();final Process[] child={null};File output=new File(run,"material-output-"+mode+".glb");
                ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"),builder->{child[0]=new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",SpatialSpec.PROMPT).put("fixtureFail",mode==1).put("fixtureSlow",mode==2))
                    .put("parameters",engine.schema(bundle).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return role.equals("source_mesh")?mesh:image;}public File output(String suffix){return output;}
                    public void check()throws Exception{if(variant==2&&System.nanoTime()-started>600000000L)throw new IOException("Cancelled fixture");}public void progress(String stage,Double fraction){}public void process(Process p){}public void execution(JSONObject details){MaterialTest.check(details.getBoolean("fixture"));}};
                if(mode==0){engine.generate(context);check(output.isFile());}else{reject(()->engine.generate(context));check(!output.exists());}
                check(child[0]!=null&&!child[0].isAlive());check(app.nativeProcess==null);check(new File(app.getFilesDir(),"engine-work").list().length==0);
            }
        }
    }
}
