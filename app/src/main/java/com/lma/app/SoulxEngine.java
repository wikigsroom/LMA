package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** One child, sequential CPU reference -> language -> acoustic stages on the same phone. */
public final class SoulxEngine implements LocalEngine {
    private final LmaApp app; private final File binary; private final JSONObject build; private final NativeWorker.Launcher launcher;
    public SoulxEngine(LmaApp app, File binary, JSONObject build) { this(app, binary, build, ProcessBuilder::start); }
    SoulxEngine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher) { this.app = app; this.binary = binary; this.build = DataFiles.copy(build); this.launcher = launcher; }
    @Override public String id() { return "soulx_native"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available", binary.isFile() && binary.canExecute()).put("deviceValidated", false); }
    @Override public void validate(ModelBundle b, String type) throws Exception { if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 未安装 SoulX 原生引擎"); SoulxSpec.validate(b, type); }
    @Override public InputSpec inputs(ModelBundle b, String type) throws Exception { SoulxSpec.validate(b, type); return SoulxSpec.inputs(); }
    @Override public JSONObject prepare(ModelBundle b, JSONObject request) throws Exception {
        SoulxSpec.validate(b, request.getString("type")); SoulxSpec.turns(request.getJSONObject("input"));
        JSONObject result = DataFiles.copy(request), n = SoulxSpec.parameters(request.getJSONObject("parameters")); JSONArray changes = result.optJSONArray("adjustments"); if (changes == null) changes = new JSONArray();
        JSONArray a = n.getJSONArray("adjustments"); for (int i = 0; i < a.length(); i++) changes.put(a.getJSONObject(i));
        return result.put("parameters", n.getJSONObject("values")).put("adjustments", changes);
    }
    @Override public File generate(Context c) throws Exception {
        JSONObject request = c.request(); BundleStore.Lease lease = c.model(); validate(lease.bundle, request.getString("type")); c.check();
        int references = SoulxSpec.references(request.getJSONObject("input")); SoulxSpec.turns(request.getJSONObject("input"));
        if (!c.adapters().isEmpty()) throw new IOException("SoulX 不接受图像 LoRA");
        JSONObject n = SoulxSpec.parameters(request.getJSONObject("parameters")); if (n.getJSONArray("adjustments").length() != 0) throw new IOException("SoulX 参数快照超出范围，请明确重试任务");
        JSONObject p = n.getJSONObject("values"); if (p.getLong("seed") == -1) p.put("seed", new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        c.execution(new JSONObject().put("effectiveParameters", p).put("pipeline", lease.bundle.pipeline).put("backend", "cpu").put("referenceSpeakers", references).put("stageLoading", "sequential"));
        EngineWorkspace work = new EngineWorkspace(new File(app.getFilesDir(), "engine-work"), c::check); final Process[] child = {null};
        try {
            for (Map.Entry<String, String> file : SoulxSpec.files().entrySet()) work.link("models", file.getValue(), lease.file(file.getKey()));
            for (int i = 1; i <= references; i++) {
                String role = "reference_s" + i; File source = c.input(role); JSONObject audio = WaveFile.inspect(source);
                if (source.length() > 1536000 || audio.getInt("sampleRate") != 24000 || audio.getInt("channels") != 1 || !(audio.getInt("formatCode") == 1 && audio.getInt("bitsPerSample") == 16 || audio.getInt("formatCode") == 3 && audio.getInt("bitsPerSample") == 32) || audio.getLong("samples") < 24000 || audio.getLong("samples") > 360000) throw new IOException("参考音频须为 1–15 秒、24 kHz 单声道 PCM16 / float32 WAV，请先显式转换后导入");
                work.link("inputs", role + ".wav", source);
            }
            File output = c.output("wav"); JSONObject command = new JSONObject().put("schema", "lma.engine-request/1").put("type", request.getString("type")).put("pipeline", lease.bundle.pipeline).put("input", request.getJSONObject("input")).put("parameters", p).put("workspace", work.directory().getPath()).put("output", output.getPath());
            NativeWorker.run(app, binary, c, command, output, Collections.emptyMap(), builder -> { Process process = launcher.start(builder); child[0] = process; return process; });
            JSONObject audio = WaveFile.inspect(output);
            if (audio.getInt("sampleRate") != 24000 || audio.getInt("channels") != 1 || audio.getInt("formatCode") != 1 || audio.getInt("bitsPerSample") != 16 || audio.getLong("samples") > 24000L * p.getInt("maxOutputSeconds")) throw new IOException("SoulX 输出不符合 24 kHz 单声道 PCM16 或任务时长约束");
            return output;
        } finally { work.closeAfter(child[0]); }
    }
}
