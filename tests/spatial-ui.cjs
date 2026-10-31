/* Production pages with labelled bridge fixtures. No trained output or phone. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const templates=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.filter(t=>t.definition.engine==='spatial_ort');
const legacy=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models;
function install({templates,legacy}){
 const f=window.__fixture;f.models=legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));
 f.bundles=templates.map((t,i)=>{
  const manifest={...t.definition,id:'spatial_ui_'+i,modelId:'spatial_ui_'+i,recipeId:t.id,name:t.name+' · UI FIXTURE',evidence:{acquisition:'import_only'},components:t.requirements.filter(r=>r.required).map(r=>({role:r.role,path:r.matchFiles[0],format:r.formats[0],bytes:100,sha256:'0'.repeat(64),url:''}))};
  const schema=JSON.parse(JSON.stringify(manifest.parameters));schema.fields.tokens.maximum=512;schema.fields.tokens.default=512;
  const ultra=manifest.capabilities.includes('coarse_mesh_conditioning'),roles={reference_image:{label:'已去背景 / 白底物体 PNG',required:true,mimes:['image/png'],maxBytes:16777216,maxPixels:4194304}};
  if(ultra)roles.coarse_mesh={label:'待精修粗网格（自包含静态 GLB）',required:true,mimes:['model/gltf-binary'],maxBytes:268435456};
  return {id:manifest.id,manifest,installed:false,parameterSchema:schema,config:{values:Object.fromEntries(Object.entries(schema.fields).map(([k,v])=>[k,v.default]))},
   inputSchemas:{'mesh.generate':{fixedPrompt:'Generate local 3D geometry from the explicitly selected inputs.',promptHelp:ultra?'选择参考 PNG 和粗 GLB；仅精修几何，不自动制作初始网格。表面点按一半面积、一半锐边长度加权采样；粗网格须含可用锐边。':'选择已去背景或白底 PNG；生成无贴图几何。此配方不包含 Hunyuan3D Paint。',roles}},
   plan:{totalBytes:500,remainingBytes:500,reusableBytes:0,components:manifest.components.map(c=>({...c,reusable:false,downloadable:false}))}};
 });
 f.localEngines=[{engine:'spatial_ort',available:true,deviceValidated:false}];f.jobs=[];f.taskDrafts=[];f.__spatialDrafts={};
 f.artifacts=[{id:'spatial_png',available:true,bytes:100,origin:{kind:'imported',name:'Object · UI FIXTURE.png'},metadata:{mime:'image/png',width:256,height:256}},
  {id:'spatial_glb',available:true,bytes:100,origin:{kind:'imported',name:'Coarse · UI FIXTURE.glb'},metadata:{mime:'model/gltf-binary',vertices:4,triangles:4}},
  {id:'spatial_jpeg',available:true,bytes:100,metadata:{mime:'image/jpeg',width:256,height:256}}];
 window.__handleFoundation=c=>{
  if(c.action==='saveBundleSettings'){const b=f.bundles.find(b=>b.id===c.id);b.config.values=c.settings;return b.config;}
  if(c.action==='preflightTask')return {canEnqueue:true,issues:[],warnings:[{message:'UI FIXTURE：未运行完整权重，资源与效果未测'}]};
  if(c.action==='saveTaskDraft'){const old=f.__spatialDrafts[c.request.bundleId];if((old?.revision||0)!==c.expectedRevision)throw Error('Draft conflict');const d={bundleId:c.request.bundleId,revision:(old?.revision||0)+1,request:JSON.parse(JSON.stringify(c.request))};d.request.allowUnmeasured=false;f.__spatialDrafts[d.bundleId]=d;f.taskDrafts=Object.values(f.__spatialDrafts).map(d=>({bundleId:d.bundleId,type:d.request.type,revision:d.revision,savedAt:Date.now(),inputSummary:'Spatial program fixture'}));return d;}
  if(c.action==='inspectTaskDraft')return f.__spatialDrafts[c.id];
  if(c.action==='submitTask'){const j={id:'spatial_job_fixture',state:'queued',request:c.request,createdAt:Date.now(),artifacts:[]};f.jobs=[j];return j;}return {};
 };window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}){
 const originalSource=await page.locator('#catalogueSource').inputValue();
 const original=await page.evaluate(()=>{window.__spatialPrevious=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
 const commands=action=>page.evaluate(a=>window.__commands.filter(c=>c.action===a),action);
 try{
  assert.equal(templates.length,2);await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{templates,legacy});
  const downloads=(await commands('downloadBundle')).length,submits=(await commands('submitTask')).length;
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(ns=>ns.map(n=>n.dataset.model)),['m08','m06','m01']);checked('Spatial preserves Recommended peers and order');
  await page.locator('[data-filter="all"]').click();await page.selectOption('#catalogueSource','registered');await page.locator('[data-task="3d"]').click();
  assert.equal(await page.locator('[data-bundle]').count(),2);assert.equal(await page.locator('.acquisition-import').count(),2);checked('Two equal spatial peers disclose matched-export import acquisition');
  await overflow(page,'Spatial cards');await capture('01-spatial-models.png','UI FIXTURE · Optional Hunyuan shape and UltraShape refinement recipes');
  await page.locator('[data-bundle="spatial_ui_0"] [data-action="bundleInfo"]').first().click();assert.equal(await page.locator('#modal [data-action="downloadBundle"]:enabled').count(),0);checked('Unverified matched ONNX downloads are not fabricated');
  await capture('02-spatial-assets.png','UI FIXTURE · Five required selected components, no bundled weights');
  await page.keyboard.press('Escape');await page.evaluate(()=>{window.__fixture.bundles.forEach(b=>{b.installed=true;b.plan.reusableBytes=b.plan.totalBytes;b.plan.remainingBytes=0;b.plan.components.forEach(c=>c.reusable=true);});window.LMA.receive(window.__fixture);});
  await page.locator('[data-filter="local"]').click();assert.equal(await page.locator('[data-bundle]').count(),2);checked('Local manages selected Spatial assets without changing recommendations');
  await page.locator('[data-bundle="spatial_ui_0"] [data-action="bundleUse"]').click();assert.equal(await page.locator('[data-mesh-role]').count(),1);assert.equal(await page.locator('[name="meshScale"]').count(),0);assert((await page.locator('#meshTaskForm').innerText()).includes('不包含 Hunyuan3D Paint'));checked('Hunyuan exposes one PNG and geometry-only capability-specific controls');
  assert.equal(await page.locator('[name="reference"] option[value="spatial_jpeg"]').count(),0);assert.equal(await page.locator('[name="reference"] option[value="spatial_glb"]').count(),0);checked('Image role filters out incompatible JPEG and GLB');
  await page.locator('[name="tokens"]').fill('99999');await page.locator('[name="tokens"]').blur();assert.equal(await page.locator('[name="tokens"]').inputValue(),'512');checked('Editable latent limit clamps to the selected installed export');
  await page.locator('[name="steps"]').fill('999');await page.locator('[name="steps"]').blur();assert.equal(await page.locator('[name="steps"]').inputValue(),'100');
  await page.locator('[data-action="meshSaveSettings"]').click();await page.waitForFunction(()=>window.__fixture.bundles[0].config.values.steps===100);assert.equal(await page.evaluate(()=>window.__fixture.bundles[1].config.values.steps),30);checked('Spatial settings remain independent per model');
  await page.locator('#meshTaskForm h3').evaluate(el=>el.scrollIntoView({block:'start'}));await overflow(page,'Hunyuan form');await capture('03-hunyuan-settings.png','UI FIXTURE · Per-model bounds; no Hunyuan Paint or phone performance claim');
  await page.keyboard.press('Escape');await page.locator('[data-bundle="spatial_ui_1"] [data-action="bundleUse"]').click();assert.equal(await page.locator('[data-mesh-role]').count(),2);assert.equal(await page.locator('[name="meshScale"]').count(),1);assert((await page.locator('#meshTaskForm').innerText()).includes('不自动制作初始网格'));checked('UltraShape requires both PNG and a coarse mesh, with refinement settings');
  assert.equal(await page.locator('[name="coarse_mesh"] option[value="spatial_png"]').count(),0);assert.equal(await page.locator('[name="coarse_mesh"] option[value="spatial_glb"]').count(),1);checked('Coarse-mesh role admits only imported GLB artifacts');
  await page.locator('[name="reference"]').selectOption('spatial_png');await page.locator('[data-action="meshSubmit"]').click();assert.equal((await commands('submitTask')).length,submits);checked('A missing coarse mesh creates no queue job');
  await page.locator('[name="coarse_mesh"]').selectOption('spatial_glb');await page.locator('[data-action="meshPreflight"]').click();await page.waitForFunction(()=>document.getElementById('meshHint').innerText.includes('检查通过'));assert.equal((await commands('submitTask')).length,submits);checked('Preflight inspects inputs without inference or submission');
  await page.locator('[data-action="meshDraft"]').click();await page.waitForFunction(()=>window.__fixture.taskDrafts.length===1);checked('Refinement draft stores both explicit input roles');
  await page.locator('#meshTaskForm h3').evaluate(el=>el.scrollIntoView({block:'start'}));await overflow(page,'UltraShape form');await capture('04-ultrashape-inputs.png','UI FIXTURE · Reference PNG plus explicitly selected static coarse GLB');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="restoreTaskDraft"][data-id="spatial_ui_1"]').click();assert.equal(await page.locator('[name="reference"]').inputValue(),'spatial_png');assert.equal(await page.locator('[name="coarse_mesh"]').inputValue(),'spatial_glb');assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false);checked('Restored refinement draft preserves inputs and renews explicit unmeasured choice');
  await page.locator('[name="allowUnmeasured"]').check();await page.locator('[data-action="meshSubmit"]').evaluate(b=>{b.click();b.click();});await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
  assert.equal((await commands('submitTask')).length,submits+1);const request=(await commands('submitTask')).at(-1).request;assert.deepEqual(request.input.artifacts,[{role:'reference_image',artifactId:'spatial_png'},{role:'coarse_mesh',artifactId:'spatial_glb'}]);assert.equal(request.type,'mesh.generate');checked('One idempotent queue action preserves the exact image and coarse mesh');
  await overflow(page,'Spatial queue');await capture('05-spatial-queue.png','UI FIXTURE · Shared local queue; no generated result or trained model depicted');
  assert.equal((await commands('downloadBundle')).length,downloads);checked('Spatial UI flow downloads zero model assets');
 }finally{
  await page.keyboard.press('Escape');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__spatialPrevious;delete window.__spatialPrevious;window.LMA.receive(f);},original);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();await page.locator('#catalogueSource').evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));},originalSource);
 }
};
