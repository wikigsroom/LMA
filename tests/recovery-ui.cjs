/* Actual production pages, explicitly simulated native data; no Android or model execution. */
const assert = require('node:assert/strict');
const {installFixture} = require('./foundation-ui.cjs');

function setup() {
  const f=window.__fixture,b=f.bundles[0]; b.installed=true;
  const request=i=>({bundleId:b.id,type:'image.generate',input:{prompt:'界面测试任务 '+i},inputSummary:'界面测试任务 '+i,parameters:{width:512,height:512,steps:4},allowUnmeasured:true});
  f.jobs=Array.from({length:26},(_,i)=>({id:'ui_history_'+i,state:i===0?'queued':i===25?'interrupted':i===1?'failed':'succeeded',stage:i===0?'queued':'saving',createdAt:Date.now()+i,finishedAt:i===0?0:Date.now()+i,request:request(i),artifacts:i===25?['wb_result']:[]}));
  f.jobs[25].outputRecovery={kind:'committed_output_after_interruption',executionResumed:false};
  f.jobs[25].error='Execution was interrupted; explicit retry starts a new task.';
  f.artifacts=[{id:'wb_result',jobId:'ui_history_25',available:true,createdAt:Date.now(),bytes:68,sha256:'f'.repeat(64),metadata:{mime:'image/png',width:1,height:1},origin:{kind:'generated'},provenance:{execution:'same_android_phone',request:request(25),bundle:{id:b.id}}}];
  f.taskDrafts=[{bundleId:b.id,type:'image.generate',revision:1,savedAt:Date.now(),inputSummary:'独立草稿保留'}];
  f.outputRecovery={recoveredOutputs:1,discardedStagingFiles:1,discardedUncommittedFiles:1,reclaimedBytes:8,executionResumed:false};
  delete f.taskCapacity;f.__historyConflict=false;
  const terminal=j=>['succeeded','failed','interrupted','cancelled'].includes(j.state);
  const review=ids=>JSON.stringify(ids.map(id=>{const j=f.jobs.find(j=>j.id===id);if(!j||!terminal(j))throw Error('任务记录已经变化，请重新检查清理范围');return [id,j.state,j.createdAt,j.finishedAt];}));
  const fallback=window.__handleFoundation;
  window.__handleFoundation=command=>{
    if(command.action==='inspectArtifact')return f.artifacts.find(a=>a.id===command.id);
    if(command.action==='planTaskHistory') {const ids=f.jobs.filter(terminal).map(j=>j.id);return {ids,count:ids.length,review:review(ids)};}
    if(command.action==='clearTaskHistory') {
      const {ids,review:expected}=command.selection;
      if(f.__historyConflict||review(ids)!==expected)throw Error('任务记录已经变化，请重新检查清理范围');
      f.jobs=f.jobs.filter(j=>!ids.includes(j.id));return {removed:ids.length};
    }
    if(command.action==='preflightTask')return {schema:'lma.task-preflight/1',canEnqueue:false,deviceValidated:false,modelInferenceTested:false,checkedStages:['request','models','engine','parameters','assets','inputs','recipe','resources'],issues:[{code:'capacity',message:'任务历史已满；检查并清理已结束记录，保留结果文件',action:'manage_tasks'}],warnings:[]};
    return fallback(command);
  };
  window.LMA.receive(f);
}

module.exports=async function(page,checked,overflow,output,shot=async()=>{}) {
  await page.waitForFunction(()=>!window.__commands.length||(window.__fixture.commandResults||[]).some(r=>r.requestId===window.__commands[window.__commands.length-1].requestId));
  await page.evaluate(installFixture);await page.evaluate(setup);
  const downloadsBefore=await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask'||/download/i.test(c.action)).length);
  await page.locator('.nav-item[data-tab="tasks"]').click();
  await page.locator('[data-action="filterJobs"][data-kind="all"]').click();await page.locator('#jobSearch').fill('');
  await page.locator('[data-action="filterArtifacts"][data-kind="all"]').click();
  assert((await page.locator('#outputRecoveryStatus').textContent()).includes('找回 1 个'));
  assert((await page.locator('.job-card').first().textContent()).includes('未自动重跑'));
  assert.equal(await page.locator('.job-card').count(),20);checked('Recovered-output status keeps interruption visible and paginates long task history');
  await overflow(page,'375px task recovery and capacity layout');await shot('01-recovery.png','UI FIXTURE · Startup output recovery and independent capacity / 中断结果与容量');
  await page.locator('.job-card').first().locator('[data-action="jobInfo"]').click();await page.waitForSelector('.task-detail');
  assert((await page.locator('.task-detail').textContent()).includes('未自动续步'));
  assert.equal(await page.locator('.task-detail [data-action="artifactInfo"]').isEnabled(),true);checked('Interrupted task details expose its recovered committed result without changing execution state');await page.keyboard.press('Escape');
  await page.locator('[data-action="moreJobs"]').click();assert.equal(await page.locator('.job-card').count(),26);checked('Load-more displays remaining records without mutating the queue');
  await page.locator('[data-action="filterJobs"][data-kind="active"]').click();assert.equal(await page.locator('.job-card').count(),1);
  await page.locator('[data-action="filterJobs"][data-kind="issues"]').click();assert.equal(await page.locator('.job-card').count(),2);
  await page.locator('#jobSearch').fill('ui_history_25');assert.equal(await page.locator('.job-card').count(),1);checked('State filters and task-identity search combine without hiding result storage');
  await shot('02-filters.png','UI FIXTURE · Filter and search interrupted tasks / 筛选和搜索任务');
  await page.locator('#jobSearch').fill('no such task');await page.locator('[data-action="resetJobFilters"]').click();assert.equal(await page.locator('.job-card').count(),20);assert.equal(await page.locator('#jobSearch').inputValue(),'');checked('Empty search offers a full reset and restores the default page size');
  const before=await page.evaluate(()=>JSON.stringify({jobs:window.__fixture.jobs,bundles:window.__fixture.bundles,artifacts:window.__fixture.artifacts,drafts:window.__fixture.taskDrafts}));
  const clears=()=>page.evaluate(()=>window.__commands.filter(c=>c.action==='clearTaskHistory').length);
  await page.locator('#clearTaskHistoryButton').click();await page.waitForSelector('#clearTaskHistoryForm');
  assert.equal(await page.evaluate(()=>JSON.stringify({jobs:window.__fixture.jobs,bundles:window.__fixture.bundles,artifacts:window.__fixture.artifacts,drafts:window.__fixture.taskDrafts})),before);checked('Reviewing a cleanup plan performs no mutation or model operation');
  const priorClears=await clears();await page.locator('#clearTaskHistoryForm [data-action="clearTaskHistory"]').click();assert.equal(await clears(),priorClears);checked('History deletion requires an explicit confirmation checkbox');
  await page.locator('#clearTaskHistoryForm details').click();await overflow(page,'375px reviewed history selection');await shot('03-review.png','UI FIXTURE · Review exactly which finished records will be removed / 确认清理范围');
  await page.evaluate(()=>{const f=window.__fixture;f.jobs.push({id:'finished_after_review',state:'succeeded',stage:'saving',createdAt:Date.now(),finishedAt:Date.now(),request:{bundleId:'ui_sd',type:'image.generate',inputSummary:'检查后才结束的任务'},artifacts:[]});window.LMA.receive(f);});
  await page.locator('[name="confirmHistory"]').check();await page.locator('#clearTaskHistoryForm [data-action="clearTaskHistory"]').click();
  await page.waitForFunction(()=>window.__fixture.jobs.length===2);
  assert.deepEqual(await page.evaluate(()=>window.__fixture.jobs.map(j=>j.id)),['ui_history_0','finished_after_review']);checked('Cleanup removes only reviewed terminal identities and retains active and newly finished tasks');
  assert.equal(await page.evaluate(()=>window.__fixture.artifacts.length),1);assert.equal(await page.evaluate(()=>window.__fixture.taskDrafts.length),1);assert.equal(await page.evaluate(()=>window.__fixture.bundles[0].installed),true);checked('Removing history leaves saved results, drafts and installed model assets independent');
  assert((await page.locator('#taskCapacity').textContent()).includes('任务记录 2 / 256'));checked('Native cleanup response refreshes task capacity in the current page');
  await page.locator('#clearTaskHistoryButton').click();await page.waitForSelector('#clearTaskHistoryForm');
  await page.evaluate(()=>window.__fixture.__historyConflict=true);await page.locator('[name="confirmHistory"]').check();await page.locator('#clearTaskHistoryForm [data-action="clearTaskHistory"]').click();
  await page.waitForFunction(()=>document.getElementById('historyCleanupHint')?.textContent.includes('重新检查'));
  assert.equal(await page.locator('[name="confirmHistory"]').isChecked(),false);assert.equal(await page.evaluate(()=>window.__fixture.jobs.length),2);checked('Native cleanup conflicts preserve the modal, clear consent and retain every task');await shot('04-conflict.png','UI FIXTURE · A changed selection requires fresh review / 冲突保留记录并重新确认');
  await page.evaluate(()=>window.__fixture.__historyConflict=false);await page.locator('#clearTaskHistoryForm [data-action="planTaskHistory"]').click();
  await page.waitForFunction(()=>document.getElementById('historyCleanupHint')?.textContent==='');
  await page.locator('[name="confirmHistory"]').check();await page.locator('#clearTaskHistoryForm [data-action="clearTaskHistory"]').click();await page.waitForFunction(()=>window.__fixture.jobs.length===1);
  assert.equal(await page.locator('#clearTaskHistoryButton').isDisabled(),true);checked('A fresh review can commit successfully and cannot offer active tasks for cleanup');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="image"]').click();
  await page.locator('[data-action="bundleUse"]').click();await page.locator('[name="prompt"]').fill('容量错误入口');await page.locator('[data-action="preflightTask"]').click();await page.waitForSelector('[data-action="preflightHistory"]');
  await page.locator('[data-action="preflightHistory"]').click();assert(await page.locator('#page-tasks.active').count());assert(await page.locator('#modalBackdrop').isHidden());checked('Preflight capacity diagnostics link to task management without submitting or downloading');
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask'||/download/i.test(c.action)).length),downloadsBefore);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();
};
module.exports.setup=setup;
