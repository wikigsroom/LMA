package com.lma.app;
import android.util.AtomicFile;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.util.*;

/** User-reviewed fixed main/projector pairs. Projectors never become standalone text models. */
public final class VisionPairs {
    private final LmaApp app;private final AtomicFile file;private JSONObject pairs;
    private volatile Set<String> bundles=Collections.emptySet();
    public VisionPairs(LmaApp app)throws Exception{this.app=app;File dir=new File(app.getFilesDir(),"vision-pairs");if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("无法创建视觉配对存储");file=new AtomicFile(new File(dir,"pairs.json"));try{pairs=DataFiles.read(file,256*1024);}catch(FileNotFoundException missing){pairs=new JSONObject();}refresh();}
    private void refresh()throws Exception{Set<String> ids=new HashSet<>();for(Iterator<String> it=pairs.keys();it.hasNext();)ids.add(pairs.getJSONObject(it.next()).getString("bundleId"));bundles=Collections.unmodifiableSet(ids);}
    public boolean referencesBundle(String id){return bundles.contains(id);}
    public synchronized JSONObject pair(String model)throws Exception{return pairs.has(model)?DataFiles.copy(pairs.getJSONObject(model)):null;}
    public synchronized JSONArray snapshot()throws Exception{JSONArray result=new JSONArray();for(Iterator<String> it=pairs.keys();it.hasNext();){JSONObject p=pair(it.next());p.put("installed",app.bundles.plan(p.getString("bundleId")).getBoolean("installed"));result.put(p);}return result;}
    public synchronized JSONObject bind(JSONObject manifest)throws Exception{
        if(!"lma.vision-pair/1".equals(manifest.getString("schema")))throw new IllegalArgumentException("视觉配对清单版本无效");
        String model=ModelBundle.key(manifest.getString("modelId")),architecture=manifest.getString("architecture");
        if(!Arrays.asList("qwen35","gemma3").contains(architecture))throw new IllegalArgumentException("此运行桥仅开放 qwen35 / gemma3；其他架构需要独立适配证据");
        if(!Protocol.isSha256(manifest.getString("mainSha256")))throw new IllegalArgumentException("必须固定主模型 SHA256");
        if(model.matches("m[0-9]{2}")&&!Arrays.asList("m03","m09","m15","m16").contains(model))throw new IllegalArgumentException("所选具体型号是文本变体，不能绑定视觉组件");
        JSONObject known=app.store.model(model);if(known.has("sha256")&&!known.getString("sha256").isEmpty()&&!known.getString("sha256").equalsIgnoreCase(manifest.getString("mainSha256")))throw new IllegalArgumentException("配对清单与已选主模型身份不同");
        if((model.equals("m03")||model.equals("m09")||model.equals("m15"))&&!architecture.equals("qwen35")||model.equals("m16")&&!architecture.equals("gemma3"))throw new IllegalArgumentException("视觉架构与具体变体不符");
        if(!Arrays.asList("m03","m09","m15","m16").contains(model)&&!manifest.optBoolean("userReviewedCompatibility"))throw new IllegalArgumentException("自定义视觉变体需要明确核对主模型与 projector 的兼容性");
        JSONObject projector=DataFiles.copy(manifest.getJSONObject("projector"));projector.put("role","projector").put("format","gguf");
        if(projector.optString("license").isEmpty()||!Protocol.isSha256(projector.getString("sha256"))||!projector.getString("revision").matches("[a-f0-9]{40,64}"))throw new IllegalArgumentException("视觉组件必须固定 revision / SHA256 并披露许可");
        String id="vision_"+projector.getString("sha256").substring(0,24);JSONObject bundle=new JSONObject().put("schema",ModelBundle.SCHEMA).put("id",id).put("modelId",id).put("recipeId","vision_projector").put("engine","vision_component").put("architecture",architecture).put("pipeline","mtmd").put("backend","cpu").put("name","视觉组件 · "+known.getString("name")).put("tasks",new JSONArray().put("text")).put("components",new JSONArray().put(projector));
        app.bundles.declare(new ModelBundle(bundle));JSONObject pair=DataFiles.copy(manifest).put("bundleId",id).put("boundAt",System.currentTimeMillis()).put("phoneVerified",false);
        JSONObject next=DataFiles.copy(pairs);next.put(model,pair);DataFiles.write(file,next);pairs=next;refresh();return DataFiles.copy(pair);
    }
    public synchronized void unbind(String model)throws Exception{JSONObject next=DataFiles.copy(pairs);next.remove(model);DataFiles.write(file,next);pairs=next;refresh();}
    public BundleStore.Lease acquire(String model,DataFiles.Check check)throws Exception{JSONObject p=pair(model);if(p==null)return null;
        if(!app.bundles.plan(p.getString("bundleId")).getBoolean("installed"))return null;
        if(!DataFiles.sha256(app.store.modelFile(model),check).equalsIgnoreCase(p.getString("mainSha256")))throw new IOException("主模型哈希与视觉配对清单不符；请重新核对导出，不会替换已有文件");
        return app.bundles.acquire(p.getString("bundleId"));
    }
}
