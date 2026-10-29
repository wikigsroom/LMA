'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const preparations = require('./preparations-ui.cjs');
const root = path.resolve(__dirname, '..');
function canonical(value) { return Array.isArray(value) ? '[' + value.map(item => canonical(item) + ',').join('') + ']' : value && typeof value === 'object' ? '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k]) + ',').join('') + '}' : JSON.stringify(value); }
function data() {
  const catalogue = JSON.parse(fs.readFileSync(path.join(root, 'catalogue/model-bundles.json'), 'utf8'));
  const descriptor = JSON.parse(fs.readFileSync(path.join(root, 'catalogue/model-assemblies.json'), 'utf8')).plans[0];
  const target = catalogue.bundles.find(b => b.id === descriptor.bundleId), source = preparations.data();
  const bound = {plan: descriptor, preparationFingerprint: source.plan.fingerprint, bundleFingerprint: crypto.createHash('sha256').update(canonical(target)).digest('hex')};
  const mapped = new Set(descriptor.roles.map(r => r.target));
  return {target, plan: {...descriptor, fingerprint: crypto.createHash('sha256').update(canonical(bound)).digest('hex'), linkedComponents: mapped.size,
    linkedBytes: target.components.filter(c => mapped.has(c.role)).reduce((sum, c) => sum + c.bytes, 0), remainingComponents: target.components.filter(c => !mapped.has(c.role)), associated: false, installed: false}, sourceId: source.manifest.id};
}
function installAssembly(payload) {
  const f = window.__fixture, manifest = payload.target, total = manifest.components.reduce((sum, c) => sum + c.bytes, 0);
  const source = f.bundles.find(b => b.id === payload.sourceId); source.preparedAssets[0].id = 'prep_' + '1'.repeat(32); source.preparedAssets[0].assemblyPlans = [payload.plan];
  f.bundles.push({id: manifest.id, manifest, installed: false, config: {values: {}}, plan: {totalBytes: total, reusableBytes: 0, remainingBytes: total, components: manifest.components.map(c => ({...c, reusable: false, downloadable: !!c.url}))}});
  const previous = window.__handleFoundation;
  window.__handleFoundation = command => {
    if (command.action === 'submitTask' && command.request.type === 'model.assemble') {
      source.preparedAssets[0].inUse = true;
      const job = {id: 'ui_assembly', state: 'queued', stage: 'queued', createdAt: Date.now(), request: {...command.request}, artifacts: [], error: ''}; f.jobs.push(job); return job;
    }
    const assemblyJob = f.jobs.find(j => j.id === command.id && j.request.type === 'model.assemble');
    if (assemblyJob && command.action === 'cancelTask') { assemblyJob.state = 'cancelled'; source.preparedAssets[0].inUse = false; return; }
    if (assemblyJob && command.action === 'retryTask') { source.preparedAssets[0].inUse = true; const job = {...assemblyJob, id: 'ui_assembly_retry', state: 'queued', stage: 'queued'}; f.jobs.push(job); return job; }
    return previous(command);
  };
  window.LMA.receive(f);
}
function finishAssociation() {
  const f = window.__fixture, source = f.bundles.find(b => (b.preparedAssets || []).some(r => (r.assemblyPlans || []).length));
  const record = source.preparedAssets[0], plan = record.assemblyPlans[0], target = f.bundles.find(b => b.id === plan.bundleId);
  record.inUse = false; plan.associated = true;
  const mapped = plan.roles.map(r => r.target); target.plan.components.forEach(c => {c.reusable = mapped.includes(c.role);});
  target.plan.reusableBytes = plan.linkedBytes; target.plan.remainingBytes = target.plan.totalBytes - plan.linkedBytes; target.transfer = {state: 'paused', token: ''};
  f.jobs.filter(j => j.request.type === 'model.assemble' && j.state === 'queued').forEach(j => {j.state = 'succeeded'; j.stage = 'associating_runtime_assets'; j.assembly = {installed: false, linkedComponents: plan.linkedComponents, remainingBytes: target.plan.remainingBytes};});
  window.LMA.receive(f);
}
async function install(page) { await preparations.install(page); await page.evaluate(preparations.markPrepared); await page.evaluate(installAssembly, data()); }
async function openReview(page) {
  const payload = data(); await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="any"]').click();
  await page.locator('[data-bundle="' + payload.sourceId + '"] [data-action="bundleInfo"]').first().click(); await page.locator('[data-action="assemblyInfo"]').click();
}
async function check(page, checked, overflow) {
  await install(page); await openReview(page); const payload = data();
  assert.equal(await page.locator('#modalContent').getByText('复用本地组件', {exact: true}).count(), 1);
  assert.equal(await page.locator('#modalContent').getByText(/t5-v1_1-xxl-encoder-Q5_K_M.gguf/).count(), 1);
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle' && c.id === 'ltx098_runtime_google_q5_v1').length), 0);
  await overflow(page, 'Runtime association dependency review'); checked('Association review discloses reusable bytes and both T5 dependencies without automatic downloads');
  await page.locator('[data-action="assembleAssets"]').click();
  const request = await page.evaluate(() => window.__commands.findLast(c => c.action === 'submitTask').request);
  assert.deepEqual(request, {type: 'model.assemble', bundleId: payload.target.id, preparedAssetsId: 'prep_' + '1'.repeat(32), assemblyId: payload.plan.id, assemblyFingerprint: payload.plan.fingerprint});
  await page.locator('.nav-item[data-tab="tasks"]').click(); const job = page.locator('.job-card').filter({hasText: '模型运行资产关联'});
  assert.equal(await job.count(), 1); checked('Explicit association submits only signed model, plan and prepared-record identities to the shared queue');
  await job.locator('[data-action="cancelTask"]').click(); await job.locator('[data-action="retryTask"]').click();
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'retryTask' && c.id === 'ui_assembly').length), 1); checked('A cancelled association requires an explicit retry');
  await page.evaluate(finishAssociation); await page.locator('.nav-item[data-tab="models"]').click();
  await page.locator('[data-bundle="' + payload.target.id + '"] [data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('[data-action="downloadBundle"]').isEnabled(), true);
  assert.equal(await page.locator('[data-action="bundleUse"]').count(), 0);
  const state = await page.evaluate(id => window.__fixture.bundles.find(b => b.id === id), payload.target.id);
  assert.equal(state.installed, false); assert.equal(state.plan.components.filter(c => !c.reusable).length, 2); assert.equal(state.transfer.state, 'paused');
  assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle' && c.id === 'ltx098_runtime_google_q5_v1').length), 0); checked('Local management shows 20 reusable components and two paused dependencies without enabling generation');
  await page.locator('[data-action="downloadBundle"]').click();
  assert.deepEqual(await page.evaluate(() => window.__commands.filter(c => c.action === 'downloadBundle' && c.id === 'ltx098_runtime_google_q5_v1').map(c => c.id)), [payload.target.id]); checked('Only an explicit runtime-model download command can request the remaining components');
  await page.keyboard.press('Escape');
}
module.exports = check;
module.exports.install = install;
module.exports.openReview = openReview;
module.exports.finishAssociation = finishAssociation;
module.exports.data = data;
