package com.lma.app.core;

import org.json.*;
import java.util.*;

/** Strict OpenAI tool delta assembler. Ordinary assistant text is never parsed as a command. */
public final class ToolCalls {
    public static final int MAX_STEPS=8, MAX_REPAIRS=1;
    private final SortedMap<Integer,JSONObject> fragments=new TreeMap<>();
    private static final Map<String,String> OPERATIONS=new LinkedHashMap<>();
    static { OPERATIONS.put("image_generate","image.generate"); OPERATIONS.put("video_generate","video.generate"); OPERATIONS.put("speech_synthesize","speech.synthesize"); OPERATIONS.put("audio_generate","audio.generate"); OPERATIONS.put("mesh_generate","mesh.generate"); OPERATIONS.put("media_compose","media.compose"); OPERATIONS.put("task_status","task.status"); OPERATIONS.put("asset_select","asset.select"); }
    public void accept(JSONArray deltas) throws Exception {
        if(deltas==null) return;
        for(int i=0;i<deltas.length();i++) {
            JSONObject delta=deltas.getJSONObject(i); int index=delta.getInt("index");
            if(index<0||index>=MAX_STEPS) throw new IllegalArgumentException("工具步骤超过 8 步预算");
            JSONObject target=fragments.get(index);
            if(target==null) { target=new JSONObject().put("id","").put("type","function").put("function",new JSONObject().put("name","").put("arguments","")); fragments.put(index,target); }
            if(delta.has("type")&&!"function".equals(delta.getString("type"))) throw new IllegalArgumentException("只接受本地函数工具");
            if(delta.has("id")) { String incoming=delta.getString("id"); if(!target.getString("id").isEmpty()&&!target.getString("id").equals(incoming)) throw new IllegalArgumentException("流式工具编号发生冲突"); target.put("id",incoming); }
            JSONObject fn=delta.optJSONObject("function"); if(fn!=null) for(String key:new String[]{"name","arguments"}) if(fn.has(key)) {
                if(!(fn.get(key) instanceof String)) throw new IllegalArgumentException("工具片段必须为文字");
                JSONObject accumulated=target.getJSONObject("function"); String value=accumulated.getString(key)+fn.getString(key);
                if(value.length()>(key.equals("name")?80:32000)) throw new IllegalArgumentException("工具调用过长"); accumulated.put(key,value);
            }
        }
    }
    public JSONArray finish(int usedSteps) throws Exception {
        if(usedSteps<0||usedSteps+fragments.size()>MAX_STEPS) throw new IllegalArgumentException("计划最多自动执行 8 步，请编辑或新建计划");
        JSONArray result=new JSONArray(); Set<String> ids=new HashSet<>();
        for(JSONObject call:fragments.values()) {
            String id=call.getString("id"); if(!id.matches("[A-Za-z0-9_-]{1,128}")||!ids.add(id)) throw new IllegalArgumentException("工具调用缺少唯一编号");
            JSONObject fn=call.getJSONObject("function"); if(!OPERATIONS.containsKey(fn.getString("name"))) throw new IllegalArgumentException("未授权的本地工具："+fn.getString("name"));
            String raw=fn.getString("arguments"); if(raw.trim().isEmpty()) raw="{}"; JSONObject args=StrictJson.object(raw);
            if((fn.getString("name").equals("task_status")||fn.getString("name").equals("asset_select"))&&(args.length()!=1||!(args.opt("id") instanceof String)))throw new IllegalArgumentException("查询工具只接受一个已有编号");
            call.put("parsed",args).put("operation",OPERATIONS.get(fn.getString("name"))); result.put(DataFiles.copy(call));
        }
        return result;
    }
    public JSONArray raw()throws Exception{JSONArray out=new JSONArray();for(JSONObject call:fragments.values()){JSONObject copy=DataFiles.copy(call);copy.remove("parsed");copy.remove("operation");out.put(copy);}return out;}
    public static boolean canRepair(int used){return used>=0&&used<MAX_REPAIRS;}
    public static JSONObject request(JSONObject call,boolean consent) throws Exception {
        String type=call.getString("operation"); if(type.equals("task.status")||type.equals("asset.select")) throw new IllegalArgumentException("查询工具没有生成请求");
        JSONObject request=DataFiles.copy(call.getJSONObject("parsed"));
        if(request.has("allowUnmeasured")||request.has("type")) throw new IllegalArgumentException("工具不能自行授权运行或更改操作");
        request.put("type",type); if(!type.equals("media.compose")) request.put("allowUnmeasured",consent);
        return TaskInput.validate(request);
    }
    public static JSONArray definitions() throws Exception {
        JSONArray result=new JSONArray();
        for(Map.Entry<String,String> entry:OPERATIONS.entrySet()) {
            boolean query=entry.getValue().endsWith("status")||entry.getValue().endsWith("select");
            JSONObject properties=query?new JSONObject().put("id",new JSONObject().put("type","string")):
                new JSONObject().put("bundleId",new JSONObject().put("type","string")).put("input",new JSONObject().put("type","object")).put("parameters",new JSONObject().put("type","object"));
            result.put(new JSONObject().put("type","function").put("function",new JSONObject().put("name",entry.getKey()).put("description","On this Android phone only: "+entry.getValue()+". Use only the supplied installed model and artifact IDs. Never download assets.")
                .put("parameters",new JSONObject().put("type","object").put("properties",properties).put("required",query?new JSONArray().put("id"):new JSONArray().put("bundleId").put("input")).put("additionalProperties",false))));
        }
        return result;
    }
}
