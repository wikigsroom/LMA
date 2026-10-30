package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Matched Qwen3/Sana mobile data contract; original Sana weights are not interchangeable. */
public final class MnnSpec {
    private MnnSpec() {}
    public static final String EDIT_PROMPT = "Convert to a Ghibli-style illustration: soft contrast, warm tones, slight linework, keep the scene consistent.";
    private static final Map<String, String> FILES = new LinkedHashMap<>();
    static {
        FILES.put("diffusion", "transformer.mnn"); FILES.put("diffusion_data", "transformer.mnn.weight");
        FILES.put("connector", "connector.mnn"); FILES.put("connector_data", "connector.mnn.weight");
        FILES.put("projector", "projector.mnn"); FILES.put("projector_data", "projector.mnn.weight");
        FILES.put("vae", "vae_decoder.mnn"); FILES.put("vae_data", "vae_decoder.mnn.weight");
        FILES.put("vae_encoder", "vae_encoder.mnn"); FILES.put("vae_encoder_data", "vae_encoder.mnn.weight");
        FILES.put("llm", "llm.mnn"); FILES.put("llm_data", "llm.mnn.weight");
        FILES.put("llm_config", "llm_config.json"); FILES.put("tokenizer", "tokenizer.txt"); FILES.put("meta_queries", "meta_queries.mnn");
    }
    public static Set<String> roles() { return Collections.unmodifiableSet(FILES.keySet()); }
    public static String filename(String role) { if (!FILES.containsKey(role)) throw new IllegalArgumentException("Unknown Sana component role"); return FILES.get(role); }
    public static String group(String role) { filename(role); return Arrays.asList("llm", "llm_data", "llm_config", "tokenizer", "meta_queries").contains(role) ? "llm" : "models"; }
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (!bundle.engine.equals("mnn_diffusion") || !bundle.backend.equals("cpu") || !bundle.architecture.equals("sana_mobile_edit") || !bundle.pipeline.equals("sana_edit_mnn_v1") || !type.equals("image.generate") || AdapterSpec.isAdapter(bundle)) throw new IllegalArgumentException("请选择 15 组件的 Sana 图片风格转换配方；旧 13 组件文生图声明不兼容，文件和设置保留，请明确选择新配方");
        Set<String> actual = new HashSet<>();
        for (ModelBundle.Component c : bundle.components) {
            actual.add(c.role); String name = filename(c.role);
            String format = name.endsWith(".weight") ? "mnn_data" : name.endsWith(".json") ? "json" : name.endsWith(".txt") ? "text" : "mnn";
            if (!c.format.equals(format) || c.role.equals("llm_config") && c.bytes > 65536 || c.role.equals("tokenizer") && c.bytes > 32L * 1024 * 1024) throw new IllegalArgumentException("Sana 组件格式或大小不匹配：" + c.role);
        }
        if (!actual.equals(FILES.keySet())) throw new IllegalArgumentException("Sana 图片编辑必须完整安装选定配方的 15 个组件（含图片编码器），不接受其他架构或额外配置");
    }
    public static InputSpec inputs() throws Exception {
        return new InputSpec(new JSONObject().put("source_image", new JSONObject().put("label", "原始图片（建议正方形）").put("required", true)
            .put("mimes", new JSONArray().put("image/png").put("image/jpeg")).put("maxBytes", 16L * 1024 * 1024).put("maxPixels", 4194304)),
            "此模型用于卡通风格图片转换：必须选择本地图片，输出固定 512×512，使用配套固定提示词。模型和素材均由你自行管理。").withFixedPrompt(EDIT_PROMPT);
    }
    public static JSONObject metadata(File file, long weightBytes) throws Exception {
        if (!file.isFile() || file.length() < 2 || file.length() > 65536) throw new IOException("Sana 编码器 metadata 大小不合法");
        byte[] data;
        try (InputStream in = new FileInputStream(file); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096]; int n;
            while ((n = in.read(buffer)) != -1) { if (out.size() + n > 65536) throw new IOException("Sana metadata 超限"); out.write(buffer, 0, n); }
            data = out.toByteArray();
        }
        JSONObject source = new JSONObject(new String(data, StandardCharsets.UTF_8));
        if (!source.getString("model_type").equals("qwen3") || source.getInt("hidden_size") != 1024 || !source.getString("attention_mask").equals("float") || !source.getString("attention_type").equals("full")) throw new IOException("此 Sana 管线需要匹配的 Qwen3-0.6B 编码器 metadata");
        JSONArray tie = source.getJSONArray("tie_embeddings");
        if (tie.length() != 5 && tie.length() != 6) throw new IOException("不支持此 embedding 布局");
        long[] values = new long[tie.length()];
        for (int i = 0; i < values.length; i++) { Object value = tie.get(i); if (!(value instanceof Number) || !Double.isFinite(((Number) value).doubleValue()) || ((Number) value).doubleValue() != ((Number) value).longValue() || ((Number) value).longValue() < 0) throw new IOException("不合法的 embedding 布局"); values[i] = ((Number) value).longValue(); }
        long block = values[4], bit = values[3];
        if (bit != 4 && bit != 8 || block < 1 || block > 1024 || (block & (block - 1)) != 0 || values.length == 6 && values[5] > 1) throw new IOException("不支持此 embedding 量化布局");
        long embeddingBytes = 151936L * 1024 * bit / 8;
        long alphaBytes = 151936L * 1024 / block * 2 * (values.length == 6 && values[5] == 1 ? 2 : 4);
        if (values[0] > weightBytes - embeddingBytes || values[1] != values[0] + embeddingBytes || values[2] != alphaBytes || values[1] > weightBytes - alphaBytes) throw new IOException("embedding metadata 引用超出已选择的权重文件");
        // Never merge arbitrary user config into MNN: base_dir, paths, cache and HTTP flags are excluded.
        return new JSONObject().put("model_type", "qwen3").put("hidden_size", 1024).put("attention_mask", "float").put("attention_type", "full").put("tie_embeddings", new JSONArray(tie.toString()));
    }
    public static JSONObject runtimeConfig(JSONObject p, File directory) throws Exception {
        return new JSONObject().put("llm_model", "llm.mnn").put("llm_weight", "llm.mnn.weight").put("backend_type", "cpu").put("thread_num", p.getInt("threads"))
            .put("precision", "low").put("memory", "low").put("max_all_tokens", p.getInt("maxInputTokens") + 256).put("max_new_tokens", 0)
            .put("use_mmap", false).put("use_cached_mmap", false).put("kvcache_mmap", false).put("prompt_cache", false).put("reuse_kv", false).put("tmp_path", directory.getCanonicalPath() + File.separator);
    }
    private static void set(JSONObject p, JSONArray changes, String key, Object value) throws Exception {
        Object old = p.opt(key); boolean same = old instanceof Number && value instanceof Number ? ((Number) old).doubleValue() == ((Number) value).doubleValue() : Objects.equals(old, value);
        if (!same) changes.put(new JSONObject().put("field", key).put("requested", old == null ? JSONObject.NULL : old).put("effective", value).put("reason", "sana_mobile_pipeline_or_application_guard"));
        p.put(key, value);
    }
    public static JSONObject prepare(ModelBundle bundle, JSONObject request) throws Exception {
        validate(bundle, request.getString("type"));
        if (!bundle.id.equals(request.getString("bundleId")) || request.optJSONArray("adapters") != null && request.getJSONArray("adapters").length() > 0) throw new IllegalArgumentException("此 Sana 配方不接收 LoRA 或其他模型快照");
        JSONObject input = request.getJSONObject("input"); String prompt = input.optString("prompt"), negative = input.optString("negativePrompt");
        if (!prompt.equals(EDIT_PROMPT) || !negative.isEmpty()) throw new IllegalArgumentException("此 Sana 编辑模型使用固定提示词，不接受自定义文本或负面条件；请使用模型表单的默认提示词");
        JSONObject result = DataFiles.copy(request), p = DataFiles.copy(request.getJSONObject("parameters")); JSONArray changes = new JSONArray();
        for (String key : Arrays.asList("width", "height")) set(p, changes, key, 512);
        String[] keys = {"steps", "threads", "maxInputTokens"}; int[] maxima = {50, 32, 1792}, defaults = {10, 4, 512};
        for (int i = 0; i < keys.length; i++) set(p, changes, keys[i], Math.max(1, Math.min(maxima[i], p.optInt(keys[i], defaults[i]))));
        if (p.has("useCfg") && !(p.get("useCfg") instanceof Boolean)) throw new IllegalArgumentException("useCfg 必须是布尔值");
        if (p.optBoolean("useCfg", false)) throw new IllegalArgumentException("此 Sana 图片编辑配方不启用 CFG");
        set(p, changes, "useCfg", false); double scale = p.optDouble("cfg", 4);
        if (!Double.isFinite(scale)) throw new IllegalArgumentException("CFG 必须是有限数值"); set(p, changes, "cfg", 4);
        long seed = p.optLong("seed", -1); set(p, changes, "seed", Math.max(-1, Math.min(Integer.MAX_VALUE, seed)));

        return result.put("diffusionPlan", DataFiles.copy(new JSONObject().put("schema", "lma.diffusion-plan/1").put("profile", "sana_edit_mnn").put("parameters", p).put("adjustments", changes)));
    }
}
