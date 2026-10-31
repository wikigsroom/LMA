package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Native TRELLIS.2/Pixal3D single-image routes; no remote nodes or Python plugins. */
public final class MeshSpec {
    private MeshSpec() {}
    public static Map<String,String> layout(String pipeline) throws IOException {
        if (!Arrays.asList("trellis2","pixal3d").contains(pipeline)) throw new IOException("当前生 3D 基座只支持 TRELLIS.2 / Pixal3D 单图路线");
        String prefix=pipeline.equals("pixal3d")?"pixal3d_":"";
        Map<String,String> files=new LinkedHashMap<>();
        files.put("image_encoder","dinov3.gguf"); files.put("ss_decoder","ss_dec.gguf"); files.put("shape_decoder","shape_dec.gguf");
        files.put("ss_flow",prefix+"ss_flow.gguf"); files.put("shape_flow",prefix+"shape_flow_512.gguf");
        files.put("shape_flow_hr",prefix+"shape_flow_1024.gguf"); files.put("texture_flow",prefix+"tex_flow_512.gguf");
        files.put("texture_flow_hr",prefix+"tex_flow_1024.gguf"); files.put("texture_decoder","tex_dec.gguf");
        files.put("background","birefnet.gguf"); if(!prefix.isEmpty()) files.put("naf","pixal3d_naf.gguf");
        return Collections.unmodifiableMap(files);
    }
    public static void validate(ModelBundle bundle,String type) throws Exception {
        if(!bundle.engine.equals("trellis_native") || !bundle.backend.equals("cpu") || !type.equals("mesh.generate") ||
           !bundle.tasks.equals(Collections.singleton("3d")) || !bundle.architecture.equals(bundle.pipeline.equals("trellis2")?"trellis2":"pixal3d"))
            throw new IOException("请选择匹配的本地生 3D 配方");
        Map<String,String> files=layout(bundle.pipeline);
        Set<String> required=new HashSet<>(Arrays.asList("image_encoder","ss_decoder","shape_decoder","ss_flow","shape_flow"));
        if(bundle.pipeline.equals("pixal3d"))required.add("naf");
        for(ModelBundle.Component c:bundle.components) {
            if(!files.containsKey(c.role)||!c.format.equals("gguf"))throw new IOException("3D 组件角色或格式不匹配："+c.role);
            required.remove(c.role);
        }
        if(!required.isEmpty())throw new IOException("生 3D 配方缺少必需组件："+required);
    }
    private static JSONObject field(String type,String label,Number value,Number low,Number high) throws Exception {
        return new JSONObject().put("type",type).put("label",label).put("default",value).put("minimum",low).put("maximum",high).put("limitSource","application_guard");
    }
    public static JSONObject schema(String pipeline) throws Exception {
        layout(pipeline);
        JSONObject f=new JSONObject().put("threads",field("integer","CPU 线程",2,1,16))
            .put("resolution",field("integer","3D 生成分辨率",512,512,1024).put("multipleOf",512).put("presets",new JSONArray().put(512).put(1024)))
            .put("steps",field("integer","每阶段采样步数",12,1,50)).put("seed",field("integer","随机种子",1234,0,2147483647))
            .put("faces",field("integer","输出网格面数目标",30000,1000,150000))
            .put("atlas",field("integer","贴图图集尺寸",1024,256,2048).put("multipleOf",256))
            .put("guidance",field("number","引导强度",7.5,0,15)).put("fov",field("number","相机水平视角（Pixal3D）",49.13,10,120))
            .put("texture",new JSONObject().put("type","boolean").put("label","生成贴图").put("default",!pipeline.equals("pixal3d")));
        return new JSONObject().put("version",1).put("fields",f);
    }
    public static JSONObject parameters(String pipeline,JSONObject values) throws Exception {
        JSONObject result=new ParameterSchema(schema(pipeline)).normalize(new JSONObject(),values), v=result.getJSONObject("values");
        if(pipeline.equals("pixal3d") && v.getInt("resolution")==512 && v.getBoolean("texture")) {
            v.put("texture",false); result.getJSONArray("adjustments").put(new JSONObject().put("field","texture").put("requested",true).put("effective",false).put("reason","pixal3d_has_no_512_texture_flow"));
        }
        return result;
    }
    public static InputSpec inputs() throws Exception {
        return new InputSpec(new JSONObject().put("reference_image",new JSONObject().put("label","单张物体参考图（建议透明背景 PNG）")
            .put("required",true).put("mimes",new JSONArray().put("image/png").put("image/jpeg")).put("maxBytes",16*1024*1024).put("maxPixels",4194304)),
            "由所选图片生成 GLB 网格；所有编码、采样、网格和贴图处理均在本机。").withFixedPrompt("Generate a 3D asset from the selected local image.").withNegativePrompt(false);
    }
    public static void assets(ModelBundle bundle,JSONObject params) throws Exception {
        boolean high=params.getInt("resolution")==1024, texture=params.getBoolean("texture");
        if(high)bundle.component("shape_flow_hr");
        if(texture) { bundle.component(high?"texture_flow_hr":"texture_flow"); bundle.component("texture_decoder"); }
    }
}
