package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.util.*;

/** Two fixed local image-preparation architectures, with user-selected assets. */
public final class VisionSpec {
    private VisionSpec() {}
    public static boolean foreground(String pipeline){return pipeline.equals("isnet_dis");}
    public static Map<String,String> layout(String pipeline){
        Map<String,String> files=new LinkedHashMap<>();
        if(foreground(pipeline)){files.put("config","vision-config.json");files.put("foreground","foreground.onnx");files.put("foreground_data","foreground.onnx.data");}
        else if(pipeline.equals("vlm_parts")){files.put("model","model.gguf");files.put("mmproj","mmproj.gguf");}
        return Collections.unmodifiableMap(files);
    }
    public static void validate(ModelBundle b,String type)throws Exception {
        boolean fg=foreground(b.pipeline);Map<String,String> files=layout(b.pipeline);
        if(files.isEmpty()||!b.engine.equals("vision_cpu")||!b.backend.equals("cpu")||!b.architecture.equals(fg?"isnet_dis":"mtmd_vlm")||!b.tasks.equals(Collections.singleton(fg?"image":"text"))||!type.equals(fg?"image.generate":"text.generate"))throw new IOException("请选择匹配的本机视觉配方");
        Set<String> missing=new HashSet<>(files.keySet());missing.remove("foreground_data");
        for(ModelBundle.Component c:b.components){String name=files.get(c.role),format=fg?(c.role.equals("config")?"json":c.role.endsWith("_data")?"onnx_data":"onnx"):"gguf";
            if(name==null||!c.format.equals(format)||c.bytes<1||c.bytes>32L*1024*1024*1024||fg&&!new File(c.path).getName().equals(name)||c.role.equals("config")&&c.bytes>65536||format.equals("onnx")&&c.bytes>128L*1024*1024)throw new IOException("视觉组件不匹配："+c.role);missing.remove(c.role);}
        if(!missing.isEmpty())throw new IOException("缺少已选择的视觉组件："+missing);
    }
    private static JSONObject field(String label,int value,int lo,int hi)throws Exception{return new JSONObject().put("type","integer").put("label",label).put("default",value).put("minimum",lo).put("maximum",hi).put("limitSource","application_guard");}
    public static JSONObject schema(String pipeline,int trainedContext)throws Exception {
        JSONObject fields=new JSONObject().put("threads",field("CPU 线程",2,1,16));
        if(!foreground(pipeline)){int bound=trainedContext>=512?Math.min(trainedContext,16384):16384;fields.put("context",field("视觉上下文",Math.min(4096,bound),512,bound).put("limitSource",trainedContext>=512?"gguf_context_length":"application_guard_unknown_metadata"));
            fields.put("maxTokens",field("部件识别输出上限",Math.min(512,bound-1),32,Math.min(2048,bound-1)).put("maximumFrom",new JSONObject().put("field","context").put("offset",-1)));fields.put("imageTokens",field("图像 token 上限",Math.min(1024,bound-1),64,Math.min(4096,bound-1)).put("maximumFrom",new JSONObject().put("field","context").put("offset",-1)));}
        return new JSONObject().put("version",1).put("fields",fields);
    }
    public static InputSpec inputs()throws Exception {return new InputSpec(new JSONObject().put("reference_image",new JSONObject().put("label","本地 RGB / RGBA PNG").put("required",true).put("mimes",new JSONArray().put("image/png")).put("maxBytes",16*1024*1024)),"选择 PNG；由已选择的手机本地视觉模型处理，不自动下载模型。").withFixedPrompt("Prepare the selected local image.").withNegativePrompt(false);}
    public static int partCount(File result)throws Exception {
        JSONObject root=new JSONObject(TextResult.read(result).getString("content"));JSONArray parts=root.getJSONArray("parts");if(root.length()!=1||parts.length()<1||parts.length()>16)throw new IOException("部件识别结果无效");Set<String> names=new HashSet<>();
        for(int i=0;i<parts.length();i++){JSONObject part=parts.getJSONObject(i);String name=part.getString("name");if(part.length()!=1||name.trim().isEmpty()||name.length()>128||!names.add(name)||name.chars().anyMatch(c->c<32))throw new IOException("部件名称无效或重复");}return parts.length();
    }
}
