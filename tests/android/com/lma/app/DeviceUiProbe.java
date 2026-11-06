package com.lma.app;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.graphics.Bitmap;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.View;
import android.view.MotionEvent;
import android.view.ViewGroup;
import android.webkit.WebView;
import java.io.File;
import java.io.FileOutputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.*;

/** Real installed WebView checks. No test bridge, model downloads or generation. */
public final class DeviceUiProbe extends Instrumentation {
    private WebView web;
    private Activity activity;
    private String mode;
    private final JSONArray checks=new JSONArray(), screenshots=new JSONArray();
    private WebView find(View v) {
        if(v instanceof WebView)return (WebView)v;
        if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++){WebView w=find(g.getChildAt(i));if(w!=null)return w;}}
        return null;
    }
    private Object js(String source)throws Exception {
        CountDownLatch done=new CountDownLatch(1);String[] result={null};
        runOnMainSync(()->web.evaluateJavascript(source,r->{result[0]=r;done.countDown();}));
        if(!done.await(20,TimeUnit.SECONDS))throw new IllegalStateException("WebView callback deadline");
        return new JSONTokener(result[0]).nextValue();
    }
    private void waitFor(String source)throws Exception {
        long until=SystemClock.elapsedRealtime()+30000;
        while(!Boolean.TRUE.equals(js("Boolean("+source+")"))){if(SystemClock.elapsedRealtime()>until)throw new IllegalStateException("UI condition: "+source);Thread.sleep(100);}
    }
    private void check(String name,String source)throws Exception {
        if(!Boolean.TRUE.equals(js("Boolean("+source+")")))throw new IllegalStateException(name);
        checks.put(name);
    }
    private void page(String name)throws Exception {
        js("document.querySelector('.nav-item[data-tab="+name+"]').click();"+(name.equals("tasks")?"document.querySelector('#jobSearch').scrollIntoView({block:'start'})":""));
        waitFor("document.querySelector('#page-"+name+"').classList.contains('active')");
    }
    private void theme(String name)throws Exception {
        page("settings");
        js("(function(){var s=document.querySelector('#settingsForm [name=theme]');s.value="+JSONObject.quote(name)+";s.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#settingsForm [type=submit]').click();})()");
        waitFor("document.querySelector('#settingsHint').textContent==='设置已保存'");
        check("Saved theme "+name,"document.documentElement.dataset.theme==="+JSONObject.quote(name.equals("system")?"dark":name));
    }
    private JSONObject preserved()throws Exception {
        return new JSONObject(String.valueOf(js("(function(){var s=JSON.parse(Android.getSnapshot());return JSON.stringify({version:s.version,models:(s.models||[]).filter(function(m){return m.installed;}).map(function(m){return {id:m.id,bytes:m.installedBytes};}),bundles:(s.bundles||[]).filter(function(m){return m.installed;}).map(function(m){return {id:m.id,bytes:m.installedBytes};}),preferences:{theme:s.settings.theme,port:s.settings.port,lan:s.settings.lan,source:s.settings.source,boot:s.settings.boot,autoLoad:s.settings.autoLoad},sessions:(s.chat.sessions||[]).length});})()")));
    }
    private void capture(String name)throws Exception {
        if(!mode.equals("capture"))return;
        // Crop OS notifications, clock and navigation; retain only the real app area.
        check("No visible API credential "+name,"!Array.from(document.querySelectorAll('.page.active input')).some(function(e){return e.type!=='password'&&/^lma_[a-f0-9]{48}$/.test(e.value)})");
        Thread.sleep(450);int[] bounds=new int[4];
        runOnMainSync(()->{web.getLocationOnScreen(bounds);bounds[2]=web.getWidth();bounds[3]=web.getHeight();});
        Bitmap raw=getUiAutomation().takeScreenshot();
        Bitmap cropped=Bitmap.createBitmap(raw,bounds[0],bounds[1],bounds[2],bounds[3]);
        File folder=new File(getTargetContext().getExternalFilesDir(null),"lma-ui-v100");folder.mkdirs();
        File file=new File(folder,name+".png");
        try(FileOutputStream out=new FileOutputStream(file)){cropped.compress(Bitmap.CompressFormat.PNG,100,out);}
        cropped.recycle();raw.recycle();screenshots.put(new JSONObject().put("file",file.getName()).put("x",bounds[0]).put("y",bounds[1]).put("width",bounds[2]).put("height",bounds[3]));
    }
    @Override public void onCreate(Bundle args){super.onCreate(args);mode=args.getString("mode","check");start();}
    @Override public void onStart(){
        JSONObject result=new JSONObject();Boolean originalLan=null;String originalTheme="";int originalOrientation=ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED;
        try{
            activity=startActivitySync(new Intent(Intent.ACTION_MAIN).setClassName(getTargetContext(),"com.lma.app.MainActivity").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            runOnMainSync(()->web=find(activity.getWindow().getDecorView()));
            waitFor("window.LMA&&window.Android&&document.querySelectorAll('#modelList .model-card').length");
            JSONObject before=preserved();result.put("before",before);
            if(!mode.equals("baseline")){
                waitFor("window.LMAMica");
                originalTheme=before.getJSONObject("preferences").optString("theme","dark");
                originalOrientation=activity.getRequestedOrientation();
                if(mode.equals("capture")){
                    originalLan=before.getJSONObject("preferences").getBoolean("lan");
                    if(originalLan){page("server");js("document.querySelector('#lanToggle').click()");waitFor("JSON.parse(Android.getSnapshot()).settings.lan===false");}
                }
                check("Actual native inset owner","document.documentElement.dataset.nativeInsets==='true'");
                check("Font scale propagated","document.documentElement.dataset.largeText===String(JSON.parse(Android.layoutInfo()).textScale>=1.5)");
                // An empty new conversation preserves all historical sessions.
                js("document.querySelector('[data-action=newChat]').click()");Thread.sleep(500);
                js("document.querySelector('#jobSearch').value='LMA-UI-1.0.0';document.querySelector('#jobSearch').dispatchEvent(new Event('input',{bubbles:true}))");
                for(String t:new String[]{"dark","light"}){
                    theme(t);if(mode.equals("capture"))Thread.sleep(3200);
                    for(String p:new String[]{"models","chat","tasks","server","settings"}){
                        page(p);
                        if(p.equals("models"))js("document.querySelector('[data-filter=recommended]').click();document.querySelector('[data-task=any]').click()");
                        check(t+" "+p+" has no horizontal overflow","document.documentElement.scrollWidth<=innerWidth+1&&document.querySelector('.page.active').scrollWidth<=document.querySelector('.page.active').clientWidth+1");
                        capture(t+"-"+p);
                        if(p.equals("server")){
                            check(t+" API page exposes independent running-model management","!!document.querySelector('#runningModelsPanel')&&document.querySelector('#runtimeAction').textContent==='运行管理'");
                            js("document.querySelector('#runtimeAction').click()");
                            check(t+" global runtime manager opens","document.querySelector('#modalTitle').textContent==='运行中的模型'");
                            capture(t+"-runtime");
                            boolean resident=Boolean.TRUE.equals(js("!!document.querySelector('#modal [data-action=stopTextModel]')"));
                            if(resident){
                                js("document.querySelector('#modal [data-action=stopTextModel]').click()");
                                check(t+" unload confirmation explains file retention","document.querySelector('#modalContent').textContent.includes('已下载文件')&&!!document.querySelector('#modal [data-command=stopEngine]')");
                                capture(t+"-unload-confirm");
                            }
                            js("document.querySelector('#modal .modal-actions [data-action=closeModal]')?document.querySelector('#modal .modal-actions [data-action=closeModal]').click():document.querySelector('#modal [data-action=closeModal]').click()");
                        }
                        if(p.equals("chat")){
                            check(t+" ordinary chat has no generation form","document.querySelector('#conversationOptions').hidden&&document.querySelector('#conversationContext').hidden&&document.querySelector('#conversationMode').value==='chat'");
                            check(t+" original empty prompts restored","document.querySelector('.chat-empty h2').textContent==='从一句话开始。'&&document.querySelectorAll('.suggestion').length===2");
                            js("document.querySelector('#chatInput').value='LMA UI 检查草稿';document.querySelector('#conversationMore').click()");
                            check(t+" creation sheet isolates chat","document.querySelector('.app-shell').inert&&!document.querySelector('#conversationOptions').hidden");
                            capture(t+"-chat-tools");
                            js("document.querySelector('#conversationMode').value='auto';document.querySelector('#conversationMode').dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('[data-action=conversationParameters]').click()");
                            js("document.querySelector('#modal [data-action=closeModal]').click();document.querySelector('#conversationMore').click()");
                            check(t+" nested sheets preserve mode and draft","document.querySelector('#conversationMode').value==='auto'&&document.querySelector('#chatInput').value==='LMA UI 检查草稿'");
                            js("document.querySelector('#modal [data-action=closeModal]').click();document.querySelector('[data-action=conversationChat]').click()");
                            check(t+" ordinary chat restores after creation","document.querySelector('#conversationContext').hidden&&document.querySelector('#conversationOptions').hidden&&!document.querySelector('.app-shell').inert");
                            js("document.querySelector('#chatInput').value='';document.querySelector('#chatInput').dispatchEvent(new Event('input',{bubbles:true}))");
                        }
                        if(p.equals("models")&&mode.equals("capture")){
                            js("document.querySelector('#modelList .model-card').scrollIntoView({block:'start'})");capture(t+"-model-cards");
                            js("document.querySelector('#page-models').scrollTop=0");
                        }
                    }
                    page("models");js("document.querySelector('[data-filter=local]').click()");
                    check(t+" local cards expose delete without opening details","Array.from(document.querySelectorAll('#modelList .bundle-card')).every(function(c){return !!c.querySelector('.model-footer [data-action=bundleRemove]')})");
                    boolean canDelete=Boolean.TRUE.equals(js("!!document.querySelector('#modelList .bundle-card [data-action=bundleRemove]:not(:disabled)')"));
                    if(canDelete)js("document.querySelector('#modelList .bundle-card [data-action=bundleRemove]:not(:disabled)').scrollIntoView({block:'center'})");
                    capture(t+"-local");
                    if(canDelete){
                        js("(function(){var b=document.querySelector('#modelList .bundle-card [data-action=bundleRemove]:not(:disabled)');window.__lmaDeleteProbeId=b.dataset.id;b.click()})()");
                        check(t+" outer delete confirms the selected model","document.querySelector('#modal [data-command=deleteBundle]').dataset.id===window.__lmaDeleteProbeId&&document.querySelector('.app-shell').inert&&document.querySelector('#modal .delete-target').textContent===JSON.parse(Android.getSnapshot()).bundles.find(function(b){return b.id===window.__lmaDeleteProbeId}).manifest.name");
                        capture(t+"-delete-confirm");
                        js("document.querySelector('#modal .modal-actions [data-action=closeModal]').click()");
                        check(t+" cancelled deletion preserves installed model","document.querySelector('#modalBackdrop').hidden&&JSON.parse(Android.getSnapshot()).bundles.some(function(b){return b.id===window.__lmaDeleteProbeId&&b.installed})");
                        js("delete window.__lmaDeleteProbeId");
                    }
                    Object has=js("Boolean(document.querySelector('[data-action=modelSettings]'))");
                    if(Boolean.TRUE.equals(has)){
                        js("document.querySelector('[data-action=modelSettings]').click()");waitFor("document.querySelector('#modelSettingsForm')");
                        check(t+" modal isolates background","document.querySelector('.app-shell').inert");capture(t+"-model-settings");
                        js("document.querySelector('#modal [data-action=closeModal]').click()");
                    }else if(Boolean.TRUE.equals(js("Boolean(document.querySelector('[data-action=bundleUse]:not(:disabled)'))"))){
                        js("document.querySelector('[data-action=bundleUse]:not(:disabled)').click()");
                        waitFor("!document.querySelector('#modalBackdrop').hidden");
                        check(t+" model task modal isolates background","document.querySelector('.app-shell').inert");capture(t+"-model-parameters");
                        js("document.querySelector('#modal [data-action=closeModal]').click()");
                    }
                }
                page("chat");
                js("document.querySelector('#chatInput').value='LMA UI draft';document.querySelector('#chatInput').focus()");
                JSONArray target=new JSONArray(String.valueOf(js("(function(){var e=document.querySelector('#chatInput');e.scrollIntoView({block:'center'});var r=e.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2,innerWidth]);})()")));
                int[] origin=new int[2];runOnMainSync(()->web.getLocationOnScreen(origin));
                float ratio=web.getWidth()/(float)target.getDouble(2),x=origin[0]+(float)target.getDouble(0)*ratio,y=origin[1]+(float)target.getDouble(1)*ratio;
                long tapTime=SystemClock.uptimeMillis();
                sendPointerSync(MotionEvent.obtain(tapTime,tapTime,MotionEvent.ACTION_DOWN,x,y,0));
                sendPointerSync(MotionEvent.obtain(tapTime,tapTime+100,MotionEvent.ACTION_UP,x,y,0));
                runOnMainSync(()->{web.requestFocus();((android.view.inputmethod.InputMethodManager)activity.getSystemService(Activity.INPUT_METHOD_SERVICE)).showSoftInput(web,0);});
                Thread.sleep(1400);
                check("IME reported by native host","document.documentElement.dataset.ime==='true'");
                check("Covered navigation hidden","getComputedStyle(document.querySelector('.bottom-nav')).display==='none'");
                runOnMainSync(()->((android.view.inputmethod.InputMethodManager)activity.getSystemService(Activity.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(web.getWindowToken(),0));Thread.sleep(800);
                js("document.querySelector('#chatInput').blur();document.querySelector('#chatInput').value=''");
                page("models");
                runOnMainSync(()->activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE));Thread.sleep(1500);
                check("Rotation keeps native page usable","innerWidth>innerHeight&&document.documentElement.scrollWidth<=innerWidth+1");capture("light-landscape");
                result.put("physicalDevice",true).put("modelInference",false).put("weightsDownloaded",false);
            }
            result.put("status","passed");
        }catch(Throwable e){try{result.put("status","failed").put("error",e.getClass().getSimpleName()+": "+e.getMessage());}catch(Exception ignored){}}
        finally{
            try{
                if(originalLan!=null){
                    page("server");boolean now=Boolean.TRUE.equals(js("JSON.parse(Android.getSnapshot()).settings.lan"));
                    if(now!=originalLan){js("document.querySelector('#lanToggle').click()");waitFor("JSON.parse(Android.getSnapshot()).settings.lan==="+originalLan);}
                }
                if(!originalTheme.isEmpty()){
                    // Restore the actual user preference, including system mode.
                    page("settings");js("(function(){var s=document.querySelector('#settingsForm [name=theme]');s.value="+JSONObject.quote(originalTheme)+";s.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#settingsForm [type=submit]').click();})()");
                    waitFor("document.querySelector('#settingsHint').textContent==='设置已保存'");
                    final int orientation=originalOrientation;runOnMainSync(()->activity.setRequestedOrientation(orientation));
                    js("document.querySelector('#jobSearch').value='';document.querySelector('#jobSearch').dispatchEvent(new Event('input',{bubbles:true}))");page("models");
                }
                result.put("after",preserved()).put("availableActions",js("Array.from(new Set(Array.from(document.querySelectorAll(\"[data-action]\")).map(function(e){return e.dataset.action})))")).put("checks",checks).put("screenshots",screenshots);
            }catch(Exception e){try{result.put("status","failed").put("restoreError",e.getClass().getSimpleName());}catch(Exception ignored){}}
        }
        Bundle out=new Bundle();out.putString("lma_ui",result.toString());finish(Activity.RESULT_OK,out);
    }
}
