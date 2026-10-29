package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.IOException;
import java.util.*;

/** Explicit local association: verified hardlinks only, no downloader or model executor. */
public final class PreparedModelAssembly {
    private PreparedModelAssembly() {}
    public interface Context {
        void check() throws IOException;
        void progress(String stage) throws Exception;
    }
    public static JSONObject run(AssemblyPlan plan, PreparedAssets prepared, BundleStore bundles, JSONObject request, String jobId, Context context) throws Exception {
        context.check(); ModelBundle target = bundles.bundle(request.getString("bundleId"));
        if (!plan.id.equals(request.getString("assemblyId")) || !plan.fingerprint.equals(request.getString("assemblyFingerprint"))) throw new IOException("Assembly plan changed; explicitly select the current plan");
        String sourceId = request.getString("preparedAssetsId"); JSONObject source = prepared.record(sourceId);
        plan.matches(source, target); String sourceFingerprint = TaskInput.fingerprint(source);
        if (!sourceFingerprint.equals(request.getString("assemblySourceFingerprint"))) throw new IOException("Prepared source identity changed after queuing");
        context.progress("verifying_prepared_assets");
        try (PreparedAssets.Lease lease = prepared.acquire(sourceId, context::check)) {
            source = lease.record(); plan.matches(source, target);
            if (!sourceFingerprint.equals(TaskInput.fingerprint(source))) throw new IOException("Prepared source identity changed before assembly");
            Map<String,File> files = new LinkedHashMap<>();
            for (Map.Entry<String,String> role : plan.roles.entrySet()) files.put(role.getValue(), lease.file(role.getKey()));
            context.progress("associating_runtime_assets");
            bundles.adoptAvailableLocal(target, files, new JSONObject(), context::check);
            JSONObject state = bundles.plan(target.id); long bytes = 0;
            for (String role : files.keySet()) bytes = Math.addExact(bytes, target.component(role).bytes);
            return new JSONObject().put("schema", "lma.model-assembly-result/1").put("jobId", jobId).put("bundleId", target.id)
                    .put("preparedAssetsId", sourceId).put("assemblyId", plan.id).put("assemblyFingerprint", plan.fingerprint).put("sourceFingerprint", sourceFingerprint)
                    .put("linkedComponents", files.size()).put("linkedBytes", bytes).put("remainingBytes", state.getLong("remainingBytes"))
                    .put("installed", state.getBoolean("installed")).put("automaticDownloads", false).put("modelInference", false).put("physicalAndroid", false);
        }
    }
}
