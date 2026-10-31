package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** App import/schema/staging/lifetime contracts with declared synthetic IO. */
final class SamTest {
    static void check(boolean value){ExpansionTest.check(value);}
    static void reject(ExpansionTest.Attempt f)throws Exception{ExpansionTest.rejects(f);}
    public static final class Worker {
        public static void main(String[] args)throws Exception {
            JSONObject command=ExpansionTest.read(new File(args[0]));String pipeline=command.getString("pipeline");File workspace=new File(command.getString("workspace"));
            SpatialSpec.readConfig(pipeline,new File(workspace,"sam-config.json"));
            if(SamSpec.multi(pipeline)){for(String name:MultiViewSpec.FILES)MultiViewSpec.reference(new File(command.getString("viewsDirectory"),name));if(command.has("referenceImage"))throw new IOException("Wrong multiview routing");}
            else {MultiViewSpec.reference(new File(command.getString("referenceImage")));if(command.has("viewsDirectory"))throw new IOException("Wrong single-view routing");}
            if(command.has("sourceMesh")||command.has("coarseMesh")||command.has("camera"))throw new IOException("Unexpected SAM inputs");
            for(Iterator<String> it=command.getJSONObject("components").keys();it.hasNext();){String role=it.next();File file=new File(command.getJSONObject("components").getString(role));if(!file.isFile()||!file.getParentFile().equals(workspace)||!file.getName().equals(SamSpec.layout(pipeline).get(role)))throw new IOException("Incorrect SAM component staging");}
            System.out.println("{\"event\":\"execution\",\"details\":{\"fixture\":true}}");
            if(command.getJSONObject("input").optBoolean("fixtureFail")){System.out.println("{\"event\":\"error\",\"message\":\"Fixture failure\"}");System.exit(8);}
            if(command.getJSONObject("input").optBoolean("fixtureSlow"))Thread.sleep(5000);
            File output=new File(command.getString("output"));ExpansionTest.glb(output,ExpansionTest.geometry());System.out.println(new JSONObject().put("event","complete").put("output",output.getPath()));
        }
    }
    static void run(File root,File run)throws Exception {
        for(boolean multi:new boolean[]{false,true}){
            File exported=new File(root,"build/sam-tests/"+(multi?"mv_bundle":"single_bundle"));JSONObject raw=ExpansionTest.read(new File(exported,"lma-bundle.json"));ModelBundle bundle=new ModelBundle(raw);SpatialSpec.validate(bundle,"mesh.generate");check(true);
            JSONObject config=ExpansionTest.read(new File(exported,"sam-config.json"));SpatialSpec.checkConfig(bundle.pipeline,config);check(true);
            for(String key:new String[]{"architecture","pipeline","engine","backend"}){JSONObject bad=DataFiles.copy(raw).put(key,"invalid");reject(()->SpatialSpec.validate(new ModelBundle(bad),"mesh.generate"));}
            for(String key:new String[]{"views","structureResolution","occupancyResolution","meshResolution","meshChannels","opset"})for(double value:new double[]{-1,1.5}){JSONObject bad=DataFiles.copy(config).put(key,value);reject(()->SpatialSpec.checkConfig(bundle.pipeline,bad));}
            JSONObject missing=DataFiles.copy(raw);missing.getJSONArray("components").remove(0);reject(()->SpatialSpec.validate(new ModelBundle(missing),"mesh.generate"));
            JSONObject bad=DataFiles.copy(config);bad.getJSONObject("structureCondition").getJSONArray("keys").put(0,"remote_image_url");reject(()->SpatialSpec.checkConfig(bundle.pipeline,bad));
            JSONObject badSchedule=DataFiles.copy(config);badSchedule.getJSONObject("slatSchedule").put("solver","external_solver");reject(()->SpatialSpec.checkConfig(bundle.pipeline,badSchedule));
            JSONObject badStats=DataFiles.copy(config);badStats.getJSONObject("slatNormalization").getJSONArray("std").put(1,-1);reject(()->SpatialSpec.checkConfig(bundle.pipeline,badStats));
            Map<String,File> files=new LinkedHashMap<>();for(ModelBundle.Component c:bundle.components)files.put(c.role,new File(exported,c.path));BundleStore store=new BundleStore(new File(run,"sam-store-"+multi));store.declare(bundle);check(!store.plan(bundle.id).getBoolean("installed"));store.adoptLocal(bundle,files,new JSONObject(),()->{});
            File executable=new File(System.getProperty("java.home"),"bin/java.exe");LmaApp app=new LmaApp(new File(run,"sam-app-"+multi));app.bundles=store;ExpansionEngine base=new ExpansionEngine(app,executable,new JSONObject().put("engine","spatial_ort"));
            JSONObject normalized=base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("structureSteps",999).put("slatSteps",999).put("maxRows",999999)).getJSONObject("values");check(normalized.getInt("structureSteps")==100&&normalized.getInt("slatSteps")==100&&normalized.getInt("maxRows")==4096);
            reject(()->base.schema(bundle).normalize(new JSONObject(),new JSONObject().put("remote_url","https://invalid.example")));
            InputSpec input=base.inputs(bundle,"mesh.generate");check(input.json().getJSONObject("roles").length()==(multi?4:1));JSONArray refs=new JSONArray();
            String[] roles=multi?MultiViewSpec.ROLES:new String[]{"reference_image"},names=multi?MultiViewSpec.FILES:new String[]{"00_front.png"};String prompt=multi?MultiViewSpec.PROMPT:SpatialSpec.PROMPT;
            for(int i=0;i<roles.length;i++){reject(()->input.validate(refs,new JSONObject().put("prompt",prompt)));File file=new File(root,"build/sam-tests/views/"+names[i]);refs.put(new JSONObject().put("role",roles[i]).put("bytes",file.length()).put("metadata",new JSONObject().put("mime","image/png").put("width",32).put("height",40)));}
            input.validate(refs,new JSONObject().put("prompt",prompt));check(true);
            try(BundleStore.Lease lease=store.acquire(bundle.id)){
                for(int mode=0;mode<3;mode++){
                    final int variant=mode;final long[] started={Long.MAX_VALUE};final Process[] child={null};File output=new File(run,"sam-"+multi+"-"+mode+".glb");
                    ExpansionEngine engine=new ExpansionEngine(app,executable,new JSONObject().put("engine","spatial_ort"),builder->{child[0]=new ProcessBuilder(executable.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),Worker.class.getName(),builder.command().get(1)).redirectErrorStream(true).start();return child[0];});
                    JSONObject request=new JSONObject().put("type","mesh.generate").put("input",new JSONObject().put("prompt",prompt).put("fixtureFail",mode==1).put("fixtureSlow",mode==2)).put("parameters",engine.schema(bundle).normalize(new JSONObject(),new JSONObject()).getJSONObject("values"));
                    LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role)throws IOException{int index=Arrays.asList(roles).indexOf(role);if(index<0)throw new IOException("Unexpected SAM input");return new File(root,"build/sam-tests/views/"+names[index]);}public File output(String suffix){return output;}public void check()throws Exception{if(variant==2&&started[0]!=Long.MAX_VALUE&&System.nanoTime()-started[0]>600000000L)throw new IOException("Cancelled fixture");}public void progress(String stage,Double f){}public void process(Process p){if(p!=null)started[0]=System.nanoTime();}public void execution(JSONObject details){SamTest.check(details.getBoolean("fixture"));}};
                    if(mode==0){engine.generate(context);check(output.isFile());}else{reject(()->engine.generate(context));check(!output.exists());}check(child[0]!=null&&!child[0].isAlive());check(app.nativeProcess==null);check(new File(app.getFilesDir(),"engine-work").list().length==0);
                }
            }
        }
    }
}
