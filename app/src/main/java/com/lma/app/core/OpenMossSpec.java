package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.util.*;

/** Distinct openmoss layouts; a catalogue entry is never device-execution evidence. */
public final class OpenMossSpec {
    private OpenMossSpec() {}
    private static final Map<String,String> DELAY=new LinkedHashMap<>();
    static {
        DELAY.put("moss_tts_openmoss_cpu_v1","moss_tts");DELAY.put("moss_tts_v15_openmoss_cpu_v1","moss_tts_v15");
        DELAY.put("moss_ttsd_openmoss_cpu_v1","moss_ttsd");DELAY.put("moss_voicegen_openmoss_cpu_v1","moss_voicegenerator");
        DELAY.put("moss_soundeffect_openmoss_cpu_v1","moss_soundeffect");
    }
    public static boolean flow(ModelBundle b) { return b.pipeline.equals("moss_soundeffect_v2_cpu_v1"); }
    public static boolean sound(ModelBundle b) { return flow(b) || effect(b); }
    public static boolean effect(ModelBundle b) { return b.pipeline.equals("moss_soundeffect_openmoss_cpu_v1"); }
    public static boolean delay(ModelBundle b) { return DELAY.containsKey(b.pipeline); }
    public static boolean dialogue(ModelBundle b) { return b.pipeline.equals("moss_ttsd_openmoss_cpu_v1"); }
    public static boolean voice(ModelBundle b) { return b.pipeline.equals("moss_voicegen_openmoss_cpu_v1"); }
    public static int sampleRate(ModelBundle b) { return delay(b)?24000:48000; }
    public static int channels(ModelBundle b) { return sound(b) || delay(b)?1:2; }
    public static void validate(ModelBundle b,String type) throws Exception {
        boolean s=sound(b);
        if(!b.engine.equals("openmoss_native") || !b.backend.equals("cpu") || !(flow(b) && b.architecture.equals("moss_soundeffect_v2") || b.pipeline.equals("moss_local_v15_cpu_v1") && b.architecture.equals("moss_local_v15") || delay(b) && b.architecture.equals(DELAY.get(b.pipeline)))) throw new IOException("需要匹配的 openmoss CPU 配方及其模型布局");
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
    public static JSONObject schema(ModelBundle b) throws Exception {
        JSONObject s=schema(flow(b));if(delay(b)) {
            JSONObject f=s.getJSONObject("fields");f.getJSONObject("maxInputTokens").put("default",1024);f.getJSONObject("maxNewTokens").put("default",375).put("maximum",1500);
            if(effect(b)) {f.getJSONObject("audioTemperature").put("default",1.5);f.getJSONObject("audioTopP").put("default",.6);f.getJSONObject("audioTopK").put("default",50);f.getJSONObject("audioRepetitionPenalty").put("default",1.2);}
            else f.put("voiceInstruction",new JSONObject().put("type","string").put("default","").put("maxLength",1000)).put("language",new JSONObject().put("type","string").put("default","").put("maxLength",64));
        }return s;
    }
    public static JSONObject parameters(ModelBundle b,JSONObject values) throws Exception {
        JSONObject result=new ParameterSchema(schema(b)).normalize(new JSONObject(),values);
        if(delay(b) && !sound(b))for(String key:Arrays.asList("voiceInstruction","language")) {String s=result.getJSONObject("values").getString(key);if(s.indexOf('\0')>=0 || s.indexOf('<')>=0 || s.indexOf('>')>=0)throw new IOException("声音描述和语言须为普通文本，不允许模板标记");}
        return result;
    }
    public static String text(ModelBundle b,JSONObject input) throws Exception {
        if(!sound(b)) {
            String text=TtsSpec.text(input);
            if(delay(b)) {
                if(text.indexOf('<')>=0 || text.indexOf('>')>=0)throw new IOException("合成文本不能包含模板标记");
                java.util.regex.Matcher m=java.util.regex.Pattern.compile("\\[S").matcher(text);
                while(m.find())if(!(text.startsWith("[S1]",m.start()) || dialogue(b) && text.startsWith("[S2]",m.start())))throw new IOException("此配方仅接受对应的 [S1] / [S2] 说话人标签");
                if(dialogue(b) && !(text.contains("[S1]") && text.contains("[S2]")))throw new IOException("TTSD 对话须包含 [S1] 和 [S2] 文本段");
            }return text;
        }
        String text=input.getString("prompt"),negative=input.optString("negativePrompt","");
        if(text.trim().isEmpty() || text.length()>8000 || text.indexOf('\0')>=0 || negative.length()>8000 || negative.indexOf('\0')>=0) throw new IOException("音效提示词不能为空，且每段最多 8000 字符");
        if(effect(b) && (!negative.isEmpty() || text.indexOf('<')>=0 || text.indexOf('>')>=0))throw new IOException("旧 SoundEffect 使用环境声音描述，不接受负面提示词或模板标记");
        return text;
    }
    public static InputSpec inputs(ModelBundle b) throws Exception {
        JSONObject roles=new JSONObject();if(sound(b) || voice(b))return InputSpec.promptOnly();
        for(String role:referenceRoles(b))roles.put(role,new JSONObject().put("label",dialogue(b)?"成对可选参考 "+(role.endsWith("s1")?"[S1]":"[S2]")+"：24 kHz 单声道 WAV，1–10 秒":delay(b)?"可选参考：24 kHz 单声道 WAV，1–10 秒":"可选参考：48 kHz 双声道 WAV，1–10 秒").put("required",false).put("mimes",new JSONArray().put("audio/wav")).put("maxBytes",(delay(b)?1:4)*1024*1024).put("maxDurationMs",10000));
        return new InputSpec(roles);
    }
    public static List<String> referenceRoles(ModelBundle b) { return sound(b) || voice(b)?Collections.emptyList():dialogue(b)?Arrays.asList("reference_audio_s1","reference_audio_s2"):Collections.singletonList("reference_audio"); }
    public static void conditioning(ModelBundle b,JSONObject input,JSONObject parameters) throws Exception {
        if(flow(b) && parameters.getDouble("cfgScale")==1 && !input.optString("negativePrompt","").trim().isEmpty())throw new IOException("CFG=1 不使用负向条件；请提高 CFG 或清空负面提示词");
        if(voice(b) && parameters.getString("voiceInstruction").trim().isEmpty())throw new IOException("VoiceGenerator 需要填写声音描述（voiceInstruction）");
        Set<String> seen=new HashSet<>();JSONArray refs=input.optJSONArray("artifacts");if(refs!=null)for(int i=0;i<refs.length();i++){String r=refs.getJSONObject(i).getString("role");if(!referenceRoles(b).contains(r) || !seen.add(r))throw new IOException("此配方不接受该参考角色或重复参考");}
        if(dialogue(b) && seen.size()==1)throw new IOException("TTSD 参考须成对选择 [S1] 与 [S2]，或全部留空");
    }
    public static void reference(File f) throws Exception {
        reference(f,48000,2,4*1024*1024);
    }
    public static void reference(ModelBundle b,File f) throws Exception { reference(f,sampleRate(b),channels(b),(delay(b)?1:4)*1024*1024); }
    private static void reference(File f,int rate,int channels,int bytes) throws Exception {
        JSONObject m=WaveFile.inspect(f);
        if(f.length()>bytes || m.getInt("sampleRate")!=rate || m.getInt("channels")!=channels || !(m.getInt("formatCode")==1 && m.getInt("bitsPerSample")==16 || m.getInt("formatCode")==3 && m.getInt("bitsPerSample")==32) || m.getLong("samples")<rate || m.getLong("samples")>rate*10) throw new IOException("参考须匹配模型的 "+rate+" Hz / "+channels+" 声道 PCM16 / float32 WAV，1–10 秒且不超过 "+bytes+" 字节");
    }
}
