package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.Collections;

/** Same-phone old Local and Realtime WAV pipelines, with opt-in incremental Realtime PCM. */
public final class MossRqEngine implements LocalEngine {
    private final LmaApp app;private final File binary;private final JSONObject build;private final NativeWorker.Launcher launcher;
    public MossRqEngine(LmaApp a,File f,JSONObject b) { this(a,f,b,ProcessBuilder::start); }
    MossRqEngine(LmaApp a,File f,JSONObject b,NativeWorker.Launcher l) { app=a;binary=f;build=DataFiles.copy(b);launcher=l; }
    @Override public String id() { return "moss_rq_native"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available",binary.isFile() && binary.canExecute()).put("deviceValidated",false).put("audioStream",new JSONObject().put("schema",AudioPcm.SCHEMA).put("pipelines",new JSONArray().put("moss_realtime_rq_cpu_v1")).put("incrementalTextInput",false)); }
    @Override public void validate(ModelBundle b,String type) throws Exception { if(!binary.isFile() || !binary.canExecute())throw new IOException("当前 App 未安装 openmoss 原生引擎");MossRqSpec.validate(b,type); }
    @Override public InputSpec inputs(ModelBundle b,String type) throws Exception { MossRqSpec.validate(b,type);return MossRqSpec.inputs(); }
    @Override public JSONObject prepare(ModelBundle b,JSONObject request) throws Exception {
        MossRqSpec.validate(b,request.getString("type"));MossRqSpec.text(request.getJSONObject("input"));
        JSONObject result=DataFiles.copy(request),n=MossRqSpec.parameters(b,request.getJSONObject("parameters"));JSONArray a=result.optJSONArray("adjustments");if(a==null)a=new JSONArray();
        JSONArray changes=n.getJSONArray("adjustments");for(int i=0;i<changes.length();i++)a.put(changes.getJSONObject(i).put("reason","native_moss_rq_application_guard"));
        conditioning(b,request.getJSONObject("input"),n.getJSONObject("values"));return result.put("parameters",n.getJSONObject("values")).put("adjustments",a);
    }
    private static void conditioning(ModelBundle b,JSONObject input,JSONObject parameters) throws Exception { MossRqSpec.conditioning(input); }
    @Override public File generate(Context c) throws Exception {
        JSONObject request=c.request();BundleStore.Lease lease=c.model();validate(lease.bundle,request.getString("type"));c.check();MossRqSpec.text(request.getJSONObject("input"));
        if(!c.adapters().isEmpty())throw new IOException("MOSS 音频不接受图像 LoRA");
        JSONObject n=MossRqSpec.parameters(lease.bundle,request.getJSONObject("parameters"));if(n.getJSONArray("adjustments").length()!=0)throw new IOException("MOSS 参数快照超出范围，请明确重试任务");
        JSONObject p=n.getJSONObject("values");conditioning(lease.bundle,request.getJSONObject("input"),p);if(p.getLong("seed")==-1)p.put("seed",new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        c.execution(new JSONObject().put("effectiveParameters",p).put("pipeline",lease.bundle.pipeline).put("backend","cpu"));
        EngineWorkspace work=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),c::check);final Process[] child={null};
        try {
            for(String role:new String[]{"model","codec","tokenizer"})work.link("models",role+".gguf",lease.file(role));File output=c.output("wav");
            JSONObject command=new JSONObject().put("schema","lma.engine-request/1").put("type",request.getString("type")).put("pipeline",lease.bundle.pipeline).put("input",request.getJSONObject("input")).put("parameters",p).put("workspace",work.directory().getPath()).put("output",output.getPath());
            if(MossRqSpec.realtime(lease.bundle) && p.optBoolean("streamAudio")) {
                if(!c.audioStreaming())throw new IOException("当前任务无法接收流式音频，请关闭模型的流式试听设置");
                command.put("audioStream",new JSONObject().put("schema",AudioPcm.SCHEMA).put("format","pcm_s16le").put("sampleRate",24000).put("channels",1).put("maxFrames",p.getInt("maxNewTokens")*1920).put("maxChunkFrames",1920));
            }
            JSONArray refs=request.getJSONObject("input").optJSONArray("artifacts");if(refs!=null && refs.length()>0) {
                File f=c.input("reference_audio");MossRqSpec.reference(f);command.put("referenceAudio",work.link("inputs","reference_audio.wav",f).getPath());
            }
            NativeWorker.run(app,binary,c,command,output,Collections.emptyMap(),builder->{Process process=launcher.start(builder);child[0]=process;return process;});
            JSONObject audio=WaveFile.inspect(output);
            if(audio.getInt("sampleRate")!=24000 || audio.getInt("channels")!=1 || audio.getInt("formatCode")!=1 || audio.getInt("bitsPerSample")!=16)throw new IOException("MOSS 未生成匹配模型采样率 / 声道的 PCM16 音频");return output;
        }finally{work.closeAfter(child[0]);}
    }
}
