package com.lma.app;

import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

/** Production metadata client/controller/storage. All model data and HTTP responses are fixtures. */
public final class RecipeSuggestionsTest {
    private static final String REV="0123456789abcdef0123456789abcdef01234567", ID="sana_edit_mnn_cpu_v1";
    private static int checks;
    private interface Attempt { void run() throws Exception; }
    private interface Condition { boolean done() throws Exception; }
    private static void check(boolean value,String why) {if(!value)throw new AssertionError(why);checks++;}
    private static void rejects(Attempt call,String why)throws Exception{try{call.run();}catch(Exception expected){checks++;return;}throw new AssertionError(why);}
    private static void await(Condition done)throws Exception{long end=System.currentTimeMillis()+7000;while(System.currentTimeMillis()<end){if(done.done())return;Thread.sleep(10);}throw new AssertionError("Async fixture timeout");}
    private static JSONObject command(String action){return new JSONObject().put("action",action).put("requestId",UUID.randomUUID().toString());}
    private static JSONObject repo(){return new JSONObject().put("id","fixture/sana").put("sha",REV).put("tags",new JSONArray());}
    private static JSONObject entry(String path){return new JSONObject().put("type","file").put("path",path).put("size",1000).put("lfs",new JSONObject().put("oid",String.join("",Collections.nCopies(64,"a"))));}
    private static String next(String value){return "<https://huggingface.co/api/models/fixture/sana/tree/"+REV+"?cursor="+value+">; rel=\"next\"";}
    private static JSONObject asset(String path)throws Exception{return HubClient.asset(HubClient.model(repo()),entry(path));}
    private static JSONArray files() {
        JSONArray a=new JSONArray();for(String name:new String[]{"transformer.mnn","transformer.mnn.weight","connector.mnn","connector.mnn.weight","projector.mnn","projector.mnn.weight","vae_decoder.mnn","vae_decoder.mnn.weight","vae_encoder.mnn","vae_encoder.mnn.weight","llm.mnn","llm.mnn.weight","llm_config.json","tokenizer.txt","meta_queries.mnn"})a.put(entry("export/"+name));return a;
    }
    private static JSONObject inventory(JSONArray entries,boolean complete)throws Exception {
        JSONArray a=new JSONArray();for(int i=0;i<entries.length();i++)a.put(HubClient.asset(HubClient.model(repo()),entries.getJSONObject(i)));
        return new JSONObject().put("repository",HubClient.model(repo())).put("assets",a).put("pages",1).put("complete",complete);
    }
    private static JSONObject row(JSONObject review,String role)throws Exception {JSONArray rows=review.getJSONArray("rows");for(int i=0;i<rows.length();i++)if(rows.getJSONObject(i).getString("role").equals(role))return rows.getJSONObject(i);throw new AssertionError(role);}
    private static JSONArray selected(JSONObject review)throws Exception{JSONArray roles=new JSONArray(),rows=review.getJSONArray("rows");for(int i=0;i<rows.length();i++)if(rows.getJSONObject(i).getString("state").equals("unique"))roles.put(rows.getJSONObject(i).getString("role"));return roles;}
    private static String draft(HubCatalog h)throws Exception{return h.snapshot().getJSONObject("recipeDraft").getString("draftId");}
    private static void start(HubCatalog h)throws Exception{
        h.dispatch(command("hubFiles").put("repository","fixture/sana"));await(()->!h.snapshot().getJSONObject("files").getBoolean("loading"));
        h.dispatch(command("hubRecipeStart").put("repository","fixture/sana"));h.dispatch(command("hubRecipeTemplate").put("draftId",draft(h)).put("templateId",ID));
    }
    public static void main(String[] args)throws Exception {
        Path root=Paths.get(args[0]),out=root.resolve("build/recipe-suggestion-tests");Files.createDirectories(out);
        RecipeCatalogue recipes=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(root.resolve("app/src/main/assets/recipe-templates.json")),"UTF-8")));
        String wan="wan21_13b_split_vulkan_v1";
        JSONArray wanFiles=new JSONArray();
        for(String name:new String[]{"Wan2.1-T2V-1.3B-Q4_K_S.gguf","Wan2.1-T2V-14B-Q4_K_S.gguf","umt5-xxl-encoder-Q4_K_M.gguf","wan_2.1_vae.safetensors","tokenizer.json"})wanFiles.put(entry(name));
        JSONObject wanReview=RecipeSuggestions.review(recipes,wan,new JSONObject(),inventory(wanFiles,true));
        check(wanReview.getInt("suggested")==4 && row(wanReview,"diffusion").getString("state").equals("unique"),"Wan GPU hints identify the four exact roles and exclude the 14B generator");
        JSONObject wanPartial=RecipeSuggestions.apply(recipes,wan,new JSONObject(),wanReview,new JSONArray().put("diffusion").put("vae"));
        check(wanPartial.length()==2 && !wanPartial.has("t5"),"Only explicitly selected video components are bound");
        wanFiles.put(entry("Wan2.1-T2V-1.3B-Q8_0.gguf"));
        JSONObject wanAmbiguous=RecipeSuggestions.review(recipes,wan,new JSONObject(),inventory(wanFiles,true));
        check(row(wanAmbiguous,"diffusion").getString("state").equals("ambiguous"),"Different Wan quantizations require a user choice");
        rejects(()->RecipeSuggestions.apply(recipes,wan,new JSONObject(),wanAmbiguous,new JSONArray().put("diffusion")),"Ambiguous video weights cannot be silently selected");
        JSONObject empty=new JSONObject(),full=inventory(files(),true),r=RecipeSuggestions.review(recipes,ID,empty,full);
        check(r.getInt("suggested")==15,"All fifteen Sana components have unique metadata suggestions");
        check(empty.length()==0,"Review never binds components implicitly");
        JSONObject applied=RecipeSuggestions.apply(recipes,ID,empty,r,selected(r));check(applied.length()==15,"Explicit confirmation applies all selected roles");
        check(empty.length()==0 && !r.has("bundleId"),"Application keeps original selection and does not declare/download a bundle");
        for(String role:new String[]{"diffusion","connector","projector","vae","vae_encoder","llm"}) check(applied.getJSONObject(role+"_data").getString("path").equals(applied.getJSONObject(role).getString("path")+".weight"),"Exact sibling data pairing: "+role);
        check(new ModelBundle(recipes.compose(ID,applied).json()).components.size()==15,"Suggested components compose through the actual immutable bundle contract");
        RecipeCatalogue previous=new RecipeCatalogue(new JSONObject(new String(Files.readAllBytes(Paths.get(args[1])),"UTF-8")));
        JSONObject legacyBindings=DataFiles.copy(applied);legacyBindings.remove("vae_encoder");legacyBindings.remove("vae_encoder_data");
        ModelBundle legacy=previous.compose("sana_mnn_cpu_v1",legacyBindings);String saved=DataFiles.canonical(legacy.json());
        check(!recipes.compose(ID,applied).id.equals(legacy.id),"An incompatible image-edit recipe has an explicitly distinct identity");
        check(DataFiles.canonical(new ModelBundle(legacy.json()).json()).equals(saved),"Old thirteen-component registered metadata remains byte-equivalent without implicit migration");
        JSONObject changed=new JSONObject().put("diffusion",asset("other/transformer.mnn"));rejects(()->RecipeSuggestions.apply(recipes,ID,changed,r,selected(r)),"Stale bindings invalidate review");
        rejects(()->RecipeSuggestions.apply(recipes,"text_gguf_cpu_v1",empty,r,selected(r)),"Wrong template invalidates review");
        rejects(()->RecipeSuggestions.apply(recipes,ID,empty,r,new JSONArray()),"Empty confirmation cannot mutate settings");
        rejects(()->RecipeSuggestions.apply(recipes,ID,empty,r,new JSONArray().put("llm").put("llm")),"Duplicate role confirmation rejected");
        rejects(()->RecipeSuggestions.apply(recipes,ID,empty,r,new JSONArray().put("invented")),"Unknown role confirmation rejected");
        JSONObject preserved=new JSONObject().put("diffusion",asset("custom/selected.mnn"));JSONObject keep=RecipeSuggestions.review(recipes,ID,preserved,full);
        check(row(keep,"diffusion").getString("state").equals("existing"),"Manual choice is preserved even when names differ");
        check(row(keep,"diffusion_data").getString("state").equals("missing"),"Other folder's weight cannot replace the selected graph's sibling");
        rejects(()->RecipeSuggestions.apply(recipes,ID,preserved,keep,new JSONArray().put("diffusion")),"Confirmation cannot overwrite an existing selection");
        JSONArray amb=files();amb.put(entry("different/llm.mnn"));JSONObject ambiguous=RecipeSuggestions.review(recipes,ID,empty,inventory(amb,true));
        check(row(ambiguous,"llm").getString("state").equals("ambiguous"),"Same basename in two folders remains ambiguous");
        check(row(ambiguous,"llm_data").getString("state").equals("missing"),"Ambiguous graph does not provide a guessed sibling anchor");
        rejects(()->RecipeSuggestions.apply(recipes,ID,empty,ambiguous,new JSONArray().put("llm")),"Ambiguous candidates cannot be confirmed as a guessed unique choice");
        JSONObject incomplete=RecipeSuggestions.review(recipes,ID,empty,inventory(files(),false));check(incomplete.getInt("suggested")==0,"Incomplete inventory never asserts uniqueness");
        rejects(()->RecipeSuggestions.apply(recipes,ID,empty,incomplete,new JSONArray().put("llm")),"Partial directory cannot be applied");
        JSONObject mixed=DataFiles.copy(full);mixed.getJSONArray("assets").getJSONObject(0).put("revision",REV.replace('0','a'));
        rejects(()->RecipeSuggestions.review(recipes,ID,empty,mixed),"Mixed revisions cannot enter a review");
        JSONObject duplicate=DataFiles.copy(full);duplicate.getJSONArray("assets").put(duplicate.getJSONArray("assets").getJSONObject(0));rejects(()->RecipeSuggestions.review(recipes,ID,empty,duplicate),"Duplicate metadata identities rejected");
        JSONObject blocked=DataFiles.copy(full);blocked.getJSONArray("assets").getJSONObject(0).put("blocked","missing SHA");check(row(RecipeSuggestions.review(recipes,ID,empty,blocked),"diffusion").getString("state").equals("missing"),"Blocked files are not proposed");
        JSONObject overlap=recipes.template(ID);overlap.getJSONArray("requirements").getJSONObject(2).put("matchFiles",new JSONArray().put("transformer.mnn"));RecipeSuggestions.validate(overlap);
        JSONObject source=new JSONObject().put("schema","lma.recipe-catalogue/1").put("templates",new JSONArray().put(overlap));JSONObject overlapping=RecipeSuggestions.review(new RecipeCatalogue(source),ID,empty,full);
        check(row(overlapping,"diffusion").getString("state").equals("overlap") && row(overlapping,"connector").getString("state").equals("overlap"),"Two roles cannot silently claim the same unique file");
        for(String hint:new String[]{"../model.mnn","a**b","file\n.mnn","x/y.mnn"}){JSONObject bad=recipes.template(ID);bad.getJSONArray("requirements").getJSONObject(0).put("matchFiles",new JSONArray().put(hint));rejects(()->RecipeSuggestions.validate(bad),"Malformed signed filename hint rejected");}
        JSONObject badSibling=recipes.template(ID);badSibling.getJSONArray("requirements").getJSONObject(1).put("matchSibling",new JSONObject().put("role","unknown").put("suffix",".weight"));rejects(()->RecipeSuggestions.validate(badSibling),"Unknown sibling anchor rejected");
        String flux="flux2_klein_4b_split_cpu_v1";
        JSONArray fluxFiles=new JSONArray().put(entry("flux-2-klein-4b-Q4_0.gguf")).put(entry("Qwen3-4B-Q4_K_M.gguf"))
            .put(entry("vae/diffusion_pytorch_model.safetensors")).put(entry("tokenizer/merges.txt"));
        JSONObject fluxReview=RecipeSuggestions.review(recipes,flux,empty,inventory(fluxFiles,true));
        check(fluxReview.getInt("suggested")==4,"Distilled FLUX.2-klein complete metadata suggests every matching role");
        check(RecipeSuggestions.apply(recipes,flux,empty,fluxReview,selected(fluxReview)).length()==4,"Every suggested component requires explicit application");
        JSONArray fluxAmbiguous=new JSONArray(fluxFiles.toString()).put(entry("flux-2-klein-4b-Q8_0.gguf"));
        check(row(RecipeSuggestions.review(recipes,flux,empty,inventory(fluxAmbiguous,true)),"diffusion").getString("state").equals("ambiguous"),"Multiple quantizations are not silently selected");
        JSONArray fluxBase=new JSONArray().put(entry("flux-2-klein-base-4b-Q4_0.gguf")).put(entry("Qwen3-4B-Instruct-2507-Q4_K_M.gguf"));
        JSONObject fluxWrong=RecipeSuggestions.review(recipes,flux,empty,inventory(fluxBase,true));
        check(row(fluxWrong,"diffusion").getString("state").equals("missing") && row(fluxWrong,"llm").getString("state").equals("missing"),"Base checkpoint and alternate text encoder are not guessed as matched distilled recipe");
        check(RecipeSuggestions.review(recipes,flux,empty,inventory(fluxFiles,false)).getInt("suggested")==0,"Incomplete FLUX metadata cannot establish unique components");
        String zimage="z_image_turbo_split_cpu_v1";
        JSONArray zFiles=new JSONArray().put(entry("z_image_turbo-Q4_0.gguf")).put(entry("Qwen3-4B-Q4_K_M.gguf")).put(entry("vae/diffusion_pytorch_model.safetensors")).put(entry("tokenizer/merges.txt"));
        JSONObject zReview=RecipeSuggestions.review(recipes,zimage,empty,inventory(zFiles,true));
        check(zReview.getInt("suggested")==4,"Complete Z-Image Turbo metadata suggests all four explicit roles");
        check(RecipeSuggestions.apply(recipes,zimage,empty,zReview,selected(zReview)).length()==4,"Z-Image suggestions need explicit application before declaration");
        JSONArray zAmbiguous=new JSONArray(zFiles.toString()).put(entry("z_image_turbo-Q8_0.gguf"));
        check(row(RecipeSuggestions.review(recipes,zimage,empty,inventory(zAmbiguous,true)),"diffusion").getString("state").equals("ambiguous"),"Z-Image quantizations remain an explicit user choice");
        JSONArray zWrong=new JSONArray().put(entry("z_image_base-Q4_0.gguf")).put(entry("Qwen3-4B-Instruct-2507-Q4_K_M.gguf"));
        JSONObject zWrongReview=RecipeSuggestions.review(recipes,zimage,empty,inventory(zWrong,true));
        check(row(zWrongReview,"diffusion").getString("state").equals("missing") && row(zWrongReview,"llm").getString("state").equals("missing"),"Turbo selection does not guess a base checkpoint or alternate encoder");
        check(row(RecipeSuggestions.review(recipes,zimage,empty,inventory(new JSONArray().put(entry("flux2_ae.safetensors")),true)),"vae").getString("state").equals("missing"),"FLUX.2 VAE is not suggested as the original Z-Image VAE");
        check(RecipeSuggestions.review(recipes,zimage,empty,inventory(zFiles,false)).getInt("suggested")==0,"Partial Z-Image inventory never establishes uniqueness");
        List<String> requests=Collections.synchronizedList(new ArrayList<>());HubClient client=new HubClient("auto","",(address,s,t)->{
            requests.add(address);if(!address.contains("/tree/"))return new HubClient.Response(repo().toString(),null,"fixture");
            JSONArray a=files(),part=new JSONArray();boolean second=address.contains("cursor=two");for(int i=second?6:0;i<(second?a.length():6);i++)part.put(a.getJSONObject(i));return new HubClient.Response(part.toString(),second?null:next("two"),"fixture");});
        JSONObject collected=client.inventory(HubClient.model(repo()),()->{});check(collected.getInt("pages")==2 && collected.getJSONArray("assets").length()==15,"Actual production pagination collects all matching roles");
        check(requests.stream().allMatch(a->a.contains("/tree/"+REV)),"Metadata requests stay on exact frozen revision");
        AtomicInteger pages=new AtomicInteger();HubClient large=new HubClient("auto","",(a,s,t)->new HubClient.Response(new JSONArray().put(entry("f"+pages.incrementAndGet()+".txt")).toString(),next("p"+pages.get()),"fixture"));
        check(!large.inventory(HubClient.model(repo()),()->{}).getBoolean("complete") && pages.get()==8,"Large inventory stops at bounded pages and reports incomplete");
        HubClient cycle=new HubClient("auto","",(a,s,t)->new HubClient.Response("[]",next("loop"),"fixture"));rejects(()->cycle.inventory(HubClient.model(repo()),()->{}),"Repeated cursors cannot loop forever");
        HubClient dup=new HubClient("auto","",(a,s,t)->new HubClient.Response(new JSONArray().put(entry("same.mnn")).toString(),a.contains("cursor=")?null:next("two"),"fixture"));rejects(()->dup.inventory(HubClient.model(repo()),()->{}),"Duplicate page paths fail atomically");
        rejects(()->client.inventory(HubClient.model(repo()),()->{throw new IOException("cancelled fixture");}),"Cancellation checked before starting requests");
        LmaApp app=new LmaApp(out.resolve("controller-"+System.nanoTime()).toFile(),root.resolve("app/src/main/assets").toFile(),out.toFile());
        try(HubCatalog hub=new HubCatalog(app,()->client)){
            start(hub);hub.dispatch(command("hubRecipeBind").put("draftId",draft(hub)).put("role","diffusion").put("repository","fixture/sana").put("revision",REV).put("path","export/transformer.mnn"));
            JSONObject before=hub.snapshot().getJSONObject("recipeDraft").getJSONObject("bindings");
            hub.dispatch(command("hubRecipeReview").put("draftId",draft(hub)));await(()->!hub.snapshot().getJSONObject("recipeDraft").optBoolean("reviewing"));
            JSONObject review=hub.snapshot().getJSONObject("recipeDraft").getJSONObject("suggestions");check(review.getInt("suggested")==14,"Controller checks remaining files while preserving manual primary");
            check(app.bundles.snapshot().length()==0,"Review leaves the user's local model store untouched");
            rejects(()->hub.dispatch(command("hubRecipeApply").put("draftId",draft(hub)).put("reviewId","invented").put("roles",selected(review))),"WebView cannot invent a review token");
            hub.dispatch(command("hubRecipeApply").put("draftId",draft(hub)).put("reviewId",review.getString("reviewId")).put("roles",selected(review)));
            JSONObject bindings=hub.snapshot().getJSONObject("recipeDraft").getJSONObject("bindings");check(bindings.length()==15 && DataFiles.canonical(bindings.getJSONObject("diffusion")).equals(DataFiles.canonical(before.getJSONObject("diffusion"))),"Explicit native application merges choices without replacement");
            check(app.bundles.snapshot().length()==0,"Applying suggestions still does not register or download a model");
            rejects(()->hub.dispatch(command("hubRecipeApply").put("draftId",draft(hub)).put("reviewId",review.getString("reviewId")).put("roles",selected(review))),"An applied token cannot be replayed");
            JSONObject declare=command("hubRecipeDeclare").put("draftId",draft(hub));hub.dispatch(declare);check(app.bundles.snapshot().length()==1 && !app.bundles.snapshot().getJSONObject(0).getBoolean("installed"),"Separate user declaration creates an uninstalled immutable bundle");
            check(requests.stream().noneMatch(a->a.contains("/resolve/")),"Review/apply/declare issue zero asset download requests");
        }
        AtomicBoolean fail=new AtomicBoolean(false);HubClient failing=new HubClient("auto","",(a,s,t)->{if(fail.get())throw new IOException("metadata fixture unavailable");return a.contains("/tree/")?new HubClient.Response(files().toString(),null,"fixture"):new HubClient.Response(repo().toString(),null,"fixture");});
        try(HubCatalog hub=new HubCatalog(app,()->failing)){
            start(hub);hub.dispatch(command("hubRecipeBind").put("draftId",draft(hub)).put("role","diffusion").put("repository","fixture/sana").put("revision",REV).put("path","export/transformer.mnn"));
            fail.set(true);hub.dispatch(command("hubRecipeReview").put("draftId",draft(hub)));await(()->!hub.snapshot().getJSONObject("recipeDraft").optBoolean("reviewing"));
            JSONObject failed=hub.snapshot().getJSONObject("recipeDraft");check(failed.optString("reviewError").contains("metadata fixture unavailable") && !failed.has("suggestions"),"Metadata failure clears progress and allows retry without a partial review");
            check(failed.getJSONObject("bindings").length()==1,"Failed metadata lookup preserves every manual binding");
            check(app.lastError.isEmpty(),"Review error remains local to component selection");
        }
        for(boolean cancel:new boolean[]{true,false}) delayed(root,out,cancel);
        JSONObject report=new JSONObject().put("passed",true).put("checks",checks).put("production_metadata_client_controller",true).put("model_inference",false).put("physical_android",false).put("asset_downloads",0);
        Files.write(out.resolve("results.json"),(report.toString(2)+"\n").getBytes("UTF-8"));System.out.println(report);
    }
    private static void delayed(Path root,Path out,boolean cancel)throws Exception{
        CountDownLatch entered=new CountDownLatch(1),release=new CountDownLatch(1);AtomicBoolean block=new AtomicBoolean(false);
        HubClient client=new HubClient("auto","",(a,s,t)->{if(!a.contains("/tree/"))return new HubClient.Response(repo().toString(),null,"fixture");if(block.get()){entered.countDown();if(!release.await(5,TimeUnit.SECONDS))throw new IOException("fixture timeout");}return new HubClient.Response(files().toString(),null,"fixture");});
        LmaApp app=new LmaApp(out.resolve("delayed-"+System.nanoTime()).toFile(),root.resolve("app/src/main/assets").toFile(),out.toFile());
        try(HubCatalog hub=new HubCatalog(app,()->client)){
            start(hub);block.set(true);JSONObject pending=command("hubRecipeReview").put("draftId",draft(hub));hub.dispatch(pending);check(entered.await(3,TimeUnit.SECONDS),"Review runs outside the UI caller");
            if(cancel)hub.dispatch(command("hubRecipeCancelReview").put("draftId",draft(hub)));else hub.dispatch(command("hubRecipeTemplate").put("draftId",draft(hub)).put("templateId","text_gguf_cpu_v1"));
            release.countDown();await(()->{synchronized(app.commands){return app.commands.stream().anyMatch(c->c.optString("requestId").equals(pending.optString("requestId")));}});
            check(!hub.snapshot().getJSONObject("recipeDraft").has("suggestions"),cancel?"Stopped review cannot restore suggestions":"Changed template cannot receive stale suggestions");
            check(app.lastError.isEmpty() && app.bundles.snapshot().length()==0,"Stopped/stale checks neither interrupt inference nor modify local models");
        }finally{release.countDown();}
    }
}
