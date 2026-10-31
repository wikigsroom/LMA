package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Selected local Hunyuan Paint asset contract; no Python or external provider. */
public final class MaterialSpec {
    private MaterialSpec() {}
    public static boolean matches(String pipeline) { return pipeline.equals("hunyuan3d_21_paint"); }
    public static Map<String,String> layout() {
        Map<String,String> result=new LinkedHashMap<>();result.put("config","material-config.json");result.put("sampler","sampler.json");
        for(String name:Arrays.asList("image_encoder","vae_encoder","flow","vae_decoder","upscale")){result.put(name,name+".onnx");result.put(name+"_data",name+".onnx.data");}
        return Collections.unmodifiableMap(result);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        if(!matches(b.pipeline)||!b.architecture.equals("hunyuan3d_21_paint")||!b.engine.equals("spatial_ort")||!b.backend.equals("cpu")||!type.equals("mesh.generate")||!b.tasks.equals(Collections.singleton("3d")))throw new IOException("请选择匹配的 Hunyuan3D Paint CPU 配方");
        Set<String> missing=new HashSet<>(Arrays.asList("config","sampler","image_encoder","vae_encoder","flow","vae_decoder","upscale"));
        for(ModelBundle.Component c:b.components){
            String name=layout().get(c.role),format=c.role.equals("config")||c.role.equals("sampler")?"json":c.role.endsWith("_data")?"onnx_data":"onnx";
            if(name==null||!new File(c.path).getName().equals(name)||!c.format.equals(format))throw new IOException("Paint 组件角色、格式或文件名不匹配："+c.role);
            long maximum=c.role.equals("config")?65536:c.role.equals("sampler")?8*1024*1024:format.equals("onnx")?128L*1024*1024:32L*1024*1024*1024;
            if(c.bytes>maximum)throw new IOException("Paint 组件超过基座范围："+c.role);missing.remove(c.role);
        }
        if(!missing.isEmpty())throw new IOException("Paint 缺少同批导出的必需组件："+missing);
    }
    private static int dimension(JSONObject c,String key,int lo,int hi)throws Exception {
        Object raw=c.get(key);double d=c.getDouble(key);int n=c.getInt(key);if(!(raw instanceof Number)||!Double.isFinite(d)||d!=n||n<lo||n>hi)throw new IOException("Paint 尺寸超出范围："+key);return n;
    }
    public static void checkConfig(JSONObject c)throws Exception {
        JSONObject source=c.getJSONObject("source");
        if(!c.getString("schema").equals("lma.material-export/1")||!matches(c.getString("pipeline"))||!c.getString("dtype").equals("float32")||c.getInt("opset")!=17||!source.getString("repository").equals("Tencent-Hunyuan/Hunyuan3D-2.1")||!source.getString("revision").equals("82920d643c0dc2f7bfd7255f45f62d386edfe60c")||!c.getString("scheduler").equals("UniPCMultistepScheduler")||!c.getString("timestepSpacing").equals("trailing"))throw new IOException("Paint 导出来源或采样器不匹配");
        int im=dimension(c,"imageSize",64,512),ds=dimension(c,"dinoSize",28,518),resize=dimension(c,"dinoResize",28,1024),tokens=dimension(c,"dinoTokens",2,2000);
        dimension(c,"dinoWidth",1536,1536);dimension(c,"views",6,6);dimension(c,"upscaleFactor",4,4);double scale=c.getDouble("vaeScaling");
        if(im%64!=0||ds%14!=0||resize<ds||tokens!=(ds/14)*(ds/14)+1||!Double.isFinite(scale)||scale<=0||scale>10)throw new IOException("Paint 图像或 VAE 配置无效");
    }
    private static JSONObject f(String type,String label,Number value,Number lo,Number hi)throws Exception {return new JSONObject().put("type",type).put("label",label).put("default",value).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema(JSONObject config)throws Exception {
        if(config!=null)checkConfig(config);
        return new JSONObject().put("version",1).put("fields",new JSONObject()
            .put("threads",f("integer","CPU 线程",2,1,16)).put("steps",f("integer","贴图采样步数",15,1,100)).put("seed",f("integer","随机种子",0,0,Integer.MAX_VALUE))
            .put("guidance",f("number","参考图引导强度",3,1,15)).put("atlas",f("integer","UV 图集目标尺寸",1024,256,4096).put("multipleOf",256))
            .put("upscale",new JSONObject().put("type","boolean").put("label","使用配套本地 RealESRGAN 4× 图").put("default",config==null||config.getInt("imageSize")<=384)));
    }
    public static InputSpec inputs()throws Exception {
        JSONObject roles=new JSONObject().put("reference_image",new JSONObject().put("label","贴图参考 PNG").put("required",true).put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024).put("maxPixels",4194304))
            .put("source_mesh",new JSONObject().put("label","待贴图网格（最多 30 万三角面的静态 GLB）").put("required",true).put("mimes",new JSONArray().put(GlbFile.MIME)).put("maxBytes",256*1024*1024));
        return new InputSpec(roles,"选择参考 PNG 与待贴图 GLB；固定六视图，生成 albedo / metallic-roughness 并重新展开 UV。不可见区域使用临近可见纹理填充。所有阶段在手机 CPU；512 分辨率导出须关闭 4× 增强以满足图集内存保护。")
            .withFixedPrompt(SpatialSpec.PROMPT).withNegativePrompt(false);
    }
    public static void sourceMesh(File file)throws Exception {SpatialSpec.coarse(file);if(GlbFile.inspect(file).getLong("triangles")>300000)throw new IOException("请先将待贴图 GLB 简化至 30 万三角面以内");}
}
