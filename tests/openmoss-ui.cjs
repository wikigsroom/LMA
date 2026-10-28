/* Production forms with explicit fixture state; no weights or neural inference. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
function installFixture(template) {
  const f=window.__fixture,sound=template.definition.capabilities.includes('text_to_audio'),local=template.id==='moss_local_v15_cpu_v1',id=template.id==='moss_soundeffect_v2_cpu_v1'?'ui_moss_sound':local?'ui_moss_local':'ui_'+template.id,definition=JSON.parse(JSON.stringify(template.definition)),dialogue=definition.architecture==='moss_ttsd',voice=definition.architecture==='moss_voicegenerator';
  const components=template.requirements.map(r=>({role:r.role,provides:r.provides||[],path:r.role+'.gguf',format:'gguf',bytes:1000,sha256:'a'.repeat(64)}));
  const manifest={...definition,id,modelId:id,recipeId:template.id,name:template.name+' · UI FIXTURE',description:template.help+' 界面夹具：未下载权重，未生成音频。',components,evidence:{physicalDeviceTests:0}};
  const values=Object.fromEntries(Object.entries(definition.parameters.fields).map(([k,v])=>[k,v.default]));
  const roles={};if(!sound && !voice)for(const role of (dialogue?['reference_audio_s1','reference_audio_s2']:['reference_audio']))roles[role]={label:dialogue?'成对可选参考 '+(role.endsWith('s1')?'[S1]':'[S2]')+'：24 kHz 单声道 WAV，1–10 秒':local?'可选参考：48 kHz 双声道 WAV，1–10 秒':'可选参考：24 kHz 单声道 WAV，1–10 秒',required:false,mimes:['audio/wav'],maxBytes:local?4194304:1048576,maxDurationMs:10000};
  const inputSchemas={[sound?'audio.generate':'speech.synthesize']:{version:1,roles}};
  f.bundles=f.bundles.filter(b=>b.id!==id).concat([{id,manifest,installed:true,config:{values},inputSchemas,plan:{installed:true,totalBytes:2000,remainingBytes:0,components}}]);
  f.localEngines=(f.localEngines||[]).filter(e=>e.engine!==definition.engine).concat([{engine:definition.engine,available:true,deviceValidated:false}]);
  f.artifacts=(f.artifacts||[]).filter(a=>a.id!=='openmoss_ref_fixture').concat([{id:'openmoss_ref_fixture',jobId:'',bytes:384044,available:true,createdAt:Date.UTC(2026,9,28),sha256:'b'.repeat(64),origin:{kind:'imported',name:'双声道参考 · UI FIXTURE'},metadata:{mime:'audio/wav',sampleRate:48000,channels:2,formatCode:1,bitsPerSample:16,durationMs:2000},provenance:{fixture:true,modelInference:false}}]);
  for(const speaker of [1,2]) {const ref='openmoss_s'+speaker+'_fixture';f.artifacts=f.artifacts.filter(a=>a.id!==ref).concat([{id:ref,jobId:'',bytes:96044,available:true,createdAt:Date.UTC(2026,9,28),sha256:String(speaker).repeat(64),origin:{kind:'imported',name:'[S'+speaker+'] 单声道 · UI FIXTURE'},metadata:{mime:'audio/wav',sampleRate:24000,channels:1,formatCode:1,bitsPerSample:16,durationMs:2000},provenance:{fixture:true,modelInference:false}}]);}
  window.LMA.receive(f);
  return id;
}
module.exports=async function(page,checked,overflow) {
  const templates=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates;
  const before=await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle','resumeBundle','resumeDownload'].includes(c.action)).length);
  for(const sound of [false,true]) {
    const template=templates.find(t=>t.id===(sound?'moss_soundeffect_v2_cpu_v1':'moss_local_v15_cpu_v1')),id=sound?'ui_moss_sound':'ui_moss_local';
    await page.evaluate(installFixture,template);await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').click();
    assert.equal(await page.locator('.bundle-components details').count(),2);await page.locator('.bundle-components details').first().evaluate(e=>{e.open=true;});
    assert((await page.locator('#modalContent').innerText()).includes('文本分词数据'));checked('Openmoss '+(sound?'sound':'local')+' discloses two physical files and embedded tokenizer');
    if(sound) {assert((await page.locator('#modalContent').innerText()).includes('30 秒'));checked('SoundEffect explains full latent cost before task selection');}
    await page.locator('#modal [data-action="bundleUse"][data-id="'+id+'"]').click();
    assert.equal(await page.locator('[name="taskType"]').inputValue(),sound?'audio.generate':'speech.synthesize');assert.equal(await page.locator('[name="negativePrompt"]').count(),sound?1:0);assert.equal(await page.locator('[data-input-role="reference_audio"]').count(),sound?0:1);checked('Openmoss task type and input controls match its distinct capability');
    await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});
    for(const [key,value,expected] of (sound?[['seconds','99','30'],['steps','999','100'],['sigmaShift','0','1']]:[['maxInputTokens','9999','2048'],['maxNewTokens','9999','750'],['audioTopP','0','0.01']])) {
      const field=page.locator('[data-bundle-field="'+key+'"]');await field.fill(value);await field.press('Tab');assert.equal(await field.inputValue(),expected);checked('Openmoss editable '+key+' enforces its own bound');
    }
    assert.equal(await page.locator('[data-bundle-field="threads"]').inputValue(),'4');checked('Openmoss per-model defaults are independent of other models');await overflow(page,'Openmoss '+(sound?'sound':'local')+' form');await page.keyboard.press('Escape');
  }
  for(const arch of ['moss_tts','moss_tts_v15','moss_ttsd','moss_voicegenerator']) {
    const template=templates.find(t=>t.definition.engine==='openmoss_native' && t.definition.architecture===arch),id=await page.evaluate(installFixture,template),dialogue=arch==='moss_ttsd',voice=arch==='moss_voicegenerator';
    await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').click();assert.equal(await page.locator('.bundle-components details').count(),2);checked('MOSS '+arch+' remains a flat model with explicit component selection');
    await page.locator('#modal [data-action="bundleUse"][data-id="'+id+'"]').click();assert.equal(await page.locator('[name="taskType"]').inputValue(),'speech.synthesize');assert.equal(await page.locator('[data-input-role]').count(),voice?0:dialogue?2:1);checked('MOSS '+arch+' exposes its actual reference roles');
    if(dialogue){await page.locator('[data-input-role="reference_audio_s1"]').selectOption('openmoss_s1_fixture');await page.locator('[data-input-role="reference_audio_s2"]').selectOption('openmoss_s2_fixture');assert.equal(await page.locator('[data-input-role="reference_audio_s2"]').inputValue(),'openmoss_s2_fixture');checked('TTSD explicitly maps both speaker references');}
    await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});const instruction=page.locator('[data-bundle-field="voiceInstruction"]');await instruction.fill('成年、低沉、温暖的声音。');assert.equal(await instruction.getAttribute('maxlength'),'1000');await page.locator('[data-bundle-field="language"]').fill('zh');checked('MOSS voice/language fields use bounded per-model text parameters');
    const budget=page.locator('[data-bundle-field="maxNewTokens"]');await budget.fill('99999');await budget.press('Tab');assert.equal(await budget.inputValue(),'1500');checked('Delay generation bound differs from Local-v1.5');await overflow(page,'MOSS '+arch+' task');await page.keyboard.press('Escape');
  }
  for(const pipeline of ['moss_soundeffect_openmoss_cpu_v1','moss_local_v10_rq_cpu_v1','moss_realtime_rq_cpu_v1']) {
    const template=templates.find(t=>t.id===pipeline),id=await page.evaluate(installFixture,template),effect=template.definition.capabilities.includes('text_to_audio'),rt=pipeline==='moss_realtime_rq_cpu_v1';
    await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').click();assert.equal(await page.locator('.bundle-components details').count(),effect?2:3);checked('MOSS '+pipeline+' explicitly selects each component');
    await page.locator('#modal [data-action="bundleUse"][data-id="'+id+'"]').click();assert.equal(await page.locator('[name="taskType"]').inputValue(),effect?'audio.generate':'speech.synthesize');assert.equal(await page.locator('[data-input-role]').count(),effect?0:1);assert.equal(await page.locator('[name="negativePrompt"]').count(),0);checked('MOSS '+pipeline+' has only supported conditioning');
    await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});assert.equal(await page.locator('[data-bundle-field="voiceInstruction"]').count(),effect||rt?0:1);assert.equal(await page.locator('[data-bundle-field="textTopP"]').count(),effect||rt?0:1);checked('MOSS '+pipeline+' exposes only consumed sampler/hint fields');
    const budget=page.locator('[data-bundle-field="maxNewTokens"]');await budget.fill('99999');await budget.press('Tab');assert.equal(await budget.inputValue(),effect?'1500':'750');checked('MOSS '+pipeline+' clamps model-local bounds');await overflow(page,'MOSS '+pipeline+' task');await page.keyboard.press('Escape');
  }
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle','resumeBundle','resumeDownload'].includes(c.action)).length),before);checked('Browsing/editing MOSS never downloads or resumes user assets');await page.locator('[data-task="any"]').click();
};
module.exports.installFixture=installFixture;
