/* Simulated native bridge for browser regression/media; no HF downloads or inference. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function installFixture(templates) {
  const f = window.__fixture, h = f.hub, revision = '0123456789abcdef0123456789abcdef01234567';
  h.recipeTemplates = templates; h.recipeError = ''; h.recipeDraft = {}; let sequence = 0;
  const repos = ['fixture/model', 'fixture/voices'];
  for (const id of repos) if (!h.fixtureRepositories.some(r => r.id === id)) h.fixtureRepositories.push({id, task: 'text-to-speech', downloads: 0, likes: 0, uncensored: {declared: false, detected: true}});
  const files = repository => [
    {path: 'model.onnx', format: 'onnx', bytes: 310000000, sha256: 'a'.repeat(64)},
    {path: 'tokens.txt', format: 'text', bytes: 1024, gitBlobSha1: 'b'.repeat(40)},
    {path: 'voices.bin', format: 'bin', bytes: 1000000, sha256: 'c'.repeat(64)},
    {path: 'adapter.safetensors', format: 'safetensors', bytes: 1200000, sha256: 'd'.repeat(64)},
    ...['browser_poc_manifest.json', 'tts_browser_onnx_meta.json', 'codec_browser_onnx_meta.json', 'tokenizer.model', 'moss_tts_prefill.onnx', 'moss_tts_decode_step.onnx', 'moss_tts_local_fixed_sampled_frame.onnx', 'moss_audio_tokenizer_decode_full.onnx', 'moss_tts_global_shared.data', 'moss_tts_local_shared.data', 'codec_weights.data'].map((file, index) => ({path: file, format: file.endsWith('.json') ? 'json' : file.endsWith('.model') ? 'sentencepiece' : file.endsWith('.data') ? 'onnx_data' : 'onnx', bytes: file.endsWith('.data') ? 128000000 : 1200, sha256: String(index % 10).repeat(64)})),
    {path: 'unverified.onnx', format: 'onnx', bytes: 5, blocked: '缺少有效文件校验信息'}
  ].map(c => ({...c, blocked: c.blocked || '', repository, revision, url: 'https://huggingface.co/' + repository + '/resolve/' + revision + '/' + c.path}));
  const page = (repository, second) => { h.files = {repository: {...h.fixtureRepositories.find(r => r.id === repository), revision}, assets: second ? [] : files(repository), items: [], loading: false, error: '', next: second ? '' : 'fixture-page-two', previous: second, page: second ? 2 : 1}; };
  window.__handleRecipe = command => {
    if (window.__rejectNextAction === command.action) return;
    const d = h.recipeDraft;
    if (command.action === 'hubFiles' && repos.includes(command.repository)) page(command.repository, false);
    if (command.action === 'hubFilePage' && repos.includes(h.files.repository.id)) page(h.files.repository.id, command.direction === 'next');
    if (command.action === 'hubRecipeStart') h.recipeDraft = {draftId: 'ui-draft-' + ++sequence, origin: {...h.files.repository}, templateId: '', bindings: {}};
    if (command.action === 'hubRecipeTemplate') h.recipeDraft = {...d, draftId: 'ui-draft-' + ++sequence, templateId: command.templateId, bindings: {}};
    if (command.action === 'hubRecipeBind') d.bindings[command.role] = {...h.files.assets.find(c => c.path === command.path)};
    if (command.action === 'hubRecipeDeclare') {
      const t = templates.find(t => t.id === d.templateId), components = t.requirements.filter(r => d.bindings[r.role]).map(r => ({...d.bindings[r.role], role: r.role})).concat(t.fixedComponents);
      const manifest = {...t.definition, schema: 'lma.model-bundle/2', id: 'ui_hf_recipe', modelId: 'ui_hf_recipe', recipeId: t.id, name: '自选 HF 组件 · 界面测试', description: '仅界面数据，没有下载或执行模型。', components, uncensored: {declared: false, detected: true}, evidence: {physicalDeviceTests: 0}};
      const totalBytes = components.reduce((n, c) => n + c.bytes, 0);
      if (!f.bundles.some(b => b.id === manifest.id)) f.bundles.push({id: manifest.id, manifest, installed: false, config: {values: {}}, plan: {installed: false, totalBytes, reusableBytes: 0, remainingBytes: totalBytes, components: components.map(c => ({...c, downloadable: true, reusable: false}))}});
      d.bundleId = manifest.id; return {bundleId: manifest.id};
    }
  };
  f.localEngines.push({engine: 'sherpa_tts', available: true, deviceValidated: false}, {engine: 'moss_nano_ort', available: true, deviceValidated: false});
  h.initialized = true; h.format = 'all'; h.query = 'fixture/model'; h.items = [h.fixtureRepositories.find(r => r.id === 'fixture/model')];
  window.LMA.receive(f);
}

async function openRecipe(page) {
  await page.locator('[data-action="tab"][data-tab="models"]').first().click();
  await page.locator('[data-task="any"]').click();
  await page.locator('[data-filter="all"]').click();
  await page.locator('[data-action="hubFiles"][data-repository="fixture/model"]').click();
  await page.locator('[data-action="recipeStart"]').click();
  await page.waitForSelector('#recipeTemplate');
}
async function selectTemplate(page, id) {
  await page.locator('#recipeTemplate').selectOption(id);
  await page.waitForFunction(id => window.__fixture.hub.recipeDraft.templateId === id, id);
  await page.waitForSelector('[data-action="recipePick"]');
}
async function bind(page, role, filename, repository) {
  await page.locator('[data-action="recipePick"][data-role="' + role + '"]').click();
  if (repository) { await page.locator('#recipeRepository').fill(repository); await page.locator('[data-action="recipeLookup"]').click(); }
  await page.locator('[data-action="recipeBind"][data-path="' + filename + '"]').click();
  await page.waitForSelector('#recipeTemplate');
}
module.exports = async function checkRecipes(page, checked) {
  const templates = JSON.parse(fs.readFileSync(path.join(__dirname, '../app/src/main/assets/recipe-templates.json'), 'utf8')).templates;
  await page.evaluate(installFixture, templates);
  const count = () => page.evaluate(() => window.__commands.filter(c => ['download', 'downloadBundle'].includes(c.action)).length);
  const before = await count(); await openRecipe(page);
  assert.equal(await page.locator('#recipeTemplate option').count(), 22); checked('HF recipe UI offers twenty-one explicit architecture/component templates');
  assert(await page.locator('[data-action="recipeDeclare"]').isDisabled()); checked('No recipe or files are selected automatically');
  await selectTemplate(page, 'kokoro_en_cpu_v1');
  assert((await page.locator('#recipePanel').innerText()).includes('lexicon')); checked('Fixed language dependency is disclosed before registration');
  await page.locator('[data-action="recipePick"][data-role="model"]').click();
  assert(await page.locator('[data-action="recipeBind"][data-path="unverified.onnx"]').isDisabled()); checked('Unverifiable components cannot be selected in the UI');
  await page.locator('[data-action="recipePage"][data-direction="next"]').click();
  await page.waitForFunction(() => window.__fixture.hub.files.page === 2);
  assert.equal(await page.locator('[data-action="recipeBind"]').count(), 0); checked('Component file pagination does not retain stale selectable rows');
  await page.locator('[data-action="recipePage"][data-direction="previous"]').click();
  await page.locator('[data-action="recipeBind"][data-path="model.onnx"]').click();
  await page.waitForSelector('#recipeTemplate');
  await bind(page, 'voices', 'voices.bin', 'fixture/voices');
  await bind(page, 'tokens', 'tokens.txt', 'fixture/model');
  await page.locator('#recipePanel details').evaluateAll(nodes => nodes.forEach(d => { d.open = true; }));
  assert((await page.locator('#recipePanel').innerText()).includes('fixture/voices')); checked('Component form preserves separate fixed-revision source repositories');
  assert((await page.locator('#recipePanel').innerText()).includes('Git blob SHA-1')); checked('Ordinary Git file identity is shown with its actual algorithm');
  assert.equal(await count(), before); checked('Browsing and component binding do not dispatch model downloads');
  await page.evaluate(() => { window.__rejectNextAction = 'hubRecipeDeclare'; });
  await page.locator('[data-action="recipeDeclare"]').click();
  await page.waitForFunction(() => document.getElementById('recipeHint')?.textContent.includes('拒绝'));
  assert(await page.locator('[data-action="recipeDeclare"]').isEnabled()); checked('Native registration errors preserve choices and allow retry');
  await page.locator('[data-action="recipeDeclare"]').click();
  await page.waitForSelector('[data-action="downloadBundle"][data-id="ui_hf_recipe"]');
  assert.equal(await count(), before); checked('Adding a model opens its separate download plan without starting a transfer');
  await page.locator('#modalContent details').evaluateAll(nodes => nodes.forEach(d => { d.open = true; }));
  assert((await page.locator('#modalContent').innerText()).includes('Git blob SHA-1')); checked('Bundle plan retains Git digest labels after registration');
  await page.locator('[data-action="downloadBundle"][data-id="ui_hf_recipe"]').click();
  await page.waitForFunction(() => window.__fixture.bundles.find(b => b.id === 'ui_hf_recipe').transfer?.state === 'downloading');
  assert.equal(await count(), before + 1); checked('Only explicit confirmation starts downloading the chosen model bundle');
  await openRecipe(page); await selectTemplate(page, 'moss_nano_cpu_v1');
  assert((await page.locator('#recipePanel').innerText()).includes('生音频')); checked('Nano shares peer audio capability labels');
  assert(await page.locator('[data-action="recipeDeclare"]').isDisabled()); checked('Nano cannot register without all eight core components');
  await bind(page, 'text_tokenizer', 'tokenizer.model', 'fixture/model');
  await bind(page, 'tts_data_1', 'moss_tts_global_shared.data', 'fixture/model');
  await page.locator('#recipePanel details').evaluateAll(nodes => nodes.forEach(d => { d.open = true; }));
  assert((await page.locator('#recipePanel').innerText()).includes('tokenizer.model')); checked('Nano tokenizer remains a separately selected component');
  assert((await page.locator('#recipePanel').innerText()).includes('moss_tts_global_shared.data')); checked('External ONNX weights are selected explicitly');
  assert.equal(await count(), before + 1); checked('Selecting Nano graph dependencies creates no extra transfer');
  await page.setViewportSize({width: 320, height: 720});
  const nanoOverflow = await page.evaluate(() => { const modal = document.getElementById('modal'); return {width: modal.clientWidth, scroll: modal.scrollWidth, elements: Array.from(modal.querySelectorAll('*')).filter(el => el.getBoundingClientRect().right > modal.getBoundingClientRect().right + 1).map(el => ({tag: el.tagName, className: el.className, width: el.clientWidth, text: el.textContent.slice(0, 70)})).slice(0, 8)}; });
  assert(nanoOverflow.scroll <= nanoOverflow.width + 1, JSON.stringify(nanoOverflow)); checked('Nano component form fits the narrow phone viewport');
  await selectTemplate(page, 'sd15_lora_cpu_v1'); await bind(page, 'lora', 'adapter.safetensors', 'fixture/model');
  assert((await page.locator('#recipePanel').innerText()).includes('LoRA 不能单独生成')); checked('LoRA selection remains a peer entry with an explicit base-model dependency');
  await page.setViewportSize({width: 360, height: 780});
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1 && document.getElementById('modal').scrollWidth <= document.getElementById('modal').clientWidth + 1)); checked('Recipe selection fits a narrow Android viewport');
  await page.locator('#modal [data-action="closeModal"]').first().click();
  await page.evaluate(() => window.LMA.receive(window.__fixture));
  assert(await page.locator('#modalBackdrop').isHidden()); checked('Closed recipe dialogs stay closed on later native updates');
};
module.exports.installFixture = installFixture;
module.exports.openRecipe = openRecipe;
module.exports.selectTemplate = selectTemplate;
module.exports.bind = bind;
