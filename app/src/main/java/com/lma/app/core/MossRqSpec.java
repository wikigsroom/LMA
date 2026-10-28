package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Old Local / Realtime RQ layouts, independent of the openmoss and Nano layouts. */
public final class MossRqSpec {
    private MossRqSpec() {}
    public static boolean realtime(ModelBundle b) { return b.pipeline.equals("moss_realtime_rq_cpu_v1"); }
    public static void validate(ModelBundle b,String type) throws Exception {
        boolean rt=realtime(b);
        if(!b.engine.equals("moss_rq_native") || !b.backend.equals("cpu") || !(rt || b.pipeline.equals("moss_local_v10_rq_cpu_v1")) || !b.architecture.equals(rt?"moss_tts_realtime":"moss_tts_local_v10"))throw new IOException("需要匹配的 moss-tts.cpp 旧 Local / Realtime CPU 配方");
        if(!type.equals("speech.synthesize") || !b.tasks.equals(Collections.singleton("audio")))throw new IOException("此配方提供单次文本到音频任务");
        Set<String> roles=new HashSet<>(Arrays.asList("model","codec","tokenizer"));
        for(ModelBundle.Component c:b.components)if(!roles.remove(c.role) || !c.format.equals("gguf"))throw new IOException("需要相同转换格式的 model / codec / tokenizer 三个 GGUF；不能混用 openmoss、Nano 或 first-class 格式");
        if(!roles.isEmpty())throw new IOException("缺少 RQ 组件："+roles);
    }
    private static JSONObject field(String type,double value,double low,double high) throws Exception { return new JSONObject().put("type",type).put("default",value).put("minimum",low).put("maximum",high); }
    public static JSONObject schema(ModelBundle b) throws Exception {
        boolean rt=realtime(b);JSONObject f=new JSONObject().put("threads",field("integer",4,1,32)).put("seed",field("integer",-1,-1,Integer.MAX_VALUE))
            .put("maxInputTokens",field("integer",1024,1,2048)).put("maxNewTokens",field("integer",375,1,750))
            .put("audioTemperature",field("number",rt?.8:1.7,0,3)).put("audioTopP",field("number",rt?.6:.8,.01,1))
            .put("audioTopK",field("integer",rt?30:25,1,1024)).put("audioRepetitionPenalty",field("number",1.1,1,2));
        if(!rt)f.put("textTemperature",field("number",1.5,0,3)).put("textTopP",field("number",1,.01,1)).put("textTopK",field("integer",50,1,1024))
            .put("voiceInstruction",new JSONObject().put("type","string").put("default","").put("maxLength",1000))
            .put("language",new JSONObject().put("type","string").put("default","").put("maxLength",64));
        return new JSONObject().put("version",1).put("fields",f);
    }
    public static JSONObject parameters(ModelBundle b,JSONObject values) throws Exception {
        JSONObject n=new ParameterSchema(schema(b)).normalize(new JSONObject(),values);
        if(!realtime(b))for(String key:Arrays.asList("voiceInstruction","language"))plain(n.getJSONObject("values").getString(key));return n;
    }
    private static void plain(String s) throws IOException { if(s.indexOf('\0')>=0 || s.indexOf('<')>=0 || s.indexOf('>')>=0)throw new IOException("请填写普通文本，不允许模板标记"); }
    public static String text(JSONObject input) throws Exception { String s=TtsSpec.text(input);plain(s);return s; }
    public static InputSpec inputs() throws Exception { return new InputSpec(new JSONObject().put("reference_audio",new JSONObject().put("label","可选参考：24 kHz 单声道 WAV，1–10 秒").put("required",false).put("mimes",new JSONArray().put("audio/wav")).put("maxBytes",1048576).put("maxDurationMs",10000))); }
    public static void conditioning(JSONObject input) throws Exception {
        JSONArray refs=input.optJSONArray("artifacts");if(refs==null)return;
        if(refs.length()>1 || refs.length()==1 && !refs.getJSONObject(0).getString("role").equals("reference_audio"))throw new IOException("RQ 仅接受一份可选参考音频");
    }
    public static void reference(File f) throws Exception {
        JSONObject m=WaveFile.inspect(f);
        if(f.length()>1048576 || m.getInt("sampleRate")!=24000 || m.getInt("channels")!=1 || m.getLong("durationMs")<1000 || m.getLong("durationMs")>10000 || !(m.getInt("formatCode")==1 && m.getInt("bitsPerSample")==16 || m.getInt("formatCode")==3 && m.getInt("bitsPerSample")==32))throw new IOException("参考音频须为 24 kHz 单声道 PCM16 / 有限浮点 WAV，1–10 秒，不超过 1 MiB");
    }
}
