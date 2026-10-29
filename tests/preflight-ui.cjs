/* Display and navigation checks with an explicit bridge fixture; no device or inference. */
const assert = require('node:assert/strict');
const {installFixture} = require('./foundation-ui.cjs');
function setup() {
  const f=window.__fixture, b=f.bundles[0]; b.installed=true;
  b.inputSchemas={'image.generate':{roles:{reference_image:{label:'参考图片',required:false,mimes:['image/png'],maxBytes:1000000}}}};
  f.__checkMode='normal';
  const fallback=window.__handleFoundation;
  window.__handleFoundation=command=>{
    if(command.action!=='preflightTask')return fallback(command);
    const report={schema:'lma.task-preflight/1',canEnqueue:command.request.allowUnmeasured,deviceValidated:false,modelInferenceTested:false,
      checkedStages:['request','models','engine','parameters','assets','inputs','recipe','resources'],issues:[],warnings:[{code:'memory_estimate_unknown',message:'此配方尚无可信峰值内存估算；检查通过不能保证能够完成生成'}],
      effectiveParameters:command.request.parameters,adjustments:[],resources:{availableRamBytes:3*1024**3,budgetRamBytes:7*1024**3,estimateKnown:false,estimatedPeakRamBytes:0,outputReserveBytes:135266304,availableStorageBytes:20*1024**3}};
    if(!report.canEnqueue)report.issues.push({code:'consent',message:'请明确选择允许尝试未测配方后运行',action:'edit_request'});
    if(f.__checkMode==='missing') {report.canEnqueue=false;report.issues=[{code:'assets',message:'缺少组件 <img src=x onerror="window.__pwned=true">',action:'manage_models'}];report.modelAssets=[{bundleId:b.id,installed:false,components:[{role:'model',bytes:1000,present:false,downloadable:true}]}];report.checkedStages=['request','models','engine','parameters'];report.warnings=[];delete report.resources;delete report.effectiveParameters;}
    if(f.__checkMode==='input') {report.canEnqueue=false;report.issues=[{code:'inputs',message:'请重新选择有效的参考素材',action:'manage_inputs'}];}
    return report;
  };
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,shot=async()=>{}) {
  await page.waitForFunction(()=>!window.__commands.length||(window.__fixture.commandResults||[]).some(r=>r.requestId===window.__commands[window.__commands.length-1].requestId));
  await page.evaluate(installFixture);await page.evaluate(setup);
  const commandsBefore=await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask'||/download/i.test(c.action)).length);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="image"]').click();
  await page.locator('[data-action="bundleUse"]').click();await page.locator('#localTaskForm [name="prompt"]').fill('只演示运行前检查；没有模型推理。');
  const config=await page.evaluate(()=>JSON.stringify(window.__fixture.bundles[0].config));
  await page.locator('[data-action="preflightTask"]').click();await page.waitForSelector('#taskPreflight.preflight-blocked');
  assert((await page.locator('#taskPreflight').textContent()).includes('试运行确认'));
  assert.equal(await page.locator('#localTaskForm [name="allowUnmeasured"]').isChecked(),false);checked('Preflight can inspect a request without manufacturing user consent');
  await shot('01-consent.png','检查参数和资源后仍需用户明确确认试运行 / Explicit consent remains required');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  assert((await page.locator('#taskPreflight').textContent()).includes('请重新检查'));
  await page.locator('[data-action="preflightTask"]').click();await page.waitForSelector('#taskPreflight.preflight-ready');
  assert((await page.locator('#taskPreflight').textContent()).includes('未知'));
  assert((await page.locator('#taskPreflight').textContent()).includes('尚无本机实测记录'));checked('Queue readiness displays resource facts and preserves unknown estimates and device limits');
  await overflow(page,'375px preflight report layout');await shot('02-ready.png','本次有效参数、资源与入队条件 / Parameters, resources and admission');
  await page.locator('#localTaskForm [name="prompt"]').fill('修改后的提示词');
  assert.equal(await page.locator('#taskPreflight.preflight-ready').count(),0);checked('Editing the request invalidates the previous readiness result');
  await page.evaluate(()=>{document.querySelector('[data-action="preflightTask"]').click();const input=document.querySelector('#localTaskForm [name="prompt"]');input.value+=' / changed during preview';input.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.waitForFunction(()=>document.getElementById('taskPreflight').textContent.includes('检查期间输入已改变'));
  checked('An asynchronous response cannot mark changed input ready');
  await page.evaluate(()=>window.__fixture.__checkMode='missing');await page.locator('[data-action="preflightTask"]').click();await page.waitForSelector('#taskPreflight.preflight-blocked');
  assert.equal(await page.locator('#taskPreflight img').count(),0);assert.equal(await page.evaluate(()=>!!window.__pwned),false);checked('Native diagnostics and component roles are escaped as text');
  await shot('03-missing.png','缺少组件及模型管理入口 / Missing assets with a management action');
  await page.locator('#taskPreflight [data-action="showLocal"]').click();assert(await page.locator('#modalBackdrop').isHidden());assert(await page.locator('#page-models.active').count());checked('Missing assets link back to Local without triggering a download');
  await page.locator('[data-action="bundleUse"]').click();await page.locator('#localTaskForm [name="prompt"]').fill('导入素材时保留当前输入');
  await page.evaluate(()=>{window.__fixture.artifacts.push({id:'fresh_input',available:true,bytes:68,origin:{kind:'imported',name:'刚导入的素材'},metadata:{mime:'image/png',width:1,height:1}});window.LMA.receive(window.__fixture);});
  assert.equal(await page.locator('[data-input-role] option[value="fresh_input"]').count(),1);
  assert.equal(await page.locator('#localTaskForm [name="prompt"]').inputValue(),'导入素材时保留当前输入');checked('A completed native input import updates the open form and preserves typed input');
  await page.locator('[data-input-role]').selectOption('fresh_input');
  assert.equal(await page.locator('[data-input-role]').inputValue(),'fresh_input');
  await page.evaluate(()=>{window.__fixture.artifacts=[];window.LMA.receive(window.__fixture);});
  assert(await page.locator('[name="inputRefreshReview"]').isVisible());
  assert.equal(await page.locator('[name="inputRefreshReview"]').isChecked(),false);
  assert.equal(await page.locator('[data-input-role]').inputValue(),'');checked('Removed media is cleared with an explicit review requirement before submission');
  await page.locator('#inputRefreshNotice').evaluate(el=>el.scrollIntoView({block:'center'}));
  await shot('04-input-review.png','素材变化与重新确认 / Changed media requires review');
  await page.evaluate(()=>window.__fixture.__checkMode='input');await page.locator('[data-action="preflightTask"]').click();await page.waitForSelector('#taskPreflight.preflight-blocked');
  await page.locator('[data-action="preflightInputs"]').click();assert(await page.locator('#page-tasks.active').count());assert(await page.locator('#modalBackdrop').isHidden());checked('Input diagnostics open the real media section of Tasks');
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>c.action==='submitTask'||/download/i.test(c.action)).length),commandsBefore);
  assert.equal(await page.evaluate(()=>JSON.stringify(window.__fixture.bundles[0].config)),config);checked('Preview and recovery navigation never submit, download or change per-model defaults');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();
};
module.exports.setup=setup;
