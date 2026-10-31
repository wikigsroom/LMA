package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Closed single-view SAM / four-view MV-SAM3D + joint DA3 CPU routes. */
public final class SamSpec {
    private SamSpec() {}
    public static boolean matches(String pipeline){return pipeline.equals("sam3d_objects")||pipeline.equals("mv_sam3d_da3");}
    public static boolean multi(String pipeline){return pipeline.equals("mv_sam3d_da3");}
    public static Map<String,String> layout(String pipeline){
        Map<String,String> out=new LinkedHashMap<>();out.put("config","sam-config.json");
        List<String> names=new ArrayList<>(Arrays.asList("ss_conditioner","slat_conditioner","structure_flow","structure_decoder","slat_flow","mesh_decoder",multi(pipeline)?"depth_anyview":"depth_moge"));if(multi(pipeline))names.add("depth_metric");
        for(String name:names){out.put(name,name+".onnx");out.put(name+"_data",name+".onnx.data");}return Collections.unmodifiableMap(out);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        if(!matches(b.pipeline)||!b.architecture.equals(b.pipeline)||!b.engine.equals("spatial_ort")||!b.backend.equals("cpu")||!b.tasks.equals(Collections.singleton("3d"))||!type.equals("mesh.generate"))throw new IOException("SAM 需要匹配的本地 CPU 重建配方");
        Map<String,String> layout=layout(b.pipeline);Set<String> missing=new HashSet<>();for(String role:layout.keySet())if(!role.endsWith("_data"))missing.add(role);
        for(ModelBundle.Component c:b.components){String name=layout.get(c.role),format=c.role.equals("config")?"json":c.role.endsWith("_data")?"onnx_data":"onnx";long limit=c.role.equals("config")?65536:format.equals("onnx")?128L*1024*1024:32L*1024*1024*1024;
            if(name==null||!new File(c.path).getName().equals(name)||!c.format.equals(format)||c.bytes>limit)throw new IOException("SAM 组件名称、格式或大小不匹配："+c.role);missing.remove(c.role);
        }if(!missing.isEmpty())throw new IOException("缺少同批 SAM 转换资产："+missing);
    }
    private static int integer(JSONObject c,String key,int lo,int hi)throws Exception {Object raw=c.get(key);double value=c.getDouble(key);int n=c.getInt(key);if(!(raw instanceof Number)||!Double.isFinite(value)||value!=n||n<lo||n>hi)throw new IOException("SAM 配置整数无效："+key);return n;}
    private static double number(JSONObject c,String key,double lo,double hi)throws Exception {Object raw=c.get(key);double value=c.getDouble(key);if(!(raw instanceof Number)||!Double.isFinite(value)||value<lo||value>hi)throw new IOException("SAM 配置数值无效："+key);return value;}
    private static void schedule(JSONObject c)throws Exception {number(c,"rescale",.000001,100);number(c,"timeScale",.000001,10000);c.getBoolean("reversed");c.getBoolean("shortcut");c.getBoolean("noShortcut");if(!Arrays.asList("euler","midpoint","rk4").contains(c.getString("solver")))throw new IOException("SAM 采样求解器不匹配");}
    private static void fusion(JSONObject c)throws Exception {c.getBoolean("enabled");integer(c,"warmupSteps",1,100);integer(c,"pooling",1,16);int lo=integer(c,"patchBegin",0,16383),hi=integer(c,"patchEnd",2,16384);if(hi-lo<2)throw new IOException("SAM 注意力区间无效");number(c,"alpha",0,1000);number(c,"temperature",.000001,100);number(c,"minimum",0,1);}
    private static long heads(JSONArray array,boolean sparse)throws Exception {
        if(array.length()<1||array.length()>16)throw new IOException("SAM 潜变量头数量无效");long total=0;Set<String> names=new HashSet<>();long shape=0;
        for(int i=0;i<array.length();i++){JSONObject h=array.getJSONObject(i);String name=h.getString("name");if(!names.add(name))throw new IOException("SAM 潜变量头重复");int rows=integer(h,"rows",1,262144),width=integer(h,"channels",1,512);total+=(long)rows*width;if(name.equals("shape")){if(width!=8)throw new IOException("SAM 形状潜变量需要 8 通道");shape=rows;}number(h,"strength",0,100);number(h,"pointStrength",0,100);
            if(!h.isNull("interval")){JSONArray interval=h.getJSONArray("interval");if(interval.length()!=2||!(interval.get(0) instanceof Number)||!(interval.get(1) instanceof Number)||!Double.isFinite(interval.getDouble(0))||!Double.isFinite(interval.getDouble(1))||interval.getDouble(0)>interval.getDouble(1))throw new IOException("SAM CFG 区间无效");}
        }if(total>32000000||shape==0||sparse&&(array.length()!=1||shape!=1))throw new IOException("SAM 潜变量布局超限");return shape;
    }
    private static void condition(JSONObject c)throws Exception {
        integer(c,"imageSize",14,1024);int tokens=integer(c,"tokens",2,16384),width=integer(c,"width",8,4096);if((long)tokens*width>32000000)throw new IOException("SAM 条件张量超限");boolean points=c.getBoolean("pointmap");Set<String> actual=new HashSet<>();JSONArray keys=c.getJSONArray("keys");for(int i=0;i<keys.length();i++)if(!actual.add(keys.getString(i)))throw new IOException("SAM 条件输入重复");Set<String> expected=new HashSet<>(Arrays.asList("image","mask","rgb_image","rgb_image_mask"));if(points)expected.addAll(Arrays.asList("pointmap","pointmap_valid","rgb_pointmap","rgb_pointmap_valid"));if(!actual.equals(expected))throw new IOException("SAM 条件输入不完整");
        JSONObject p=c.getJSONObject("preprocessing");number(p,"boxFactor",1,3);number(p,"padding",0,1);if(points){JSONObject n=p.getJSONObject("normalizer");if(!Arrays.asList("ssi","object_scene","object_quantile","object_norm_median").contains(n.getString("method")))throw new IOException("SAM 点图归一化不匹配");if(n.has("scaleFactor"))number(n,"scaleFactor",.000001,100);if(n.has("clip"))number(n,"clip",0,1000);if(n.has("quantile"))number(n,"quantile",0,.499999);}
    }
    public static void checkConfig(String pipeline,JSONObject c)throws Exception {
        boolean mv=multi(pipeline);JSONObject s=c.getJSONObject("source");if(!matches(pipeline)||!c.getString("schema").equals("lma.sam-export/1")||!c.getString("pipeline").equals(pipeline)||!c.getString("dtype").equals("float32")||integer(c,"opset",17,17)!=17||!s.getString("repository").equals(mv?"devinli123/MV-SAM3D":"facebookresearch/sam-3d-objects")||!s.getString("revision").equals(mv?"abb04b5e8af5bc33b0265bdf19937e76bbb6bcdd":"f91db411c50efee93d8db7aeb323885650f6f722")||!c.getString("inputPolicy").equals("explicit_rgba_fixed_square")||!c.getString("surfacePolicy").equals("source_flexicubes_vertex_attributes"))throw new IOException("SAM 导出来源或执行方式不匹配");
        JSONObject aux=c.getJSONObject("auxiliarySources");String[][] required={{"MOGE","microsoft/MoGe","74fbce054ebed49800de42d0ad0e83495065719a"},{"TIMM","huggingface/pytorch-image-models","78c3724f4545c0067d0b4d2f7df6337196be01ce"},{"DA3","ByteDance-Seed/Depth-Anything-3","3d835ec1a5802d64a8b8b15f817a1ab54809bfe4"}};
        if(aux.length()!=(mv?3:2))throw new IOException("SAM 辅助网络来源不匹配");for(int i=0;i<(mv?3:2);i++){JSONObject value=aux.getJSONObject(required[i][0]);if(value.length()!=2||!value.getString("repository").equals(required[i][1])||!value.getString("revision").equals(required[i][2]))throw new IOException("SAM 辅助网络版本不匹配");}
        integer(c,"views",mv?4:1,mv?4:1);int grid=integer(c,"occupancyResolution",4,256),latent=integer(c,"structureResolution",2,32),mesh=integer(c,"meshResolution",16,1024);integer(c,"meshChannels",c.getBoolean("meshColor")?101:53,c.getBoolean("meshColor")?101:53);integer(c,"prune",0,2);if(mesh!=grid*4||heads(c.getJSONArray("heads"),false)!=(long)latent*latent*latent)throw new IOException("SAM 结构尺寸不匹配");heads(c.getJSONArray("slatHeads"),true);
        for(String key:Arrays.asList("structureCondition","slatCondition"))condition(c.getJSONObject(key));for(String key:Arrays.asList("structureSchedule","slatSchedule"))schedule(c.getJSONObject(key));for(String key:Arrays.asList("structureFusion","slatFusion"))fusion(c.getJSONObject(key));
        for(String key:Arrays.asList("structureFlow","slatFlow")){JSONObject f=c.getJSONObject(key);f.getBoolean("capture");f.getBoolean("pointmapCfg");integer(f,"attentionHeads",1,64);integer(f,"attentionWidth",1,256);}
        if(!Arrays.asList("default","ApparentSize","DisparitySpace","ScaleShiftInvariant","ZeroPredictionScaleShiftInvariant").contains(c.getString("poseConvention")))throw new IOException("SAM 姿态约定不匹配");
        JSONObject depth=c.getJSONObject("depth");if(integer(depth,"imageSize",28,1024)%14!=0||mv&&!depth.getString("referenceView").equals("first"))throw new IOException("SAM 深度输入尺寸不匹配");if(!mv)number(depth,"maskThreshold",-100,100);
        JSONObject stats=c.getJSONObject("slatNormalization");for(String key:Arrays.asList("mean","std")){JSONArray a=stats.getJSONArray(key);if(a.length()!=8)throw new IOException("SAM 归一化维度不匹配");for(int i=0;i<8;i++){double value=a.getDouble(i);if(!(a.get(i) instanceof Number)||!Double.isFinite(value)||key.equals("std")&&value<=0)throw new IOException("SAM 归一化参数无效");}}
    }
    private static JSONObject f(String label,int value,int lo,int hi)throws Exception {return new JSONObject().put("type","integer").put("label",label).put("default",value).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema(String pipeline,JSONObject config)throws Exception {
        if(config!=null)checkConfig(pipeline,config);return new JSONObject().put("version",1).put("fields",new JSONObject().put("threads",f("CPU 线程",2,1,16)).put("seed",f("随机种子",42,0,Integer.MAX_VALUE)).put("structureSteps",f("结构采样步数",25,1,100)).put("slatSteps",f("细节采样步数",25,1,100)).put("maxRows",f("潜变量坐标保护上限",4096,64,4096)).put("maxTriangles",f("三角面保护上限",300000,1000,1000000)));
    }
    public static InputSpec inputs(String pipeline)throws Exception {
        JSONObject roles=new JSONObject();if(multi(pipeline)){String[] labels={"正面 RGBA PNG","右面 RGBA PNG","背面 RGBA PNG","左面 RGBA PNG"};for(int i=0;i<4;i++)roles.put(MultiViewSpec.ROLES[i],png(labels[i]));}else roles.put("reference_image",png("已去背景的 RGBA PNG"));
        return new InputSpec(roles,multi(pipeline)?"四张有顺序的物体图；DA3 联合深度、度量对齐、共享潜变量的加权采样与带颜色网格均在手机。完整权重较大，内存不足会报错。":"单张物体图；MoGe、条件编码、SAM 采样与原始 FlexiCubes 均在手机。输出带顶点颜色的网格，不包含高斯贴图烘焙。").withFixedPrompt(multi(pipeline)?MultiViewSpec.PROMPT:SpatialSpec.PROMPT).withNegativePrompt(false);
    }
    private static JSONObject png(String label)throws Exception{return new JSONObject().put("label",label).put("required",true).put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024).put("maxPixels",4194304);}
}
