package com.lma.app.core;

import java.io.IOException;
import java.io.File;
import java.io.DataInputStream;
import java.io.FileInputStream;
import java.nio.file.Files;
import java.util.*;
import org.json.*;

/** Four posed Pixal3D views; the MV family is independent of the single-view recipes. */
public final class MultiViewSpec {
    private MultiViewSpec() {}
    public static final String PROMPT="Generate one 3D asset from four posed local views.";
    public static final String[] ROLES={"reference_front","reference_right","reference_back","reference_left"};
    public static final String[] FILES={"00_front.png","01_right.png","02_back.png","03_left.png"};
    public static Map<String,String> layout() {
        Map<String,String> f=new LinkedHashMap<>();
        f.put("image_encoder","dinov3.gguf");f.put("naf","pixal3d_naf.gguf");f.put("ss_decoder","ss_dec.gguf");
        f.put("shape_decoder","shape_dec.gguf");f.put("texture_decoder","tex_dec.gguf");
        f.put("ss_flow","pixal3d_ss_flow_mv.gguf");f.put("shape_flow","pixal3d_shape_flow_512_mv.gguf");
        f.put("shape_flow_hr","pixal3d_shape_flow_1024_mv.gguf");f.put("texture_flow_hr","pixal3d_tex_flow_1024_mv.gguf");
        return Collections.unmodifiableMap(f);
    }
    public static void validate(ModelBundle b,String type) throws Exception {
        if(!b.engine.equals("pixal_multiview")||!b.pipeline.equals("pixal3d_mv")||!b.architecture.equals("pixal3d_mv")||
           !b.backend.equals("cpu")||!type.equals("mesh.generate")||!b.tasks.equals(Collections.singleton("3d")))
            throw new IOException("请选择匹配的 Pixal3D 多视图配方");
        Set<String> required=new HashSet<>(layout().keySet());required.remove("texture_decoder");required.remove("texture_flow_hr");
        for(ModelBundle.Component c:b.components) {
            if(!layout().containsKey(c.role)||!c.format.equals("gguf"))throw new IOException("多视图组件角色或格式不匹配："+c.role);
            required.remove(c.role);
        }
        if(!required.isEmpty())throw new IOException("多视图配方缺少必需组件："+required);
    }
    private static JSONObject number(String type,String label,Number value,Number min,Number max)throws Exception{
        return new JSONObject().put("type",type).put("label",label).put("default",value).put("minimum",min).put("maximum",max).put("limitSource","application_guard");
    }
    public static JSONObject schema()throws Exception{
        JSONObject f=new JSONObject().put("threads",number("integer","CPU 线程",2,1,16))
          .put("resolution",number("integer","3D 生成分辨率",1024,1024,1024))
          .put("steps",number("integer","每阶段采样步数",12,1,50))
          .put("seed",number("integer","随机种子",1234,1,2147483647))
          .put("faces",number("integer","输出网格面数目标",30000,1000,150000))
          .put("atlas",number("integer","贴图图集尺寸",1024,256,2048).put("multipleOf",256))
          .put("guidance",number("number","引导强度",7.5,0,15))
          .put("maxTokens",number("integer","稀疏 token 保护上限",8192,1024,49152))
          .put("meshScale",number("number","相机对应的网格尺度",1,0.1,10))
          .put("texture",new JSONObject().put("type","boolean").put("label","生成贴图").put("default",true))
          .put("cameraPoses",new JSONObject().put("type","string").put("label","四视图相机参数（留空使用标准转台）").put("default","").put("maxLength",16000));
        return new JSONObject().put("version",1).put("fields",f);
    }
    public static JSONObject parameters(JSONObject requested)throws Exception{
        JSONObject r=new ParameterSchema(schema()).normalize(new JSONObject(),requested);
        cameras(r.getJSONObject("values").getString("cameraPoses"));return r;
    }
    /** Strict data-only camera contract; no input filenames, URLs or executable fields. */
    public static void cameras(String text)throws Exception{
        if(text.isEmpty())return;
        JSONObject j=new JSONObject(text);
        if(j.length()!=1||!j.has("frames"))throw new IOException("相机参数只能包含 frames");
        JSONArray frames=j.getJSONArray("frames");if(frames.length()!=4)throw new IOException("需要按前、右、后、左提供四个相机");
        for(int i=0;i<4;i++){
            JSONObject f=frames.getJSONObject(i);
            if(f.length()!=2||!f.has("transform_matrix")||!f.has("camera_angle_x"))throw new IOException("相机需要 transform_matrix 与弧度制 camera_angle_x");
            Object raw=f.get("camera_angle_x");
            if(!(raw instanceof Number)||!Double.isFinite(((Number)raw).doubleValue())||((Number)raw).doubleValue()<=0||((Number)raw).doubleValue()>=Math.PI)throw new IOException("相机水平视角必须在 0 与 π 弧度之间");
            JSONArray a=f.getJSONArray("transform_matrix");if(a.length()!=4)throw new IOException("相机必须是 4×4 矩阵");double[][] m=new double[4][4];
            for(int row=0;row<4;row++){
                JSONArray line=a.getJSONArray(row);if(line.length()!=4)throw new IOException("相机必须是 4×4 矩阵");
                for(int col=0;col<4;col++){Object n=line.get(col);if(!(n instanceof Number)||!Double.isFinite(((Number)n).doubleValue())||Math.abs(((Number)n).doubleValue())>10000)throw new IOException("相机数值无效");m[row][col]=((Number)n).doubleValue();}
            }
            for(int col=0;col<4;col++)if(Math.abs(m[3][col]-(col==3?1:0))>1e-6)throw new IOException("相机必须是仿射变换");
            double distance=0;for(int row=0;row<3;row++)distance+=m[row][3]*m[row][3];if(distance<1e-12)throw new IOException("相机不能位于原点");
            for(int x=0;x<3;x++)for(int y=0;y<3;y++){double dot=0;for(int row=0;row<3;row++)dot+=m[row][x]*m[row][y];if(Math.abs(dot-(x==y?1:0))>1e-3)throw new IOException("相机旋转必须正交且不含缩放");}
            double det=m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0]);
            if(Math.abs(det-1)>1e-3)throw new IOException("相机旋转不能包含镜像");
        }
    }
    public static void assets(ModelBundle b,JSONObject p)throws Exception{
        if(p.getBoolean("texture")){b.component("texture_decoder");b.component("texture_flow_hr");}
    }
    public static void reference(File file)throws Exception{
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()>16L*1024*1024)throw new IOException("需要本地、最多 16 MiB 的四视图图片");
        try(DataInputStream in=new DataInputStream(new FileInputStream(file))){
            if(in.readLong()!=0x89504e470d0a1a0aL||in.readInt()!=13||in.readInt()!=0x49484452)throw new IOException("四视图只接受 RGBA PNG");
            long width=Integer.toUnsignedLong(in.readInt()),height=Integer.toUnsignedLong(in.readInt());
            if(width<1||height<1||width>4194304||height>4194304||width*height>4194304||in.readUnsignedByte()!=8||in.readUnsignedByte()!=6||in.readUnsignedByte()!=0||in.readUnsignedByte()!=0||in.readUnsignedByte()>1)
                throw new IOException("四视图需要最多 4 百万像素的 8-bit RGBA PNG，请先去除背景");
        }
    }
    public static InputSpec inputs()throws Exception{
        JSONObject roles=new JSONObject();String[] labels={"正面","右侧","背面","左侧"};
        for(int i=0;i<4;i++)roles.put(ROLES[i],new JSONObject().put("label",labels[i]+" · 已去背景的 RGBA PNG")
          .put("required",true).put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024).put("maxPixels",4194304));
        return new InputSpec(roles,"四张图片必须来自同一物体并符合所选相机。标准转台：20° 水平视角、零仰角、距离 3.119204998；不得将任意照片当作已标定视图。")
          .withFixedPrompt(PROMPT).withNegativePrompt(false);
    }
}
