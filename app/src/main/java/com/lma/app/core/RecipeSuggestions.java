package com.lma.app.core;

import org.json.*;
import java.util.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Read-only file-name suggestions. They never establish architecture/compatibility or fetch assets. */
public final class RecipeSuggestions {
    private RecipeSuggestions() {}
    public static void validate(JSONObject template) throws Exception {
        JSONArray rules=template.getJSONArray("requirements"); Set<String> roles=new HashSet<>();
        for(int i=0;i<rules.length();i++) roles.add(rules.getJSONObject(i).getString("role"));
        for(int i=0;i<rules.length();i++) {
            JSONObject rule=rules.getJSONObject(i); JSONArray names=rule.optJSONArray("matchFiles");
            if(rule.has("matchFiles") && (names==null || names.length()<1 || names.length()>16)) throw new IllegalArgumentException("Invalid file matching hints");
            if(names!=null) for(int n=0;n<names.length();n++) {
                String name=names.getString(n);
                if(name.length()>160 || !name.matches("[\\p{L}\\p{N}_.+() @*\\-]+") || name.equals(".") || name.equals("..") || name.indexOf('*')!=name.lastIndexOf('*')) throw new IllegalArgumentException("Invalid file-name hint");
            }
            if(rule.has("matchSibling")) {
                JSONObject sibling=rule.getJSONObject("matchSibling"); String role=sibling.getString("role"), suffix=sibling.getString("suffix");
                if(sibling.length()!=2 || !roles.contains(role) || role.equals(rule.getString("role")) || !suffix.matches("\\.[a-z0-9_.]{1,32}") || suffix.contains("..")) throw new IllegalArgumentException("Invalid paired-file hint");
            }
        }
    }
    public static String fingerprint(String template, JSONObject bindings) throws Exception {
        return Protocol.hex(MessageDigest.getInstance("SHA-256").digest((template+"\n"+DataFiles.canonical(bindings)).getBytes(StandardCharsets.UTF_8)));
    }
    private static boolean nameMatches(String pattern,String name) {
        int star=pattern.indexOf('*');
        return star<0?pattern.equals(name):name.startsWith(pattern.substring(0,star)) && name.endsWith(pattern.substring(star+1)) && name.length()>=pattern.length()-1;
    }
    private static boolean matches(JSONObject rule,JSONObject asset,JSONObject anchors) throws Exception {
        String path=asset.getString("path"), name=path.substring(path.lastIndexOf('/')+1);
        if(rule.has("matchSibling")) {
            JSONObject sibling=rule.getJSONObject("matchSibling"),anchor=anchors.optJSONObject(sibling.getString("role"));
            return anchor!=null && anchor.getString("repository").equals(asset.getString("repository")) && anchor.getString("revision").equals(asset.getString("revision")) && (anchor.getString("path")+sibling.getString("suffix")).equals(path);
        }
        JSONArray hints=rule.optJSONArray("matchFiles");
        if(hints!=null) for(int i=0;i<hints.length();i++) if(nameMatches(hints.getString(i),name))return true;
        return false;
    }
    private static String identity(JSONObject asset) throws Exception { return asset.getString("repository")+"@"+asset.getString("revision")+":"+asset.getString("path"); }
    public static JSONObject review(RecipeCatalogue recipes,String templateId,JSONObject bindings,JSONObject inventory) throws Exception {
        JSONObject template=recipes.template(templateId), repository=inventory.getJSONObject("repository");
        JSONArray assets=inventory.getJSONArray("assets"),rules=template.getJSONArray("requirements"),rows=new JSONArray();
        if(assets.length()>2048) throw new IllegalArgumentException("Too many metadata candidates");
        Set<String> seen=new HashSet<>();
        for(int i=0;i<assets.length();i++) {
            JSONObject asset=assets.getJSONObject(i);
            if(!asset.getString("repository").equals(repository.getString("id")) || !asset.getString("revision").equals(repository.getString("revision")) || !seen.add(identity(asset))) throw new IllegalArgumentException("Mixed or duplicate repository metadata");
        }
        JSONObject anchors=DataFiles.copy(bindings); Map<String,JSONArray> candidates=new LinkedHashMap<>();
        // Resolve directly named files first, then companions anchored to one exact selected/proposed path.
        for(int pass=0;pass<2;pass++) for(int i=0;i<rules.length();i++) {
            JSONObject rule=rules.getJSONObject(i);String role=rule.getString("role");if(bindings.has(role))continue;
            JSONArray options=new JSONArray();
            for(int j=0;j<assets.length();j++) {
                JSONObject asset=assets.getJSONObject(j);
                if(!matches(rule,asset,anchors))continue;
                try { recipes.accept(templateId,role,asset); } catch(IllegalArgumentException invalid) { continue; }
                options.put(DataFiles.copy(asset));
            }
            candidates.put(role,options);
            if(options.length()==1 && inventory.getBoolean("complete"))anchors.put(role,options.getJSONObject(0));else anchors.remove(role);
        }
        Map<String,Integer> uses=new HashMap<>();
        for(JSONArray options:candidates.values()) if(options.length()==1) {String id=identity(options.getJSONObject(0));uses.put(id,uses.getOrDefault(id,0)+1);}
        Set<String> already=new HashSet<>(); for(Iterator<String> it=bindings.keys();it.hasNext();)already.add(identity(bindings.getJSONObject(it.next())));
        int suggested=0;
        for(int i=0;i<rules.length();i++) {
            JSONObject rule=rules.getJSONObject(i);String role=rule.getString("role");
            JSONObject row=new JSONObject().put("role",role).put("label",rule.optString("label",role)).put("required",rule.optBoolean("required",true));
            if(bindings.has(role))row.put("state","existing").put("selected",DataFiles.copy(bindings.getJSONObject(role))).put("count",0).put("candidates",new JSONArray());
            else {
                JSONArray options=candidates.get(role),shown=new JSONArray();for(int j=0;j<Math.min(16,options.length());j++)shown.put(options.getJSONObject(j));
                String state=options.length()==0?"missing":options.length()>1?"ambiguous":!inventory.getBoolean("complete")?"incomplete":uses.get(identity(options.getJSONObject(0)))>1 || already.contains(identity(options.getJSONObject(0)))?"overlap":"unique";
                if(!rule.has("matchFiles")&&!rule.has("matchSibling"))state="manual";
                row.put("state",state).put("count",options.length()).put("candidates",shown);if(state.equals("unique"))suggested++;
            }
            rows.put(row);
        }
        return new JSONObject().put("schema","lma.recipe-suggestions/1").put("reviewId",UUID.randomUUID().toString()).put("templateId",templateId).put("bindingsFingerprint",fingerprint(templateId,bindings)).put("repository",DataFiles.copy(repository)).put("complete",inventory.getBoolean("complete")).put("pages",inventory.getInt("pages")).put("rows",rows).put("suggested",suggested);
    }
    public static JSONObject apply(RecipeCatalogue recipes,String template,JSONObject bindings,JSONObject review,JSONArray selected) throws Exception {
        if(!review.getString("templateId").equals(template) || !review.getString("bindingsFingerprint").equals(fingerprint(template,bindings)))throw new IllegalArgumentException("组件选择已变化，请重新检查配套文件");
        if(selected.length()<1 || selected.length()>64 || !review.getBoolean("complete"))throw new IllegalArgumentException("请选择已完整检查的建议，或继续手动选择");
        JSONObject result=DataFiles.copy(bindings);Set<String> seen=new HashSet<>();JSONArray rows=review.getJSONArray("rows");
        for(int i=0;i<selected.length();i++) {
            String role=selected.getString(i);if(!seen.add(role)||bindings.has(role))throw new IllegalArgumentException("不能重复选择或覆盖已有组件");
            JSONObject found=null;for(int j=0;j<rows.length();j++)if(rows.getJSONObject(j).getString("role").equals(role))found=rows.getJSONObject(j);
            if(found==null || !found.getString("state").equals("unique") || found.getJSONArray("candidates").length()!=1)throw new IllegalArgumentException("存在多个或无法确认的文件，请手动选择");
            JSONObject asset=found.getJSONArray("candidates").getJSONObject(0);recipes.accept(template,role,asset);result.put(role,DataFiles.copy(asset));
        }
        return result;
    }
}
