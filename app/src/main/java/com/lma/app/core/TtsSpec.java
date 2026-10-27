package com.lma.app.core;

import org.json.JSONObject;
import java.io.IOException;
import java.util.*;

/** Data and safety contract for the signed-in sherpa TTS worker, independent of imported schemas. */
public final class TtsSpec {
    private TtsSpec() {}
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!bundle.engine.equals("sherpa_tts") || !bundle.backend.equals("cpu") || !Arrays.asList("kokoro", "piper_vits", "matcha").contains(bundle.pipeline)) throw new IOException("当前语音基座没有匹配的管线或后端");
        if (!type.equals("speech.synthesize") || !bundle.tasks.contains("audio")) throw new IOException("此模型配方不支持语音合成任务");
        Set<String> required = new HashSet<>(Arrays.asList("model", "tokens", "lexicon"));
        if (bundle.pipeline.equals("kokoro")) required.add("voices");
        if (bundle.pipeline.equals("matcha")) required.add("vocoder");
        for (ModelBundle.Component component : bundle.components) {
            String role = component.role;
            boolean lexicon = role.equals("lexicon") || role.matches("lexicon_[2-8]");
            String expected = role.equals("model") || role.equals("vocoder") ? "onnx" : role.equals("voices") ? "bin" : role.equals("rule_fst") ? "fst" : role.equals("rule_far") ? "far" : role.equals("tokens") || lexicon ? "text" : "";
            if (expected.isEmpty() || !component.format.equals(expected)) throw new IOException("语音配方组件角色或格式不匹配：" + role);
            if (role.equals("voices") && !bundle.pipeline.equals("kokoro") || role.equals("vocoder") && !bundle.pipeline.equals("matcha")) throw new IOException("语音配方包含其他管线的组件");
            required.remove(role);
        }
        if (!required.isEmpty()) throw new IOException("语音配方缺少必需组件：" + required);
    }
    public static JSONObject parameters(JSONObject input, String pipeline) throws Exception {
        JSONObject fields = new JSONObject();
        fields.put("threads", field("integer", 2, 1, 16));
        fields.put("speaker", field("integer", 0, 0, 65535));
        fields.put("speed", field("number", 1, 0.25, 3));
        fields.put("silenceScale", field("number", 1, 0, 3));
        fields.put("maxAudioSeconds", field("integer", 180, 1, 600));
        if (pipeline.equals("piper_vits") || pipeline.equals("matcha")) fields.put("noiseScale", field("number", 0.667, 0, 2));
        if (pipeline.equals("piper_vits")) fields.put("noiseScaleW", field("number", 0.8, 0, 2));
        return new ParameterSchema(new JSONObject().put("version", 1).put("fields", fields)).normalize(new JSONObject(), input).getJSONObject("values");
    }
    private static JSONObject field(String type, double value, double low, double high) throws Exception {
        return new JSONObject().put("type", type).put("default", value).put("minimum", low).put("maximum", high);
    }
    public static String text(JSONObject input) throws Exception {
        String text = input.getString("prompt");
        if (text.trim().isEmpty() || text.length() > 4000 || text.indexOf('\0') >= 0) throw new IOException("语音合成文本须为 1–4000 字符且不包含空字符；较长内容请分段提交");
        if (!input.optString("negativePrompt").isEmpty()) throw new IOException("语音合成不接受负面提示词");
        return text;
    }
}
