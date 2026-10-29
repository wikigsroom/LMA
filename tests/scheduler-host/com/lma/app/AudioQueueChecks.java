package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Actual production LocalJobs lifecycle with a labelled synthetic PCM provider. */
final class AudioQueueChecks {
    private static int passed;
    private static void verify(boolean value,String message){if(!value)throw new AssertionError(message);passed++;}
    private interface Ready{boolean get()throws Exception;}
    private static void until(Ready ready)throws Exception{long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(10);while(!ready.get()){if(System.nanoTime()>deadline)throw new AssertionError("Audio queue did not reach its expected boundary");Thread.sleep(10);}}
    private static byte[] wav()throws Exception{ByteArrayOutputStream bytes=new ByteArrayOutputStream();DataOutputStream out=new DataOutputStream(bytes);out.writeBytes("RIFF");out.writeInt(Integer.reverseBytes(52));out.writeBytes("WAVEfmt ");out.writeInt(Integer.reverseBytes(16));out.writeShort(Short.reverseBytes((short)1));out.writeShort(Short.reverseBytes((short)1));out.writeInt(Integer.reverseBytes(24000));out.writeInt(Integer.reverseBytes(48000));out.writeShort(Short.reverseBytes((short)2));out.writeShort(Short.reverseBytes((short)16));out.writeBytes("data");out.writeInt(Integer.reverseBytes(16));out.write(new byte[16]);return bytes.toByteArray();}
    static int run(Path repository,Path root)throws Exception{
        LmaApp app=new LmaApp(root.toFile(),repository.resolve("app/src/main/assets").toFile(),root.resolve("libraries").toFile());
        app.artifacts=new ArtifactStore(new File(app.getFilesDir(),"audio-results"),WaveFile::inspect);app.artifacts.references(app.jobs::referencesArtifact);
        Path data=root.resolve("provider-fixture.bin");Files.write(data,new byte[]{1,2,3});
        ModelBundle bundle=new ModelBundle(new JSONObject().put("schema",ModelBundle.SCHEMA).put("id","audio_queue_fixture").put("modelId","audio_queue_fixture").put("name","NOT A MODEL: synthetic audio provider").put("recipeId","fixture_audio_v1").put("engine","fixture_audio").put("backend","cpu").put("architecture","fixture").put("pipeline","fixture").put("tasks",new JSONArray().put("audio")).put("capabilities",new JSONArray().put("text_to_speech")).put("parameters",new JSONObject().put("version",1).put("fields",new JSONObject())).put("components",new JSONArray().put(new JSONObject().put("role","fixture").put("path","fixture.bin").put("format","fixture_data").put("bytes",3).put("sha256",DataFiles.sha256(data.toFile())))));
        app.bundles.adoptLocal(bundle,Collections.singletonMap("fixture",data.toFile()),new JSONObject(),()->{});
        final CountDownLatch[] release={new CountDownLatch(1)};
        app.localEngines.fixture(new LocalEngine(){public String id(){return "fixture_audio";}public JSONObject describe(){return new JSONObject().put("syntheticFixture",true);}public void validate(ModelBundle b,String type)throws Exception{if(!type.equals("speech.synthesize"))throw new IOException("Wrong fixture type");}public File generate(Context context)throws Exception{
            String mode=context.request().getJSONObject("input").getString("prompt");AudioPcm.Format format=new AudioPcm.Format(new JSONObject().put("schema",AudioPcm.SCHEMA).put("format","pcm_s16le").put("sampleRate",24000).put("channels",1).put("maxFrames",64).put("maxChunkFrames",64));AudioPcm.Sequence sequence=new AudioPcm.Sequence(format);context.audioStart(format);context.audioChunk(sequence.chunk(new JSONObject().put("schema",AudioPcm.SCHEMA).put("sequence",0).put("startFrame",0).put("frames",8).put("sampleRate",24000).put("channels",1).put("pcm",Base64.getEncoder().encodeToString(new byte[16]))));
            if(!release[0].await(10,TimeUnit.SECONDS))throw new IOException("Fixture release timeout");context.check();if(mode.equals("failed"))throw new IOException("Explicit audio provider fixture failure");File output=context.output("wav");Files.write(output.toPath(),wav());sequence.end(new JSONObject().put("schema",AudioPcm.SCHEMA).put("nextSequence",1).put("frames",8));sequence.verify(output);return output;
        }});
        LmaService service=new LmaService();EngineHost engine=new EngineHost(service,app);service.engine=engine;LocalJobs runner=new LocalJobs(app,engine,()->{});app.jobHost=runner;ApiHost api=new ApiHost(service,app);
        try{
            for(String mode:Arrays.asList("succeeded","failed","cancelled","interrupted")){
                release[0]=new CountDownLatch(1);JSONObject job=runner.submit(new JSONObject().put("bundleId",bundle.id).put("type","speech.synthesize").put("input",new JSONObject().put("prompt",mode)).put("parameters",new JSONObject()).put("allowUnmeasured",true),"audio_"+mode);String id=job.getString("id");
                until(()->{JSONArray all=app.audioStreams.snapshot();for(int i=0;i<all.length();i++)if(all.getJSONObject(i).getString("jobId").equals(id))return all.getJSONObject(i).getInt("frames")==8;return false;});
                verify(app.jobs.get(id).getJSONArray("artifacts").length()==0,"Audio arrives before artifact publication");verify(api.audioStreams()==app.audioStreams && app.audioStreams.get(id,0).getString("state").equals("streaming"),"API and actual runner share the same stream store");
                if(mode.equals("cancelled"))runner.cancel(id);if(mode.equals("interrupted"))runner.close();release[0].countDown();
                until(()->app.audioStreams.get(id,0).getString("state").equals(mode));JSONObject result=app.jobs.get(id);verify(result.getString("state").equals(mode),"Preview follows actual terminal task state");
                if(mode.equals("succeeded")){String artifact=result.getJSONArray("artifacts").getString(0);verify(app.audioStreams.get(id,0).getString("artifactId").equals(artifact)&&app.artifacts.get(artifact).getJSONObject("metadata").getString("mime").equals("audio/wav"),"Only the committed complete WAV becomes the durable result");}
                else verify(result.getJSONArray("artifacts").length()==0&&app.audioStreams.get(id,0).getString("artifactId").isEmpty(),"Failed/cancelled/interrupted audio never becomes a successful artifact");
                verify(!result.toString().contains("\"pcm\""),"Durable jobs contain no audio payload");
            }
            verify(app.audioStreams.snapshot().length()==4,"Four terminal previews are retained independently from durable results");
        }finally{release[0].countDown();runner.close();api.close();engine.close();}
        return passed;
    }
}
