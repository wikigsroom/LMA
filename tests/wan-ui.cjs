/* Actual shipped model metadata and production UI; explicitly simulated bridge, no inference. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../research/wan_trained/catalogue-bundle.json'),'utf8'));
function installWan(model) {
  const f=window.__fixture;
  const components=model.components.map(c=>({...c,reusable:false,downloadable:true}));
  const total=components.reduce((n,c)=>n+c.bytes,0);
  f.bundles=[{id:model.id,manifest:model,installed:false,config:{values:Object.fromEntries(Object.entries(model.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:0,remainingBytes:total,components}}];
  f.localEngines.push({engine:'wan_sd_cpp',available:true,deviceValidated:false});
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}) {
  await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(installWan,manifest);
  const id=manifest.id,downloads=()=>page.evaluate(()=>window.__commands.filter(c=>c.action==='downloadBundle').map(c=>c.id));
  const before=await downloads();
  await page.locator('[data-tab="models"]').first().click();await page.locator('[data-filter="all"]').click();await page.locator('[data-task="video"]').click();
  await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').first().click();
  assert.equal(manifest.components.length,4);assert.equal(manifest.backend,'vulkan');assert.equal(manifest.components.reduce((n,c)=>n+c.bytes,0),4741874667);
  assert.deepEqual(await downloads(),before);checked('Video peer exposes all four complete optional user assets without a download');
  await overflow(page,'Wan model metadata');await capture('01-components.png','Wan complete selected components / production UI fixture, no download or phone inference');
  await page.locator('#modal [data-action="downloadBundle"]').click();await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),id);
  assert.deepEqual(await downloads(),before.concat(id));checked('Explicit download selects only the chosen video model');
  await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);b.installed=true;delete b.transfer;window.LMA.receive(window.__fixture);},id);
  await page.locator('[data-filter="local"]').click();await page.locator('[data-action="bundleInfo"][data-id="'+id+'"]').first().click();await page.locator('#modal [data-action="bundleSettings"]').click();
  for(const [field,value] of [['steps','200'],['frames','129'],['fps','60']]) {
    await page.locator('#bundleSettingsForm [data-bundle-field="'+field+'"]').fill('999');await page.locator('#bundleSettingsForm [data-bundle-field="'+field+'"]').blur();
    assert.equal(await page.locator('#bundleSettingsForm [data-bundle-field="'+field+'"]').inputValue(),value);
  }
  checked('Editable per-model video steps, frame count and frame rate clamp to declared ceilings');
  await overflow(page,'Wan per-model settings');await capture('02-settings.png','Independent editable video settings / production UI fixture');
  await page.keyboard.press('Escape');await page.locator('[data-action="bundleUse"][data-id="'+id+'"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});
  await page.locator('#localTaskForm [name="prompt"]').fill('A small red robot waves beside a blue teapot. Interface fixture only.');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  assert.equal(await page.locator('[data-bundle-field="scheduler"] option:checked').textContent(),'discrete');
  await overflow(page,'Wan shared generation form');await capture('03-task.png','Video prompt and shared model parameter form / no model execution');
  await page.locator('#localTaskForm [type="submit"]').click();await page.waitForSelector('#page-tasks.active .job-card');
  const request=await page.evaluate(()=>window.__commands.findLast(c=>c.action==='submitTask').request);
  assert.equal(request.type,'video.generate');assert.equal(request.bundleId,id);
  assert.equal(request.parameters.steps,20);assert.equal(request.parameters.frames,17);assert.equal(request.parameters.fps,8);assert.equal(request.parameters.flowShift,3);
  checked('Shared task queue retains selected model identity and exact video parameters');
  assert.deepEqual(await downloads(),before.concat(id));checked('Settings, Local management and task submission issue no implicit second download');
  await capture('04-queued.png','Shared persistent video queue / simulated bridge, not execution evidence');
};
