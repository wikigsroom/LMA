package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** Fixed, explicitly selected same-phone preparation/material stages around geometry engines. */
public final class PreparationEngine implements LocalEngine {
    public interface Lookup { LocalEngine require(ModelBundle bundle,String type) throws Exception; }
    private final LmaApp app;private final LocalEngine geometry;private final Lookup lookup;
    private static final List<String> MODELS=Arrays.asList("foregroundModel","partModel","materialModel");
    private static final List<String> FIELDS=Arrays.asList("foregroundModel","partModel","materialModel","materialPrompt");
    public PreparationEngine(LmaApp app,LocalEngine geometry,Lookup lookup){this.app=app;this.geometry=geometry;this.lookup=lookup;}
    @Override public String id(){return geometry.id();}
    @Override public JSONObject describe()throws Exception{return geometry.describe().put("localPreparation",true);}
    @Override public void validate(ModelBundle b,String type)throws Exception{geometry.validate(b,type);}
    @Override public InputSpec inputs(ModelBundle b,String type)throws Exception{
        InputSpec original=geometry.inputs(b,type);if(!points(b))return original;JSONObject definition=original.json(),roles=definition.getJSONObject("roles");roles.put("reference_image",new JSONObject().put("label","材质参考 PNG（选择后续材质模型时必选）").put("required",false).put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024));return new InputSpec(roles,definition.optString("promptHelp")).withFixedPrompt(definition.getString("fixedPrompt")).withNegativePrompt(false);
    }
    private static boolean material(ModelBundle b){return MaterialSpec.matches(b.pipeline)||UltraTexSpec.matches(b.pipeline)||SupraSpec.matches(b.pipeline);}
    private static boolean points(ModelBundle b){return PointCloudSpec.matches(b.pipeline);}
    private static boolean parts(ModelBundle b){return b.pipeline.equals("partcrafter")||b.pipeline.equals("partcrafter_scene");}
    private static boolean materialsAllowed(ModelBundle b){return !material(b);}
    private static boolean foregroundAllowed(ModelBundle b){return !material(b)&&!points(b);}
    private boolean accepts(ModelBundle candidate,String role){return role.equals("foregroundModel")?candidate.engine.equals("vision_cpu")&&candidate.pipeline.equals("isnet_dis"):role.equals("partModel")?candidate.engine.equals("vision_cpu")&&candidate.pipeline.equals("vlm_parts"):candidate.engine.equals("spatial_ort")&&(MaterialSpec.matches(candidate.pipeline)||UltraTexSpec.matches(candidate.pipeline));}
    private List<ModelBundle> options(String role)throws Exception {List<ModelBundle> result=new ArrayList<>();if(app.bundles!=null)for(ModelBundle b:app.bundles.installedModels())if(accepts(b,role))result.add(b);return result;}
    @Override public ParameterSchema schema(ModelBundle b)throws Exception {
        JSONObject result=geometry.schema(b).json(),fields=result.getJSONObject("fields");if(!b.tasks.contains("3d"))return new ParameterSchema(result);
        for(String role:MODELS){if(role.equals("foregroundModel")&&!foregroundAllowed(b)||role.equals("partModel")&&!parts(b)||role.equals("materialModel")&&!materialsAllowed(b))continue;
            JSONArray values=new JSONArray().put("none");JSONObject labels=new JSONObject().put("none","不使用");for(ModelBundle candidate:options(role)){values.put(candidate.id);labels.put(candidate.id,candidate.name);}
            JSONObject saved=null;try{if(app.bundles!=null)saved=app.bundles.record(b.id).optJSONObject("settings");}catch(Exception notDeclared){}String previous=saved==null?"none":saved.optString(role,"none");if(!previous.equals("none")&&!labels.has(previous)){values.put(ModelBundle.key(previous));labels.put(previous,previous+"（当前未安装，请重新选择）");}
            fields.put(role,new JSONObject().put("type","enum").put("label",role.equals("foregroundModel")?"自动前景模型（可选）":role.equals("partModel")?"自动部件识别模型（可选）":"几何完成后的材质模型（可选）").put("default","none").put("values",values).put("optionLabels",labels).put("help","仅显示已完整安装的兼容模型；none 为不使用。模型和阶段参数独立管理；本机顺序执行，任何阶段失败均不提交结果。"));
        }if(materialsAllowed(b))fields.put("materialPrompt",new JSONObject().put("type","string").put("label","后续材质描述（UltraTex）").put("default","Realistic materials matching the selected reference image.").put("maxLength",4000));return new ParameterSchema(result);
    }
    private static JSONObject withoutHelpers(JSONObject parameters){JSONObject result=DataFiles.copy(parameters);for(String key:FIELDS)result.remove(key);return result;}
    @Override public JSONObject prepare(ModelBundle b,JSONObject request)throws Exception {
        if(points(b)&&!request.getJSONObject("parameters").optString("materialModel","none").equals("none")){JSONArray refs=request.getJSONObject("input").optJSONArray("artifacts");boolean found=false;if(refs!=null)for(int i=0;i<refs.length();i++)if(refs.getJSONObject(i).getString("role").equals("reference_image"))found=true;if(!found)throw new IOException("点云材质步骤需要选择参考 PNG");}
        JSONObject all=schema(b).normalize(new JSONObject(),request.getJSONObject("parameters")),copy=DataFiles.copy(request);copy.put("parameters",withoutHelpers(all.getJSONObject("values")));copy=geometry.prepare(b,copy);
        for(String role:MODELS){String id=all.getJSONObject("values").optString(role,"none");if(id.equals("none"))continue;ModelBundle chosen=null;for(ModelBundle candidate:options(role))if(candidate.id.equals(id))chosen=candidate;if(chosen==null)throw new IOException("所选准备 / 材质模型未完整安装，请重新选择："+id);String type=role.equals("foregroundModel")?"image.generate":role.equals("partModel")?"text.generate":"mesh.generate";lookup.require(chosen,type).validate(chosen,type);}
        JSONObject values=copy.getJSONObject("parameters");for(String key:FIELDS)if(all.getJSONObject("values").has(key))values.put(key,all.getJSONObject("values").get(key));JSONArray adjustments=copy.optJSONArray("adjustments");if(adjustments==null)adjustments=new JSONArray();JSONArray more=all.getJSONArray("adjustments");for(int i=0;i<more.length();i++)adjustments.put(more.get(i));return copy.put("adjustments",adjustments);
    }
    private static class Forward implements Context {
        final Context parent;final BundleStore.Lease selected;final JSONObject request;final Map<String,File> inputs;final File outputRoot;int sequence;
        Forward(Context parent,BundleStore.Lease selected,JSONObject request,Map<String,File> inputs,File outputRoot){this.parent=parent;this.selected=selected;this.request=request;this.inputs=inputs;this.outputRoot=outputRoot;}
        @Override public BundleStore.Lease model(){return selected;}
        @Override public JSONObject request(){return request;}
        @Override public File input(String role)throws Exception{return inputs.containsKey(role)?inputs.get(role):parent.input(role);}
        @Override public File output(String suffix)throws Exception{parent.check();return new File(outputRoot,"stage_"+(sequence++)+"_"+UUID.randomUUID().toString().replace("-","")+"."+suffix);}
        @Override public void check()throws Exception{parent.check();}
        @Override public void progress(String stage,Double fraction)throws Exception{parent.progress(stage,fraction);}
        @Override public void process(Process child)throws Exception{parent.process(child);}
        @Override public void execution(JSONObject details)throws Exception{parent.execution(new JSONObject().put("stageModel",selected.bundle.id).put("stageDetails",details));}
    }
    private File stage(Context parent,BundleStore.Lease lease,String type,Map<String,File> inputs,File directory,JSONObject input)throws Exception {
        LocalEngine engine=lookup.require(lease.bundle,type);JSONObject parameters=app.bundles.settings(lease.bundle.id).getJSONObject("values");
        JSONObject request=new JSONObject().put("bundleId",lease.bundle.id).put("type",type).put("input",input).put("parameters",parameters);
        parent.execution(new JSONObject().put("stageModel",lease.bundle.id).put("stageIntegrity",lease.integrity()).put("effectiveParameters",parameters));return engine.generate(new Forward(parent,lease,engine.prepare(lease.bundle,request),inputs,directory));
    }
    @Override public File generate(Context context)throws Exception {
        ModelBundle b=context.model().bundle;JSONObject request=DataFiles.copy(context.request()),parameters=request.getJSONObject("parameters");Map<String,String> selection=new LinkedHashMap<>();
        for(String role:MODELS){String id=parameters.optString(role,"none");if(!id.equals("none"))selection.put(role,ModelBundle.key(id));}
        if(selection.isEmpty()){request.put("parameters",withoutHelpers(parameters));return geometry.generate(new Forward(context,context.model(),request,Collections.emptyMap(),new File(app.getFilesDir(),"unused")){
            @Override public File output(String suffix)throws Exception{return context.output(suffix);}
            @Override public List<BundleStore.Lease> adapters(){return context.adapters();}
            @Override public void execution(JSONObject details)throws Exception{context.execution(details);}
        });}
        if(!context.adapters().isEmpty())throw new IOException("几何流程不接受图像 LoRA");
        if(selection.containsKey("foregroundModel")&&!foregroundAllowed(b)||selection.containsKey("partModel")&&!parts(b)||selection.containsKey("materialModel")&&!materialsAllowed(b))throw new IOException("该几何配方不支持所选准备步骤");
        Map<String,BundleStore.Lease> held=new LinkedHashMap<>();EngineWorkspace work=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),context::check);
        try{
            for(Map.Entry<String,String> e:selection.entrySet()){BundleStore.Lease lease=app.bundles.acquire(e.getValue());held.put(e.getKey(),lease);if(!accepts(lease.bundle,e.getKey())||lease.bundle.id.equals(b.id))throw new IOException("准备模型与步骤不匹配");lease.integrity();}
            JSONArray selectedStages=new JSONArray();for(Map.Entry<String,BundleStore.Lease> e:held.entrySet())selectedStages.put(new JSONObject().put("role",e.getKey()).put("bundleId",e.getValue().bundle.id).put("components",e.getValue().integrity()).put("parameters",app.bundles.settings(e.getValue().bundle.id).getJSONObject("values")));context.execution(new JSONObject().put("localStages",selectedStages).put("inferenceLocation","same_android_phone").put("automaticModelDownloads",false));
            Map<String,File> images=new LinkedHashMap<>();InputSpec spec=inputs(b,"mesh.generate");JSONObject roles=spec.json().getJSONObject("roles");for(Iterator<String> it=roles.keys();it.hasNext();){String role=it.next();if(roles.getJSONObject(role).getJSONArray("mimes").toString().contains("image/png")){boolean selected=roles.getJSONObject(role).getBoolean("required");JSONArray refs=request.getJSONObject("input").optJSONArray("artifacts");if(refs!=null)for(int i=0;i<refs.length();i++)if(refs.getJSONObject(i).getString("role").equals(role))selected=true;if(selected)images.put(role,context.input(role));}}
            if(held.containsKey("foregroundModel")){int i=0;for(Map.Entry<String,File> entry:images.entrySet()){context.check();context.progress("preparing_foreground",null);Map<String,File> input=Collections.singletonMap("reference_image",entry.getValue());entry.setValue(stage(context,held.get("foregroundModel"),"image.generate",input,work.directory(),new JSONObject().put("prompt","Prepare local foreground.")));i++;}if(i==0)throw new IOException("该任务没有可抠图输入");}
            JSONObject geometryRequest=DataFiles.copy(request).put("parameters",withoutHelpers(parameters));
            if(held.containsKey("partModel")){File image=images.get("reference_image");if(image==null)throw new IOException("自动部件识别需要单张参考图");context.progress("identifying_parts",null);File result=stage(context,held.get("partModel"),"text.generate",Collections.singletonMap("reference_image",image),work.directory(),new JSONObject().put("prompt","Identify local object parts."));int count=VisionSpec.partCount(result);JSONObject effective=geometry.schema(b).normalize(new JSONObject(),new JSONObject(geometryRequest.getJSONObject("parameters").toString()).put("parts",count));if(effective.getJSONObject("values").getInt("parts")!=count)throw new IOException("识别部件数超过选定几何模型上限");geometryRequest.put("parameters",effective.getJSONObject("values"));context.execution(new JSONObject().put("partIdentification",new JSONObject(TextResult.read(result).getString("content"))).put("effectivePartCount",count));}
            File result=geometry.generate(new Forward(context,context.model(),geometryRequest,images,work.directory()));
            if(held.containsKey("materialModel")){File reference=images.get("reference_image");if(reference==null&&images.size()>0)reference=images.values().iterator().next();if(reference==null)throw new IOException("材质步骤需要明确选择参考图片；点云重建请另行选择材质配方和参考图");context.progress("generating_materials",null);Map<String,File> inputs=new HashMap<>();inputs.put("source_mesh",result);inputs.put("reference_image",reference);String prompt=held.get("materialModel").bundle.pipeline.startsWith("ultratex")?parameters.optString("materialPrompt","Realistic materials matching the selected reference image."):SpatialSpec.PROMPT;if(prompt.trim().isEmpty())throw new IOException("请填写后续材质描述");result=stage(context,held.get("materialModel"),"mesh.generate",inputs,work.directory(),new JSONObject().put("prompt",prompt));}
            context.check();GlbFile.inspect(result);File output=context.output("glb");DataFiles.move(result,output);return output;
        }finally{try{work.close();}finally{for(BundleStore.Lease lease:held.values())lease.close();}}
    }
}
