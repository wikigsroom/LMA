package com.lma.app;
import com.lma.app.core.*;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Tiny GGUF/header fixtures only; actual native rendering is a separate gate. */
public final class TemplateProfilesTest {
    interface Action { void run() throws Exception; }
    static void number(OutputStream out, long n, int bytes) throws IOException { for (int i=0;i<bytes;i++) out.write((int)(n >>> (i*8)) & 255); }
    static void string(OutputStream out, String s) throws IOException { byte[] b=s.getBytes(StandardCharsets.UTF_8); number(out,b.length,8);out.write(b); }
    static void entry(OutputStream out, String key, String value) throws IOException { string(out,key);number(out,8,4);string(out,value); }
    static void check(boolean b, String label, List<String> checks) { if(!b) throw new AssertionError(label);checks.add(label); }
    static void rejects(Action a, String label, List<String> checks) throws Exception { try {a.run();throw new AssertionError(label);}catch(IOException expected){checks.add(label);} }
    public static List<String> run(Path work, Path sourceAssets, Path libraries) throws Exception {
        List<String> checks=new ArrayList<>();Path dir=work.resolve("template-profile-fixtures"), assets=dir.resolve("assets");Files.createDirectories(assets);
        String original=new String(Files.readAllBytes(sourceAssets.resolve("chat-templates/dolphin3-chatml-tools-v1.jinja")), StandardCharsets.UTF_8);
        String embedded="{{ messages }}";Path weight=dir.resolve("tiny.gguf");
        try(OutputStream out=Files.newOutputStream(weight)) {number(out,0x46554747L,4);number(out,3,4);number(out,0,8);number(out,3,8);entry(out,"general.architecture","llama");string(out,"llama.context_length");number(out,4,4);number(out,131072,4);entry(out,"tokenizer.chat_template",embedded);}
        check(GgufMetadata.chatTemplate(weight.toFile()).equals(embedded),"Bounded GGUF template reader skips unrelated values and reads actual UTF-8 metadata",checks);
        check(GgufMetadata.read(weight.toFile()).getInt("contextLength")==131072,"Template inspection preserves the model context metadata",checks);
        JSONObject profile=new JSONObject().put("id","fixture-profile").put("architecture","llama").put("weightSha256",DataFiles.sha256(weight.toFile())).put("weightBytes",Files.size(weight)).put("embeddedTemplateSha256",TemplateProfiles.hash(embedded)).put("asset","fixture.jinja").put("sha256",TemplateProfiles.hash(original)).put("source",new JSONObject().put("fixture",true));
        Path manifest=assets.resolve("chat-template-profiles.json");Files.write(manifest,new JSONObject().put("profiles",new JSONArray().put(profile)).toString().getBytes(StandardCharsets.UTF_8));Files.write(assets.resolve("fixture.jinja"),original.getBytes(StandardCharsets.UTF_8));
        LmaApp app=new LmaApp(dir.resolve("app").toFile(),assets.toFile(),libraries.toFile());
        String beforeHash=DataFiles.sha256(weight.toFile());app.prefs.edit().putInt("context",131072).apply();
        TemplateProfiles.Selection selected=TemplateProfiles.resolve(app,"fixture",weight.toFile(),beforeHash,()->{});
        List<String> command=new ArrayList<>();selected.command(command);
        check(command.size()==2&&command.get(0).equals("--chat-template-file"),"Reviewed identity selects an explicit native template file",checks);
        check(DataFiles.sha256(weight.toFile()).equals(beforeHash)&&app.prefs.getInt("context",0)==131072,"Repair does not change model bytes or the saved 131072 context",checks);
        JSONObject request=TemplateProfiles.probe();
        rejects(()->TemplateProfiles.admit("fixture",request),"Selected profile alone is not declared tool-ready",checks);
        rejects(()->TemplateProfiles.verify("fixture",selected,new JSONObject().put("chat_template","wrong"),new JSONObject().put("prompt","")),"An ineffective native override fails loading explicitly",checks);
        TemplateProfiles.verify("fixture",selected,new JSONObject().put("chat_template",original),new JSONObject().put("prompt","tools were omitted"));
        rejects(()->TemplateProfiles.admit("fixture",request),"A native renderer that drops definitions cannot admit tool requests",checks);
        JSONObject rendered = new JSONObject().put("prompt","lma_template_probe_7e10 LMA_TOOL_DEFINITION_7e10");
        TemplateProfiles.verify("fixture",selected,new JSONObject().put("chat_template",original),rendered);
        rejects(()->TemplateProfiles.admit("fixture",request),"Rendered definitions alone cannot admit tools without a native tool-call parser",checks);
        JSONObject props = new JSONObject().put("chat_template",original).put("chat_template_caps",new JSONObject().put("supports_tools",true).put("supports_tool_calls",true));
        TemplateProfiles.verify("fixture",selected,props,rendered);TemplateProfiles.admit("fixture",request);
        check(TemplateProfiles.status("fixture").getBoolean("toolDefinitionsRendered"),"Effective template plus rendered definition establishes template readiness only",checks);
        check(TemplateProfiles.status("fixture").getBoolean("effectiveMatchesSelection") && !TemplateProfiles.status("fixture").getBoolean("embeddedMatchesEffective"),"Diagnostics distinguish selected override identity from the different original embedded template",checks);
        JSONObject exposed=TemplateProfiles.status("fixture");exposed.put("state","tampered");check(!TemplateProfiles.status("fixture").getString("state").equals("tampered"),"Published template status is a detached copy",checks);
        TemplateProfiles.Selection unknown=TemplateProfiles.resolve(app,"unknown",weight.toFile(),"",()->{});List<String> unknownCommand=new ArrayList<>();unknown.command(unknownCommand);
        check(unknownCommand.isEmpty(),"Unknown weights never receive a guessed family-wide override",checks);
        JSONObject history=new JSONObject().put("messages",new JSONArray().put(new JSONObject().put("role","tool").put("tool_call_id","fixture_call").put("content","42")));
        rejects(()->TemplateProfiles.admit("unknown",history),"Historical tool results need a working template even without current definitions",checks);
        profile.put("embeddedTemplateSha256",TemplateProfiles.hash("foreign template"));Files.write(manifest,new JSONObject().put("profiles",new JSONArray().put(profile)).toString().getBytes(StandardCharsets.UTF_8));
        rejects(()->TemplateProfiles.resolve(app,"foreign",weight.toFile(),beforeHash,()->{}),"A same-weight declaration with mismatched embedded metadata is not applied",checks);
        profile.put("embeddedTemplateSha256",TemplateProfiles.hash(embedded));Files.write(manifest,new JSONObject().put("profiles",new JSONArray().put(profile)).toString().getBytes(StandardCharsets.UTF_8));Files.write(assets.resolve("fixture.jinja"),"changed".getBytes(StandardCharsets.UTF_8));
        rejects(()->TemplateProfiles.resolve(app,"changed-asset",weight.toFile(),beforeHash,()->{}),"A template asset with changed bytes is rejected",checks);
        return checks;
    }
}
