/* Production LMA assets with an explicit program fixture; no Android/device/model execution. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const {chromium}=require(process.env.LMA_PLAYWRIGHT||'playwright');
const root=path.resolve(__dirname,'..'),assets=path.join(root,'app/src/main/assets');
const version=fs.readFileSync(path.join(root,'app/src/main/AndroidManifest.xml'),'utf8').match(/versionName="([^"]+)"/)[1];
const out=path.join(root,'build/workspace-ui'),media=path.join(root,'docs/media/workspace-v'+version);
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(media,{recursive:true});fs.rmSync(path.join(out,'results.json'),{force:true});
const names=['tests/workspace-ui.cjs','docs/design/tokens.json','app/src/main/java/com/lma/app/MainActivity.java',...fs.readdirSync(assets).filter(n=>!['foundation.js','license.js'].includes(n)&&!n.endsWith('.header.json')).map(n=>'app/src/main/assets/'+n)].filter(n=>fs.statSync(path.join(root,n)).isFile());
const fingerprint=Object.fromEntries(names.sort().map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')]));
const fixture={app:'LMA',version,models:JSON.parse(fs.readFileSync(path.join(assets,'models.json'),'utf8')).models.map(m=>({...m,installed:m.id==='m08',installedBytes:m.id==='m08'?m.bytes:0,download:{}})),settings:{theme:'dark',port:52187,apiKey:'lma_PROGRAM_FIXTURE_ONLY',source:'auto'},api:{state:'stopped'},engine:{state:'stopped',modelId:'',generating:false,localUrl:'http://127.0.0.1:52187/v1',addresses:[]},device:{name:'程序界面夹具 · 非真机',android:'fixture',totalMemory:8e9,availableMemory:4e9,freeStorage:20e9},chat:{sessionId:'session_0',messages:[],sessions:Array.from({length:32},(_,i)=>({id:'session_'+i,title:['规划一场周末旅行','整理项目的下一步','本地模型如何选型'][i%3]+' '+(i+1),updated:1793952000000-i*100000,modelId:'m08'}))},logs:[],error:'',commandResults:[],workflows:[],visionPairs:[],jobs:[],artifacts:[],bundles:[]};
let browser,context,server,page;const checks=[],errors=[],captures=[];
function check(value,name){assert(value,name);checks.push(name);console.log('PASS '+name);}
async function shot(name){await page.waitForTimeout(120);await page.screenshot({path:path.join(media,name+'.png')});captures.push(name+'.png');}
async function route(tab){await page.locator('.nav-item[data-tab="'+tab+'"]').click();}
async function snapshot(){await page.evaluate(()=>window.LMA.receive(structuredClone(window.__fixture)));}
async function main(){
 server=http.createServer((req,res)=>{const file=path.resolve(assets,decodeURIComponent(req.url.split('?')[0]).replace(/^\//,'')||'index.html');if(!file.startsWith(assets+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':file.endsWith('.png')?'image/png':file.endsWith('.json')?'application/json':'text/html; charset=utf-8');res.end(fs.readFileSync(file));});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({headless:true,executablePath:process.env.LMA_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',args:['--disable-background-networking','--disable-component-update']});
 context=await browser.newContext({viewport:{width:393,height:873},recordVideo:{dir:path.join(out,'video'),size:{width:393,height:873}}});
 await context.route('**/*',r=>r.request().url().startsWith(origin+'/')?r.continue():r.abort());
 page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(f=>{window.__fixture=f;window.__commands=[];window.Android={themePreference:()=>f.settings.theme,theme:()=>{},layoutInfo:()=>JSON.stringify({nativeInsets:false,ime:false,textScale:1}),requestSnapshot:()=>window.LMA.receive(structuredClone(f)),copy:()=>{},dispatch:raw=>{const c=JSON.parse(raw);window.__commands.push(c);if(c.action==='selectSession'){f.chat.sessionId=c.id;window.LMA.receive(structuredClone(f));}}};},fixture);
 await page.goto(origin);await page.waitForSelector('#page-chat.active');
 await page.evaluate(()=>{const label=document.createElement('div');label.className='program-capture-label';label.textContent='程序界面夹具 · 非真机 · 未执行模型';label.style.cssText='position:fixed;bottom:0;right:0;z-index:9999;background:#141414;color:#eee;text-align:center;font:10px sans-serif;padding:3px 8px;pointer-events:none';document.body.appendChild(label);});
 check(await page.locator('html').getAttribute('data-theme')==='dark','Conversation-first home resolves the dark default before interaction');
 check(await page.locator('#page-models').isHidden(),'Home does not require opening the model catalogue');
 check(await page.locator('.workspace-sidebar').isVisible()&&await page.locator('.bottom-nav .nav-item').count()===5,'Compact left navigation exposes all five destinations');
 check(await page.locator('#chatForm #chatModelPicker').count()===1,'Model picker is inside the composer');
 check(await page.locator('#conversationMore').isVisible()&&await page.locator('#conversationOptions').isHidden(),'Creation controls stay in the optional plus sheet');
 check(await page.locator('#runtimeAction').isVisible(),'Runtime management stays visible on the conversation home');
 await shot('01-home-dark');
 await page.locator('#sidebarToggle').click();
 check(await page.locator('#workspaceSidebar').getAttribute('aria-modal')==='true','Expanded narrow sidebar is a full-width modal workspace');
 check(await page.locator('#main').evaluate(e=>e.inert)&&await page.locator('.topbar').evaluate(e=>e.inert),'Expanded narrow sidebar makes covered content inert');
 check(await page.locator('#workspaceSidebar').evaluate(e=>e.getBoundingClientRect().width)===393,'Expanded narrow sidebar occupies the full available width');
 check(await page.locator('.sidebar-session').count()===24,'Recent sessions are bounded to 24 rendered rows');
 await page.evaluate(()=>window.LMAMica.receiveNative({nativeInsets:false,ime:true,textScale:1}));
 check(await page.locator('#workspaceSidebar').isVisible(),'A delayed keyboard callback cannot hide an expanded narrow drawer');
 await page.evaluate(()=>window.LMAMica.receiveNative({nativeInsets:false,ime:false,textScale:1}));
 await shot('02-sidebar-dark');
 await page.locator('.sidebar-settings').focus();await page.keyboard.press('Tab');
 check(await page.locator('.brand').evaluate(e=>e===document.activeElement),'Drawer keyboard focus wraps to its first control');
 await page.keyboard.press('Escape');
 check(await page.locator('html').getAttribute('data-sidebar')==='collapsed'&&!await page.locator('#main').evaluate(e=>e.inert),'Escape restores the compact workspace and releases inert');
 await page.locator('#sidebarToggle').click();await page.locator('.sidebar-session[data-id="session_1"]').click();
 check(await page.locator('html').getAttribute('data-sidebar')==='collapsed'&&await page.locator('#workspaceChatTitle').textContent()==='整理项目的下一步 2','Session selection dispatches the original contract and closes the drawer');
 await page.locator('#conversationMore').click();
 check(await page.locator('#conversationMode').isVisible()&&await page.locator('#conversationOptions').isVisible(),'Plus opens real creation modes and parameters');
 await page.locator('#modal [data-action="closeModal"]').click();
 await page.locator('#chatInput').fill('下一步，试试在手机上整理我的想法。');await route('models');
 check(await page.locator('.model-card').evaluateAll(cards=>cards.slice(0,3).map(e=>e.dataset.model).join(','))==='m08,m06,m01','Original recommended prefix remains unchanged');
 await shot('03-models-dark');await page.locator('[data-filter="local"]').click();
 check(await page.locator('[data-action="deleteModel"][data-id="m08"]').isVisible(),'Local model deletion is labelled and visible on the outer row');
 await shot('04-local-dark');
 await page.evaluate(()=>{window.__fixture.engine.state='ready';window.__fixture.engine.modelId='m08';window.__fixture.engine.detail='模型已加载，可在本机对话';});await snapshot();
 await route('chat');
 check(await page.locator('#chatInput').inputValue()==='下一步，试试在手机上整理我的想法。','Draft survives navigation');
 const sends=await page.evaluate(()=>window.__commands.filter(c=>['sendMessage','chatSubmit'].includes(c.action)).length);
 await page.locator('#chatModelPicker').click();await page.waitForTimeout(30);
 check(await page.locator('#modal').isVisible()&&await page.evaluate(()=>window.__commands.filter(c=>['sendMessage','chatSubmit'].includes(c.action)).length)===sends,'Opening the composer model picker never submits a prepared draft');
 await page.locator('#modal [data-action="closeModal"]').click();
 await page.locator('#runtimeAction').click();
 check(await page.locator('#modal [data-action="stopTextModel"]').isVisible(),'Global runtime manager exposes the real Unload action');
 await page.locator('#modal [data-action="closeModal"]').click();
 await page.evaluate(()=>{window.__fixture.chat.messages=[{id:'fixture-user',role:'user',content:'帮我规划一次本地 AI 创作。',status:'done'},{id:'fixture-assistant',role:'assistant',content:'先从你想完成的作品开始。\n\n**选择模型**：在模型库中按生图、视频、音频或 3D 标签筛选。\n\n**开始创作**：点击输入框旁的「＋」，设置本次参数，再提交到本机队列。',status:'done'}];});await snapshot();
 check(!await page.locator('#page-chat').evaluate(e=>e.classList.contains('is-empty')),'Active messages switch to the bottom-anchored composer layout');
 await shot('05-conversation-dark');
 await route('tasks');await shot('06-tasks-dark');await route('server');await shot('07-api-dark');await route('settings');await shot('08-settings-dark');
 await page.evaluate(()=>{window.__fixture.settings.theme='light';window.__fixture.chat.messages=[];});await snapshot();await route('chat');await shot('09-home-light');
 check(await page.locator('html').getAttribute('data-theme')==='light'&&await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundColor)==='rgb(255, 255, 255)','Light theme uses neutral white with the same layout');
 await route('models');await shot('10-models-light');
 await page.setViewportSize({width:1280,height:800});await route('chat');await shot('11-wide-light');
 check(await page.locator('html').getAttribute('data-sidebar')==='expanded','Wide workspace expands the labelled navigation and sessions');
 check(await page.locator('#workspaceSidebar').getAttribute('aria-modal')===null&&!await page.locator('#main').evaluate(e=>e.inert),'Wide sidebar remains non-modal with an interactive centre');
 await page.locator('#sidebarToggle').click();
 check(await page.locator('html').getAttribute('data-sidebar')==='collapsed','Wide sidebar can collapse for additional workspace');
 await page.evaluate(()=>{window.__fixture.settings.theme='dark';});await snapshot();await page.locator('#sidebarToggle').click();await shot('12-wide-dark');
 const ids=await page.evaluate(()=>{const values=Array.from(document.querySelectorAll('[id]')).map(e=>e.id);return values.filter((v,i)=>values.indexOf(v)!==i);});
 check(ids.length===0,'Restructuring retains unique element identifiers');
 const before=await page.evaluate(()=>window.__commands.length);await page.waitForTimeout(1500);
 check(await page.evaluate(()=>window.__commands.length)===before,'Idle workspace does not poll the native bridge');
 check(await page.evaluate(()=>!window.__commands.some(c=>/download|delete|load|start|submit/i.test(c.action))),'Navigation and style verification never starts downloads, inference, deletion or services');
 check(errors.length===0,'Production workspace has no unhandled JavaScript errors');
}
main().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
 let video;if(page)video=page.video();
 if(context)await context.close();if(browser)await browser.close();if(server)await new Promise(resolve=>server.close(resolve));
 if(video)fs.copyFileSync(await video.path(),path.join(out,'workspace-demo.webm'));
 if(!process.exitCode){fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({version,passed:checks.length,checks,physicalDevice:false,modelInference:false,weightsDownloaded:false,browser_closed:true,captures,input_fingerprint:fingerprint},null,2)+'\n');console.log(JSON.stringify({passed:checks.length,captures:captures.length,browser_closed:true}));}
});
