/* Current product pages with explicit desktop OS/task fixture data, never phone evidence. */
const assert=require('node:assert/strict');
const {installFixture}=require('./foundation-ui.cjs');
function setup(){
  const f=window.__fixture,b=f.bundles[0];b.installed=true;
  const r={enabled:true,status:'monitoring',samples:4,minimumAvailableRamBytes:1900*1048576,minimumAvailableStorageBytes:12000*1048576,maximumThermalStatus:-1,thermalKnown:false,probeErrors:0,stopCode:'',message:'',scope:'shared_system_availability_not_model_peak_memory'};
  f.foundation=f.foundation||{};f.foundation.execution={resourceMonitoringEnabled:true,active:{id:91,kind:'job',modelId:b.id,runtimeResources:r},waiting:[],lastResourceStop:null};
  f.jobs=[{id:'resource_job',state:'running',stage:'generating',createdAt:Date.now(),request:{bundleId:b.id,type:'image.generate',input:{prompt:'山间的小屋，晨光'},parameters:{width:512,height:512,steps:4},allowUnmeasured:true},artifacts:[]}];
  f.taskDrafts=[];f.artifacts=[];
  const fallback=window.__handleFoundation;
  window.__handleFoundation=command=>{
    if(command.action==='retryTask'){
      const previous=f.jobs.find(j=>j.id===command.id),job={...JSON.parse(JSON.stringify(previous)),id:'resource_retry',state:'queued',stage:'queued',error:'',createdAt:Date.now()};delete job.runtimeResources;f.jobs.unshift(job);return job;
    }
    return fallback(command);
  };
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,shot=async()=>{}){
  await page.evaluate(installFixture);await page.evaluate(setup);
  const before=await page.evaluate(()=>window.__commands.length);
  await page.locator('.nav-item[data-tab="tasks"]').click();
  let panel=page.locator('#runtimeResourceStatus');await panel.waitFor({state:'visible'});
  assert.match(await panel.textContent(),/最低系统可用内存/);assert.match(await panel.textContent(),/未知（系统未提供）/);
  checked('Active task displays shared system minima and honestly unknown Android thermal data');
  await overflow(page,'375px running-resource panel');await shot('01-running.png','UI FIXTURE · Running resource observations / 运行资源检查，温度未知');
  await page.evaluate(()=>{
    const f=window.__fixture,ticket=f.foundation.execution.active,r=ticket.runtimeResources;
    r.status='stopped';r.thermalKnown=true;r.maximumThermalStatus=3;r.stopCode='severe_thermal';r.message='手机处于严重高温状态，已停止本次执行；请降温后明确重试，参数和模型文件保留';
    const job=f.jobs[0];job.state='failed';job.error=r.message;job.runtimeResources=JSON.parse(JSON.stringify(r));f.foundation.execution.lastResourceStop=ticket;f.foundation.execution.active=null;window.LMA.receive(f);
  });
  assert.match(await panel.textContent(),/最近停止/);assert.match(await panel.textContent(),/降温后明确重试/);
  checked('Completed stop remains visible after the execution slot is released');
  await page.locator('[data-action="jobInfo"][data-id="resource_job"]').click();await page.waitForSelector('.task-detail');
  const detail=await page.locator('#modalContent').textContent();assert.match(detail,/运行资源/);assert.match(detail,/模型峰值内存和速度需单独测量/);assert.match(detail,/重试会创建新任务/);
  checked('Task details retain resource cause and distinguish system availability from model peak memory');
  await overflow(page,'375px stopped-resource details');await shot('02-stopped-detail.png','UI FIXTURE · Stop reason and saved task report / 停止原因和任务记录');
  await page.keyboard.press('Escape');await page.locator('[data-action="retryTask"][data-id="resource_job"]').click();
  await page.waitForFunction(()=>window.__fixture.jobs.some(j=>j.id==='resource_retry'));
  assert.equal(await page.evaluate(()=>window.__fixture.jobs.find(j=>j.id==='resource_job').state),'failed');
  assert.equal(await page.evaluate(()=>window.__fixture.jobs.find(j=>j.id==='resource_retry').runtimeResources),undefined);
  checked('Explicit retry creates a separate task without rewriting the previous resource report');
  await shot('03-explicit-retry.png','UI FIXTURE · User retries a new task / 用户明确重试，保留原记录');
  const commands=await page.evaluate(n=>window.__commands.slice(n),before);assert.equal(commands.filter(c=>/download|import|prepareAssets|assembleAssets|deleteBundle/.test(c.action)).length,0);
  checked('Resource review and explicit retry never retrieve or replace model assets');
  await page.evaluate(()=>{const f=window.__fixture,r=f.foundation.execution.lastResourceStop.runtimeResources;r.status='ended';r.message='';r.samples=0;window.LMA.receive(f);});
  assert.match(await panel.textContent(),/本次执行未取得系统资源读数/);
  checked('An ended short execution without samples never appears to be still awaiting a measurement');
  await page.evaluate(()=>{const f=window.__fixture;f.foundation.execution.lastResourceStop=null;window.LMA.receive(f);});assert.equal(await panel.isHidden(),true);
  checked('Resource panel disappears when there is no active execution or stop report');
  await page.locator('.nav-item[data-tab="models"]').click();
};
