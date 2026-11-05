/* Destructive actions run against bridge fixtures only, never phone model files. */
const assert = require('node:assert/strict');
const {installFixture} = require('./foundation-ui.cjs');

module.exports = async function (page, checked, checkOverflow) {
  const original = await page.evaluate(() => structuredClone(window.__fixture));
  try {
    await page.evaluate(installFixture);
    await page.evaluate(() => {
      const f = window.__fixture, base = f.bundles[0];
      f.bundles = ['image', 'video', 'audio', '3d'].map(task => {
        const b = structuredClone(base); b.id = b.manifest.id = b.manifest.modelId = 'delete_fixture_' + task;
        b.manifest.name = '删除入口检查 · ' + task; b.manifest.tasks = [task]; b.installed = true; return b;
      });
      const text = f.models.find(m => m.id === 'm08'); text.installed = true; text.download = {};
      window.LMA.receive(f);
    });
    await page.locator('.nav-item[data-tab="models"]').click();
    await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="any"]').click();
    const deletions = () => page.evaluate(() => window.__commands.filter(c => /^delete(Model|Bundle)$/.test(c.action)).length);
    const before = await deletions();
    for (const task of ['image', 'video', 'audio', '3d']) {
      const button = page.locator('[data-bundle="delete_fixture_' + task + '"] .model-footer [data-action="bundleRemove"]');
      await button.scrollIntoViewIfNeeded(); assert(await button.isVisible()); assert(await button.isEnabled());
      assert.equal((await button.textContent()).trim(), '删除');
    }
    const textDelete = page.locator('[data-model="m08"] .model-footer [data-action="deleteModel"]');
    assert.equal((await textDelete.textContent()).trim(), '删除');
    assert.equal(await deletions(), before); checked('All five model types expose labelled deletion on their outer card without dispatching deletion');
    await textDelete.click(); assert.equal(await page.locator('#modal [data-command="deleteModel"]').getAttribute('data-id'), 'm08');
    await page.locator('#modal .modal-actions [data-action="closeModal"]').click();
    assert.equal(await deletions(), before); checked('Text card deletion requires confirmation and cancelling preserves the model');
    const imageDelete = page.locator('[data-bundle="delete_fixture_image"] [data-action="bundleRemove"]');
    await imageDelete.click(); assert.equal(await deletions(), before);
    assert.equal(await page.locator('#modal [data-command="deleteBundle"]').getAttribute('data-id'), 'delete_fixture_image');
    assert.equal(await page.locator('#modal .delete-target').innerText(), '删除入口检查 · image');
    await page.locator('#modal .modal-actions [data-action="closeModal"]').click();
    assert.equal(await deletions(), before); checked('Media card deletion reuses the existing confirmation and cancel sends no native deletion');
    for (const state of ['queued', 'downloading', 'verifying', 'pausing', 'importing', 'installing']) {
      await page.evaluate(state => { window.__fixture.bundles[0].transfer = {state, received: 100}; window.LMA.receive(window.__fixture); }, state);
      assert(await imageDelete.isDisabled()); assert((await imageDelete.textContent()).includes('暂停后删除'));
    }
    await page.evaluate(() => { window.__fixture.bundles[0].transfer.state = 'paused'; window.LMA.receive(window.__fixture); });
    assert(await imageDelete.isEnabled()); checked('Busy media transfers retain a disabled, explained delete entry and paused transfers restore it');
    for (const state of ['queued', 'downloading', 'verifying', 'pausing']) {
      await page.evaluate(state => { window.__fixture.models.find(m => m.id === 'm08').download = {state, received: 100}; window.LMA.receive(window.__fixture); }, state);
      assert(await textDelete.isDisabled()); assert((await textDelete.textContent()).includes('暂停后删除'));
    }
    await page.evaluate(() => { window.__fixture.models.find(m => m.id === 'm08').download.state = 'paused'; window.LMA.receive(window.__fixture); });
    assert(await textDelete.isEnabled()); checked('Busy text transfers explain deletion availability instead of hiding the entry');
    await page.setViewportSize({width: 320, height: 720}); await checkOverflow(page, '320px model-card delete controls');
    await imageDelete.click(); await page.locator('#modal [data-command="deleteBundle"]').click();
    await page.waitForFunction(() => !window.__fixture.bundles[0].installed);
    assert.equal(await deletions(), before + 1);
    assert.deepEqual(await page.evaluate(() => window.__fixture.bundles.slice(1).map(b => b.installed)), [true, true, true]);
    checked('Confirm deletes exactly the selected fixture bundle and preserves peer models');
  } finally {
    await page.keyboard.press('Escape');
    await page.evaluate(original => { window.__fixture = original; window.LMA.receive(original); }, original);
    await page.setViewportSize({width: 375, height: 812});
  }
};
