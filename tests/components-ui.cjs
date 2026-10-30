/* Production pages with explicit metadata/bridge fixtures. No HF downloads or neural execution. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const foundation=require('./foundation-ui.cjs'),recipes=require('./recipes-ui.cjs');
const templates=JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/recipe-templates.json'),'utf8')).templates;
function installSuggestions() {
  const f=window.__fixture,h=f.hub,base=window.__handleRecipe,foundation=window.__handleFoundation;
  const t=h.recipeTemplates.find(t=>t.id==='sana_edit_mnn_cpu_v1'),revision='0123456789abcdef0123456789abcdef01234567';
  const names={diffusion:'transformer.mnn',diffusion_data:'transformer.mnn.weight',connector:'connector.mnn',connector_data:'connector.mnn.weight',projector:'projector.mnn',projector_data:'projector.mnn.weight',vae:'vae_decoder.mnn',vae_data:'vae_decoder.mnn.weight',vae_encoder:'vae_encoder.mnn',vae_encoder_data:'vae_encoder.mnn.weight',llm:'llm.mnn',llm_data:'llm.mnn.weight',llm_config:'llm_config.json',tokenizer:'tokenizer.txt',meta_queries:'meta_queries.mnn'};
  const assets=t.requirements.map((r,i)=>({path:'export/'+names[r.role],format:r.formats[0],repository:'fixture/model',revision,bytes:1000+i,sha256:String(i%10).repeat(64),url:'https://huggingface.co/fixture/model/resolve/'+revision+'/export/'+names[r.role],blocked:''}));
  window.__suggestionMode='complete';let sequence=0;
  window.__handleRecipe=command=>{
    const old=base(command),d=h.recipeDraft;
    if(command.action==='hubFiles')h.files.assets=assets;
    if(command.action==='hubRecipeReview'){
      d.reviewing=false;
      if(window.__suggestionMode==='hold'){d.reviewing=true;delete d.suggestions;return {};}
      if(window.__suggestionMode==='error'){delete d.suggestions;d.reviewError='HF metadata fixture unavailable';return {};}
      const complete=window.__suggestionMode!=='incomplete';
      d.suggestions={reviewId:'fixture-review-'+ ++sequence,templateId:d.templateId,repository:{id:'fixture/model',revision},complete,pages:2,rows:t.requirements.map((r,i)=>{
        const state=d.bindings[r.role]?'existing':!complete?'incomplete':window.__suggestionMode==='ambiguous'&&r.role==='tokenizer'?'ambiguous':'unique';
        return {role:r.role,label:r.label,required:r.required!==false,state,selected:d.bindings[r.role],count:state==='ambiguous'?2:state==='existing'?0:1,candidates:state==='ambiguous'?[assets[i],{...assets[i],path:'alternate/tokenizer.txt'}]:[assets[i]]};
      })};d.suggestions.suggested=d.suggestions.rows.filter(r=>r.state==='unique').length;
    }
    if(command.action==='hubRecipeApply'){
      for(const role of command.roles){const row=d.suggestions.rows.find(r=>r.role===role);if(!row||row.state!=='unique'||d.bindings[role])throw Error('Stale fixture selection');d.bindings[role]={...row.candidates[0]};}delete d.suggestions;
    }
    if(command.action==='hubRecipeCancelReview'){d.reviewing=false;delete d.suggestions;}
    return old===undefined&&command.action.startsWith('hub')?{}:old;
  };
  window.__handleFoundation=command=>command.action.startsWith('hub')?window.__handleRecipe(command):foundation(command);
  f.localEngines.push({engine:'mnn_diffusion',available:true,deviceValidated:false});window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}){
  await page.evaluate(()=>{window.__componentPrevious={hub:JSON.parse(JSON.stringify(window.__fixture.hub)),recipe:window.__handleRecipe,foundation:window.__handleFoundation};});
  try {
  await page.keyboard.press('Escape');await page.evaluate(foundation.installFixture);await page.evaluate(()=>{window.__fixture.hub.fixtureRepositories=[];});await page.evaluate(recipes.installFixture,templates);await page.evaluate(installSuggestions);
  const commands=()=>page.evaluate(()=>window.__commands),count=async action=>(await commands()).filter(c=>c.action===action).length;
  const downloads=await count('downloadBundle'),declarations=await count('hubRecipeDeclare');await recipes.openRecipe(page);await recipes.selectTemplate(page,'sana_edit_mnn_cpu_v1');
  await page.locator('[data-action="recipePick"][data-role="diffusion"]').click();await page.locator('[data-action="recipeBind"][data-path="export/transformer.mnn"]').click();await page.waitForSelector('[data-action="recipeReview"]');
  assert.match(await page.locator('#recipePanel').innerText(),/不会下载文件，也不会覆盖已有选择/);checked('Component helper discloses metadata-only checking and preserves user control');
  await capture('01-component-selection.png','UI FIXTURE · selected primary and explicit companion review / 只读元数据，未下载模型');
  const review=async mode=>{const previous=await page.evaluate(()=>window.__fixture.hub.recipeDraft.suggestions?.reviewId||'');await page.evaluate(mode=>window.__suggestionMode=mode,mode);await page.locator('[data-action="recipeReview"]').click();await page.waitForFunction(previous=>{const r=window.__fixture.hub.recipeDraft.suggestions;return r&&r.reviewId!==previous;},previous);await page.waitForSelector('[data-action="recipeApply"]');};
  await review('complete');assert.equal(await page.locator('[data-recipe-suggestion]').count(),14);checked('Review offers all fourteen missing Sana components beside the preserved primary');
  assert.match(await page.locator('#recipePanel').innerText(),/0123456789abcdef0123456789abcdef01234567/);assert.match(await page.locator('#recipePanel').innerText(),/仍需核对模型架构/);checked('Review identifies exact revision and does not claim architecture compatibility');
  const before=await page.evaluate(()=>Object.keys(window.__fixture.hub.recipeDraft.bindings));assert.deepEqual(before,['diffusion']);checked('Viewing a complete proposal changes no binding');
  assert.equal(await count('downloadBundle'),downloads);assert.equal(await count('hubRecipeDeclare'),declarations);checked('Review neither registers nor downloads a model');
  await capture('02-companion-review.png','UI FIXTURE · exact-revision component suggestions / 用户确认前不应用');
  await page.locator('[data-recipe-suggestion="llm"]').uncheck();await page.locator('[data-action="recipeApply"]').click();await page.waitForSelector('#recipeTemplate');
  const request=(await commands()).findLast(c=>c.action==='hubRecipeApply');assert.equal(request.roles.length,13);assert(!request.roles.includes('llm'));assert(!('assets' in request));checked('Confirmation sends only checked roles and native review identity');
  assert.equal(await page.evaluate(()=>Object.keys(window.__fixture.hub.recipeDraft.bindings).length),14);assert.equal(await page.locator('[data-action="recipeDeclare"]').isEnabled(),false);checked('Unchecked required component remains missing and blocks declaration');
  await review('complete');assert.equal(await page.locator('[data-recipe-suggestion]').count(),1);await page.locator('[data-recipe-suggestion]').uncheck();const applies=await count('hubRecipeApply');await page.locator('[data-action="recipeApply"]').click();assert.equal(await count('hubRecipeApply'),applies);checked('An empty confirmation displays guidance without sending a mutation');
  await page.locator('[data-recipe-suggestion]').check();await page.locator('[data-action="recipeApply"]').click();await page.waitForSelector('#recipeTemplate');assert.equal(await page.locator('[data-action="recipeDeclare"]').isEnabled(),true);checked('Explicit remaining choice completes the existing recipe form');
  await page.locator('[data-action="recipeDeclare"]').click();await page.waitForSelector('#modal .bundle-components');assert.equal(await page.locator('#modal .bundle-components details').count(),15);assert.equal(await count('downloadBundle'),downloads);checked('Separate declaration discloses fifteen files and waits for a separate download action');
  await capture('03-complete-download-plan.png','UI FIXTURE · complete uninstalled model plan / 尚未下载或执行推理');await page.keyboard.press('Escape');
  await recipes.openRecipe(page);await recipes.selectTemplate(page,'sana_edit_mnn_cpu_v1');await review('ambiguous');
  assert.equal(await page.locator('[data-recipe-suggestion="tokenizer"]').count(),0);assert.match(await page.locator('#recipePanel').innerText(),/多个文件匹配，请手动选择/);checked('Ambiguous companion has no preselected or confirmable candidate');
  await page.locator('#recipePanel .hub-file').filter({hasText:'多个文件匹配'}).scrollIntoViewIfNeeded();await capture('04-ambiguous-component.png','UI FIXTURE · ambiguous filenames require manual selection / 不猜测配套版本');
  await page.locator('[data-action="recipeBack"]').click();await review('incomplete');assert.equal(await page.locator('[data-recipe-suggestion]').count(),0);assert.equal(await page.locator('[data-action="recipeApply"]').isEnabled(),false);checked('Incomplete directory disables automatic suggestions and retains manual selection');
  await page.locator('[data-action="recipeBack"]').click();await page.evaluate(()=>window.__suggestionMode='hold');await page.locator('[data-action="recipeReview"]').click();await page.waitForSelector('[data-action="recipeCancelReview"]');assert.equal(await page.locator('[data-action="recipeCancelReview"]').isEnabled(),true);await page.locator('[data-action="recipeCancelReview"]').click();await page.waitForSelector('#recipeTemplate');checked('Active metadata review has an enabled stop action and returns to preserved selection');
  await page.evaluate(()=>window.__suggestionMode='error');await page.locator('[data-action="recipeReview"]').click();await page.waitForSelector('[data-action="recipeBack"]');assert.match(await page.locator('#recipePanel').innerText(),/metadata fixture unavailable/);checked('Metadata errors provide a return path for retry or manual selection');
  await overflow(page,'375px companion-review and error layout');await page.keyboard.press('Escape');
  assert.equal(await count('downloadBundle'),downloads);checked('All helper states perform zero implicit model downloads');
  } finally {
    await page.evaluate(()=>{const previous=window.__componentPrevious,h=window.__fixture.hub;for(const key of Object.keys(h))delete h[key];Object.assign(h,previous.hub);window.__handleRecipe=previous.recipe;window.__handleFoundation=previous.foundation;delete window.__componentPrevious;delete window.__suggestionMode;window.LMA.receive(window.__fixture);});
  }
};
