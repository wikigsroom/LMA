package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.nio.file.*;

/** Sequential old-LTX stages under one task/model lease, followed by same-phone MediaCodec. */
public final class Ltx098Engine implements LocalEngine {
    interface Encoder { void encode(File frames, File output, DataFiles.Check check) throws Exception; }
    interface Specification { void validate(ModelBundle bundle,String type) throws Exception; }
    private final LmaApp app; private final File binary; private final JSONObject build;
    private final NativeWorker.Launcher launcher; private final Encoder encoder;
    private final Specification specification;
    static final String TEXT = "liblma-ltx098-app-text.so", SAMPLE = "liblma-ltx098-app-sample.so", VAE = "liblma-ltx098-app-vae.so";
    public Ltx098Engine(LmaApp app, File binary, JSONObject build) { this(app,binary,build,ProcessBuilder::start,(frames,output,check)->VideoEncoder.encode(frames,output,check::run)); }
    Ltx098Engine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher, Encoder encoder) { this(app,binary,build,launcher,encoder,Ltx098Engine::specification); }
    Ltx098Engine(LmaApp app, File binary, JSONObject build, NativeWorker.Launcher launcher, Encoder encoder,Specification specification) { this.app=app; this.binary=binary; this.build=DataFiles.copy(build); this.launcher=launcher; this.encoder=encoder;this.specification=specification; }
    @Override public String id() { return "ltx098_native"; }
    private static boolean multiscale(ModelBundle bundle) {return bundle.pipeline.equals(LtxPixArtSpec.PIPELINE);}
    private static JSONObject parameters(ModelBundle bundle,JSONObject values) throws Exception {return multiscale(bundle)?LtxPixArtSpec.parameters(values):Ltx098Spec.parameters(values);}
    private static JSONObject plan(ModelBundle bundle,JSONObject values) throws Exception {return multiscale(bundle)?LtxPixArtSpec.plan(values):Ltx098Spec.plan(values);}
    private static void specification(ModelBundle bundle,String type) throws Exception {if(multiscale(bundle))LtxPixArtSpec.validate(bundle,type);else Ltx098Spec.validate(bundle,type);}
    @Override public ParameterSchema schema(ModelBundle bundle) throws Exception { return new ParameterSchema(multiscale(bundle)?LtxPixArtSpec.schema():Ltx098Spec.schema()); }
    private File helper(String name) { return new File(binary.getParentFile(),name); }
    @Override public JSONObject describe() throws Exception { return DataFiles.copy(build).put("available",binary.isFile() && binary.canExecute()).put("requiredModelCapability","text_to_video").put("deviceValidated",false).put("numericalAccepted",false).put("qualityAccepted",false); }
    @Override public void validate(ModelBundle b,String type) throws Exception {
        specification.validate(b,type);
        for (File file : Arrays.asList(binary,helper(TEXT),helper(SAMPLE),helper(VAE))) if (!file.isFile() || !file.canExecute()) throw new IOException("当前 App 缺少完整旧 LTX 运行阶段");
    }
    @Override public InputSpec inputs(ModelBundle b,String type) throws Exception { specification.validate(b,type);return new InputSpec(new JSONObject(),multiscale(b)?"旧 LTX PixArt 多尺度：输入完整提示词，固定 7＋3 步；全部在本手机运行，模型由用户选择，不自动下载提示词增强模型。":"旧 LTX 单尺度 Google T5 Q5 实验配方；输入完整提示词，不使用官方 PixArt / 多尺度默认，数值和画质尚未通过验收。").withNegativePrompt(false); }
    @Override public JSONObject prepare(ModelBundle b,JSONObject request) throws Exception {
        specification.validate(b,request.getString("type")); Ltx098Spec.prompt(request.getJSONObject("input"));
        JSONObject result=DataFiles.copy(request), normalized=parameters(b,request.getJSONObject("parameters"));
        JSONArray changes=result.optJSONArray("adjustments"); if(changes==null) changes=new JSONArray();
        JSONArray added=normalized.getJSONArray("adjustments"); for(int i=0;i<added.length();i++) changes.put(added.getJSONObject(i));
        JSONObject parameters=normalized.getJSONObject("values"); return result.put("parameters",parameters).put("adjustments",changes).put("ltx098Plan",plan(b,parameters));
    }
    private static File payload(Context c,JSONObject value) throws Exception {
        c.check(); File file=c.output("json");
        try(FileOutputStream out=new FileOutputStream(file)) { out.write(value.toString().getBytes(StandardCharsets.UTF_8)); out.getFD().sync(); }
        c.check(); return file;
    }
    private static JSONObject shape(JSONObject p) throws Exception { JSONObject value=new JSONObject(); for(String key:Arrays.asList("width","height","frames","fps")) value.put(key,p.getInt(key)); return value; }
    private static void size(File file,long bytes) throws IOException { if(!file.isFile() || file.length()!=bytes) throw new IOException("旧 LTX 阶段输出尺寸不匹配"); }
    private JSONObject stage(Context c,File executable,List<String> arguments,File output,String name,NativeStages.Receipt receipt,NativeWorker.Launcher owned,JSONArray records) throws Exception {
        c.progress(name,null); long started=System.nanoTime(); JSONObject value=NativeStages.run(app,executable,c,arguments,output,name,receipt,owned);
        records.put(new JSONObject().put("stage",name).put("seconds",(System.nanoTime()-started)/1e9).put("bytes",output.length())); return value;
    }
    @Override public File generate(Context c) throws Exception {
        JSONObject request=c.request(); BundleStore.Lease lease=c.model(); validate(lease.bundle,request.getString("type"));
        String prompt=Ltx098Spec.prompt(request.getJSONObject("input")); if(!c.adapters().isEmpty()) throw new IOException("此旧 LTX 配方不接受图像 LoRA");
        boolean multi=multiscale(lease.bundle);JSONObject normalized=parameters(lease.bundle,request.getJSONObject("parameters")); if(normalized.getJSONArray("adjustments").length()!=0) throw new IOException("旧 LTX 参数快照超限，请明确重试");
        JSONObject p=normalized.getJSONObject("values");
        if(!request.has("ltx098Plan") || !DataFiles.canonical(request.getJSONObject("ltx098Plan")).equals(DataFiles.canonical(plan(lease.bundle,p)))) throw new IOException("旧 LTX 配方快照不一致，请明确重试");
        if(p.getLong("seed")==-1) p.put("seed",new java.security.SecureRandom().nextInt(Integer.MAX_VALUE));
        JSONObject details=plan(lease.bundle,p).put("effectiveParameters",p).put("stageLoading","sequential_processes").put("samplerBackend","vulkan").put("textBackend","cpu").put("vaeBackend","cpu").put("mediaBackend","android_mediacodec_avc");
        JSONArray records=new JSONArray(); details.put("stages",records); c.execution(details);
        EngineWorkspace work=new EngineWorkspace(new File(app.getFilesDir(),"engine-work"),c::check); final Process[] last={null};
        NativeWorker.Launcher owned=builder->{Process child=launcher.start(builder);last[0]=child;return child;};
        try {
            Map<String,File> models=new HashMap<>(); for(Map.Entry<String,String> item:(multi?LtxPixArtSpec.files():Ltx098Spec.files()).entrySet()) models.put(item.getKey(),work.link("models",item.getValue(),lease.file(item.getKey())));
            JSONObject sampling=DataFiles.copy(p);
            if(multi) {
                sampling.put("width",details.getInt("firstWidth")).put("height",details.getInt("firstHeight"));
                File graph=new File(models.get("upscaler").getParentFile(),"ltx098-upscaler.onnx");
                try(InputStream input=app.getAssets().open("architectures/ltx098-upscaler.onnx");OutputStream out=Files.newOutputStream(graph.toPath(),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
                    byte[] buffer=new byte[8192];int count;long total=0;while((count=input.read(buffer))!=-1){c.check();total+=count;if(total>1024*1024)throw new IOException("放大器架构图超限");out.write(buffer,0,count);}
                }
            }
            int tokens=((sampling.getInt("frames")-1)/8+1)*(sampling.getInt("height")/32)*(sampling.getInt("width")/32); long latentBytes=tokens*128L*4;
            File initial=c.output("f32"),noise=c.output("f32");
            File command=payload(c,shape(sampling).put("operation","noise").put("seed",p.getInt("seed")).put("latents",initial.getPath()).put("noise",noise.getPath()));
            stage(c,binary,Arrays.asList(command.getPath()),initial,"video_noise",v->v.optString("operation").equals("noise") && v.optBoolean("ok"),owned,records); size(initial,latentBytes);size(noise,latentBytes);c.execution(details);
            File caption=c.output("f32"); command=payload(c,new JSONObject().put("operation","encode").put("inputs",new JSONArray().put(new JSONObject().put("prompt",prompt))).put("max_tokens",256));
            List<String> textArgs=new ArrayList<>(Arrays.asList(models.get(multi?"text_index":"text_encoder").getPath(),models.get("tokenizer_config").getPath(),command.getPath(),caption.getPath(),String.valueOf(p.getInt("threads"))));
            if(multi){textArgs.add("--pixart");textArgs.add(models.get("tokenizer").getPath());}
            JSONObject text=stage(c,helper(TEXT),textArgs,caption,"video_text_encoding",v->v.optString("schema").equals("lma.ltx098-text/1"),owned,records);
            if(text.optBoolean("fixture",true) || !text.optBoolean("model_inference") || text.optInt("layers")!=24 || text.getJSONArray("items").length()!=1) throw new IOException("旧 LTX 需要完整训练 T5 编码结果");
            if(multi && !text.optString("text_variant").equals("pixart_original_f32"))throw new IOException("多尺度配方需要官方 PixArt T5 编码阶段");
            JSONObject item=text.getJSONArray("items").getJSONObject(0);int textTokens=item.getJSONArray("tokens").length();
            if(textTokens<1 || textTokens>256 || item.getLong("offset_bytes")!=0 || item.getLong("bytes")!=textTokens*4096L*4 || !item.getJSONArray("shape").toString().equals(new JSONArray().put(1).put(textTokens).put(4096).toString()) || item.getJSONArray("mask").length()!=textTokens) throw new IOException("旧 LTX T5 桥接格式不匹配");
            for(int i=0;i<textTokens;i++) if(item.getJSONArray("mask").getInt(i)!=1 || item.getJSONArray("tokens").getInt(i)<0 || item.getJSONArray("tokens").getInt(i)>32127) throw new IOException("旧 LTX T5 分词或掩码不匹配");
            size(caption,textTokens*4096L*4);details.put("textTokens",textTokens).put("promptTruncated",item.getBoolean("truncated"));c.execution(details);
            final String samplingOperation=multi?"sample_multiscale_first":"sample_files";
            File sampled=c.output("f32");command=payload(c,shape(sampling).put("operation",samplingOperation).put("latents",initial.getPath()).put("context",caption.getPath()).put("text_tokens",textTokens));
            JSONObject sample=stage(c,helper(SAMPLE),Arrays.asList(models.get("diffusion_model").getPath(),command.getPath(),sampled.getPath(),"vulkan",String.valueOf(p.getInt("threads"))),sampled,"video_sampling",v->v.optString("operation").equals(samplingOperation) && v.optBoolean("ok"),owned,records);
            samplerReceipt(sample,multi?7:8);
            size(sampled,latentBytes);c.execution(details);
            File restored=c.output("f32");command=payload(c,shape(sampling).put("operation","unpatchify").put("input",sampled.getPath()).put("output",restored.getPath()));
            stage(c,binary,Arrays.asList(command.getPath()),restored,"video_latent_layout",v->v.optString("operation").equals("unpatchify") && v.optBoolean("ok"),owned,records);size(restored,latentBytes);
            if(multi) {
                File upscaled=c.output("f32");command=payload(c,new JSONObject().put("operation","upsample").put("latent_shape",latentShape(sampling)).put("latents",restored.getPath()).put("threads",p.getInt("threads")));
                JSONObject up=stage(c,helper(VAE),Arrays.asList(models.get("vae_manifest").getParent(),command.getPath(),upscaled.getPath()),upscaled,"video_spatial_upscaling",v->v.optString("operation").equals("upsample") && v.optBoolean("ok"),owned,records);
                sampling.put("width",details.getInt("secondWidth")).put("height",details.getInt("secondHeight"));
                if(!up.getJSONArray("output_shape").toString().equals(latentShape(sampling).toString()) || up.getInt("graph_runs")!=1 || up.getInt("session_loads")!=1 || up.getInt("session_unloads")!=1 || up.getInt("max_live_sessions")!=1 || !up.getBoolean("adain") || up.optBoolean("fixture",true) || !up.optString("backend").equals("cpu") || !up.optString("normalization").equals("vae_per_channel"))throw new IOException("空间放大或 AdaIN 阶段未完整执行");
                latentBytes=((sampling.getInt("frames")-1)/8+1)*(long)(sampling.getInt("height")/32)*(sampling.getInt("width")/32)*128*4;size(upscaled,latentBytes);
                initial=c.output("f32");noise=c.output("f32");command=payload(c,shape(sampling).put("operation","refine_noise").put("seed",p.getInt("seed")).put("input",upscaled.getPath()).put("latents",initial.getPath()).put("noise",noise.getPath()));
                stage(c,binary,Arrays.asList(command.getPath()),initial,"video_refinement_noise",v->v.optString("operation").equals("refine_noise") && v.optBoolean("ok"),owned,records);size(initial,latentBytes);size(noise,latentBytes);
                sampled=c.output("f32");command=payload(c,shape(sampling).put("operation","sample_multiscale_second").put("latents",initial.getPath()).put("context",caption.getPath()).put("text_tokens",textTokens));
                JSONObject refined=stage(c,helper(SAMPLE),Arrays.asList(models.get("diffusion_model").getPath(),command.getPath(),sampled.getPath(),"vulkan",String.valueOf(p.getInt("threads"))),sampled,"video_refinement_sampling",v->v.optString("operation").equals("sample_multiscale_second") && v.optBoolean("ok"),owned,records);samplerReceipt(refined,3);size(sampled,latentBytes);
                restored=c.output("f32");command=payload(c,shape(sampling).put("operation","unpatchify").put("input",sampled.getPath()).put("output",restored.getPath()));
                stage(c,binary,Arrays.asList(command.getPath()),restored,"video_refined_latent_layout",v->v.optString("operation").equals("unpatchify") && v.optBoolean("ok"),owned,records);size(restored,latentBytes);c.execution(details);
            }
            File decoded=c.output("f32");JSONArray latentShape=latentShape(sampling);
            command=payload(c,new JSONObject().put("operation","decode").put("latent_shape",latentShape).put("latents",restored.getPath()).put("noise",noise.getPath()).put("timestep",.05).put("noise_scale",.025).put("threads",p.getInt("threads")));
            JSONObject vae=stage(c,helper(VAE),Arrays.asList(models.get("vae_manifest").getParent(),command.getPath(),decoded.getPath()),decoded,"video_decoding",v->v.has("graph_runs") && v.optBoolean("ok"),owned,records);
            JSONArray decodedShape=new JSONArray().put(1).put(3).put(p.getInt("frames")).put(sampling.getInt("height")).put(sampling.getInt("width"));
            if(!vae.getJSONArray("output_shape").toString().equals(decodedShape.toString()) || vae.getInt("graph_runs")!=9 || vae.getInt("session_loads")!=9 || vae.getInt("session_unloads")!=9 || vae.getInt("max_live_sessions")!=1) throw new IOException("旧 LTX VAE 阶段或会话释放不完整");
            long rgbBytes=p.getInt("frames")*(long)p.getInt("width")*p.getInt("height")*3;size(decoded,p.getInt("frames")*(long)sampling.getInt("width")*sampling.getInt("height")*3*4);c.execution(details);
            File frames=c.output("rgb");command=payload(c,shape(p).put("operation","frames").put("input",decoded.getPath()).put("output",frames.getPath()));
            if(multi)command=payload(c,shape(p).put("operation","frames").put("input",decoded.getPath()).put("output",frames.getPath()).put("input_width",sampling.getInt("width")).put("input_height",sampling.getInt("height")));
            stage(c,binary,Arrays.asList(command.getPath()),frames,"video_frames",v->v.optString("operation").equals("frames") && v.optBoolean("ok"),owned,records);size(frames,28+rgbBytes);c.execution(details);
            c.progress("encoding",null);File video=c.output("mp4");encoder.encode(frames,video,()->{try{c.check();}catch(Exception failure){throw new IOException(failure);}});c.check();
            details.put("completeGeneratedFrames",true).put("encodedVideoBytes",video.length());c.execution(details);return video;
        } finally { work.closeAfter(last[0]); }
    }
    private static JSONArray latentShape(JSONObject p) throws Exception {return new JSONArray().put(1).put(128).put((p.getInt("frames")-1)/8+1).put(p.getInt("height")/32).put(p.getInt("width")/32);}
    private static void samplerReceipt(JSONObject sample,int steps) throws Exception {
        if(!sample.optBoolean("model_executed") || sample.optBoolean("fixture",true) || !sample.optString("backend").equals("vulkan") || sample.optInt("layers")!=28 || sample.optInt("steps")!=steps || sample.optLong("parameters")!=1923385472L)throw new IOException("旧 LTX 采样阶段未完整执行");
    }
}
