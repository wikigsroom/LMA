package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Production protocol, transient storage and authenticated sockets; audio is a labelled PCM fixture. */
public final class AudioStreamingTest {
    private static int passed;
    private interface Op { void run() throws Exception; }
    private static void check(boolean value, String label) { if (!value) throw new AssertionError(label); passed++; }
    private static void reject(Op op, String label) throws Exception { try { op.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError(label); }
    private static JSONObject format() { return new JSONObject().put("schema", AudioPcm.SCHEMA).put("format", "pcm_s16le").put("sampleRate", 24000).put("channels", 1).put("maxFrames", 48000).put("maxChunkFrames", 1920); }
    private static byte[] pcm(int frames, int offset) { byte[] b = new byte[frames * 2]; for (int i = 0; i < frames; i++) { short v = (short) ((i + offset) % 512 - 256); b[i*2] = (byte) v; b[i*2+1] = (byte) (v >> 8); } return b; }
    private static JSONObject chunk(int sequence, int start, int frames) { return new JSONObject().put("event", "audio_chunk").put("schema", AudioPcm.SCHEMA).put("sequence", sequence).put("startFrame", start).put("frames", frames).put("sampleRate", 24000).put("channels", 1).put("pcm", Base64.getEncoder().encodeToString(pcm(frames, start))); }
    private static JSONObject end(int chunks, int frames) { return new JSONObject().put("event", "audio_end").put("schema", AudioPcm.SCHEMA).put("nextSequence", chunks).put("frames", frames); }
    private static byte[] wave(byte[] pcm) throws Exception { ByteArrayOutputStream b = new ByteArrayOutputStream(); DataOutputStream out = new DataOutputStream(b); out.writeBytes("RIFF"); out.writeInt(Integer.reverseBytes(36 + pcm.length)); out.writeBytes("WAVEfmt "); out.writeInt(Integer.reverseBytes(16)); out.writeShort(Short.reverseBytes((short)1)); out.writeShort(Short.reverseBytes((short)1)); out.writeInt(Integer.reverseBytes(24000)); out.writeInt(Integer.reverseBytes(48000)); out.writeShort(Short.reverseBytes((short)2)); out.writeShort(Short.reverseBytes((short)16)); out.writeBytes("data"); out.writeInt(Integer.reverseBytes(pcm.length)); out.write(pcm); return b.toByteArray(); }
    private static void emit(JSONObject e) { System.out.println(e); System.out.flush(); }
    private static void child(String path) throws Exception {
        JSONObject command = new JSONObject(new String(Files.readAllBytes(Paths.get(path)), "UTF-8")); String mode = command.getString("fixtureMode"); Path output = Paths.get(command.getString("output"));
        JSONObject first = chunk(0, 0, 512);
        if (mode.equals("gap")) first.put("sequence", 1);
        if (mode.equals("rate")) first.put("sampleRate", 48000);
        emit(first);
        Path heard = Paths.get(output + ".heard"); long deadline = System.nanoTime() + 5_000_000_000L;
        while (!Files.exists(heard) && System.nanoTime() < deadline) Thread.sleep(10);
        if (!Files.exists(heard)) throw new IOException("No consumer received the first block before output");
        if (mode.equals("cancel")) Thread.sleep(60000);
        emit(chunk(1, 512, 256));
        byte[] samples = pcm(768, 0); if (mode.equals("mismatch")) samples[0] ^= 1;
        Files.write(output, wave(samples));
        if (!mode.equals("missing_end")) emit(end(2, 768));
        if (mode.equals("duplicate_end")) emit(end(2, 768));
        if (mode.equals("late_chunk")) emit(chunk(2, 768, 1));
        emit(new JSONObject().put("event", "complete").put("output", output.toString()));
    }
    private static final class Reply { int status; byte[] bytes; Reply(int s, byte[] b) { status=s; bytes=b; } JSONObject json() { return new JSONObject(new String(bytes, java.nio.charset.StandardCharsets.UTF_8)); } }
    private static Reply get(int port, String method, String path, String key) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL("http://127.0.0.1:"+port+path).openConnection(); c.setRequestMethod(method); c.setConnectTimeout(2000); c.setReadTimeout(3000); if (key != null) c.setRequestProperty("Authorization", "Bearer " + key); if(method.equals("POST")){c.setDoOutput(true);c.setFixedLengthStreamingMode(0);c.getOutputStream().close();}
        try { int code=c.getResponseCode(); ByteArrayOutputStream out=new ByteArrayOutputStream(); try(InputStream in=code>=400?c.getErrorStream():c.getInputStream()){ if(in!=null){byte[] b=new byte[4096];int n;while((n=in.read(b))!=-1)out.write(b,0,n);} } return new Reply(code,out.toByteArray()); } finally { c.disconnect(); }
    }
    public static void main(String[] args) throws Exception {
        if(args[0].equals("child")){child(args[1]);return;}
        File root=new File(args[0]);root.mkdirs();AudioPcm.Format format=new AudioPcm.Format(format());
        for(JSONObject bad:Arrays.asList(format().put("channels",3),format().put("sampleRate",24000.5),format().put("sampleRate","24000"),format().put("maxFrames",48000000),format().put("maxChunkFrames",4801),format().put("schema","other")))reject(()->new AudioPcm.Format(bad),"invalid stream format rejected");
        for(JSONObject bad:Arrays.asList(chunk(1,0,1),chunk(0,1,1),chunk(0,0,1).put("channels",2),chunk(0,0,1).put("sampleRate",48000),chunk(0,0,1).put("frames",1.5),chunk(0,0,1921),chunk(0,0,1).put("pcm","!!!!"),chunk(0,0,1).put("pcm","AA=="),chunk(0,0,1).put("schema","other")))reject(()->new AudioPcm.Sequence(format).chunk(bad),"invalid chunk rejected");
        AudioPcm.Sequence sequence=new AudioPcm.Sequence(format);sequence.chunk(chunk(0,0,512));sequence.chunk(chunk(1,512,256));reject(()->sequence.end(end(1,768)),"wrong final chunk count rejected");reject(()->sequence.end(end(2,769)),"wrong final frame count rejected");
        File wav=new File(root,"fixture.wav");Files.write(wav.toPath(),wave(pcm(768,0)));reject(()->sequence.verify(wav),"missing end rejected");sequence.end(end(2,768));reject(()->sequence.end(end(2,768)),"duplicate end rejected");reject(()->sequence.chunk(chunk(2,768,1)),"late chunk rejected");sequence.verify(wav);check(true,"stream and final WAV use identical samples");
        AudioPcm.Sequence limited=new AudioPcm.Sequence(new AudioPcm.Format(format().put("maxFrames",512)));limited.chunk(chunk(0,0,512));reject(()->limited.chunk(chunk(1,512,1)),"total frame bound enforced");
        AudioPcm.Sequence capped=new AudioPcm.Sequence(format);for(int i=0;i<4096;i++)capped.chunk(chunk(i,i,1));reject(()->capped.chunk(chunk(4096,4096,1)),"chunk metadata is bounded");
        AudioStreams previews=new AudioStreams(new File(root,"previews"));previews.begin("first",format);AudioPcm.Sequence ordered=new AudioPcm.Sequence(format);AudioPcm.Chunk one=ordered.chunk(chunk(0,0,512));previews.append("first",one);
        check(Arrays.equals(previews.read("first",0),pcm(512,0)),"private PCM read is exact");check(!previews.snapshot().toString().contains("pcm\""),"PCM is absent from snapshots");reject(()->previews.append("first",one),"duplicate append rejected");reject(()->previews.begin("other",format),"two active previews rejected");reject(()->previews.get("first",2),"future cursor rejected");reject(()->previews.read("../first",0),"path traversal rejected");reject(()->previews.remove("first"),"active preview cannot be deleted");reject(()->previews.finish("first","succeeded",""),"partial audio cannot become a successful result");previews.finish("first","cancelled","");check(previews.get("first",1).getJSONArray("chunks").length()==0 && previews.get("first",0).getString("artifactId").isEmpty(),"cancelled preview remains partial");
        for(int i=0;i<4;i++){String id="retained_"+i;previews.begin(id,format);previews.finish(id,"failed","");}check(previews.snapshot().length()==4,"retention is bounded");reject(()->previews.read("first",0),"oldest preview is evicted");
        AudioStreams restarted=new AudioStreams(new File(root,"previews"));check(restarted.snapshot().length()==0 && new File(root,"previews").list().length==0 && wav.isFile(),"restart removes only transient previews");
        JobStore jobs=new JobStore(new File(root,"jobs"));ArtifactStore artifacts=new ArtifactStore(new File(root,"artifacts"),WaveFile::inspect);final String key="lma_audio_test_key";
        LocalApi.Runtime runtime=new LocalApi.Runtime(){public String apiKey(){return key;}public JSONObject health(){return new JSONObject();}public JSONArray models(){return new JSONArray();}public JSONArray engines(){return new JSONArray();}public JobStore jobs(){return jobs;}public ArtifactStore artifacts(){return artifacts;}public AudioStreams audioStreams(){return restarted;}public JSONObject submit(JSONObject r,String k)throws Exception{return jobs.submit(r,k);}public void cancel(String id)throws Exception{jobs.cancel(id);}public LocalHttp.Response text(String p,JSONObject r){return LocalApi.json(200,new JSONObject());}};
        AtomicInteger children=new AtomicInteger(),early=new AtomicInteger();LmaApp app=new LmaApp(new File(root,"worker"));File java=new File(System.getProperty("java.home"),"bin/java.exe");
        try(LocalHttp server=new LocalHttp("127.0.0.1",0,new LocalApi(runtime))){
            for(String mode:Arrays.asList("valid","gap","rate","missing_end","duplicate_end","late_chunk","mismatch","cancel")){
                JSONObject task=jobs.submit(new JSONObject().put("bundleId","fixture_audio").put("type","speech.synthesize").put("input",new JSONObject().put("prompt",mode)).put("parameters",new JSONObject()),"");String id=task.getString("id");File output=new File(root,id+".wav");final boolean[] cancelled={false};
                JSONObject command=new JSONObject().put("fixtureMode",mode).put("output",output.getPath()).put("audioStream",format());
                LocalEngine.Context context=new LocalEngine.Context(){public BundleStore.Lease model(){return null;}public JSONObject request(){return command;}public File output(String ext){return new File(root,id+"-input."+ext);}public void check()throws Exception{if(cancelled[0])throw new IOException("fixture cancellation");}public void progress(String s,Double f){}public void process(Process p){}public void execution(JSONObject d){}public boolean audioStreaming(){return true;}public void audioStart(AudioPcm.Format f)throws Exception{restarted.begin(id,f);}public void audioChunk(AudioPcm.Chunk c)throws Exception{
                    restarted.append(id,c);if(c.sequence==0){AudioStreamingTest.check(!output.exists() && app.nativeProcess.isAlive(),"first PCM arrives while owned child is still generating");Reply live=get(server.port(),"GET","/v1/jobs/"+id+"/audio?after=0",key);AudioStreamingTest.check(live.status==200 && live.json().getInt("nextSequence")==1 && live.json().getString("state").equals("streaming"),"authenticated API observes incremental progress before WAV exists");AudioStreamingTest.check(Arrays.equals(get(server.port(),"GET","/v1/jobs/"+id+"/audio/0",key).bytes,c.pcm),"API audio chunk has exact bytes");early.incrementAndGet();Files.write(Paths.get(output+".heard"),new byte[]{1});if(mode.equals("cancel")){cancelled[0]=true;app.nativeProcess.destroyForcibly();}}}};
                Op run=()->NativeWorker.run(app,java,context,command,output,Collections.emptyMap(),builder->{children.incrementAndGet();return new ProcessBuilder(java.getPath(),"-Dfile.encoding=UTF-8","-Dstdout.encoding=UTF-8","-cp",System.getProperty("java.class.path"),AudioStreamingTest.class.getName(),"child",builder.command().get(1)).redirectErrorStream(true).start();});
                if(mode.equals("valid")){run.run();restarted.finish(id,"succeeded","fixture_full_result");check(WaveFile.inspect(output).getLong("samples")==768,"verified full WAV is preserved");check(get(server.port(),"GET","/v1/jobs/"+id+"/audio",null).status==401,"PCM metadata requires authentication");check(get(server.port(),"GET","/v1/jobs/"+id+"/audio/0","wrong").status==401,"PCM bytes require authentication");check(get(server.port(),"HEAD","/v1/jobs/"+id+"/audio/0",key).bytes.length==0,"HEAD has no PCM body");check(get(server.port(),"POST","/v1/jobs/"+id+"/audio/0",key).status==405,"preview routes are read-only");check(get(server.port(),"GET","/v1/jobs/"+id+"/audio?after=-1",key).status==400,"invalid API cursor rejected");}
                else{reject(run,"malformed / truncated / mismatched / cancelled worker rejected");restarted.finish(id,mode.equals("cancel")?"cancelled":"failed","");check(restarted.get(id,0).getString("artifactId").isEmpty(),"partial preview is never a completed artifact");}
                check(app.nativeProcess==null && !context.output("json").exists(),"worker and private request released");
            }
        }
        check(children.get()==8 && early.get()==6,"actual host children exercise incremental transport");
        System.out.println(new JSONObject().put("passed",passed).put("actual_host_children",children.get()).put("before_final_wav_observations",early.get()).put("actual_authenticated_socket_io",true).put("production_native_worker",true).put("audio_is_synthetic_protocol_fixture",true).put("model_inference",false).put("physical_android",false));
    }
}
