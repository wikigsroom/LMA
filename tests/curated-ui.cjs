/* Exact shipped metadata with an explicitly simulated native bridge; no weights/inference. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const catalogue=JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/model-bundles.json'),'utf8')).bundles;
const fixtureData={manifests:catalogue,legacyModels:JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models};
function installCatalogue({manifests,legacyModels}) {
  const f=window.__fixture;
  f.models=legacyModels.map(m=>({...m,installed:false,installedBytes:0,partialBytes:0,download:{}}));
  f.bundles=manifests.filter(m=>m.id==='sd15_ss_q4_0_r031b5f5'||m.id.endsWith('_catalogue_v1')).map(manifest=>{
    const components=manifest.components.map(c=>({...c,reusable:false,downloadable:!!c.url}));
    const total=components.reduce((n,c)=>n+c.bytes,0);
    return {id:manifest.id,manifest,installed:false,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:0,remainingBytes:total,components}};
  });
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}) {
  await page.keyboard.press('Escape');
  await page.evaluate(installFixture); await page.evaluate(installCatalogue,fixtureData);
  await page.locator('[data-tab="models"]').first().click(); await page.locator('[data-task="any"]').click(); await page.locator('[data-filter="recommended"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(nodes=>nodes.map(n=>n.dataset.model)),['m08','m06','m01']);checked('New curated peers preserve the exact Recommended order');
  await page.locator('[data-filter="all"]').click(); await page.locator('[data-task="image"]').click();
  assert.equal(await page.locator('[data-bundle]').count(),8); checked('All exposes eight complete optional diffusion profiles including FLUX.2-klein');
  const downloads=()=>page.evaluate(()=>window.__commands.filter(c=>c.action==='downloadBundle').map(c=>c.id));
  const start=await downloads();
  const cases=[['sd15_pixelart_redmond_catalogue_v1','sd15_ss_q4_0_r031b5f5'],['sdxl_pixelart_nerijs_catalogue_v1','sdxl_base_q4_0_catalogue_v1'],['sd15_lcm_lora_catalogue_v1','sd15_ss_q4_0_r031b5f5'],['sdxl_lcm_lora_catalogue_v1','sdxl_base_q4_0_catalogue_v1']];
  for (const [index,[adapter,base]] of cases.entries()) {
    const ceiling=catalogue.find(m=>m.id===adapter).parameters.fields.scale.maximum;
    if(index) { await page.evaluate(installFixture);await page.evaluate(installCatalogue,fixtureData);await page.locator('[data-tab="models"]').first().click();await page.locator('[data-filter="all"]').click(); }
    await page.locator('[data-action="bundleInfo"][data-id="'+adapter+'"]').first().click();
    assert.deepEqual(await page.locator('#modal [data-action="bundleDependencyInfo"]').evaluateAll(nodes=>nodes.map(n=>n.dataset.id)),[base]); checked(adapter+': dependency review excludes every incompatible peer');
    assert((await page.locator('#modal').innerText()).includes('不会自动下载基础模型'));checked(adapter+': separate user-controlled base installation is disclosed');
    if(index===1) await capture('01-dependency-review.png','SDXL LoRA dependency review · UI fixture / 尚未执行模型推理');
    await page.locator('#modal [data-action="bundleDependencyInfo"]').click();
    assert((await page.locator('#modal').innerText()).includes('clip_merges')); assert.equal(await page.locator('#modal [data-action="bundleInfo"][data-id="'+adapter+'"]').count(),1);checked(adapter+': base review shows its complete components and a return action');
    if(index===1) await capture('02-base-review.png','Complete base asset disclosure and explicit download · UI fixture / 下载未实际执行');
    assert.deepEqual(await downloads(),start.concat(index ? [cases[0][0],cases[0][1]] : []));
    if(index===0) {
      await page.locator('#modal [data-action="bundleInfo"][data-id="'+adapter+'"]').click();await page.locator('#modal [data-action="downloadBundle"]').click();
      await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),adapter);
      assert.deepEqual(await downloads(),start.concat(adapter));checked('Explicit LoRA download dispatches only that selected package');
    } else await page.keyboard.press('Escape');
    await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);b.installed=true;delete b.transfer;window.LMA.receive(window.__fixture);},adapter);
    await page.locator('[data-filter="local"]').click();await page.locator('[data-action="bundleUse"][data-id="'+adapter+'"]').click();
    assert.equal(await page.locator('#adapterPairForm [type="submit"]').count(),0);assert.equal(await page.locator('#adapterPairForm [data-action="bundleDependencyInfo"][data-id="'+base+'"]').count(),1);checked(adapter+': missing base blocks pairing and offers a direct review entry');
    if(index===0) {
      await page.locator('#adapterPairForm [data-action="bundleDependencyInfo"]').click();await page.locator('#modal [data-action="downloadBundle"]').click();
      await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),base);
      assert.deepEqual(await downloads(),start.concat(adapter,base));checked('Base download occurs only after a second explicit user action');
    } else await page.keyboard.press('Escape');
    await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);b.installed=true;delete b.transfer;window.LMA.receive(window.__fixture);},base);
    await page.locator('[data-action="bundleUse"][data-id="'+adapter+'"]').click();
    assert.deepEqual(await page.locator('#adapterPairForm option').evaluateAll(nodes=>nodes.map(n=>n.value)),[base]);await page.locator('#adapterPairForm [type="submit"]').click();checked(adapter+': installed exact App model identity is eligible for pairing');
    assert(await page.locator('[data-adapter-select="'+adapter+'"]').isChecked());
    await page.locator('[data-adapter-scale="'+adapter+'"]').fill('999');await page.locator('[data-adapter-scale="'+adapter+'"]').blur();
    assert.equal(await page.locator('[data-adapter-scale="'+adapter+'"]').inputValue(),String(ceiling));checked(adapter+': editable task strength clamps to this model ceiling');
    await page.locator('#localTaskForm [name="prompt"]').fill('Pixel art landscape; interface fixture only.');await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
    if(index===1) {await overflow(page,'375px real SDXL/LoRA manifest form');await capture('03-paired-task.png','Independent LoRA strength and local generation request · UI fixture / 未执行推理');}
    await page.locator('#localTaskForm [type="submit"]').click();await page.waitForSelector('#page-tasks.active .job-card');
    const request=await page.evaluate(()=>window.__commands.findLast(c=>c.action==='submitTask').request);
    assert.equal(request.bundleId,base);assert.deepEqual(request.adapters,[{bundleId:adapter,scale:ceiling}]);checked(adapter+': shared queue receives frozen base/adapter IDs and explicit strength');
    assert.equal(await page.evaluate(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.scale,adapter),1);checked(adapter+': task edits preserve independent saved model settings');
    if(adapter.includes('_lcm_')) {assert.equal(request.parameters.steps,8);assert.equal(request.parameters.cfg,1);checked(adapter+': explicit low-step LCM policy survives task submission');}
    if(index===1) await capture('04-queued-task.png','Persistent task queue interaction · UI fixture / 无训练输出或 Android 证据');
  }
  assert.deepEqual(await downloads(),start.concat(cases[0][0],cases[0][1]));checked('Remaining dependency browsing, pairing and queued tasks issue zero implicit downloads');
  await page.evaluate(installFixture);await page.evaluate(installCatalogue,fixtureData);
  const flux='flux2_klein4b_q4_0_catalogue_v1',fluxBefore=await downloads();
  await page.locator('[data-tab="models"]').first().click();await page.locator('[data-filter="all"]').click();await page.locator('[data-task="image"]').click();
  await page.locator('[data-action="bundleInfo"][data-id="'+flux+'"]').first().click();
  assert.equal(catalogue.find(m=>m.id===flux).components.length,4);assert((await page.locator('#modal').innerText()).includes('Q4_0'));checked('FLUX catalogue entry exposes complete four-component optional download');
  assert.deepEqual(await downloads(),fluxBefore);checked('Viewing FLUX metadata starts no transfer');
  await overflow(page,'FLUX complete metadata');await capture('05-flux2-components.png','FLUX.2-klein four complete optional components · UI fixture / 尚未执行模型');
  await page.locator('#modal [data-action="downloadBundle"]').click();await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),flux);
  assert.deepEqual(await downloads(),fluxBefore.concat(flux));checked('One explicit FLUX download chooses only this model bundle');
  await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);b.installed=true;delete b.transfer;window.LMA.receive(window.__fixture);},flux);
  await page.locator('[data-filter="local"]').click();await page.locator('[data-action="bundleInfo"][data-id="'+flux+'"]').first().click();
  await page.locator('#modal [data-action="bundleSettings"]').click();
  await page.locator('#bundleSettingsForm [data-bundle-field="steps"]').fill('999');await page.locator('#bundleSettingsForm [data-bundle-field="steps"]').blur();
  assert.equal(await page.locator('#bundleSettingsForm [data-bundle-field="steps"]').inputValue(),'4');checked('FLUX editable per-model steps clamp to its four-step ceiling');
  await page.keyboard.press('Escape');await page.locator('[data-action="bundleUse"][data-id="'+flux+'"]').click();
  await page.locator('#localTaskForm .task-parameters').evaluate(e=>{e.open=true;});
  assert(await page.locator('#localTaskForm [name="negativePrompt"]').isDisabled());assert.equal(await page.locator('[data-bundle-field="scheduler"] option:checked').textContent(),'flux2');checked('Actual FLUX form binds distilled scheduler and disables unsupported negative conditioning');
  await page.locator('#localTaskForm [name="prompt"]').fill('A red toy robot beside a blue teapot. UI fixture only.');await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  await overflow(page,'FLUX generation');await capture('06-flux2-task.png','FLUX.2-klein independent model parameters · UI fixture / 本页不执行推理');
  await page.locator('#localTaskForm [type="submit"]').click();await page.waitForSelector('#page-tasks.active .job-card');
  const fluxRequest=await page.evaluate(()=>window.__commands.findLast(c=>c.action==='submitTask').request);
  assert.equal(fluxRequest.bundleId,flux);assert.equal(fluxRequest.parameters.steps,4);assert.equal(fluxRequest.parameters.cfg,1);assert.equal(fluxRequest.parameters.scheduler,'flux2');checked('FLUX submits immutable selected model and distilled parameters through shared task queue');
  assert.deepEqual(await downloads(),fluxBefore.concat(flux));checked('Settings, Local view and task submission never download a second model');
};
module.exports.installCatalogue=installCatalogue;
