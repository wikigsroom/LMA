/* Product interactions with an explicit simulated bridge, never model/Android evidence. */
const assert = require('node:assert/strict');
const {installFixture} = require('./foundation-ui.cjs');

function setup() {
  const f = window.__fixture, b = f.bundles[0]; b.installed = true;
  b.inputSchemas = {'image.generate': {roles: {reference_image: {label: '参考图片', required: false, mimes: ['image/png'], maxBytes: 1000000}}}};
  f.taskDrafts = []; f.__drafts = {}; f.__revision = 0;
  const fallback = window.__handleFoundation;
  const clean = request => Object.fromEntries(['bundleId', 'type', 'input', 'parameters', 'adapters'].filter(k => request[k] !== undefined).map(k => [k, JSON.parse(JSON.stringify(request[k]))]));
  window.__handleFoundation = command => {
    if (command.action === 'saveTaskDraft') {
      const current = f.__drafts[command.request.bundleId];
      if ((current ? current.revision : 0) !== command.expectedRevision) throw Error('Draft conflict');
      const record = {bundleId: command.request.bundleId, request: {...clean(command.request), allowUnmeasured: false}, revision: ++f.__revision, savedAt: Date.now()};
      f.__drafts[record.bundleId] = record;
      f.taskDrafts = Object.values(f.__drafts).map(d => ({bundleId:d.bundleId,type:d.request.type,revision:d.revision,savedAt:d.savedAt,inputSummary:d.request.input.prompt})); return record;
    }
    if (command.action === 'inspectTaskDraft') return f.__drafts[command.id];
    if (command.action === 'deleteTaskDraft') { delete f.__drafts[command.id]; f.taskDrafts = f.taskDrafts.filter(d => d.bundleId !== command.id); return {}; }
    if (command.action === 'editTask') return {...clean(f.jobs.find(j => j.id === command.id).request), allowUnmeasured:false};
    if (command.action === 'editArtifact') return {...clean(f.artifacts.find(a => a.id === command.id).provenance.request), allowUnmeasured:false};
    if (command.action === 'inspectArtifact') return f.artifacts.find(a => a.id === command.id);
    return fallback(command);
  };
  window.LMA.receive(f);
}
module.exports = async function (page, checked, overflow, output, shot = async () => {}) {
  await page.waitForFunction(() => !window.__commands.length || (window.__fixture.commandResults || []).some(r => r.requestId === window.__commands[window.__commands.length - 1].requestId));
  await page.evaluate(installFixture); await page.evaluate(setup);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="image"]').click();
  const settings = await page.evaluate(() => JSON.stringify(window.__fixture.bundles[0].config));
  await page.locator('[data-bundle="ui_sd"] [data-action="bundleUse"]').click();
  await page.locator('[data-action="saveTaskDraft"]').click();
  await page.waitForFunction(() => window.__fixture.taskDrafts.length === 1);
  assert.equal(await page.evaluate(() => window.__fixture.jobs.length), 0); checked('Empty-prompt draft saves without task submission or admission consent');
  await page.locator('.task-parameters summary').click();
  await page.locator('[name="prompt"]').fill('保存草稿：一只在书桌旁的狐狸'); await page.locator('[data-bundle-field="steps"]').fill('12');
  await page.locator('[data-action="saveTaskDraft"]').click();
  await page.waitForFunction(() => window.__fixture.__drafts.ui_sd.request.input.prompt.includes('狐狸'));
  await page.keyboard.press('Escape'); await page.locator('.nav-item[data-tab="tasks"]').click(); await page.locator('[data-action="filterArtifacts"][data-kind="all"]').click();
  assert.equal(await page.locator('.draft-card').count(), 1); await overflow(page, '375px per-model draft cards'); await shot('01-drafts.png', 'UI FIXTURE · Per-model persistent-draft controls / 按模型保存草稿');
  await page.locator('[data-action="restoreTaskDraft"]').click(); await page.waitForSelector('#localTaskForm');
  assert.equal(await page.locator('[name="prompt"]').inputValue(), '保存草稿：一只在书桌旁的狐狸');
  assert.equal(await page.locator('[data-bundle-field="steps"]').inputValue(), '12'); assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(), false);
  assert.equal(await page.evaluate(() => JSON.stringify(window.__fixture.bundles[0].config)), settings); checked('Draft restore recovers prompt and parameters without changing model settings or accepting admission');
  await shot('02-restore.png', 'UI FIXTURE · Restored request awaits explicit submission / 恢复后仍需主动提交');
  await page.locator('[name="allowUnmeasured"]').check(); await page.locator('#localTaskForm [type="submit"]').click();
  await page.waitForSelector('.job-card');
  await page.evaluate(() => {
    const f=window.__fixture,j=f.jobs[0]; j.state='succeeded'; j.stage='saving'; j.artifacts=['wb_result']; j.request.submissionHash='stale receipt';
    f.artifacts=[{id:'wb_result',jobId:j.id,createdAt:Date.now(),available:true,bytes:68,sha256:'f'.repeat(64),metadata:{mime:'image/png',width:1,height:1},origin:{kind:'generated'},provenance:{execution:'same_android_phone',request:JSON.parse(JSON.stringify(j.request)),bundle:{id:'ui_sd'}}}];
    window.LMA.receive(f);
  });
  await page.locator('[data-action="jobInfo"]').click(); await page.waitForSelector('.task-detail');
  assert((await page.locator('.task-prompt-text').textContent()).includes('狐狸')); assert.equal(await page.locator('.task-detail [data-action="artifactInfo"]').count(), 1);
  await shot('03-task-details.png', 'UI FIXTURE · Readable task parameters and direct result actions / 任务参数与结果入口');
  await page.locator('.task-detail [data-action="editTask"]').click(); await page.waitForSelector('#localTaskForm');
  assert.equal(await page.locator('[data-bundle-field="steps"]').inputValue(),'12'); assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false); checked('Completed task opens an editable new request without starting another generation');
  await page.keyboard.press('Escape');
  await page.locator('[data-action="jobResults"]').click(); await page.waitForSelector('[data-action="editArtifact"]');
  await page.locator('[data-action="editArtifact"]').click(); await page.waitForSelector('#localTaskForm');
  assert((await page.locator('[name="prompt"]').inputValue()).includes('狐狸')); checked('Result provenance restores the original generation inputs'); await page.keyboard.press('Escape');
  await page.locator('.artifact-card [data-action="artifactInput"]').click(); await page.waitForSelector('[data-action="useArtifactInput"]');
  await shot('04-next-model.png', 'UI FIXTURE · Select a compatible local input role / 选择接收素材的本机模型');
  await page.locator('[data-action="useArtifactInput"]').click(); await page.waitForSelector('#localTaskForm');
  assert.equal(await page.locator('[data-input-role="reference_image"]').inputValue(),'wb_result');
  assert.equal(await page.locator('[name="prompt"]').inputValue(),''); checked('Generated media fills a compatible local input role and waits for user text/confirmation');
  await page.locator('[name="prompt"]').fill('用此参考素材生成下一张图'); await page.locator('[data-action="saveTaskDraft"]').click();
  await page.waitForFunction(()=>window.__fixture.__drafts.ui_sd.request.input.artifacts?.[0]?.artifactId==='wb_result');
  await page.keyboard.press('Escape');
  await page.evaluate(()=>{window.__fixture.artifacts=[];window.LMA.receive(window.__fixture);});
  await page.locator('[data-action="restoreTaskDraft"]').click(); await page.waitForSelector('[name="reviewRestored"]');
  assert((await page.locator('.restore-notice').textContent()).includes('参考素材不可用')); assert.equal(await page.locator('[name="reviewRestored"]').isChecked(),false); checked('Missing restored references are disclosed and require an explicit review');
  await shot('05-missing-reference.png','UI FIXTURE · Missing media stays visible for user review / 缺失素材明确提示');
  await page.keyboard.press('Escape');
  await page.locator('[data-action="removeTaskDraft"]').click(); await page.locator('[data-action="deleteTaskDraft"]').click();
  await page.waitForFunction(()=>window.__fixture.taskDrafts.length===0); assert.equal(await page.locator('#draftSection').isVisible(),false); checked('Draft deletion keeps submitted history and model configuration independent');
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="any"]').click();
  assert.equal(await page.evaluate(()=>window.__fixture.jobs.length),1); assert.equal(await page.evaluate(()=>JSON.stringify(window.__fixture.bundles[0].config)),settings);
};
module.exports.setup = setup;
