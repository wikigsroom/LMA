/* Current production forms with an explicit bridge fixture; no model or phone. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const all=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates;
const templates=all.filter(t=>['ultratex_flux1','ultratex_flux2'].includes(t.definition.pipeline));
const legacy=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models;
function install({templates,legacy}){
 const f=window.__fixture;f.models=legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));
 f.bundles=templates.map((template,i)=>{const manifest={...template.definition,id:'ultratex_ui_'+i,modelId:'ultratex_ui_'+i,recipeId:template.id,name:template.name+' '+(i+1)+' · UI FIXTURE',evidence:{acquisition:'import_only'},components:template.requirements.filter(r=>r.required).map(r=>({role:r.role,path:r.matchFiles[0],format:r.formats[0],bytes:100,sha256:'0'.repeat(64),url:''}))};
  const schema=JSON.parse(JSON.stringify(manifest.parameters));return {id:manifest.id,manifest,installed:false,parameterSchema:schema,config:{values:Object.fromEntries(Object.entries(schema.fields).map(([k,v])=>[k,v.default]))},
   inputSchemas:{'mesh.generate':{negativePrompt:false,promptHelp:'输入材质描述，选择参考 PNG 与待贴图 GLB；全部在手机本地处理。完整模型和手机效果未测。',roles:{reference_image:{label:'贴图参考 PNG',required:true,mimes:['image/png'],maxBytes:16777216,maxPixels:4194304},source_mesh:{label:'待贴图静态 GLB',required:true,mimes:['model/gltf-binary'],maxBytes:268435456}}}},
   plan:{totalBytes:700,remainingBytes:700,reusableBytes:0,components:manifest.components.map(c=>({...c,reusable:false,downloadable:false}))}};});
 f.localEngines=[{engine:'spatial_ort',available:true,deviceValidated:false}];f.jobs=[];f.taskDrafts=[];f.__ultratexDrafts={};
 f.artifacts=[{id:'ultratex_png',available:true,bytes:100,origin:{kind:'imported',name:'Reference · UI FIXTURE.png'},metadata:{mime:'image/png',width:256,height:256}},
  {id:'ultratex_glb',available:true,bytes:100,origin:{kind:'imported',name:'Mesh · UI FIXTURE.glb'},metadata:{mime:'model/gltf-binary',vertices:4,triangles:4}},
  {id:'ultratex_wav',available:true,bytes:100,metadata:{mime:'audio/wav'}}];
 window.__handleFoundation=c=>{
  if(c.action==='inspectArtifact')return f.artifacts.find(a=>a.id===c.id);
  if(c.action==='saveBundleSettings'){const b=f.bundles.find(b=>b.id===c.id);b.config.values=c.settings;return b.config;}
  if(c.action==='preflightTask')return {canEnqueue:true,issues:[],warnings:[{message:'UI FIXTURE：完整训练模型与手机资源未测'}]};
  if(c.action==='saveTaskDraft'){const old=f.__ultratexDrafts[c.request.bundleId];if((old?.revision||0)!==c.expectedRevision)throw Error('Draft conflict');const d={bundleId:c.request.bundleId,revision:(old?.revision||0)+1,request:JSON.parse(JSON.stringify(c.request))};d.request.allowUnmeasured=false;f.__ultratexDrafts[d.bundleId]=d;f.taskDrafts=Object.values(f.__ultratexDrafts).map(d=>({bundleId:d.bundleId,type:d.request.type,revision:d.revision,savedAt:Date.now(),inputSummary:'UltraTex program fixture'}));return d;}
  if(c.action==='inspectTaskDraft')return f.__ultratexDrafts[c.id];
  if(c.action==='submitTask'){const j={id:'ultratex_job_fixture',state:'queued',request:c.request,createdAt:Date.now(),artifacts:[]};f.jobs=[j];return j;}return {};
 };window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}){
 const originalSource=await page.locator('#catalogueSource').inputValue();
 const original=await page.evaluate(()=>{window.__ultratexPrevious=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
 const commands=action=>page.evaluate(a=>window.__commands.filter(c=>c.action===a),action);
 try{
  assert.equal(templates.length,2);assert.deepEqual(templates.map(t=>t.requirements.filter(r=>r.required).length),[10,8]);checked('Both UltraTex families require their distinct complete asset sets');
  const f5=all.find(t=>t.id==='f5_v1_official_frontend_cpu_v1');assert(f5.requirements.some(r=>r.role==='frontend'&&r.required&&r.formats.includes('json')));checked('UltraTex addition preserves explicit optional F5 frontend selection');
  await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{templates,legacy});
  const downloads=(await commands('downloadBundle')).length,submits=(await commands('submitTask')).length;
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(ns=>ns.map(n=>n.dataset.model)),['m08','m06','m01']);checked('UltraTex peers preserve the original recommendations');
  await page.locator('[data-filter="all"]').click();await page.selectOption('#catalogueSource','registered');await page.locator('[data-task="3d"]').click();
  assert.equal(await page.locator('[data-bundle]').count(),2);assert.equal(await page.locator('.acquisition-import').count(),2);checked('UltraTex versions are equal peers and disclose selected import acquisition');
  await overflow(page,'UltraTex cards');await capture('01-ultratex-models.png','UI FIXTURE · User-selected local ultratex recipes; no weights installed');
  await page.locator('[data-bundle="ultratex_ui_0"] [data-action="bundleInfo"]').first().click();assert.equal(await page.locator('#modal [data-action="downloadBundle"]:enabled').count(),0);checked('No fabricated complete UltraTex download or implicit model acquisition');
  await capture('02-ultratex-components.png','UI FIXTURE · Matching encoders, tokenizers and dual PBR networks chosen by the user');await page.keyboard.press('Escape');
  await page.evaluate(()=>{window.__fixture.bundles.forEach(b=>{b.installed=true;b.plan.reusableBytes=b.plan.totalBytes;b.plan.remainingBytes=0;b.plan.components.forEach(c=>c.reusable=true);});window.LMA.receive(window.__fixture);});
  await page.locator('[data-filter="local"]').click();assert.equal(await page.locator('[data-bundle]').count(),2);checked('Local manages each ultratex model independently');
  await page.locator('[data-bundle="ultratex_ui_0"] [data-action="bundleUse"]').click();assert.equal(await page.locator('[data-mesh-role]').count(),2);assert.equal(await page.locator('[name="negativePrompt"]').count(),0);assert.equal(await page.locator('[name="dropBackground"]').count(),0);assert.equal(await page.locator('[name="prompt"]').count(),1);await page.locator('[name="prompt"]').fill('Blue ceramic with subtle roughness · UI FIXTURE');checked('UltraTex form requires PNG and GLB and exposes no unsupported negative prompt');
  assert.equal(await page.locator('[name="reference"] option[value="ultratex_glb"]').count(),0);assert.equal(await page.locator('[name="source_mesh"] option[value="ultratex_png"]').count(),0);checked('Source mesh and reference image remain typed artifact roles');
  await page.locator('[name="steps"]').fill('9999');await page.locator('[name="steps"]').blur();assert.equal(await page.locator('[name="steps"]').inputValue(),'100');
  await page.locator('[name="atlas"]').fill('99999');await page.locator('[name="atlas"]').blur();assert.equal(await page.locator('[name="atlas"]').inputValue(),'4096');checked('Editable ultratex settings return excessive values to the model limits');
  await page.locator('[data-action="meshSaveSettings"]').click();await page.waitForFunction(()=>window.__fixture.bundles[0].config.values.steps===100);assert.equal(await page.evaluate(()=>window.__fixture.bundles[1].config.values.steps),25);checked('UltraTex parameters follow the model and do not overwrite peers');
  await page.locator('#meshTaskForm h3').evaluate(e=>e.scrollIntoView({block:'start'}));await overflow(page,'UltraTex settings');await capture('03-ultratex-settings.png','UI FIXTURE · Editable per-model steps, UV atlas and local enhancement');
  await page.locator('[name="reference"]').selectOption('ultratex_png');await page.locator('[data-action="meshSubmit"]').click();assert.equal((await commands('submitTask')).length,submits);checked('Missing source mesh creates no queue job');
  await page.locator('[name="source_mesh"]').selectOption('ultratex_glb');await page.locator('[data-action="meshPreflight"]').click();await page.waitForFunction(()=>document.getElementById('meshHint').innerText.includes('检查通过'));assert.equal((await commands('submitTask')).length,submits);checked('UltraTex preflight validates without inference');
  await page.locator('[data-action="meshDraft"]').click();await page.waitForFunction(()=>window.__fixture.taskDrafts.length===1);checked('UltraTex draft retains both explicitly selected artifacts');
  await page.locator('#meshTaskForm h3').evaluate(e=>e.scrollIntoView({block:'start'}));await capture('04-ultratex-inputs.png','UI FIXTURE · Selected PNG and existing GLB; no model-generated result');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="tasks"]').click();await page.locator('[data-action="restoreTaskDraft"][data-id="ultratex_ui_0"]').click();assert.equal(await page.locator('[name="reference"]').inputValue(),'ultratex_png');assert.equal(await page.locator('[name="source_mesh"]').inputValue(),'ultratex_glb');assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false);assert.equal(await page.locator('[name="prompt"]').inputValue(),'Blue ceramic with subtle roughness · UI FIXTURE');checked('Restored ultratex draft preserves inputs and resets the resource confirmation');
  await page.locator('[name="allowUnmeasured"]').check();await page.locator('[data-action="meshSubmit"]').evaluate(b=>{b.click();b.click();});await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);
  assert.equal((await commands('submitTask')).length,submits+1);const request=(await commands('submitTask')).at(-1).request;assert.deepEqual(request.input.artifacts,[{role:'reference_image',artifactId:'ultratex_png'},{role:'source_mesh',artifactId:'ultratex_glb'}]);assert.equal(request.input.prompt,'Blue ceramic with subtle roughness · UI FIXTURE');checked('UltraTex submission is idempotent and carries the selected inputs and material prompt');
  await overflow(page,'UltraTex queue');await capture('05-ultratex-queue.png','UI FIXTURE · Shared task queue; no phone or trained-model inference');assert.equal((await commands('downloadBundle')).length,downloads);checked('UltraTex browsing and task editing download zero model assets');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();
  await page.locator('[data-bundle="ultratex_ui_1"] [data-action="bundleUse"]').click();
  assert.equal(await page.locator('[name="dropBackground"]').isChecked(),false);assert.equal(await page.locator('[name="steps"]').inputValue(),'25');checked('FLUX2 keeps its own optional background mask and independent defaults');
  await page.locator('[name="reference"]').selectOption('ultratex_png');await page.locator('[name="source_mesh"]').selectOption('ultratex_glb');
  const beforePreflight=(await commands('preflightTask')).length;await page.locator('[data-action="meshPreflight"]').click();assert.equal((await commands('preflightTask')).length,beforePreflight);checked('An empty material description is rejected before task preflight');
  await page.locator('[name="prompt"]').fill('磨砂金属与蓝色陶瓷 · UI FIXTURE');await page.locator('[name="dropBackground"]').check();await page.locator('[data-action="meshSaveSettings"]').click();
  await page.waitForFunction(()=>window.__fixture.bundles[1].config.values.dropBackground===true);assert.equal(await page.evaluate(()=>window.__fixture.bundles[0].config.values.steps),100);checked('FLUX2 mask settings do not overwrite the FLUX1 peer');
  await page.locator('#meshTaskForm h3').evaluate(e=>e.scrollIntoView({block:'start'}));await capture('06-ultratex-flux2.png','UI FIXTURE · FLUX2 has distinct text/VAE assets and optional foreground compaction');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="tasks"]').click();
  await require('./glb-preview-ui.cjs').checks(page,checked,async(file,caption)=>capture(file.replace('06-material-preview','07-ultratex-preview'),caption));
 }finally{
  await page.keyboard.press('Escape');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__ultratexPrevious;delete window.__ultratexPrevious;window.LMA.receive(f);},original);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();await page.locator('#catalogueSource').evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));},originalSource);
 }
};
