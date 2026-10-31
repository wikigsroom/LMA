package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Closed same-phone four-view UniForge cascade. User assets, never user code. */
public final class UniForgeSpec {
    private UniForgeSpec() {}
    public static boolean matches(String pipeline){return pipeline.equals("uniforge3d");}
    public static final String[] GRAPHS={"dino512","dino1024","structure_flow","structure_decoder","conditioner","shape512_adapter","shape1024_adapter","texture_adapter","shape512_flow","shape1024_flow","texture_flow","shape512_decoder","shape1024_decoder","texture_decoder"};
    public static Map<String,String> layout(){Map<String,String> r=new LinkedHashMap<>();r.put("config","uniforge-config.json");for(String n:GRAPHS){r.put(n,n+".onnx");r.put(n+"_data",n+".onnx.data");}return Collections.unmodifiableMap(r);}
    public static void validate(ModelBundle b,String type)throws Exception {
        if(!matches(b.pipeline)||!b.architecture.equals("uniforge3d")||!b.engine.equals("spatial_ort")||!b.backend.equals("cpu")||!b.tasks.equals(Collections.singleton("3d"))||!type.equals("mesh.generate"))throw new IOException("请选择匹配的 UniForge 本地 CPU 配方");
        Set<String> missing=new HashSet<>();for(String k:layout().keySet())if(!k.endsWith("_data"))missing.add(k);
        for(ModelBundle.Component c:b.components){String name=layout().get(c.role),format=c.role.equals("config")?"json":c.role.endsWith("_data")?"onnx_data":"onnx";long max=c.role.equals("config")?65536:format.equals("onnx")?128L*1024*1024:32L*1024*1024*1024;
            if(name==null||!new File(c.path).getName().equals(name)||!c.format.equals(format)||c.bytes>max)throw new IOException("UniForge 组件角色、名称、格式或大小不匹配："+c.role);missing.remove(c.role);}
        if(!missing.isEmpty())throw new IOException("UniForge 缺少同批转换组件："+missing);
    }
    public static void checkConfig(JSONObject c)throws Exception {
        JSONObject s=c.getJSONObject("source");if(!c.getString("schema").equals("lma.uniforge-export/1")||!c.getString("pipeline").equals("uniforge3d")||!c.getString("dtype").equals("float32")||c.getInt("opset")!=17||!s.getString("repository").equals("xibushu/UniForge3D")||!s.getString("revision").equals("8b6094780e202b8a6b1d239e0997552e18547026")||c.getInt("views")!=4||!c.getString("inputPolicy").equals("explicit_rgba_foreground")||!c.getString("surfacePolicy").equals("raw_fdg_sat_handoff"))throw new IOException("UniForge 来源或执行方式不匹配");
        if(!c.getJSONArray("imageSizes").toString().equals("[512,1024,448]")||c.getInt("structureChannels")!=8||c.getInt("structureResolution")!=16||c.getInt("latentChannels")!=32||c.getInt("featureWidth")!=1024||c.getInt("conditionWidth")!=2048||c.getInt("decoderLevels")!=4)throw new IOException("UniForge 网络尺寸不匹配");
        int grid=c.getInt("occupancyResolution");if(grid<64||grid>256||grid%64!=0)throw new IOException("UniForge 结构解码网格无效");
        for(String key:new String[]{"shapeNormalization","textureNormalization"}){JSONObject n=c.getJSONObject(key);JSONArray mean=n.getJSONArray("mean"),std=n.getJSONArray("std");if(mean.length()!=32||std.length()!=32)throw new IOException("UniForge 归一化通道不匹配");for(int i=0;i<32;i++)if(!Double.isFinite(mean.getDouble(i))||!Double.isFinite(std.getDouble(i))||std.getDouble(i)<=0)throw new IOException("UniForge 归一化参数无效");}
    }
    private static JSONObject f(String label,int value,int lo,int hi)throws Exception{return new JSONObject().put("type","integer").put("label",label).put("default",value).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema(JSONObject config)throws Exception {
        if(config!=null)checkConfig(config);return new JSONObject().put("version",1).put("fields",new JSONObject()
            .put("threads",f("CPU 线程",2,1,16)).put("seed",f("随机种子",42,0,Integer.MAX_VALUE)).put("structureSteps",f("结构采样步数",12,1,100))
            .put("shapeSteps",f("每阶段形状采样步数",20,1,100)).put("textureSteps",f("材质采样步数",20,1,100)).put("maxRows",f("潜变量坐标保护上限",16384,64,20000))
            .put("maxTriangles",f("三角面保护上限",300000,1000,300000)).put("atlas",f("UV 图集目标尺寸",1024,256,4096).put("multipleOf",256)));
    }
    public static InputSpec inputs()throws Exception {
        JSONObject roles=new JSONObject();String[] labels={"正面 RGBA PNG","右面 RGBA PNG","背面 RGBA PNG","左面 RGBA PNG"};for(int i=0;i<4;i++)roles.put(MultiViewSpec.ROLES[i],new JSONObject().put("label",labels[i]).put("required",true).put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024).put("maxPixels",4194304));
        return new InputSpec(roles,"选择四张已去背景 RGBA 视图，按正 / 右 / 后 / 左排序。逐阶段在手机 CPU 生成几何与 PBR GLB；模型资产独立选择。CPU 路径保留原始网格，超出内存或拓扑保护上限会报错。").withFixedPrompt(MultiViewSpec.PROMPT).withNegativePrompt(false);
    }
}
