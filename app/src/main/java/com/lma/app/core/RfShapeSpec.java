package com.lma.app.core;

import java.io.*;
import java.nio.file.Files;
import java.util.*;
import org.json.*;

/** Matched CPU RF/SDF exports, not arbitrary ONNX or raw PyTorch models. */
public final class RfShapeSpec {
    private RfShapeSpec() {}
    public static final String PROMPT="Generate local 3D geometry from the selected image.";
    public static Map<String,String> layout() {
        Map<String,String> f=new LinkedHashMap<>();f.put("config","shape-config.json");
        for(String role:new String[]{"image_encoder","flow","cache","query"}) {f.put(role,role+".onnx");f.put(role+"_data",role+".onnx.data");}
        return Collections.unmodifiableMap(f);
    }
    private static boolean parts(String pipeline)throws IOException {
        if(!pipeline.equals("triposg")&&!pipeline.equals("partcrafter")&&!pipeline.equals("partcrafter_scene"))throw new IOException("请选择已匹配的 TripoSG / PartCrafter 配方");
        return !pipeline.equals("triposg");
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        boolean p=parts(b.pipeline);
        if(!b.engine.equals("rf_shape_ort")||!b.backend.equals("cpu")||!b.architecture.equals(p?"partcrafter":"triposg")||!type.equals("mesh.generate")||!b.tasks.equals(Collections.singleton("3d")))
            throw new IOException("需要匹配的 RF Shape CPU 形状配方");
        Set<String> missing=new HashSet<>(Arrays.asList("config","image_encoder","flow","cache","query"));
        for(ModelBundle.Component c:b.components) {
            String file=layout().get(c.role),format=c.role.equals("config")?"json":c.role.endsWith("_data")?"onnx_data":"onnx";
            if(file==null||!c.format.equals(format)||!new File(c.path).getName().equals(file))throw new IOException("形状组件角色、格式或导出文件名不匹配："+c.role);
            if(c.role.equals("config")&&c.bytes>65536||format.equals("onnx")&&c.bytes>128L*1024*1024||c.bytes>32L*1024*1024*1024)throw new IOException("形状组件超出导出范围");
            missing.remove(c.role);
        }
        if(!missing.isEmpty())throw new IOException("形状配方缺少必需组件："+missing);
    }
    private static JSONObject f(String type,String label,Number value,Number min,Number max)throws Exception {
        return new JSONObject().put("type",type).put("label",label).put("default",value).put("minimum",min).put("maximum",max).put("limitSource","application_guard");
    }
    public static JSONObject schema(String pipeline)throws Exception {
        boolean p=parts(pipeline);
        return new JSONObject().put("version",1).put("fields",new JSONObject()
            .put("threads",f("integer","CPU 线程",2,1,16)).put("steps",f("integer","形状采样步数",30,1,100))
            .put("seed",f("integer","随机种子",1234,0,Integer.MAX_VALUE))
            .put("tokens",f("integer","每部件潜变量 token",pipeline.equals("partcrafter")?1024:2048,512,4096).put("multipleOf",512))
            .put("parts",f("integer","部件数量",p?3:1,1,p?16:1))
            .put("grid",f("integer","SDF 网格单轴格数",64,32,256).put("multipleOf",16))
            .put("queryChunk",f("integer","SDF 分块查询点数",512,128,4096))
            .put("guidance",f("number","图像引导强度",7,0,15)).put("maxTriangles",f("integer","全部部件三角面保护上限",300000,1000,1000000)));
    }
    public static JSONObject parameters(String pipeline,JSONObject requested)throws Exception {return new ParameterSchema(schema(pipeline)).normalize(new JSONObject(),requested);}
    public static void reference(File file)throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()>16L*1024*1024)throw new IOException("需要最多 16 MiB 的本地 PNG");
        try(DataInputStream in=new DataInputStream(new FileInputStream(file))) {
            if(in.readLong()!=0x89504e470d0a1a0aL||in.readInt()!=13||in.readInt()!=0x49484452)throw new IOException("形状输入只接受 PNG");
            long w=Integer.toUnsignedLong(in.readInt()),h=Integer.toUnsignedLong(in.readInt());int depth=in.readUnsignedByte(),color=in.readUnsignedByte();
            if(w<1||h<1||w>4194304||h>4194304||w*h>4194304||depth!=8||(color!=2&&color!=6))throw new IOException("需要最多四百万像素的 8-bit RGB / RGBA PNG");
        }
    }
    public static InputSpec inputs()throws Exception {
        return new InputSpec(new JSONObject().put("reference_image",new JSONObject().put("label","已去背景 / 白底物体 PNG").put("required",true)
            .put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024).put("maxPixels",4194304)),
            "选择已经去背景或白底的 PNG。透明区域明确合成白色；不自动分割。部件处于模型共同坐标系，输出一个含独立部件的 GLB，无贴图。")
            .withFixedPrompt(PROMPT).withNegativePrompt(false);
    }
}
