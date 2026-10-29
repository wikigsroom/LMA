package com.lma.app;

import android.app.ActivityManager;
import android.os.Build;
import android.os.PowerManager;
import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** App-owned association plans; remaining user dependencies never start downloading here. */
public final class ModelAssemblies {
    private final LmaApp app;
    private final Map<String,AssemblyPlan> plans = new LinkedHashMap<>();
    public ModelAssemblies(LmaApp app) throws Exception {
        this.app = app; JSONObject catalogue, preparations;
        try (InputStream in = app.getAssets().open("model-assemblies.json")) { catalogue = new JSONObject(Store.read(in, 512 * 1024)); }
        try (InputStream in = app.getAssets().open("asset-preparations.json")) { preparations = new JSONObject(Store.read(in, 512 * 1024)); }
        if (!catalogue.getString("schema").equals("lma.model-assembly-catalogue/1")) throw new IOException("Unsupported App assembly catalogue");
        Map<String,PreparationPlan> sources = new HashMap<>(); JSONArray entries = preparations.getJSONArray("plans");
        for (int i = 0; i < entries.length(); i++) { PreparationPlan plan = new PreparationPlan(entries.getJSONObject(i)); sources.put(plan.id, plan); }
        entries = catalogue.getJSONArray("plans");
        for (int i = 0; i < entries.length(); i++) {
            JSONObject entry = entries.getJSONObject(i);
            AssemblyPlan plan = new AssemblyPlan(entry, sources.get(entry.getString("preparationId")), app.bundles.bundle(entry.getString("bundleId")));
            if (plans.put(plan.id, plan) != null) throw new IOException("Duplicate App assembly plan");
        }
    }
    public JSONArray options(JSONObject prepared) throws Exception {
        JSONArray result = new JSONArray();
        for (AssemblyPlan plan : plans.values()) {
            if (!plan.sourceBundleId.equals(prepared.getString("bundleId")) || !plan.preparationFingerprint.equals(prepared.getString("planFingerprint"))) continue;
            ModelBundle target = app.bundles.bundle(plan.bundleId); plan.matches(prepared, target);
            JSONObject description = plan.describe(target), targetPlan = app.bundles.plan(target.id); boolean associated = true;
            JSONArray files = targetPlan.getJSONArray("components"), missing = new JSONArray();
            for (int i = 0; i < files.length(); i++) {
                JSONObject file = files.getJSONObject(i);
                if (plan.roles.containsValue(file.getString("role"))) { if (!file.getBoolean("reusable")) associated = false; }
                else if (!file.getBoolean("reusable")) missing.put(DataFiles.copy(file));
            }
            result.put(description.put("remainingComponents", missing).put("associated", associated).put("installed", targetPlan.getBoolean("installed")));
        }
        return result;
    }
    public JSONArray snapshot(String bundleId) throws Exception {
        JSONArray records = app.prepared.snapshot(bundleId);
        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.getJSONObject(i);
            record.put("assemblyPlans", options(record)).put("inUse", record.optBoolean("inUse") || app.jobs.referencesPrepared(record.getString("id")));
        }
        return records;
    }
    public AssemblyPlan require(JSONObject request) throws Exception {
        AssemblyPlan plan = plans.get(request.getString("assemblyId"));
        if (plan == null || !plan.fingerprint.equals(request.getString("assemblyFingerprint"))) throw new IOException("App 关联方案已改变，请重新查看并明确选择当前方案");
        if (!plan.bundleId.equals(request.getString("bundleId"))) throw new IOException("关联方案与所选运行模型不匹配");
        JSONObject source = app.prepared.record(request.getString("preparedAssetsId")); plan.matches(source, app.bundles.bundle(plan.bundleId));
        JSONArray jobs = app.jobs.snapshot();
        for (int i = 0; i < jobs.length(); i++) { JSONObject job = jobs.getJSONObject(i); if (job.getString("id").equals(source.getString("jobId")) && !job.getString("state").equals("succeeded")) throw new IOException("源模型准备任务尚未成功完成"); }
        if (request.has("assemblySourceFingerprint") && !request.getString("assemblySourceFingerprint").equals(TaskInput.fingerprint(source))) throw new IOException("排队后的准备资产身份已改变，请重新提交");
        return plan;
    }
    public JSONObject admission() throws Exception {
        long reserve = 128L * 1024 * 1024;
        if (app.getFilesDir().getUsableSpace() < reserve) throw new IOException("关联运行模型需保留 128 MiB 元数据空间；模型文件通过本地硬链接复用");
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo(); ((ActivityManager) app.getSystemService(LmaApp.ACTIVITY_SERVICE)).getMemoryInfo(memory);
        if (memory.lowMemory || memory.availMem < reserve) throw new IOException("当前可用内存不足，请释放内存后重试");
        if (Build.VERSION.SDK_INT >= 29 && ((PowerManager) app.getSystemService(LmaApp.POWER_SERVICE)).getCurrentThermalStatus() >= PowerManager.THERMAL_STATUS_SEVERE) throw new IOException("手机当前温度过高，请降温后重试");
        return new JSONObject().put("reservedFreeBytes", reserve).put("modelBytesCopied", 0).put("automaticDownloads", false).put("physicalAndroid", false);
    }
}
