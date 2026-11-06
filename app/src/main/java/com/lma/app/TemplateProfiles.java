package com.lma.app;

import com.lma.app.core.DataFiles;
import org.json.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/** Reviewed, weight-bound template repairs. Never changes weights or saved parameters. */
public final class TemplateProfiles {
    private static final Map<String, JSONObject> states = new ConcurrentHashMap<>();
    private static final java.util.concurrent.atomic.AtomicLong revision = new java.util.concurrent.atomic.AtomicLong();
    public static long revision() { return revision.get(); }
    private static void publish(String id, JSONObject state) { states.put(id, state); revision.incrementAndGet(); }
    private TemplateProfiles() {}
    private static String read(InputStream in, int limit) throws IOException { return new String(com.lma.app.core.ToolReply.read(in, limit), StandardCharsets.UTF_8); }
    public static String hash(String text) throws Exception {
        return com.lma.app.core.Protocol.hex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
    }
    public static JSONObject status(String id) throws Exception {
        JSONObject state = states.get(id);
        return state == null ? new JSONObject().put("state", "not_loaded").put("modelQuality", "unverified") : new JSONObject(state.toString());
    }
    public static void clear(String id) { states.remove(id); }
    public static final class Selection {
        final File file; final JSONObject identity;
        Selection(File file, JSONObject identity) { this.file = file; this.identity = identity; }
        public void command(List<String> command) { if (file != null) { command.add("--chat-template-file"); command.add(file.getAbsolutePath()); } }
        public JSONObject identity() throws Exception { return new JSONObject(identity.toString()); }
    }
    public static Selection resolve(LmaApp app, String id, File weight, String expectedSha, DataFiles.Check check) throws Exception {
        check.run(); String embedded = GgufMetadata.chatTemplate(weight), embeddedHash = hash(embedded);
        JSONObject identity = new JSONObject().put("state", "embedded_unverified").put("embeddedTemplateSha256", embeddedHash)
            .put("effectiveTemplateSha256", embeddedHash).put("weightBytes", weight.length()).put("modelQuality", "unverified");
        JSONArray profiles;
        try (InputStream in = app.getAssets().open("chat-template-profiles.json")) { profiles = new JSONObject(read(in, 256 * 1024)).getJSONArray("profiles"); }
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.getJSONObject(i);
            if (!expectedSha.equals(profile.getString("weightSha256")) || weight.length() != profile.getLong("weightBytes")) continue;
            // A changed/foreign embedded template is not silently replaced by a family guess.
            if (!embeddedHash.equals(profile.getString("embeddedTemplateSha256"))) {
                identity.put("state", "identity_mismatch"); publish(id, identity);
                throw new IOException("模型的内置模板与已审核修复不一致；未替换权重或参数");
            }
            if (!GgufMetadata.read(weight).optString("architecture").equals(profile.getString("architecture"))) throw new IOException("Template profile architecture mismatch");
            File directory = new File(app.getFilesDir(), "chat-template-profiles"); if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create template cache");
            File receipt = new File(directory, com.lma.app.core.Protocol.safeId(id) + "-weight.json");
            String key = weight.getCanonicalPath() + ":" + weight.length() + ":" + weight.lastModified() + ":" + expectedSha;
            JSONObject prior = new JSONObject();
            if (receipt.isFile()) try (InputStream in = new FileInputStream(receipt)) { prior = new JSONObject(read(in, 8192)); } catch (Exception ignored) {}
            if (!key.equals(prior.optString("key"))) {
                if (!DataFiles.sha256(weight, check).equals(expectedSha)) throw new IOException("模型文件 SHA256 与模板修复绑定不符；未改动文件");
                try (OutputStream out = new FileOutputStream(receipt)) { out.write(new JSONObject().put("key", key).toString().getBytes(StandardCharsets.UTF_8)); }
            }
            String source; try (InputStream in = app.getAssets().open(profile.getString("asset"))) { source = read(in, 1024 * 1024); }
            if (!hash(source).equals(profile.getString("sha256"))) throw new IOException("Template asset identity mismatch");
            File target = new File(directory, profile.getString("sha256") + ".jinja");
            if (!target.isFile() || !DataFiles.sha256(target, check).equals(profile.getString("sha256"))) {
                try (OutputStream out = new FileOutputStream(target)) { out.write(source.getBytes(StandardCharsets.UTF_8)); }
            }
            identity.put("profile", profile.getString("id")).put("source", profile.getJSONObject("source"))
                .put("effectiveTemplateSha256", profile.getString("sha256")).put("weightSha256", expectedSha).put("state", "profile_selected");
            publish(id, identity); check.run(); return new Selection(target, identity);
        }
        publish(id, identity); return new Selection(null, identity);
    }
    /** Validates the actual running server, not merely the selected command-line file. */
    public static void verify(String id, Selection selection, JSONObject props, JSONObject probe) throws Exception {
        String effective = props.optString("chat_template");
        JSONObject state = selection.identity();
        boolean matches = !effective.isEmpty() && hash(effective).equals(state.getString("effectiveTemplateSha256"));
        if (selection.file != null && !matches) throw new IOException("本机引擎生效模板与模型加载记录不一致");
        if (!effective.isEmpty()) state.put("effectiveTemplateSha256", hash(effective));
        state.put("effectiveMatchesSelection", matches).put("embeddedMatchesEffective", !effective.isEmpty() && hash(effective).equals(state.getString("embeddedTemplateSha256")));
        String prompt = probe.optString("prompt");
        JSONObject caps = props.optJSONObject("chat_template_caps");
        boolean rendered = prompt.contains("lma_template_probe_7e10") && prompt.contains("LMA_TOOL_DEFINITION_7e10");
        boolean supported = rendered && caps != null && caps.optBoolean("supports_tools") && caps.optBoolean("supports_tool_calls");
        state.put("state", supported ? "native_template_verified" : "tools_unavailable").put("toolDefinitionsRendered", rendered).put("toolParserReady", supported)
            .put("parser", "pinned_llama_autoparser");
        if (caps != null) state.put("nativeCaps", caps);
        publish(id, state);
    }
    public static JSONObject probe() throws Exception {
        return new JSONObject().put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", "Template readiness check")))
            .put("tools", new JSONArray().put(new JSONObject().put("type", "function").put("function", new JSONObject().put("name", "lma_template_probe_7e10").put("description", "LMA_TOOL_DEFINITION_7e10").put("parameters", new JSONObject().put("type", "object").put("properties", new JSONObject())))));
    }
    public static void admit(String id, JSONObject request) throws Exception {
        JSONArray tools = request.optJSONArray("tools"), messages = request.optJSONArray("messages");
        boolean required = tools != null && tools.length() > 0 && !"none".equals(request.opt("tool_choice"));
        if (messages != null) for (int i = 0; i < messages.length(); i++) {
            JSONObject message = messages.getJSONObject(i);
            required |= message.optString("role").equals("tool") || message.has("tool_calls");
        }
        if (!required) return;
        JSONObject state = states.get(id);
        if (state == null || !state.optBoolean("toolParserReady")) throw new com.lma.app.core.LocalHttp.Failure(422, "tool_template_unavailable", "当前模型的生效模板或工具解析器未就绪；请使用已审核模板，模型文件与参数未变", "tools");
    }
}
