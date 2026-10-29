/* Production pages and real Web Audio scheduling; PCM/bridge are explicit synthetic fixtures. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
module.exports=async function(page,checked,overflow,output,shot=async()=>{}){
  await page.waitForFunction(()=>!window.__commands.length||(window.__fixture.commandResults||[]).some(r=>r.requestId===window.__commands[window.__commands.length-1].requestId));
  await page.evaluate(installFixture);
  const recipe=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.find(t=>t.id==='moss_realtime_rq_cpu_v1');
  await page.evaluate(recipe=>{
    const f=window.__fixture,d=recipe.definition;
    const manifest={...d,schema:'lma.model-bundle/1',id:'ui_audio_rt',modelId:'ui_audio_rt',recipeId:recipe.id,name:'MOSS Realtime · 界面测试',components:['model','codec','tokenizer'].map((role,i)=>({role,path:role+'.gguf',format:'gguf',bytes:100,sha256:String(i).repeat(64)}))};
    f.bundles=[{id:manifest.id,manifest,installed:true,config:{values:Object.fromEntries(Object.entries(d.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:300,reusableBytes:300,remainingBytes:0,components:manifest.components.map(c=>({...c,reusable:true,downloadable:false}))}}];
    f.localEngines=[{engine:'moss_rq_native',available:true,deviceValidated:false}];f.jobs=[];f.artifacts=[];f.audioStreams=[];f.taskDrafts=[];
    window.__audioUI={available:1,terminal:false,expired:false,wrongSequence:false,chunkRequests:[],contexts:0,closed:0,scheduled:0,stopped:0};
    if(!window.__realAudioContext){window.__realAudioContext=window.AudioContext;window.AudioContext=function(){const context=new window.__realAudioContext(),state=window.__audioUI;state.contexts++;const close=context.close.bind(context);context.close=()=>{state.closed++;return close();};const create=context.createBufferSource.bind(context);context.createBufferSource=()=>{const source=create(),start=source.start.bind(source),stop=source.stop.bind(source);source.start=(...args)=>{state.scheduled++;return start(...args);};source.stop=(...args)=>{state.stopped++;return stop(...args);};return source;};return context;};}
    window.LMA.receive(f);
  },recipe);
  const route='**/audio-streams/**';
  await page.route(route,async r=>{
    const state=await page.evaluate(()=>window.__audioUI);if(state.expired)return r.fulfill({status:404,body:'Expired UI fixture'});
    const url=new URL(r.request().url()),parts=url.pathname.split('/').filter(Boolean);
    if(parts.length===2){const after=Number(url.searchParams.get('after')||0),chunks=[];for(let i=after;i<Math.min(state.available,after+32);i++)chunks.push({sequence:state.wrongSequence?i+1:i,startFrame:i*1920,frames:1920,bytes:3840});return r.fulfill({contentType:'application/json',body:JSON.stringify({jobId:'ui_audio_job',format:{schema:'lma.audio-stream/1',format:'pcm_s16le',sampleRate:24000,channels:1,maxFrames:48000,maxChunkFrames:1920},state:state.terminal?'succeeded':'streaming',nextSequence:state.available,frames:state.available*1920,chunks,cursor:after+chunks.length,transient:true,artifactId:state.terminal?'ui_audio_full':''})});}
    const sequence=Number(parts[2]);await page.evaluate(n=>window.__audioUI.chunkRequests.push(n),sequence);const pcm=Buffer.alloc(3840);for(let i=0;i<1920;i++)pcm.writeInt16LE(Math.round(Math.sin((sequence*1920+i)*2*Math.PI*220/24000)*3000),i*2);return r.fulfill({contentType:'application/octet-stream',body:pcm});
  });
  try{
    const before=await page.evaluate(()=>window.__commands.length);
    await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="audio"]').click();
    await page.locator('[data-bundle="ui_audio_rt"] [data-action="bundleInfo"]').click();await page.locator('#modalContent [data-action="bundleSettings"]').click();
    assert.equal(await page.locator('[data-bundle-field="streamAudio"]').isChecked(),false);checked('Realtime streaming is an explicit model setting, disabled by default');
    assert.match(await page.locator('#bundleSettingsForm').innerText(),/固定增益/);await page.locator('[data-bundle-field="streamAudio"]').check();await shot('01-model-setting.png','UI FIXTURE · Opt-in per-model streaming and gain explanation / 按模型选择流式试听');
    await page.locator('#bundleSettingsForm [type="submit"]').click();await page.waitForFunction(()=>window.__fixture.bundles[0].config.values.streamAudio===true);checked('Streaming choice is saved through the existing model settings flow');
    await page.evaluate(()=>{const f=window.__fixture;f.jobs=[{id:'ui_audio_job',createdAt:Date.now(),state:'running',stage:'generating_audio',request:{bundleId:'ui_audio_rt',type:'speech.synthesize',input:{prompt:'界面协议测试，非模型音质演示。'},parameters:{streamAudio:true}},artifacts:[]}];f.audioStreams=[{jobId:'ui_audio_job',state:'streaming',format:{schema:'lma.audio-stream/1',format:'pcm_s16le',sampleRate:24000,channels:1,maxFrames:48000,maxChunkFrames:1920},frames:1920,nextSequence:1,durationMs:80,transient:true,artifactId:''}];window.LMA.receive(f);});
    await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="filterJobs"][data-kind="all"]').click();await page.locator('[data-action="audioPreview"]').click();
    assert.equal((await page.evaluate(()=>window.__audioUI.chunkRequests)).length,0);checked('Opening the preview does not autoplay or fetch PCM');
    await overflow(page,'375px audio preview panel');await page.locator('[data-action="startAudioPreview"]').click();await page.waitForFunction(()=>window.__audioUI.scheduled>=1);
    assert.equal(await page.evaluate(()=>window.__fixture.artifacts.length),0);checked('Web Audio schedules an actual PCM block before a final artifact exists');
    await page.evaluate(()=>window.__audioUI.available=4);await page.waitForFunction(()=>window.__audioUI.scheduled>=4);assert.deepEqual((await page.evaluate(()=>window.__audioUI.chunkRequests)).slice(0,4),[0,1,2,3]);checked('Incremental polling plays chunks in sequence');
    await shot('02-incremental-playback.png','UI FIXTURE · Synthetic PCM scheduled while the task is running / 任务进行中逐段试听，非模型推理');
    await page.locator('[data-action="stopAudioPreview"]').click();await page.waitForFunction(()=>window.__audioUI.closed===window.__audioUI.contexts);assert.equal(await page.evaluate(()=>window.__fixture.jobs[0].state),'running');checked('Stopping playback closes its AudioContext and preserves generation');
    const received=await page.evaluate(()=>window.__audioUI.chunkRequests.length);await page.waitForTimeout(350);assert.equal(await page.evaluate(()=>window.__audioUI.chunkRequests.length),received);checked('Stopped previews release their polling and audio resources');
    await page.locator('[data-action="startAudioPreview"]').click();await page.waitForFunction(()=>window.__audioUI.contexts===2);await page.keyboard.press('Escape');await page.waitForFunction(()=>window.__audioUI.closed===2);checked('Closing the modal closes active audio resources');
    await page.locator('[data-action="audioPreview"]').click();await page.evaluate(()=>window.__audioUI.expired=true);await page.locator('[data-action="startAudioPreview"]').click();await page.waitForFunction(()=>document.getElementById('audioPreviewStatus').textContent.includes('失效'));assert.equal(await page.locator('[data-action="startAudioPreview"]').isDisabled(),false);checked('Expired transient data offers a retry without marking the task as succeeded');
    await shot('03-expired-preview.png','UI FIXTURE · Expired preview is distinct from the durable full result / 缓存失效提示与完整结果分开');
    await page.evaluate(()=>{window.__audioUI.expired=false;window.__audioUI.wrongSequence=true;});await page.locator('[data-action="startAudioPreview"]').click();await page.waitForFunction(()=>document.getElementById('audioPreviewStatus').textContent.includes('顺序无效'));checked('Out-of-order preview data stops playback');
    await page.keyboard.press('Escape');
    const commands=await page.evaluate(n=>window.__commands.slice(n),before);assert.equal(commands.filter(c=>/download|submitTask|cancelTask/i.test(c.action)).length,0);checked('Preview interactions never download, submit or cancel model tasks');
  }finally{await page.evaluate(()=>{window.LMAAudioPreview.close();window.__fixture.audioStreams=[];window.LMA.receive(window.__fixture);});await page.unroute(route);}
};
