/* Production UI with explicit simulated bundle state; no weights or audio generation. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
function installFixture(template){
  const f=window.__fixture,id='ui_stable_audio',definition=JSON.parse(JSON.stringify(template.definition));
  const components=template.requirements.map(r=>({role:r.role,provides:r.provides||[],path:r.role+(r.formats[0]==='sentencepiece'?'.model':'.tflite'),format:r.formats[0],bytes:1000,sha256:'a'.repeat(64)}));
  const manifest={...definition,id,modelId:id,recipeId:template.id,name:template.name+' · UI FIXTURE',description:template.help+' 界面夹具：未下载权重，未生成音频。',components,evidence:{physicalDeviceTests:0}};
  const values=Object.fromEntries(Object.entries(definition.parameters.fields).map(([k,v])=>[k,v.default]));
  f.bundles=f.bundles.filter(b=>b.id!==id).concat([{id,manifest,installed:true,config:{values},inputSchemas:{'audio.generate':{version:1,roles:{}}},plan:{installed:true,totalBytes:4000,remainingBytes:0,components}}]);
  f.localEngines=(f.localEngines||[]).filter(e=>e.engine!==definition.engine).concat([{engine:definition.engine,available:true,deviceValidated:false}]);window.LMA.receive(f);return id;
}
module.exports=async function(page,checked,overflow){
  const template=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.find(t=>t.id==='stable_audio_small_litert_v1');
  const id=await page.evaluate(installFixture,template);await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').click();
  assert.equal(await page.locator('.bundle-components details').count(),4);assert((await page.locator('#modalContent').innerText()).includes('524288'));checked('Stable Audio exposes four user-selected components and fixed decoder cost');
  await page.locator('#modal [data-action="bundleUse"][data-id="'+id+'"]').click();assert.equal(await page.locator('[name="taskType"]').inputValue(),'audio.generate');assert.equal(await page.locator('[name="negativePrompt"],[data-input-role]').count(),0);checked('Stable Audio only exposes actual text-to-audio conditioning');
  await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});
  for(const [key,value,expected] of [['seconds','99','11'],['steps','999','32'],['maxInputTokens','999','64'],['threads','0','1']]){
    const field=page.locator('[data-bundle-field="'+key+'"]');assert.equal(await field.getAttribute('role'),'combobox');await field.fill(value);await field.press('Tab');assert.equal(await field.inputValue(),expected);checked('Stable Audio editable '+key+' enforces its own bound');
  }
  await overflow(page,'Stable Audio form');await page.keyboard.press('Escape');
};
module.exports.installFixture=installFixture;
