/* Text bundle UI fixtures; no weights, actual generation or Android execution. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const template = JSON.parse(fs.readFileSync(path.join(__dirname, '../app/src/main/assets/recipe-templates.json'), 'utf8')).templates.find(t => t.id === 'text_gguf_cpu_v1');
const result = {schema: 'lma.text-result/1', content: '这是本地文本结果的界面测试数据。\n正文与思考分别保存，支持选择文本及导出。\n<img src=x onerror="window.__pwned=true">', reasoning: '这里是独立的思考内容测试数据；没有运行任何模型。', finishReason: 'length', usage: {prompt_tokens: 24, completion_tokens: 32, total_tokens: 56}};
function installFixture(template) {
  const f = window.__fixture, m = {...JSON.parse(JSON.stringify(template.definition)), schema: 'lma.model-bundle/1', id: 'ui_text', modelId: 'ui_text_model', recipeId: template.id, name: '文本模型 · 界面测试数据', description: '仅界面测试，无实际下载和推理', license: 'UI fixture only', components: [{role: 'text_gguf', format: 'gguf', path: 'fixture.gguf', bytes: 1000, sha256: 'a'.repeat(64)}]};
  const parameterSchema = JSON.parse(JSON.stringify(m.parameters)); parameterSchema.fields.threads.maximum = 8; parameterSchema.fields.context.maximum = 1024; parameterSchema.fields.context.limitSource = 'gguf_metadata'; parameterSchema.contextKnown = true;
  const b = {id: m.id, manifest: m, parameterSchema, installed: true, config: {values: {threads: 2, context: 512, maxTokens: 256, temperature: 0.7, reasoning: 'off', systemPrompt: '本地助手（界面测试）'}}, plan: {installed: true, totalBytes: 1000, reusableBytes: 1000, remainingBytes: 0, components: m.components.map(c => ({...c, reusable: true, downloadable: false}))}};
  f.bundles = (f.bundles || []).filter(b => b.id !== m.id).concat(b); f.localEngines = (f.localEngines || []).filter(e => e.engine !== 'llama_text').concat({engine: 'llama_text', available: true, deviceValidated: false});
  const artifact = {id: 'ui_text_artifact', available: true, bytes: 420, createdAt: Date.now(), sha256: 'b'.repeat(64), metadata: {mime: 'application/vnd.lma.text+json', characters: 98, reasoningCharacters: 29, finishReason: 'length'}, provenance: {execution: 'UI fixture only', bundle: m, request: {type: 'text.generate', parameters: {...b.config.values}}, engine: {engine: 'llama_text', model_inference_tested: false}}};
  f.artifacts = (f.artifacts || []).filter(a => a.id !== artifact.id).concat(artifact);
  const previous = window.__handleFoundation;
  window.__handleFoundation = command => {
    if (command.action === 'saveBundleSettings' && command.id === b.id) { b.config.values = {...command.settings}; return; }
    if (command.action === 'inspectArtifact' && command.id === artifact.id) return artifact;
    if (command.action === 'submitTask' && command.request.bundleId === b.id) {
      const job = {id: 'ui_text_job', state: 'queued', stage: 'queued', request: {...command.request}, createdAt: Date.now(), artifacts: [], error: ''}; f.jobs = (f.jobs || []).filter(j => j.id !== job.id).concat(job); return job;
    }
    return previous ? previous(command) : undefined;
  };
  window.LMA.receive(f);
}
async function install(page) { await page.evaluate(installFixture, template); }
async function resultRoute(page) { await page.route('**/artifacts/ui_text_artifact', route => route.fulfill({status: 200, contentType: 'application/vnd.lma.text+json', body: JSON.stringify(result)})); }
module.exports = async function checkText(page, checked, checkOverflow, output) {
  await install(page); await resultRoute(page);
  try {
    await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('#modelSearch').fill(''); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="text"]').click();
    assert.equal(await page.locator('[data-bundle="ui_text"]').count(), 1); checked('Text bundles are equal peers in the shared Local library and task filter');
    const before = await page.evaluate(() => window.__commands.filter(c => ['download', 'downloadBundle', 'load', 'submitTask'].includes(c.action)).length);
    await page.locator('[data-bundle="ui_text"] [data-action="bundleInfo"]').click(); await page.locator('[data-action="bundleSettings"][data-id="ui_text"]').click();
    assert((await page.locator('#bundleSettingsForm').innerText()).includes('上限 1024')); checked('Text settings display actual GGUF limits separately from manifest guards');
    await page.locator('[data-bundle-field="context"]').fill('99999'); await page.locator('[data-bundle-field="context"]').blur(); assert.equal(await page.locator('[data-bundle-field="context"]').inputValue(), '1024'); checked('Editable text context clamps to the installed model limit');
    await page.locator('[data-bundle-field="context"]').fill('128'); await page.locator('[data-bundle-field="context"]').blur();
    await page.locator('[data-bundle-field="maxTokens"]').fill('99999'); await page.locator('[data-bundle-field="maxTokens"]').blur(); assert.equal(await page.locator('[data-bundle-field="maxTokens"]').inputValue(), '127'); assert((await page.locator('[data-bundle-bound-caption="maxTokens"]').innerText()).includes('当前上限 127')); checked('Output ceiling follows context in the shared editable parameter form');
    await checkOverflow(page, '375px unified text settings'); await page.screenshot({path: path.join(output, '22-text-model-settings.png')});
    await page.locator('#bundleSettingsForm [type="submit"]').click(); await page.waitForFunction(() => document.getElementById('modalBackdrop').hidden);
    const saved = await page.evaluate(() => window.__commands.findLast(c => c.action === 'saveBundleSettings' && c.id === 'ui_text')); assert.equal(saved.settings.context, 128); assert.equal(saved.settings.maxTokens, 127); checked('Text profile save carries the normalized independent values to the native bridge');
    assert.equal(await page.evaluate(() => window.__commands.filter(c => ['download', 'downloadBundle', 'load', 'submitTask'].includes(c.action)).length), before); checked('Browsing and editing a text profile never downloads or starts inference');
    await page.locator('[data-bundle="ui_text"] [data-action="bundleUse"]').click();
    assert.equal(await page.locator('#localTaskForm [name="negativePrompt"]').count(), 0); assert.equal(await page.locator('#localTaskForm [name="taskType"]').inputValue(), 'text.generate'); checked('Text generation uses the common task form without unsupported negative prompts');
    await page.locator('#localTaskForm [name="prompt"]').fill('解释如何在本地模型中保存独立参数。（界面测试，不执行模型）'); await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
    await page.locator('.task-parameters').evaluate(el => {el.open = true;}); await checkOverflow(page, '375px shared text task form'); await page.screenshot({path: path.join(output, '23-text-queue-form.png')});
    await page.locator('#localTaskForm [type="submit"]').click(); await page.waitForSelector('#page-tasks.active .job-card');
    const submitted = await page.evaluate(() => window.__commands.findLast(c => c.action === 'submitTask' && c.request.bundleId === 'ui_text')); assert.equal(submitted.request.parameters.maxTokens, 127); assert.equal(submitted.request.type, 'text.generate'); checked('Text requests enter the shared job contract with fixed bundle IDs and settings');
    await page.locator('.nav-item[data-tab="tasks"]').click(); await page.locator('[data-action="artifactInfo"][data-id="ui_text_artifact"]').click(); await page.waitForSelector('#textArtifact pre');
    assert((await page.locator('#textArtifact > pre').textContent()).includes('<img src=x')); assert.equal(await page.locator('#textArtifact img, #textArtifact script').count(), 0); assert.equal(await page.evaluate(() => window.__pwned), false); checked('Saved model text and markup render as inert selectable text');
    await page.locator('[data-action="copyArtifactText"]').click(); assert.equal(await page.evaluate(() => window.__copied), result.content); checked('Copy exports the literal response body without reasoning or markup interpretation');
    await page.locator('#textArtifact details').evaluate(el => {el.open = true;}); assert((await page.locator('#textArtifact details pre').textContent()).includes('独立的思考内容')); assert((await page.locator('#textArtifact > p').textContent()).includes('输出上限')); checked('Text results show reasoning separately and explain token-limit completion');
    await checkOverflow(page, '375px text artifact preview'); await page.screenshot({path: path.join(output, '24-text-result.png')});
    await page.locator('[data-action="closeModal"]').first().click();
    await page.unroute('**/artifacts/ui_text_artifact'); await page.route('**/artifacts/ui_text_artifact', route => route.fulfill({status: 200, contentType: 'application/json', body: '{"schema":"unknown"}'}));
    await page.locator('[data-action="artifactInfo"][data-id="ui_text_artifact"]').click(); await page.waitForFunction(() => document.getElementById('textArtifact')?.textContent.includes('格式无效')); checked('Malformed local text artifacts show an error instead of a fabricated result');
    await page.locator('[data-action="closeModal"]').first().click();
  } finally { await page.unroute('**/artifacts/ui_text_artifact'); }
};
module.exports.install = install;
module.exports.resultRoute = resultRoute;
