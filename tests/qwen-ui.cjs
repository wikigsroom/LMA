/* Real forms with a simulated installed state. No weights, model inference or generated audio. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
function installFixture(template) {
  const f=window.__fixture,id='ui_qwen_tts',definition=JSON.parse(JSON.stringify(template.definition));
  const components=template.requirements.map(r=>({role:r.role,provides:r.provides||[],path:r.role+'.gguf',format:'gguf',bytes:1000,sha256:'a'.repeat(64)}));
  const manifest={...definition,id,modelId:id,recipeId:template.id,name:'Qwen3-TTS 0.6B Base · UI FIXTURE',description:'界面夹具：未下载权重，未执行语音合成或克隆。',components,evidence:{physicalDeviceTests:0}};
  const values=Object.fromEntries(Object.entries(definition.parameters.fields).map(([k,v])=>[k,v.default]));
  const inputSchemas={'speech.synthesize':{version:1,roles:{reference_audio:{label:'可选参考音频：24 kHz 单声道 WAV，1–30 秒',required:false,mimes:['audio/wav'],maxBytes:4194304,maxDurationMs:30000}}}};
  f.bundles=f.bundles.filter(b=>b.id!==id).concat([{id,manifest,installed:true,config:{values},inputSchemas,plan:{installed:true,totalBytes:2000,remainingBytes:0,components}}]);
  f.localEngines=(f.localEngines||[]).filter(e=>e.engine!=='qwen_tts_native').concat([{engine:'qwen_tts_native',available:true,deviceValidated:false}]);
  f.artifacts=(f.artifacts||[]).filter(a=>a.id!=='qwen_ref_fixture').concat([{id:'qwen_ref_fixture',jobId:'',bytes:96044,available:true,createdAt:Date.UTC(2026,9,28),sha256:'b'.repeat(64),origin:{kind:'imported',name:'参考 WAV · UI FIXTURE'},metadata:{mime:'audio/wav',sampleRate:24000,channels:1,formatCode:1,bitsPerSample:16,durationMs:2000},provenance:{fixture:true,modelInference:false}}]);
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow){
  const template=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.find(t=>t.id==='qwen3_tts_06b_base_cpu_v1');
  await page.evaluate(installFixture,template);
  const before=await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle'].includes(c.action)).length);
  await page.locator('[data-tab="models"]').first().click();await page.locator('[data-task="audio"]').click();await page.locator('[data-filter="local"]').click();
  await page.locator('[data-action="bundleInfo"][data-id="ui_qwen_tts"]').click();
  assert.equal(await page.locator('.bundle-components details').count(),2);await page.locator('.bundle-components details').first().evaluate(e=>{e.open=true;});
  assert((await page.locator('#modalContent').innerText()).includes('文本分词数据'));checked('Two physical Qwen files disclose their embedded dependencies');
  await page.locator('#modal [data-action="bundleUse"][data-id="ui_qwen_tts"]').click();
  assert(await page.locator('[data-input-role="reference_audio"]').isVisible());assert.equal(await page.locator('[data-input-role="reference_audio"]').inputValue(),'');checked('Qwen reference WAV is optional and uses shared local input selection');
  await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});
  for(const [key,high] of [['threads','32'],['maxInputTokens','2048'],['maxAudioTokens','1500']]){
    const field=page.locator('[data-bundle-field="'+key+'"]');await field.fill('99999');await field.press('Tab');assert.equal(await field.inputValue(),high);checked('Qwen per-model '+key+' clamps to its application guard');
  }
  await page.locator('[data-bundle-field="language"]').selectOption({label:'zh'});await page.locator('[data-input-role="reference_audio"]').selectOption('qwen_ref_fixture');
  assert.equal(await page.locator('[name="negativePrompt"]').count(),0);checked('Speech form offers language and reference input without image-only controls');
  await overflow(page,'Qwen speech parameter/reference form');await page.keyboard.press('Escape');
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle'].includes(c.action)).length),before);checked('Browsing Qwen and editing task parameters never starts model downloads');
  await page.locator('[data-task="any"]').click();
};
module.exports.installFixture=installFixture;
