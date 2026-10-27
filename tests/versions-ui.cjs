/* Explicit version-management UI fixture. Storage semantics are tested in Java, not simulated here. */
const assert = require('node:assert/strict');
const {installFixture: installFoundation} = require('./foundation-ui.cjs');

function installFixture() {
  const f = window.__fixture, source = f.bundles.find(b => b.id === 'ui_sd'); source.installed = true; source.config.values.steps = 18;
  source.manifest.name = '图像模型 V1 · 界面测试数据';
  const target = JSON.parse(JSON.stringify(source)); target.id = target.manifest.id = target.manifest.modelId = 'ui_sd_v2';
  target.manifest.name = '图像模型 V2 · 界面测试数据'; target.manifest.recipeId = 'ui_recipe_v2'; target.installed = false;
  target.manifest.parameters.fields.steps.maximum = 8; target.manifest.license = 'UI fixture target license; no weights'; target.config.values.steps = 6;
  target.manifest.components[0].sha256 = 'a'.repeat(64); target.manifest.components[0].revision = '1'.repeat(40); target.manifest.components[0].repository = 'fixture/model-v2';
  target.plan = {...target.plan, availableBytes: 30000000000, components: target.manifest.components.map(c => ({...c, reusable: c.role === 'clip_merges', downloadable: true}))};
  f.bundles.push(target);
  const other = JSON.parse(JSON.stringify(target)); other.id = other.manifest.id = 'ui_incompatible'; other.manifest.architecture = 'sdxl'; other.manifest.name = '不兼容候选 · 界面测试'; f.bundles.push(other);
  const previous = window.__handleFoundation; let generation = 0, current = source.id, members = [source.id], update = null, history = [];
  const sync = () => {
    for (const b of [source, target]) b.version = members.includes(b.id) || update && b.id === update.toBundleId
      ? {groupId: source.id, activeBundleId: current, members: members.slice(), isActive: b.id === current, historyCount: history.length, ...(update ? {pending: {...update, ready: target.installed, targetName: target.manifest.name}} : {})} : {};
  };
  const plan = command => {
    const a = f.bundles.find(b => b.id === command.from), b = f.bundles.find(b => b.id === command.to);
    const steps = command.settingsMode === 'copy' ? Math.min(b.manifest.parameters.fields.steps.maximum, a.config.values.steps) : b.config.values.steps;
    return {fromBundleId: a.id, toBundleId: b.id, settingsMode: command.settingsMode, review: String(generation % 10).repeat(64),
      components: b.plan.components.map((c, i) => ({role: c.role, change: i ? 'unchanged' : 'changed', from: a.manifest.components[i], to: b.manifest.components[i]})),
      settings: {values: {...b.config.values, steps}, changes: [{field: 'steps', from: a.config.values.steps, to: steps, reason: command.settingsMode === 'keep' ? 'target_settings' : 'clamped'}]},
      metadataChanges: ['license', 'parameters'], download: {...b.plan, installed: b.installed}};
  };
  window.__handleFoundation = command => {
    if (window.__rejectNextAction === command.action) return;
    if (command.action === 'planBundleUpdate') return plan(command);
    if (command.action === 'prepareBundleUpdate' || command.action === 'downloadBundleUpdate') {
      update = {fromBundleId: command.from, toBundleId: command.to, settingsMode: command.settingsMode, review: command.review, stale: false};
      if (command.action === 'downloadBundleUpdate') target.transfer = {state: 'downloading', role: 'model', received: 100};
      sync(); return plan(command);
    }
    if (command.action === 'activateBundleUpdate') {
      const p = plan(command), b = f.bundles.find(b => b.id === command.to); b.config.values = p.settings.values;
      current = b.id; if (!members.includes(current)) members.push(current);
      history.push({fromBundleId: command.from, toBundleId: command.to, settingsMode: command.settingsMode, review: command.review, at: Date.now()}); update = null; generation++; sync(); return {bundleId: current};
    }
    if (command.action === 'cancelBundleUpdate') { update = null; generation++; sync(); return; }
    if (command.action === 'inspectBundleVersions') return {history};
    return previous(command);
  };
  sync(); window.LMA.receive(f);
}

module.exports = async function checkVersions(page, checked, checkOverflow) {
  await page.keyboard.press('Escape'); await page.evaluate(installFoundation); await page.evaluate(installFixture);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="any"]').click();
  const before = await page.evaluate(() => window.__commands.filter(c => ['downloadBundle', 'downloadBundleUpdate'].includes(c.action)).length);
  await page.locator('[data-bundle="ui_sd"] [data-action="bundleInfo"]').click(); await page.locator('[data-action="bundleVersions"]').click();
  assert.deepEqual(await page.locator('#bundleVersionForm [name="target"] option').evaluateAll(options => options.map(o => o.value)), ['', 'ui_sd_v2']); checked('Version candidates preserve architecture/engine/task boundaries');
  await page.locator('#bundleVersionForm [name="target"]').selectOption('ui_sd_v2'); await page.locator('#bundleVersionForm [type="submit"]').click();
  await page.waitForSelector('[data-action="versionDownload"]');
  const plan = await page.evaluate(() => window.__commands.findLast(c => c.action === 'planBundleUpdate'));
  assert.deepEqual([plan.from, plan.to, plan.settingsMode], ['ui_sd', 'ui_sd_v2', 'copy']);
  assert((await page.locator('#modalContent').textContent()).includes('18 → 8')); checked('Update review shows immutable selections, component changes and model-limit adjustments');
  assert.equal(await page.evaluate(() => window.__commands.filter(c => ['downloadBundle', 'downloadBundleUpdate'].includes(c.action)).length), before); checked('Opening and reviewing model versions never downloads assets');
  await page.setViewportSize({width: 320, height: 720}); await page.locator('#modalContent .bundle-components details').first().evaluate(el => {el.open = true;});
  assert(await page.locator('#modal').evaluate(el => el.scrollWidth <= el.clientWidth + 1)); await checkOverflow(page, '320px model version review');
  await page.setViewportSize({width: 375, height: 812});
  await page.evaluate(() => {window.__rejectNextAction = 'downloadBundleUpdate';}); await page.locator('[data-action="versionDownload"]').click();
  await page.waitForFunction(() => document.getElementById('versionHint').textContent.includes('拒绝'));
  assert.equal(await page.locator('[data-action="versionDownload"]').isEnabled(), true); checked('Rejected native update commands retain the review and allow an explicit retry');
  await page.locator('[data-action="versionDownload"]').click(); await page.waitForSelector('[data-action="versionCancel"]');
  assert.deepEqual(await page.evaluate(() => {const [a,b] = window.__fixture.bundles; return [a.installed, b.installed, a.config.values.steps, a.version.activeBundleId];}), [true, false, 18, 'ui_sd']);
  const download = await page.evaluate(() => window.__commands.findLast(c => c.action === 'downloadBundleUpdate'));
  assert.deepEqual([download.from, download.to, download.settingsMode, download.review], ['ui_sd', 'ui_sd_v2', 'copy', '0'.repeat(64)]); checked('Only explicit confirmation starts the selected version download; the old profile remains active');
  await page.evaluate(() => {const b = window.__fixture.bundles.find(b => b.id === 'ui_sd_v2'); b.transfer = {state: 'failed', error: '界面模拟校验失败'}; window.LMA.receive(window.__fixture);});
  await page.waitForFunction(() => document.getElementById('modalContent').textContent.includes('旧版本保留'));
  assert((await page.locator('#modalContent').textContent()).includes('界面模拟校验失败')); checked('An open version manager reflects failed verification without changing the current version');
  await page.evaluate(() => {for (const b of window.__fixture.bundles) if (b.version?.pending) b.version.pending.ready = true; const t=window.__fixture.bundles.find(b => b.id === 'ui_sd_v2'); t.installed=true; t.transfer={state:'installed'}; window.LMA.receive(window.__fixture);});
  await page.waitForFunction(() => document.getElementById('modalContent').textContent.includes('等待你确认切换'));
  assert.equal(await page.evaluate(() => window.__fixture.bundles[0].version.activeBundleId), 'ui_sd'); checked('Completed downloads wait for a separate activation confirmation');
  await page.locator('[data-action="versionPendingReview"]').click(); await page.waitForSelector('[data-action="versionActivate"]'); await page.locator('[data-action="versionActivate"]').click();
  await page.waitForFunction(() => window.__fixture.bundles[0].version.activeBundleId === 'ui_sd_v2');
  assert.deepEqual(await page.evaluate(() => window.__fixture.bundles.slice(0,2).map(b => [b.installed,b.config.values.steps])), [[true,18],[true,8]]); checked('Explicit activation keeps old assets/settings and applies reviewed target parameters');
  await page.locator('[data-action="versionHistory"]').click(); await page.waitForFunction(() => document.getElementById('modalTitle').textContent.includes('切换记录'));
  assert((await page.locator('#modalContent').textContent()).includes('ui_sd → ui_sd_v2')); checked('Persistent version history has a dedicated readable view');
  await page.keyboard.press('Escape'); await page.locator('[data-bundle="ui_sd_v2"] [data-action="bundleInfo"]').click(); await page.locator('[data-action="bundleVersions"]').click();
  await page.locator('#bundleVersionForm [name="target"]').selectOption('ui_sd'); await page.locator('#bundleVersionForm [name="settingsMode"]').selectOption('keep');
  await page.locator('#bundleVersionForm [type="submit"]').click(); await page.waitForSelector('[data-action="versionActivate"]');
  assert((await page.locator('#modalContent').textContent()).includes('8 → 18')); await page.locator('[data-action="versionActivate"]').click();
  await page.waitForFunction(() => window.__fixture.bundles[0].version.activeBundleId === 'ui_sd');
  assert.deepEqual(await page.evaluate(() => window.__fixture.bundles.slice(0,2).map(b => b.config.values.steps)), [18,8]); checked('Rollback explicitly selects an installed old version and preserves its original parameter profile');
  await page.evaluate(() => {const t=window.__fixture.bundles.find(b=>b.id==='ui_sd_v2'); t.installed=false; window.LMA.receive(window.__fixture);});
  await page.locator('#bundleVersionForm [name="target"]').selectOption('ui_sd_v2'); await page.locator('#bundleVersionForm [type="submit"]').click(); await page.waitForSelector('[data-action="versionDownload"]');
  await page.locator('[data-action="versionDownload"]').click(); await page.waitForSelector('[data-action="versionCancel"]');
  await page.evaluate(() => {window.__fixture.bundles.forEach(b => {if(b.version?.pending) b.version.pending.stale=true;});window.LMA.receive(window.__fixture);});
  assert.equal(await page.locator('[data-action="versionPendingReview"]').isDisabled(), true); checked('Stale model configuration consent is visible and cannot be activated directly');
  await page.locator('[data-action="versionCancel"]').click(); await page.waitForSelector('#bundleVersionForm');
  assert.equal(await page.evaluate(() => window.__fixture.bundles[0].installed), true); checked('Cancelling an update plan retains the old installed model');
  await page.locator('#bundleVersionForm [name="target"]').selectOption('ui_sd_v2'); await page.locator('#bundleVersionForm [type="submit"]').click(); await page.keyboard.press('Escape');
  await page.waitForTimeout(250); assert.equal(await page.locator('#modalBackdrop').isHidden(), true); checked('Late update previews cannot reopen a closed model dialog');
};
module.exports.installFixture = installFixture;
