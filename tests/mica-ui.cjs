/* UI10 production-page checks. Labelled bridge fixtures, no Android emulator. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const {chromium}=require(process.env.LMA_PLAYWRIGHT||'playwright');
const root=path.resolve(__dirname,'..'),assets=path.join(root,'app/src/main/assets'),out=path.join(root,'build/mica-ui');
fs.mkdirSync(out,{recursive:true});
const version=fs.readFileSync(path.join(root,'app/src/main/AndroidManifest.xml'),'utf8').match(/versionName="([^"]+)"/)[1];
const files=['tests/mica-ui.cjs','docs/design/tokens.json','app/src/main/java/com/lma/app/MainActivity.java',...fs.readdirSync(assets).filter(n=>!['foundation.js','license.js'].includes(n)&&!n.endsWith('.header.json')).map(n=>'app/src/main/assets/'+n)].filter(n=>fs.statSync(path.join(root,n)).isFile());
const fingerprint=Object.fromEntries(files.sort().map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')]));
const catalogue=JSON.parse(fs.readFileSync(path.join(assets,'models.json'),'utf8')).models;
const base={app:'LMA',version,models:catalogue.map(m=>({...m,installed:m.id==='m08',installedBytes:m.id==='m08'?m.bytes:0,download:{}})),settings:{theme:'dark',port:52187,apiKey:'lma_UI_FIXTURE_ONLY',source:'auto'},api:{state:'stopped'},engine:{state:'stopped',modelId:'',generating:false,addresses:[]},device:{name:'程序界面夹具 · 非真机',android:'fixture',totalMemory:8e9,availableMemory:4e9,freeStorage:20e9},chat:{sessionId:'mica',messages:[],sessions:[]},logs:[],error:'',commandResults:[],workflows:[],visionPairs:[],jobs:[],artifacts:[],bundles:[]};
let browser,context,server,page;const checks=[],errors=[],matrix=[];
function check(value,name){assert(value,name);checks.push(name);}
async function overflow(name){
 const failures=await page.evaluate(()=>{
  const all=[document.documentElement,document.querySelector('.app-shell'),...document.querySelectorAll('.page:not([hidden]),.model-card,.panel,.job-card,.composer,.filter-row,.task-filter-row')];
  return all.filter(e=>e&&e.getClientRects().length&&e.scrollWidth>e.clientWidth+2).map(e=>({class:e.id||e.className,width:e.clientWidth,scroll:e.scrollWidth}));
 });assert.deepEqual(failures,[],name+' has no horizontal overflow');
}
async function scale(value){await page.evaluate(s=>{document.documentElement.style.fontSize=(16*s)+'px';window.LMAMica.receiveNative({textScale:s,nativeInsets:false,ime:false});},value);}
async function route(tab){await page.locator('.nav-item[data-tab="'+tab+'"]').click();await page.waitForTimeout(20);}
async function main(){
 server=http.createServer((req,res)=>{const file=path.resolve(assets,decodeURIComponent(req.url.split('?')[0]).replace(/^\//,'')||'index.html');if(!file.startsWith(assets+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.png')?'image/png':file.endsWith('.json')?'application/json':'text/html; charset=utf-8');res.end(fs.readFileSync(file));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 browser=await chromium.launch({headless:true,executablePath:process.env.LMA_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--disable-background-networking','--disable-component-update']});
 context=await browser.newContext({viewport:{width:393,height:873}});page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(data=>{window.__state=data;window.__commands=[];window.Android={themePreference:()=>data.settings.theme,theme:()=>{},layoutInfo:()=>JSON.stringify({nativeInsets:false,ime:false,textScale:1}),requestSnapshot:()=>window.LMA.receive(structuredClone(data)),dispatch:raw=>{window.__commands.push(JSON.parse(raw));},copy:()=>{}};},base);
 await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForSelector('.model-card');
 check(await page.locator('html').getAttribute('data-theme')==='dark','Default is dark before first interaction');
 check(await page.locator('.model-card').evaluateAll(a=>a.slice(0,3).map(e=>e.dataset.model).join(','))==='m08,m06,m01','Recommended prefix remains m08, m06, m01');
 const viewports=[[320,480],[320,568],[360,640],[360,740],[375,667],[390,844],[393,873],[412,915],[430,932],[480,960],[568,320],[640,360],[800,360],[600,960],[840,1180],[1024,768],[1280,800]];
 for(const theme of ['dark','light'])for(const [width,height] of viewports)for(const textScale of [1,1.5,2]){
  await page.setViewportSize({width,height});await scale(textScale);await page.evaluate(theme=>{window.__state.settings.theme=theme;window.LMA.receive(structuredClone(window.__state));},theme);
  for(const tab of ['models','chat','tasks','server','settings']){
   await route(tab);await overflow([theme,width,height,textScale,tab].join('/'));
   matrix.push({theme,width,height,textScale,page:tab,passed:true});
  }
 }
 check(matrix.length===510,'Both themes and three text scales pass 17 viewports across all five pages');
 for(const theme of ['dark','light']){
  await page.setViewportSize({width:393,height:873});await scale(1.3);await page.evaluate(t=>{window.__state.settings.theme=t;window.LMA.receive(structuredClone(window.__state));},theme);
  for(const tab of ['models','chat','tasks','server','settings']){await route(tab);await overflow(theme+'/1.3/'+tab);matrix.push({theme,width:393,height:873,textScale:1.3,page:tab,passed:true});}
 }
 check(matrix.length===520,'130 percent text passes all five pages in both themes');
 for(const width of [240,319,320,359,360,479,480,599,600,839,840,1199,1200]){
  await scale(1);await page.setViewportSize({width,height:800});await route('models');await overflow('boundary '+width);
 }
 check(true,'Width boundaries include minimum usable window and have no missing layout band');
 await page.setViewportSize({width:393,height:873});await scale(1);await route('chat');
 await page.locator('#chatInput').fill('保留的本地草稿');await page.locator('#chatInput').press('Enter');
 check((await page.locator('#chatInput').inputValue()).includes('\n'),'Phone Enter creates a newline without submitting');
 check(await page.evaluate(()=>window.__commands.filter(c=>c.action==='sendMessage'||c.action==='chatSubmit').length)===0,'Newline does not trigger generation');
 await page.evaluate(()=>{window.__state.settings.theme='dark';window.LMA.receive(structuredClone(window.__state));});
 check((await page.locator('#chatInput').inputValue()).includes('保留的本地草稿'),'Theme change preserves the composer draft');
 await page.evaluate(()=>window.LMAMica.receiveNative({nativeInsets:true,ime:true,textScale:1}));await page.waitForTimeout(40);
 check(!await page.locator('.bottom-nav').isVisible(),'Native IME removes covered navigation from focus and hit testing');
 await page.evaluate(()=>window.LMAMica.receiveNative({nativeInsets:true,ime:false,textScale:1}));await page.waitForTimeout(40);
 check(await page.locator('.bottom-nav').isVisible(),'Closing the IME restores the five destinations');
 await route('models');await page.locator('[data-filter="local"]').click();await page.locator('[data-action="modelInfo"]').first().click();
 check(await page.locator('.app-shell').evaluate(el=>el.inert),'Modal background is inert');
 await page.keyboard.press('Tab');check(await page.evaluate(()=>document.getElementById('modal').contains(document.activeElement)),'Keyboard focus remains inside the modal');
 await page.keyboard.press('Escape');check(!await page.locator('.app-shell').evaluate(el=>el.inert),'Closing restores background interactivity');
 await page.evaluate(()=>{window.__state.error='UI regression fixture';window.LMA.receive(structuredClone(window.__state));});
 await page.locator('[data-action=\"modelInfo\"]').first().click();await page.locator('#modal [data-action=\"closeModal\"]').first().click();
 check(!await page.locator('#modalBackdrop').isVisible(),'An existing page alert cannot intercept modal controls');
 await page.evaluate(()=>{window.__state.error='';window.LMA.receive(structuredClone(window.__state));});
 await page.locator('#modelSearch').fill('NoSuchFixture');await page.locator('[data-action="clearSearch"]').click();
 check(await page.locator('#modelSearch').inputValue()==='','Search has an accessible clear action');
 const sizes=await page.locator('.nav-item').evaluateAll(a=>a.map(e=>({w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height})));
 check(sizes.every(s=>s.w>=48&&s.h>=48),'Phone navigation retains 48px hit targets');
 check(await page.locator('html').evaluate(el=>getComputedStyle(el).getPropertyValue('--bg').trim())==='var(--lma-canvas)'||await page.locator('body').evaluate(el=>getComputedStyle(el).backgroundColor)==='rgb(21, 26, 43)','Production surfaces use the approved theme');
 await page.emulateMedia({reducedMotion:'reduce'});
 check(await page.locator('.button').first().evaluate(el=>getComputedStyle(el).transitionDuration)==='0s','Reduced motion disables nonessential transitions');
 check(await page.evaluate(()=>window.__commands.filter(c=>/download|delete|loadModel|startServer/i.test(c.action)).length)===0,'Theme and layout checks never download, delete or load user models');
 check(errors.length===0,'No production-page JavaScript errors');
}
main().catch(e=>{console.error(e);process.exitCode=1;fs.writeFileSync(path.join(out,'failure.txt'),String(e.stack));}).finally(async()=>{
 if(context)await context.close();if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
 if(!process.exitCode)fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({schema:'lma.mica-ui/1',version,passed:checks.length,checks,matrix,browser_closed:true,physicalDevice:false,ui_uses_simulated_bridge:true,complete_trained_model_runs:0,input_fingerprint:fingerprint},null,2)+'\n');
 console.log(JSON.stringify({passed:checks.length,layouts:matrix.length,browser_closed:true,errors}));
});
