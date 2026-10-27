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
            File binary = new File(app.getApplicationInfo().nativeLibraryDir, build.getString("file"));
            if (!binary.isFile() || !DataFiles.sha256(binary).equals(build.getString("sha256"))) throw new IOException("原生引擎文件与签名包清单不一致");
            JSONArray dependencies = build.optJSONArray("dependencies");
            if (dependencies != null) for (int d = 0; d < dependencies.length(); d++) {
                JSONObject dependency = dependencies.getJSONObject(d);
                File library = new File(app.getApplicationInfo().nativeLibraryDir, dependency.getString("file"));
                if (!library.isFile() || !DataFiles.sha256(library).equals(dependency.getString("sha256"))) throw new IOException("引擎依赖与签名包清单不一致");
            }
            if (id.equals("sd_cpp")) register(new SdEngine(app, binary, build));
            else if (id.equals("sherpa_tts")) register(new SherpaEngine(app, binary, build));
            else throw new IOException("未知的签名原生模块：" + id);
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
