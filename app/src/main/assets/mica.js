/* Window events only: no polling, catalogue observation or decorative render loop. */
(function () {
  'use strict';
  var root=document.documentElement, frame=0, nativeInfo={}, baselineHeight=0;
  function editable(){return document.activeElement && /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);}
  function layout(){
    frame=0;
    var viewport=window.visualViewport, height=viewport?viewport.height:window.innerHeight;
    if(!editable())baselineHeight=Math.max(height,window.innerHeight);
    var ime=nativeInfo.ime===true || (!nativeInfo.nativeInsets && editable() && baselineHeight-height>140);
    root.dataset.ime=String(!!ime);
    root.dataset.largeText=String(Number(nativeInfo.textScale||1)>=1.5);
    root.dataset.nativeInsets=String(nativeInfo.nativeInsets===true);
    // Native insets already resize the WebView. Only a browser fallback supplies height.
    if(!nativeInfo.nativeInsets && viewport)root.style.setProperty('--visible-height',height+'px');
  }
  function schedule(){if(!frame)frame=requestAnimationFrame(layout);}
  function receiveNative(info){
    if(typeof info==='string'){try{info=JSON.parse(info);}catch(_){return;}}
    Object.assign(nativeInfo,info||{});schedule();
  }
  function releaseMedia(){
    document.querySelectorAll('.page[hidden] audio,.page[hidden] video').forEach(function(el){el.pause();});
    if(window.LMAGlbPreview)window.LMAGlbPreview.close();
  }
  window.LMAMica={receiveNative:receiveNative,pageChanged:releaseMedia};
  window.addEventListener('resize',schedule,{passive:true});
  if(window.visualViewport)window.visualViewport.addEventListener('resize',schedule,{passive:true});
  document.addEventListener('focusin',schedule);
  document.addEventListener('focusout',schedule);
  document.addEventListener('visibilitychange',function(){
    if(document.hidden){document.querySelectorAll('audio,video').forEach(function(el){el.pause();});if(window.LMAGlbPreview)window.LMAGlbPreview.close();}
  });
  if(window.Android&&window.Android.layoutInfo){try{receiveNative(window.Android.layoutInfo());}catch(_){}}
  schedule();
}());
