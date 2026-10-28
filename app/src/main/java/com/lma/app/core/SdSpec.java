package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Signed diffusion routing and sampling policy; declarations do not verify weight tensors. */
public final class SdSpec {
    private SdSpec() {}
    private static final Set<String> PIPELINES = new HashSet<>(Arrays.asList("sd15", "sd21_turbo", "sd15_lcm", "sdxl", "sdxl_lcm", "z_image_turbo", "flux2_klein_4b", "qwen_image_21", "wan21_13b"));
    public static void validate(ModelBundle bundle, String type) throws Exception {
        if (AdapterSpec.isAdapter(bundle)) throw new IllegalArgumentException("LoRA 需要与兼容的基础模型配对使用");
        if (!bundle.engine.equals("sd_cpp") || !bundle.backend.equals("cpu") || !PIPELINES.contains(bundle.pipeline)) throw new IllegalArgumentException("当前扩散引擎没有匹配的管线或后端");
        boolean video = type.equals("video.generate");
        if (!type.equals("image.generate") && !video || video != bundle.pipeline.equals("wan21_13b")) throw new IllegalArgumentException("此配方不支持所选生成任务");
        Set<String> roles = new HashSet<>(); for (ModelBundle.Component c : bundle.components) roles.add(c.role);
        if (roles.contains("model") == roles.contains("diffusion")) throw new IllegalArgumentException("配方必须明确选择完整 checkpoint 或独立 diffusion 组件");
        String arch = bundle.pipeline.startsWith("sd15") ? "sd15" : bundle.pipeline.startsWith("sdxl") ? "sdxl" : bundle.pipeline.equals("sd21_turbo") ? "sd21" : "";
        if (!arch.isEmpty()) {
            if (!bundle.architecture.equals(arch)) throw new IllegalArgumentException("扩散架构与管线声明不匹配");
            if (!roles.contains("clip_merges")) throw new IllegalArgumentException("请单独安装配套 CLIP merges 词表组件");
            ModelBundle.Component merges = bundle.component("clip_merges");
            if (!merges.format.equals("text") || merges.bytes > 32L * 1024 * 1024) throw new IllegalArgumentException("CLIP merges 格式或大小不合法");
            if (roles.contains("diffusion")) {
                if (arch.equals("sd21")) throw new IllegalArgumentException("SD-Turbo 当前配方需要含编码器与 VAE 的完整 checkpoint");
                for (String role : arch.equals("sdxl") ? Arrays.asList("clip_l", "clip_g", "vae") : Arrays.asList("clip_l", "vae"))
                    if (!roles.contains(role)) throw new IllegalArgumentException("独立 diffusion 配方缺少必需组件：" + role);
            }
            for (String role : Arrays.asList("model", "diffusion", "clip_l", "clip_g", "vae")) if (roles.contains(role) && !Arrays.asList("gguf", "safetensors").contains(bundle.component(role).format)) throw new IllegalArgumentException("扩散组件需要 GGUF 或 Safetensors：" + role);
        }
    }
    private static void set(JSONObject p, JSONArray changes, String field, Object value, String reason) throws Exception {
        Object old = p.opt(field);
        boolean same = old instanceof Number && value instanceof Number ? ((Number) old).doubleValue() == ((Number) value).doubleValue() : Objects.equals(old, value);
        if (!same) changes.put(new JSONObject().put("field", field).put("requested", old == null ? JSONObject.NULL : old).put("effective", value).put("reason", reason));
        p.put(field, value);
    }
    public static JSONObject prepare(ModelBundle base, List<ModelBundle> adapters, JSONObject request) throws Exception {
        validate(base, request.getString("type"));
        if (!base.id.equals(request.getString("bundleId"))) throw new IllegalArgumentException("扩散任务与模型快照不匹配");
        JSONArray selected = request.optJSONArray("adapters");
        if ((selected == null ? 0 : selected.length()) != adapters.size()) throw new IllegalArgumentException("扩散适配器快照不完整");
        int lcm = 0;
        for (int i = 0; i < adapters.size(); i++) {
            ModelBundle adapter = adapters.get(i); JSONObject item = selected.getJSONObject(i);
            if (!item.getString("bundleId").equals(adapter.id)) throw new IllegalArgumentException("扩散适配器顺序不匹配");
            AdapterSpec.requirePair(base, adapter);
            double scale = item.getDouble("scale");
            if (!Double.isFinite(scale) || scale < -4 || scale > 4) throw new IllegalArgumentException("LoRA 强度尚未归位");
            if (AdapterSpec.lcm(adapter)) { if (scale <= 0) throw new IllegalArgumentException("LCM-LoRA 加速需要大于零的强度"); lcm++; }
        }
        if (lcm > 1 || lcm > 0 && base.pipeline.endsWith("_lcm")) throw new IllegalArgumentException("一次只使用一个 LCM 加速来源；LCM checkpoint 无需再叠加 LCM-LoRA");
        String profile = lcm > 0 || base.pipeline.endsWith("_lcm") ? "lcm" : base.pipeline.equals("sd21_turbo") ? "sd_turbo" : "standard";
        JSONObject result = DataFiles.copy(request), p = DataFiles.copy(request.getJSONObject("parameters")); JSONArray changes = new JSONArray();
        if (!profile.equals("standard")) {
            if (!request.getJSONObject("input").optString("negativePrompt").isEmpty()) throw new IllegalArgumentException("当前低步数配方关闭 CFG，不支持负面提示词；请清空后重试");
            int maximum = profile.equals("lcm") ? 8 : 4;
            set(p, changes, "steps", Math.max(1, Math.min(maximum, p.optInt("steps", 4))), "distilled_sampling_limit");
            set(p, changes, "cfg", 1.0, "distilled_sampling_cfg_disabled");
            set(p, changes, "sampler", profile.equals("lcm") ? "lcm" : "euler_a", "distilled_sampling_method");
            set(p, changes, "scheduler", profile.equals("lcm") ? "lcm" : "discrete", "distilled_sampling_schedule");
        } else if (p.optString("sampler").equals("lcm") || p.optString("scheduler").equals("lcm")) throw new IllegalArgumentException("LCM 采样需要 LCM checkpoint 或明确声明的 LCM-LoRA");
        // Persisted JSON normalizes 1.0 to 1; compare the same representation after restart.
        result.put("diffusionPlan", DataFiles.copy(new JSONObject().put("schema", "lma.diffusion-plan/1").put("profile", profile).put("parameters", p).put("adjustments", changes)));
        return result;
    }
}
