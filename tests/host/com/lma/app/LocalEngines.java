package com.lma.app;

import org.json.JSONArray;
import com.lma.app.core.ModelBundle;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** No model execution modules are fabricated in host gateway checks. */
public final class LocalEngines {
    private final Map<String, LocalEngine> fixtures = new ConcurrentHashMap<>();
    public void fixture(LocalEngine engine) { fixtures.put(engine.id(), engine); }
    public LocalEngine require(ModelBundle bundle, String type) throws Exception {
        LocalEngine engine = fixtures.get(bundle.engine);
        if (engine == null) throw new java.io.IOException("No real engine in this host port");
        engine.validate(bundle, type); return engine;
    }
    public org.json.JSONObject inputSchemas(ModelBundle bundle) { return new org.json.JSONObject(); }
    public JSONArray snapshot() { return new JSONArray(); }
}
