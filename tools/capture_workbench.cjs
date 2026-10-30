/* Execute current production UI against labelled bridge fixtures and record the interactions. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const assert = require('node:assert/strict');
const {chromium} = require(process.env.LMA_PLAYWRIGHT || 'playwright');
const mode=process.argv[2] || 'workbench'; assert(['workbench','preflight','recovery','lcm','audio','ltx','resources'].includes(mode));
const checkScreen=require('../tests/'+mode+'-ui.cjs');
const root = path.resolve(__dirname, '..'), assets = path.join(root, 'app/src/main/assets');
const out = path.join(root, 'docs/media/development',mode), work = path.join(root, 'build',mode+'-media');
fs.mkdirSync(out, {recursive:true}); fs.mkdirSync(work, {recursive:true});
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const sourceFiles = fs.readdirSync(assets, {recursive:true}).map(n=>path.join(assets,n)).filter(p=>fs.statSync(p).isFile()).concat(__filename, path.join(root,'tests',mode+'-ui.cjs'), path.join(root,'tests/foundation-ui.cjs'), ...(['lcm','ltx'].includes(mode)?['model-bundles.json','asset-preparations.json','model-assemblies.json'].map(n=>path.join(root,'catalogue',n)):[]));
const fingerprint = () => Object.fromEntries(sourceFiles.sort().map(file=>[path.relative(root,file).split(path.sep).join('/'),digest(file)]));
const inputs = fingerprint(), checks=[], screenshots=[]; let context, server;
const version = fs.readFileSync(path.join(root,'app/src/main/AndroidManifest.xml'),'utf8').match(/versionName="([^"]+)"/)[1];
function ffmpeg(args) { const p=cp.spawnSync(process.env.LMA_FFMPEG || 'ffmpeg',['-hide_banner','-loglevel','error','-y',...args],{cwd:root,encoding:'utf8'}); if(p.status!==0)throw Error(p.stderr); }
async function main() {
  server=http.createServer((req,res)=>{
    const file=path.resolve(assets,decodeURIComponent((req.url || '/').split('?')[0]).replace(/^\//,'') || 'index.html');
    if(!file.startsWith(assets+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8');res.end(fs.readFileSync(file));
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const origin='http://127.0.0.1:'+server.address().port;
  context=await chromium.launchPersistentContext(path.join(work,'profile'),{executablePath:process.env.LMA_BROWSER||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true,viewport:{width:375,height:812},deviceScaleFactor:1,reducedMotion:'reduce',recordVideo:{dir:path.join(work,'raw'),size:{width:375,height:812}},args:['--no-first-run','--disable-background-networking','--disable-component-update','--disk-cache-dir='+path.join(work,'cache')]});
  await context.route('**/*',route=>route.request().url().startsWith(origin+'/')?route.continue():route.abort());
  const page=context.pages()[0]||await context.newPage(); for(const extra of context.pages())if(extra!==page)await extra.close();
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/artifacts/wb_result',route=>route.fulfill({contentType:'image/png',body:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQ0AAAAASUVORK5CYII=','base64')}));
  await page.addInitScript(({version})=>{
    const f=window.__fixture={app:'LMA',version,models:[],settings:{lan:false,port:8080,source:'auto',boot:false,autoLoad:true,theme:'light',hfTokenSet:false,apiKey:'lma_UI_FIXTURE_ONLY'},api:{state:'stopped',detail:'界面测试数据'},engine:{state:'stopped',modelId:'',detail:'开发界面测试',generating:false,localUrl:'http://127.0.0.1:8080/v1'},device:{name:'UI FIXTURE · 非真机',totalMemory:8*1073741824,freeStorage:30e9,batteryExempt:false},hub:{items:[],results:[],query:'',loading:false,error:'',source:'huggingface'},chat:{sessions:[],messages:[]},logs:[],error:'',commandResults:[]};
    window.__commands=[];window.Android={getSnapshot:()=>JSON.stringify(f),theme:()=>{},copy:()=>{},openLink:()=>{},dispatch:raw=>{
      const command=JSON.parse(raw);window.__commands.push(command);setTimeout(()=>{try{
        const result=window.__handleFoundation?window.__handleFoundation(command):undefined;
        f.commandResult={requestId:command.requestId,ok:true,data:result};f.commandResults.push(f.commandResult);window.LMA.receive(f);
      }catch(error){f.commandResult={requestId:command.requestId,ok:false,error:error.message};f.commandResults.push(f.commandResult);window.LMA.receive(f);}},20);
    }};
  },{version});
  await page.goto(origin,{waitUntil:'networkidle'});
  await page.evaluate(()=>{const banner=document.createElement('div');banner.textContent='UI FIXTURE · 桌面界面录制 · 未执行 Android / 模型推理';banner.style.cssText='position:fixed;top:0;left:0;right:0;z-index:99999;padding:7px;background:#fff0c2;color:#633c00;font:10px sans-serif;text-align:center;pointer-events:none';document.body.appendChild(banner);});
  const checked=name=>{checks.push(name);console.log('PASS '+name);};
  const overflow=async(p,name)=>{assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),name);checked(name);};
  await checkScreen(page,checked,overflow,work,async(file,caption)=>{if(mode==='recovery'&&/^0[12]-/.test(file))await page.locator('.job-tools').evaluate(el=>el.scrollIntoView({block:'center'}));await page.evaluate(()=>{document.getElementById('toast').hidden=true;});await page.screenshot({path:path.join(out,file)});screenshots.push({file,caption});});
  assert.deepEqual(errors,[]);assert.deepEqual(fingerprint(),inputs);
  const video=page.video();await context.close();context=null;const raw=await video.path();
  ffmpeg(['-i',raw,'-an','-c:v','libx264','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,mode+'-ui.mp4')]);
  ffmpeg(['-i',path.join(out,mode+'-ui.mp4'),'-vf','fps=5,scale=300:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',path.join(out,mode+'-ui.gif')]);
  const files=fs.readdirSync(out).filter(n=>/\.(png|mp4|gif)$/.test(n)).sort().map(file=>({file,bytes:fs.statSync(path.join(out,file)).size,sha256:digest(path.join(out,file))}));
  fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({version,kind:'current production UI with an explicit simulated bridge',android_device:false,model_inference:false,weights_downloaded:false,browser_closed:true,browser_errors:errors,checks,screenshots,files,input_fingerprint:inputs},null,2)+'\n');
  console.log(JSON.stringify({passed:true,checks:checks.length,screenshots:screenshots.length,browser_closed:true,android_device:false,model_inference:false}));
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{if(context)await context.close();if(server)await new Promise(resolve=>server.close(resolve));});
