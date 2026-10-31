package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Production staging and process lifecycle with a declared Java IO fixture. */
final class SupraTest {
    static void check(boolean v){ExpansionTest.check(v);}
    static void reject(ExpansionTest.Attempt f)throws Exception{ExpansionTest.rejects(f);}
    public static final class Worker {
        public static void main(String[] args)throws Exception {
            JSONObject c=ExpansionTest.read(new File(args[0]));File workspace=new File(c.getString("workspace"));SupraSpec.checkConfig(ExpansionTest.read(new File(workspace,"supra-config.json")));
            SupraSpec.reference(new File(c.getString("referenceImage")));SupraSpec.camera(new File(c.getString("camera")));MaterialSpec.sourceMesh(new File(c.getString("sourceMesh")));
            if(c.has("viewsDirectory")||c.has("coarseMesh"))throw new IOException("Wrong SUPRA input routing");
            for(Iterator<String> it=c.getJSONObject("components").keys();it.hasNext();){String role=it.next();File file=new File(c.getJSONObject("components").getString(role));if(!file.getParentFile().equals(workspace)||!file.getName().equals(SupraSpec.layout().get(role)))throw new IOException("Wrong SUPRA component staging");}
            System.out.println("{\"event\":\"execution\",\"details\":{\"fixture\":true}}");
            if(c.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture failure\"}");System.exit(8);}
            if(c.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            File output=new File(c.getString("output"));ExpansionTest.glb(output,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",output.getPath()));
        }
    }
    static void run(File root,File run)throws Exception {
        File exported=new File(root,"build/supra-tests/bundle");JSONObject raw=ExpansionTest.read(new File(exported,"lma-bundle.json"));ModelBundle bundle=new ModelBundle(raw);
        SpatialSpec.validate(bundle,"mesh.generate");check(true);JSONObject config=ExpansionTest.read(new File(exported,"supra-config.json"));SpatialSpec.checkConfig(bundle.pipeline,config);check(true);
        for(String key:new String[]{"architecture","pipeline","engine","backend"}){JSONObject bad=DataFiles.copy(raw).put(key,"invalid");reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));}
        for(String key:new String[]{"resolution","latentChannels","decoderLevels","opset"})for(double n:new double[]{-1,1.5}){JSONObject bad=DataFiles.copy(config).put(key,n);reject(()->SpatialSpec.checkConfig(bundle.pipeline,bad));}
        JSONObject bad=DataFiles.copy(raw);bad.getJSONArray("components").remove(0);reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));
        JSONObject badConfig=DataFiles.copy(config);badConfig.getJSONObject("qwen").getJSONArray("tokenIds").put(0,-1);reject(()->SpatialSpec.checkConfig(bundle.pipeline,badConfig));
        SupraSpec.reference(new File(root,"build/supra-tests/reference.png"));SupraSpec.camera(new File(root,"build/supra-tests/camera.txt"));check(true);
        File camera=new File(run,"invalid-camera.txt");java.nio.file.Files.write(camera.toPath(),new JSONObject().put("distance",-1).put("camera_angle_x",1).toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));reject(()->SupraSpec.camera(camera));
        Map<String,File> files=new LinkedHashMap<>();for(ModelBundle.Component component:bundle.components)files.put(component.role,new File(exported,component.path));
        BundleStore store=new BundleStore(new File(run,"supra-store"));store.declare(bundle);check(!store.plan(bundle.id).getBoolean("installed"));store.adoptLocal(bundle,files,new JSONObject(),()->{});
        File exe=new File(System.getProperty("java.home"),"bin/java.exe");LmaApp app=new LmaApp(new File(run,"supra-app"));app.bundles=store;
        ExpansionEngine base=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"));JSONObject values=base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("steps",999).put("maxRows",999999).put("atlas",999999)).getJSONObject("values");check(values.getInt("steps")==100&&values.getInt("maxRows")==20000&&values.getInt("atlas")==4096);
        reject(()->base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("remote_url","https://invalid.example")));
        InputSpec inputs=base.inputs(bundle,"mesh.generate");check(inputs.json().getJSONObject("roles").length()==3);JSONArray refs=new JSONArray();
        String[] roles={"reference_image","source_mesh","camera"},names={"reference.png","source.glb","camera.txt"},mimes={"image/png",GlbFile.MIME,StructuredInput.MIME};
        for(int i=0;i<roles.length;i++){reject(()->inputs.validate(refs,new JSONObject().put("prompt",SpatialSpec.PROMPT)));File file=new File(root,"build/supra-tests/"+names[i]);JSONObject metadata=new JSONObject().put("mime",mimes[i]);if(i==0)metadata.put("width",1024).put("height",1024);refs.put(new JSONObject().put("role",roles[i]).put("bytes",file.length()).put("metadata",metadata));}
        inputs.validate(refs,new JSONObject().put("prompt",SpatialSpec.PROMPT));check(true);
        try(BundleStore.Lease lease=store.acquire(bundle.id)){
            for(int mode=0;mode<3;mode++){
                final int variant=mode;final long[] started={Long.MAX_VALUE};final Process[] child={null};File output=new File(run,"supra-"+mode+".glb");
                ExpansionEngine engine=new ExpansionEngine(app,exe,new JSONObject().put("engine","spatial_ort"),builder->{child[0]=new ProcessBuilder(exe.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",SpatialSpec.PROMPT).put("fixtureFail",mode==1).put("fixtureSlow",mode==2)).put("parameters",engine.schema(bundle).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role)throws IOException{int index=Arrays.asList(roles).indexOf(role);if(index<0)throw new IOException("Unexpected input role");return new File(root,"build/supra-tests/"+names[index]);}public File output(String suffix){return output;}public void check()throws Exception{if(variant==2&&started[0]!=Long.MAX_VALUE&&System.nanoTime()-started[0]>600000000L)throw new IOException("Cancelled fixture");}public void progress(String stage,Double f){}public void process(Process p){if(p!=null)started[0]=System.nanoTime();}public void execution(JSONObject d){SupraTest.check(d.getBoolean("fixture"));}};
                if(mode==0){engine.generate(context);check(output.isFile());}else{reject(()->engine.generate(context));check(!output.exists());}
                check(child[0]!=null&&!child[0].isAlive());check(app.nativeProcess==null);check(new File(app.getFilesDir(),"engine-work").list().length==0);
            }
        }
    }
}
