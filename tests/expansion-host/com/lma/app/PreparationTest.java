package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Real stores / selection / staging / completion, explicit non-neural stage fixtures. */
final class PreparationTest {
    static void check(boolean value){ExpansionTest.check(value);}
    static void reject(ExpansionTest.Attempt attempt)throws Exception{ExpansionTest.rejects(attempt);}
    static ModelBundle fixture(File root,File run,BundleStore store,String pipeline)throws Exception {
        JSONArray templates=ExpansionTest.read(new File(root,"app/src/main/assets/recipe-templates.json")).getJSONArray("templates");JSONObject template=null;
        for(int i=0;i<templates.length();i++)if(templates.getJSONObject(i).getJSONObject("definition").getString("pipeline").equals(pipeline)){template=templates.getJSONObject(i);break;}
        if(template==null)throw new AssertionError(pipeline);JSONObject definition=DataFiles.copy(template.getJSONObject("definition"));String id="preparation_"+pipeline;
        definition.put("schema","lma.model-bundle/2").put("recipeId",template.getString("id")).put("id",id).put("modelId",id).put("name",id);JSONArray components=new JSONArray();Map<String,File> sources=new HashMap<>();JSONArray requirements=template.getJSONArray("requirements");
        for(int i=0;i<requirements.length();i++){JSONObject requirement=requirements.getJSONObject(i);if(!requirement.getBoolean("required"))continue;String role=requirement.getString("role"),format=requirement.getJSONArray("formats").getString(0);File file=new File(run,id+"_"+role);Files.write(file.toPath(),new byte[]{(byte)(i+3)});String name=role+"."+format;if(requirement.has("matchFiles"))name=requirement.getJSONArray("matchFiles").getString(0);components.put(new JSONObject().put("role",role).put("path",name).put("format",format).put("bytes",1).put("sha256",DataFiles.sha256(file)).put("url",""));sources.put(role,file);}
        ModelBundle bundle=new ModelBundle(definition.put("components",components));store.declare(bundle);store.adoptLocal(bundle,sources,new JSONObject(),()->{});return bundle;
    }
    static void run(File root,File run)throws Exception {
        // Typed JSON travels through the real import / persistence / role checks.
        ArtifactStore artifacts=new ArtifactStore(new File(run,"data-artifacts"),StructuredInput::inspectDocument);JSONObject camera=new JSONObject().put("schema","lma.camera/1").put("distance",3).put("camera_angle_x",Math.PI/9);byte[] bytes=camera.toString().getBytes("UTF-8");
        JSONObject imported=artifacts.importStream(new ByteArrayInputStream(bytes),"camera.json",()->{});check(imported.getString("filename").endsWith(".json"));check(imported.getJSONObject("metadata").getString("dataType").equals("lma.camera/1"));check(StructuredInput.looksJson(artifacts.file(imported.getString("id"))));check(new ArtifactStore(new File(run,"data-artifacts"),StructuredInput::inspectDocument).snapshot().length()==1);
        reject(()->artifacts.importStream(new ByteArrayInputStream("{\"url\":\"https://example.invalid\"}".getBytes("UTF-8")),"arbitrary.json",()->{}));
        reject(()->artifacts.importStream(new ByteArrayInputStream("{\"schema\":\"lma.camera/1\",\"distance\":-1,\"camera_angle_x\":1}".getBytes("UTF-8")),"bad.json",()->{}));
        JSONObject text=new JSONObject().put("schema","lma.text-result/1").put("content","x").put("reasoning","").put("finishReason","stop").put("usage",new JSONObject());reject(()->artifacts.importStream(new ByteArrayInputStream(text.toString().getBytes("UTF-8")),"text.json",()->{}));
        JSONArray points=new JSONArray();for(int i=0;i<16;i++)points.put(new JSONArray().put(.01*i).put(0).put(0).put(1).put(0).put(0));JSONObject pointcloud=new JSONObject().put("schema","lma.pointcloud/1").put("coordinates","publisher_normalized").put("points",points);JSONObject point=artifacts.importStream(new ByteArrayInputStream(pointcloud.toString().getBytes("UTF-8")),"points.json",()->{});check(point.getJSONObject("metadata").getInt("points")==16);PointCloudSpec.inputs().validate(new JSONArray().put(new JSONObject().put("role","point_cloud").put("bytes",point.getLong("bytes")).put("metadata",point.getJSONObject("metadata"))),new JSONObject().put("prompt","Reconstruct local 3D geometry from the selected point cloud."));check(true);
        JSONObject excessive=new ParameterSchema(PointCloudSpec.schema()).normalize(new JSONObject(),new JSONObject().put("octreeDepth",5).put("denseDepth",8));check(excessive.getJSONObject("values").getInt("denseDepth")==5);
        JSONObject v=new ParameterSchema(VisionSpec.schema("vlm_parts",1024)).normalize(new JSONObject(),new JSONObject().put("context",99999).put("maxTokens",99999));check(v.getJSONObject("values").getInt("context")==1024&&v.getJSONObject("values").getInt("maxTokens")==1023);
        File validParts=new File(run,"parts.json");TextResult.write(validParts,new JSONObject(text.toString()).put("content","{\"parts\":[{\"name\":\"leg\"},{\"name\":\"seat\"}]}"));check(VisionSpec.partCount(validParts)==2);
        TextResult.write(validParts,new JSONObject(text.toString()).put("content","{\"parts\":[{\"name\":\"a\"},{\"name\":\"a\"}]}"));reject(()->VisionSpec.partCount(validParts));
        BundleStore store=new BundleStore(new File(run,"preparation-store"));LmaApp app=new LmaApp(new File(run,"preparation-app"));app.bundles=store;
        ModelBundle shape=fixture(root,run,store,"partcrafter"),fg=fixture(root,run,store,"isnet_dis"),vlm=fixture(root,run,store,"vlm_parts"),paint=fixture(root,run,store,"hunyuan3d_21_paint");
        check(store.installedModels().size()==4);List<String> events=new ArrayList<>();final boolean[] fail={false};
        LocalEngine stage=new LocalEngine(){
            public String id(){return "fixture";}public JSONObject describe(){return new JSONObject();}public void validate(ModelBundle b,String type){}public File generate(Context c)throws Exception{
                c.check();events.add(c.model().bundle.pipeline);if(c.model().bundle.id.equals(fg.id)){File file=c.output("png");Files.copy(c.input("reference_image").toPath(),file.toPath());return file;}
                if(c.model().bundle.id.equals(vlm.id)){File file=c.output("json");TextResult.write(file,new JSONObject(text.toString()).put("content","{\"parts\":[{\"name\":\"leg\"},{\"name\":\"seat\"}]}"));return file;}
                if(fail[0])throw new IOException("Explicit material fixture failure");MaterialSpec.sourceMesh(c.input("source_mesh"));File output=c.output("glb");ExpansionTest.glb(output,ExpansionTest.geometry());return output;
            }
        };
        LocalEngine geometry=new LocalEngine(){
            public String id(){return "rf_shape_ort";}public JSONObject describe(){return new JSONObject();}public void validate(ModelBundle b,String type)throws Exception{RfShapeSpec.validate(b,type);}public ParameterSchema schema(ModelBundle b)throws Exception{return new ParameterSchema(RfShapeSpec.schema(b.pipeline));}public InputSpec inputs(ModelBundle b,String type)throws Exception{return RfShapeSpec.inputs(b.pipeline);}
            public File generate(Context c)throws Exception{events.add("geometry");check(!c.request().getJSONObject("parameters").has("foregroundModel"));check(c.request().getJSONObject("parameters").getInt("parts")==2);check(c.input("reference_image").isFile());File output=c.output("glb");ExpansionTest.glb(output,ExpansionTest.geometry());return output;}
        };
        PreparationEngine engine=new PreparationEngine(app,geometry,(b,type)->stage);store.setParameterResolver(b->b.id.equals(shape.id)?engine.schema(b):b.parameters());check(store.snapshot().length()==4);check(engine.schema(shape).json().getJSONObject("fields").getJSONObject("foregroundModel").getJSONArray("values").toString().contains(fg.id));
        File image=new File(run,"chain.png");MultiViewTest.png(image,256,256,6);JSONObject parameters=new JSONObject().put("foregroundModel",fg.id).put("partModel",vlm.id).put("materialModel",paint.id);
        JSONObject request=engine.prepare(shape,new JSONObject().put("type","mesh.generate").put("bundleId",shape.id).put("parameters",parameters).put("input",new JSONObject().put("prompt",RfShapeSpec.PROMPT)));
        try(BundleStore.Lease lease=store.acquire(shape.id)){
            for(int mode=0;mode<2;mode++){fail[0]=mode==1;events.clear();File result=new File(run,"chain-result-"+mode+".glb");LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return image;}public File output(String suffix){return result;}public void check(){}public void progress(String stage,Double fraction){}public void process(Process p){}public void execution(JSONObject d){}};
                if(mode==0){engine.generate(context);check(result.isFile());check(events.equals(Arrays.asList("isnet_dis","vlm_parts","geometry","hunyuan3d_21_paint")));}else{reject(()->engine.generate(context));check(!result.exists());}
                check(new File(app.getFilesDir(),"engine-work").list().length==0);check(!store.record(fg.id).optBoolean("inUse"));
            }
        }
        store.saveSettings(shape.id,parameters);store.remove(fg.id,false);JSONObject field=engine.schema(shape).json().getJSONObject("fields").getJSONObject("foregroundModel");check(field.getJSONArray("values").length()==2);check(field.getJSONObject("optionLabels").getString(fg.id).contains("未安装"));check(store.settings(shape.id).getJSONObject("values").getString("foregroundModel").equals(fg.id));check(store.snapshot().length()==4);reject(()->engine.prepare(shape,new JSONObject().put("type","mesh.generate").put("bundleId",shape.id).put("parameters",parameters).put("input",new JSONObject().put("prompt",RfShapeSpec.PROMPT))));store.saveSettings(shape.id,new JSONObject().put("foregroundModel","none"));check(store.settings(shape.id).getJSONObject("values").getString("foregroundModel").equals("none"));try(BundleStore.Lease lease=store.acquire(shape.id)){reject(()->engine.generate(new LocalEngine.Context(){public BundleStore.Lease model(){return lease;}public JSONObject request(){return request;}public File input(String role){return image;}public File output(String suffix){return new File(run,"removed-helper.glb");}public void check(){}public void progress(String s,Double f){}public void process(Process p){}public void execution(JSONObject d){}}));check(new File(app.getFilesDir(),"engine-work").list().length==0);}
    }
}
