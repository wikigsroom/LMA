package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.util.*;

/** Exact native Qwen3-TTS 12Hz 0.6B Base data contract; runtime data stays user-owned. */
public final class QwenTtsSpec {
    private QwenTtsSpec() {}
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!bundle.engine.equals("qwen_tts_native") || !bundle.pipeline.equals("qwen3_tts_06b_base") || !bundle.architecture.equals("qwen3_tts_06b") || !bundle.backend.equals("cpu")) throw new IOException("当前 Qwen 语音基座只接受匹配的 0.6B Base CPU 配方");
        if (!type.equals("speech.synthesize") || !bundle.tasks.equals(Collections.singleton("audio"))) throw new IOException("此配方只提供语音合成任务");
        Set<String> required = new HashSet<>(Arrays.asList("talker", "audio_codec"));
        for (ModelBundle.Component c : bundle.components) if (!required.remove(c.role) || !c.format.equals("gguf")) throw new IOException("Qwen Base 须选择 Talker 与 12Hz codec 两个 GGUF；词表、Code Predictor 和说话人编码器包含在 Talker 内");
        if (!required.isEmpty()) throw new IOException("Qwen Base 配方缺少必需组件：" + required);
    }
    public static JSONObject schema() throws Exception {
        JSONObject fields = new JSONObject().put("threads", field("integer",4,1,32)).put("maxInputTokens",field("integer",512,1,2048)).put("maxAudioTokens",field("integer",375,1,1500))
            .put("temperature",field("number",.9,0,2)).put("topP",field("number",1,.01,1)).put("topK",field("integer",50,1,1024)).put("repetitionPenalty",field("number",1.05,1,2)).put("seed",field("integer",-1,-1,Integer.MAX_VALUE))
            .put("language",new JSONObject().put("type","enum").put("default","auto").put("values",new JSONArray(Arrays.asList("auto","en","zh","ja","ko","de","fr","ru","pt","es","it"))));
        return new JSONObject().put("version",1).put("fields",fields);
    }
    private static JSONObject field(String type, double value, double low, double high) throws Exception { return new JSONObject().put("type",type).put("default",value).put("minimum",low).put("maximum",high); }
    public static JSONObject parameters(JSONObject values) throws Exception { return new ParameterSchema(schema()).normalize(new JSONObject(),values); }
    public static InputSpec inputs() throws Exception {
        return new InputSpec(new JSONObject().put("reference_audio",new JSONObject().put("label","可选参考音频：24 kHz 单声道 WAV，1–30 秒").put("required",false).put("mimes",new JSONArray().put("audio/wav")).put("maxBytes",4*1024*1024).put("maxDurationMs",30000)));
    }
    public static void reference(File file) throws Exception {
        if (file.length() > 4*1024*1024) throw new IOException("参考 WAV 不得超过 4 MiB");
        JSONObject m = WaveFile.inspect(file);
        if (m.getInt("sampleRate") != 24000 || m.getInt("channels") != 1 || !(m.getInt("formatCode") == 1 && m.getInt("bitsPerSample") == 16 || m.getInt("formatCode") == 3 && m.getInt("bitsPerSample") == 32) || m.getLong("samples") < 24000 || m.getLong("samples") > 720000) throw new IOException("参考音频须为 24 kHz 单声道 PCM16 或 float32 WAV，时长 1–30 秒");
    }
}
