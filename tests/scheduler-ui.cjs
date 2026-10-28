/* Shared execution waiting states with an explicit simulated native bridge. */
const assert = require('node:assert/strict');
const migrationUI = require('./migration-ui.cjs');

async function install(page, reply = false) {
  await migrationUI.install(page);
  await page.evaluate(reply => {
    const f = window.__fixture;
    f.engine = {...f.engine, state: 'suspended', modelId: 'm08', generating: reply, externalGenerating: false,
      detail: '文本模型暂时卸载，由本机队列使用执行槽；空闲后恢复'};
    f.foundation = {...f.foundation, execution: {policy: 'single_engine_fifo', active: {id: 1, kind: 'job', modelId: 'ui_sd', state: 'active'},
      waiting: reply ? [{id: 2, kind: 'chat', modelId: 'm08', state: 'waiting'}] : [], waitingCount: reply ? 1 : 0}};
    if (reply) f.chat = {...f.chat, messages: [{id: 'ui_waiting_reply', role: 'assistant', content: '', reasoning: '', status: 'generating', error: '', tokens: 0, elapsed: 0}]};
    window.LMA.receive(f);
  }, reply);
}

module.exports = async function checkScheduler(page, checked, checkOverflow) {
  await install(page);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="text"]').click(); await page.locator('[data-filter="local"]').click();
  const card = page.locator('.model-card').filter({has: page.locator('[data-action="modelInfo"][data-id="m08"]')});
  assert((await card.innerText()).includes('等待执行')); checked('Suspended resident remains selected with a waiting label');
  assert.equal(await card.locator('[data-action="load"]').count(), 0); checked('A suspended selected resident is not offered as a new load action');
  await page.locator('.nav-item[data-tab="chat"]').click(); await page.locator('#chatInput').fill('等待图片任务结束后，在本机回复。');
  assert(await page.locator('#sendButton').isEnabled()); checked('Chat can queue for an explicitly selected suspended model');
  assert((await page.locator('#composerHint').innerText()).includes('排队')); checked('Composer explains automatic slot waiting');
  await page.locator('[data-action="pickModel"]').first().click();
  assert((await page.locator('#modalContent').innerText()).includes('自动切换引擎')); checked('Model picker explains shared scheduling');
  assert.equal(await page.locator('[data-action="stopTextModel"]').count(), 1); checked('User can stop a resident while it is temporarily suspended');
  await page.keyboard.press('Escape');
  await install(page, true); await page.locator('.nav-item[data-tab="chat"]').click();
  assert((await page.locator('#composerHint').innerText()).includes('回复已排队')); checked('Waiting chat is distinguished from active token generation');
  assert.equal(await page.locator('#sendButton').getAttribute('aria-label'), '停止生成'); checked('Waiting reply retains its cancellation control');
  assert((await page.locator('#runtimeDetail').innerText()).includes('等待本机执行槽')); checked('Runtime status explains the queued reply');
  await checkOverflow(page, 'Shared execution waiting state');
  await page.evaluate(() => { const f = window.__fixture; f.engine = {...f.engine, state: 'stopped', generating: false}; f.chat.messages = []; window.LMA.receive(f); });
  assert(await page.locator('#sendButton').isDisabled()); checked('A user-stopped model cannot enqueue a new chat');
};
module.exports.install = install;
