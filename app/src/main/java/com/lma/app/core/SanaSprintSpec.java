package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Four-chunk Gemma2 / Sana-Sprint 0.6B / DC-AE; separate from Sana Edit. */
public final class SanaSprintSpec {
    private SanaSprintSpec() {}
    public static final String PIPELINE = "sana_sprint_06b_mnn_v1", PROFILE = "sana_sprint_scm_1024_v1";
    private static final Map<String, String> FILES = new LinkedHashMap<>();
    static {
        FILES.put("diffusion", "dit.mnn"); FILES.put("diffusion_data", "dit.mnn.weight");
        for (int i = 0; i < 4; i++) { FILES.put("gemma"+i, "gemma_chunk"+i+".mnn"); FILES.put("gemma"+i+"_data", "gemma_chunk"+i+".mnn.weight"); }
        FILES.put("embeddings", "token_emb.bin"); FILES.put("encoder_config", "gemma_meta.json");
        FILES.put("tokenizer", "tokenizer.model"); FILES.put("vae", "vae_decoder.mnn");
    }
    public static Set<String> roles() { return Collections.unmodifiableSet(FILES.keySet()); }
    public static String filename(String role) { String name = FILES.get(role); if (name == null) throw new IllegalArgumentException("Unknown Sana-Sprint component"); return name; }
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!bundle.engine.equals("mnn_diffusion") || !bundle.backend.equals("cpu") || !bundle.architecture.equals("sana_sprint_06b") || !bundle.pipeline.equals(PIPELINE) || !type.equals("image.generate") || AdapterSpec.isAdapter(bundle)) throw new IllegalArgumentException("请选择独立的 Sana-Sprint 0.6B 文生图配方");
        Set<String> actual = new HashSet<>();
        for (ModelBundle.Component c : bundle.components) {
            actual.add(c.role); String name = filename(c.role);
            String format = name.endsWith(".weight") ? "mnn_data" : name.endsWith(".json") ? "json" : name.endsWith(".bin") ? "bin" : name.endsWith(".model") ? "sentencepiece" : "mnn";
            if (!c.format.equals(format) || c.role.equals("embeddings") && c.bytes != 256000L*2304*2 || c.role.equals("encoder_config") && c.bytes > 4096 || c.role.equals("tokenizer") && c.bytes > 16L*1024*1024) throw new IllegalArgumentException("Sana-Sprint 组件格式或布局不匹配："+c.role);
        }
        if (!actual.equals(FILES.keySet())) throw new IllegalArgumentException("Sana-Sprint 必须完整选择 14 个组件，不能混用 Edit / 普通 Sana / 1.6B 权重");
    }
    public static void metadata(File file) throws Exception {
        if (!file.isFile() || file.length() < 2 || file.length() > 4096) throw new IOException("Sana-Sprint 编码器配置大小不合法");
        byte[] data = new byte[(int)file.length()];
        try (DataInputStream in = new DataInputStream(new FileInputStream(file))) { in.readFully(data); if (in.read() != -1) throw new IOException("编码器配置发生变化"); }
        JSONObject source = new JSONObject(new String(data, StandardCharsets.UTF_8));
        if (source.length() != 6 || source.getInt("vocab_size") != 256000 || source.getInt("hidden_size") != 2304 || source.getInt("seq_len") != 506 || source.getDouble("normalizer") != 48 || source.getInt("n_layers") != 26 || source.getInt("chunks") != 4) throw new IOException("需要四段、506 token 的匹配 Gemma2 编码器配置");
    }
    private static void set(JSONObject p, JSONArray changes, String key, Number value) throws Exception {
        Object old = p.opt(key);
        if (!(old instanceof Number) || ((Number)old).doubleValue() != value.doubleValue()) changes.put(new JSONObject().put("field", key).put("requested", old == null ? JSONObject.NULL : old).put("effective", value).put("reason", "sana_sprint_export_or_application_guard"));
        p.put(key, value);
    }
    private static int integer(JSONObject p, String key, int fallback, int low, int high) throws Exception {
        Object value = p.opt(key); if (value == null) return fallback;
        if (!(value instanceof Number) || !Double.isFinite(((Number)value).doubleValue()) || ((Number)value).doubleValue() != Math.rint(((Number)value).doubleValue())) throw new IllegalArgumentException("参数必须是有限整数："+key);
        return (int)Math.max(low, Math.min(high, ((Number)value).doubleValue()));
    }
    public static JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        validate(bundle, request.getString("type"));
        if (!bundle.id.equals(request.getString("bundleId")) || request.optJSONArray("adapters") != null && request.getJSONArray("adapters").length() > 0) throw new IllegalArgumentException("Sana-Sprint 不接收 LoRA 或其他模型快照");
        JSONObject input = request.getJSONObject("input"); String prompt = input.getString("prompt");
        if (prompt.trim().isEmpty() || prompt.length() > 16000 || prompt.indexOf('\0') >= 0 || !input.optString("negativePrompt").isEmpty()) throw new IllegalArgumentException("请输入提示词；Sana-Sprint 使用内嵌引导，不接收负面提示词");
        JSONObject result = DataFiles.copy(request), p = DataFiles.copy(request.getJSONObject("parameters")); JSONArray changes = new JSONArray();
        for (String key : Arrays.asList("width", "height")) set(p, changes, key, 1024);
        set(p, changes, "steps", integer(p, "steps", 2, 1, 4)); set(p, changes, "threads", integer(p, "threads", 4, 1, 32));
        set(p, changes, "seed", integer(p, "seed", -1, -1, Integer.MAX_VALUE));
        Object raw = p.opt("guidance"); if (raw != null && (!(raw instanceof Number) || !Double.isFinite(((Number)raw).doubleValue()))) throw new IllegalArgumentException("引导强度必须是有限数值");
        set(p, changes, "guidance", Math.max(1, Math.min(30, raw == null ? 4.5 : ((Number)raw).doubleValue())));
        Set<String> accepted = new HashSet<>(Arrays.asList("width", "height", "steps", "threads", "seed", "guidance"));
        for (Iterator<String> it = p.keys(); it.hasNext();) if (!accepted.contains(it.next())) throw new IllegalArgumentException("Sana-Sprint 包含不支持的参数");
        return result.put("diffusionPlan", new JSONObject().put("schema", "lma.diffusion-plan/1").put("profile", PROFILE).put("parameters", p).put("adjustments", changes));
    }
    public static String normalizedPrompt(String prompt) {
        String text = prompt.toLowerCase(Locale.ROOT); int start = 0, end = text.length();
        while (start < end && space(text.codePointAt(start))) start += Character.charCount(text.codePointAt(start));
        while (end > start && space(text.codePointBefore(end))) end -= Character.charCount(text.codePointBefore(end));
        return text.substring(start, end);
    }
    private static boolean space(int code) { return Character.isWhitespace(code) || Character.isSpaceChar(code) || code == 0x85; }
}
