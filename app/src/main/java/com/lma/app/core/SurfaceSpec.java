package com.lma.app.core;
import org.json.*;

/** Original RF adaptive extraction is selectable independently of model assets. */
public final class SurfaceSpec {
    private SurfaceSpec() {}
    public static JSONObject extend(JSONObject schema)throws Exception {
        JSONObject fields=schema.getJSONObject("fields");
        fields.put("extraction",new JSONObject().put("type","enum").put("label","曲面提取").put("default","uniform").put("values",new JSONArray().put("uniform").put("publisher_octree").put("publisher_flash")));
        fields.put("octreeDepth",new JSONObject().put("type","integer").put("label","分层提取目标深度").put("default",6).put("minimum",5).put("maximum",8).put("limitSource","application_guard"));
        fields.put("denseDepth",new JSONObject().put("type","integer").put("label","初始稠密网格深度（octree）").put("default",5).put("minimum",3).put("maximum",8).put("maximumFrom",new JSONObject().put("field","octreeDepth")).put("limitSource","application_guard"));
        return schema;
    }
}
