package com.lma.app.core;

import org.json.*;

/** Bounded, explicit-export observations. Never includes prompts, paths, keys or model settings. */
public final class RuntimeDiagnostics {
    private RuntimeDiagnostics() {}
    private static JSONObject select(JSONObject source,String...keys)throws Exception{
        JSONObject out=new JSONObject();if(source==null)return out;
        for(String key:keys)if(source.has(key)){
            Object value=source.get(key);
            if(value instanceof Number||value instanceof Boolean||value==JSONObject.NULL)out.put(key,value);
            else if(value instanceof String)out.put(key,((String)value).substring(0,Math.min(160,((String)value).length())));
        }return out;
    }
    private static JSONObject measurements(JSONObject source)throws Exception{
        JSONObject out=select(source,"schema","elapsedMs","memoryScope","peakResidentBytes","memorySource","platform");
        out.put("qualityAssessed",false);
        JSONArray stages=source.optJSONArray("stages"),clean=new JSONArray();
        if(stages!=null)for(int i=0;i<Math.min(64,stages.length());i++){
            JSONObject stage=stages.optJSONObject(i);if(stage!=null)clean.put(select(stage,"stage","elapsedMs"));
        }
        return out.put("stages",clean);
    }
    public static JSONObject report(JSONObject state,String version)throws Exception{
        JSONObject r=new JSONObject().put("schema","lma.runtime-diagnostics/1").put("appVersion",version)
          .put("createdAt",System.currentTimeMillis()).put("assurance","observations_not_quality_or_background_endurance_acceptance")
          .put("device",select(state.optJSONObject("device"),"name","android","sdk","totalMemory","availableMemory","freeStorage",
            "batteryExempt","powerSaveMode","deviceIdle","interactive","backgroundRestricted","notificationsEnabled"));
        JSONArray jobs=state.optJSONArray("jobs"),observations=new JSONArray();
        if(jobs!=null)for(int i=Math.max(0,jobs.length()-64);i<jobs.length();i++){
            JSONObject job=jobs.getJSONObject(i),row=select(job,"id","bundleId","state","stage","createdAt","startedAt","finishedAt");
            JSONObject req=job.optJSONObject("request");if(req!=null)row.put("type",req.optString("type"));
            JSONObject exec=job.optJSONObject("engineExecution");
            if(exec!=null){
                JSONObject worker=select(exec,"pipeline","backend");
                if(exec.optJSONObject("runtimeMeasurements")!=null)worker.put("runtimeMeasurements",measurements(exec.getJSONObject("runtimeMeasurements")));
                row.put("worker",worker);
            }
            JSONObject resources=job.optJSONObject("runtimeResources");
            if(resources!=null)row.put("systemResources",select(resources,"status","samples","probeErrors","startedAt","endedAt","minimumAvailableRamBytes","minimumAvailableStorageBytes","maximumThermalStatus","thermalKnown","stopCode","scope"));
            long start=job.optLong("startedAt"),end=job.optLong("finishedAt");if(start>0&&end>=start)row.put("wallElapsedMs",end-start);
            observations.put(row);
        }
        r.put("jobs",observations);return r;
    }
}
