package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Signed adapter contracts; imported model metadata cannot widen these bounds. */
public final class AudioCppSpec {
    private AudioCppSpec() {}
    public static Map<String,String> layout(String pipeline, boolean gguf) throws IOException {
        Map<String,String> files = new LinkedHashMap<>();
        if (pipeline.equals("f5_v1")) {
            files.put("model", "model.safetensors"); files.put("vocoder", "vocos.safetensors");
            files.put("vocab", "vocab.txt"); files.put("pinyin_chars", "pinyin.txt"); files.put("pinyin_phrases", "phrases.txt");
            files.put("frontend", "f5-frontend.json");
        } else if (pipeline.equals("omnivoice")) {
            files.put("model", gguf ? "omnivoice.gguf" : "model.safetensors");
            if (!gguf) {
                files.put("config", "config.json"); files.put("text_tokenizer", "tokenizer.json");
                files.put("tokenizer_config", "tokenizer_config.json"); files.put("codec_config", "audio_tokenizer/config.json");
                files.put("codec_preprocessor", "audio_tokenizer/preprocessor_config.json"); files.put("audio_codec", "audio_tokenizer/model.safetensors");
            }
        } else throw new IOException("当前语音基座不支持此管线");
        return Collections.unmodifiableMap(files);
    }
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!bundle.engine.equals("audio_cpp") || !bundle.backend.equals("cpu") || !type.equals("speech.synthesize") ||
            !bundle.tasks.equals(Collections.singleton("audio"))) throw new IOException("请选择匹配的本地语音配方");
        boolean f5 = bundle.pipeline.equals("f5_v1"), gguf = bundle.component("model").format.equals("gguf");
        if (!bundle.architecture.equals(f5 ? "f5_tts_v1" : "omnivoice")) throw new IOException("语音模型架构与配方不一致");
        Map<String,String> files = layout(bundle.pipeline, gguf);
        Set<String> required = new HashSet<>(files.keySet());
        if (f5) { required.remove("pinyin_chars"); required.remove("pinyin_phrases"); required.remove("frontend"); if (gguf) throw new IOException("F5 v1 使用原版 safetensors 权重，不能套用 Habibi GGUF"); }
        for (ModelBundle.Component c : bundle.components) {
            if (!files.containsKey(c.role)) throw new IOException("此语音配方不接受组件：" + c.role);
            String expected = c.role.equals("model") ? gguf ? "gguf" : "safetensors" :
                c.role.equals("vocoder") || c.role.equals("audio_codec") ? "safetensors" :
                c.role.equals("vocab") || c.role.startsWith("pinyin_") ? "text" : "json";
            if (!c.format.equals(expected) && !(c.role.equals("vocoder") && c.format.equals("bin"))) throw new IOException("语音组件格式不匹配：" + c.role);
            if(c.role.equals("frontend")&&c.bytes>96L*1024*1024)throw new IOException("F5 前端资产超过 96 MiB 的基座上限");
            required.remove(c.role);
        }
        if (!required.isEmpty()) throw new IOException("语音配方缺少必需组件：" + required);
    }
    private static JSONObject field(String type, Number value, Number low, Number high) throws Exception {
        return new JSONObject().put("type",type).put("default",value).put("minimum",low).put("maximum",high).put("limitSource","application_guard");
    }
    public static JSONObject schema(String pipeline) throws Exception {
        boolean f5 = pipeline.equals("f5_v1"); layout(pipeline, false);
        JSONObject f = new JSONObject().put("threads",field("integer",2,1,16)).put("steps",field("integer",32,1,64))
            .put("speed",field("number",1,0.5,2)).put("cfg",field("number",2,0,10)).put("seed",field("integer",1234,0,2147483647))
            .put("maxAudioSeconds",field("integer",30,1,120));
        if (f5) f.put("frameBudget",field("integer",2048,512,4096)).put("sway",field("number",-1,-5,5));
        else {
            f.put("durationSeconds",field("number",4,1,30).put("maximumFrom",new JSONObject().put("field","maxAudioSeconds")));
            f.put("language",new JSONObject().put("type","string").put("default","auto").put("maxLength",80));
            f.put("voiceMode",new JSONObject().put("type","enum").put("default","auto").put("values",new JSONArray(Arrays.asList("auto","clone","design"))));
            f.put("voiceInstruction",new JSONObject().put("type","string").put("default","").put("maxLength",1000));
        }
        JSONObject labels=new JSONObject().put("threads","CPU 线程").put("steps","采样步数").put("speed","语速").put("cfg","引导强度")
            .put("seed","随机种子").put("maxAudioSeconds","输出时长保护上限（秒）").put("frameBudget","单块 mel 帧预算").put("sway","Sway 系数")
            .put("durationSeconds","目标时长（秒）").put("language","语言（auto 自动）").put("voiceMode","音色模式").put("voiceInstruction","音色描述");
        for(Iterator<String> it=f.keys();it.hasNext();) { String key=it.next(); f.getJSONObject(key).put("label",labels.getString(key)); }
        return new JSONObject().put("version",1).put("fields",f);
    }
    public static JSONObject parameters(String pipeline, JSONObject values) throws Exception { return new ParameterSchema(schema(pipeline)).normalize(new JSONObject(),values); }
    public static InputSpec inputs(String pipeline) throws Exception {
        boolean f5 = pipeline.equals("f5_v1");
        JSONObject rule = new JSONObject().put("label",f5 ? "参考音频：24 kHz 单声道 WAV，1–12 秒" : "可选音色参考：24 kHz 单声道 WAV，1–30 秒")
            .put("required",f5).put("mimes",new JSONArray().put("audio/wav")).put("maxBytes",8*1024*1024)
            .put("minDurationMs",1000).put("maxDurationMs",f5?12000:30000)
            .put("transcript",new JSONObject().put("label","与参考音频准确对应的文本").put("maxLength",4000));
        return new InputSpec(new JSONObject().put("reference_audio",rule),
            f5 ? "输入要朗读的中英文。可为此模型选择官方兼容前端资产：固定版本分词、多音字与变调；未知词元按官方规则映射为 0。旧版拼音字典配方继续使用原匹配规则。"
               : "输入要朗读的文本；音色模式和描述在此模型的本地参数中设置。600+ 语言为上游声明，未逐语言验证。").withNegativePrompt(false);
    }
    public static void reference(File file, String pipeline) throws Exception {
        JSONObject value = WaveFile.inspect(file); long maximum = pipeline.equals("f5_v1") ? 288000 : 720000;
        if (file.length()>8*1024*1024 || value.getInt("sampleRate")!=24000 || value.getInt("channels")!=1 ||
            !(value.getInt("formatCode")==1 && value.getInt("bitsPerSample")==16 || value.getInt("formatCode")==3 && value.getInt("bitsPerSample")==32) ||
            value.getLong("samples")<24000 || value.getLong("samples")>maximum)
            throw new IOException("参考音频须为所选配方时长内的 24 kHz 单声道 WAV");
    }
}
