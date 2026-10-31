/* Production forms with explicit bridge fixtures. No trained output or phone. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const pipelines=['partcrafter','triposg_points','uniforge3d','sam3d_objects','mv_sam3d_da3','supratex','isnet_dis','vlm_parts','hunyuan3d_21_paint'];
const templates=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates.filter(t=>pipelines.includes(t.definition.pipeline));
const legacy=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/models.json'),'utf8')).models;
function install({templates,legacy}){
 const f=window.__fixture;f.models=legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));
 const png=label=>({label,required:true,mimes:['image/png'],maxBytes:16777216}),data=label=>({label,required:true,mimes:['application/vnd.lma.data+json'],maxBytes:8388608});
 const mesh={label:'已有静态 GLB',required:true,mimes:['model/gltf-binary'],maxBytes:268435456};
 f.bundles=templates.map(t=>{
  const p=t.definition.pipeline,type=p==='isnet_dis'?'image.generate':p==='vlm_parts'?'text.generate':'mesh.generate';
  const manifest={...t.definition,id:'adapt_'+p,modelId:'adapt_'+p,recipeId:t.id,name:t.name+' · UI FIXTURE',evidence:{acquisition:'import_only'},components:t.requirements.filter(r=>r.required).map(r=>({role:r.role,path:r.matchFiles?.[0]||r.role+'.gguf',format:r.formats[0],bytes:100,sha256:'0'.repeat(64),url:''}))};
  const schema=JSON.parse(JSON.stringify(manifest.parameters));let roles={reference_image:png('参考 PNG')};
  if(['uniforge3d','mv_sam3d_da3'].includes(p))roles=Object.fromEntries(['front','right','back','left'].map((v,i)=>['reference_'+v,png(['正面 RGBA','右面 RGBA','背面 RGBA','左面 RGBA'][i])]));
  if(p==='triposg_points')roles={point_cloud:data('XYZ＋单位法线点云 JSON'),reference_image:{...png('可选材质参考 PNG'),required:false}};
  if(['supratex','hunyuan3d_21_paint'].includes(p))roles={reference_image:png('已对齐的 RGBA PNG'),source_mesh:mesh};
  if(p==='supratex')roles.camera=data('匹配网格与参考图的相机 JSON');
  if(p==='partcrafter')for(const [key,label,pipeline] of [['foregroundModel','自动前景模型','isnet_dis'],['partModel','自动部件识别模型','vlm_parts'],['materialModel','几何完成后的材质模型','hunyuan3d_21_paint']])schema.fields[key]={type:'enum',label,default:'none',values:['none','adapt_'+pipeline],optionLabels:{none:'不使用',['adapt_'+pipeline]:pipeline+' · UI FIXTURE'}};
  const input={negativePrompt:false,roles,promptHelp:p==='vlm_parts'?'手机本地视觉模型识别部件并输出严格 JSON；用户单独选择模型和视觉投影。':'选择匹配的本地素材；模型和手机效果未测，不会自动下载模型。',fixedPrompt:p==='triposg_points'?'Reconstruct local 3D geometry from the selected point cloud.':'Prepare the selected local image.'};
  return {id:manifest.id,manifest,installed:true,parameterSchema:schema,config:{values:Object.fromEntries(Object.entries(schema.fields).map(([k,v])=>[k,v.default]))},inputSchemas:{[type]:input},plan:{totalBytes:700,reusableBytes:700,remainingBytes:0,components:manifest.components.map(c=>({...c,reusable:true,downloadable:false}))}};
 });
 f.localEngines=['spatial_ort','rf_shape_ort','vision_cpu'].map(engine=>({engine,available:true,deviceValidated:false}));f.jobs=[];f.taskDrafts=[];
 f.artifacts=[...['front','right','back','left'].map(v=>({id:'adapt_'+v,available:true,bytes:100,origin:{kind:'imported',name:v+' · UI FIXTURE.png'},metadata:{mime:'image/png',width:1024,height:1024}})),
  {id:'adapt_mesh',available:true,bytes:100,metadata:{mime:'model/gltf-binary',vertices:4,triangles:4}},
  {id:'adapt_camera',available:true,bytes:100,metadata:{mime:'application/vnd.lma.data+json',schema:'lma.camera/1'}},
  {id:'adapt_points',available:true,bytes:100,metadata:{mime:'application/vnd.lma.data+json',schema:'lma.pointcloud/1'}}];
 window.__handleFoundation=c=>{
  if(c.action==='saveBundleSettings'){const b=f.bundles.find(b=>b.id===c.id);b.config.values=c.settings;return b.config;}
  if(c.action==='inspectArtifact')return f.artifacts.find(a=>a.id===c.id);
  if(c.action==='preflightTask')return {canEnqueue:true,issues:[],warnings:[{message:'UI FIXTURE：未运行完整模型，手机资源未测'}]};
  if(c.action==='submitTask'){const j={id:'adapt_job_'+f.jobs.length,state:'queued',request:c.request,createdAt:Date.now(),artifacts:[]};f.jobs.push(j);return j;}return {};
 };window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}){
 const originalSource=await page.locator('#catalogueSource').inputValue();
 const original=await page.evaluate(()=>{window.__adaptPrevious=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
 const commands=action=>page.evaluate(a=>window.__commands.filter(c=>c.action===a),action);
 const open=async p=>{await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-bundle="adapt_'+p+'"] [data-action="bundleUse"]').click();};
 const shot=async(file,caption)=>{await page.locator('#meshTaskForm h3').evaluate(e=>e.scrollIntoView({block:'start'}));await overflow(page,caption);await capture(file,'UI FIXTURE · '+caption);};
 try{
  assert.equal(templates.length,9);await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{templates,legacy});
  const downloads=(await commands('downloadBundle')).length,submits=(await commands('submitTask')).length;
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="recommended"]').click();await page.locator('[data-task="any"]').click();
  assert.deepEqual(await page.locator('.model-card').evaluateAll(ns=>ns.map(n=>n.dataset.model)),['m08','m06','m01']);checked('New adapters retain the exact three recommendations');
  await page.locator('[data-filter="local"]').click();assert.equal(await page.locator('[data-bundle]').count(),9);checked('Vision and geometry models are equal peers in Local');
  await capture('01-local-adapters.png','UI FIXTURE · User-installed equal model peers; no weights bundled');
  await open('partcrafter');for(const key of ['foregroundModel','partModel','materialModel'])assert.equal(await page.locator('select[name="'+key+'"]').inputValue(),'none');checked('All local preparation and material stages start as an explicit opt-in');
  await page.locator('[name="foregroundModel"]').selectOption('adapt_isnet_dis');await page.locator('[name="partModel"]').selectOption('adapt_vlm_parts');await page.locator('[name="materialModel"]').selectOption('adapt_hunyuan3d_21_paint');
  await page.locator('[data-action="meshSaveSettings"]').click();await page.waitForFunction(()=>window.__fixture.bundles.find(b=>b.id==='adapt_partcrafter').config.values.partModel==='adapt_vlm_parts');checked('Named model selectors save string IDs without numeric coercion');
  await page.locator('[name="foregroundModel"]').evaluate(e=>e.closest('label').scrollIntoView({block:'start'}));await overflow(page,'Local preparation selectors');await capture('02-local-stages.png','UI FIXTURE · Optional local foreground, part identification and material models');
  await open('triposg_points');assert.equal(await page.locator('[data-mesh-role="point_cloud"] option[value="adapt_mesh"]').count(),0);checked('Point-cloud role excludes GLB and PNG inputs');
  await page.locator('[name="posterior"]').selectOption('sample');await page.locator('[name="extraction"]').selectOption('publisher_flash');await page.locator('[name="octreeDepth"]').fill('5');await page.locator('[name="denseDepth"]').fill('8');await page.locator('[name="denseDepth"]').blur();assert.equal(await page.locator('[name="denseDepth"]').inputValue(),'5');checked('Original extraction choices and dependent depth bounds remain editable');
  await page.locator('[name="point_cloud"]').selectOption('adapt_points');await page.locator('[data-action="meshPreflight"]').click();await page.waitForFunction(()=>document.getElementById('meshHint').innerText.includes('检查通过'));assert.equal((await commands('submitTask')).length,submits);checked('Point-cloud preflight submits no model work');await shot('03-pointcloud.png','Typed point-cloud input and original Flash extraction');
  await open('mv_sam3d_da3');assert.equal(await page.locator('[data-mesh-role]').count(),4);for(const side of ['front','right','back','left'])await page.locator('[name="reference_'+side+'"]').selectOption('adapt_'+side);checked('MV-SAM exposes four independently selected view roles');await shot('04-mv-sam.png','Four-view SAM and local DA3 inputs');
  await open('supratex');assert.equal(await page.locator('[data-mesh-role]').count(),3);await page.locator('[name="reference"]').selectOption('adapt_front');await page.locator('[name="source_mesh"]').selectOption('adapt_mesh');await page.locator('[name="camera"]').selectOption('adapt_camera');assert.equal(await page.locator('[name="negativePrompt"]').count(),0);checked('SUPRA requires explicit image, mesh and camera artifacts');await shot('05-supra.png','SUPRA aligned RGBA, mesh and camera inputs');
  await open('isnet_dis');assert.equal(await page.locator('[data-mesh-role]').count(),1);await page.locator('[name="reference"]').selectOption('adapt_front');await page.locator('[name="allowUnmeasured"]').check();await shot('06-foreground.png','Local image foreground adapter');await page.locator('[data-action="meshSubmit"]').click();await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);assert.equal((await commands('submitTask')).at(-1).request.type,'image.generate');checked('Foreground submits the image task type through the shared queue');
  await open('vlm_parts');await page.locator('[name="context"]').fill('512');await page.locator('[name="context"]').blur();await page.locator('[name="maxTokens"]').fill('9999');await page.locator('[name="maxTokens"]').blur();assert.equal(await page.locator('[name="maxTokens"]').inputValue(),'511');checked('Vision output limit follows the editable context bound');
  await page.locator('[name="reference"]').selectOption('adapt_front');await page.locator('[name="allowUnmeasured"]').check();await shot('07-part-recognition.png','Local VLM with matched user-selected projection and context limits');await page.locator('[data-action="meshSubmit"]').click();await page.waitForFunction(()=>document.getElementById('modalBackdrop').hidden);assert.equal((await commands('submitTask')).at(-1).request.type,'text.generate');checked('Part identification submits a text result task rather than a mesh request');
  await open('uniforge3d');assert.equal(await page.locator('[data-mesh-role]').count(),4);checked('UniForge retains its own four-view form');await shot('08-uniforge.png','UniForge joint geometry and material recipe');
  await open('sam3d_objects');assert.equal(await page.locator('[data-mesh-role]').count(),1);checked('Single-image SAM remains independent of multiview SAM');await shot('09-sam.png','Single-image SAM with its own model settings');
  assert.equal((await commands('downloadBundle')).length,downloads);checked('All new UI paths download zero model assets automatically');
 }finally{
  await page.keyboard.press('Escape');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__adaptPrevious;delete window.__adaptPrevious;window.LMA.receive(f);},original);
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();await page.locator('#catalogueSource').evaluate((e,v)=>{e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}));},originalSource);
 }
};
