package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Program contracts only; declared component sizes are metadata, never written as model data. */
public final class SanaSprintTest {
    private static int passed;
    private interface Action { void run() throws Exception; }
    private static void check(boolean ok) { if (!ok) throw new AssertionError("Sana-Sprint contract"); passed++; }
    private static void rejects(Action action) throws Exception { try { action.run(); } catch (Exception expected) { passed++; return; } throw new AssertionError("Expected invalid Sana-Sprint request"); }
    private static JSONObject read(String path) throws Exception { return new JSONObject(new String(Files.readAllBytes(Paths.get(path)), "UTF-8")); }
    private static JSONObject request(ModelBundle bundle) throws Exception { return new JSONObject().put("bundleId", bundle.id).put("type", "image.generate").put("input", new JSONObject().put("prompt", "  A Cat 中文  ")).put("parameters", bundle.parameters().normalize(new JSONObject(), new JSONObject()).getJSONObject("values")); }
    public static void main(String[] args) throws Exception {
        JSONArray models=read(args[0]).getJSONArray("bundles"); ModelBundle bundle=null;
        for (int i=0;i<models.length();i++) if (models.getJSONObject(i).getString("pipeline").equals(SanaSprintSpec.PIPELINE)) bundle=new ModelBundle(models.getJSONObject(i));
        if (bundle==null) throw new AssertionError("Missing complete Sana-Sprint catalogue recipe");
        final ModelBundle b=bundle; SanaSprintSpec.validate(b,"image.generate"); check(b.components.size()==14);
        InputSpec input=InputSpec.promptOnly().withNegativePrompt(false);
        check(!input.json().getBoolean("negativePrompt")); input.validate(new JSONArray(),new JSONObject().put("prompt","cat")); check(true);
        rejects(()->input.validate(new JSONArray(),new JSONObject().put("negativePrompt","bad")));
        check(b.tags().getString("kind").equals("kind:model") && b.tasks.contains("image"));
        long total=0; for (ModelBundle.Component c:b.components) { total+=c.bytes; check(!c.url.isEmpty()); check(SanaSprintSpec.filename(c.role).length()>0); }
        check(total==6754581137L); check(b.component("embeddings").bytes==1179648000L);
        JSONObject r=request(b), plan=SanaSprintSpec.prepare(b,r).getJSONObject("diffusionPlan"); check(plan.getString("profile").equals(SanaSprintSpec.PROFILE)); check(!r.has("diffusionPlan"));
        check(plan.getJSONObject("parameters").getInt("width")==1024 && plan.getJSONObject("parameters").getInt("steps")==2);
        JSONObject high=request(b); high.getJSONObject("parameters").put("width",65535).put("height",1).put("steps",99).put("threads",999).put("guidance",100).put("seed",9999999999L);
        JSONObject bounded=SanaSprintSpec.prepare(b,high).getJSONObject("diffusionPlan").getJSONObject("parameters");
        check(bounded.getInt("width")==1024 && bounded.getInt("height")==1024 && bounded.getInt("steps")==4 && bounded.getInt("threads")==32 && bounded.getDouble("guidance")==30 && bounded.getLong("seed")==Integer.MAX_VALUE);
        for (Object bad:new Object[]{"2",2.5,true}) { JSONObject value=request(b); value.getJSONObject("parameters").put("steps",bad); rejects(()->SanaSprintSpec.prepare(b,value)); }
        JSONObject negative=request(b); negative.getJSONObject("input").put("negativePrompt","negative"); rejects(()->SanaSprintSpec.prepare(b,negative));
        JSONObject adapter=request(b).put("adapters",new JSONArray().put(new JSONObject())); rejects(()->SanaSprintSpec.prepare(b,adapter));
        rejects(()->SanaSprintSpec.prepare(b,request(b).put("bundleId","other")));
        JSONObject empty=request(b); empty.getJSONObject("input").put("prompt"," "); rejects(()->SanaSprintSpec.prepare(b,empty));
        JSONObject extra=request(b); extra.getJSONObject("parameters").put("useCfg",true); rejects(()->SanaSprintSpec.prepare(b,extra));
        for (String field:new String[]{"engine","pipeline","architecture","backend"}) rejects(()->SanaSprintSpec.validate(new ModelBundle(b.json().put(field,"other")),"image.generate"));
        JSONObject missing=b.json(); missing.getJSONArray("components").remove(0); rejects(()->SanaSprintSpec.validate(new ModelBundle(missing),"image.generate"));
        JSONObject wrong=b.json(); wrong.getJSONArray("components").getJSONObject(0).put("format","gguf"); rejects(()->SanaSprintSpec.validate(new ModelBundle(wrong),"image.generate"));
        check(SanaSprintSpec.normalizedPrompt("\u0085\u00a0 A Cat 中文\u2003").equals("a cat 中文")); check(SanaSprintSpec.normalizedPrompt("İ ΟΣ").equals("i\u0307 ος"));
        SanaSprintSpec.metadata(new File(args[1])); check(true);
        File invalid=new File(args[2]); JSONObject config=read(args[1]).put("external_file","https://invalid.example/weights"); Files.write(invalid.toPath(),config.toString().getBytes("UTF-8")); rejects(()->SanaSprintSpec.metadata(invalid));
        System.out.println(new JSONObject().put("passed",passed).put("model_data_written",false).put("model_inference",false));
    }
}
