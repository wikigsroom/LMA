package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Fixed same-phone UltraTex asset and input contract. No downloaded code. */
public final class UltraTexSpec {
    private UltraTexSpec() {}
    public static boolean matches(String pipeline){return pipeline.equals("ultratex_flux1")||pipeline.equals("ultratex_flux2");}
    private static boolean one(String pipeline)throws IOException {if(!matches(pipeline))throw new IOException("请选择匹配的 UltraTex 本地配方");return pipeline.endsWith("1");}
    public static Map<String,String> layout(String pipeline)throws IOException {
        boolean one=one(pipeline);Map<String,String> r=new LinkedHashMap<>();r.put("config","ultratex-config.json");r.put("tokenizer",one?"t5.model":"qwen-tokenizer.json");
        if(one)r.put("clip_tokenizer","clip-tokenizer.json");
        List<String> graphs=new ArrayList<>(Arrays.asList("text","vae_encoder","albedo_flow","mr_flow","albedo_decoder","mr_decoder"));if(one)graphs.add("clip");
        for(String graph:graphs){r.put(graph,graph+".onnx");r.put(graph+"_data",graph+".onnx.data");}return Collections.unmodifiableMap(r);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        one(b.pipeline);if(!b.architecture.equals(b.pipeline)||!b.engine.equals("spatial_ort")||!b.backend.equals("cpu")||!b.tasks.equals(Collections.singleton("3d"))||!type.equals("mesh.generate"))throw new IOException("UltraTex 需要匹配的本地 CPU 材质配方");
        Map<String,String> layout=layout(b.pipeline);Set<String> missing=new HashSet<>();for(String key:layout.keySet())if(!key.endsWith("_data"))missing.add(key);
        for(ModelBundle.Component c:b.components){String name=layout.get(c.role);if(name==null)throw new IOException("未知 UltraTex 组件："+c.role);
            String format=name.endsWith(".json")?"json":name.endsWith(".model")?"sentencepiece":name.endsWith(".data")?"onnx_data":"onnx";
            long maximum=c.role.equals("config")?65536:format.equals("json")?32L*1024*1024:format.equals("sentencepiece")?16L*1024*1024:format.equals("onnx")?128L*1024*1024:32L*1024*1024*1024;
            if(!new File(c.path).getName().equals(name)||!c.format.equals(format)||c.bytes>maximum)throw new IOException("UltraTex 组件名称、格式或大小不匹配："+c.role);missing.remove(c.role);
        }if(!missing.isEmpty())throw new IOException("UltraTex 缺少同批转换组件："+missing);
    }
    private static int dimension(JSONObject c,String key,int lo,int hi)throws Exception {Object raw=c.get(key);double value=c.getDouble(key);int n=c.getInt(key);if(!(raw instanceof Number)||!Double.isFinite(value)||value!=n||n<lo||n>hi)throw new IOException("UltraTex 配置尺寸无效："+key);return n;}
    public static void checkConfig(String pipeline,JSONObject c)throws Exception {
        boolean one=one(pipeline);JSONObject source=c.getJSONObject("source");
        if(!c.getString("schema").equals("lma.ultratex-export/1")||!c.getString("pipeline").equals(pipeline)||!c.getString("dtype").equals("float32")||c.getInt("opset")!=17||!source.getString("repository").equals("yiboz2001/UltraTex")||!source.getString("revision").equals("a726678f3f3631fe2c5e3d1fb4597114784c7a8b")||!c.getString("cameraRig").equals("lma_orthographic_y_up_six_v1")||c.getInt("textLength")!=512||!(c.get("guidanceEmbedding") instanceof Boolean)||one&&!c.getBoolean("guidanceEmbedding"))throw new IOException("UltraTex 来源、文本或相机配置不匹配");
        int size=dimension(c,"imageSize",32,512),channels=dimension(c,"latentChannels",4,128),vocab=dimension(c,"textVocab",32,300000);
        dimension(c,"textWidth",8,12288);dimension(c,"textPad",0,vocab-1);if(size%16!=0||channels%4!=0)throw new IOException("UltraTex 图像或潜变量对齐无效");
        if(one){dimension(c,"clipWidth",8,4096);int cv=dimension(c,"clipVocab",32,300000);dimension(c,"clipPad",0,cv-1);if(c.getInt("clipLength")!=77)throw new IOException("UltraTex CLIP 长度不匹配");}
    }
    private static JSONObject f(String type,String label,Number value,Number lo,Number hi)throws Exception {return new JSONObject().put("type",type).put("label",label).put("default",value).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema(String pipeline,JSONObject config)throws Exception {
        boolean one=one(pipeline);if(config!=null)checkConfig(pipeline,config);
        JSONObject fields=new JSONObject().put("threads",f("integer","CPU 线程",2,1,16)).put("steps",f("integer","每种材质采样步数",25,1,100))
            .put("seed",f("integer","随机种子",0,0,Integer.MAX_VALUE)).put("guidance",f("number","材质引导强度",one?4:3.5,0,15))
            .put("atlas",f("integer","UV 图集目标尺寸",1024,256,4096).put("multipleOf",256));
        if(!one)fields.put("dropBackground",new JSONObject().put("type","boolean").put("label","省略背景 token").put("default",false));
        return new JSONObject().put("version",1).put("fields",fields);
    }
    public static InputSpec inputs()throws Exception {
        JSONObject roles=MaterialSpec.inputs().json().getJSONObject("roles");
        return new InputSpec(roles,"输入物体的材质描述，选择参考 PNG 和已有 GLB；手机完成文本编码、六视图条件、两种材质采样、解码、UV 和 PBR。便携相机和 CPU 计算与训练环境存在差异。").withNegativePrompt(false);
    }
}
