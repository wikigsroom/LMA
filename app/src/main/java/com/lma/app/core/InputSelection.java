package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Immutable media references; callers serialize preparation/job publication with artifact deletion. */
public final class InputSelection {
    private InputSelection() {}
    public static List<String> ids(JSONObject request) throws Exception {
        List<String> result = new ArrayList<>(); JSONObject input = request.optJSONObject("input");
        JSONArray refs = input == null ? null : input.optJSONArray("artifacts");
        if (refs != null) for (int i = 0; i < refs.length(); i++) result.add(ModelBundle.key(refs.getJSONObject(i).getString("artifactId")));
        return result;
    }
    public static JSONObject prepare(ArtifactStore store, InputSpec spec, JSONObject request) throws Exception {
        JSONArray refs = request.getJSONObject("input").optJSONArray("artifacts"), receipts = new JSONArray();
        if (refs != null) for (int i = 0; i < refs.length(); i++) {
            JSONObject ref = refs.getJSONObject(i), artifact = store.get(ref.getString("artifactId")); store.file(artifact.getString("id"));
            receipts.put(new JSONObject().put("role", ref.getString("role")).put("artifactId", artifact.getString("id")).put("sha256", artifact.getString("sha256"))
                    .put("bytes", artifact.getLong("bytes")).put("metadata", DataFiles.copy(artifact.getJSONObject("metadata"))));
        }
        spec.validate(receipts, request.getJSONObject("input")); JSONObject result = DataFiles.copy(request);
        if (receipts.length() > 0) result.put("inputReceipts", receipts);
        return result;
    }
    public static Selection acquire(ArtifactStore store, InputSpec spec, JSONObject request, DataFiles.Check check) throws Exception {
        Selection result = new Selection();
        try {
            JSONArray receipts = request.optJSONArray("inputReceipts"); if (receipts == null) receipts = new JSONArray();
            List<String> ids = ids(request);
            if (receipts.length() != ids.size()) throw new IOException("Task input receipts are missing or inconsistent");
            spec.validate(receipts, request.getJSONObject("input"));
            for (int i = 0; i < receipts.length(); i++) {
                check.run(); JSONObject receipt = receipts.getJSONObject(i); String role = receipt.getString("role"), id = receipt.getString("artifactId");
                JSONObject reference = request.getJSONObject("input").getJSONArray("artifacts").getJSONObject(i);
                if (!ids.get(i).equals(id) || !reference.getString("role").equals(role)) throw new IOException("Task input binding changed");
                ArtifactStore.Lease lease = store.acquire(id); result.leases.add(lease);
                JSONObject artifact = store.get(id);
                if (lease.file.length() != receipt.getLong("bytes") || !artifact.getString("sha256").equals(receipt.getString("sha256")) || !DataFiles.canonical(artifact.getJSONObject("metadata")).equals(DataFiles.canonical(receipt.getJSONObject("metadata"))) || !DataFiles.sha256(lease.file, check).equals(receipt.getString("sha256"))) throw new IOException("Task input is missing or changed; import it again explicitly");
                result.files.put(role, lease.file);
            }
            check.run(); return result;
        } catch (Exception error) { result.close(); throw error; }
    }
    public static final class Selection implements AutoCloseable {
        private final List<ArtifactStore.Lease> leases = new ArrayList<>();
        private final Map<String, File> files = new LinkedHashMap<>();
        public File file(String role) throws IOException { File file = files.get(InputSpec.key(role)); if (file == null) throw new IOException("No selected local input for role: " + role); return file; }
        @Override public void close() { for (ArtifactStore.Lease lease : leases) lease.close(); leases.clear(); files.clear(); }
    }
}
