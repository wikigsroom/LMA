/* Production UI with explicit desktop bridge data; no inference or Android device. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
function data(){
  const all=JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/model-bundles.json'),'utf8')).bundles;
  return {target:all.find(b=>b.id==='ltx098_runtime_google_q5_v2'),old:all.find(b=>b.id==='ltx098_runtime_google_q5_v1')};
}
function install(payload){
  const f=window.__fixture;
  const entry=manifest=>{const total=manifest.components.reduce((n,c)=>n+c.bytes,0);return {id:manifest.id,manifest,installed:true,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields||{}).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:total,remainingBytes:0,components:manifest.components.map(c=>({...c,reusable:true,downloadable:!!c.url}))},inputSchemas:{'video.generate':{roles:{}}}};};
  f.bundles=[entry(payload.target),entry(payload.old)];f.localEngines=[{engine:'ltx098_native',available:true,requiredModelCapability:'text_to_video',deviceValidated:false}];
  f.jobs=[];f.artifacts=[];f.taskDrafts=[];window.LMA.receive(f);
}
async function acknowledged(page,action){await page.waitForFunction(action=>{const commands=window.__commands.filter(c=>c.action===action),last=commands[commands.length-1];return last&&(window.__fixture.commandResults||[]).some(r=>r.requestId===last.requestId);},action);}
module.exports=async function(page,checked,overflow,output,shot=async()=>{}){
  await page.evaluate(installFixture);const payload=data();assert(payload.target&&payload.old);await page.evaluate(install,payload);
  const before=await page.evaluate(()=>window.__commands.length);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="any"]').click();
  assert.equal(await page.locator('[data-bundle="'+payload.old.id+'"] [data-action="bundleUse"]').isDisabled(),true);
  assert.equal(await page.locator('[data-bundle="'+payload.target.id+'"] [data-action="bundleUse"]').isDisabled(),false);
  checked('Old LTX asset-only records remain unchanged; only the explicitly associated generation variant can start');
  await page.locator('[data-bundle="'+payload.target.id+'"] [data-action="bundleInfo"]').click();
  const info=await page.locator('#modalContent').textContent();assert.match(info,/Google/);assert.match(info,/数值/);assert.match(info,/画质/);
  await overflow(page,'375px LTX profile and component review');await shot('01-model-profile.png','UI FIXTURE · Explicit old-LTX variant and open quality gates / 旧 LTX 变体与未通过的画质门槛');
  checked('The selected model discloses its exact community T5 variant and unaccepted numerical and quality status');
  await page.locator('#modalContent [data-action="bundleSettings"]').click();
  const width=page.locator('[data-bundle-field="width"]');assert(await width.getAttribute('list'));await width.fill('9999');await width.blur();assert.equal(await width.inputValue(),'256');
  for(const [key,value] of [['frames','33'],['steps','8']]){const field=page.locator('[data-bundle-field="'+key+'"]');await field.fill('9999');await field.blur();assert.equal(await field.inputValue(),value);}
  checked('Editable model presets clamp excessive width, frame count and fixed distilled steps to declared limits');
  await page.locator('[data-bundle-field="seed"]').fill('42');await page.locator('[data-bundle-field="seed"]').blur();
  await overflow(page,'375px LTX independent model settings');await shot('02-model-settings.png','UI FIXTURE · Editable presets with model-specific bounds / 可编辑预设与模型独立上限');
  await page.locator('#bundleSettingsForm [type="submit"]').click();await acknowledged(page,'saveBundleSettings');
  assert.equal(await page.evaluate(()=>window.__fixture.bundles[0].config.values.seed),42);assert.equal(await page.evaluate(()=>Object.keys(window.__fixture.bundles[1].config.values).length),0);
  checked('Saving new LTX settings preserves the historical asset record and its independent configuration');
  await page.locator('[data-bundle="'+payload.target.id+'"] [data-action="bundleUse"]').click();
  await page.locator('[name="prompt"]').fill('A red balloon floats slowly across a blue sky. · 本地视频界面演示');
  assert.equal(await page.locator('[data-adapter-select]').count(),0);assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false);await page.locator('[name="allowUnmeasured"]').check();
  await page.locator('.task-parameters summary').click();assert.equal(await page.locator('[data-bundle-field="steps"]').inputValue(),'8');
  await overflow(page,'375px explicit local video request');await shot('03-video-request.png','UI FIXTURE · Explicit video request and user-selected parameters / 用户明确提交本地视频任务');
  await page.locator('#localTaskForm [type="submit"]').click();await page.waitForFunction(()=>window.__fixture.jobs.some(j=>j.request.type==='video.generate'));await acknowledged(page,'submitTask');
  const request=await page.evaluate(()=>window.__fixture.jobs.find(j=>j.request.type==='video.generate').request);assert.equal(request.bundleId,payload.target.id);assert.equal(request.parameters.steps,8);assert.equal(request.parameters.frames,33);assert.equal(request.parameters.seed,42);assert.equal(request.allowUnmeasured,true);
  checked('Video generation uses the shared task submission path with explicit trial consent, fixed eight steps and no image LoRA');
  await page.evaluate(()=>{const f=window.__fixture;f.bundles[0].config.values.seed=43;const j=f.jobs.find(j=>j.request.type==='video.generate');j.state='running';j.stage='video_sampling';window.LMA.receive(f);});
  assert.equal(await page.evaluate(()=>window.__fixture.jobs.find(j=>j.request.type==='video.generate').request.parameters.seed),42);
  checked('An accepted task keeps its captured parameters when future model settings change');
  await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="filterJobs"][data-kind="all"]').click();assert.match(await page.locator('#page-tasks').textContent(),/生成视频/);
  await overflow(page,'375px shared video queue');await shot('04-video-queue.png','UI FIXTURE · Shared queue, video stage and cancellation / 共用队列、视频阶段与取消');
  await page.locator('[data-action="cancelTask"]').click();await page.waitForFunction(()=>window.__fixture.jobs.find(j=>j.request.type==='video.generate').state==='cancelled');await acknowledged(page,'cancelTask');
  checked('The shared queue displays video progress and dispatches explicit cancellation');
  const commands=await page.evaluate(n=>window.__commands.slice(n),before);assert.equal(commands.filter(c=>/download|import|prepareAssets|assembleAssets|deleteBundle/.test(c.action)).length,0);assert.equal(await page.evaluate(()=>window.__fixture.bundles.every(b=>b.installed)),true);
  checked('Browsing, settings, submission and cancellation retrieve no model data and preserve installed assets');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();
};
