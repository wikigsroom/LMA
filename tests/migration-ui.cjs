/* Existing text model -> shared task controls, with an explicit simulated bridge only. */
const assert = require('node:assert/strict');
const textUI = require('./text-ui.cjs');

async function install(page) {
  await textUI.install(page);
  await page.evaluate(() => {
    const f = window.__fixture, model = f.models.find(m => m.id === 'm08'), b = f.bundles.find(b => b.id === 'ui_text');
    b.id = 'ui_migrated_text'; b.manifest.id = b.id; b.manifest.modelId = model.id; b.manifest.name = model.name;
    b.manifest.uncensored = JSON.parse(JSON.stringify(model.uncensored));
    model.bundleId = b.id; model.installed = true; model.installedBytes = b.plan.totalBytes;
    model.download = {state: 'done', sha256: model.sha256, verification: 'publisher-sha256'};
    window.LMA.receive(f);
  });
}

module.exports = async function checkMigration(page, checked, checkOverflow) {
  await install(page);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('#modelSearch').fill(''); await page.locator('[data-task="text"]').click(); await page.locator('[data-filter="local"]').click();
  assert.equal(await page.locator('.bundle-card[data-bundle="ui_migrated_text"]').count(), 0); checked('Migrated legacy text model has no duplicate shared-library card');
  const before = await page.evaluate(() => window.__commands.filter(c => ['download', 'downloadBundle', 'load', 'submitTask'].includes(c.action)).length);
  await page.locator('[data-action="modelInfo"][data-id="m08"]').first().click();
  assert((await page.locator('#modalContent').innerText()).includes('复用已下载文件')); checked('Existing model details expose shared tasks without requiring another download');
  assert.equal(await page.locator('[data-action="bundleVersions"][data-id="ui_migrated_text"]').count(), 1); checked('Existing model exposes its immutable bundle version-management entry');
  assert((await page.locator('#modalContent').innerText()).includes('无审查')); checked('Migration preserves the checked publisher content label');
  await checkOverflow(page, 'Migrated model details');
  assert.equal(await page.evaluate(() => window.__commands.filter(c => ['download', 'downloadBundle', 'load', 'submitTask'].includes(c.action)).length), before); checked('Browsing migrated model details does not download, load or generate');
  await page.locator('[data-action="bundleUse"][data-id="ui_migrated_text"]').click(); await page.waitForSelector('#localTaskForm');
  assert.equal(await page.locator('[name="taskType"]').inputValue(), 'text.generate'); checked('Existing text model opens the same typed task form as other modalities');
  await page.locator('[name="prompt"]').fill('本地迁移界面测试，不运行模型'); await page.locator('[name="allowUnmeasured"]').check();
  await page.locator('#localTaskForm [type="submit"]').click();
  const submitted = await page.evaluate(() => window.__commands.filter(c => c.action === 'submitTask').slice(-1)[0]);
  assert.equal(submitted.request.bundleId, 'ui_migrated_text'); checked('Shared job submission fixes the migrated immutable bundle ID');
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-filter="recommended"]').click();
  const ids = await page.locator('#modelList .model-name[data-id]').evaluateAll(nodes => nodes.map(n => n.dataset.id));
  assert.deepEqual(ids, ['m08', 'm06', 'm01']); checked('Migration retains the existing Recommended order and original record IDs');
};
module.exports.install = install;
