package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.util.*;

/** Distinct openmoss layouts; a catalogue entry is never device-execution evidence. */
public final class OpenMossSpec {
    private OpenMossSpec() {}
    public static boolean sound(ModelBundle b) { return b.pipeline.equals("moss_soundeffect_v2_cpu_v1"); }
    public static void validate(ModelBundle b,String type) throws Exception {
        boolean s=sound(b);
        if(!b.engine.equals("openmoss_native") || !b.backend.equals("cpu") || !(s && b.architecture.equals("moss_soundeffect_v2") || b.pipeline.equals("moss_local_v15_cpu_v1") && b.architecture.equals("moss_local_v15"))) throw new IOException("需要匹配的 openmoss Local-v1.5 / SoundEffect-v2 CPU 配方");
        if(!type.equals(s?"audio.generate":"speech.synthesize") || !b.tasks.equals(Collections.singleton("audio"))) throw new IOException("所选 MOSS 配方不提供此任务");
        Set<String> roles=new HashSet<>(Arrays.asList("backbone","extras"));
        for(ModelBundle.Component c:b.components) if(!roles.remove(c.role) || !c.format.equals("gguf")) throw new IOException("需要同次转换且匹配的主干与 extras GGUF；不能混用 first-class / Nano / 旧版文件");
        if(!roles.isEmpty()) throw new IOException("MOSS 缺少组件："+roles);
    }
    private static JSONObject field(String type,double value,double low,double high) throws Exception { return new JSONObject().put("type",type).put("default",value).put("minimum",low).put("maximum",high); }
    public static JSONObject schema(boolean sound) throws Exception {
        JSONObject f=new JSONObject().put("threads",field("integer",4,1,32)).put("seed",field("integer",-1,-1,Integer.MAX_VALUE));
        if(sound) f.put("seconds",field("number",5,1,30)).put("steps",field("integer",50,1,100)).put("cfgScale",field("number",4,1,10)).put("sigmaShift",field("number",5,1,10));
        else f.put("maxInputTokens",field("integer",512,1,2048)).put("maxNewTokens",field("integer",250,1,750))
            .put("textTemperature",field("number",1,0,3)).put("audioTemperature",field("number",1.7,0,3))
            .put("audioTopP",field("number",.8,.01,1)).put("audioTopK",field("integer",25,1,1024)).put("audioRepetitionPenalty",field("number",1,1,2));
        return new JSONObject().put("version",1).put("fields",f);
    }
    public static JSONObject parameters(ModelBundle b,JSONObject values) throws Exception { return new ParameterSchema(schema(sound(b))).normalize(new JSONObject(),values); }
    public static String text(ModelBundle b,JSONObject input) throws Exception {
        if(!sound(b)) return TtsSpec.text(input);
        String text=input.getString("prompt"),negative=input.optString("negativePrompt","");
        if(text.trim().isEmpty() || text.length()>8000 || text.indexOf('\0')>=0 || negative.length()>8000 || negative.indexOf('\0')>=0) throw new IOException("音效提示词不能为空，且每段最多 8000 字符");
        return text;
    }
    public static InputSpec inputs(ModelBundle b) throws Exception {
        if(sound(b)) return InputSpec.promptOnly();
        return new InputSpec(new JSONObject().put("reference_audio",new JSONObject().put("label","可选参考：48 kHz 双声道 WAV，1–10 秒").put("required",false).put("mimes",new JSONArray().put("audio/wav")).put("maxBytes",4*1024*1024).put("maxDurationMs",10000)));
    }
    public static void reference(File f) throws Exception {
        JSONObject m=WaveFile.inspect(f);
        if(f.length()>4*1024*1024 || m.getInt("sampleRate")!=48000 || m.getInt("channels")!=2 || !(m.getInt("formatCode")==1 && m.getInt("bitsPerSample")==16 || m.getInt("formatCode")==3 && m.getInt("bitsPerSample")==32) || m.getLong("samples")<48000 || m.getLong("samples")>480000) throw new IOException("Local-v1.5 参考须为 48 kHz 双声道 PCM16 / float32 WAV，1–10 秒且不超过 4 MiB");
    }
}
