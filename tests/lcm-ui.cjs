/* Actual production pages; all transfers/jobs below are explicitly simulated bridge data. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const {installFixture}=require('./foundation-ui.cjs');
const root=path.resolve(__dirname,'..');
function canonical(v){return Array.isArray(v)?'['+v.map(x=>canonical(x)+',').join('')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])+',').join('')+'}':JSON.stringify(v);}
const hash=v=>crypto.createHash('sha256').update(canonical(v)).digest('hex');
function data(){
  const models=JSON.parse(fs.readFileSync(path.join(root,'catalogue/model-bundles.json'),'utf8')).bundles;
  const source=models.find(b=>b.id==='lcm_dreamshaper_source_ra85df6a'),target=models.find(b=>b.id==='lcm_dreamshaper_guidance85_runtime_v1');
  const preparation=JSON.parse(fs.readFileSync(path.join(root,'catalogue/asset-preparations.json'),'utf8')).plans.find(p=>p.id==='lcm_dreamshaper_guidance85_v1');
  const descriptor=JSON.parse(fs.readFileSync(path.join(root,'catalogue/model-assemblies.json'),'utf8')).plans.find(p=>p.bundleId===target.id);
  const outputBytes=preparation.stages.flatMap(s=>s.outputs).reduce((n,o)=>n+o.bytes,0);
  return {source,target,preparation:{...preparation,fingerprint:hash(preparation),outputBytes,requiredFreeBytes:outputBytes+128*1024*1024,ready:false,available:true},
    assembly:{...descriptor,fingerprint:hash({plan:descriptor,preparationFingerprint:hash(preparation),bundleFingerprint:hash(target)}),linkedComponents:1,linkedBytes:outputBytes,remainingComponents:target.components.filter(c=>c.role!=='condition_bias'),associated:false,installed:false}};
}
function install(payload){
  const f=window.__fixture;
  const entry=(manifest,installed)=>{const total=manifest.components.reduce((n,c)=>n+c.bytes,0);return {id:manifest.id,manifest,installed,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:installed?total:0,remainingBytes:installed?0:total,components:manifest.components.map(c=>({...c,reusable:installed,downloadable:!!c.url}))}};};
  const source=entry(payload.source,true),target=entry(payload.target,false);source.preparationPlans=[payload.preparation];source.preparedAssets=[];
  f.bundles=[source,target];f.__lcm=payload;f.jobs=[];f.artifacts=[];
  const lora={schema:'lma.model-bundle/1',id:'ui_condition_lora',modelId:'ui_condition_lora',recipeId:'ui_lora_v1',name:'LoRA compatibility fixture',engine:'sd_cpp',architecture:'sd15',pipeline:'lora',backend:'cpu',tasks:['image'],capabilities:['image_adapter'],adapter:{kind:'lora',baseArchitectures:['sd15'],basePipelines:['sd15_lcm']},parameters:{fields:{scale:{type:'number',default:1,minimum:0,maximum:2}}},components:[{role:'lora',path:'fixture.gguf',format:'gguf',bytes:300,sha256:'3'.repeat(64)}]};f.bundles.push(entry(lora,true));
  const previous=window.__handleFoundation;
  window.__handleFoundation=command=>{
    if(command.action==='submitTask'){
      const job={id:'ui_lcm_'+f.jobs.length,state:'queued',stage:'queued',createdAt:Date.now(),request:JSON.parse(JSON.stringify(command.request)),artifacts:[],error:''};f.jobs.push(job);return job;
    }
    return previous(command);
  };
  window.LMA.receive(f);
}
function prepared(){
  const f=window.__fixture,b=f.bundles[0];b.preparationPlans[0].ready=true;b.preparedAssets=[{id:'prep_'+'2'.repeat(32),bytes:5696,available:true,inUse:false,createdAt:Date.now(),assemblyPlans:[f.__lcm.assembly]}];
  f.jobs.forEach(j=>{j.state='succeeded';j.preparation={id:b.preparedAssets[0].id};});window.LMA.receive(f);
}
function associated(){
  const f=window.__fixture,b=f.bundles[1];b.plan.components.forEach(c=>{c.reusable=c.role==='condition_bias';});b.plan.reusableBytes=5696;b.plan.remainingBytes=b.plan.totalBytes-5696;b.transfer={state:'paused',token:''};
  f.bundles[0].preparedAssets[0].assemblyPlans[0].associated=true;f.jobs.filter(j=>j.request.type==='model.assemble').forEach(j=>{j.state='succeeded';j.assembly={installed:false,remainingBytes:b.plan.remainingBytes,linkedComponents:1};});window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,shot=async()=>{}){
  const initialDownloads=await page.evaluate(()=>window.__commands.filter(c=>c.action==='downloadBundle').length);
  await page.evaluate(installFixture);await page.evaluate(install,data());const payload=data();
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();await page.locator('[data-task="any"]').click();
  await page.locator('[data-bundle="'+payload.source.id+'"] [data-action="bundleInfo"]').first().click();
  assert((await page.locator('#modalContent').textContent()).includes('源模型'));assert.equal(await page.locator('#modalContent [data-action="bundleUse"]').isDisabled(),true);
  await page.locator('[data-action="preparationInfo"]').click();assert((await page.locator('#modalContent').textContent()).includes('所需额外可用空间'));
  await overflow(page,'LCM explicit preparation review');await shot('01-prepare.png','UI FIXTURE · User-selected source preparation / 用户明确准备源模型');
  await page.locator('[data-action="prepareAssets"]').click();
  await page.waitForFunction(()=>window.__fixture.jobs.some(j=>j.request.type==='model.prepare'));
  const preparation=await page.evaluate(()=>window.__fixture.jobs.find(j=>j.request.type==='model.prepare').request);
  assert.deepEqual(preparation,{type:'model.prepare',bundleId:payload.source.id,preparationId:payload.preparation.id,planFingerprint:payload.preparation.fingerprint});
  checked('LCM source is a peer model and only explicit signed preparation enters the queue');
  await page.evaluate(prepared);await page.locator('.nav-item[data-tab="models"]').click();
  await page.locator('[data-bundle="'+payload.source.id+'"] [data-action="bundleInfo"]').first().click();await page.locator('[data-action="assemblyInfo"]').click();
  const review=await page.locator('#modalContent').textContent();assert(review.includes('LCM_Dreamshaper_v7-f16.gguf')&&review.includes('merges.txt')&&review.includes('暂停'));
  await overflow(page,'LCM association dependency review');await shot('02-associate.png','UI FIXTURE · Explicit association and missing dependencies / 明确关联及缺失依赖');
  await page.locator('[data-action="assembleAssets"]').click();await page.waitForFunction(()=>window.__fixture.jobs.some(j=>j.request.type==='model.assemble'));
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>c.action==='downloadBundle').length),initialDownloads);await page.evaluate(associated);
  checked('Prepared condition association starts no base or vocabulary download');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-bundle="'+payload.target.id+'"] [data-action="bundleInfo"]').first().click();
  assert((await page.locator('#modalContent').textContent()).includes('像素'));await shot('03-dependencies.png','UI FIXTURE · Remaining user downloads and failed pixel gate / 用户选择依赖并保留像素失败状态');
  await page.locator('[data-action="downloadBundle"]').click();await page.waitForFunction(before=>window.__commands.filter(c=>c.action==='downloadBundle').length>before,initialDownloads);
  await page.waitForFunction(()=>{const commands=window.__commands.filter(c=>c.action==='downloadBundle'),last=commands[commands.length-1];return last&&(window.__fixture.commandResults||[]).some(r=>r.requestId===last.requestId);});
  assert.equal(await page.evaluate(()=>window.__commands.filter(c=>c.action==='downloadBundle').length),initialDownloads+1);
  await page.evaluate(()=>{const f=window.__fixture,b=f.bundles[1];b.installed=true;delete b.transfer;b.plan.components.forEach(c=>{c.reusable=true;});b.plan.reusableBytes=b.plan.totalBytes;b.plan.remainingBytes=0;window.LMA.receive(f);});
  await page.keyboard.press('Escape');await page.locator('[data-bundle="'+payload.target.id+'"] [data-action="bundleUse"]').click();
  assert.equal(await page.locator('[name="negativePrompt"]').isDisabled(),true);assert.equal(await page.locator('[data-adapter-select]').count(),0);
  await page.locator('[name="prompt"]').fill('LCM user-selected local image task · 界面演示');
  assert.equal(await page.locator('[name="allowUnmeasured"]').isChecked(),false);await page.locator('[name="allowUnmeasured"]').check();
  await page.locator('.task-parameters summary').click(); assert.equal(await page.locator('[data-bundle-field="steps"]').inputValue(),'4');
  await overflow(page,'LCM generation request');await shot('04-generate.png','UI FIXTURE · Model-scoped parameters and explicit trial / 模型专属参数及用户明确尝试');
  await page.locator('#localTaskForm button[type="submit"]').click();await page.waitForFunction(()=>window.__fixture.jobs.some(j=>j.request.type==='image.generate'));
  const generated=await page.evaluate(()=>window.__fixture.jobs.find(j=>j.request.type==='image.generate').request);
  assert.equal(generated.bundleId,payload.target.id);assert.equal(generated.allowUnmeasured,true);assert.equal(generated.parameters.cfg,1);assert.equal(generated.parameters.steps,4);assert.equal(generated.parameters.sampler,'lcm');
  checked('Only explicit dependency download and model-scoped LCM generation are dispatched; no LoRA is offered');
  await page.keyboard.press('Escape');await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();
};
