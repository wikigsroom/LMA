package com.lma.app;

import com.lma.app.core.*;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.util.*;

/** Only actual signed-App implementations are registered; missing modules stay unavailable. */
public final class LocalEngines {
    private final Map<String, LocalEngine> modules = new LinkedHashMap<>();
    public LocalEngines(LmaApp app) throws Exception {
        JSONObject manifest;
        try (InputStream in = app.getAssets().open("engine-builds.json")) { manifest = new JSONObject(Store.read(in, 512 * 1024)); }
        catch (FileNotFoundException absent) { return; }
        JSONArray engines = manifest.getJSONArray("engines");
        for (int i = 0; i < engines.length(); i++) {
            JSONObject build = engines.getJSONObject(i); String id = build.getString("engine");
            if (id.equals("sd_cpp")) {
                File binary = new File(app.getApplicationInfo().nativeLibraryDir, "liblma-sd.so");
                if (!binary.isFile() || !DataFiles.sha256(binary).equals(build.getString("sha256"))) throw new IOException("扩散引擎文件与签名包清单不一致");
                register(new SdEngine(app, binary, build));
            }
        }
    }
    private void register(LocalEngine engine) { if (modules.put(engine.id(), engine) != null) throw new IllegalStateException("Duplicate internal engine module"); }
    public LocalEngine require(ModelBundle bundle, String type) throws Exception {
        LocalEngine engine = modules.get(bundle.engine);
        if (engine == null) throw new IOException("当前基座尚未接入 " + bundle.engine + "；下载权重不会安装运行引擎");
        engine.validate(bundle, type); return engine;
    }
    public JSONArray snapshot() throws Exception { JSONArray result = new JSONArray(); for (LocalEngine engine : modules.values()) result.put(engine.describe()); return result; }
}
