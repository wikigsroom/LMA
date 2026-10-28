package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.util.*;

/** Native first-class MOSS Delay layout; model/tokenizer/codec assets remain user-selected. */
public final class MossDelaySpec {
    private MossDelaySpec() {}
    public static boolean hasEncoder(ModelBundle bundle) { for(ModelBundle.Component c:bundle.components) if(c.role.equals("audio_encoder")) return true;return false; }
    public static void validate(ModelBundle bundle,String type) throws Exception {
        if(!bundle.engine.equals("moss_delay_native") || !bundle.pipeline.equals("moss_delay_firstclass_v1") || !bundle.architecture.equals("moss_delay_8b_v1") || !bundle.backend.equals("cpu")) throw new IOException("MOSS Delay 基座需要匹配的 8B / 32 路 / 24 kHz first-class CPU 配方");
        if(!type.equals("speech.synthesize") || !bundle.tasks.equals(Collections.singleton("audio"))) throw new IOException("当前 Delay 配方只提供语音合成");
        Set<String> missing=new HashSet<>(Arrays.asList("backbone","audio_decoder")),allowed=new HashSet<>(Arrays.asList("backbone","audio_decoder","audio_encoder"));
        for(ModelBundle.Component c:bundle.components) { if(!allowed.remove(c.role) || !c.format.equals("gguf")) throw new IOException("只接受匹配的 first-class 主模型 / 原生 codec GGUF，不能使用普通文本或旧版 MOSS GGUF");missing.remove(c.role); }
        if(!missing.isEmpty()) throw new IOException("MOSS Delay 缺少必需组件："+missing);
    }
    private static JSONObject field(String type,double value,double low,double high) throws Exception { return new JSONObject().put("type",type).put("default",value).put("minimum",low).put("maximum",high); }
    public static JSONObject schema() throws Exception {
        JSONObject fields=new JSONObject().put("threads",field("integer",4,1,32)).put("maxInputTokens",field("integer",512,1,2048)).put("maxNewTokens",field("integer",375,64,1500))
            .put("textTemperature",field("number",1.5,0,3)).put("textTopP",field("number",1,.01,1)).put("textTopK",field("integer",50,1,1024))
            .put("audioTemperature",field("number",1.7,0,3)).put("audioTopP",field("number",.8,.01,1)).put("audioTopK",field("integer",25,1,1024))
            .put("audioRepetitionPenalty",field("number",1,1,2)).put("seed",field("integer",-1,-1,Integer.MAX_VALUE))
            .put("language",new JSONObject().put("type","enum").put("default","auto").put("values",new JSONArray(Arrays.asList("auto","zh","en","de","es","fr","ja","it","hu","ko","ru","fa","ar","pl","pt","cs","da","sv","el","tr"))));
        return new JSONObject().put("version",1).put("fields",fields);
    }
    public static JSONObject parameters(JSONObject values) throws Exception { return new ParameterSchema(schema()).normalize(new JSONObject(),values); }
    public static InputSpec inputs(ModelBundle bundle) throws Exception {
        JSONObject roles=new JSONObject();if(hasEncoder(bundle)) roles.put("reference_audio",new JSONObject().put("label","可选参考音频：24 kHz 单声道 WAV，1–10 秒").put("required",false).put("mimes",new JSONArray().put("audio/wav")).put("maxBytes",1024*1024).put("maxDurationMs",10000));
        return new InputSpec(roles);
    }
    public static void reference(File file) throws Exception {
        JSONObject m=WaveFile.inspect(file);
        if(file.length()>1024*1024 || m.getInt("sampleRate")!=24000 || m.getInt("channels")!=1 || !(m.getInt("formatCode")==1 && m.getInt("bitsPerSample")==16 || m.getInt("formatCode")==3 && m.getInt("bitsPerSample")==32) || m.getLong("samples")<24000 || m.getLong("samples")>240000) throw new IOException("MOSS 参考音频须为 24 kHz 单声道 PCM16 / float32 WAV，1–10 秒且不超过 1 MiB");
    }
}
