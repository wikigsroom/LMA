/* Production UI + explicit fixture bridge. No model downloads, voice or phone evidence. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
function installFixture(template){
  const f=window.__fixture,id='ui_soulx',definition=JSON.parse(JSON.stringify(template.definition));
  const files=['language.gguf','reference-s3.onnx','reference-s3.onnx.data','reference-speaker.onnx','reference-speaker.onnx.data','flow-encoder.onnx','flow-encoder.onnx.data','flow-estimator.onnx','flow-estimator.onnx.data','hift-f0.onnx','hift-f0.onnx.data','hift-spectrum.onnx','hift-spectrum.onnx.data','hift-source.f32'];
  const components=template.requirements.map((r,i)=>({role:r.role,path:files[i],format:r.formats[0],bytes:r.role==='hift_source'?40:1000,sha256:'a'.repeat(64)}));
  const manifest={...definition,id,modelId:id,recipeId:template.id,name:template.name+' · UI FIXTURE',description:template.help+' 界面夹具：未下载权重，未生成音频。',components,evidence:{physicalDeviceTests:0}};
  const values=Object.fromEntries(Object.entries(definition.parameters.fields).map(([k,v])=>[k,v.default]));
  const roles={};for(let i=1;i<=4;i++)roles['reference_s'+i]={label:'S'+i+' 参考音频（24 kHz 单声道 PCM16 / float32，1–15 秒）',required:i===1,mimes:['audio/wav'],maxBytes:1536000,minDurationMs:1000,maxDurationMs:15000,transcript:{label:'S'+i+' 参考音频原文',maxLength:4000}};
  f.bundles=f.bundles.filter(b=>b.id!==id).concat([{id,manifest,installed:true,config:{values},inputSchemas:{'speech.synthesize':{version:1,promptHelp:'单段文字默认 S1；多段每行 [S1] 原文 至 [S4] 原文。参考音频从 S1 开始连续选择，并填写实际原文。',roles}},plan:{installed:true,totalBytes:13040,remainingBytes:0,components}}]);
  f.localEngines=(f.localEngines||[]).filter(e=>e.engine!==definition.engine).concat([{engine:definition.engine,available:true,deviceValidated:false}]);
  for(let i=1;i<=4;i++)if(!f.artifacts.some(a=>a.id==='soulx_ref_'+i))f.artifacts.push({id:'soulx_ref_'+i,bytes:48044,metadata:{mime:'audio/wav',sampleRate:24000,channels:1,durationMs:1000},available:true,origin:{kind:'imported',name:'S'+i+' · 合成界面样本.wav'}});
  window.LMA.receive(f);return id;
}
module.exports=async function(page,checked,overflow){
  const template=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.find(t=>t.id==='soulx_podcast_cpu_v1');
  const id=await page.evaluate(installFixture,template);await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').click();assert.equal(await page.locator('.bundle-components details').count(),14);checked('SoulX exposes all fourteen explicit assets including trained source coefficients');
  await page.locator('#modal [data-action="bundleUse"][data-id="'+id+'"]').click();assert.equal(await page.locator('[data-input-role]').count(),4);assert.equal(await page.locator('[data-input-transcript]').count(),4);assert((await page.locator('#taskInputs').innerText()).includes('[S4]'));checked('Input schema exposes four paired references and escaped prompt help');
  await page.locator('[name="prompt"]').fill('[S1] 本地第一段。\n[S2] Local second turn.');await page.locator('[name="allowUnmeasured"]').check();
  await page.locator('[data-input-role="reference_s1"]').selectOption('soulx_ref_1');assert(await page.locator('[data-input-transcript="reference_s1"]').evaluate(e=>e.required&&!e.disabled));assert(await page.locator('[data-input-transcript="reference_s2"]').isDisabled());
  const before=await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask').length);await page.locator('#localTaskForm [type="submit"]').click();assert.equal(await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask').length),before);checked('Selecting audio makes its transcript mandatory before submission');
  await page.locator('[data-input-transcript="reference_s1"]').fill('第一段参考音频原文。');await page.locator('[data-input-role="reference_s2"]').selectOption('soulx_ref_2');await page.locator('[data-input-transcript="reference_s2"]').fill('Second reference transcript.');
  await page.evaluate(()=>{window.__fixture.artifacts.push({id:'soulx_new_ref',bytes:48044,available:true,metadata:{mime:'audio/wav',durationMs:1000},origin:{name:'新增界面样本.wav'}});window.LMA.receive(window.__fixture);});
  assert.equal(await page.locator('[data-input-transcript="reference_s1"]').inputValue(),'第一段参考音频原文。');assert.equal(await page.locator('[data-input-role="reference_s2"]').inputValue(),'soulx_ref_2');checked('Media refresh preserves paired audio and typed transcripts');
  await page.locator('[data-input-role="reference_s2"]').selectOption('');assert(await page.locator('[data-input-transcript="reference_s2"]').isDisabled());await page.locator('[data-input-role="reference_s2"]').selectOption('soulx_ref_2');assert.equal(await page.locator('[data-input-transcript="reference_s2"]').inputValue(),'Second reference transcript.');checked('Optional deselection disables its transcript and reselect retains the draft');
  await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});await page.locator('[data-bundle-field="context"]').fill('256');await page.locator('[data-bundle-field="context"]').blur();
  await page.locator('[data-bundle-field="maxNewTokens"]').fill('99999');await page.locator('[data-bundle-field="maxNewTokens"]').blur();assert.equal(await page.locator('[data-bundle-field="maxNewTokens"]').inputValue(),'192');assert.equal(await page.locator('[data-bundle-field="historyThreshold"]').inputValue(),'256');checked('SoulX editable profile enforces shared context/output/history bounds');
  await overflow(page,'SoulX paired input and parameters');await page.locator('#localTaskForm [type="submit"]').click();await page.waitForFunction(n=>window.__commands.filter(c=>c.action==='submitTask').length>n,before);
  const request=await page.evaluate(()=>window.__commands.findLast(c=>c.action==='submitTask').request);assert.deepEqual(request.input.transcripts,{reference_s1:'第一段参考音频原文。',reference_s2:'Second reference transcript.'});assert.deepEqual(request.input.artifacts,[{role:'reference_s1',artifactId:'soulx_ref_1'},{role:'reference_s2',artifactId:'soulx_ref_2'}]);checked('Shared task API carries only selected IDs and paired immutable text');
  await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
};
module.exports.installFixture=installFixture;
