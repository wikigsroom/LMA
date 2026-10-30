package com.lma.app.core;

import org.json.*;
import java.util.*;

/** Original old LTX 0.9.8 PixArt T5 and publisher 7+3 multi-scale schedule. */
public final class LtxPixArtSpec {
    private LtxPixArtSpec() {}
    public static final String PIPELINE="ltx098_pixart_multiscale_v1", PROFILE="ltx098_pixart_7_plus_3_v1";
    public static Map<String,String> files() {
        Map<String,String> result=new LinkedHashMap<>(Ltx098Spec.files());result.remove("text_encoder");
        result.put("text_config","text-config.json");result.put("text_index","model.safetensors.index.json");
        result.put("text_shard_1","model-00001-of-00002.safetensors");result.put("text_shard_2","model-00002-of-00002.safetensors");
        result.put("tokenizer","spiece.model");result.put("upscaler","ltx098-upscaler.onnx.data");return Collections.unmodifiableMap(result);
    }
    public static void validate(ModelBundle b,String type) throws Exception {
        if(!b.engine.equals("ltx098_native") || !b.architecture.equals("ltx098") || !b.pipeline.equals(PIPELINE) || !b.backend.equals("vulkan") || !type.equals("video.generate"))throw new IllegalArgumentException("请选择旧 LTX PixArt 多尺度运行模型");
        JSONArray capabilities=b.json().optJSONArray("capabilities");boolean video=false;
        if(capabilities!=null)for(int i=0;i<capabilities.length();i++)video|=capabilities.getString(i).equals("text_to_video");
        if(!video)throw new IllegalArgumentException("此记录缺少文生视频能力");
        Set<String> expected=new HashSet<>(files().keySet());
        for(ModelBundle.Component c:b.components) {
            if(!expected.remove(c.role))throw new IllegalArgumentException("旧 LTX 多尺度组件重复或不受支持："+c.role);
            String format=c.role.equals("diffusion_model")?"gguf":c.role.startsWith("text_shard_") || c.role.equals("upscaler")?"safetensors":c.role.equals("tokenizer")?"sentencepiece":c.role.startsWith("vae_graph_")?"onnx":c.role.startsWith("vae_data_")?"onnx_data":"json";
            if(!c.format.equals(format) || ((format.equals("json") || format.equals("onnx")) && c.bytes>1024*1024))throw new IllegalArgumentException("旧 LTX 多尺度组件格式不匹配："+c.role);
        }
        if(!expected.isEmpty())throw new IllegalArgumentException("缺少官方 PixArt T5、空间放大器或完整 DiT / 九段 VAE");
        identity(b,"text_config",788,"9a2865cce66d6dbfdc0fd185faed2394344fc5f61b2cbf9579ca2e6dc882f927");
        identity(b,"text_index",19886,"fb4665a1a122b7e5270f0e4494c653839c11a5a978e03b0df6dfa714258716e6");
        identity(b,"text_shard_1",9989150328L,"eb529f693f4b17773a24e787fcba29486d5e1700dadcc20bb91e4c8b00212d08");
        identity(b,"text_shard_2",9060119392L,"58f33f4acba7a5502b6b3e4cb7863f8fd503d5012016428099bb460c98e2fe77");
        identity(b,"tokenizer_config",20509,"71730771351a8f0463bd2e545fbfaadc9dc01a7a222306ff4795cc48dfe168c0");
        identity(b,"tokenizer",791656,"d60acb128cf7b7f2536e8f38a5b18a05535c9e14c7a355904270e15b0945ea86");
        identity(b,"upscaler",505024432,"5b076031c6f860db9037a54f3bb819f10bfb5532ea26a6d30062292428a0c208");
    }
    private static void identity(ModelBundle b,String role,long bytes,String sha) {
        ModelBundle.Component c=b.component(role);if(c.bytes!=bytes || !c.sha256.equals(sha))throw new IllegalArgumentException("需要与配方匹配的官方组件："+role);
    }
    public static JSONObject schema() throws Exception {
        JSONObject schema=Ltx098Spec.schema(),fields=schema.getJSONObject("fields");
        for(String key:Arrays.asList("width","height"))fields.getJSONObject(key).put("minimum",128);
        fields.getJSONObject("steps").put("default",10).put("minimum",10).put("maximum",10).put("help","官方多尺度调度：7 步初次生成、空间放大和 AdaIN、3 步细化。");return schema;
    }
    public static JSONObject parameters(JSONObject values) throws Exception {return new ParameterSchema(schema()).normalize(new JSONObject(),values);}
    public static int firstExtent(int requested) {int value=(int)(requested*.6666666);return value-value%32;}
    public static JSONObject plan(JSONObject parameters) throws Exception {
        int width=firstExtent(parameters.getInt("width")),height=firstExtent(parameters.getInt("height"));
        return new JSONObject().put("profile",PROFILE).put("parameters",DataFiles.copy(parameters)).put("textVariant","pixart_original_f32")
            .put("pipelineKind","multi_scale").put("firstWidth",width).put("firstHeight",height).put("secondWidth",width*2).put("secondHeight",height*2)
            .put("firstTimesteps",new JSONArray("[1,0.9937,0.9875,0.9812,0.975,0.9094,0.725]"))
            .put("secondTimesteps",new JSONArray("[0.9094,0.725,0.4219]"))
            .put("downscaleFactor",.6666666).put("guidanceScale",1).put("stgScale",0).put("spatialUpscaler","ltxv-spatial-upscaler-0.9.8")
            .put("adain",true).put("resize","bilinear_align_corners_false").put("decodeTimestep",.05).put("decodeNoiseScale",.025)
            .put("promptEnhancement",false).put("rng","lma_splitmix64_box_muller_f32_v1").put("matchesPytorchSeed",false)
            .put("qualityAccepted",false).put("numericalAccepted",false);
    }
}
