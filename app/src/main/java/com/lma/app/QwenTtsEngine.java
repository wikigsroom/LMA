package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.Collections;

/** Same-phone BPE -> Talker/Code Predictor -> 12Hz codec -> WAV pipeline. */
public final class QwenTtsEngine implements LocalEngine {
    private final LmaApp app; private final File binary; private final JSONObject build; private final NativeWorker.Launcher launcher;
    public QwenTtsEngine(LmaApp app, File binary, JSONObject build) { this(app,binary,build,ProcessBuilder::start); }
    QwenTtsEngine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher) { this.app=app; this.binary=binary; this.build=DataFiles.copy(build); this.launcher=launcher; }
    @Override public String id() { return "qwen_tts_native"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available",binary.isFile() && binary.canExecute()).put("deviceValidated",false); }
    @Override public void validate(ModelBundle bundle,String type) throws Exception { if (!binary.isFile() || !binary.canExecute()) throw new IOException("当前 App 没有安装 Qwen 本地语音引擎"); QwenTtsSpec.validate(bundle,type); }
    @Override public InputSpec inputs(ModelBundle bundle,String type) throws Exception { QwenTtsSpec.validate(bundle,type); return QwenTtsSpec.inputs(); }
    @Override public JSONObject prepare(ModelBundle bundle,JSONObject request) throws Exception {
        QwenTtsSpec.validate(bundle,request.getString("type")); TtsSpec.text(request.getJSONObject("input"));
        JSONObject normalized=QwenTtsSpec.parameters(request.getJSONObject("parameters")), result=DataFiles.copy(request);
        JSONArray adjustments=result.optJSONArray("adjustments"); if(adjustments==null) adjustments=new JSONArray();
        JSONArray changes=normalized.getJSONArray("adjustments"); for(int i=0;i<changes.length();i++) adjustments.put(changes.getJSONObject(i).put("reason","native_qwen_application_guard"));
        return result.put("parameters",normalized.getJSONObject("values")).put("adjustments",adjustments);
    }
    @Override public File generate(Context context) throws Exception {
        JSONObject request=context.request(); BundleStore.Lease lease=context.model(); validate(lease.bundle,request.getString("type")); context.check(); TtsSpec.text(request.getJSONObject("input"));
        if(!context.adapters().isEmpty()) throw new IOException("Qwen Base 不接受图像适配器");
        JSONObject normalized=QwenTtsSpec.parameters(request.getJSONObject("parameters"));
        if(normalized.getJSONArray("adjustments").length()!=0) throw new IOException("语音参数快照已超出当前基座约束，请明确重试任务");
        JSONObject parameters=normalized.getJSONObject("values"); if(parameters.getLong("seed")==-1) parameters.put("seed",new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        context.execution(new JSONObject().put("effectiveParameters",parameters).put("pipeline",lease.bundle.pipeline).put("backend","cpu"));
        EngineWorkspace workspace=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),context::check); final Process[] child={null};
        try {
            workspace.link("models","qwen-talker-0.6b-base.gguf",lease.file("talker")); workspace.link("models","qwen-tokenizer-12hz.gguf",lease.file("audio_codec"));
            File output=context.output("wav"); JSONObject command=new JSONObject().put("schema","lma.engine-request/1").put("type","speech.synthesize").put("pipeline",lease.bundle.pipeline).put("input",request.getJSONObject("input")).put("parameters",parameters).put("workspace",workspace.directory().getPath()).put("output",output.getPath());
            JSONArray refs=request.getJSONObject("input").optJSONArray("artifacts"); if(refs!=null) for(int i=0;i<refs.length();i++) {
                if(!refs.getJSONObject(i).getString("role").equals("reference_audio") || command.has("referenceAudio")) throw new IOException("只接受一个明确选择的参考 WAV");
                File reference=context.input("reference_audio"); QwenTtsSpec.reference(reference); command.put("referenceAudio",workspace.link("inputs","reference.wav",reference).getPath());
            }
            NativeWorker.run(app,binary,context,command,output,Collections.emptyMap(),builder->{Process process=launcher.start(builder);child[0]=process;return process;});
            JSONObject audio=WaveFile.inspect(output); if(audio.getInt("sampleRate")!=24000 || audio.getInt("channels")!=1 || audio.getInt("bitsPerSample")!=16) throw new IOException("Qwen 引擎未产生有效的 24 kHz 单声道音频");
            return output;
        } finally { workspace.closeAfter(child[0]); }
    }
}
