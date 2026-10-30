/* Exact shipped metadata + independently checked name fixture; bridge/download/inference are simulated. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {installFixture}=require('./foundation-ui.cjs');
const catalogue=JSON.parse(fs.readFileSync(path.join(__dirname,'../catalogue/model-bundles.json'),'utf8')).bundles;
const headers=JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/speech-voices.json'),'utf8')).models;
const nano='moss_nano_100m_onnx_catalogue_v1';
function installSpeech({catalogue,headers}) {
  const f=window.__fixture;
  f.bundles=catalogue.filter(m=>m.tasks.includes('audio')).map(manifest=>{
    const components=manifest.components.map(c=>({...c,reusable:false,downloadable:!!c.url})),total=components.reduce((n,c)=>n+c.bytes,0);
    return {id:manifest.id,manifest,installed:false,config:{values:Object.fromEntries(Object.entries(manifest.parameters.fields).map(([k,v])=>[k,v.default]))},plan:{totalBytes:total,reusableBytes:0,remainingBytes:total,components}};
  });
  for(const b of f.bundles) {
    const kind=b.manifest.pipeline==='piper_vits'?'piper':b.id==='moss_nano_100m_onnx_catalogue_v1'?'nano':b.manifest.pipeline;
    const h=headers.find(h=>h.id===kind);if(!h)continue;
    b.parameterSchema=JSON.parse(JSON.stringify(b.manifest.parameters));const field=b.parameterSchema.fields.speaker;
    field.maximum=Math.min(field.maximum,h.count-1);field.actualVoiceCount=h.count;field.limitSource='model_metadata';
    if(h.names.length)field.choices=h.names.map((label,value)=>({value,label}));
    field.help='音色名称来自已下载的模型文件，也可直接输入编号；名称不扩展当前配方的语言能力。';
  }
  f.localEngines=[...new Set(f.bundles.map(b=>b.manifest.engine))].map(engine=>({engine,available:true,deviceValidated:false}));
  window.LMA.receive(f);
}
module.exports=async function(page,checked,overflow,output,capture=async()=>{}) {
  await page.keyboard.press('Escape');await page.evaluate(installFixture);await page.evaluate(installSpeech,{catalogue,headers});
  const command=action=>page.evaluate(action=>window.__commands.filter(c=>c.action===action),action);
  const start=await command('downloadBundle');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="all"]').click();await page.locator('[data-task="audio"]').click();
  assert.equal(await page.locator('[data-bundle="'+nano+'"]').count(),1);checked('All includes the complete Nano 100M profile beside existing speech peers');
  await capture('01-audio-catalogue.png','UI FIXTURE · optional audio catalogue / 用户自主选择下载，无模型推理');
  await page.locator('[data-bundle="'+nano+'"] [data-action="bundleInfo"]').first().click();
  assert.equal(await page.locator('#modal .bundle-components details').count(),11);checked('Nano review discloses all eleven required component files');
  assert.deepEqual(await command('downloadBundle'),start);checked('Audio catalogue and component review trigger zero model downloads');
  await page.locator('#modal [data-action="downloadBundle"]').click();await page.waitForFunction(id=>window.__commands.some(c=>c.action==='downloadBundle'&&c.id===id),nano);
  assert.deepEqual((await command('downloadBundle')).slice(start.length).map(c=>c.id),[nano]);checked('Explicit Nano installation dispatches exactly one selected bundle intent');
  await page.evaluate(()=>{for(const b of window.__fixture.bundles){b.installed=true;delete b.transfer;}window.LMA.receive(window.__fixture);});
  const kokoro=catalogue.find(m=>m.pipeline==='kokoro').id;
  await page.locator('[data-filter="local"]').click();await page.locator('[data-bundle="'+kokoro+'"] [data-action="bundleInfo"]').first().click();await page.locator('#modal [data-action="bundleSettings"]').click();
  const voice=()=>page.locator('[data-bundle-field="speaker"]');
  assert.equal(await page.locator('#modal datalist option').filter({hasText:'em_santa'}).getAttribute('value'),'53 · em_santa');
  assert.equal(await page.locator('#modal datalist option').filter({hasText:'af_alloy'}).getAttribute('value'),'0 · af_alloy');checked('Kokoro names reflect exact pinned file indices including em_santa at 53');
  assert.match(await page.locator('#bundleSettingsForm').innerText(),/54 个音色/);checked('Model-derived voice count is visible beside editable bounds');
  await voice().fill('999');await voice().blur();assert.equal(await voice().inputValue(),'53 · em_santa');checked('Oversized voice ID fills back the actual maximum and its name');
  await voice().fill('af_heart');await voice().blur();assert.equal(await voice().inputValue(),'3 · af_heart');checked('Exact unique voice name resolves to its numeric ID');
  await voice().fill('1.9');await voice().blur();assert.equal(await voice().inputValue(),'1 · af_aoede');checked('Numeric editing retains native integer floor and named presentation');
  await voice().fill('missing voice');await voice().blur();const saves=(await command('saveBundleSettings')).length;
  await page.locator('#bundleSettingsForm [type="submit"]').click();assert.equal((await command('saveBundleSettings')).length,saves);checked('Unknown nonnumeric voice names cannot submit invalid settings');
  await voice().fill('53 · em_santa');await voice().blur();await capture('02-kokoro-voices.png','UI FIXTURE · local-file names and 54 voice IDs / 真实文件名称，非声音质量演示');
  await page.locator('#bundleSettingsForm [type="submit"]').click();await page.waitForFunction(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.speaker===53,kokoro);
  assert.equal(typeof(await command('saveBundleSettings')).at(-1).settings.speaker,'number');checked('Named voice settings persist a numeric API-compatible value');
  await page.locator('[data-bundle="'+nano+'"] [data-action="bundleUse"]').click();await page.locator('.task-parameters summary').click();
  assert.equal(await voice().inputValue(),'0 · CN 欢迎关注模思智能');checked('Nano keeps its own default independently of Kokoro settings');
  await voice().fill('1000');await voice().blur();assert.equal(await voice().inputValue(),'17 · JP Arisa');checked('Nano clamps to its separate eighteen-voice file bound');
  await page.locator('#localTaskForm [name="prompt"]').fill('本段用于界面交互测试，不代表手机生成的声音。');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();await capture('03-nano-parameters.png','UI FIXTURE · Nano model-specific voice and generation parameters / 无真实推理');
  await page.locator('#localTaskForm [type="submit"]').click();await page.waitForSelector('#page-tasks.active .job-card');
  const request=(await command('submitTask')).at(-1).request;assert.equal(request.bundleId,nano);assert.equal(request.parameters.speaker,17);assert.equal(request.type,'speech.synthesize');checked('Speech task freezes selected bundle and numeric named-voice value');
  const saved=await page.evaluate(id=>window.__fixture.bundles.find(b=>b.id===id).config.values.speaker,kokoro);assert.equal(saved,53);checked('Submitting Nano cannot change another model’s stored voice');
  await capture('04-speech-queue.png','UI FIXTURE · immutable speech task / 仅验证队列交互，未生成音频');
  await page.locator('.nav-item[data-tab="models"]').click();await page.locator('[data-filter="local"]').click();
  const piper=catalogue.find(m=>m.pipeline==='piper_vits').id;
  await page.locator('[data-bundle="'+piper+'"] [data-action="bundleUse"]').click();await page.locator('.task-parameters summary').click();
  await voice().fill('20');await voice().blur();assert.equal(await voice().inputValue(),'0');checked('Unnamed single-voice model stays numeric and clamps to zero');
  await page.keyboard.press('Escape');
  await page.evaluate(id=>{const b=window.__fixture.bundles.find(b=>b.id===id);delete b.parameterSchema;window.LMA.receive(window.__fixture);},kokoro);
  await page.locator('[data-bundle="'+kokoro+'"] [data-action="bundleUse"]').click();await page.locator('.task-parameters summary').click();
  await voice().fill('999');await voice().blur();assert.equal(await voice().inputValue(),'53');assert.match(await page.locator('#localTaskForm').innerText(),/发布者声明上限（待核对）/);checked('Unreadable metadata falls back to disclosed recipe limits without invented names');
  await page.keyboard.press('Escape');
  const qwen=catalogue.find(m=>m.engine==='qwen_tts_native').id;
  await page.locator('[data-bundle="'+qwen+'"] [data-action="bundleUse"]').click();assert.equal(await voice().count(),0);checked('Qwen Base gains no unsupported named-speaker controls');
  await overflow(page,'375px speech selection and numeric form layout');await page.keyboard.press('Escape');
  assert.deepEqual((await command('downloadBundle')).slice(start.length).map(c=>c.id),[nano]);checked('Voice settings, previews and task submission issue no further downloads');
};
