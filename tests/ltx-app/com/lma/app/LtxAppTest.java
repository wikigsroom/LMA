package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.CopyOnWriteArrayList;

/** Production engine AND queue; Android framework/media ports and neural fixtures are explicit. */
public final class LtxAppTest {
    private static int checks; private static String mode="succeeded";
    private static final List<Process> children=new CopyOnWriteArrayList<>(); private static final List<List<String>> commands=new CopyOnWriteArrayList<>();
    interface Action {void run()throws Exception;}
    interface Ready {boolean get()throws Exception;}
    static void verify(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static void rejects(Action action,String message)throws Exception{try{action.run();}catch(Exception expected){checks++;return;}throw new AssertionError(message);}
    static JSONObject read(File file)throws Exception{return new JSONObject(new String(Files.readAllBytes(file.toPath()),StandardCharsets.UTF_8));}
    static void write(File file,JSONObject value)throws Exception{Files.write(file.toPath(),(value.toString(2)+"\n").getBytes(StandardCharsets.UTF_8));}
    static void until(Ready ready,int seconds)throws Exception{long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(seconds);while(!ready.get()){if(System.nanoTime()>end)throw new IOException("LTX test boundary timed out");Thread.sleep(20);}}
    static JSONObject select(JSONArray values,String id)throws Exception{for(int i=0;i<values.length();i++)if(values.getJSONObject(i).getString("id").equals(id))return values.getJSONObject(i);throw new IOException("Missing catalogue ID");}
    static void floats(File file,int count,int variant)throws Exception{
        ByteBuffer bytes=ByteBuffer.allocate(count*4).order(ByteOrder.LITTLE_ENDIAN);
        for(int i=0;i<count;i++)bytes.putFloat((float)Math.sin(i*.03+variant*.15)*.7f);Files.write(file.toPath(),bytes.array());
    }
    static void child(String[] args)throws Exception{
        String stage=args[1],selected=args[2];String[] original=Arrays.copyOfRange(args,3,args.length);
        if(selected.equals("cancelled")||selected.equals("interrupted")){System.out.println(new JSONObject().put("stage","waiting_fixture").put("done",1).put("total",2));System.out.flush();Thread.sleep(30000);return;}
        JSONObject payload=read(new File(original[stage.equals("text")?3:2]));File output=new File(original[stage.equals("text")?4:3]);JSONObject receipt=new JSONObject();
        if(stage.equals("text")){
            floats(output,4096,1);receipt.put("schema","lma.ltx098-text/1").put("fixture",false).put("model_inference",true).put("layers",24)
                .put("items",new JSONArray().put(new JSONObject().put("tokens",new JSONArray().put(1)).put("mask",new JSONArray().put(1)).put("offset_bytes",0).put("bytes",16384).put("shape",new JSONArray().put(1).put(1).put(selected.equals("bad_text")?32:4096)).put("truncated",false)));
        }else if(stage.equals("sample")){
            int count=((payload.getInt("frames")-1)/8+1)*(payload.getInt("height")/32)*(payload.getInt("width")/32)*128;
            floats(output,count,2);receipt.put("ok",true).put("operation","sample_files").put("model_executed",!selected.equals("bad_sample")).put("fixture",false).put("backend","vulkan").put("layers",28).put("steps",8).put("parameters",1923385472L);
        }else{
            JSONArray shape=payload.getJSONArray("latent_shape");int frames=(shape.getInt(2)-1)*8+1,height=shape.getInt(3)*32,width=shape.getInt(4)*32;
            floats(output,frames*height*width*3,3);receipt.put("ok",true).put("output_shape",new JSONArray().put(1).put(3).put(frames).put(height).put(width)).put("graph_runs",selected.equals("bad_vae")?8:9).put("session_loads",9).put("session_unloads",9).put("max_live_sessions",1);
        }
        if(!selected.equals("missing_receipt")){System.out.println(receipt);if(selected.equals("duplicate_receipt"))System.out.println(receipt);}
    }
    static JSONObject inspect(File video,String ffprobe)throws Exception{
        Process process=new ProcessBuilder(ffprobe,"-v","error","-count_frames","-select_streams","v:0","-show_entries","stream=codec_name,width,height,nb_read_frames,avg_frame_rate","-of","json",video.getPath()).redirectErrorStream(true).start();
        try{ByteArrayOutputStream bytes=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int n;try(InputStream in=process.getInputStream()){while((n=in.read(buffer))>=0){if(bytes.size()>65536)throw new IOException("Probe response too long");bytes.write(buffer,0,n);}}
            if(!process.waitFor(30,TimeUnit.SECONDS)||process.exitValue()!=0)throw new IOException("Host probe failed");JSONObject stream=new JSONObject(new String(bytes.toByteArray(),StandardCharsets.UTF_8)).getJSONArray("streams").getJSONObject(0);
            if(!stream.getString("codec_name").equals("h264") || stream.getInt("nb_read_frames")<9)throw new IOException("Not a complete AVC fixture/host result");
            return new JSONObject().put("mime","video/mp4").put("width",stream.getInt("width")).put("height",stream.getInt("height")).put("frameCount",stream.getInt("nb_read_frames")).put("hostFfprobe",true);
        }finally{ProcessControl.stop(process);}
    }
    static void encode(File frames,File output,DataFiles.Check check,String ffmpeg,File capture,JSONObject bridge)throws Exception{
        check.run();if(mode.equals("bad_encoder"))throw new IOException("Explicit failing host encoder port");
        byte[] file=Files.readAllBytes(frames.toPath());ByteBuffer header=ByteBuffer.wrap(file).order(ByteOrder.LITTLE_ENDIAN);
        byte[] magic=new byte[8];header.get(magic);verify(Arrays.equals(magic,new byte[]{'L','M','A','F','R','M','1',0}),"Production tensor stage writes the shared frame format");
        int width=header.getInt(),height=header.getInt(),count=header.getInt(),fps=header.getInt(),channels=header.getInt();
        verify(channels==3 && file.length==28L+width*(long)height*count*3,"Actual frame extent matches its complete header");
        boolean moving=false;int stride=width*height*3;for(int i=28+stride;i<file.length;i++)if(file[i]!=file[28+(i-28)%stride]){moving=true;break;}
        verify(moving,"Actual generated/fixture frames vary over time");
        for(List<String> command:commands){String name=new File(command.get(0)).getName();JSONObject p=read(new File(command.get(name.contains("text")?3:name.contains("sample")||name.contains("vae")?2:1)));
            Map<String,String> files=new LinkedHashMap<>();
            if(p.optString("operation").equals("noise")){files.put("initial-tokens.f32",p.getString("latents"));files.put("decode-noise.f32",p.getString("noise"));}
            else if(name.contains("text"))files.put("caption.f32",command.get(4));
            else if(name.contains("sample"))files.put("denoised-tokens.f32",command.get(3));
            else if(name.contains("vae"))files.put("decoded-ncthw.f32",command.get(3));
            else if(p.optString("operation").equals("unpatchify"))files.put("denoised-ncthw.f32",p.getString("output"));
            else if(p.optString("operation").equals("frames"))files.put("frames.lma",p.getString("output"));
            for(Map.Entry<String,String> entry:files.entrySet()){File value=new File(entry.getValue());bridge.put(entry.getKey(),new JSONObject().put("bytes",value.length()).put("sha256",DataFiles.sha256(value)));}
        }
        if(capture!=null)Files.copy(frames.toPath(),new File(capture,"frames.lma").toPath());
        Process process=new ProcessBuilder(ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-n","-f","rawvideo","-pixel_format","rgb24","-video_size",width+"x"+height,"-framerate",String.valueOf(fps),"-i","pipe:0","-an","-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",output.getPath()).redirectError(ProcessBuilder.Redirect.INHERIT).start();
        try{try(OutputStream in=process.getOutputStream()){in.write(file,28,file.length-28);}if(!process.waitFor(60,TimeUnit.SECONDS)||process.exitValue()!=0)throw new IOException("Explicit host AVC port failed");check.run();}
        finally{ProcessControl.stop(process);}
    }
    public static void main(String[] args)throws Exception{
        if(args.length>0&&args[0].equals("--child")){child(args);return;}
        File repository=new File(args[0]),root=new File(args[1]),libraries=new File(args[2]);boolean trained=Boolean.parseBoolean(args[3]);JSONObject selectedAssets=read(new File(args[4]));String ffmpeg=args[5],ffprobe=args[6];root.mkdirs();
        JSONArray catalogue=read(new File(repository,"catalogue/model-bundles.json")).getJSONArray("bundles");JSONObject current=select(catalogue,"ltx098_runtime_google_q5_v2"),old=select(catalogue,"ltx098_runtime_google_q5_v1");ModelBundle production=new ModelBundle(current);
        Ltx098Spec.validate(production,"video.generate");checks++;
        rejects(()->Ltx098Spec.validate(new ModelBundle(old),"video.generate"),"Historical runtime-only record cannot silently change into a generation model");
        rejects(()->Ltx098Spec.validate(production,"image.generate"),"Image generation cannot use a video recipe");
        for(String prompt:Arrays.asList(""," ","bad\0text"))rejects(()->Ltx098Spec.prompt(new JSONObject().put("prompt",prompt)),"Invalid prompt rejected before native work");
        rejects(()->Ltx098Spec.prompt(new JSONObject().put("prompt","valid").put("reference","remote")),"Only the supported full-text input is accepted");
        JSONObject clamped=Ltx098Spec.parameters(new JSONObject().put("width",999).put("height",1).put("frames",999).put("steps",999).put("threads",999).put("fps",999)).getJSONObject("values");
        verify(clamped.getInt("width")==256&&clamped.getInt("height")==64&&clamped.getInt("frames")==33&&clamped.getInt("steps")==8&&clamped.getInt("threads")==8&&clamped.getInt("fps")==60,"All editable parameters clamp to this exact model profile");
        verify(Ltx098Spec.parameters(new JSONObject().put("width",95).put("frames",24)).getJSONObject("values").getInt("frames")==17,"Frame alignment follows 8n+1");
        LmaApp app=new LmaApp(new File(root,"files"),new File(repository,"app/src/main/assets"),libraries);app.artifacts=new ArtifactStore(new File(root,"artifacts"),f->inspect(f,ffprobe));app.artifacts.references(app.jobs::referencesArtifact);
        app.bundles.declare(new ModelBundle(old));app.bundles.saveSettings(old.getString("id"),new JSONObject());
        for(int i=0;i<catalogue.length();i++)app.bundles.declare(new ModelBundle(catalogue.getJSONObject(i)));
        verify(DataFiles.canonical(app.bundles.bundle(old.getString("id")).json()).equals(DataFiles.canonical(old)),"Upgrading the catalogue preserves the immutable historical record");
        JSONObject chosen=DataFiles.copy(current);Map<String,File> assets=new LinkedHashMap<>();
        if(!trained){chosen.put("id","ltx_explicit_synthetic_fixture");JSONArray components=chosen.getJSONArray("components");File fixture=new File(root,"NOT_MODEL.bin");Files.write(fixture.toPath(),new byte[]{1,2,3,4});for(int i=0;i<components.length();i++){JSONObject component=components.getJSONObject(i);for(String key:Arrays.asList("url","repository","revision","derivedFrom"))component.remove(key);component.put("bytes",4).put("sha256",DataFiles.sha256(fixture));assets.put(component.getString("role"),fixture);}}
        else for(String role:Ltx098Spec.files().keySet())assets.put(role,new File(selectedAssets.getString(role)));
        ModelBundle model=new ModelBundle(chosen);app.bundles.adoptLocal(model,assets,new JSONObject(),()->{});verify(app.bundles.plan(model.id).getBoolean("installed"),"Only explicitly selected complete local components are adopted");
        JSONObject p=new JSONObject().put("width",trained?256:64).put("height",trained?256:64).put("frames",trained?33:9).put("fps",24).put("seed",42).put("threads",4);app.bundles.saveSettings(model.id,p);
        JSONArray runs=new JSONArray();List<String> modes=trained?Arrays.asList("succeeded"):Arrays.asList("succeeded","bad_text","bad_sample","bad_vae","missing_receipt","duplicate_receipt","bad_encoder","cancelled","interrupted");
        for(String selected:modes){mode=selected;children.clear();commands.clear();JSONObject bridges=new JSONObject();File capture=trained?new File(root,"captured"):null;if(capture!=null)capture.mkdirs();
            NativeWorker.Launcher launcher=builder->{List<String> command=new ArrayList<>(builder.command());String name=new File(command.get(0)).getName();
                if(!trained&&!name.contains("tensors")){String stage=name.contains("text")?"text":name.contains("sample")?"sample":"vae";List<String> child=new ArrayList<>(Arrays.asList(new File(System.getProperty("java.home"),"bin/java.exe").getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-Dstderr.encoding=UTF-8","-cp",System.getProperty("java.class.path"),LtxAppTest.class.getName(),"--child",stage,mode));child.addAll(command);builder.command(child);}
                Process child=builder.start();for(Process previous:children)verify(!previous.isAlive(),"Only one native stage is live at a time");children.add(child);commands.add(command);return child;};
            Ltx098Engine engine=new Ltx098Engine(app,new File(libraries,"liblma-ltx098-app-tensors.so"),new JSONObject().put("engine","ltx098_native"),launcher,(frames,video,check)->encode(frames,video,check,ffmpeg,capture,bridges));app.localEngines.fixture(engine);
            LmaService service=new LmaService();EngineHost resident=new EngineHost(service,app);service.engine=resident;LocalJobs queue=new LocalJobs(app,resident,()->{});app.jobHost=queue;
            try{
                JSONObject request=new JSONObject().put("type","video.generate").put("bundleId",model.id).put("input",new JSONObject().put("prompt",trained?selectedAssets.getString("prompt"):"Explicit synthetic protocol fixture")).put("parameters",new JSONObject()).put("allowUnmeasured",true);
                verify(LocalJobs.preflight(app,request).getBoolean("canEnqueue"),"The production preflight accepts complete explicit assets and exact parameters");verify(children.isEmpty(),"Preflight launches no stage or transfer");
                JSONObject job=queue.submit(request,"ltx_"+selected);String id=job.getString("id");
                if(selected.equals("cancelled")||selected.equals("interrupted")){until(()->children.size()>=2&&children.get(1).isAlive(),30);if(selected.equals("cancelled"))queue.cancel(id);else queue.close();}
                String[] previousStage={""};until(()->{JSONObject state=app.jobs.get(id);String stage=state.optString("stage");if(!stage.equals(previousStage[0])){System.err.println("Observed production queue stage: "+stage);previousStage[0]=stage;}return Arrays.asList("succeeded","failed","cancelled","interrupted").contains(state.getString("state"));},trained?7200:90);
                until(()->{for(Process child:children)if(child.isAlive())return false;return app.nativeProcess==null;},15);
                JSONObject result=app.jobs.get(id);String expected=selected.equals("succeeded")?selected:selected.equals("cancelled")||selected.equals("interrupted")?selected:"failed";
                verify(result.getString("state").equals(expected),"Actual queue reaches the expected terminal state: "+selected+" / "+result.optString("error"));
                verify(app.nativeProcess==null,"Actual stage ownership is released after "+selected);
                until(()->!select(app.bundles.snapshot(),model.id).getBoolean("inUse"),15);verify(!select(app.bundles.snapshot(),model.id).getBoolean("inUse"),"Actual model leases are released after terminal cleanup");
                JSONObject run=new JSONObject().put("case",selected).put("job",result).put("actualChildren",children.size()).put("bridgeFiles",bridges);
                if(expected.equals("succeeded")){verify(children.size()==6,"One real task uses exactly six sequential native stages");String artifact=result.getJSONArray("artifacts").getString(0);JSONObject record=app.artifacts.get(artifact);File video=app.artifacts.file(artifact);verify(record.getJSONObject("metadata").getString("mime").equals("video/mp4"),"The production artifact store publishes the complete AVC result");verify(record.getJSONObject("provenance").getJSONObject("request").getJSONObject("ltx098Plan").getString("profile").equals(Ltx098Spec.PROFILE),"Artifact provenance retains the immutable exact profile");run.put("artifact",record).put("videoSha256",DataFiles.sha256(video)).put("videoBytes",video.length());if(capture!=null)Files.copy(video.toPath(),new File(capture,"video.mp4").toPath());}
                else verify(result.getJSONArray("artifacts").length()==0,"Failed/cancelled/interrupted stages never publish partial video");
                until(()->new File(app.getFilesDir(),"engine-work").list().length==0,15);verify(new File(app.getFilesDir(),"engine-work").list().length==0,"Filename-preserving model workspace is cleaned after "+selected);runs.put(run);
            }finally{queue.close();resident.close();for(Process child:children)ProcessControl.stop(child);}
        }
        JSONObject report=new JSONObject().put("assertions",checks).put("runs",runs).put("productionEngineAndQueue",true).put("hostFrameworkPort",true).put("hostMediaPort","ffmpeg_libx264_not_android").put("modelInference",trained).put("syntheticNeuralStages",!trained).put("physicalAndroid",false).put("numericalAccepted",false).put("qualityAccepted",false);
        write(new File(root,"results.json"),report);System.out.println(new JSONObject().put("assertions",checks).put("runs",runs.length()).put("trained",trained));
    }
}
