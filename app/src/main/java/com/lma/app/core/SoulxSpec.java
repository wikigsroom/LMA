package com.lma.app.core;

import java.io.*;
import java.util.*;
import org.json.*;

/** Complete SoulX-Podcast reference/language/acoustic CPU contract, not generic Qwen TTS. */
public final class SoulxSpec {
    private SoulxSpec() {}
    public static final String PIPELINE = "soulx_podcast_cpu_v1";
    private static final String[] ROLES = {"language", "s3", "s3_data", "speaker", "speaker_data", "flow_encoder", "flow_encoder_data", "flow_estimator", "flow_estimator_data", "hift_f0", "hift_f0_data", "hift_spectrum", "hift_spectrum_data", "hift_source"};
    private static final String[] FILES = {"language.gguf", "reference-s3.onnx", "reference-s3.onnx.data", "reference-speaker.onnx", "reference-speaker.onnx.data", "flow-encoder.onnx", "flow-encoder.onnx.data", "flow-estimator.onnx", "flow-estimator.onnx.data", "hift-f0.onnx", "hift-f0.onnx.data", "hift-spectrum.onnx", "hift-spectrum.onnx.data", "hift-source.f32"};
    public static Map<String, String> files() { Map<String, String> result = new LinkedHashMap<>(); for (int i = 0; i < ROLES.length; i++) result.put(ROLES[i], FILES[i]); return Collections.unmodifiableMap(result); }
    public static void validate(ModelBundle b, String type) throws Exception {
        if (!b.engine.equals("soulx_native") || !b.backend.equals("cpu") || !b.architecture.equals("soulx_podcast_17b") || !b.pipeline.equals(PIPELINE)) throw new IOException("需要匹配的 SoulX-Podcast 1.7B 完整 CPU 配方");
        if (!type.equals("speech.synthesize") || !b.tasks.equals(Collections.singleton("audio"))) throw new IOException("SoulX 配方提供语音合成任务");
        Set<String> missing = new HashSet<>(Arrays.asList(ROLES));
        for (ModelBundle.Component c : b.components) {
            String name = files().get(c.role), format = c.role.equals("language") ? "gguf" : c.role.equals("hift_source") ? "bin" : c.role.endsWith("_data") ? "onnx_data" : "onnx";
            if (name == null || !missing.remove(c.role) || !c.format.equals(format)) throw new IOException("SoulX 组件角色或格式不匹配：" + c.role);
            String lower = c.path.toLowerCase(Locale.ROOT);
            if (!lower.endsWith(c.role.equals("language") ? ".gguf" : c.role.equals("hift_source") ? ".f32" : c.role.endsWith("_data") ? ".onnx.data" : ".onnx")) throw new IOException("SoulX 组件文件类型不匹配：" + c.role);
            if (c.role.equals("hift_source") && c.bytes != 40 || format.equals("onnx") && c.bytes > 128L * 1024 * 1024) throw new IOException("SoulX 图或声源参数大小不符合导出约束");
        }
        if (!missing.isEmpty()) throw new IOException("缺少 SoulX 必需组件：" + missing);
    }
    private static JSONObject field(String type, double value, double low, double high) throws Exception { return new JSONObject().put("type", type).put("default", value).put("minimum", low).put("maximum", high); }
    private static JSONObject bound(JSONObject f, String name, int offset) throws Exception { return f.put("maximumFrom", new JSONObject().put("field", name).put("offset", offset)); }
    public static JSONObject schema() throws Exception {
        JSONObject f = new JSONObject().put("context", field("integer", 4096, 256, 8192)).put("threads", field("integer", 4, 1, 32))
            .put("maxNewTokens", bound(field("integer", 512, 1, 3000), "context", -64)).put("minNewTokens", bound(field("integer", 8, 0, 2999), "maxNewTokens", -1))
            .put("temperature", field("number", .6, 0, 3)).put("repetitionPenalty", field("number", 1.25, .01, 10)).put("topK", field("integer", 100, 0, 262144)).put("topP", field("number", .9, .0001, 1))
            .put("useRas", new JSONObject().put("type", "boolean").put("default", true)).put("rasWindow", field("integer", 25, 1, 256)).put("rasTau", field("number", .2, .0001, 1))
            .put("maxHistoryTurns", field("integer", 10, 5, 64)).put("historyTurns", bound(field("integer", 2, 1, 8), "maxHistoryTurns", -4)).put("textHistoryTurns", field("integer", 2, 0, 16)).put("historyThreshold", bound(field("integer", 4096, 128, 8192), "context", 0))
            .put("steps", field("integer", 15, 1, 100)).put("cfg", field("number", .7, 0, 10)).put("seed", field("integer", -1, -1, Integer.MAX_VALUE))
            .put("pauseMs", field("integer", 200, 0, 2000)).put("maxOutputSeconds", field("integer", 120, 1, 960));
        return new JSONObject().put("version", 1).put("fields", f);
    }
    public static JSONObject parameters(JSONObject values) throws Exception {
        JSONObject n = new ParameterSchema(schema()).normalize(new JSONObject(), values), p = n.getJSONObject("values");
        if (p.getDouble("temperature") == 0 && p.getBoolean("useRas")) {
            p.put("useRas", false); n.getJSONArray("adjustments").put(new JSONObject().put("field", "useRas").put("requested", true).put("effective", false).put("reason", "greedy_requires_ras_disabled"));
        }
        return n;
    }
    public static InputSpec inputs() throws Exception {
        JSONObject roles = new JSONObject();
        for (int i = 1; i <= 4; i++) roles.put("reference_s" + i, new JSONObject().put("label", "S" + i + " 参考音频（24 kHz 单声道 PCM16 / float32，1–15 秒）").put("required", i == 1)
            .put("mimes", new JSONArray().put("audio/wav")).put("maxBytes", 1536000).put("minDurationMs", 1000).put("maxDurationMs", 15000)
            .put("transcript", new JSONObject().put("label", "S" + i + " 参考音频原文").put("maxLength", 4000)));
        return new InputSpec(roles, "单段文字默认 S1；多段文字每行使用 [S1] 原文 至 [S4] 原文，最多 64 段。参考音频从 S1 开始连续选择，每段填写音频实际说出的原文。各发言段只会使用已选择的对应参考音频。");
    }
    private static String plain(String text) throws IOException {
        if (text.trim().isEmpty() || text.length() > 4000 || text.indexOf('\0') >= 0) throw new IOException("SoulX 文本须为 1–4000 字符且不包含 NUL");
        for (String token : new String[]{"<|SPEAKER_", "<|text_start|>", "<|text_end|>", "<|semantic_token_start|>", "<|semantic_token_end|>", "<|task_podcast|>"}) if (text.contains(token)) throw new IOException("SoulX 原文不能包含内部控制标记");
        return text;
    }
    public static int references(JSONObject input) throws Exception {
        JSONArray refs = input.optJSONArray("artifacts"); Set<String> selected = new HashSet<>();
        if (refs != null) for (int i = 0; i < refs.length(); i++) if (!selected.add(refs.getJSONObject(i).getString("role"))) throw new IOException("每个说话人只能选择一段参考音频");
        int count = selected.size();
        if (count < 1 || count > 4) throw new IOException("请选择 S1 及最多三个连续编号的其他参考音频");
        JSONObject texts = input.getJSONObject("transcripts");
        if (texts.length() != count) throw new IOException("每段参考音频都需要对应原文");
        for (int i = 1; i <= count; i++) { String role = "reference_s" + i; if (!selected.contains(role)) throw new IOException("参考音频编号须从 S1 开始连续选择"); plain(texts.getString(role)); }
        return count;
    }
    public static JSONArray turns(JSONObject input) throws Exception {
        String text = TtsSpec.text(input); plain(text); int references = references(input); JSONArray result = new JSONArray();
        if (!text.contains("[S")) return result.put(new JSONObject().put("speaker", 0).put("text", text));
        for (String raw : text.split("\\r?\\n", -1)) {
            String line = raw.trim(); if (line.isEmpty()) continue;
            if (line.length() < 6 || line.charAt(0) != '[' || line.charAt(1) != 'S' || line.charAt(2) < '1' || line.charAt(2) > '4' || line.charAt(3) != ']' || line.substring(4).trim().isEmpty()) throw new IOException("多说话人文本每行使用 [S1] 原文 至 [S4] 原文");
            int speaker = line.charAt(2) - '1'; if (speaker >= references) throw new IOException("所选说话人没有参考音频");
            String target = line.substring(4).trim(); if (target.contains("[S")) throw new IOException("每行只允许一个说话人标记"); plain(target);
            result.put(new JSONObject().put("speaker", speaker).put("text", target));
        }
        if (result.length() < 1 || result.length() > 64) throw new IOException("SoulX 一次任务允许 1–64 个发言段");
        return result;
    }
}
