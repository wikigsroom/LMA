/* Production forms with explicit fixture state; no weights or neural inference. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
function installFixture(template) {
  const f=window.__fixture,sound=template.id==='moss_soundeffect_v2_cpu_v1',id=sound?'ui_moss_sound':'ui_moss_local',definition=JSON.parse(JSON.stringify(template.definition));
  const components=template.requirements.map(r=>({role:r.role,provides:r.provides||[],path:r.role+'.gguf',format:'gguf',bytes:1000,sha256:'a'.repeat(64)}));
  const manifest={...definition,id,modelId:id,recipeId:template.id,name:(sound?'MOSS SoundEffect-v2':'MOSS Local-v1.5')+' · UI FIXTURE',description:template.help+' 界面夹具：未下载权重，未生成音频。',components,evidence:{physicalDeviceTests:0}};
  const values=Object.fromEntries(Object.entries(definition.parameters.fields).map(([k,v])=>[k,v.default]));
  const inputSchemas={[sound?'audio.generate':'speech.synthesize']:{version:1,roles:sound?{}:{reference_audio:{label:'可选参考：48 kHz 双声道 WAV，1–10 秒',required:false,mimes:['audio/wav'],maxBytes:4194304,maxDurationMs:10000}}}};
  f.bundles=f.bundles.filter(b=>b.id!==id).concat([{id,manifest,installed:true,config:{values},inputSchemas,plan:{installed:true,totalBytes:2000,remainingBytes:0,components}}]);
  f.localEngines=(f.localEngines||[]).filter(e=>e.engine!=='openmoss_native').concat([{engine:'openmoss_native',available:true,deviceValidated:false}]);
  f.artifacts=(f.artifacts||[]).filter(a=>a.id!=='openmoss_ref_fixture').concat([{id:'openmoss_ref_fixture',jobId:'',bytes:384044,available:true,createdAt:Date.UTC(2026,9,28),sha256:'b'.repeat(64),origin:{kind:'imported',name:'双声道参考 · UI FIXTURE'},metadata:{mime:'audio/wav',sampleRate:48000,channels:2,formatCode:1,bitsPerSample:16,durationMs:2000},provenance:{fixture:true,modelInference:false}}]);
  window.LMA.receive(f);
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
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle','resumeBundle','resumeDownload'].includes(c.action)).length),before);checked('Browsing/editing Openmoss never downloads or resumes user assets');await page.locator('[data-task="any"]').click();
};
module.exports.installFixture=installFixture;
