package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.Collections;

/** Three sequential, same-phone LiteRT CPU stages; all four assets are user supplied. */
public final class StableAudioEngine implements LocalEngine {
    private final LmaApp app;private final File binary;private final JSONObject build;private final NativeWorker.Launcher launcher;
    public StableAudioEngine(LmaApp a,File f,JSONObject b) { this(a,f,b,ProcessBuilder::start); }
    StableAudioEngine(LmaApp a,File f,JSONObject b,NativeWorker.Launcher l) { app=a;binary=f;build=DataFiles.copy(b);launcher=l; }
    @Override public String id() { return "stable_audio_litert"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available",binary.isFile() && binary.canExecute()).put("deviceValidated",false); }
    @Override public void validate(ModelBundle b,String type) throws Exception { if(!binary.isFile() || !binary.canExecute())throw new IOException("当前 App 未安装 Stable Audio 原生引擎");StableAudioSpec.validate(b,type); }
    @Override public InputSpec inputs(ModelBundle b,String type) throws Exception { StableAudioSpec.validate(b,type);return new InputSpec(new JSONObject()); }
    @Override public JSONObject prepare(ModelBundle b,JSONObject request) throws Exception {
        StableAudioSpec.validate(b,request.getString("type"));StableAudioSpec.text(request.getJSONObject("input"));
        JSONObject result=DataFiles.copy(request),n=StableAudioSpec.parameters(request.getJSONObject("parameters"));JSONArray changes=result.optJSONArray("adjustments");if(changes==null)changes=new JSONArray();
        JSONArray a=n.getJSONArray("adjustments");for(int i=0;i<a.length();i++)changes.put(a.getJSONObject(i).put("reason","stable_audio_model_or_application_guard"));
        return result.put("parameters",n.getJSONObject("values")).put("adjustments",changes);
    }
    @Override public File generate(Context c) throws Exception {
        JSONObject request=c.request();BundleStore.Lease lease=c.model();validate(lease.bundle,request.getString("type"));c.check();StableAudioSpec.text(request.getJSONObject("input"));
        if(!c.adapters().isEmpty())throw new IOException("Stable Audio 不接受图像 LoRA");
        JSONObject n=StableAudioSpec.parameters(request.getJSONObject("parameters"));if(n.getJSONArray("adjustments").length()!=0)throw new IOException("参数快照超出范围，请明确重试任务");
        JSONObject p=n.getJSONObject("values");if(p.getLong("seed")==-1)p.put("seed",new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        c.execution(new JSONObject().put("effectiveParameters",p).put("pipeline",lease.bundle.pipeline).put("backend","cpu").put("fixedLatentFrames",256).put("decodedFrames",524288));
        EngineWorkspace work=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),c::check);final Process[] child={null};
        try {
            for(String role:new String[]{"conditioner","diffusion_model","audio_decoder","tokenizer"})work.link("models",role+(role.equals("tokenizer")?".model":".tflite"),lease.file(role));
            File output=c.output("wav");JSONObject command=new JSONObject().put("schema","lma.engine-request/1").put("type",request.getString("type")).put("pipeline",lease.bundle.pipeline).put("input",request.getJSONObject("input")).put("parameters",p).put("workspace",work.directory().getPath()).put("output",output.getPath());
            NativeWorker.run(app,binary,c,command,output,Collections.emptyMap(),builder->{Process process=launcher.start(builder);child[0]=process;return process;});
            JSONObject audio=WaveFile.inspect(output);
            if(audio.getInt("sampleRate")!=44100 || audio.getInt("channels")!=2 || audio.getInt("formatCode")!=1 || audio.getInt("bitsPerSample")!=16 || audio.getLong("samples")!=44100L*p.getInt("seconds"))throw new IOException("Stable Audio 未生成匹配时长的 44.1 kHz 立体声 PCM16 音频");
            return output;
        }finally{work.closeAfter(child[0]);}
    }
}
