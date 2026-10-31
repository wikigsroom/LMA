package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.nio.file.Files;
import java.util.*;

/** Source-matched VAE reconstruction; never an image-flow substitute. */
public final class PointCloudSpec {
    private PointCloudSpec() {}
    public static boolean matches(String p) { return p.equals("triposg_points") || p.equals("partcrafter_points"); }
    public static Map<String,String> layout() {
        Map<String,String> result=new LinkedHashMap<>();result.put("config","shape-config.json");
        for(String role:new String[]{"encoder","cache","query"}) { result.put(role,role+".onnx");result.put(role+"_data",role+".onnx.data"); }
        return Collections.unmodifiableMap(result);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        if(!matches(b.pipeline)||!b.engine.equals("rf_shape_ort")||!b.backend.equals("cpu")||!b.architecture.equals(b.pipeline.equals("triposg_points")?"triposg":"partcrafter")||!type.equals("mesh.generate")||!b.tasks.equals(Collections.singleton("3d")))throw new IOException("请选择匹配的点云 VAE 配方");
        Set<String> missing=new HashSet<>(Arrays.asList("config","encoder","cache","query"));
        for(ModelBundle.Component c:b.components){String name=layout().get(c.role),format=c.role.equals("config")?"json":c.role.endsWith("_data")?"onnx_data":"onnx";
            if(name==null||!name.equals(new File(c.path).getName())||!format.equals(c.format)||c.bytes<1||c.bytes>32L*1024*1024*1024||c.role.equals("config")&&c.bytes>65536||format.equals("onnx")&&c.bytes>128L*1024*1024)throw new IOException("点云 VAE 组件不匹配");missing.remove(c.role);}
        if(!missing.isEmpty())throw new IOException("点云配方缺少组件："+missing);
    }
    private static JSONObject f(String label,int v,int lo,int hi)throws Exception{return new JSONObject().put("type","integer").put("label",label).put("default",v).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema()throws Exception {
        return SurfaceSpec.extend(new JSONObject().put("version",1).put("fields",new JSONObject().put("threads",f("CPU 线程",2,1,16)).put("seed",f("随机种子",1234,0,Integer.MAX_VALUE))
            .put("tokens",f("VAE 查询 token",2048,512,4096).put("multipleOf",512)).put("posterior",new JSONObject().put("type","enum").put("label","VAE 重建方式").put("default","mean").put("values",new JSONArray().put("mean").put("sample")))
            .put("grid",f("SDF 网格格数",64,32,256).put("multipleOf",16)).put("queryChunk",f("SDF 分块点数",512,128,4096)).put("maxTriangles",f("三角面保护上限",300000,1000,1000000))));
    }
    public static InputSpec inputs()throws Exception{return new InputSpec(new JSONObject().put("point_cloud",new JSONObject().put("label","XYZ＋法线点云 JSON 文本").put("required",true).put("mimes",new JSONArray().put(StructuredInput.MIME)).put("maxBytes",8*1024*1024)),"选择 .json 文件，内容为 lma.pointcloud/1 JSON；每点 [x,y,z,nx,ny,nz]，坐标须已归一化，法线须为单位向量。重建单个整体，不运行图片扩散。最多 16,384 点；点数×token 受内存保护限制。")
        .withFixedPrompt("Reconstruct local 3D geometry from the selected point cloud.").withNegativePrompt(false);}
    public static void reference(File file)throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()<1||file.length()>8L*1024*1024)throw new IOException("请选择本地点云文本");
        JSONObject root=new JSONObject(new String(Files.readAllBytes(file.toPath()),java.nio.charset.StandardCharsets.UTF_8));
        if(root.length()!=3||!root.getString("schema").equals("lma.pointcloud/1")||!root.getString("coordinates").equals("publisher_normalized"))throw new IOException("点云格式不匹配");
        JSONArray rows=root.getJSONArray("points");if(rows.length()<16||rows.length()>16384)throw new IOException("点云数量超限");
        for(int i=0;i<rows.length();i++){JSONArray row=rows.getJSONArray(i);if(row.length()!=6)throw new IOException("每点须包含 XYZ 和法线");double norm=0;
            for(int j=0;j<6;j++){Object v=row.get(j);if(!(v instanceof Number)||!Double.isFinite(((Number)v).doubleValue())||Math.abs(((Number)v).doubleValue())>1.005)throw new IOException("点云坐标超出归一化范围");if(j>=3)norm+=Math.pow(((Number)v).doubleValue(),2);}
            if(norm<=.8||norm>=1.2)throw new IOException("点云法线需要单位长度");}
    }
}
