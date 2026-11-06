/* Memory unloading is distinct from model-file deletion; only fixture commands execute here. */
const assert = require('node:assert/strict');
const {installFixture} = require('./foundation-ui.cjs');

module.exports = async function (page, checked, checkOverflow) {
  const original = await page.evaluate(() => structuredClone(window.__fixture));
  try {
    await page.evaluate(installFixture);
    await page.evaluate(() => {
      const f = window.__fixture; f.models.find(m => m.id === 'm08').installed = true;
      f.engine = {state: 'ready', modelId: 'm08', generating: false, externalGenerating: false, detail: '模型已就绪'};
      window.LMA.receive(f);
    });
    const before = await page.evaluate(() => window.__commands.filter(c => c.action === 'stopEngine').length);
    await page.locator('#runtimeAction').click();
    assert.equal(await page.locator('#modalTitle').textContent(), '运行中的模型');
    assert((await page.locator('#modal').textContent()).includes('已加载到内存'));
    assert.equal(await page.locator('#modal [data-action="stopTextModel"]').textContent().then(s => s.trim()), '卸载模型');
    checked('The global runtime strip opens named resident-model management');
    await page.locator('#modal [data-action="stopTextModel"]').click();
    assert.equal(await page.locator('#modal [data-command="stopEngine"]').getAttribute('data-id'), 'm08');
    assert((await page.locator('#modal').textContent()).includes('已下载文件'));
    await page.locator('#modal .modal-actions [data-action="closeModal"]').click();
    assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'stopEngine').length), before);
    checked('Unloading explains cancellation and preservation, names the model and requires confirmation');
    await page.locator('.nav-item[data-tab="models"]').click();
    await page.locator('[data-filter="local"]').click();
    await page.locator('[data-task="any"]').click();
    const card = page.locator('[data-model="m08"]');
    assert(await card.locator('[data-action="stopTextModel"]').isVisible());
    assert(await card.locator('[data-action="deleteModel"]').isVisible());
    assert(await card.locator('[data-action="stopTextModel"]').isEnabled());
    checked('Loaded Local cards expose separate enabled unload and file-delete controls');
    await card.locator('[data-action="stopTextModel"]').click();
    await page.locator('#modal [data-command="stopEngine"]').click();
    assert.equal(await page.evaluate(() => window.__commands.filter(c => c.action === 'stopEngine').length), before + 1);
    assert(await page.evaluate(() => window.__fixture.models.find(m => m.id === 'm08').installed));
    checked('Confirmed unload dispatches stopEngine while preserving the downloaded fixture model');
    await page.evaluate(() => { window.__fixture.engine.state = 'stopped'; window.__fixture.engine.generating = false; window.LMA.receive(window.__fixture); });
    await page.locator('.nav-item[data-tab="server"]').click();
    assert((await page.locator('#runningModelsPanel').textContent()).includes('当前没有驻留'));
    checked('The API page accurately shows the unloaded state independently of the listener');
    await page.evaluate(() => { window.__fixture.engine.state = 'suspended'; window.LMA.receive(window.__fixture); });
    assert((await page.locator('#runningModelsPanel').textContent()).includes('暂挂'));
    checked('Suspended models are distinguished from models currently loaded in memory');
    for (const theme of ['dark', 'light']) {
      await page.evaluate(theme => { window.__fixture.settings.theme = theme; window.LMA.receive(window.__fixture); }, theme);
      for (const width of [320, 390, 768, 1024]) {
        await page.setViewportSize({width, height: 850});
        await checkOverflow(page, `running-model management ${theme} ${width}px`);
      }
    }
  } finally {
    await page.keyboard.press('Escape');
    await page.evaluate(original => { window.__fixture = original; window.LMA.receive(original); }, original);
    await page.setViewportSize({width: 375, height: 812});
  }
};
