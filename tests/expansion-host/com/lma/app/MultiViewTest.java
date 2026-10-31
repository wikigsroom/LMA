package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;

/** Production contracts with tiny synthetic assets and owned Java child processes. */
final class MultiViewTest {
    static void check(boolean v){ExpansionTest.check(v);}
    static void rejects(ExpansionTest.Attempt fn)throws Exception{ExpansionTest.rejects(fn);}
    static JSONObject camera()throws Exception{
        JSONArray f=new JSONArray();for(int i=0;i<4;i++)f.put(new JSONObject().put("camera_angle_x",Math.PI/9).put("transform_matrix",new JSONArray("[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]")));
        return new JSONObject().put("frames",f);
    }
    static void png(File f,int w,int h,int color)throws Exception{
        ByteBuffer b=ByteBuffer.allocate(29).order(ByteOrder.BIG_ENDIAN);b.putLong(0x89504e470d0a1a0aL).putInt(13).putInt(0x49484452).putInt(w).putInt(h).put((byte)8).put((byte)color).put(new byte[]{0,0,0});Files.write(f.toPath(),b.array());
    }
    public static final class Worker {
        public static void main(String[] args)throws Exception{
            JSONObject c=ExpansionTest.read(new File(args[0]));File views=new File(c.getString("viewsDirectory"));
            if(!c.getString("pipeline").equals("pixal3d_mv"))throw new IOException("Wrong pipeline");
            for(String name:MultiViewSpec.FILES)MultiViewSpec.reference(new File(views,name));
            if(views.list().length!=4)throw new IOException("Wrong view layout");
            File out=new File(c.getString("output"));if(!out.getParentFile().equals(views.getParentFile()))throw new IOException("Output escaped owned workspace");
            Files.write(new File(out.getParentFile(),"sidecar.ply").toPath(),new byte[]{1});
            System.out.println(new JSONObject().put("event","stage").put("stage","loading_views"));
            System.out.println(new JSONObject().put("event","execution").put("details",new JSONObject().put("fixture",true).put("views",4)));
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println(new JSONObject().put("event","error").put("message","Explicit program fixture failure"));System.exit(9);}
            ExpansionTest.glb(out,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",c.getString("output")));
        }
    }
    static void run(File root,File run)throws Exception{
        JSONArray bundles=ExpansionTest.read(new File(root,"catalogue/multiview-bundles.json")).getJSONArray("bundles");check(bundles.length()==4);
        File exe=new File(System.getProperty("java.home"),"bin/java.exe");LmaApp app=new LmaApp(new File(run,"mv-app"));
        for(int i=0;i<bundles.length();i++){
            ModelBundle b=new ModelBundle(bundles.getJSONObject(i));MultiViewSpec.validate(b,"mesh.generate");check(true);
            boolean texture=b.id.contains("pbr");check(b.components.size()==(texture?9:7));MultiViewSpec.assets(b,MultiViewSpec.parameters(new JSONObject().put("texture",texture)).getJSONObject("values"));check(true);
            if(!texture)rejects(()->MultiViewSpec.assets(b,new JSONObject().put("texture",true)));
            BundleStore store=new BundleStore(new File(run,"mv-plan-"+i));store.declare(b);check(!store.plan(b.id).getBoolean("installed"));
            JSONArray plan=store.plan(b.id).getJSONArray("components");for(int j=0;j<plan.length();j++)check(!plan.getJSONObject(j).getBoolean("downloadable"));
        }
        JSONObject raw=DataFiles.copy(bundles.getJSONObject(0));
        for(String key:Arrays.asList("engine","pipeline","architecture","backend")){JSONObject bad=DataFiles.copy(raw).put(key,"other");rejects(()->MultiViewSpec.validate(new ModelBundle(bad),"mesh.generate"));}
        JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);rejects(()->MultiViewSpec.validate(new ModelBundle(missing),"mesh.generate"));
        rejects(()->MultiViewSpec.validate(new ModelBundle(raw),"image.generate"));
        JSONObject p=MultiViewSpec.parameters(new JSONObject().put("maxTokens",999999).put("steps",9999).put("resolution",512).put("seed",-1)).getJSONObject("values");
        check(p.getInt("maxTokens")==49152);check(p.getInt("steps")==50);check(p.getInt("resolution")==1024);check(p.getInt("seed")==1);rejects(()->MultiViewSpec.parameters(new JSONObject().put("remote_url","https://example.invalid")));
        MultiViewSpec.cameras("");MultiViewSpec.cameras(camera().toString());check(true);
        for(String variant:Arrays.asList("count","field","fov","fov_string","shape","scale","reflection","origin","affine","number")){
            JSONObject c=camera(),f=c.getJSONArray("frames").getJSONObject(0);JSONArray m=f.getJSONArray("transform_matrix");
            if(variant.equals("count"))c.getJSONArray("frames").remove(0);if(variant.equals("field"))f.put("file_path","https://example.invalid");
            if(variant.equals("fov"))f.put("camera_angle_x",Math.PI);if(variant.equals("fov_string"))f.put("camera_angle_x","0.5");if(variant.equals("shape"))m.remove(0);
            if(variant.equals("scale"))m.getJSONArray(0).put(0,2);if(variant.equals("reflection"))m.getJSONArray(0).put(0,-1);if(variant.equals("origin"))m.getJSONArray(2).put(3,0);
            if(variant.equals("affine"))m.getJSONArray(3).put(0,1);if(variant.equals("number"))m.getJSONArray(1).put(0,"1");rejects(()->MultiViewSpec.cameras(c.toString()));
        }
        InputSpec spec=MultiViewSpec.inputs();JSONArray receipts=new JSONArray();JSONObject input=new JSONObject().put("prompt",MultiViewSpec.PROMPT);
        for(String role:MultiViewSpec.ROLES)receipts.put(new JSONObject().put("role",role).put("bytes",100).put("metadata",new JSONObject().put("mime","image/png").put("width",512).put("height",512)));
        spec.validate(receipts,input);check(true);JSONArray three=new JSONArray(receipts.toString());three.remove(0);rejects(()->spec.validate(three,input));
        JSONArray jpg=new JSONArray(receipts.toString());jpg.getJSONObject(0).getJSONObject("metadata").put("mime","image/jpeg");rejects(()->spec.validate(jpg,input));rejects(()->spec.validate(receipts,new JSONObject().put("prompt","arbitrary prompt")));
        File view=new File(run,"mv-view.png");png(view,512,512,6);MultiViewSpec.reference(view);check(true);
        for(int color:new int[]{0,2,3,4}){png(view,512,512,color);rejects(()->MultiViewSpec.reference(view));}png(view,4096,4096,6);rejects(()->MultiViewSpec.reference(view));png(view,512,512,6);
        raw.put("id","fixture_mv");Map<String,File> components=new LinkedHashMap<>();
        for(int i=0;i<raw.getJSONArray("components").length();i++){JSONObject c=raw.getJSONArray("components").getJSONObject(i);File f=new File(run,"mv-component-"+i);Files.write(f.toPath(),new byte[]{(byte)i});c.put("bytes",1).put("sha256",DataFiles.sha256(f)).put("url","");components.put(c.getString("role"),f);}
        ModelBundle model=new ModelBundle(raw);BundleStore store=new BundleStore(new File(run,"mv-engine"));store.adoptLocal(model,components,new JSONObject(),()->{});
        try(BundleStore.Lease lease=store.acquire(model.id)){
            for(boolean fail:new boolean[]{false,true}){
                final Process[] child={null};final boolean[] measured={false};
                ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","pixal_multiview"),builder->new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start());
                JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",MultiViewSpec.PROMPT).put("fixtureFail",fail)).put("parameters",MultiViewSpec.parameters(new JSONObject().put("texture",false)).getJSONObject("values"));
                LocalEngine.Context context=new LocalEngine.Context(){
                    public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return view;}
                    public File output(String suffix){return new File(run,UUID.randomUUID()+"."+suffix);}public void check(){}public void progress(String s,Double f){}
                    public void process(Process value){child[0]=value;}public void execution(JSONObject details){measured[0]=details.optBoolean("fixture");}
                };
                if(fail)rejects(()->engine.generate(context));else check(GlbFile.inspect(engine.generate(context)).getInt("triangles")==1);
                check(measured[0]);check(child[0]!=null&&!child[0].isAlive());check(app.nativeProcess==null);check(new File(app.getFilesDir(),"engine-work").list().length==0);
            }
        }
        diagnostics(run);
    }
    static void diagnostics(File run)throws Exception{
        JSONObject request=new JSONObject().put("bundleId","fixture_mv").put("type","mesh.generate").put("input",new JSONObject().put("prompt",MultiViewSpec.PROMPT));
        File file=new File(run,"execution-jobs.json");JobStore store=new JobStore(file);JSONObject job=store.submit(request,""),claim=store.claimNext();String id=job.getString("id"),token=claim.getString("token");
        JSONObject details=new JSONObject().put("pipeline","pixal3d_mv").put("runtimeMeasurements",new JSONObject().put("elapsedMs",30));
        store.recordExecution(id,token,details);details.put("pipeline","mutated");check(store.get(id).getJSONObject("engineExecution").getString("pipeline").equals("pixal3d_mv"));
        store.recordExecution(id,token,new JSONObject().put("backend","cpu"));
        JSONObject merged=store.recordExecution(id,token,new JSONObject().put("runtimeMeasurements",new JSONObject().put("elapsedMs",30)));
        check(merged.getString("pipeline").equals("pixal3d_mv"));check(merged.getString("backend").equals("cpu"));
        merged.put("pipeline","external mutation");check(store.get(id).getJSONObject("engineExecution").getString("pipeline").equals("pixal3d_mv"));
        store.recordExecution(id,token,new JSONObject().put("largeA",String.join("",Collections.nCopies(8500,"x"))));
        rejects(()->store.recordExecution(id,token,new JSONObject().put("largeB",String.join("",Collections.nCopies(8500,"x")))));
        check(!store.get(id).getJSONObject("engineExecution").has("largeB"));
        rejects(()->store.recordExecution(id,"stale",details));rejects(()->store.recordExecution(id,token,new JSONObject().put("oversized",String.join("",Collections.nCopies(16001,"x")))));
        store.finish(id,token,new JSONArray(),"explicit fixture failure");check(store.get(id).getString("state").equals("failed"));check(new JobStore(file).get(id).getJSONObject("engineExecution").getJSONObject("runtimeMeasurements").getInt("elapsedMs")==30);rejects(()->store.recordExecution(id,token,details));
        JSONArray jobs=new JSONArray();for(int i=0;i<75;i++)jobs.put(new JSONObject().put("id","job_"+i).put("bundleId","fixture_mv").put("state","failed").put("startedAt",100).put("finishedAt",150)
            .put("request",new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt","PRIVATE_SENTINEL")))
            .put("engineExecution",new JSONObject().put("pipeline","pixal3d_mv").put("parameters","PRIVATE_SENTINEL").put("runtimeMeasurements",new JSONObject().put("elapsedMs",40).put("path","PRIVATE_SENTINEL").put("stages",new JSONArray().put(new JSONObject().put("stage","loading_views").put("elapsedMs",20).put("prompt","PRIVATE_SENTINEL"))))));
        JSONObject report=RuntimeDiagnostics.report(new JSONObject().put("jobs",jobs).put("settings",new JSONObject().put("apiKey","PRIVATE_SENTINEL")),"program-fixture");
        check(report.getJSONArray("jobs").length()==64);check(report.getJSONArray("jobs").getJSONObject(0).getString("id").equals("job_11"));check(!report.toString().contains("PRIVATE_SENTINEL"));check(report.getJSONArray("jobs").getJSONObject(0).getLong("wallElapsedMs")==50);
        check(!report.getJSONArray("jobs").getJSONObject(0).getJSONObject("worker").getJSONObject("runtimeMeasurements").getBoolean("qualityAssessed"));check(!TaskRequests.replay(store.get(id).getJSONObject("request")).has("engineExecution"));
    }
}
