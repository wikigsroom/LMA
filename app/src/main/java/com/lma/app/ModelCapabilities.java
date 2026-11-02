package com.lma.app;

import com.lma.app.core.DataFiles;
import org.json.*;

/** One declaration source; executable operations remain the engine's responsibility. */
public final class ModelCapabilities {
    private final JSONObject catalogue;private final LmaApp app;
    public ModelCapabilities(LmaApp app) throws Exception {this.app=app;
        try (java.io.InputStream in = app.getAssets().open("capabilities.json")) { catalogue = new JSONObject(Store.read(in, 256 * 1024)); }
    }
    public JSONObject describe(JSONObject record) throws Exception {
        JSONObject known = catalogue.getJSONObject("models").optJSONObject(record.optString("id"));
        if (known != null){JSONObject value=DataFiles.copy(known),pair=app.visionPairs==null?null:app.visionPairs.pair(record.optString("id"));if(pair!=null){value.getJSONObject("lma").put("visionBridge","paired_component_required").put("pair",pair);value.getJSONObject("evidence").put("pinnedExportPair",true);}return value;}
        String task = record.optString("task");
        JSONArray nativeCaps = new JSONArray();
        nativeCaps.put(new JSONObject().put("tag", "input:text").put("support", "unknown").put("evidence",new JSONArray()));
        nativeCaps.put(new JSONObject().put("tag", "output:text").put("support", task.contains("text") || record.has("family") ? "publisher_metadata" : "unknown").put("evidence",new JSONArray()));
        for (String tag : new String[]{"input:image", "input:audio", "input:video", "tool:calling", "output:json"})
            nativeCaps.put(new JSONObject().put("tag", tag).put("support", "unknown").put("evidence", new JSONArray()));
        return new JSONObject().put("native",nativeCaps).put("lma",new JSONObject().put("operations",new JSONArray().put("text.generate")).put("visionBridge","unknown").put("modelToolReliability","unknown"))
            .put("composed",new JSONArray()).put("evidence",new JSONObject().put("phoneOutput",false).put("quality",false));
    }
    public JSONArray enrich(JSONArray records) throws Exception {
        for (int i=0;i<records.length();i++) records.getJSONObject(i).put("capabilities",describe(records.getJSONObject(i)));
        return records;
    }
}
