/* Actual UI and pinned manifests; synthetic bridge and input receipts only. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const bundles=JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/multiview-bundles.json'),'utf8')).bundles;
const legacy=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models;
const roles=['reference_front','reference_right','reference_back','reference_left'];
function install({bundles,legacy,roles}){
 const f=window.__fixture;f.models=legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));
 f.bundles=bundles.map(manifest=>({id:manifest.id,manifest,installed:false,parameterSchema:manifest.parameters,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},
  inputSchemas:{'mesh.generate':{fixedPrompt:'Generate one 3D asset from four posed local views.',promptHelp:'标准转台：20° 水平视角、零仰角、距离 3.119204998；图片必须匹配相机。',roles:Object.fromEntries(roles.map(r=>[r,{label:r+' · RGBA PNG',required:true,mimes:['image/png'],maxBytes:16777216,maxPixels:4194304}]))}},
  plan:{totalBytes:manifest.components.reduce((n,c)=>n+c.bytes,0),remainingBytes:manifest.components.reduce((n,c)=>n+c.bytes,0),reusableBytes:0,components:manifest.components.map(c=>({...c,reusable:false,downloadable:false}))}}));
 f.localEngines=[{engine:'pixal_multiview',available:true,deviceValidated:false}];
 f.artifacts=roles.map((r,i)=>({id:'mv_view_'+i,available:true,bytes:100,origin:{kind:'imported',name:r+' · UI FIXTURE.png'},metadata:{mime:'image/png',width:256,height:256}}));
 f.artifacts.push({id:'mv_jpeg',available:true,bytes:100,metadata:{mime:'image/jpeg',width:256,height:256}});f.jobs=[];f.taskDrafts=[];f.__mvDrafts={};
 window.__handleFoundation=c=>{
  if(c.action==='saveBundleSettings'){const b=f.bundles.find(b=>b.id===c.id);b.config.values=c.settings;return b.config;}
  if(c.action==='preflightTask')return {canEnqueue:true,issues:[],warnings:[{message:'UI FIXTURE：未执行权重'}]};
  if(c.action==='saveTaskDraft'){const old=f.__mvDrafts[c.request.bundleId];if((old?.revision||0)!==c.expectedRevision)throw Error('Draft conflict');const d={bundleId:c.request.bundleId,revision:(old?.revision||0)+1,request:JSON.parse(JSON.stringify(c.request))};d.request.allowUnmeasured=false;f.__mvDrafts[d.bundleId]=d;f.taskDrafts=Object.values(f.__mvDrafts).map(d=>({bundleId:d.bundleId,type:d.request.type,revision:d.revision,savedAt:Date.now(),inputSummary:'Four-view program fixture'}));return d;}
  if(c.action==='inspectTaskDraft')return f.__mvDrafts[c.id];
  if(c.action==='submitTask'){const j={id:'mv_job_fixture',state:'queued',request:c.request,createdAt:Date.now(),artifacts:[]};f.jobs=[j];return j;}
  return {};
 };window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}){
 const originalSource=await page.locator('#catalogueSource').inputValue();
 const original=await page.evaluate(()=>{window.__mvPrevious=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
 const commands=action=>page.evaluate(a=>window.__commands.filter(c=>c.action===a),action),id=bundles[0].id;
 try{
  await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{bundles,legacy,roles});
  const downloads=(await commands('downloadBundle')).length,submits=(await commands('submitTask')).length;
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(ns=>ns.map(n=>n.dataset.model)),['m08','m06','m01']);checked('Multiview preserves all original recommended peers');
  await page.locator('[data-filter="all"]').click();await page.selectOption('#catalogueSource','registered');await page.locator('[data-task="3d"]').click();
  assert.equal(await page.locator('[data-bundle]').count(),4);assert.equal(await page.locator('.acquisition-import').count(),4);checked('Four MV precision/output choices show explicit import-only tags');
  await overflow(page,'MV model cards');await capture('01-multiview-models.png','UI FIXTURE · Four optional MV choices, no model installed');
  await page.locator('[data-bundle="'+id+'"] [data-action="bundleInfo"]').first().click();
  assert((await page.locator('#modal').innerText()).includes('尚无已核实的权重下载来源'));assert.equal(await page.locator('#modal [data-action="downloadBundle"]:enabled').count(),0);checked('Unavailable download sources cannot launch a catalogue transfer');
  assert((await page.locator('#modal').innerText()).includes('导入'));checked('Component management keeps the verified local import route');
  await capture('02-import-plan.png','UI FIXTURE · Pinned component identities and honest acquisition status');
  await page.keyboard.press('Escape');await page.evaluate(()=>{window.__fixture.bundles.forEach(b=>{b.installed=true;b.plan.reusableBytes=b.plan.totalBytes;b.plan.remainingBytes=0;b.plan.components.forEach(c=>c.reusable=true);});window.LMA.receive(window.__fixture);});
  await page.locator('[data-filter="local"]').click();await page.locator('[data-bundle="'+id+'"] [data-action="bundleUse"]').click();
  assert.equal(await page.locator('[data-mesh-role]').count(),4);checked('MV editor requires four individually labelled reference roles');
  for(const role of roles)assert.equal(await page.locator('[name="'+role+'"] option[value="mv_jpeg"]').count(),0);checked('Four-view choices exclude JPEG artifacts');
  await page.locator('[data-action="meshSubmit"]').click();assert.equal((await commands('submitTask')).length,submits);checked('Missing MV views create no queue request');
  for(let i=0;i<4;i++)await page.locator('[name="'+roles[i]+'"]').selectOption('mv_view_'+i);
  await page.locator('[name="maxTokens"]').fill('999999');await page.locator('[name="maxTokens"]').blur();assert.equal(await page.locator('[name="maxTokens"]').inputValue(),'49152');
  await page.locator('[name="resolution"]').fill('512');await page.locator('[name="resolution"]').blur();assert.equal(await page.locator('[name="resolution"]').inputValue(),'1024');checked('Signed MV token and fixed-resolution limits clamp editable input');
  const cameras=JSON.stringify({frames:Array.from({length:4},()=>({camera_angle_x:.34906585,transform_matrix:[[1,0,0,0],[0,1,0,0],[0,0,1,3],[0,0,0,1]]}))});
  await page.locator('textarea[name="cameraPoses"]').fill(cameras);await page.locator('[data-action="meshSaveSettings"]').click();
  await page.waitForFunction(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.maxTokens===49152,id);
  assert.equal(await page.evaluate(()=>window.__fixture.bundles[1].config.values.maxTokens),8192);checked('Camera parameters and numeric settings remain independent per model');
  await page.locator('[data-action="meshPreflight"]').click();await page.waitForFunction(()=>document.getElementById('meshHint').innerText.includes('检查通过'));checked('Four-view preflight validates without creating or executing a task');
  await page.locator('[data-action="meshDraft"]').click();await page.waitForFunction(()=>window.__fixture.taskDrafts.length===1);checked('MV draft stores the four references and camera string');
  await page.locator('#meshTaskForm h3').evaluate(el=>el.scrollIntoView({block:'start'}));
  await overflow(page,'MV editor');await capture('03-four-view-form.png','UI FIXTURE · Four RGBA views and model-specific parameters; cameras further below');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="restoreTaskDraft"][data-id="'+id+'"]').click();
  assert.equal(await page.locator('textarea[name="cameraPoses"]').inputValue(),cameras);for(let i=0;i<4;i++)assert.equal(await page.locator('[name="'+roles[i]+'"]').inputValue(),'mv_view_'+i);
  assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false);checked('Restored MV draft retains inputs and requires fresh execution consent');
  await page.locator('[name="allowUnmeasured"]').check();await page.locator('[data-action="meshSubmit"]').evaluate(b=>{b.click();b.click();});await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
  const request=(await commands('submitTask')).at(-1).request;assert.equal((await commands('submitTask')).length,submits+1);assert.deepEqual(request.input.artifacts,roles.map((role,i)=>({role,artifactId:'mv_view_'+i})));assert.equal(request.parameters.cameraPoses,cameras);checked('One MV queue submission preserves exact role and camera identity');
  await overflow(page,'MV queue');await capture('04-multiview-queue.png','UI FIXTURE · Four-view task in shared queue, not trained output');
  await page.evaluate(()=>{Object.assign(window.__fixture.device,{backgroundRestricted:true,powerSaveMode:true,deviceIdle:true,notificationsEnabled:false});window.LMA.receive(window.__fixture);});
  await page.locator('.nav-item[data-tab="server"]').click();const status=await page.locator('#batteryDescription').innerText();for(const s of ['系统限制后台活动','省电模式已开启','设备处于待机状态','服务通知未开启'])assert(status.includes(s));checked('Background diagnostics display observed Android restrictions without an endurance claim');
  await page.locator('#batteryDescription').evaluate(el=>el.scrollIntoView({block:'center'}));
  await overflow(page,'Background diagnostics');await capture('05-background-observations.png','UI FIXTURE · Simulated power states; no physical phone test');
  assert.equal((await commands('downloadBundle')).length,downloads);checked('The complete MV UI flow downloads zero weights and auxiliary components');
 }finally{
  await page.keyboard.press('Escape');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__mvPrevious;delete window.__mvPrevious;window.LMA.receive(f);},original);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  await page.locator('#catalogueSource').evaluate((element,value)=>{element.value=value;element.dispatchEvent(new Event('change',{bubbles:true}));},originalSource);
 }
};
