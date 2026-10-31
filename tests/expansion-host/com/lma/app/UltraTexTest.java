package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.util.*;

/** Actual exported random assets, Java staging, cancellation and cleanup. */
final class UltraTexTest {
    static void check(boolean v){ExpansionTest.check(v);}
    static void reject(ExpansionTest.Attempt f)throws Exception{ExpansionTest.rejects(f);}
    public static final class Worker {
        public static void main(String[] args)throws Exception{
            JSONObject c=ExpansionTest.read(new File(args[0]));String pipeline=c.getString("pipeline");File workspace=new File(c.getString("workspace"));
            UltraTexSpec.checkConfig(pipeline,ExpansionTest.read(new File(workspace,"ultratex-config.json")));
            if(!c.getString("prompt").equals(c.getJSONObject("input").getString("prompt")))throw new IOException("Lost material prompt");
            MaterialSpec.sourceMesh(new File(c.getString("sourceMesh")));RfShapeSpec.reference(new File(c.getString("referenceImage")));
            for(Iterator<String> it=c.getJSONObject("components").keys();it.hasNext();){String role=it.next();File f=new File(c.getJSONObject("components").getString(role));if(!f.getParentFile().equals(workspace)||!f.getName().equals(UltraTexSpec.layout(pipeline).get(role)))throw new IOException("Wrong UltraTex component staging");}
            System.out.println("{\"event\":\"execution\",\"details\":{\"fixture\":true}}");
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture failure\"}");System.exit(7);}
            if(c.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            File out=new File(c.getString("output"));ExpansionTest.glb(out,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",out.getPath()));
        }
    }
    static void run(File root,File run)throws Exception{
        for(String family:new String[]{"flux1","flux2"}){
            String pipeline="ultratex_"+family;File exported=new File(root,"build/ultratex-tests/"+family);JSONObject raw=ExpansionTest.read(new File(exported,"lma-bundle.json"));
            ModelBundle bundle=new ModelBundle(raw);SpatialSpec.validate(bundle,"mesh.generate");check(true);JSONObject config=ExpansionTest.read(new File(exported,"ultratex-config.json"));
            SpatialSpec.checkConfig(pipeline,config);check(true);
            for(String key:new String[]{"imageSize","latentChannels","textWidth","textVocab","textPad"}){
                JSONObject bad=DataFiles.copy(config).put(key,-1);reject(()->SpatialSpec.checkConfig(pipeline,bad));JSONObject fractional=DataFiles.copy(config).put(key,1.5);reject(()->SpatialSpec.checkConfig(pipeline,fractional));
            }
            for(String key:new String[]{"architecture","engine","pipeline","backend"}){JSONObject bad=DataFiles.copy(raw).put(key,"invalid");reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));}
            JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);reject(()->SpatialSpec.validate(new ModelBundle(missing),"mesh.generate"));
            Map<String,File> files=new LinkedHashMap<>();for(ModelBundle.Component c:bundle.components)files.put(c.role,new File(exported,c.path));
            File image=new File(root,"build/ultratex-tests/reference.png"),mesh=new File(root,"build/ultratex-tests/input.glb"),exe=new File(System.getProperty("java.home"),"bin/java.exe");
            JSONObject input=new JSONObject().put("prompt","blue ceramic object");JSONArray receipts=new JSONArray().put(new JSONObject().put("role","reference_image").put("bytes",image.length()).put("metadata",new JSONObject().put("mime","image/png").put("width",59).put("height",47)));
            reject(()->UltraTexSpec.inputs().validate(receipts,input));receipts.put(new JSONObject().put("role","source_mesh").put("bytes",mesh.length()).put("metadata",GlbFile.inspect(mesh)));UltraTexSpec.inputs().validate(receipts,input);check(true);
            BundleStore store=new BundleStore(new File(run,pipeline+"-store"));store.declare(bundle);check(!store.plan(bundle.id).getBoolean("installed"));store.adoptLocal(bundle,files,new JSONObject(),()->{});
            LmaApp app=new LmaApp(new File(run,pipeline+"-app"));app.bundles=store;ExpansionEngine base=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"));
            JSONObject values=base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("steps",999).put("guidance",999).put("atlas",99999)).getJSONObject("values");check(values.getInt("steps")==100&&values.getInt("atlas")==4096&&values.getInt("guidance")==15);
            reject(()->base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("remote_url","https://example.invalid")));
            check(!base.inputs(bundle,"mesh.generate").json().has("fixedPrompt"));check(!base.inputs(bundle,"mesh.generate").json().getBoolean("negativePrompt"));
            try(BundleStore.Lease lease=store.acquire(bundle.id)){
                for(int mode=0;mode<3;mode++){
                    final int variant=mode;final long[] started={Long.MAX_VALUE};final Process[] child={null};File output=new File(run,pipeline+"-"+mode+".glb");
                    ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"),builder->{child[0]=new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                    JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt","blue ceramic object").put("fixtureFail",mode==1).put("fixtureSlow",mode==2)).put("parameters",engine.schema(bundle).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                    LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return role.equals("source_mesh")?mesh:image;}public File output(String suffix){return output;}public void check()throws Exception{if(variant==2&&started[0]!=Long.MAX_VALUE&&System.nanoTime()-started[0]>600000000L)throw new IOException("Cancelled fixture");}public void progress(String stage,Double f){}public void process(Process p){if(p!=null)started[0]=System.nanoTime();}public void execution(JSONObject d){UltraTexTest.check(d.getBoolean("fixture"));}};
                    if(mode==0){engine.generate(context);check(output.isFile());}else{reject(()->engine.generate(context));check(!output.exists());}
                    check(child[0]!=null&&!child[0].isAlive());check(app.nativeProcess==null);check(new File(app.getFilesDir(),"engine-work").list().length==0);
                }
            }
        }
    }
}
