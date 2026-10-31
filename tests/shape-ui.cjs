/* Production pages, explicitly synthetic models and bridge. No trained output. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const templates=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.filter(t=>t.definition.engine==='rf_shape_ort');
const legacy=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models;
function install({templates,legacy}){
 const f=window.__fixture;f.models=legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));
 f.bundles=templates.map((t,i)=>{const manifest={...t.definition,id:'shape_ui_'+i,modelId:'shape_ui_'+i,recipeId:t.id,name:t.name+' · UI FIXTURE',components:t.requirements.filter(r=>r.required).map(r=>({role:r.role,path:r.matchFiles[0],format:r.formats[0],bytes:100,sha256:'0'.repeat(64),url:''}))};return {
  id:manifest.id,manifest,installed:false,parameterSchema:manifest.parameters,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},
  inputSchemas:{'mesh.generate':{fixedPrompt:'Generate local 3D geometry from the selected image.',promptHelp:'已去背景 / 白底 PNG；本地 RF / SDF 生成，独立部件 GLB，无贴图。',roles:{reference_image:{label:'物体 / 场景 PNG',required:true,mimes:['image/png'],maxBytes:16777216,maxPixels:4194304}}}},
  plan:{totalBytes:500,remainingBytes:500,reusableBytes:0,components:manifest.components.map(c=>({...c,reusable:false,downloadable:false}))}};});
 f.bundles.forEach(b=>b.manifest.evidence={acquisition:'import_only'});
 f.localEngines=[{engine:'rf_shape_ort',available:true,deviceValidated:false}];f.jobs=[];f.taskDrafts=[];f.__shapeDrafts={};
 f.artifacts=[{id:'shape_png',available:true,bytes:100,origin:{kind:'imported',name:'Object · UI FIXTURE.png'},metadata:{mime:'image/png',width:256,height:256}},{id:'shape_jpeg',available:true,bytes:100,metadata:{mime:'image/jpeg',width:256,height:256}}];
 window.__handleFoundation=c=>{
  if(c.action==='saveBundleSettings'){const b=f.bundles.find(b=>b.id===c.id);b.config.values=c.settings;return b.config;}
  if(c.action==='preflightTask')return {canEnqueue:true,issues:[],warnings:[{message:'UI FIXTURE：未执行权重，内存及速度未测'}]};
  if(c.action==='saveTaskDraft'){const old=f.__shapeDrafts[c.request.bundleId];if((old?.revision||0)!==c.expectedRevision)throw Error('Draft conflict');const d={bundleId:c.request.bundleId,revision:(old?.revision||0)+1,request:JSON.parse(JSON.stringify(c.request))};d.request.allowUnmeasured=false;f.__shapeDrafts[d.bundleId]=d;f.taskDrafts=Object.values(f.__shapeDrafts).map(d=>({bundleId:d.bundleId,type:d.request.type,revision:d.revision,savedAt:Date.now(),inputSummary:'Shape program fixture'}));return d;}
  if(c.action==='inspectTaskDraft')return f.__shapeDrafts[c.id];
  if(c.action==='submitTask'){const j={id:'shape_job_fixture',state:'queued',request:c.request,createdAt:Date.now(),artifacts:[]};f.jobs=[j];return j;}return {};
 };window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}){
 const originalSource=await page.locator('#catalogueSource').inputValue();
 const original=await page.evaluate(()=>{window.__shapePrevious=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
 const commands=action=>page.evaluate(a=>window.__commands.filter(c=>c.action===a),action);
 try{
  assert.equal(templates.length,3);await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{templates,legacy});
  const downloads=(await commands('downloadBundle')).length,submits=(await commands('submitTask')).length;
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(ns=>ns.map(n=>n.dataset.model)),['m08','m06','m01']);checked('RF shape keeps the exact recommended peers and order');
  await page.locator('[data-filter="all"]').click();await page.selectOption('#catalogueSource','registered');await page.locator('[data-task="3d"]').click();
  assert.equal(await page.locator('[data-bundle]').count(),3);assert.equal(await page.locator('.acquisition-import').count(),3);checked('Three optional RF recipes expose import-only acquisition and 3D tags');
  await overflow(page,'Shape model cards');await capture('01-shape-recipes.png','UI FIXTURE · Three optional matched-export recipes, no trained models installed');
  await page.locator('[data-bundle="shape_ui_1"] [data-action="bundleInfo"]').first().click();
  assert((await page.locator('#modal').innerText()).includes('尚无已核实的权重下载来源'));assert.equal(await page.locator('#modal [data-action="downloadBundle"]:enabled').count(),0);checked('No fabricated matched ONNX download is offered');
  await capture('02-selected-assets.png','UI FIXTURE · Explicit local component import, no automatic model download');
  await page.keyboard.press('Escape');await page.evaluate(()=>{window.__fixture.bundles.forEach(b=>{b.installed=true;b.plan.reusableBytes=b.plan.totalBytes;b.plan.remainingBytes=0;b.plan.components.forEach(c=>c.reusable=true);});window.LMA.receive(window.__fixture);});
  await page.locator('[data-filter="local"]').click();assert.equal(await page.locator('[data-bundle]').count(),3);checked('Local manages every selected shape model as an equal peer');
  await page.locator('[data-bundle="shape_ui_1"] [data-action="bundleUse"]').click();assert.equal(await page.locator('[data-mesh-role]').count(),1);assert.equal(await page.locator('[name="reference"] option[value="shape_jpeg"]').count(),0);checked('Shape form accepts one PNG and excludes JPEG');
  await page.locator('[data-action="meshSubmit"]').click();assert.equal((await commands('submitTask')).length,submits);checked('Missing shape input creates no task');
  await page.locator('[name="reference"]').selectOption('shape_png');
  for(const [name,typed,want] of [['parts','999','16'],['tokens','999999','4096'],['grid','999','256'],['grid','79','64']]){await page.locator('[name="'+name+'"]').fill(typed);await page.locator('[name="'+name+'"]').blur();assert.equal(await page.locator('[name="'+name+'"]').inputValue(),want);}
  checked('Part count, latent token and aligned grid limits clamp editable inputs');
  await page.locator('[data-action="meshSaveSettings"]').click();await page.waitForFunction(()=>window.__fixture.bundles[1].config.values.parts===16);assert.equal(await page.evaluate(()=>window.__fixture.bundles[2].config.values.parts),3);checked('Shape settings are independent for each model');
  await page.locator('[data-action="meshPreflight"]').click();await page.waitForFunction(()=>document.getElementById('meshHint').innerText.includes('检查通过'));assert.equal((await commands('submitTask')).length,submits);checked('Shape preflight performs no queue submission or inference');
  await page.locator('[data-action="meshDraft"]').click();await page.waitForFunction(()=>window.__fixture.taskDrafts.length===1);checked('Part form persists inputs and parameters in a draft');
  await page.locator('#meshTaskForm h3').evaluate(el=>el.scrollIntoView({block:'start'}));await overflow(page,'Part editor');await capture('03-part-settings.png','UI FIXTURE · Per-model part count, latent tokens and SDF settings');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="restoreTaskDraft"][data-id="shape_ui_1"]').click();
  assert.equal(await page.locator('[name="reference"]').inputValue(),'shape_png');assert.equal(await page.locator('[name="parts"]').inputValue(),'16');assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false);checked('Restored shape draft requires a fresh choice to attempt an unmeasured model');
  await page.locator('[name="allowUnmeasured"]').check();await page.locator('[data-action="meshSubmit"]').evaluate(b=>{b.click();b.click();});await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
  assert.equal((await commands('submitTask')).length,submits+1);const request=(await commands('submitTask')).at(-1).request;assert.equal(request.type,'mesh.generate');assert.equal(request.parameters.parts,16);assert.deepEqual(request.input.artifacts,[{role:'reference_image',artifactId:'shape_png'}]);checked('One shape queue submission preserves selected image and part settings');
  await overflow(page,'Shape queue');await capture('04-shape-queue.png','UI FIXTURE · Shared local queue; no trained-model result depicted');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-bundle="shape_ui_0"] [data-action="bundleUse"]').click();assert.equal(await page.locator('[name="parts"]').inputValue(),'1');checked('TripoSG keeps one-part output independently of PartCrafter settings');
  await page.locator('#meshTaskForm h3').evaluate(el=>el.scrollIntoView({block:'start'}));await capture('05-triposg-form.png','UI FIXTURE · Single-object shape recipe, no automatically selected weights');
  assert.equal((await commands('downloadBundle')).length,downloads);checked('Complete RF UI flow downloads zero model assets');
 }finally{
  await page.keyboard.press('Escape');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__shapePrevious;delete window.__shapePrevious;window.LMA.receive(f);},original);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();await page.locator('#catalogueSource').evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));},originalSource);
 }
};
