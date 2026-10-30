/* Current production screens; simulated bridge and installation, no model downloads or inference. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/model-bundles.json'),'utf8')).bundles.find(b=>b.pipeline==='sana_sprint_06b_mnn_v1');
function installSana(manifest) {
  const f=window.__fixture, components=manifest.components.map(c=>({...c,reusable:false,downloadable:!!c.url})),total=components.reduce((n,c)=>n+c.bytes,0);
  f.bundles.push({id:manifest.id,manifest,inputSchemas:{'image.generate':{version:1,roles:{},negativePrompt:false}},installed:false,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:0,remainingBytes:total,components}});
  f.localEngines.push({engine:'mnn_diffusion',available:true,deviceValidated:false});window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,out,capture=async()=>{}) {
  await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(installSana,manifest);
  const commands=action=>page.evaluate(action=>window.__commands.filter(c=>c.action===action),action),id=manifest.id;
  const before=await commands('downloadBundle');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="image"]').click();
  assert.equal(await page.locator('[data-bundle="'+id+'"]').count(),0);checked('Uninstalled Sana-Sprint is excluded from Local');
  await page.locator('[data-filter="all"]').click();
  assert.equal(await page.locator('[data-bundle="'+id+'"]').count(),1);checked('All exposes Sana-Sprint as a flat image-model peer');
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('#modal .bundle-components details').count(),14);checked('Sana-Sprint discloses fourteen independently pinned components');
  assert.match(await page.locator('#modal').innerText(),/6.29 GiB/);assert.match(await page.locator('#modal').innerText(),/Gemma/);checked('Component review discloses asset size, variant and separate Gemma terms');
  assert.deepEqual(await commands('downloadBundle'),before);checked('Sana browsing and component review never implicitly download assets');
  await capture('01-sana-components.png','UI FIXTURE · Sana-Sprint 14 components / 用户选择，未下载权重');
  await page.locator('#modal [data-action="downloadBundle"]').click();
  await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),id);
  assert.deepEqual((await commands('downloadBundle')).slice(before.length).map(c=>c.id),[id]);checked('Explicit confirmation downloads exactly the selected Sana bundle');
  await page.keyboard.press('Escape');await page.locator('[data-filter="local"]').click();
  await page.locator('[data-bundle="'+id+'"] [data-action="pauseBundle"]').click();await page.waitForFunction(id=>window.__fixture.bundles.find(b=>b.id===id).transfer.state==='paused',id);checked('Unfinished Sana transfer remains visible and can be paused in Local');
  // Installation is a labelled fixture state; no placeholder weights or generated image.
  await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);b.installed=true;delete b.transfer;window.LMA.receive(window.__fixture);},id);
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleInfo"]').first().click();await page.locator('#modal [data-action="bundleSettings"]').click();
  const field=name=>page.locator('[data-bundle-field="'+name+'"]');
  await field('steps').fill('999');await field('steps').blur();assert.equal(await field('steps').inputValue(),'4');checked('Sana editable step selection clamps to four');
  await field('guidance').fill('999');await field('guidance').blur();assert.equal(await field('guidance').inputValue(),'30');checked('Sana embedded guidance clamps to thirty');
  await field('width').fill('2048');await field('width').blur();assert.equal(await field('width').inputValue(),'1024');checked('Sana export-fixed width fills back to 1024');
  await field('steps').fill('3');await field('steps').blur();await field('guidance').fill('7');await field('guidance').blur();
  await capture('02-sana-settings.png','UI FIXTURE · editable per-model settings / 配方上限归位，非性能结果');
  await page.locator('#bundleSettingsForm [type="submit"]').click();
  await page.waitForFunction(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.steps===3,id);checked('Sana parameters save against its own model bundle');
  const saved=(await commands('saveBundleSettings')).at(-1);assert.equal(saved.id,id);assert.equal(saved.settings.guidance,7);checked('Saved Sana numeric settings use the shared model-settings command');
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleUse"]').click();
  assert(await page.locator('#localTaskForm [name="negativePrompt"]').isDisabled());assert(await page.locator('#localTaskForm [name="negativePrompt"]').isHidden());assert.equal(await page.locator('#localTaskForm [data-input-role]').count(),0);checked('Sana task disables and hides unsupported negative conditioning and has no image input');
  await page.locator('.task-parameters summary').click();assert.equal(await field('steps').inputValue(),'3');checked('Task starts from the saved Sana settings');
  await field('steps').fill('2');await field('steps').blur();await page.locator('#localTaskForm [name="prompt"]').fill('A small cabin beside a lake. Interface validation only.');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();await overflow(page,'375px Sana-Sprint task and parameter form');
  await capture('03-sana-task.png','UI FIXTURE · local Sana-Sprint task / 仅提交交互，不执行完整模型');
  await page.locator('#localTaskForm [type="submit"]').click();await page.waitForSelector('#page-tasks.active .job-card');
  const request=(await commands('submitTask')).at(-1).request;
  assert.equal(request.bundleId,id);assert.equal(request.type,'image.generate');assert.equal(request.parameters.steps,2);assert.equal(request.parameters.width,1024);checked('Sana submission freezes its selected bundle and effective parameters in the shared queue');
  assert.equal(await page.evaluate(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.steps,id),3);checked('Per-task changes leave saved Sana settings intact');
  assert.equal(await page.evaluate(()=>window.__fixture.bundles.find(b=>b.id==='ui_sd').config.values.steps),4);checked('Sana settings cannot change another image model');
  await capture('04-sana-queue.png','UI FIXTURE · shared queue / 未生成图片，无真机或完整模型验证');
  assert.deepEqual((await commands('downloadBundle')).slice(before.length).map(c=>c.id),[id]);checked('Sana settings and task submission create no additional asset downloads');
};
