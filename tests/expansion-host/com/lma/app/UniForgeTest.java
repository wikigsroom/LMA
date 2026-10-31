package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Production four-view staging, strict contracts, cancel/failure cleanup. */
final class UniForgeTest {
    static void check(boolean v){ExpansionTest.check(v);}
    static void reject(ExpansionTest.Attempt f)throws Exception{ExpansionTest.rejects(f);}
    public static final class Worker {
        public static void main(String[] args)throws Exception {
            JSONObject c=ExpansionTest.read(new File(args[0]));File workspace=new File(c.getString("workspace"));UniForgeSpec.checkConfig(ExpansionTest.read(new File(workspace,"uniforge-config.json")));
            File views=new File(c.getString("viewsDirectory"));for(String n:MultiViewSpec.FILES)RfShapeSpec.reference(new File(views,n));
            if(c.has("referenceImage")||c.has("sourceMesh"))throw new IOException("Incorrect UniForge input routing");
            for(Iterator<String> it=c.getJSONObject("components").keys();it.hasNext();){String role=it.next();File f=new File(c.getJSONObject("components").getString(role));if(!f.getParentFile().equals(workspace)||!f.getName().equals(UniForgeSpec.layout().get(role)))throw new IOException("Wrong UniForge staging");}
            System.out.println("{\"event\":\"execution\",\"details\":{\"fixture\":true}}");
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture failure\"}");System.exit(7);}
            if(c.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            File output=new File(c.getString("output"));ExpansionTest.glb(output,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",output.getPath()));
        }
    }
    static void run(File root,File run)throws Exception {
        File exported=new File(root,"build/uniforge-tests/bundle");JSONObject raw=ExpansionTest.read(new File(exported,"lma-bundle.json"));ModelBundle bundle=new ModelBundle(raw);
        SpatialSpec.validate(bundle,"mesh.generate");check(true);JSONObject config=ExpansionTest.read(new File(exported,"uniforge-config.json"));SpatialSpec.checkConfig(bundle.pipeline,config);check(true);
        for(String key:new String[]{"architecture","pipeline","engine","backend"}){JSONObject bad=DataFiles.copy(raw).put(key,"invalid");reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));}
        for(String key:new String[]{"views","structureChannels","decoderLevels","occupancyResolution","latentChannels"}){JSONObject bad=DataFiles.copy(config).put(key,-1);reject(()->SpatialSpec.checkConfig(bundle.pipeline,bad));}
        JSONObject bad=DataFiles.copy(raw);bad.getJSONArray("components").remove(0);reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));
        Map<String,File> files=new LinkedHashMap<>();for(ModelBundle.Component c:bundle.components)files.put(c.role,new File(exported,c.path));
        BundleStore store=new BundleStore(new File(run,"uniforge-store"));store.declare(bundle);check(!store.plan(bundle.id).getBoolean("installed"));store.adoptLocal(bundle,files,new JSONObject(),()->{});
        File exe=new File(System.getProperty("java.home"),"bin/java.exe");LmaApp app=new LmaApp(new File(run,"uniforge-app"));app.bundles=store;ExpansionEngine base=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"));
        JSONObject values=base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("shapeSteps",999).put("maxRows",999999).put("atlas",99999)).getJSONObject("values");check(values.getInt("shapeSteps")==100&&values.getInt("maxRows")==20000&&values.getInt("atlas")==4096);
        reject(()->base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("remote_url","https://example.invalid")));
        check(base.inputs(bundle,"mesh.generate").json().getJSONObject("roles").length()==4);JSONArray refs=new JSONArray();
        for(int n=0;n<4;n++){if(n>0)reject(()->UniForgeSpec.inputs().validate(refs,new JSONObject()));File image=new File(root,"build/uniforge-tests/views/"+MultiViewSpec.FILES[n]);refs.put(new JSONObject().put("role",MultiViewSpec.ROLES[n]).put("bytes",image.length()).put("metadata",new JSONObject().put("mime","image/png").put("width",32).put("height",32)));}
        UniForgeSpec.inputs().validate(refs,new JSONObject().put("prompt",MultiViewSpec.PROMPT));check(true);
        try(BundleStore.Lease lease=store.acquire(bundle.id)){
            for(int mode=0;mode<3;mode++){
                final int variant=mode;final long[] started={Long.MAX_VALUE};final Process[] child={null};File output=new File(run,"uniforge-"+mode+".glb");
                ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"),builder->{child[0]=new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",MultiViewSpec.PROMPT).put("fixtureFail",mode==1).put("fixtureSlow",mode==2)).put("parameters",engine.schema(bundle).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role)throws IOException{int index=Arrays.asList(MultiViewSpec.ROLES).indexOf(role);if(index<0)throw new IOException("Unexpected role");return new File(root,"build/uniforge-tests/views/"+MultiViewSpec.FILES[index]);}public File output(String suffix){return output;}public void check()throws Exception{if(variant==2&&started[0]!=Long.MAX_VALUE&&System.nanoTime()-started[0]>600000000L)throw new IOException("Cancelled fixture");}public void progress(String stage,Double f){}public void process(Process p){if(p!=null)started[0]=System.nanoTime();}public void execution(JSONObject d){UniForgeTest.check(d.getBoolean("fixture"));}};
                if(mode==0){engine.generate(context);check(output.isFile());}else{reject(()->engine.generate(context));check(!output.exists());}
                check(child[0]!=null&&!child[0].isAlive());check(app.nativeProcess==null);check(new File(app.getFilesDir(),"engine-work").list().length==0);
            }
        }
    }
}
