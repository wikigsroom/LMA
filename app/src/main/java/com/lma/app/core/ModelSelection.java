package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Resolve explicit installed peers and freeze scales without initiating a transfer. */
public final class ModelSelection {
    private ModelSelection() {}
    public static List<String> ids(JSONObject request) throws Exception {
        List<String> result = new ArrayList<>(); result.add(ModelBundle.key(request.getString("bundleId")));
        JSONArray adapters = request.optJSONArray("adapters");
        if (adapters != null) for (int i = 0; i < adapters.length(); i++) {
            String id = ModelBundle.key(adapters.getJSONObject(i).getString("bundleId"));
            if (result.contains(id)) throw new IllegalArgumentException("Select each model or adapter only once");
            result.add(id);
        }
        if (result.size() > 9) throw new IllegalArgumentException("At most eight LoRAs can be selected");
        return result;
    }
    public static JSONObject prepare(BundleStore store, ModelBundle base, JSONObject request) throws Exception {
        if (!base.id.equals(request.getString("bundleId"))) throw new IllegalArgumentException("Base selection does not match the task");
        if (AdapterSpec.isAdapter(base)) throw new IllegalArgumentException("LoRA 需要先选择兼容的基础模型，不能单独生成");
        JSONArray selected = request.optJSONArray("adapters"), effective = new JSONArray(), adjustments = new JSONArray();
        if (selected != null && !request.getString("type").equals("image.generate")) throw new IllegalArgumentException("This adapter contract supports image generation only");
        try (BundleStore.Selection leases = store.acquireAll(ids(request))) {
            for (int i = 0; selected != null && i < selected.length(); i++) {
                JSONObject item = selected.getJSONObject(i); ModelBundle adapter = leases.models.get(i + 1).bundle;
                AdapterSpec.requirePair(leases.models.get(0).bundle, adapter);
                JSONObject normalized = AdapterSpec.scale(adapter, store.settings(adapter.id).getJSONObject("values"), item);
                effective.put(new JSONObject().put("bundleId", adapter.id).put("scale", normalized.getJSONObject("values").getDouble("scale")));
                if (normalized.getJSONArray("adjustments").length() > 0) adjustments.put(new JSONObject().put("bundleId", adapter.id).put("adjustments", normalized.getJSONArray("adjustments")));
            }
        }
        JSONObject result = DataFiles.copy(request);
        if (selected != null) result.put("adapters", effective);
        if (adjustments.length() > 0) result.put("adapterAdjustments", adjustments);
        return result;
    }
    public static JSONArray nativeLoras(BundleStore.Lease base, List<BundleStore.Lease> adapters, JSONObject request) throws Exception {
        JSONArray selected = request.optJSONArray("adapters"), result = new JSONArray();
        if (!base.bundle.id.equals(request.getString("bundleId")) || adapters.size() > 8) throw new IllegalArgumentException("Model lease snapshot does not match the task");
        if (!adapters.isEmpty() && !request.getString("type").equals("image.generate")) throw new IllegalArgumentException("LoRA selection requires image generation");
        if ((selected == null ? 0 : selected.length()) != adapters.size()) throw new IllegalArgumentException("Adapter lease snapshot does not match the task");
        for (int i = 0; i < adapters.size(); i++) {
            BundleStore.Lease adapter = adapters.get(i); JSONObject item = selected.getJSONObject(i);
            if (!adapter.bundle.id.equals(item.getString("bundleId"))) throw new IllegalArgumentException("Adapter lease order does not match the task");
            AdapterSpec.requirePair(base.bundle, adapter.bundle);
            double scale = item.getDouble("scale");
            if (!Double.isFinite(scale) || scale < -4 || scale > 4) throw new IllegalArgumentException("Unnormalized LoRA scale");
            result.put(new JSONObject().put("path", adapter.file("lora").getAbsolutePath()).put("scale", scale));
        }
        return result;
    }
}
