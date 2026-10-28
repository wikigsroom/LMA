/* Signed recipe metadata plus simulated installed state; no model downloads or inference. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function installFixture(templates) {
  const f = window.__fixture;
  const make = (id, template, name) => {
    const t = templates.find(t => t.id === template), definition = JSON.parse(JSON.stringify(t.definition));
    const components = t.requirements.filter(r => r.required).map(r => ({role:r.role, path:r.role + '.fixture', format:r.formats[0], bytes:1000, sha256:'a'.repeat(64)})).concat(t.fixedComponents);
    const manifest = {...definition, id, modelId:id, recipeId:template, name, description:'UI FIXTURE：未下载权重，未执行模型。', components, evidence:{physicalDeviceTests:0}};
    const values = Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v]) => [k,v.default]));
    return {id,manifest,installed:true,config:{values},plan:{installed:true,totalBytes:1000,remainingBytes:0,components}};
  };
  f.bundles = f.bundles.filter(b => !b.id.startsWith('ui_sampling_')).concat([
    make('ui_sampling_base','sd15_checkpoint_cpu_v1','SD 1.5 基础模型 · UI FIXTURE'),
    make('ui_sampling_lora','sd15_lcm_lora_cpu_v1','LCM-LoRA · UI FIXTURE'),
    make('ui_sampling_turbo','sd21_turbo_checkpoint_cpu_v1','SD-Turbo · UI FIXTURE'),
    make('ui_sampling_zimage','z_image_turbo_split_cpu_v1','Z-Image-Turbo · UI FIXTURE'),
    make('ui_sampling_flux','flux2_klein_4b_split_cpu_v1','FLUX.2-klein 4B · UI FIXTURE'),
    make('ui_sampling_qwen','qwen_image_21_split_cpu_v1','Qwen-Image 2.1 · UI FIXTURE'),
    make('ui_sampling_wan','wan21_13b_split_cpu_v1','Wan 2.1 T2V 1.3B · UI FIXTURE'),
    make('ui_sampling_sana','sana_mnn_cpu_v1','Sana mobile · MNN · UI FIXTURE')
  ]);
  if (!f.localEngines.some(e => e.engine === 'sd_cpp')) f.localEngines.push({engine:'sd_cpp',available:true,deviceValidated:false});
  f.localEngines.find(e => e.engine === 'sd_cpp').available = true;
  if (!f.localEngines.some(e => e.engine === 'mnn_diffusion')) f.localEngines.push({engine:'mnn_diffusion',available:true,deviceValidated:false});
  window.LMA.receive(f);
}

module.exports = async function(page, checked, overflow) {
  const templates = JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates;
  await page.evaluate(installFixture,templates);
  const downloads = () => page.evaluate(() => window.__commands.filter(c => ['download','downloadBundle'].includes(c.action)).length);
  const before = await downloads();
  await page.locator('[data-tab="models"]').first().click(); await page.locator('[data-task="image"]').click(); await page.locator('[data-filter="local"]').click();
  await page.locator('[data-action="bundleUse"][data-id="ui_sampling_base"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e => {e.open=true;});
  const steps=page.locator('[data-bundle-field="steps"]'), cfg=page.locator('[data-bundle-field="cfg"]'), negative=page.locator('[name="negativePrompt"]'), choice=page.locator('[data-adapter-select="ui_sampling_lora"]');
  assert.equal(await steps.inputValue(),'20'); assert.equal(await cfg.inputValue(),'7'); checked('Ordinary base retains its independent sampling defaults');
  await negative.fill('blur'); await choice.check();
  assert((await page.locator('#samplingHint').innerText()).includes('LCM')); assert.equal(await steps.inputValue(),'8'); checked('Explicit LCM selection displays its sampler and clamps task steps');
  assert(await cfg.isDisabled()); assert.equal(await cfg.inputValue(),'1'); assert(await negative.isDisabled()); checked('Distilled task disables CFG and unsupported negative conditioning');
  assert(await page.locator('[data-bundle-field="sampler"]').evaluate(e => e.closest('label').hidden)); checked('Ordinary sampler controls cannot contradict the LCM policy');
  await steps.fill('999'); await steps.blur(); assert.equal(await steps.inputValue(),'8'); checked('Edited LCM steps return to the active recipe ceiling');
  await choice.uncheck(); assert.equal(await steps.inputValue(),'20'); assert.equal(await cfg.inputValue(),'7'); assert(await negative.isEnabled()); assert.equal(await negative.inputValue(),'blur'); checked('Removing the adapter restores this task form without changing saved settings');
  await choice.check(); await page.locator('[name="prompt"]').fill('Low-step image task; interface fixture only.'); await page.locator('[name="allowUnmeasured"]').check();
  await overflow(page,'LCM task sampling form');
  await page.locator('#localTaskForm button[type="submit"]').click(); await page.waitForSelector('.job-card');
  const request=await page.evaluate(() => window.__commands.findLast(c=>c.action==='submitTask').request);
  assert.equal(request.parameters.steps,8); assert.equal(request.parameters.cfg,1); assert.equal(request.input.negativePrompt,''); assert.equal(request.adapters[0].bundleId,'ui_sampling_lora'); checked('LCM task submits explicit peer IDs and applicable parameters');
  const saved=await page.evaluate(() => window.__fixture.bundles.find(b=>b.id==='ui_sampling_base').config.values);
  assert.equal(saved.steps,20); assert.equal(saved.cfg,7); checked('Submitting LCM keeps stored base-model settings intact');
  await page.locator('[data-tab="models"]').first().click(); await page.locator('[data-action="bundleUse"][data-id="ui_sampling_turbo"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e => {e.open=true;});
  assert((await page.locator('#samplingHint').innerText()).includes('1–4')); assert(await negative.isDisabled()); checked('SD-Turbo exposes its distinct low-step policy');
  await steps.fill('99'); await steps.blur(); assert.equal(await steps.inputValue(),'4'); checked('SD-Turbo edits clamp independently of LCM');
  await page.keyboard.press('Escape');
  for (const [id, label, maximum] of [['zimage','Z-Image-Turbo',8],['flux','FLUX.2-klein',4]]) {
    await page.locator('[data-action="bundleUse"][data-id="ui_sampling_' + id + '"]').click();
    await page.locator('#localTaskForm .task-parameters').evaluate(e => {e.open=true;});
    assert((await page.locator('#samplingHint').innerText()).includes(label)); assert(await negative.isDisabled()); assert(await cfg.isDisabled()); checked(label + ' uses its own declared distilled policy');
    await steps.fill('999'); await steps.blur(); assert.equal(await steps.inputValue(),String(maximum)); checked(label + ' task steps clamp to its own application policy');
    await overflow(page,label + ' task'); await page.keyboard.press('Escape');
  }
  await page.locator('[data-action="bundleUse"][data-id="ui_sampling_qwen"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e => {e.open=true;});
  assert(await negative.isEnabled()); assert.equal(await page.locator('[data-bundle-field="scheduler"] option:checked').innerText(),'flux'); assert.equal(await steps.inputValue(),'20'); checked('Qwen 2.1 retains normal CFG and its resolution-aware scheduler');
  await page.keyboard.press('Escape');
  await page.locator('[data-action="bundleInfo"][data-id="ui_sampling_sana"]').click();
  assert((await page.locator('#modal').innerText()).includes('mnn_diffusion')); checked('Sana remains a peer image entry with its own engine requirement');
  await page.locator('#modal [data-action="bundleUse"][data-id="ui_sampling_sana"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e => {e.open=true;});
  assert((await page.locator('#samplingHint').innerText()).includes('13 个')); checked('Sana form explains complete matched components and local CPU evidence limits');
  const useCfg=page.locator('[data-bundle-field="useCfg"]'); assert.equal(await useCfg.isChecked(),false); assert.equal(await page.locator('[data-bundle-field="maxInputTokens"]').inputValue(),'512'); checked('Sana owns editable CFG and input token settings');
  await useCfg.check(); await negative.fill('explicit negative conditioning'); assert(await negative.isEnabled()); checked('Sana allows explicit CFG and negative conditioning without discarding text');
  await overflow(page,'Sana mobile task');
  await page.keyboard.press('Escape'); await page.locator('[data-task="video"]').click();
  await page.locator('[data-action="bundleUse"][data-id="ui_sampling_wan"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e => {e.open=true;});
  assert.equal(await page.locator('[name="taskType"]').inputValue(),'video.generate'); assert.equal(await page.locator('[data-bundle-field="frames"]').inputValue(),'17'); assert.equal(await page.locator('[data-bundle-field="flowShift"]').inputValue(),'3'); checked('Wan uses the same task form with explicit video frames and flow shift');
  await overflow(page,'Wan video task');
  assert.equal(await downloads(),before); checked('Sampling forms never initiate model downloads');
  await page.keyboard.press('Escape'); await page.locator('[data-task="any"]').click();
};
module.exports.installFixture=installFixture;
