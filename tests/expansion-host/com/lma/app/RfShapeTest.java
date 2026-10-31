package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.util.*;

/** Production store/adapter contracts; tiny files and owned Java child processes. */
final class RfShapeTest {
    static void check(boolean v){ExpansionTest.check(v);}
    static void reject(ExpansionTest.Attempt fn)throws Exception{ExpansionTest.rejects(fn);}
    public static final class Worker {
        public static void main(String[] args)throws Exception{
            JSONObject c=ExpansionTest.read(new File(args[0]));File output=new File(c.getString("output")),workspace=new File(c.getString("workspace"));
            if(!output.getParentFile().equals(workspace.getParentFile()))throw new IOException("Output escaped private workspace");
            JSONObject paths=c.getJSONObject("components");for(String role:RfShapeSpec.layout().keySet()){
                File file=new File(paths.getString(role));if(!file.getParentFile().equals(workspace)||!file.getName().equals(RfShapeSpec.layout().get(role))||!file.isFile())throw new IOException("Unmatched graph/data path");
            }
            RfShapeSpec.reference(new File(c.getString("referenceImage")));
            System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("fixture",true).put("parts",c.getJSONObject("parameters").getInt("parts"))));
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture error\"}");System.exit(7);}
            if(c.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            ExpansionTest.glb(output,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",c.getString("output")));
        }
    }
    static void run(File root,File run)throws Exception{
        JSONArray templates=ExpansionTest.read(new File(root,"app/src/main/assets/recipe-templates.json")).getJSONArray("templates");
        File exe=new File(System.getProperty("java.home"),"bin/java.exe"),image=new File(run,"shape-reference.png");MultiViewTest.png(image,256,256,6);
        LmaApp app=new LmaApp(new File(run,"shape-app"));int families=0;
        for(int t=0;t<templates.length();t++){
            JSONObject template=templates.getJSONObject(t);if(!template.getJSONObject("definition").optString("engine").equals("rf_shape_ort"))continue;families++;
            JSONObject raw=DataFiles.copy(template.getJSONObject("definition")).put("schema","lma.model-bundle/2").put("id","fixture_shape_"+families).put("modelId","fixture_shape_"+families).put("name","SHAPE PROGRAM FIXTURE");
            JSONArray components=new JSONArray();Map<String,File> selected=new LinkedHashMap<>();int number=0;
            for(Map.Entry<String,String> item:RfShapeSpec.layout().entrySet()){
                File f=new File(run,"shape-component-"+families+"-"+(number++));Files.write(f.toPath(),new byte[]{(byte)number});String role=item.getKey();
                components.put(new JSONObject().put("role",role).put("path",item.getValue()).put("format",role.equals("config")?"json":role.endsWith("_data")?"onnx_data":"onnx").put("bytes",1).put("sha256",DataFiles.sha256(f)).put("url",""));selected.put(role,f);
            }
            raw.put("recipeId",template.getString("id")).put("components",components);ModelBundle b=new ModelBundle(raw);RfShapeSpec.validate(b,"mesh.generate");check(true);
            BundleStore store=new BundleStore(new File(run,"shape-store-"+families));store.declare(b);check(!store.plan(b.id).getBoolean("installed"));
            JSONArray plan=store.plan(b.id).getJSONArray("components");for(int i=0;i<plan.length();i++)check(!plan.getJSONObject(i).getBoolean("downloadable"));
            for(String field:new String[]{"engine","pipeline","architecture","backend"}){JSONObject bad=DataFiles.copy(raw).put(field,"unknown");reject(()->RfShapeSpec.validate(new ModelBundle(bad),"mesh.generate"));}
            reject(()->RfShapeSpec.validate(b,"image.generate"));
            JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);reject(()->RfShapeSpec.validate(new ModelBundle(missing),"mesh.generate"));
            JSONObject wrong=DataFiles.copy(raw);wrong.getJSONArray("components").getJSONObject(1).put("format","safetensors");reject(()->RfShapeSpec.validate(new ModelBundle(wrong),"mesh.generate"));
            JSONObject named=DataFiles.copy(raw);named.getJSONArray("components").getJSONObject(0).put("path","other.json");reject(()->RfShapeSpec.validate(new ModelBundle(named),"mesh.generate"));
            JSONObject p=RfShapeSpec.parameters(b.pipeline,new JSONObject().put("parts",999).put("tokens",100000).put("grid",999).put("steps",999).put("threads",999)).getJSONObject("values");
            check(p.getInt("parts")==(!b.pipeline.equals("triposg")?16:1));check(p.getInt("tokens")==4096);check(p.getInt("grid")==256);check(p.getInt("steps")==100);check(p.getInt("threads")==16);
            reject(()->RfShapeSpec.parameters(b.pipeline,new JSONObject().put("remote_url","https://example.invalid")));
            RfShapeSpec.inputs().validate(new JSONArray().put(new JSONObject().put("role","reference_image").put("bytes",29).put("metadata",new JSONObject().put("mime","image/png").put("width",256).put("height",256))),new JSONObject().put("prompt",RfShapeSpec.PROMPT));check(true);
            store.adoptLocal(b,selected,new JSONObject(),()->{});
            try(BundleStore.Lease lease=store.acquire(b.id)){
                for(int mode=0;mode<3;mode++){
                    final int variant=mode;final Process[] child={null};final boolean[] measured={false};final long started=System.nanoTime();
                    ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","rf_shape_ort"),builder->{child[0]=new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                    JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",RfShapeSpec.PROMPT).put("fixtureFail",mode==1).put("fixtureSlow",mode==2))
                        .put("parameters",engine.schema(b).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                    File output=new File(run,"shape-result-"+families+"-"+mode+".glb");
                    LocalEngine.Context context=new LocalEngine.Context(){
                        public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return image;}public File output(String suffix){return suffix.equals("glb")?output:new File(output.getPath()+"."+suffix);}
                        public void check()throws Exception{if(variant==2&&System.nanoTime()-started>500000000L)throw new IOException("Fixture cancellation");}
                        public void process(Process p){}public void progress(String stage,Double f){}public void execution(JSONObject d){RfShapeTest.check(d.getBoolean("fixture"));measured[0]=true;}
                    };
                    if(mode==0){engine.generate(context);check(output.isFile());check(GlbFile.inspect(output).getInt("meshes")==1);check(measured[0]);}
                    else{reject(()->engine.generate(context));check(!output.exists());}
                    check(child[0]!=null&&!child[0].isAlive());check(new File(app.getFilesDir(),"engine-work").list().length==0);check(app.nativeProcess==null);
                }
            }
        }
        check(families==3);RfShapeSpec.reference(image);check(true);MultiViewTest.png(image,256,256,2);RfShapeSpec.reference(image);check(true);
        MultiViewTest.png(image,4096,4096,6);reject(()->RfShapeSpec.reference(image));MultiViewTest.png(image,256,256,3);reject(()->RfShapeSpec.reference(image));
    }
}
