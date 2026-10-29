package com.lma.app;

import android.app.ActivityManager;
import android.os.Build;
import android.os.PowerManager;
import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Foundation-owned preparation programs, independent from model-generation adapters. */
public final class ModelPreparations {
    private final LmaApp app;
    private final Map<String,PreparationPlan> plans = new LinkedHashMap<>();
    private final Map<String,File> programs = new HashMap<>();
    public ModelPreparations(LmaApp app) throws Exception {
        this.app = app; JSONObject catalogue, builds;
        try (InputStream in = app.getAssets().open("asset-preparations.json")) { catalogue = new JSONObject(Store.read(in, 512 * 1024)); }
        try (InputStream in = app.getAssets().open("engine-builds.json")) { builds = new JSONObject(Store.read(in, 512 * 1024)); }
        if (!catalogue.getString("schema").equals("lma.asset-preparation-catalogue/1")) throw new IOException("Unknown foundation preparation catalogue");
        JSONArray modules = builds.optJSONArray("preparations");
        if (modules != null) for (int i = 0; i < modules.length(); i++) {
            JSONObject module = modules.getJSONObject(i); String id = ModelBundle.key(module.getString("engine"));
            String name = EngineWorkspace.filename(module.getString("file")); File program = new File(app.getApplicationInfo().nativeLibraryDir, name);
            if (!program.isFile() || program.length() != module.getLong("bytes") || !DataFiles.sha256(program).equals(module.getString("sha256")) || programs.put(id, program) != null) throw new IOException("Preparation program differs from the signed App");
        }
        JSONArray entries = catalogue.getJSONArray("plans");
        for (int i = 0; i < entries.length(); i++) {
            PreparationPlan plan = new PreparationPlan(entries.getJSONObject(i));
            for (PreparationPlan.Stage stage : plan.stages) if (!programs.containsKey(stage.module)) throw new IOException("Preparation plan has no signed program");
            if (plans.put(plan.id, plan) != null) throw new IOException("Duplicate preparation plan");
        }
    }
    public JSONArray options(ModelBundle bundle) throws Exception {
        JSONArray result = new JSONArray();
        for (PreparationPlan plan : plans.values()) if (plan.matches(bundle)) result.put(plan.describe().put("ready", app.prepared.contains(bundle.id, plan)).put("available", true));
        return result;
    }
    public PreparationPlan require(JSONObject request, ModelBundle bundle) throws Exception {
        PreparationPlan plan = plans.get(request.getString("preparationId"));
        if (plan == null || !plan.fingerprint.equals(request.getString("planFingerprint"))) throw new IOException("App 准备方案已改变，请重新查看并明确选择当前方案");
        if (!plan.matches(bundle)) throw new IOException("所选源文件的版本、大小或 SHA 与准备方案不匹配");
        if (request.has("sourceBundleFingerprint") && !request.getString("sourceBundleFingerprint").equals(TaskInput.fingerprint(bundle.json()))) throw new IOException("排队后的源模型配方已改变，请重新提交");
        return plan;
    }
    public JSONObject admission(PreparationPlan plan) throws Exception {
        if (app.getFilesDir().getUsableSpace() < plan.reserveBytes) throw new IOException("准备运行资产需要额外 " + plan.reserveBytes + " 字节可用空间；源文件会保留");
        ActivityManager.MemoryInfo memory = new ActivityManager.MemoryInfo(); ((ActivityManager) app.getSystemService(LmaApp.ACTIVITY_SERVICE)).getMemoryInfo(memory);
        if (memory.lowMemory || memory.availMem < 256L * 1024 * 1024) throw new IOException("当前可用内存不足以安全准备模型资产，请释放内存后重试");
        if (Build.VERSION.SDK_INT >= 29 && ((PowerManager) app.getSystemService(LmaApp.POWER_SERVICE)).getCurrentThermalStatus() >= PowerManager.THERMAL_STATUS_SEVERE) throw new IOException("手机当前温度过高，请降温后重试");
        return plan.describe().put("availableRamBytes", memory.availMem).put("availableStorageBytes", app.getFilesDir().getUsableSpace()).put("physicalAndroidMeasured", false);
    }
    public void run(PreparationPlan plan, BundleStore.Lease source, PreparedAssets.Session session, NativePreparation.Context context) throws Exception {
        NativePreparation.run(plan, source.file(plan.sourceRole), programs, session, context);
    }
    public File graphs(PreparationPlan plan, PreparationPlan.Stage stage) throws Exception {
        File root = new File(app.getFilesDir(), "preparation-code");
        if (Files.isSymbolicLink(root.toPath()) || !root.getCanonicalFile().equals(root.getAbsoluteFile())) throw new IOException("Architecture cache is an alias");
        Files.createDirectories(root.toPath()); File folder = new File(root, stage.module + "_" + plan.fingerprint);
        if (Files.isSymbolicLink(folder.toPath()) || !folder.getCanonicalFile().equals(folder.getAbsoluteFile())) throw new IOException("Architecture cache escaped its private root");
        Files.createDirectories(folder.toPath());
        for (int i = 0; i < stage.graphs.length(); i++) {
            JSONObject graph = stage.graphs.getJSONObject(i); File file = new File(folder, graph.getString("file"));
            if (Files.exists(file.toPath(), LinkOption.NOFOLLOW_LINKS)) { PreparedAssets.verify(file, graph.getLong("bytes"), graph.getString("sha256"), () -> {}); continue; }
            File temporary = new File(folder, graph.getString("file") + ".tmp");
            if (Files.exists(temporary.toPath(), LinkOption.NOFOLLOW_LINKS)) { if (!Files.isRegularFile(temporary.toPath(), LinkOption.NOFOLLOW_LINKS)) throw new IOException("Invalid architecture staging file"); Files.delete(temporary.toPath()); }
            try {
                try (InputStream input = app.getAssets().open("preparations/" + stage.module + "/" + graph.getString("file")); OutputStream out = Files.newOutputStream(temporary.toPath(), StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                    byte[] buffer = new byte[8192]; long total = 0; int count;
                    while ((count = input.read(buffer)) >= 0) { total += count; if (total > graph.getLong("bytes")) throw new IOException("Architecture resource exceeds signed size"); out.write(buffer, 0, count); }
                }
                PreparedAssets.verify(temporary, graph.getLong("bytes"), graph.getString("sha256"), () -> {});
                Files.move(temporary.toPath(), file.toPath());
            } finally { if (Files.isRegularFile(temporary.toPath(), LinkOption.NOFOLLOW_LINKS)) Files.delete(temporary.toPath()); }
        }
        return folder;
    }
}
