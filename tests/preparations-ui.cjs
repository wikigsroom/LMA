/* Actual UI with explicitly simulated source/preparation state. No model download or Android. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {installFixture} = require('./foundation-ui.cjs');
const root = path.resolve(__dirname, '..');
function canonical(value) { return Array.isArray(value) ? '[' + value.map(item => canonical(item) + ',').join('') + ']' : value && typeof value === 'object' ? '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k]) + ',').join('') + '}' : JSON.stringify(value); }
function data() {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'catalogue/model-bundles.json'), 'utf8')).bundles.find(b => b.id === 'ltx098_source_r8984fa2');
  const source = JSON.parse(fs.readFileSync(path.join(root, 'catalogue/asset-preparations.json'), 'utf8')).plans[0];
  const outputBytes = source.stages.flatMap(s => s.outputs).reduce((total, file) => total + file.bytes, 0);
  const plan = {id: source.id, name: source.name, fingerprint: crypto.createHash('sha256').update(canonical(source)).digest('hex'), sourceBytes: source.sourceBytes, outputBytes, requiredFreeBytes: outputBytes + 128 * 1024 * 1024, ready: false, available: true};
  return {manifest, plan};
}
function installPreparation(payload) {
  const f = window.__fixture, manifest = JSON.parse(JSON.stringify(payload.manifest)); manifest.name += ' · 界面演示';
  const plan = payload.plan, total = manifest.components.reduce((sum, c) => sum + c.bytes, 0);
  f.bundles.push({id: manifest.id, manifest, installed: true, config: {values: {}}, plan: {totalBytes: total, reusableBytes: total, remainingBytes: 0, components: manifest.components.map(c => ({...c, reusable: true, downloadable: true}))}, preparationPlans: [plan], preparedAssets: []});
  const previous = window.__handleFoundation;
  window.__handleFoundation = command => {
    if (command.action === 'submitTask' && command.request.type === 'model.prepare') {
      const job = {id: 'ui_preparation', state: 'queued', stage: 'queued', createdAt: Date.now(), request: {...command.request}, artifacts: [], error: ''}; f.jobs = [job]; return job;
    }
    if (command.action === 'retryTask' && f.jobs.some(j => j.id === command.id && j.request.type === 'model.prepare')) {
      const job = {...f.jobs.find(j => j.id === command.id), id: 'ui_preparation_retry', state: 'queued', stage: 'queued', error: ''}; f.jobs.push(job); return job;
    }
    if (command.action === 'deletePreparedAssets') {
      const b = f.bundles.find(b => (b.preparedAssets || []).some(r => r.id === command.id));
      b.preparedAssets = b.preparedAssets.filter(r => r.id !== command.id); b.preparationPlans.forEach(p => {p.ready = false;}); return;
    }
    return previous(command);
  };
  window.LMA.receive(f);
}
function markPrepared() {
  const b = window.__fixture.bundles.find(b => (b.preparationPlans || []).length);
  b.preparationPlans[0].ready = true;
  b.preparedAssets = [{id: 'prep_ui_fixture', bytes: b.preparationPlans[0].outputBytes, available: true, inUse: false, createdAt: Date.now()}];
  const job = window.__fixture.jobs.findLast(j => j.request.type === 'model.prepare'); if (job) {job.state = 'succeeded'; job.stage = 'verifying_prepared_assets'; job.preparation = {id: 'prep_ui_fixture'};}
  window.LMA.receive(window.__fixture);
}
async function install(page) { await page.evaluate(installFixture); await page.evaluate(installPreparation, data()); }
async function check(page, checked, overflow) {
  await install(page); const payload = data(), id = payload.manifest.id;
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="any"]').click();
  assert.equal(await page.locator('[data-bundle="' + id + '"] [data-action="bundleUse"]').count(), 0);
  await page.locator('[data-bundle="' + id + '"] [data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('.preparation-section').isVisible(), true);
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'submitTask' && c.request.type === 'model.prepare').length), 0);
  checked('Viewing an installed source offers preparation without automatic conversion or generation');
  await page.locator('[data-action="preparationInfo"]').click(); await overflow(page, 'Preparation storage confirmation');
  assert.equal(await page.locator('#modalContent').getByText('所需额外可用空间', {exact: true}).count(), 1);
  await page.locator('[data-action="prepareAssets"]').click();
  const request = await page.evaluate(() => window.__commands.findLast(c => c.action === 'submitTask').request);
  assert.deepEqual(request, {type: 'model.prepare', bundleId: id, preparationId: payload.plan.id, planFingerprint: payload.plan.fingerprint});
  await page.locator('.nav-item[data-tab="tasks"]').click();
  await page.locator('.job-card').filter({hasText: '模型运行资产准备'}).waitFor();
  assert.equal(await page.locator('.job-card').filter({hasText: '模型运行资产准备'}).count(), 1); checked('Explicit preparation freezes only the selected source and signed plan in the shared queue');
  await page.locator('.job-card [data-action="cancelTask"]').click();
  await page.locator('.job-card [data-action="retryTask"]').waitFor();
  assert.equal(await page.locator('.job-card [data-action="retryTask"]').count(), 1); await page.locator('.job-card [data-action="retryTask"]').click();
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'retryTask').length), 1); checked('Preparation cancellation exposes an explicit retry instead of starting another conversion');
  await page.evaluate(markPrepared); await page.locator('.nav-item[data-tab="models"]').click();
  await page.locator('[data-bundle="' + id + '"] [data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('[data-action="preparationInfo"]').isDisabled(), true);
  assert.equal(await page.locator('[data-action="bundleUse"]').isDisabled(), true); checked('Ready assets do not enable an absent video-generation adapter');
  await page.locator('[data-action="closeModal"]').first().click();
  await page.evaluate(id => {const b = window.__fixture.bundles.find(b => b.id === id); b.installed = false; window.LMA.receive(window.__fixture);}, id);
  assert.equal(await page.locator('[data-bundle="' + id + '"] [data-action="bundleInfo"]').filter({hasText: '管理运行资产'}).count(), 1);
  assert.equal(await page.locator('#modelResultCount').getByText(/1 仅运行资产/).count(), 1);
  checked('Derived-only runtime assets remain manageable in Local after deleting source weights');
  await page.locator('[data-bundle="' + id + '"] [data-action="bundleInfo"]').first().click();
  await page.evaluate(id => {window.__fixture.bundles.find(b => b.id === id).installed = true; window.LMA.receive(window.__fixture);}, id);
  await page.locator('[data-action="preparedRemove"]').click(); await page.locator('[data-action="confirmed"][data-command="deletePreparedAssets"]').click();
  await page.waitForFunction(id => window.__fixture.bundles.find(b => b.id === id).preparedAssets.length === 0, id);
  const record = await page.evaluate(id => window.__fixture.bundles.find(b => b.id === id), id);
  assert.equal(record.installed, true); assert.deepEqual(record.config.values, {}); assert.equal(record.preparedAssets.length, 0);
  assert.equal(await page.evaluate(id => window.__commands.filter(c => c.id === id && (c.action === 'downloadBundle' || c.action === 'importBundle')).length, id), 0); checked('Deleting derived runtime files preserves the source, settings and independent asset choices');
  await page.keyboard.press('Escape');
}
module.exports = check;
module.exports.install = install;
module.exports.markPrepared = markPrepared;
module.exports.data = data;
