package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import org.json.*;
import java.util.*;
import java.util.concurrent.*;

/** Bounded real-device zero-model measurements. Reports numbers only, never snapshot contents. */
public final class DevicePerformance extends Instrumentation {
    private boolean allowExisting;
    private LmaApp app;
    private WebView web;
    private interface Task { Object run() throws Exception; }
    private WebView find(View view) {
        if (view instanceof WebView) return (WebView)view;
        if (view instanceof ViewGroup) { ViewGroup g=(ViewGroup)view;for(int i=0;i<g.getChildCount();i++){WebView w=find(g.getChildAt(i));if(w!=null)return w;} }
        return null;
    }
    private Object js(String source) throws Exception {
        CountDownLatch done=new CountDownLatch(1);String[] value={null};
        runOnMainSync(()->web.evaluateJavascript(source,r->{value[0]=r;done.countDown();}));
        if(!done.await(20,TimeUnit.SECONDS))throw new IllegalStateException("UI measurement callback timed out");
        return new JSONTokener(value[0]).nextValue();
    }
    private JSONObject measure(Task task,int count) throws Exception {
        List<Double> samples=new ArrayList<>();
        for(int i=0;i<count;i++){long start=SystemClock.elapsedRealtimeNanos();task.run();samples.add((SystemClock.elapsedRealtimeNanos()-start)/1e6);}
        List<Double> sorted=new ArrayList<>(samples);Collections.sort(sorted);double sum=0;for(double n:samples)sum+=n;
        return new JSONObject().put("samplesMs",new JSONArray(samples)).put("meanMs",sum/count).put("p50Ms",sorted.get(count/2)).put("p95Ms",sorted.get((int)Math.ceil(count*.95)-1));
    }
    private JSONObject heartbeat() throws Exception {
        Handler main=new Handler(Looper.getMainLooper());long[] last={0},max={0};int[] callbacks={0},over={0};boolean[] active={true};CountDownLatch started=new CountDownLatch(1),done=new CountDownLatch(1);
        Runnable tick=new Runnable(){@Override public void run(){long now=SystemClock.elapsedRealtime();if(last[0]!=0){long gap=now-last[0];max[0]=Math.max(max[0],gap);callbacks[0]++;if(gap>100)over[0]++;}last[0]=now;if(active[0])main.postDelayed(this,16);}};
        main.post(()->{tick.run();started.countDown();});if(!started.await(20,TimeUnit.SECONDS))throw new IllegalStateException("Main thread did not respond");
        long begin=SystemClock.elapsedRealtime();for(int i=0;i<8;i++){app.emit();Thread.sleep(300);}
        main.post(()->{active[0]=false;main.removeCallbacks(tick);done.countDown();});if(!done.await(40,TimeUnit.SECONDS))throw new IllegalStateException("Main-thread sampling timed out");
        return new JSONObject().put("durationMs",SystemClock.elapsedRealtime()-begin).put("callbacks",callbacks[0]).put("maximumGapMs",max[0]).put("gapsOver100Ms",over[0]).put("broadcasts",8);
    }
    @Override public void onCreate(Bundle args){super.onCreate(args);allowExisting="true".equals(args.getString("allow_existing_models"));start();}
    @Override public void onStart(){
        JSONObject result=new JSONObject();
        try{
            app=(LmaApp)getTargetContext().getApplicationContext();
            Activity activity=startActivitySync(new Intent(Intent.ACTION_MAIN).setClassName(getTargetContext(),"com.lma.app.MainActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            runOnMainSync(()->web=find(activity.getWindow().getDecorView()));
            if(web==null)throw new IllegalStateException("WebView absent");
            long deadline=SystemClock.elapsedRealtime()+40000;
            while(!Boolean.TRUE.equals(js("Boolean(window.LMA&&document.querySelectorAll('#modelList .model-card').length)"))){if(SystemClock.elapsedRealtime()>deadline)throw new IllegalStateException("Catalogue not ready");Thread.sleep(100);}
            JSONObject snapshot=app.snapshot();JSONArray models=snapshot.getJSONArray("models"),bundles=snapshot.getJSONArray("bundles");
            for(int i=0;i<models.length();i++)if(!allowExisting&&models.getJSONObject(i).optBoolean("installed"))throw new IllegalStateException("Zero-model measurement requires no installed weights");
            for(int i=0;i<bundles.length();i++)if(!allowExisting&&bundles.getJSONObject(i).optBoolean("installed"))throw new IllegalStateException("Zero-model measurement requires no installed bundles");
            if(app.generating||app.textRequestBusy||app.jobHost!=null&&app.jobHost.busy())throw new IllegalStateException("Generation is active");
            result.put("existingModelsPreserved",allowExisting).put("generationIdle",true);
            result.put("version",snapshot.getString("version")).put("physicalDevice",true).put("modelInference",false).put("completeWeightsDownloaded",false)
                .put("device",new JSONObject().put("model",android.os.Build.MODEL).put("api",android.os.Build.VERSION.SDK_INT).put("soc",android.os.Build.SOC_MODEL))
                .put("bundleCount",bundles.length()).put("snapshotBytes",snapshot.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
            result.put("snapshot",measure(()->app.snapshot().toString(),7));
            result.put("bundleSnapshot",measure(()->app.bundles.snapshot(),5));
            result.put("mainThread",heartbeat());
            // Execute public UI methods only. Opaque bundled frontend sources are never inspected.
            js("window.__lmaPerfState="+snapshot.toString()+";document.querySelector('.nav-item[data-tab=models]').click();document.querySelector('[data-filter=recommended]').click();document.querySelector('[data-task=any]').click()");
            Object rendering=js("(function(){var ui=window.LMAFoundation,original=ui.views,views=0,mutations=0,samples=[],observer=new MutationObserver(function(rs){mutations+=rs.length;});ui.views=function(){views++;return original.apply(this,arguments);};observer.observe(document.querySelector('.app-shell'),{subtree:true,childList:true,attributes:true,characterData:true});try{for(var i=0;i<12;i++){var t=performance.now();window.LMA.receive(window.__lmaPerfState);samples.push(performance.now()-t);mutations+=observer.takeRecords().length;}return JSON.stringify({samplesMs:samples,viewsCalls:views,mutations:mutations,updates:12,cards:document.querySelectorAll('#modelList .model-card').length});}finally{observer.disconnect();ui.views=original;delete window.__lmaPerfState;}})()");
            result.put("uiReceive",new JSONObject(String.valueOf(rendering)));
            result.put("status","passed");
        }catch(Throwable error){try{result.put("status","failed").put("error",error.getClass().getSimpleName()+": "+error.getMessage());}catch(Exception ignored){}}
        Bundle output=new Bundle();output.putString("lma_performance",result.toString());finish(Activity.RESULT_OK,output);
    }
}
