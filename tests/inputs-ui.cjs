/* Media/input UI contract only; no Android picker, model or voice cloning is simulated as real. */
const assert = require('node:assert/strict');
const foundation = require('./foundation-ui.cjs');

async function install(page) {
  await page.evaluate(foundation.installFixture);
  await page.evaluate(() => {
    const f = window.__fixture, b = f.bundles[0];
    f.engine = {...f.engine,state:'stopped',modelId:'',generating:false,detail:'选择模型后，在当前手机执行'}; f.chat.messages = [];
    b.id = b.manifest.id = 'ui_inputs'; b.installed = true; b.manifest.engine = 'ui_input_contract';
    b.manifest.name = '素材输入表单 · UI FIXTURE'; b.manifest.architecture = 'ui_contract'; b.manifest.tasks = ['audio']; b.manifest.capabilities = ['text_to_speech'];
    b.manifest.parameters = {version:1,fields:{speed:{type:'number',minimum:0.5,maximum:2,default:1,presets:[0.8,1,1.2]}}}; b.config.values = {speed:1};
    b.inputSchemas = {'speech.synthesize':{version:1,roles:{reference_audio:{label:'参考音频（输入契约演示）',required:true,mimes:['audio/wav'],maxBytes:1048576,maxDurationMs:5000}}}};
    f.localEngines = [{engine:'ui_input_contract',available:true,deviceValidated:false}];
    const artifact = (id, name, kind, durationMs, available=true) => ({id,jobId:kind==='generated'?'ui_old_job':'',bytes:32044,createdAt:Date.UTC(2026,9,28),sha256:'a'.repeat(64),available,metadata:{mime:'audio/wav',sampleRate:16000,channels:1,durationMs},origin:{kind,name},provenance:{fixture:true,modelInference:false}});
    f.artifacts = [artifact('artifact_missing','<img src=x onerror=window.__pwned=true>.wav','imported',1000,false),artifact('artifact_long','时长不匹配.wav','imported',6000),artifact('artifact_old','已有音频结果','generated',2000),artifact('artifact_ref','参考配音.wav','imported',1000)];
    f.artifacts.find(a=>a.id==='artifact_ref').inUse = true; f.inputImport = {busy:false};
    const previous = window.__handleFoundation;
    window.__handleFoundation = command => {
      if (command.action === 'inspectArtifact') return f.artifacts.find(a=>a.id===command.id);
      if (command.action === 'inputPicker') f.inputImport = {busy:true,pending:1,name:'新素材.wav'};
      if (command.action === 'cancelInputImport') f.inputImport = {busy:false};
      if (command.action === 'deleteArtifact') f.artifacts = f.artifacts.filter(a=>a.id!==command.id);
      return previous(command);
    };
    window.LMA.receive(f);
  });
}

module.exports = async function checkInputs(page, checked, checkOverflow) {
  await install(page); await page.locator('.nav-item[data-tab="tasks"]').click();
  await page.locator('[data-action="filterArtifacts"][data-kind="all"]').click();
  assert.equal(await page.locator('.artifact-card').count(),4); checked('Imported media and generated results share one library');
  assert((await page.locator('.artifact-card').first().innerText()).includes('导入素材')); checked('Imported source is distinct from generated output');
  assert(await page.locator('[data-action="artifactRemove"][data-id="artifact_ref"]').isDisabled()); checked('Queued/running input references disable library deletion');
  assert.equal(await page.locator('.artifact-info img').count(),0); assert.equal(await page.evaluate(()=>window.__pwned),false); checked('Untrusted input names render as text');
  await page.locator('[data-action="filterArtifacts"][data-kind="generated"]').click(); assert.equal(await page.locator('.artifact-card').count(),1); checked('Result filter excludes imported inputs');
  await page.locator('[data-action="filterArtifacts"][data-kind="imported"]').click(); assert.equal(await page.locator('.artifact-card').count(),3); checked('Imported-only filter retains missing files with their actual availability');
  const before = await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle','load','submitTask'].includes(c.action)).length);
  await page.locator('[data-action="inputPicker"]').first().click(); await page.waitForSelector('[data-action="cancelInputImport"]');
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>['download','downloadBundle','load','submitTask'].includes(c.action)).length),before); checked('Input picker and source filtering never download or load a model');
  await page.locator('[data-action="cancelInputImport"]').click(); await page.waitForFunction(()=>!window.__fixture.inputImport.busy); checked('In-progress local input import exposes a separate cancellation action');
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('#modelSearch').fill(''); await page.locator('[data-task="audio"]').click(); await page.locator('[data-filter="local"]').click();
  await page.locator('[data-action="bundleUse"][data-id="ui_inputs"]').click(); await page.waitForSelector('[data-input-role="reference_audio"]');
  assert.equal(await page.locator('[data-input-role] option').count(),3); checked('Role selectors include compatible imported media and previous results only');
  assert(await page.locator('[data-input-role]').evaluate(el=>el.required)); checked('Signed engine input schema controls required media fields');
  await page.locator('[name="prompt"]').fill('这是一条界面契约示例，不执行模型。'); await page.locator('[name="allowUnmeasured"]').check();
  const submitted = await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask').length);
  await page.locator('#localTaskForm [type="submit"]').click();
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask').length),submitted); checked('Required reference media cannot be omitted by UI submission');
  await page.locator('[data-input-role]').selectOption('artifact_ref');
  await page.evaluate(()=>{window.__fixture.artifacts.push({id:'artifact_new',bytes:100,metadata:{mime:'audio/wav',durationMs:1000},available:true,origin:{kind:'imported',name:'新增.wav'}}); window.LMA.receive(window.__fixture);});
  assert.equal(await page.locator('[data-input-role]').inputValue(),'artifact_ref'); checked('Library refresh preserves an explicitly selected input');
  await checkOverflow(page,'Input role form on a narrow phone');
  await page.locator('#localTaskForm [type="submit"]').click(); await page.waitForFunction(()=>window.__commands.filter(c=>c.action==='submitTask').length>0);
  const request = await page.evaluate(()=>window.__commands.findLast(c=>c.action==='submitTask').request);
  assert.deepEqual(request.input.artifacts,[{role:'reference_audio',artifactId:'artifact_ref'}]); checked('Task form sends only the selected artifact ID and role, never a path or client receipt');
  await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
  await page.evaluate(foundation.installFixture); await page.evaluate(()=>{window.__fixture.bundles[0].installed=true; window.LMA.receive(window.__fixture);});
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="image"]').click();
  await page.locator('[data-action="bundleUse"][data-id="ui_sd"]').click();
  assert.equal(await page.locator('[data-input-role]').count(),0); assert((await page.locator('#taskInputs').innerText()).includes('仅接受文字')); checked('Existing prompt-only recipes do not acquire media editing or cloning capability');
  await page.keyboard.press('Escape'); await page.locator('[data-task="any"]').click();
};
module.exports.install = install;
