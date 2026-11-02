package com.lma.app.core;
import org.json.*;
import java.util.*;

/** Built-in local edit, not a downloaded or advertised AI model. */
public final class CompositionSpec {
    public static final String ID="builtin_media";
    private CompositionSpec() {}
    public static InputSpec inputs() throws Exception {
        JSONObject roles=new JSONObject();
        roles.put("visual",rule("图片或原视频",true,new JSONArray().put("image/png").put("image/jpeg").put("video/mp4")));
        roles.put("voice",rule("WAV 配音",false,new JSONArray().put("audio/wav")));
        roles.put("music",rule("WAV 音乐 / 音效",false,new JSONArray().put("audio/wav")));
        return new InputSpec(roles).withNegativePrompt(false);
    }
    private static JSONObject rule(String label,boolean required,JSONArray mimes) throws Exception {return new JSONObject().put("label",label).put("required",required).put("mimes",mimes).put("maxBytes",ArtifactStore.MAX_INPUT_BYTES).put("maxPixels",4096L*4096).put("maxDurationMs",60000);}
    public static JSONObject validate(JSONObject source) throws Exception {
        for(Iterator<String> it=source.keys();it.hasNext();) if(!Arrays.asList("bundleId","type","input","parameters").contains(it.next())) throw new IllegalArgumentException("合成只接受受管素材与音量参数");
        if(!source.getString("bundleId").equals(ID)) throw new IllegalArgumentException("合成使用本机内置工具");
        JSONObject input=source.getJSONObject("input"); for(Iterator<String> it=input.keys();it.hasNext();) if(!Arrays.asList("prompt","artifacts").contains(it.next())) throw new IllegalArgumentException("合成不能接收文件路径或 URL");
        if(input.has("prompt")&&(!(input.get("prompt") instanceof String)||input.getString("prompt").length()>16000))throw new IllegalArgumentException("合成说明应为不超过 16000 字符的文字");
        JSONArray refs=input.getJSONArray("artifacts"); boolean visual=false,audio=false; Set<String> seen=new HashSet<>();
        for(int i=0;i<refs.length();i++) { JSONObject ref=refs.getJSONObject(i); if(ref.length()!=2) throw new IllegalArgumentException("素材仅接受角色与编号"); String role=ref.getString("role"); if(!Arrays.asList("visual","voice","music").contains(role)||!seen.add(role)) throw new IllegalArgumentException("合成角色不支持或重复"); ModelBundle.key(ref.getString("artifactId")); if(role.equals("visual")) visual=true; else audio=true; }
        if(!visual||!audio) throw new IllegalArgumentException("请选择一份画面和至少一份 WAV 声轨");
        JSONObject p=source.optJSONObject("parameters"); if(p==null)p=new JSONObject();
        for(Iterator<String> it=p.keys();it.hasNext();) if(!Arrays.asList("durationSeconds","voiceGain","musicGain").contains(it.next())) throw new IllegalArgumentException("未知合成参数");
        JSONObject values=new JSONObject(); for(String name:new String[]{"durationSeconds","voiceGain","musicGain"}) {
            double value=p.optDouble(name,name.equals("durationSeconds")?6:name.equals("musicGain")?.25:1);
            if(p.has(name)&&!(p.get(name) instanceof Number)||!Double.isFinite(value)||value<(name.equals("durationSeconds")?5.1:0)||value>(name.equals("durationSeconds")?60:2)) throw new IllegalArgumentException("合成时长应为 5.1–60 秒，音量为 0–2"); values.put(name,value);
        }
        if((!seen.contains("voice")||values.getDouble("voiceGain")==0)&&(!seen.contains("music")||values.getDouble("musicGain")==0)) throw new IllegalArgumentException("至少保留一条非静音声轨");
        return DataFiles.copy(source).put("parameters",values).put("input",DataFiles.copy(input).put("prompt",input.optString("prompt","本机媒体合成")));
    }
}
