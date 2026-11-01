package com.lma.app.core;

import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/** Production metadata, admission journal and real HTTP sockets; explicit bounded output fixtures. */
public final class ApiPublicationTest {
    static final List<String> checks = new ArrayList<>();
    static void check(boolean value, String name) { if (!value) throw new AssertionError(name); checks.add(name); }
    static final String KEY = "publication-test-key";
    static final class Reply {
        int status; byte[] bytes; String etag, range, mime;
        JSONObject json() { return new JSONObject(new String(bytes, StandardCharsets.UTF_8)); }
    }
    static Reply call(int port, String method, String path, JSONObject body, String... headers) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL("http://127.0.0.1:" + port + path).openConnection();
        c.setConnectTimeout(2000); c.setReadTimeout(5000); c.setRequestMethod(method); c.setRequestProperty("Authorization", "Bearer " + KEY);
        for (int i = 0; i < headers.length; i += 2) c.setRequestProperty(headers[i], headers[i+1]);
        if (body != null) { byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8); c.setDoOutput(true); c.setRequestProperty("Content-Type", "application/json"); c.setFixedLengthStreamingMode(payload.length); try(OutputStream out=c.getOutputStream()){out.write(payload);} }
        try {
            Reply r = new Reply(); r.status=c.getResponseCode(); r.etag=c.getHeaderField("ETag");r.range=c.getHeaderField("Content-Range");r.mime=c.getContentType();
            InputStream in = r.status >= 400 ? c.getErrorStream() : c.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream();
            if(in!=null)try(InputStream owned=in){byte[] b=new byte[1024];int n;while((n=in.read(b))>=0)out.write(b,0,n);} r.bytes=out.toByteArray(); return r;
        } finally {c.disconnect();}
    }
    static JSONObject model(String id,String operation,int steps) throws Exception {
        return new JSONObject().put("id",id).put("object","model").put("owned_by","local").put("bundle_id",id)
            .put("x_lma",new JSONObject().put("operations",new JSONArray().put(operation)).put("publication",new JSONObject().put("eligible",true))
                .put("saved_parameters",new JSONObject().put("steps",steps)).put("parameter_schema",new JSONObject().put("type","object").put("properties",new JSONObject().put("steps",new JSONObject().put("type","integer").put("minimum",1).put("maximum",8)).put("speaker",new JSONObject().put("type","integer").put("minimum",0).put("maximum",1)).put("speed",new JSONObject().put("type","number").put("minimum",.5).put("maximum",2)))));
    }
    static final class Source implements ApiCatalogue.Source {
        int version=0, builds=0, steps=2; boolean busy=false, removed=false;
        public String version(){return ""+version;}
        public JSONArray build()throws Exception {builds++;return removed?new JSONArray():new JSONArray().put(model("image_fixture","image.generate",steps)).put(model("speech_fixture","speech.synthesize",steps));}
        public JSONObject readiness(JSONObject m)throws Exception{return new JSONObject().put("loaded",false).put("available",true).put("status",busy?"busy":"unloaded").put("reason_codes",new JSONArray());}
    }
    public static void main(String[] args)throws Exception {
        File root=new File(args[0]); Source source=new Source(); ApiCatalogue cat=new ApiCatalogue(new File(root,"api"),source);
        JSONObject first=cat.snapshot();String instance=first.getJSONObject("x_lma").getString("instance_id");long revision=first.getJSONObject("x_lma").getLong("revision");
        long created=cat.model("image_fixture").getLong("created");
        for(int i=0;i<20;i++)cat.snapshot();check(source.builds==1,"Unchanged discovery performs one metadata build and no model probe");
        source.busy=true;check(cat.model("image_fixture").getJSONObject("x_lma").getJSONObject("ready").getString("status").equals("busy"),"Busy metadata updates without evicting an eligible unloaded model");
        check(source.builds==1,"Readiness polling does not rebuild or write the catalogue");
        long config=cat.model("image_fixture").getJSONObject("x_lma").getJSONObject("publication").getLong("config_revision");
        source.steps=4;source.version++;check(cat.snapshot().getJSONObject("x_lma").getLong("revision")>revision,"Saved model changes increment the catalogue revision");
        check(cat.model("image_fixture").getJSONObject("x_lma").getJSONObject("publication").getLong("config_revision")>config,"Saved tunables increment only that model configuration revision");
        ApiCatalogue restarted=new ApiCatalogue(new File(root,"api"),source);
        check(restarted.snapshot().getJSONObject("x_lma").getString("instance_id").equals(instance),"Phone instance identity survives process restart");
        check(restarted.model("image_fixture").getLong("created")==created,"Model creation identity survives restart and settings changes");
        JSONObject publicValues=ApiCatalogue.publicParameters(new JSONObject().put("systemPrompt","private").put("referenceAudioPath","/private").put("apiKey","secret").put("maxTokens",512));
        check(publicValues.length()==1&&publicValues.getInt("maxTokens")==512,"Discovery strips private prompts, paths and credentials without dropping token limits");
        source.removed=true;source.version++;check(cat.snapshot().getJSONArray("data").length()==0,"Asset deletion removes publication on the next event revision");source.removed=false;source.version++;
        final JobStore jobs=new JobStore(new File(root,"jobs"));final ApiSubmissions journal=new ApiSubmissions(new File(root,"api"));AtomicInteger runs=new AtomicInteger(),freezes=new AtomicInteger();
        ArtifactStore artifacts=new ArtifactStore(new File(root,"artifacts"),file->new JSONObject().put("mime",file.getName().endsWith("wav")?"audio/wav":"image/png"));
        LocalApi.Runtime runtime=new LocalApi.Runtime(){
            public String apiKey(){return KEY;}public JSONObject health(){return new JSONObject();}public JSONArray models()throws Exception{return cat.snapshot().getJSONArray("data");}
            public JSONObject catalogue()throws Exception{return cat.snapshot();}public JSONObject model(String id)throws Exception{return cat.model(id);}public JSONObject capabilities(){return new JSONObject().put("schema","lma.capabilities/1");}
            public JSONArray engines(){return new JSONArray();}public JobStore jobs(){return jobs;}public ArtifactStore artifacts(){return artifacts;}public ApiSubmissions submissions(){return journal;}
            public JSONObject freezePublic(JSONObject r)throws Exception{freezes.incrementAndGet();JSONObject v=TaskInput.validate(r);v.put("parameters",new JSONObject().put("steps",source.steps));return v;}
            public JSONObject submit(JSONObject r,String key)throws Exception{
                JSONObject old=jobs.lookup(key);if(old!=null)return old;
                JSONObject accepted=jobs.submit(r,key),claimed=jobs.claimNext();runs.incrementAndGet();String id=claimed.getString("id");boolean wav=r.getString("type").equals("speech.synthesize");
                File output=artifacts.staging(id,wav?"wav":"png");byte[] bytes=wav?"RIFF0123WAVEfmt bounded-fixture".getBytes(StandardCharsets.US_ASCII):Base64.getDecoder().decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aYaQAAAAASUVORK5CYII=");Files.write(output.toPath(),bytes);
                JSONObject a=artifacts.commit(id,output,new JSONObject(),()->{});jobs.finish(id,claimed.getString("token"),new JSONArray().put(a.getString("id")),"");return jobs.get(id);
            }
            public void cancel(String id)throws Exception{jobs.cancel(id);}public LocalHttp.Response text(String p,JSONObject r){return LocalApi.json(200,r);}
        };
        try(LocalHttp http=new LocalHttp("127.0.0.1",0,new LocalApi(runtime,1000))){int port=http.port();
            Reply listing=call(port,"GET","/v1/models",null);check(listing.status==200&&listing.json().getJSONArray("data").length()==2,"Real socket publishes all complete image and speech peers");
            check(call(port,"GET","/v1/models",null,"If-None-Match",listing.etag).status==304,"Catalogue conditional GET returns genuine bodyless 304");
            check(call(port,"HEAD","/v1/models",null).bytes.length==0,"Catalogue HEAD has no response body");
            check(call(port,"GET","/v1/models/image_fixture",null).json().getString("id").equals("image_fixture"),"Single-model discovery uses the public stable ID");
            check(call(port,"GET","/v1/models/missing",null).status==404,"An unpublished model is a structured 404");
            check(call(port,"GET","/v1/capabilities",null).json().getString("schema").equals("lma.capabilities/1"),"Capability profile is independently discoverable");
            JSONObject image=new JSONObject().put("model","image_fixture").put("prompt","an orange cube").put("n",1).put("size","256x256");
            check(call(port,"POST","/v1/images/generations",image).status==400,"Generation requires a caller idempotency key before enqueue");
            Reply result=call(port,"POST","/v1/images/generations",image,"Idempotency-Key","image-one");
            check(result.status==200&&Base64.getDecoder().decode(result.json().getJSONArray("data").getJSONObject(0).getString("b64_json"))[1]=='P',"Image facade emits real PNG bytes in OpenAI b64_json");
            String job=result.json().getJSONObject("x_lma").getString("job_id");
            source.steps=6;source.version++;int previous=freezes.get();
            check(call(port,"POST","/v1/images/generations",image,"Idempotency-Key","image-one").status==200&&runs.get()==1&&freezes.get()==previous,"Retry after changed defaults finds the existing frozen job before resolving current settings");
            check(call(port,"POST","/v1/images/generations",new JSONObject(image.toString()).put("prompt","different"),"Idempotency-Key","image-one").status==409,"Same caller key with different semantic body conflicts");
            check(call(port,"POST","/v1/images/generations",new JSONObject(image.toString()).put("n",2),"Idempotency-Key","unsupported-n").status==400,"Unsupported image batch size is rejected before inference");
            check(call(port,"POST","/v1/images/generations",new JSONObject(image.toString()).put("quality","high"),"Idempotency-Key","unsupported-quality").status==400,"Unmapped quality presets are not silently discarded");
            check(call(port,"POST","/v1/images/generations",new JSONObject(image.toString()).put("image_url","https://example.invalid/a.png"),"Idempotency-Key","remote-input").status==400,"Remote media URLs cannot become phone inputs");
            JSONObject speech=new JSONObject().put("model","speech_fixture").put("input","Hello").put("voice","default");
            check(call(port,"POST","/v1/audio/speech",speech,"Idempotency-Key","missing-format").status==400,"Omitted response format requests MP3 and is honestly rejected");
            Reply audio=call(port,"POST","/v1/audio/speech",speech.put("response_format","wav"),"Idempotency-Key","speech-one");
            check(audio.status==200&&audio.mime.equals("audio/wav")&&audio.bytes[0]=='R'&&audio.bytes[8]=='W',"Speech facade returns a WAV byte body with the correct MIME");
            check(call(port,"POST","/v1/audio/speech",new JSONObject(speech.toString()).put("voice","99"),"Idempotency-Key","bad-voice").status==400,"Unknown numeric speakers are rejected rather than coerced to another voice");
            Reply named=call(port,"GET","/v1/lma/jobs/"+job,null);JSONObject j=named.json();String artifact=j.getJSONArray("outputs").getJSONObject(0).getString("id");
            check(named.status==200&&j.getString("model").equals("image_fixture")&&!j.has("request"),"Public job responses preserve model affinity and omit private prompts");
            String path="/v1/lma/artifacts/"+artifact+"/content";Reply range=call(port,"GET",path,null,"Range","bytes=0-7");
            check(range.status==206&&range.bytes.length==8&&range.range.startsWith("bytes 0-7/"),"Artifact byte ranges stream the requested bytes");
            check(call(port,"GET",path,null,"Range","bytes=0-7","If-Range","\"stale\"").status==200,"Stale If-Range triggers a complete artifact response");
            check(call(port,"GET",path,null,"If-None-Match",range.etag).status==304,"Artifact ETag supports a genuine conditional response");
            check(call(port,"DELETE","/v1/lma/jobs/"+job,null).status==200,"The caller can explicitly remove its terminal job history");
            check(call(port,"POST","/v1/images/generations",image,"Idempotency-Key","image-one").status==410&&runs.get()==2,"Removing history does not allow a duplicate image generation");
            check(new JobStore(new File(root,"jobs")).lookup(jobs.lookup("api_"+ApiCatalogue.hash(new JSONObject().put("endpoint","/v1/images/generations").put("key","image-one")))==null?"missing":"api_"+ApiCatalogue.hash(new JSONObject().put("endpoint","/v1/images/generations").put("key","image-one"))).optBoolean("historyRemoved"),"Independent native tombstone survives history removal and process restart");
        }
        JSONObject media=new JSONObject().put("bundleId","mesh_fixture").put("type","mesh.generate").put("input",new JSONObject().put("artifacts",new JSONArray().put(new JSONObject().put("role","reference_image").put("artifactId","artifact_fixture"))));
        check(TaskInput.validate(media).getJSONObject("input").getString("prompt").isEmpty(),"Image-only requests can defer fixed conditioning to the selected engine's input schema");
        try{TaskInput.validate(new JSONObject().put("bundleId","mesh_fixture").put("type","mesh.generate").put("input",new JSONObject().put("prompt","")));throw new AssertionError();}catch(IllegalArgumentException expected){check(true,"Empty text without any declared media input is rejected");}
        System.out.println(new JSONObject().put("passed",checks.size()).put("checks",new JSONArray(checks)).put("actual_socket_io",true).put("model_inference_tested",false).put("physical_device",false));
    }
}
