package com.lma.app.core;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import org.json.*;

/** Matched Hunyuan shape and coarse-mesh UltraShape refinement exports. */
public final class SpatialSpec {
    private SpatialSpec() {}
    public static final String PROMPT="Generate local 3D geometry from the explicitly selected inputs.";
    public static boolean ultra(String pipeline)throws IOException {
        if(!pipeline.equals("hunyuan3d_21_shape")&&!pipeline.equals("ultrashape_1_refine"))throw new IOException("请选择匹配的 Hunyuan3D 2.1 形状或 UltraShape 精修配方");
        return pipeline.equals("ultrashape_1_refine");
    }
    public static Map<String,String> layout() {
        Map<String,String> result=new LinkedHashMap<>(RfShapeSpec.layout());result.put("config","spatial-config.json");return Collections.unmodifiableMap(result);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        boolean u=ultra(b.pipeline);
        if(!b.engine.equals("spatial_ort")||!b.backend.equals("cpu")||!b.architecture.equals(u?"ultrashape_1":"hunyuan3d_21")||!type.equals("mesh.generate")||!b.tasks.equals(Collections.singleton("3d")))throw new IOException("需要匹配的本地 Spatial CPU 配方");
        Set<String> missing=new HashSet<>(Arrays.asList("config","image_encoder","flow","cache","query"));
        for(ModelBundle.Component c:b.components){
            String name=layout().get(c.role),format=c.role.equals("config")?"json":c.role.endsWith("_data")?"onnx_data":"onnx";
            if(name==null||!format.equals(c.format)||!new File(c.path).getName().equals(name))throw new IOException("Spatial 组件角色、格式或导出文件名不匹配："+c.role);
            if(c.role.equals("config")&&c.bytes>65536||format.equals("onnx")&&c.bytes>128L*1024*1024||c.bytes>32L*1024*1024*1024)throw new IOException("Spatial 组件超出导出范围");
            missing.remove(c.role);
        }
        if(!missing.isEmpty())throw new IOException("Spatial 配方缺少必需组件："+missing);
    }
    private static JSONObject f(String type,String label,Number value,Number min,Number max)throws Exception {
        return new JSONObject().put("type",type).put("label",label).put("default",value).put("minimum",min).put("maximum",max).put("limitSource","application_guard");
    }
    public static JSONObject schema(String pipeline)throws Exception {return schema(pipeline,null);}
    public static JSONObject schema(String pipeline,JSONObject config)throws Exception {
        boolean u=ultra(pipeline);int max=32768;
        if(config!=null){checkConfig(pipeline,config);max=Math.min(config.getInt("maxTokens"),(32000000/config.getInt("decoderWidth")/512)*512);}
        JSONObject result=new JSONObject().put("version",1).put("fields",new JSONObject()
            .put("threads",f("integer","CPU 线程",2,1,16)).put("steps",f("integer","形状采样步数",30,1,100))
            .put("seed",f("integer","随机种子",1234,0,Integer.MAX_VALUE))
            .put("tokens",f("integer","形状潜变量 token",Math.min(max,u?8192:4096),512,max).put("multipleOf",512))
            .put("grid",f("integer","SDF 网格单轴格数",64,32,256).put("multipleOf",16))
            .put("queryChunk",f("integer","SDF 分块查询点数",512,128,4096))
            .put("guidance",f("number","图像引导强度",5,0,15)).put("maxTriangles",f("integer","三角面保护上限",300000,1000,1000000))
            .put("meshScale",f("number","粗网格归一化半边长",.99,.1,1)).put("surfaceSamples",f("integer","粗网格表面采样点",65536,1024,409600)));
        if(!u){result.getJSONObject("fields").remove("meshScale");result.getJSONObject("fields").remove("surfaceSamples");}
        return result;
    }
    private static int dimension(JSONObject c,String key,int lo,int hi)throws Exception {
        Object raw=c.get(key);double value=c.getDouble(key);int n=c.getInt(key);
        if(!(raw instanceof Number)||!Double.isFinite(value)||value!=n||n<lo||n>hi)throw new IOException("Spatial 导出尺寸无效："+key);return n;
    }
    public static void checkConfig(String pipeline,JSONObject c)throws Exception {
        boolean u=ultra(pipeline);JSONObject source=c.getJSONObject("source");
        if(!c.getString("schema").equals("lma.spatial-shape-export/1")||!c.getString("pipeline").equals(pipeline)||!c.getString("dtype").equals("float32")||c.getInt("opset")!=17||
            !source.getString("repository").equals(u?"PKU-YuanGroup/UltraShape-1.0":"Tencent-Hunyuan/Hunyuan3D-2.1")||
            !source.getString("revision").equals(u?"5e8dcef05df101ab00ab6cd5fdd0ed0c74fbca66":"82920d643c0dc2f7bfd7255f45f62d386edfe60c"))throw new IOException("Spatial 导出架构或来源版本不匹配");
        dimension(c,"latentChannels",1,512);dimension(c,"decoderWidth",8,4096);int im=dimension(c,"imageSize",28,1022);
        dimension(c,"processorSize",28,1024);int et=dimension(c,"encoderTokens",2,6000);dimension(c,"encoderWidth",8,4096);
        dimension(c,"maxTokens",512,32768);dimension(c,"voxelResolution",8,256);
        double shift=c.getDouble("scheduleShift"),border=c.getDouble("borderRatio"),box=c.getDouble("boxExtent");
        if(im%14!=0||et!=(im/14)*(im/14)+1||!Double.isFinite(shift)||shift<=0||shift>16||!(border>=0&&border<.5)||!(box>.5&&box<=1.1))throw new IOException("Spatial 图像或采样配置超出支持范围");
    }
    public static JSONObject readConfig(String pipeline,File file)throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()<2||file.length()>65536)throw new IOException("需要已验证的 spatial-config.json");
        JSONObject c=new JSONObject(new String(Files.readAllBytes(file.toPath()),StandardCharsets.UTF_8));checkConfig(pipeline,c);return c;
    }
    public static void coarse(File file)throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()>256L*1024*1024)throw new IOException("粗网格需要最多 256 MiB 的自包含 GLB");
        JSONObject m=GlbFile.inspect(file);if(m.getLong("triangles")<1||m.getLong("triangles")>1000000||m.getLong("vertices")>3000000)throw new IOException("粗网格超过一百万三角面或三百万顶点");
    }
    public static InputSpec inputs(String pipeline)throws Exception {
        boolean u=ultra(pipeline);JSONObject roles=new JSONObject().put("reference_image",new JSONObject().put("label","已去背景 / 白底物体 PNG").put("required",true)
            .put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024).put("maxPixels",4194304));
        if(u)roles.put("coarse_mesh",new JSONObject().put("label","待精修粗网格（自包含静态 GLB）").put("required",true).put("mimes",new JSONArray().put(GlbFile.MIME)).put("maxBytes",256*1024*1024));
        return new InputSpec(roles,u?"选择参考 PNG 和粗 GLB；仅精修几何，不自动制作初始网格。表面点按一半面积、一半锐边长度加权采样；粗网格须含可用锐边。":"选择已去背景或白底 PNG；生成无贴图几何。此配方不包含 Hunyuan3D Paint。")
            .withFixedPrompt(PROMPT).withNegativePrompt(false);
    }
}
