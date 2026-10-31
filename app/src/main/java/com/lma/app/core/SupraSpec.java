package com.lma.app.core;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import org.json.*;

/** Fixed same-phone SUPRA-Tex existing-mesh / camera material route. */
public final class SupraSpec {
    private SupraSpec() {}
    public static boolean matches(String pipeline){return pipeline.equals("supratex");}
    public static Map<String,String> layout(){
        Map<String,String> result=new LinkedHashMap<>();result.put("config","supra-config.json");result.put("tokenizer","qwen-tokenizer.json");
        for(String graph:Arrays.asList("qwen_text","qwen_encode","qwen_decode","qwen_material","shape_encoder","material_encoder","shape_decoder","material_decoder","completion")){result.put(graph,graph+".onnx");result.put(graph+"_data",graph+".onnx.data");}return Collections.unmodifiableMap(result);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        if(!matches(b.pipeline)||!b.architecture.equals("supratex")||!b.engine.equals("spatial_ort")||!b.backend.equals("cpu")||!b.tasks.equals(Collections.singleton("3d"))||!type.equals("mesh.generate"))throw new IOException("SUPRA-Tex 需要匹配的本地 CPU 材质配方");
        Map<String,String> layout=layout();Set<String> missing=new HashSet<>();for(String role:layout.keySet())if(!role.endsWith("_data"))missing.add(role);
        for(ModelBundle.Component component:b.components){String name=layout.get(component.role),format=name==null?"":name.endsWith(".json")?"json":name.endsWith(".data")?"onnx_data":"onnx";
            long limit=component.role.equals("config")?65536:component.role.equals("tokenizer")?32L*1024*1024:format.equals("onnx")?128L*1024*1024:32L*1024*1024*1024;
            if(name==null||!new File(component.path).getName().equals(name)||!component.format.equals(format)||component.bytes>limit)throw new IOException("SUPRA 组件名称、格式或大小不匹配："+component.role);missing.remove(component.role);
        }if(!missing.isEmpty())throw new IOException("缺少同批 SUPRA 转换资产："+missing);
    }
    private static int integer(JSONObject c,String key,int lo,int hi)throws Exception {Object raw=c.get(key);double v=c.getDouble(key);int n=c.getInt(key);if(!(raw instanceof Number)||!Double.isFinite(v)||v!=n||n<lo||n>hi)throw new IOException("SUPRA 配置整数无效："+key);return n;}
    private static void stats(JSONObject c,String name)throws Exception {JSONObject value=c.getJSONObject(name);for(String key:Arrays.asList("mean","std")){JSONArray array=value.getJSONArray(key);if(array.length()!=32)throw new IOException("SUPRA 归一化维度不匹配");for(int i=0;i<32;i++){double n=array.getDouble(i);if(!(array.get(i) instanceof Number)||!Double.isFinite(n)||key.equals("std")&&n<=0)throw new IOException("SUPRA 归一化值无效");}}}
    public static void checkConfig(JSONObject c)throws Exception {
        JSONObject source=c.getJSONObject("source");
        if(!c.getString("schema").equals("lma.supratex-export/1")||!c.getString("pipeline").equals("supratex")||!c.getString("dtype").equals("float32")||integer(c,"opset",17,17)!=17||!source.getString("repository").equals("Supra-3D/SUPRA-Tex")||!source.getString("revision").equals("cee4435652d0f23737bd28d5704e0fae9830b411")||!c.getString("inputPolicy").equals("mesh_camera_rgba")||!c.getString("surfacePolicy").equals("original_mesh_exact_encoder_topology"))throw new IOException("SUPRA 导出来源或输入方式不匹配");
        integer(c,"resolution",1024,1024);integer(c,"latentChannels",32,32);integer(c,"decoderLevels",4,4);
        JSONObject q=c.getJSONObject("qwen");integer(q,"patch",16,16);integer(q,"merge",2,2);integer(q,"temporal",2,2);integer(q,"vocabulary",151936,151936);integer(q,"imageToken",0,151935);
        if(!q.getJSONArray("grid").toString().equals("[1,64,64]")||q.getString("template").length()>4096||q.getString("prompt").isEmpty())throw new IOException("Qwen 视觉布局不匹配");
        JSONArray ids=q.getJSONArray("tokenIds");if(ids.length()<1025||ids.length()>2048)throw new IOException("Qwen token 数量无效");int images=0;for(int i=0;i<ids.length();i++){Object raw=ids.get(i);int n=ids.getInt(i);if(!(raw instanceof Number)||ids.getDouble(i)!=n||n<0||n>=151936)throw new IOException("Qwen token ID 无效");if(n==q.getInt("imageToken"))images++;}if(images!=1024)throw new IOException("Qwen 图像 token 布局不匹配");integer(q,"drop",1,ids.length()-1024);
        for(String key:Arrays.asList("mean","std")){JSONArray a=q.getJSONArray(key);if(a.length()!=3)throw new IOException("Qwen 图像归一化维度无效");for(int i=0;i<3;i++)if(!(a.get(i) instanceof Number)||!Double.isFinite(a.getDouble(i))||key.equals("std")&&a.getDouble(i)<=0)throw new IOException("Qwen 图像归一化值无效");}
        for(String name:Arrays.asList("shapeNormalization","partialNormalization","pbrNormalization"))stats(c,name);
        JSONObject sampler=c.getJSONObject("sampler");integer(sampler,"steps",25,25);if(sampler.getDouble("shift")!=3||sampler.getDouble("sigmaMin")!=1e-5||!sampler.getString("policy").equals("euler_static_observation_no_cfg"))throw new IOException("SUPRA 采样配置不匹配");
    }
    private static JSONObject f(String label,int value,int lo,int hi)throws Exception {return new JSONObject().put("type","integer").put("label",label).put("default",value).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema(JSONObject config)throws Exception {
        if(config!=null)checkConfig(config);return new JSONObject().put("version",1).put("fields",new JSONObject().put("threads",f("CPU 线程",2,1,16)).put("seed",f("补全随机种子",42,0,Integer.MAX_VALUE)).put("steps",f("材质补全步数",25,1,100)).put("atlas",f("UV 图集目标尺寸",1024,256,4096).put("multipleOf",256)).put("maxRows",f("潜变量坐标保护上限",20000,64,20000)));
    }
    public static void reference(File file)throws Exception {
        MultiViewSpec.reference(file);try(DataInputStream in=new DataInputStream(new FileInputStream(file))){in.skipBytes(16);if(in.readInt()!=1024||in.readInt()!=1024)throw new IOException("SUPRA 参考图需要与相机对齐的 1024×1024 RGBA PNG");}
    }
    public static void camera(File file)throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()<2||file.length()>16384)throw new IOException("请选择最多 16 KiB 的相机 JSON 文件（.json）");
        JSONObject c=new JSONObject(new String(Files.readAllBytes(file.toPath()),StandardCharsets.UTF_8));
        if(c.has("extrinsic")){JSONArray e=c.getJSONArray("extrinsic"),k=c.has("projection_intrinsic")?c.getJSONArray("projection_intrinsic"):c.getJSONArray("intrinsic");if(e.length()!=4||k.length()!=3)throw new IOException("相机矩阵需要 4×4 / 3×3");for(int i=0;i<4;i++){JSONArray row=e.getJSONArray(i);if(row.length()!=4)throw new IOException("相机外参维度无效");for(int j=0;j<4;j++)if(!(row.get(j) instanceof Number)||!Double.isFinite(row.getDouble(j)))throw new IOException("相机数值无效");}for(int i=0;i<3;i++){JSONArray row=k.getJSONArray(i);if(row.length()!=3)throw new IOException("相机内参维度无效");for(int j=0;j<3;j++)if(!(row.get(j) instanceof Number)||!Double.isFinite(row.getDouble(j)))throw new IOException("相机数值无效");}}
        else {double d=c.getDouble("distance"),f=c.getDouble("camera_angle_x"),s=c.optDouble("mesh_scale",1);if(!(c.get("distance") instanceof Number)||!(c.get("camera_angle_x") instanceof Number)||!Double.isFinite(d)||d<=0||d>100||!Double.isFinite(f)||f<=.01||f>=3.1||!Double.isFinite(s)||s<=0||s>100)throw new IOException("相机距离、弧度视场角或缩放无效");}
    }
    public static InputSpec inputs()throws Exception {
        JSONObject roles=MaterialSpec.inputs().json().getJSONObject("roles");roles.getJSONObject("reference_image").put("label","已对齐的 1024×1024 RGBA PNG");roles.put("camera",new JSONObject().put("label","匹配网格与参考图的相机 JSON（.json）").put("required",true).put("mimes",new JSONArray().put(StructuredInput.MIME)).put("maxBytes",16384));
        return new InputSpec(roles,"选择已有归一化 GLB、相机和匹配参考图；手机执行 Qwen 双材质预测、可见面观察、背面补全和 PBR 烘焙。完整权重很大，手机内存不足时会本地报错。").withFixedPrompt(SpatialSpec.PROMPT).withNegativePrompt(false);
    }
}
