package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.Collections;

/** Native same-phone Local-v1.5 speech and SoundEffect-v2 flow-matching pipelines. */
public final class OpenMossEngine implements LocalEngine {
    private final LmaApp app;private final File binary;private final JSONObject build;private final NativeWorker.Launcher launcher;
    public OpenMossEngine(LmaApp a,File f,JSONObject b) { this(a,f,b,ProcessBuilder::start); }
    OpenMossEngine(LmaApp a,File f,JSONObject b,NativeWorker.Launcher l) { app=a;binary=f;build=DataFiles.copy(b);launcher=l; }
    @Override public String id() { return "openmoss_native"; }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available",binary.isFile() && binary.canExecute()).put("deviceValidated",false); }
    @Override public void validate(ModelBundle b,String type) throws Exception { if(!binary.isFile() || !binary.canExecute())throw new IOException("当前 App 未安装 openmoss 原生引擎");OpenMossSpec.validate(b,type); }
    @Override public InputSpec inputs(ModelBundle b,String type) throws Exception { OpenMossSpec.validate(b,type);return OpenMossSpec.inputs(b); }
    @Override public JSONObject prepare(ModelBundle b,JSONObject request) throws Exception {
        OpenMossSpec.validate(b,request.getString("type"));OpenMossSpec.text(b,request.getJSONObject("input"));
        JSONObject result=DataFiles.copy(request),n=OpenMossSpec.parameters(b,request.getJSONObject("parameters"));JSONArray a=result.optJSONArray("adjustments");if(a==null)a=new JSONArray();
        JSONArray changes=n.getJSONArray("adjustments");for(int i=0;i<changes.length();i++)a.put(changes.getJSONObject(i).put("reason","native_openmoss_application_guard"));
        conditioning(b,request.getJSONObject("input"),n.getJSONObject("values"));return result.put("parameters",n.getJSONObject("values")).put("adjustments",a);
    }
    private static void conditioning(ModelBundle b,JSONObject input,JSONObject parameters) throws Exception { if(OpenMossSpec.sound(b) && parameters.getDouble("cfgScale")==1 && !input.optString("negativePrompt","").trim().isEmpty())throw new IOException("CFG=1 不使用负向条件；请提高 CFG 或清空负面提示词"); }
    @Override public File generate(Context c) throws Exception {
        JSONObject request=c.request();BundleStore.Lease lease=c.model();validate(lease.bundle,request.getString("type"));c.check();OpenMossSpec.text(lease.bundle,request.getJSONObject("input"));
        if(!c.adapters().isEmpty())throw new IOException("MOSS 音频不接受图像 LoRA");
        JSONObject n=OpenMossSpec.parameters(lease.bundle,request.getJSONObject("parameters"));if(n.getJSONArray("adjustments").length()!=0)throw new IOException("MOSS 参数快照超出范围，请明确重试任务");
        JSONObject p=n.getJSONObject("values");conditioning(lease.bundle,request.getJSONObject("input"),p);if(p.getLong("seed")==-1)p.put("seed",new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        c.execution(new JSONObject().put("effectiveParameters",p).put("pipeline",lease.bundle.pipeline).put("backend","cpu"));
        EngineWorkspace work=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),c::check);final Process[] child={null};
        try {
            work.link("models","model.gguf",lease.file("backbone"));work.link("models","model.extras.gguf",lease.file("extras"));File output=c.output("wav");
            JSONObject command=new JSONObject().put("schema","lma.engine-request/1").put("type",request.getString("type")).put("pipeline",lease.bundle.pipeline).put("input",request.getJSONObject("input")).put("parameters",p).put("workspace",work.directory().getPath()).put("output",output.getPath());
            JSONArray refs=request.getJSONObject("input").optJSONArray("artifacts");if(refs!=null)for(int i=0;i<refs.length();i++) {
                if(OpenMossSpec.sound(lease.bundle) || !refs.getJSONObject(i).getString("role").equals("reference_audio") || command.has("referenceAudio"))throw new IOException("此配方仅接受一个 Local-v1.5 参考 WAV");
                File f=c.input("reference_audio");OpenMossSpec.reference(f);command.put("referenceAudio",work.link("inputs","reference.wav",f).getPath());
            }
            NativeWorker.run(app,binary,c,command,output,Collections.emptyMap(),builder->{Process process=launcher.start(builder);child[0]=process;return process;});
            JSONObject audio=WaveFile.inspect(output);int channels=OpenMossSpec.sound(lease.bundle)?1:2;
            if(audio.getInt("sampleRate")!=48000 || audio.getInt("channels")!=channels || audio.getInt("formatCode")!=1 || audio.getInt("bitsPerSample")!=16)throw new IOException("MOSS 未生成匹配的 48 kHz PCM16 音频");return output;
        }finally{work.closeAfter(child[0]);}
    }
}
