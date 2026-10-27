package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Data-only LoRA compatibility declarations; declarations are not inspected weight evidence. */
public final class AdapterSpec {
    private AdapterSpec() {}
    public static boolean isAdapter(ModelBundle bundle) { return bundle.json().has("adapter"); }
    public static void validate(ModelBundle bundle) throws Exception {
        JSONObject value = bundle.json();
        if (!value.has("adapter")) return;
        JSONObject spec = value.getJSONObject("adapter");
        for (Iterator<String> it = spec.keys(); it.hasNext();) if (!Arrays.asList("schema", "kind", "baseArchitectures", "basePipelines", "baseModelIds").contains(it.next())) throw new IllegalArgumentException("Unknown adapter declaration field");
        if (!spec.getString("schema").equals("lma.adapter/1") || !spec.getString("kind").equals("lora")) throw new IllegalArgumentException("Unsupported adapter schema or kind");
        if (!bundle.engine.equals("sd_cpp") || !bundle.backend.equals("cpu") || !bundle.pipeline.equals("lora") || !bundle.tasks.equals(Collections.singleton("image"))) throw new IllegalArgumentException("This LoRA adapter requires the local image CPU engine");
        Set<String> architectures = keys(spec.getJSONArray("baseArchitectures"));
        if (architectures.size() != 1 || !architectures.contains(bundle.architecture) || !Arrays.asList("sd15", "sdxl").contains(bundle.architecture)) throw new IllegalArgumentException("Declare one matching SD 1.5 or SDXL base architecture");
        Set<String> pipelines = keys(spec.getJSONArray("basePipelines"));
        for (String pipeline : pipelines) if (!pipeline.equals(bundle.architecture) && !pipeline.equals(bundle.architecture + "_lcm")) throw new IllegalArgumentException("Adapter base pipeline does not match its architecture");
        if (spec.has("baseModelIds")) keys(spec.getJSONArray("baseModelIds"));
        if (bundle.components.size() != 1 || !bundle.components.get(0).role.equals("lora") || !Arrays.asList("safetensors", "gguf").contains(bundle.components.get(0).format)) throw new IllegalArgumentException("A LoRA bundle requires one safetensors/GGUF lora component");
        JSONObject fields = bundle.parameters().json().optJSONObject("fields");
        if (fields == null || fields.length() != 1 || !fields.has("scale") || !Arrays.asList("number", "integer").contains(fields.getJSONObject("scale").getString("type"))) throw new IllegalArgumentException("A LoRA bundle declares only its independent numeric scale parameter");
        JSONObject scale = fields.getJSONObject("scale");
        if (!scale.has("minimum") || !scale.has("maximum") || scale.getDouble("minimum") < -4 || scale.getDouble("maximum") > 4) throw new IllegalArgumentException("Declare LoRA scale limits within the engine range -4 to 4");
    }
    private static Set<String> keys(JSONArray values) throws Exception {
        if (values.length() < 1 || values.length() > 32) throw new IllegalArgumentException("Invalid adapter compatibility list");
        Set<String> result = new LinkedHashSet<>();
        for (int i = 0; i < values.length(); i++) if (!result.add(ModelBundle.key(values.getString(i)))) throw new IllegalArgumentException("Duplicate adapter compatibility entry");
        return result;
    }
    public static void requirePair(ModelBundle base, ModelBundle adapter) throws Exception {
        validate(adapter);
        if (!isAdapter(adapter)) throw new IllegalArgumentException("The selected entry is not a LoRA adapter");
        JSONObject spec = adapter.json().getJSONObject("adapter");
        if (isAdapter(base) || !base.engine.equals(adapter.engine) || !base.backend.equals(adapter.backend) || !base.tasks.contains("image") || !keys(spec.getJSONArray("baseArchitectures")).contains(base.architecture) || !keys(spec.getJSONArray("basePipelines")).contains(base.pipeline)
                || spec.has("baseModelIds") && !keys(spec.getJSONArray("baseModelIds")).contains(base.modelId)) throw new IllegalArgumentException("LoRA 与所选基础模型的架构、配方或后端不兼容");
    }
    public static JSONObject scale(ModelBundle adapter, JSONObject saved, JSONObject selection) throws Exception {
        validate(adapter);
        JSONObject changes = new JSONObject(); if (selection.has("scale")) changes.put("scale", selection.get("scale"));
        JSONObject normalized = adapter.parameters().normalize(saved, changes), values = normalized.getJSONObject("values");
        double before = values.getDouble("scale"), effective = Math.max(-4, Math.min(4, before));
        if (before != effective) normalized.getJSONArray("adjustments").put(new JSONObject().put("field", "scale").put("requested", before).put("effective", effective).put("reason", "engine_application_guard"));
        values.put("scale", effective); return normalized;
    }
    /** Conservative extra guard, not measured RAM: possible four-byte expanded weights. */
    public static long extraRam(ModelBundle adapter) { return Math.multiplyExact(adapter.component("lora").bytes, 4L); }
}
