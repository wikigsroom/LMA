/* Current optional recommendations, real catalogue metadata, simulated transfers only. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const read=name=>JSON.parse(fs.readFileSync(path.join(__dirname,'../app/src/main/assets/',name),'utf8'));
const manifests=read('model-bundles.json').bundles, legacy=read('models.json').models;
const policy=read('recommendations.json');
function install(data) {
  const f=window.__fixture;
  f.recommendations=data.policy;
  f.models=data.legacy.map(m=>({...m,installed:false,download:{},partialBytes:0}));
  f.bundles=data.manifests.map(manifest=>({id:manifest.id,manifest,installed:false,
    config:{values:Object.fromEntries(Object.entries((manifest.parameters||{}).fields||{}).map(([k,v])=>[k,v.default]))},
    plan:{totalBytes:manifest.components.reduce((n,c)=>n+c.bytes,0),remainingBytes:manifest.components.reduce((n,c)=>n+c.bytes,0),reusableBytes:0,
      components:manifest.components.map(c=>({...c,reusable:false,downloadable:!!c.url}))}}));
  f.localEngines=[...new Set(data.manifests.map(m=>m.engine))].map(engine=>({engine,available:true,deviceValidated:false}));
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}) {
  const original=await page.evaluate(()=>{window.__recommendationsPreviousHandler=window.__handleFoundation;return JSON.parse(JSON.stringify(window.__fixture));});
  const controls=await page.evaluate(()=>({source:document.getElementById('catalogueSource').value,content:document.getElementById('contentFilter').value}));
  const commands=()=>page.evaluate(()=>window.__commands.filter(c=>/^(download|downloadBundle|submitTask|load|import)/.test(c.action)));
  try {
    await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(install,{manifests,legacy,policy});
    const start=(await commands()).length;
    await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="recommended"]').click();await page.locator('[data-task="any"]').click();
    assert.equal(await page.locator('#modelList .model-card').count(),14);checked('Default Recommended exposes fourteen optional text/image/video/audio/3D choices');
    assert.deepEqual(await page.locator('#modelList .model-card').evaluateAll(ns=>ns.slice(0,3).map(n=>n.dataset.model)),['m08','m06','m01']);checked('The three original text recommendations remain first in the same order');
    assert.equal(await page.locator('#modelList .recommendation-note').count(),11);checked('Every new recommendation shows a reason and its resource or workflow hint');
    for(const [task,count] of Object.entries({any:14,text:3,image:3,video:2,audio:3,'3d':3})) {
      assert.equal(await page.locator('[data-task="'+task+'"] .recommendation-count').innerText(),String(count));
      checked('Recommendation count for '+task+' matches visible catalogue choices');
    }
    await overflow(page,'Recommended overview at 375px');await capture('01-recommended-overview.png','UI FIXTURE · Fourteen optional recommendations; original text order retained');
    for(const [index,task] of ['image','video','audio','3d'].entries()) {
      await page.locator('[data-task="'+task+'"]').click();
      const expected=policy.entries.filter(e=>e.task===task);
      assert.deepEqual(await page.locator('#modelList [data-bundle]').evaluateAll(ns=>ns.map(n=>n.dataset.bundle)),expected.map(e=>e.bundleId));
      assert.equal(await page.locator('#modelList [data-recommended-task="'+task+'"]').count(),expected.length);
      checked(task+' recommendations use exact pinned downloadable bundle identities');
      for(const e of expected) assert(await page.locator('[data-bundle="'+e.bundleId+'"] .recommendation-note').innerText().then(t=>t.includes(e.reason)&&t.includes(e.hint)));
      assert.equal(await page.locator('#modelList .content-nsfw').count(),task==='image'?2:task==='video'?1:0);checked(task+' recommendations preserve independent sourced NSFW labels');
      assert(await page.locator('#modelList [data-action="bundleInfo"]').count()>=expected.length);checked(task+' recommendations retain model details and download-management entry points');
      await page.locator('#page-models').evaluate(el=>el.scrollTop=0);await overflow(page,task+' recommended choices at 375px');
      await capture('0'+(index+2)+'-recommended-'+task+'.png','UI FIXTURE · Optional '+task+' choices; no model download or inference');
    }
    assert.equal((await commands()).length,start);checked('Opening all recommendation categories starts no downloads, model loads or generation');
    const selected=policy.entries.find(e=>e.task==='audio').bundleId;
    await page.locator('[data-task="audio"]').click();await page.locator('[data-bundle="'+selected+'"] [data-action="bundleInfo"]').first().click();
    assert(await page.locator('.bundle-components details').count()>0);checked('Recommendation details disclose required components before download');
    assert.equal((await commands()).length,start);checked('Viewing recommendation details still requires explicit download consent');
    await page.locator('#modal [data-action="downloadBundle"]').click();await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),selected);
    assert.equal((await commands()).length,start+1);checked('One explicit download selects only the chosen recommendation (simulated bridge)');
    await page.keyboard.press('Escape');await page.locator('[data-filter="local"]').click();await page.locator('[data-task="any"]').click();
    assert.deepEqual(await page.locator('#modelList [data-bundle]').evaluateAll(ns=>ns.map(n=>n.dataset.bundle)),[selected]);checked('Local shows the selected transfer without treating other recommendations as installed');
    await page.locator('[data-filter="all"]').click();await page.selectOption('#catalogueSource','registered');await page.selectOption('#contentFilter','any');
    assert.equal(await page.locator('#modelList [data-bundle]').count(),82);checked('All keeps the full 82-bundle catalogue beyond the recommendation subset');
    await page.locator('[data-filter="recommended"]').click();
    await page.evaluate(()=>{delete window.__fixture.recommendations;window.LMA.receive(window.__fixture);});
    assert.equal(await page.locator('#modelList .model-card').count(),3);checked('Missing optional recommendation metadata falls back to the original three text choices');
    await page.evaluate(data=>{window.__fixture.recommendations=data;window.LMA.receive(window.__fixture);},policy);
    await page.locator('[data-task="video"]').click();await page.setViewportSize({width:320,height:720});await overflow(page,'320px recommendation counts and hints wrap');await page.setViewportSize({width:375,height:812});
  } finally {
    await page.keyboard.press('Escape');await page.evaluate(f=>{window.__fixture=f;window.__handleFoundation=window.__recommendationsPreviousHandler;delete window.__recommendationsPreviousHandler;window.LMA.receive(f);},original);
    await page.evaluate(values=>{for(const [id,value] of [['catalogueSource',values.source],['contentFilter',values.content]]){const el=document.getElementById(id);el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}));}},controls);
    await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-task="any"]').click();await page.locator('[data-filter="recommended"]').click();
  }
};
