package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Contract for the pinned Arm SAO Small TFLite export; not arbitrary audio TFLite. */
public final class StableAudioSpec {
    private StableAudioSpec() {}
    public static final String PIPELINE="stable_audio_small_litert_v1";
    public static void validate(ModelBundle b,String type) throws Exception {
        if(!b.engine.equals("stable_audio_litert") || !b.backend.equals("cpu") || !b.pipeline.equals(PIPELINE) || !b.architecture.equals("stable_audio_open_small"))throw new IOException("需要匹配的 Stable Audio Open Small LiteRT CPU 配方");
        if(!type.equals("audio.generate") || !b.tasks.equals(Collections.singleton("audio")))throw new IOException("此配方提供英文提示词到短音频任务");
        Set<String> roles=new HashSet<>(Arrays.asList("conditioner","diffusion_model","audio_decoder","tokenizer"));
        for(ModelBundle.Component c:b.components) {
            boolean tokenizer=c.role.equals("tokenizer");
            if(!roles.remove(c.role) || !c.format.equals(tokenizer?"sentencepiece":"tflite") || !c.path.toLowerCase(Locale.ROOT).endsWith(tokenizer?".model":".tflite"))throw new IOException("须选择同版三个 TFLite 图及配套 SentencePiece .model 词表");
            if(tokenizer && c.bytes>16*1024*1024)throw new IOException("词表不能超过 16 MiB");
        }
        if(!roles.isEmpty())throw new IOException("缺少 Stable Audio 组件："+roles);
    }
    private static JSONObject field(double value,double low,double high) throws Exception { return new JSONObject().put("type","integer").put("default",value).put("minimum",low).put("maximum",high); }
    public static JSONObject schema() throws Exception {
        return new JSONObject().put("version",1).put("fields",new JSONObject().put("threads",field(4,1,32)).put("seed",field(-1,-1,Integer.MAX_VALUE))
            .put("seconds",field(5,1,11)).put("steps",field(8,1,32)).put("maxInputTokens",field(64,1,64)));
    }
    public static JSONObject parameters(JSONObject values) throws Exception { return new ParameterSchema(schema()).normalize(new JSONObject(),values); }
    public static String text(JSONObject input) throws Exception {
        String s=TtsSpec.text(input);
        if(s.indexOf('\0')>=0)throw new IOException("提示词不能包含 NUL");
        JSONArray refs=input.optJSONArray("artifacts");if(refs!=null && refs.length()>0)throw new IOException("此导出不接受参考音频或图像");
        if(!input.optString("negativePrompt").isEmpty())throw new IOException("此蒸馏配方不使用负面提示词或 CFG");
        return s;
    }
}
