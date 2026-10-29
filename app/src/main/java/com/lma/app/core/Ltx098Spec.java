package com.lma.app.core;

import org.json.*;
import java.util.*;
import java.nio.charset.StandardCharsets;

/** Explicit old-0.9.8 single-scale Google/community T5 Q5 variant, not the publisher default. */
public final class Ltx098Spec {
    private Ltx098Spec() {}
    public static final String PIPELINE = "ltx098_single_scale_google_q5";
    public static final String PROFILE = "ltx098_google_q5_linear_quadratic_8_v1";
    public static Map<String,String> files() {
        Map<String,String> result = new LinkedHashMap<>();
        result.put("diffusion_model", "ltx098-dit.gguf"); result.put("text_encoder", "t5.gguf"); result.put("tokenizer_config", "tokenizer_config.json");
        for (int i = 0; i < 9; i++) { String name = String.format(Locale.ROOT, "stage-%02d.onnx", i); result.put("vae_graph_" + i, name); result.put("vae_data_" + i, name + ".data"); }
        result.put("vae_manifest", "ltx098-vae.json"); return Collections.unmodifiableMap(result);
    }
    public static void validate(ModelBundle b, String type) throws Exception {
        if (!b.engine.equals("ltx098_native") || !b.architecture.equals("ltx098") || !b.pipeline.equals(PIPELINE) || !b.backend.equals("vulkan") || !type.equals("video.generate")) throw new IllegalArgumentException("请选择已关联的旧 LTX Google T5 Q5 运行模型；源模型需先准备资产");
        JSONArray capabilities=b.json().optJSONArray("capabilities"); boolean generation=false;
        if(capabilities!=null) for(int i=0;i<capabilities.length();i++) generation|=capabilities.getString(i).equals("text_to_video");
        if(!generation) throw new IllegalArgumentException("这是旧版运行资产记录；请在已准备资产中显式关联可生成的运行模型，原有文件与设置会保留");
        Set<String> expected = new HashSet<>(files().keySet());
        for (ModelBundle.Component c : b.components) {
            if (!expected.remove(c.role)) throw new IllegalArgumentException("旧 LTX 组件重复或不受支持：" + c.role);
            String format = c.role.equals("diffusion_model") || c.role.equals("text_encoder") ? "gguf" : c.role.startsWith("vae_graph_") ? "onnx" : c.role.startsWith("vae_data_") ? "onnx_data" : "json";
            if (!c.format.equals(format)) throw new IllegalArgumentException("旧 LTX 组件格式不匹配：" + c.role);
            if (format.equals("json") && c.bytes > 1024 * 1024 || format.equals("onnx") && c.bytes > 1024 * 1024) throw new IllegalArgumentException("旧 LTX 描述或图过大");
        }
        if (!expected.isEmpty()) throw new IllegalArgumentException("旧 LTX 缺少完整 DiT、T5、分词配置或九段 VAE");
    }
    public static JSONObject schema() throws Exception {
        JSONObject fields = new JSONObject();
        fields.put("width", integer(256,64,256).put("multipleOf",32)); fields.put("height", integer(256,64,256).put("multipleOf",32));
        fields.put("frames", integer(33,9,33).put("multipleOf",8).put("alignmentOrigin",1)); fields.put("fps", integer(24,1,60));
        fields.put("seed", integer(-1,-1,Integer.MAX_VALUE)); fields.put("threads", integer(4,1,8));
        fields.put("steps", integer(8,8,8).put("help", "此蒸馏配方固定八步；单尺度、CFG=1、STG=0，数值与画质尚未验收。"));
        return new JSONObject().put("version",1).put("fields",fields);
    }
    private static JSONObject integer(int value, int min, int max) throws Exception { return new JSONObject().put("type","integer").put("default",value).put("minimum",min).put("maximum",max); }
    public static JSONObject parameters(JSONObject values) throws Exception { return new ParameterSchema(schema()).normalize(new JSONObject(), values); }
    public static String prompt(JSONObject input) throws Exception {
        if (input.length() != 1 || !(input.opt("prompt") instanceof String)) throw new IllegalArgumentException("旧 LTX 目前仅接收完整文本提示词");
        String prompt = input.getString("prompt"); if (prompt.trim().isEmpty() || prompt.indexOf('\0') >= 0 || prompt.getBytes(StandardCharsets.UTF_8).length > 65536) throw new IllegalArgumentException("提示词须非空且不超过 64 KiB"); return prompt;
    }
    public static JSONObject plan(JSONObject parameters) throws Exception {
        return new JSONObject().put("profile",PROFILE).put("parameters",DataFiles.copy(parameters)).put("textVariant","google_community_t5_q5")
                .put("pipelineKind","single_scale").put("guidanceScale",1).put("stgScale",0).put("decodeTimestep",.05).put("decodeNoiseScale",.025)
                .put("promptEnhancement",false).put("qualityAccepted",false).put("numericalAccepted",false);
    }
}
