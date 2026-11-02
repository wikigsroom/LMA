package com.lma.app.core;
import org.json.*;
import java.util.*;

/** Dependency state machine. Admission is delegated to the one original persistent job queue. */
public final class WorkflowRunner {
    private WorkflowRunner(){}
    public interface Host {
        JSONObject lookup(String key)throws Exception;
        JSONObject get(String id)throws Exception;
        JSONObject admit(String session,JSONObject request,String key)throws Exception;
        String readText(String artifact)throws Exception;
        void cancel(String id)throws Exception;
    }
    public static boolean terminal(String state){return Arrays.asList("succeeded","failed","cancelled","interrupted").contains(state);}
    public static boolean advance(JSONObject chain,Host host)throws Exception{
        String before=chain.toString();JSONArray steps=chain.getJSONArray("steps");boolean cancel=chain.optBoolean("cancelRequested");
        for(int i=0;i<steps.length();i++) {
            JSONObject step=steps.getJSONObject(i);String status=step.getString("state");if(status.equals("succeeded"))continue;
            String key=chain.getString("id")+"_"+i+"_"+step.getInt("attempt");
            if(cancel){JSONObject prior=host.lookup(key);if(prior!=null&&prior.getString("state").equals("succeeded")){step.put("state","succeeded").put("artifacts",prior.getJSONArray("artifacts"));}else if(prior!=null&&!terminal(prior.getString("state"))){host.cancel(prior.getString("id"));step.put("state","cancelling");}else step.put("state","cancelled");continue;}
            if(!step.getString("jobId").isEmpty()){JSONObject job=host.get(step.getString("jobId"));step.put("state",job.getString("state")).put("artifacts",job.getJSONArray("artifacts")).put("error",job.optString("error"));continue;}
            if(!status.equals("ready"))continue;
            JSONArray dependencies=step.getJSONArray("dependsOn");boolean ready=true,blocked=false;
            for(int j=0;j<dependencies.length();j++){String s=steps.getJSONObject(dependencies.getInt(j)).getString("state");if(!s.equals("succeeded"))ready=false;if(Arrays.asList("failed","interrupted","cancelled","rejected","blocked").contains(s))blocked=true;}
            if(blocked){step.put("state","blocked").put("error","前置步骤未成功，保留已完成结果；请重试失败步骤");continue;}if(!ready)continue;
            try{
                JSONObject request=DataFiles.copy(step.getJSONObject("request"));JSONArray bindings=step.getJSONArray("bindings"),refs=request.getJSONObject("input").optJSONArray("artifacts");if(refs==null)refs=new JSONArray();
                for(int j=0;j<bindings.length();j++){JSONObject binding=bindings.getJSONObject(j);String artifact=steps.getJSONObject(binding.getInt("step")).getJSONArray("artifacts").getString(binding.optInt("output",0));if(binding.getString("role").equals("prompt"))request.getJSONObject("input").put("prompt",host.readText(artifact));else refs.put(new JSONObject().put("role",binding.getString("role")).put("artifactId",artifact));}
                if(refs.length()>0)request.getJSONObject("input").put("artifacts",refs);
                JSONObject job=host.lookup(key);if(job==null)job=host.admit(chain.getString("session"),TaskInput.validate(request),key);
                step.put("jobId",job.getString("id")).put("state",job.getString("state")).put("resolvedRequest",request);break;
            }catch(Exception error){step.put("state","rejected").put("error",error.getMessage()==null?"本机处理失败":error.getMessage());}
        }
        boolean success=true,active=false,failure=false;
        for(int i=0;i<steps.length();i++){String s=steps.getJSONObject(i).getString("state");success&=s.equals("succeeded");active|=Arrays.asList("ready","queued","loading","running","cancelling").contains(s);failure|=Arrays.asList("failed","rejected","interrupted","blocked").contains(s);}
        chain.put("state",cancel?(active?"cancelling":"cancelled"):success?"succeeded":active?"running":failure?"blocked":"ready");return !chain.toString().equals(before);
    }
}
