/* Real forms with a simulated installed state. No weights, model inference or generated audio. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
function installFixture(template) {
  const f=window.__fixture,id='ui_moss_delay',definition=JSON.parse(JSON.stringify(template.definition));
  const components=template.requirements.filter(r=>template.fixtureWithoutEncoder?r.role!=='audio_encoder':true).map(r=>({role:r.role,provides:r.provides||[],path:r.role+'.gguf',format:'gguf',bytes:1000,sha256:'a'.repeat(64)}));
  const manifest={...definition,id,modelId:id,recipeId:template.id,name:'MOSS Delay 8B · UI FIXTURE',description:'界面夹具：未下载权重，未执行语音合成或克隆。',components,evidence:{physicalDeviceTests:0}};
  const values=Object.fromEntries(Object.entries(definition.parameters.fields).map(([k,v])=>[k,v.default]));
  const inputSchemas={'speech.synthesize':{version:1,roles:{reference_audio:{label:'可选参考音频：24 kHz 单声道 WAV，1–10 秒',required:false,mimes:['audio/wav'],maxBytes:1048576,maxDurationMs:10000}}}};
  if(template.fixtureWithoutEncoder)inputSchemas['speech.synthesize'].roles={};
  f.bundles=f.bundles.filter(b=>b.id!==id).concat([{id,manifest,installed:true,config:{values},inputSchemas,plan:{installed:true,totalBytes:3000,remainingBytes:0,components}}]);
  f.localEngines=(f.localEngines||[]).filter(e=>e.engine!=='moss_delay_native').concat([{engine:'moss_delay_native',available:true,deviceValidated:false}]);
  f.artifacts=(f.artifacts||[]).filter(a=>a.id!=='moss_delay_ref_fixture').concat([{id:'moss_delay_ref_fixture',jobId:'',bytes:96044,available:true,createdAt:Date.UTC(2026,9,28),sha256:'b'.repeat(64),origin:{kind:'imported',name:'参考 WAV · UI FIXTURE'},metadata:{mime:'audio/wav',sampleRate:24000,channels:1,formatCode:1,bitsPerSample:16,durationMs:2000},provenance:{fixture:true,modelInference:false}}]);
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow){
  const template=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.find(t=>t.id==='moss_delay_firstclass_cpu_v1');
  await page.evaluate(installFixture,template);
  const before=await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle'].includes(c.action)).length);
  await page.locator('[data-tab="models"]').first().click();await page.locator('[data-task="audio"]').click();await page.locator('[data-filter="local"]').click();
  await page.locator('[data-action="bundleInfo"][data-id="ui_moss_delay"]').click();
  assert.equal(await page.locator('.bundle-components details').count(),3);await page.locator('.bundle-components details').first().evaluate(e=>{e.open=true;});
  assert((await page.locator('#modalContent').innerText()).includes('文本分词数据'));checked('Three explicitly selected MOSS Delay files disclose their embedded dependencies');
  await page.locator('#modal [data-action="bundleUse"][data-id="ui_moss_delay"]').click();
  assert(await page.locator('[data-input-role="reference_audio"]').isVisible());assert.equal(await page.locator('[data-input-role="reference_audio"]').inputValue(),'');checked('MOSS Delay reference WAV is optional and uses shared local input selection');
  await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});
  for(const [key,high] of [['threads','32'],['maxInputTokens','2048'],['maxNewTokens','1500']]){
    const field=page.locator('[data-bundle-field="'+key+'"]');await field.fill('99999');await field.press('Tab');assert.equal(await field.inputValue(),high);checked('MOSS Delay per-model '+key+' clamps to its application guard');
  }
  await page.locator('[data-bundle-field="language"]').selectOption({label:'zh'});await page.locator('[data-input-role="reference_audio"]').selectOption('moss_delay_ref_fixture');
  assert.equal(await page.locator('[name="negativePrompt"]').count(),0);checked('Speech form offers language and reference input without image-only controls');
  for(const [key,value,expected] of [['audioTemperature','99','3'],['textTopP','0','0.01'],['maxNewTokens','1','64']]) {const field=page.locator('[data-bundle-field="'+key+'"]');await field.fill(value);await field.press('Tab');assert.equal(await field.inputValue(),expected);checked('MOSS editable '+key+' enforces native application bounds');}
  await overflow(page,'MOSS Delay speech parameter/reference form');await page.keyboard.press('Escape');
  await page.evaluate(installFixture,{...template,fixtureWithoutEncoder:true});
  await page.locator('[data-action="bundleInfo"][data-id="ui_moss_delay"]').click();await page.locator('#modal [data-action="bundleUse"][data-id="ui_moss_delay"]').click();
  assert.equal(await page.locator('[data-input-role="reference_audio"]').count(),0);checked('Plain MOSS speech does not expose reference input or require an encoder');await page.keyboard.press('Escape');
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle'].includes(c.action)).length),before);checked('Browsing MOSS Delay and editing task parameters never starts model downloads');
  await page.locator('[data-task="any"]').click();
};
module.exports.installFixture=installFixture;
