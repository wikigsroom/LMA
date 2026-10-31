/* Shipped optional manifests and production UI, with explicitly synthetic bridge/files. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {installFixture} = require('./foundation-ui.cjs');
const bundles = JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/expansion-bundles.json'),'utf8')).bundles;
const legacy = JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models;
function cube() {
  const positions = [-1,-1,-1,1,-1,-1,1,1,-1,-1,1,-1,-1,-1,1,1,-1,1,1,1,1,-1,1,1];
  const indices = [0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,3,7,6,3,6,2,1,2,6,1,6,5,0,4,7,0,7,3];
  const bin=Buffer.alloc(positions.length*4+indices.length*2);
  positions.forEach((v,i)=>bin.writeFloatLE(v,i*4));indices.forEach((v,i)=>bin.writeUInt16LE(v,96+i*2));
  const doc={asset:{version:'2.0',generator:'LMA PROGRAM FIXTURE; not model output'},buffers:[{byteLength:bin.length}],bufferViews:[{buffer:0,byteLength:96},{buffer:0,byteOffset:96,byteLength:72}],accessors:[{bufferView:0,componentType:5126,count:8,type:'VEC3'},{bufferView:1,componentType:5123,count:36,type:'SCALAR'}],meshes:[{primitives:[{attributes:{POSITION:0},indices:1,mode:4}]}],nodes:[{mesh:0}],scenes:[{nodes:[0]}],scene:0};
  let json=Buffer.from(JSON.stringify(doc));json=Buffer.concat([json,Buffer.alloc((4-json.length%4)%4,32)]);
  const out=Buffer.alloc(28+json.length+bin.length);out.writeUInt32LE(0x46546c67);out.writeUInt32LE(2,4);out.writeUInt32LE(out.length,8);out.writeUInt32LE(json.length,12);out.writeUInt32LE(0x4e4f534a,16);json.copy(out,20);out.writeUInt32LE(bin.length,20+json.length);out.writeUInt32LE(0x004e4942,24+json.length);bin.copy(out,28+json.length);return out;
}
function install(data) {
  const f=window.__fixture;f.models=data.legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));f.bundles=data.bundles.map(manifest=>({id:manifest.id,manifest,installed:true,parameterSchema:manifest.parameters,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:manifest.components.reduce((n,c)=>n+c.bytes,0),remainingBytes:0,reusableBytes:manifest.components.reduce((n,c)=>n+c.bytes,0),components:manifest.components.map(c=>({...c,reusable:true,downloadable:true}))}}));
  f.localEngines=['sherpa_tts','audio_cpp','trellis_native'].map(engine=>({engine,available:true,deviceValidated:false}));
  const image={id:'expansion_input',available:true,bytes:100,origin:{kind:'imported',name:'物体参考图 · UI FIXTURE.png'},metadata:{mime:'image/png',width:256,height:256}};
  const audio={id:'expansion_voice',available:true,bytes:96044,origin:{kind:'imported',name:'参考音频 · UI FIXTURE.wav'},metadata:{mime:'audio/wav',sampleRate:24000,channels:1,durationMs:2000,samples:48000}};
  f.artifacts=[image,audio];f.jobs=[];f.taskDrafts=[];f.__drafts={};f.__revision=0;
  f.bundles.forEach(b=>{if(b.manifest.tasks.includes('audio'))b.inputSchemas={'speech.synthesize':{negativePrompt:false,roles:b.manifest.pipeline==='f5_v1'||b.manifest.pipeline==='omnivoice'?{reference_audio:{label:'24 kHz 单声道 WAV 参考音频',required:b.manifest.pipeline==='f5_v1',mimes:['audio/wav'],minDurationMs:1000,maxDurationMs:12000,maxBytes:8388608,transcript:{label:'参考音频对应文本',maxLength:4000}}}:{}}};});
  window.__handleFoundation=command=>{
    const b=f.bundles.find(v=>v.id===command.id);
    if(command.action==='saveBundleSettings'){b.config.values=command.settings;return b.config;}
    if(command.action==='preflightTask')return {canEnqueue:true,issues:[],warnings:[{message:'程序界面样例：未运行完整权重。'}]};
    if(command.action==='saveTaskDraft'){
      const current=f.__drafts[command.request.bundleId];if((current?current.revision:0)!==command.expectedRevision)throw Error('Draft conflict');
      const record={bundleId:command.request.bundleId,revision:++f.__revision,savedAt:Date.now(),request:JSON.parse(JSON.stringify(command.request))};record.request.allowUnmeasured=false;f.__drafts[record.bundleId]=record;
      f.taskDrafts=Object.values(f.__drafts).map(d=>({bundleId:d.bundleId,type:d.request.type,revision:d.revision,savedAt:d.savedAt,inputSummary:d.request.input.prompt}));return record;
    }
    if(command.action==='inspectTaskDraft')return f.__drafts[command.id];
    if(command.action==='submitTask'){const job={id:'expansion_job',state:'queued',createdAt:Date.now(),request:command.request,artifacts:[]};f.jobs=[job];return job;}
    if(command.action==='inspectArtifact')return f.artifacts.find(a=>a.id===command.id);
    if(command.action==='editArtifact')return {...f.artifacts.find(a=>a.id===command.id).provenance.request,allowUnmeasured:false};
    return {};
  };window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}) {
  // A preceding case restores its own snapshot, including its acknowledgement history.
  await page.waitForFunction(()=>window.LMA && window.__fixture);
  const original=await page.evaluate(()=>{window.__expansionPreviousHandler=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
  const glb=cube();await page.route('**/artifacts/expansion_result',route=>route.fulfill({contentType:'model/gltf-binary',body:glb}));
  const id=p=>bundles.find(b=>b.pipeline===p).id, tre=id('trellis2'), pix=id('pixal3d'), f5=id('f5_v1'), omni=id('omnivoice');
  const commands=action=>page.evaluate(action=>window.__commands.filter(c=>c.action===action),action);
  try {
    await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{bundles,legacy});
    const start=(await commands('downloadBundle')).length, submitStart=(await commands('submitTask')).length;
    await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
    assert.deepEqual(await page.locator('.model-card').evaluateAll(ns=>ns.map(n=>n.dataset.model)),['m08','m06','m01']);checked('Speech and 3D keep the original three recommendations in order');
    await page.locator('[data-filter="local"]').click();await page.locator('[data-task="audio"]').click();
    assert.equal(await page.locator('[data-bundle]').count(),6);checked('Six speech download choices are peers in the existing Local model list');
    assert.equal(await page.locator('#modelList .content-nsfw').count(),0);checked('Speech models do not acquire NSFW labels from architecture');
    await overflow(page,'Speech peers at 375px');await capture('01-speech-models.png','UI FIXTURE · Optional Kokoro / Melo / F5 / OmniVoice download choices');
    await page.locator('[data-bundle="'+omni+'"] [data-action="bundleSettings"]').count();
    await page.locator('[data-bundle="'+omni+'"] [data-action="bundleInfo"]').click();await page.locator('#modal [data-action="bundleSettings"]').click();
    assert.equal(await page.locator('[data-bundle-field="voiceMode"]').count(),1);checked('OmniVoice voice mode remains an editable per-model enum');
    await page.locator('[data-bundle-field="language"]').fill('zh');await page.locator('[data-bundle-field="voiceInstruction"]').fill('清晰、温和的中文声音');
    await page.locator('[data-bundle-field="maxAudioSeconds"]').fill('99999');await page.locator('[data-bundle-field="maxAudioSeconds"]').blur();
    assert.equal(await page.locator('[data-bundle-field="maxAudioSeconds"]').inputValue(),'120');checked('Speech duration protection clamps to the signed adapter limit');
    await page.locator('#bundleSettingsForm [type="submit"]').click();await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
    assert.equal(await page.evaluate(omni=>window.__fixture.bundles.find(b=>b.id===omni).config.values.language,omni),'zh');checked('Language and voice description persist only with the selected speech model');
    await page.locator('[data-bundle="'+f5+'"] [data-action="bundleUse"]').click();
    assert.equal(await page.locator('[name="negativePrompt"]:visible').count(),0);checked('F5 hides unsupported negative prompts');
    const reference=page.locator('#modal select').filter({has:page.locator('option[value="expansion_voice"]')});assert.equal(await reference.count(),1);checked('F5 accepts a local WAV reference through the shared artifact picker');
    await reference.selectOption('expansion_voice');assert((await page.locator('#modal').innerText()).includes('对应文本'));checked('F5 exposes a matching reference transcript field');
    await page.keyboard.press('Escape');await page.locator('[data-task="3d"]').click();
    assert.equal(await page.locator('[data-bundle]').count(),5);assert.equal(await page.locator('#modelList .task-3d').count(),5);checked('Five TRELLIS/Pixal component choices have a functional 3D tag');
    assert.equal((await commands('downloadBundle')).length,start);checked('Opening speech and 3D choices downloads no model or auxiliary data');
    await overflow(page,'3D model peers');await capture('02-3d-models.png','UI FIXTURE · Single-image TRELLIS.2 / Pixal3D routes');
    await page.locator('[data-bundle="'+tre+'"] [data-action="bundleUse"]').click();
    await page.locator('[data-action="meshSubmit"]').click();assert((await page.locator('#meshHint').innerText()).includes('参考图片'));checked('A 3D job cannot be submitted without its required image');
    await page.locator('#meshTaskForm [name="reference"]').selectOption('expansion_input');
    await page.locator('#meshTaskForm [name="steps"]').fill('9999');await page.locator('#meshTaskForm [name="steps"]').blur();assert.equal(await page.locator('#meshTaskForm [name="steps"]').inputValue(),'50');
    await page.locator('#meshTaskForm [name="resolution"]').fill('9999');await page.locator('#meshTaskForm [name="resolution"]').blur();assert.equal(await page.locator('#meshTaskForm [name="resolution"]').inputValue(),'1024');checked('Editable 3D presets return excessive values to hard maxima');
    await page.locator('#meshTaskForm [name="resolution"]').fill('512');await page.locator('#meshTaskForm [name="steps"]').fill('12');
    await page.locator('[data-action="meshSaveSettings"]').click();await page.waitForFunction(tre=>window.__fixture.bundles.find(b=>b.id===tre).config.values.steps===12,tre);checked('3D settings save under their selected model identity');
    await page.locator('[data-action="meshPreflight"]').click();await page.waitForFunction(()=>document.getElementById('meshHint').textContent.includes('检查通过'));assert.equal(await page.evaluate(()=>window.__fixture.jobs.length),0);checked('Preflight shows a program report without enqueueing or running a model');
    await page.locator('[data-action="meshDraft"]').click();await page.waitForFunction(()=>window.__fixture.taskDrafts.length===1);checked('3D image and parameters save as a revisioned per-model draft');
    await overflow(page,'3D task form');await capture('03-3d-form.png','UI FIXTURE · Local image, editable bounds, preflight and draft');
    await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="restoreTaskDraft"][data-id="'+tre+'"]').click();
    assert.equal(await page.locator('#meshTaskForm [name="reference"]').inputValue(),'expansion_input');assert.equal(await page.locator('#meshTaskForm [name="allowUnmeasured"]').isChecked(),false);checked('Draft restore keeps the image but requires fresh unmeasured-recipe consent');
    await page.locator('[data-action="meshSubmit"]').click();assert.equal((await commands('submitTask')).length,submitStart);checked('3D admission requires explicit consent before task creation');
    await page.locator('#meshTaskForm [name="allowUnmeasured"]').check();await page.locator('[data-action="meshSubmit"]').evaluate(b=>{b.click();b.click();});await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);await page.waitForSelector('.job-card');assert.equal((await commands('submitTask')).length,submitStart+1);checked('Repeated submit clicks create a single queue request');
    const request=(await commands('submitTask')).at(-1).request;assert.equal(request.type,'mesh.generate');assert.equal(request.input.artifacts[0].role,'reference_image');checked('The queue receives the production mesh task contract');
    await overflow(page,'3D task queue');await capture('04-3d-queue.png','UI FIXTURE · One queued local mesh task, not a model run');
    await page.evaluate(({bytes,request})=>{const f=window.__fixture;f.jobs[0].state='succeeded';f.jobs[0].artifacts=['expansion_result'];f.artifacts.push({id:'expansion_result',available:true,jobId:'expansion_job',bytes,origin:{kind:'generated'},metadata:{mime:'model/gltf-binary',vertices:8,triangles:12,textures:0},provenance:{execution:'PROGRAM FIXTURE; not model output',request}});window.LMA.receive(f);},{bytes:glb.length,request});
    await page.locator('.job-card [data-action="jobResults"]').click();await page.waitForFunction(()=>document.getElementById('glbPreviewStatus')?.textContent.includes('几何预览'));
    checked('A synthetic GLB renders in the production bounded WebGL preview');
    await page.locator('#modal [data-action="exportArtifact"][data-id="expansion_result"]').click();await page.locator('#modal [data-action="exportArtifactMetadata"][data-id="expansion_result"]').click();assert.equal((await commands('exportArtifact')).at(-1).id,'expansion_result');checked('GLB and generation-record exports keep the selected artifact identity');
    const geometry=await page.evaluate(base64=>{const data=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));const g=window.LMAGlbPreview.geometry(data.buffer);return {vertices:g.positions.length/3,indices:g.indices.length};},glb.toString('base64'));assert.deepEqual(geometry,{vertices:8,indices:36});checked('GLB geometry parser reads embedded vertices and triangle indices');
    const rejects=await page.evaluate(base64=>{const raw=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));const fail=fn=>{const a=raw.slice();fn(a,new DataView(a.buffer));try{window.LMAGlbPreview.geometry(a.buffer);return false;}catch(_){return true;}};return [fail((a,v)=>v.setUint32(0,0,true)),fail((a,v)=>v.setUint32(8,a.length+4,true)),fail((a,v)=>v.setFloat32(28+v.getUint32(12,true),NaN,true)),fail((a,v)=>v.setUint16(28+v.getUint32(12,true)+96,99,true))];},glb.toString('base64'));assert.deepEqual(rejects,[true,true,true,true]);checked('Preview rejects malformed, non-finite and out-of-bounds synthetic GLB data');
    await overflow(page,'GLB result controls');await capture('05-glb-preview.png','UI FIXTURE · Synthetic cube; GLB rotation and export controls');
    await page.locator('#modal [data-action="editArtifact"]').click();await page.waitForSelector('#meshTaskForm');assert.equal(await page.locator('#meshTaskForm [name="allowUnmeasured"]').isChecked(),false);checked('Editing a GLB result restores input without automatically rerunning it');
    await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="3d"]').click();await page.locator('[data-bundle="'+pix+'"] [data-action="bundleUse"]').click();
    await page.locator('#meshTaskForm [name="texture"]').click();await page.locator('#meshTaskForm [name="texture"]').dispatchEvent('change');assert.equal(await page.locator('#meshTaskForm [name="texture"]').isChecked(),false);checked('Pixal3D 512 automatically returns unsupported texture generation to off');
    await page.setViewportSize({width:320,height:720});await overflow(page,'320px editable 3D controls');await page.setViewportSize({width:375,height:812});
  } finally {
    await page.keyboard.press('Escape');await page.unroute('**/artifacts/expansion_result');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__expansionPreviousHandler;delete window.__expansionPreviousHandler;window.LMA.receive(f);},original);
    await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  }
};
