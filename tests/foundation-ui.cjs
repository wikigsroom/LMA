/* Product interaction regression with explicit data fixtures, never inference evidence. */
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');

function installFixture() {
    const field = (value, min, max, presets) => ({type: 'integer', default: value, minimum: min, maximum: max, multipleOf: 64, presets});
    const manifest = {schema: 'lma.model-bundle/1', id: 'ui_sd', modelId: 'ui_sd_model', recipeId: 'ui_recipe_v1', engine: 'sd_cpp', architecture: 'sd15', pipeline: 'sd15', backend: 'cpu', name: '图像模型 · 界面测试数据', description: '仅验证界面，不代表手机推理结果。', tasks: ['image'], capabilities: ['text_to_image'], license: 'UI fixture; no weights', components: [{role: 'model', path: 'model.gguf', bytes: 1000, sha256: '0'.repeat(64), url: 'https://example.invalid/model.gguf', format: 'gguf'}, {role: 'clip_merges', path: 'merges.txt', bytes: 200, sha256: '1'.repeat(64), url: 'https://example.invalid/merges.txt', format: 'text'}], parameters: {version: 1, fields: {width: field(512, 64, 768, [256, 512, 768]), height: field(512, 64, 768, [256, 512, 768]), steps: {type: 'integer', default: 4, minimum: 1, maximum: 30, presets: [4, 8, 20, 30]}}, allowedShapes: [{width: 512, height: 512}, {width: 768, height: 768}]}};
    const entry = {id: manifest.id, manifest, installed: false, config: {values: {width: 512, height: 512, steps: 4}}, plan: {totalBytes: 1200, reusableBytes: 200, remainingBytes: 1000, components: manifest.components.map(c => ({...c, reusable: c.role === 'clip_merges', downloadable: true}))}};
    window.__fixture.bundles = [entry]; window.__fixture.jobs = []; window.__fixture.artifacts = []; window.__fixture.localEngines = [{engine: 'sd_cpp', available: true, deviceValidated: false}];
    window.__handleFoundation = command => {
      const f = window.__fixture, b = f.bundles.find(x => x.id === command.id);
      if (command.action === 'downloadBundle') b.transfer = {state: 'downloading', role: 'model', received: 100};
      if (command.action === 'pauseBundle') b.transfer.state = 'paused';
      if (command.action === 'saveBundleSettings') b.config.values = command.settings;
      if (command.action === 'submitTask') {
        const job = {id: 'ui_job', state: 'queued', stage: 'queued', createdAt: Date.now(), error: '', request: {...command.request, inputSummary: command.request.input.prompt}, artifacts: []};
        f.jobs = [job]; return job;
      }
      if (command.action === 'cancelTask') f.jobs.find(j => j.id === command.id).state = 'cancelled';
      if (command.action === 'deleteTask') f.jobs = f.jobs.filter(j => j.id !== command.id);
      if (command.action === 'inspectTask') return f.jobs.find(j => j.id === command.id);
      if (command.action === 'deleteBundle') { b.installed = false; delete b.transfer; }
    };
    window.LMA.receive(window.__fixture);
}
function installSpeechFixture(manifest) {
  const values = Object.fromEntries(Object.entries(manifest.parameters.fields).map(([key, field]) => [key, field.default]));
  const components = manifest.components.map(c => ({...c, reusable: true, downloadable: true}));
  const total = components.reduce((sum, c) => sum + c.bytes, 0);
  window.__fixture.bundles.push({id: manifest.id, manifest, installed: true, config: {values}, plan: {totalBytes: total, reusableBytes: total, remainingBytes: 0, components}});
  window.__fixture.localEngines.push({engine: 'sherpa_tts', available: true, deviceValidated: false});
  window.LMA.receive(window.__fixture);
}
function installAdapterFixture() {
  const base = window.__fixture.bundles.find(b => b.id === 'ui_sd'); base.installed = true;
  const xl = JSON.parse(JSON.stringify(base)); xl.id = xl.manifest.id = xl.manifest.modelId = 'ui_sdxl'; xl.manifest.name = 'SDXL 基础模型 · 界面占位'; xl.manifest.architecture = xl.manifest.pipeline = 'sdxl'; xl.installed = false;
  window.__fixture.bundles.push(xl);
  for (const arch of ['sd15', 'sdxl']) {
    const id = 'ui_lora_' + arch;
    const manifest = {schema: 'lma.model-bundle/1', id, modelId: id, recipeId: id + '_v1', engine: 'sd_cpp', architecture: arch, pipeline: 'lora', backend: 'cpu', name: arch.toUpperCase() + ' LoRA · 界面占位', description: 'LoRA 配对界面测试，未下载权重、未生成图像。', tasks: ['image'], capabilities: ['image_adapter'], adapter: {schema: 'lma.adapter/1', kind: 'lora', baseArchitectures: [arch], basePipelines: [arch]}, parameters: {version: 1, fields: {scale: {type: 'number', label: 'LoRA 强度', default: 0.75, minimum: -2, maximum: 2, presets: [0.5, 0.75, 1]}}}, components: [{role: 'lora', path: 'fixture.safetensors', format: 'safetensors', bytes: 300, sha256: (arch === 'sd15' ? '2' : '3').repeat(64)}]};
    window.__fixture.bundles.push({id, manifest, installed: true, config: {values: {scale: 0.75}}, plan: {totalBytes: 300, reusableBytes: 300, remainingBytes: 0, components: manifest.components.map(c => ({...c, reusable: true, downloadable: false}))}});
  }
  window.LMA.receive(window.__fixture);
}
module.exports = async function (page, checked, checkOverflow, output) {
  await page.evaluate(installFixture);
  await page.locator('.nav-item[data-tab="models"]').click();
  await page.locator('[data-filter="recommended"]').click();
  await page.locator('[data-task="any"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(nodes => nodes.map(x => x.dataset.model)), ['m08', 'm06', 'm01']); checked('Media bundle entries preserve the curated recommendation IDs and order');
  const before = await page.evaluate(() => window.__commands.filter(c => /Bundle|Task/.test(c.action)).length);
  await page.evaluate(() => { window.__fixture.bundles[0].manifest.catalogue = true; window.LMA.receive(window.__fixture); });
  await page.locator('[data-filter="all"]').click(); await page.locator('[data-task="image"]').click();
  assert.equal(await page.locator('.bundle-card').count(), 1); checked('Pinned bundle metadata is discoverable in All independently of HF repository results');
  await page.locator('[data-filter="local"]').click();
  assert.equal(await page.locator('.bundle-card').count(), 0); checked('Unselected catalogue recipes do not masquerade as downloaded Local models');
  await page.evaluate(() => { window.__fixture.bundles[0].manifest.catalogue = false; window.LMA.receive(window.__fixture); });
  await page.locator('[data-filter="local"]').click();
  await page.locator('[data-task="image"]').click();
  assert.equal(await page.locator('.bundle-card').count(), 1);
  assert.equal(await page.locator('#modelList .task-image').count(), 1);
  assert.equal(await page.evaluate(() => window.__commands.filter(c => /Bundle|Task/.test(c.action)).length), before); checked('Browsing and filtering a flat model pool starts no model transfers');
  await page.locator('[data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('.bundle-components details').count(), 2);
  assert((await page.locator('.model-info').textContent()).includes('可复用资产'));
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle').length), 0); checked('Complete bundle dependencies and reuse are shown before explicit download');
  await page.locator('[data-action="downloadBundle"]').click();
  await page.waitForSelector('[data-action="pauseBundle"]');
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle').length), 1); checked('Explicit download selects exactly one bundle');
  await page.locator('[data-action="pauseBundle"]').click();
  await page.waitForSelector('.bundle-card .model-tags .tag:text-is("已暂停")'); checked('Bundle transfers expose an independent pause state');
  await page.evaluate(() => { window.__fixture.bundles[0].installed = true; delete window.__fixture.bundles[0].transfer; window.LMA.receive(window.__fixture); });
  await page.locator('[data-action="bundleInfo"]').first().click();
  await page.locator('[data-action="bundleSettings"]').click();
  const textConfigs = await page.evaluate(() => JSON.stringify(window.__fixture.models.map(m => m.config)));
  await page.locator('[data-bundle-field="width"]').fill('99999');
  await page.locator('[data-bundle-field="width"]').blur();
  assert.equal(await page.locator('[data-bundle-field="width"]').inputValue(), '768');
  assert((await page.locator('#bundleFormHint').textContent()).includes('组合')); checked('Media parameter maxima clamp while rejecting unsupported joint shapes');
  await page.locator('#bundleShape').selectOption('1');
  assert.equal(await page.locator('[data-bundle-field="height"]').inputValue(), '768');
  await page.locator('#bundleSettingsForm [type="submit"]').click();
  await page.waitForFunction(() => document.getElementById('modalBackdrop').hidden);
  assert.equal(await page.evaluate(() => window.__fixture.bundles[0].config.values.width), 768);
  assert.equal(await page.evaluate(() => JSON.stringify(window.__fixture.models.map(m => m.config))), textConfigs); checked('Compiled shape selection saves only the selected bundle settings');
  await page.locator('[data-action="bundleUse"]').click();
  await page.locator('#localTaskForm [name="prompt"]').fill('<img src=x onerror="window.__pwned=true"> 本地测试输入');
  await page.locator('#localTaskForm [type="submit"]').click();
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'submitTask').length), 0); checked('Unmeasured recipe execution requires the explicit user choice');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  await page.locator('#localTaskForm [type="submit"]').click();
  await page.waitForSelector('#page-tasks.active .job-card');
  const request = await page.evaluate(() => window.__commands.findLast(c => c.action === 'submitTask').request);
  assert.equal(request.bundleId, 'ui_sd'); assert.equal(request.parameters.width, 768); assert.equal(request.allowUnmeasured, true);
  assert.equal(await page.evaluate(() => window.__pwned), false); checked('Task form submits a parameter snapshot and escapes the queue prompt');
  await checkOverflow(page, '375px task queue layout');
  await page.screenshot({path: path.join(output, '08-tasks-phone.png')});
  await page.locator('[data-action="jobInfo"]').click(); await page.waitForSelector('.task-detail');
  assert((await page.locator('.provenance').textContent()).includes('ui_job')); checked('Task details use the matching native command result');
  await page.locator('[data-action="closeModal"]').click();
  await page.locator('[data-action="cancelTask"]').click();
  await page.waitForSelector('.job-card .status-pill:text-is("已取消")');
  assert.equal(await page.locator('[data-action="retryTask"]').count(), 1); checked('Cancelled jobs remain explicit retriable records');
  await page.locator('[data-action="deleteTask"]').click(); await page.waitForSelector('#jobList .empty-list'); checked('Removing a terminal job restores the empty queue');
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="any"]').click();
  const speech = JSON.parse(fs.readFileSync(path.join(__dirname, '../app/src/main/assets/model-bundles.json'), 'utf8')).bundles.find(b => b.pipeline === 'kokoro');
  await page.evaluate(installSpeechFixture, speech);
  await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="audio"]').click();
  assert.equal(await page.locator('.bundle-card').count(), 1); assert((await page.locator('.bundle-card').textContent()).includes('生音频')); checked('User-installed speech model is a peer with audio and engine tags');
  await page.locator('[data-action="bundleUse"]').click();
  assert.equal(await page.locator('#localTaskForm [name="taskType"]').inputValue(), 'speech.synthesize');
  assert.equal(await page.locator('#localTaskForm [name="prompt"]').getAttribute('maxlength'), '4000');
  assert.equal(await page.locator('#localTaskForm [name="negativePrompt"]').count(), 0); checked('Speech form has bounded narration text and no ignored negative prompt');
  await page.locator('.task-parameters summary').click();
  await page.locator('[data-bundle-field="speaker"]').fill('999'); await page.locator('[data-bundle-field="speaker"]').blur();
  await page.locator('[data-bundle-field="speed"]').fill('99'); await page.locator('[data-bundle-field="speed"]').blur();
  assert.equal(await page.locator('[data-bundle-field="speaker"]').inputValue(), '53'); assert.equal(await page.locator('[data-bundle-field="speed"]').inputValue(), '3');
  assert((await page.locator('#localTaskForm').textContent()).includes('发布者声明上限（待核对）')); checked('Editable voice/speed presets clamp and label unverified publisher limits');
  await page.locator('#localTaskForm [name="prompt"]').fill('Hello world. This is an explicit UI fixture.');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  await checkOverflow(page, '375px speech task layout'); await page.screenshot({path: path.join(output, '09-tts-form.png')});
  await page.locator('#localTaskForm [type="submit"]').click(); await page.waitForSelector('#page-tasks.active .job-card');
  const speechRequest = await page.evaluate(() => window.__commands.findLast(c => c.action === 'submitTask').request);
  assert.equal(speechRequest.type, 'speech.synthesize'); assert.equal(speechRequest.input.negativePrompt, ''); assert.equal(speechRequest.parameters.speaker, 53); checked('Speech submits an independent parameter snapshot through the shared task queue');
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="any"]').click();
  await page.evaluate(installAdapterFixture); await page.locator('[data-task="image"]').click();
  assert.equal(await page.locator('.bundle-card').count(), 4);
  assert((await page.locator('[data-bundle="ui_lora_sd15"]').textContent()).includes('需要基础模型')); checked('LoRAs are flat peer image entries with explicit base-model dependency tags');
  const downloadsBeforePairing = await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle').length);
  await page.locator('[data-bundle="ui_lora_sdxl"] [data-action="bundleUse"]').click();
  assert((await page.locator('#adapterPairForm').textContent()).includes('尚未安装兼容'));
  assert.equal(await page.locator('#adapterPairForm [type="submit"]').count(), 0); checked('Missing compatible bases explain the requirement without choosing or downloading a model');
  await page.locator('#adapterPairForm [data-action="closeModal"]').click();
  await page.locator('[data-bundle="ui_lora_sd15"] [data-action="bundleUse"]').click();
  assert.deepEqual(await page.locator('#adapterPairForm option').evaluateAll(options => options.map(o => o.value)), ['ui_sd']); checked('SD 1.5 adapter picker excludes incompatible SDXL and audio peers');
  await page.locator('#adapterPairForm [type="submit"]').click();
  assert.equal(await page.locator('[data-adapter-select="ui_lora_sd15"]').isChecked(), true);
  assert.equal(await page.locator('[data-adapter-select="ui_lora_sdxl"]').count(), 0);
  await page.locator('[data-adapter-scale="ui_lora_sd15"]').fill('999'); await page.locator('[data-adapter-scale="ui_lora_sd15"]').blur();
  assert.equal(await page.locator('[data-adapter-scale="ui_lora_sd15"]').inputValue(), '2'); checked('Explicit adapter selection carries to the base task and clamps to its own limit');
  await page.locator('#localTaskForm [name="prompt"]').fill('只演示 LoRA 与基础模型配对，不生成占位图片。');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  await checkOverflow(page, '375px LoRA composition form'); await page.screenshot({path: path.join(output, '10-lora-form.png')});
  await page.locator('#localTaskForm [type="submit"]').click(); await page.waitForSelector('#page-tasks.active .job-card');
  const loraRequest = await page.evaluate(() => window.__commands.findLast(c => c.action === 'submitTask').request);
  assert.equal(loraRequest.bundleId, 'ui_sd'); assert.deepEqual(loraRequest.adapters, [{bundleId: 'ui_lora_sd15', scale: 2}]);
  assert.equal(await page.evaluate(() => window.__fixture.bundles.find(b => b.id === 'ui_lora_sd15').config.values.scale), 0.75); checked('Shared queue receives immutable base/adapter IDs and scales without changing saved settings');
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle').length), downloadsBeforePairing); checked('Adapter browsing and task composition create no model download commands');
  await page.evaluate(() => {window.__fixture.bundles.find(b => b.id === 'ui_sdxl').installed = true; window.LMA.receive(window.__fixture);});
  await page.locator('.nav-item[data-tab="models"]').click();
  await page.locator('[data-bundle="ui_lora_sdxl"] [data-action="bundleUse"]').click();
  assert.deepEqual(await page.locator('#adapterPairForm option').evaluateAll(options => options.map(o => o.value)), ['ui_sdxl']);
  await page.locator('#adapterPairForm [type="submit"]').click();
  assert.equal(await page.locator('[data-adapter-select="ui_lora_sdxl"]').isChecked(), true);
  assert.equal(await page.locator('[data-adapter-select="ui_lora_sd15"]').count(), 0); checked('SDXL uses the same pairing form with its separate compatible base');
  await page.locator('#localTaskForm [data-action="closeModal"]').click(); await page.locator('[data-task="any"]').click();
};
module.exports.installFixture = installFixture;
module.exports.installSpeechFixture = installSpeechFixture;

module.exports.installAdapterFixture = installAdapterFixture;
