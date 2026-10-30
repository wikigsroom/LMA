package com.lma.app.core;

import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

/** Signed-App recipe definitions; file choices are supplied only from native HF metadata. */
public final class RecipeCatalogue {
    private final JSONObject source;
    private final Map<String, JSONObject> templates = new LinkedHashMap<>();
    public RecipeCatalogue(JSONObject value) throws Exception {
        if (!value.getString("schema").equals("lma.recipe-catalogue/1")) throw new IllegalArgumentException("Unknown recipe catalogue schema");
        source = DataFiles.copy(value); JSONArray list = source.getJSONArray("templates");
        if (list.length() > 128) throw new IllegalArgumentException("Too many component templates");
        for (int i = 0; i < list.length(); i++) {
            JSONObject template = list.getJSONObject(i); String id = ModelBundle.key(template.getString("id"));
            if (templates.put(id, template) != null) throw new IllegalArgumentException("Duplicate recipe template");
            Set<String> roles = new HashSet<>(); JSONArray requirements = template.getJSONArray("requirements"), fixed = template.getJSONArray("fixedComponents");
            if (requirements.length() < 1 || requirements.length() + fixed.length() > 64) throw new IllegalArgumentException("Invalid template component count");
            for (int r = 0; r < requirements.length(); r++) {
                JSONObject item = requirements.getJSONObject(r); if (!roles.add(ModelBundle.key(item.getString("role"))) || item.getJSONArray("formats").length() == 0) throw new IllegalArgumentException("Invalid component requirement");
            }
            RecipeSuggestions.validate(template);
            if (!roles.contains(template.getString("primaryRole"))) throw new IllegalArgumentException("Template primary role must be selectable");
            for (int r = 0; r < fixed.length(); r++) if (!roles.add(ModelBundle.key(fixed.getJSONObject(r).getString("role")))) throw new IllegalArgumentException("Duplicate fixed role");
        }
    }
    public JSONArray list() throws Exception { return new JSONArray(source.getJSONArray("templates").toString()); }
    public JSONObject template(String id) {
        JSONObject value = templates.get(ModelBundle.key(id));
        if (value == null) throw new IllegalArgumentException("Unknown signed-App component recipe"); return DataFiles.copy(value);
    }
    public JSONObject requirement(String id, String role) throws Exception {
        JSONArray list = template(id).getJSONArray("requirements");
        for (int i = 0; i < list.length(); i++) if (list.getJSONObject(i).getString("role").equals(role)) return list.getJSONObject(i);
        throw new IllegalArgumentException("This recipe does not accept the selected component role");
    }
    public void accept(String id, String role, JSONObject asset) throws Exception {
        JSONObject rule = requirement(id, role); boolean format = false; JSONArray formats = rule.getJSONArray("formats");
        for (int i = 0; i < formats.length(); i++) if (formats.getString(i).equals(asset.getString("format"))) format = true;
        if (!format || !asset.optString("blocked").isEmpty()) throw new IllegalArgumentException("文件格式或校验信息不符合这个组件角色，请选择配套资产");
    }
    public ModelBundle compose(String id, JSONObject bindings) throws Exception {
        JSONObject template = template(id), definition = template.getJSONObject("definition"), primary = bindings.getJSONObject(template.getString("primaryRole"));
        for (Iterator<String> it = bindings.keys(); it.hasNext();) { String role = it.next(); accept(id, role, bindings.getJSONObject(role)); }
        JSONArray components = new JSONArray(), requirements = template.getJSONArray("requirements"), fixed = template.getJSONArray("fixedComponents");
        for (int i = 0; i < requirements.length(); i++) {
            JSONObject rule = requirements.getJSONObject(i); String role = rule.getString("role");
            if (!bindings.has(role)) { if (rule.optBoolean("required", true)) throw new IllegalArgumentException("请先选择全部必需组件：" + role); else continue; }
            JSONObject asset = bindings.getJSONObject(role), component = new JSONObject().put("role", role);
            for (String field : Arrays.asList("path", "repository", "revision", "url", "format", "bytes", "sha256", "gitBlobSha1")) if (asset.has(field)) component.put(field, asset.get(field));
            if (requirement(id, role).has("provides")) component.put("provides", DataFiles.copy(requirement(id, role)).getJSONArray("provides"));
            component.put("importPath", role + "/" + component.getString("path")); components.put(component);
        }
        for (int i = 0; i < fixed.length(); i++) { JSONObject component = DataFiles.copy(fixed.getJSONObject(i)); component.put("importPath", component.getString("role") + "/" + component.getString("path")); components.put(component); }
        // Matching aids do not change the identity of an existing model/component selection.
        JSONObject identityTemplate=DataFiles.copy(template);JSONArray identityRules=identityTemplate.getJSONArray("requirements");
        for(int i=0;i<identityRules.length();i++){identityRules.getJSONObject(i).remove("matchFiles");identityRules.getJSONObject(i).remove("matchSibling");}
        JSONObject identity = new JSONObject().put("template", identityTemplate).put("components", components);
        String digest = Protocol.hex(MessageDigest.getInstance("SHA-256").digest(DataFiles.canonical(identity).getBytes(StandardCharsets.UTF_8)));
        String bundleId = "hfb_" + digest.substring(0, 40), repository = primary.getString("repository");
        String display = repository.substring(repository.indexOf('/') + 1) + " · " + template.getString("name");
        if (display.length() > 160) display = display.substring(0, 160);
        JSONObject manifest = DataFiles.copy(definition).put("schema", ModelBundle.SCHEMA_V2).put("id", bundleId).put("modelId", bundleId).put("recipeId", id)
                .put("name", display).put("description", "用户从固定 HF 版本明确选择的组件配方；架构与实际手机执行尚未验证。")
                .put("components", components).put("catalogue", false).put("sourceUrl", "https://huggingface.co/" + repository)
                .put("license", new JSONObject().put("name", "请分别核对模型与各组件许可").put("url", "https://huggingface.co/" + repository))
                .put("evidence", new JSONObject().put("status", "user_selected_hf_components_not_device_tested").put("physicalDeviceTests", 0).put("architectureVerified", false));
        JSONObject hint = primary.optJSONObject("uncensored");
        manifest.put("uncensored", new JSONObject().put("declared", false).put("detected", hint != null && hint.optBoolean("detected")).put("basis", "repository-metadata").put("refusalRateTested", false));
        return new ModelBundle(manifest);
    }
}
