/* Current production screens; simulated bridge and installation, no model downloads or inference. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/model-bundles.json'),'utf8')).bundles.find(b=>b.pipeline==='ltx098_pixart_multiscale_v1');
function installLtxOfficial(manifest) {
  // Twenty prepared DiT/VAE components already exist in this explicit fixture;
  // only seven original publisher dependencies can be downloaded by this bundle.
  const f=window.__fixture, components=manifest.components.map(c=>({...c,reusable:!c.url,downloadable:!!c.url})),total=components.reduce((n,c)=>n+c.bytes,0),reusable=components.filter(c=>c.reusable).reduce((n,c)=>n+c.bytes,0);
  f.bundles.push({id:manifest.id,manifest,inputSchemas:{'video.generate':{version:1,roles:{},negativePrompt:false}},installed:false,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:reusable,remainingBytes:total-reusable,components}});
  f.localEngines.push({engine:'ltx098_native',available:true,deviceValidated:false});window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,out,capture=async()=>{}) {
  await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(installLtxOfficial,manifest);
  const commands=action=>page.evaluate(action=>window.__commands.filter(c=>c.action===action),action),id=manifest.id;
  const before=await commands('downloadBundle');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="video"]').click();
  assert.equal(await page.locator('[data-bundle="'+id+'"]').count(),0);checked('Uninstalled LTX PixArt multiscale is excluded from Local');
  await page.locator('[data-filter="all"]').click();
  assert.equal(await page.locator('[data-bundle="'+id+'"]').count(),1);checked('All exposes LTX PixArt multiscale as a flat video-model peer');
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('#modal .bundle-components details').count(),27);checked('LTX PixArt multiscale discloses twenty-seven independently pinned components');
  assert.match(await page.locator('#modal').innerText(),/25.62 GB/);assert.match(await page.locator('#modal').innerText(),/PixArt/);checked('Component review discloses asset size, variant and original PixArt F32 identity');
  assert.deepEqual(await commands('downloadBundle'),before);checked('LTX browsing and component review never implicitly download assets');
  await capture('01-ltx-official-components.png','UI FIXTURE · LTX PixArt multiscale 27 components / 用户选择，未下载权重');
  await page.locator('#modal [data-action="downloadBundle"]').click();
  await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),id);
  assert.deepEqual((await commands('downloadBundle')).slice(before.length).map(c=>c.id),[id]);checked('Explicit confirmation downloads exactly the selected LTX bundle');
  await page.keyboard.press('Escape');await page.locator('[data-filter="local"]').click();
  await page.locator('[data-bundle="'+id+'"] [data-action="pauseBundle"]').click();await page.waitForFunction(id=>window.__fixture.bundles.find(b=>b.id===id).transfer.state==='paused',id);checked('Unfinished LTX transfer remains visible and can be paused in Local');
  // Installation is a labelled fixture state; no placeholder weights or generated image.
  await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);b.installed=true;delete b.transfer;window.LMA.receive(window.__fixture);},id);
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleInfo"]').first().click();await page.locator('#modal [data-action="bundleSettings"]').click();
  const field=name=>page.locator('[data-bundle-field="'+name+'"]');
  await field('steps').fill('999');await field('steps').blur();assert.equal(await field('steps').inputValue(),'10');checked('LTX editable step selection stays at its fixed ten steps');
  await field('fps').fill('999');await field('fps').blur();assert.equal(await field('fps').inputValue(),'60');checked('LTX frame rate clamps to sixty');
  await field('frames').fill('100');await field('frames').blur();assert.equal(await field('frames').inputValue(),'33');checked('Video frame count clamps to its model bound');
  await field('width').fill('2048');await field('width').blur();assert.equal(await field('width').inputValue(),'256');checked('LTX width clamps back to 256');
  await field('steps').fill('10');await field('steps').blur();await field('fps').fill('24');await field('fps').blur();
  await capture('02-ltx-official-settings.png','UI FIXTURE · editable per-model settings / 配方上限归位，非性能结果');
  await page.locator('#bundleSettingsForm [type="submit"]').click();
  await page.waitForFunction(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.steps===10,id);checked('LTX parameters save against its own model bundle');
  const saved=(await commands('saveBundleSettings')).at(-1);assert.equal(saved.id,id);assert.equal(saved.settings.fps,24);checked('Saved LTX numeric settings use the shared model-settings command');
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleUse"]').click();
  assert(await page.locator('#localTaskForm [name="negativePrompt"]').isDisabled());assert(await page.locator('#localTaskForm [name="negativePrompt"]').isHidden());assert.equal(await page.locator('#localTaskForm [data-input-role]').count(),0);checked('LTX task disables and hides unsupported negative conditioning and has no image input');
  await page.locator('.task-parameters summary').click();assert.equal(await field('steps').inputValue(),'10');checked('Task starts from the saved LTX settings');
  await field('frames').fill('17');await field('frames').blur();await page.locator('#localTaskForm [name="prompt"]').fill('A small cabin beside a lake. Interface validation only.');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();await overflow(page,'375px LTX PixArt multiscale task and parameter form');
  await capture('03-ltx-official-task.png','UI FIXTURE · local LTX PixArt multiscale task / 仅提交交互，不执行完整模型');
  await page.locator('#localTaskForm [type="submit"]').click();await page.waitForSelector('#page-tasks.active .job-card');
  const request=(await commands('submitTask')).at(-1).request;
  assert.equal(request.bundleId,id);assert.equal(request.type,'video.generate');assert.equal(request.parameters.steps,10);assert.equal(request.parameters.width,256);assert.equal(request.parameters.frames,17);checked('LTX submission freezes its selected bundle and effective parameters in the shared queue');
  assert.equal(await page.evaluate(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.frames,id),33);checked('Per-task changes leave saved LTX settings intact');
  assert.equal(await page.evaluate(()=>window.__fixture.bundles.find(b=>b.id==='ui_sd').config.values.steps),4);checked('LTX settings cannot change another model');
  await capture('04-ltx-official-queue.png','UI FIXTURE · shared queue / 未生成视频，无真机或完整模型验证');
  await page.locator('.job-card [data-action="cancelTask"]').first().click();await page.waitForFunction(()=>window.__commands.some(c=>c.action==='cancelTask'));checked('Video tasks expose cancellation through the shared queue');
  assert.deepEqual((await commands('downloadBundle')).slice(before.length).map(c=>c.id),[id]);checked('LTX settings and task submission create no additional asset downloads');
};
