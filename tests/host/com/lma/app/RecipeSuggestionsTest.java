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
