/* Record the shipped UI with an explicit demonstration bridge. No Android runtime. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const {chromium} = require(process.env.LMA_PLAYWRIGHT || 'playwright');
const root = path.resolve(__dirname, '..');
const assets = path.join(root, 'app/src/main/assets');
const output = path.join(root, 'docs/media');
const temporary = path.join(root, 'build/media');
fs.mkdirSync(output, {recursive:true});
fs.mkdirSync(temporary, {recursive:true});
const catalogue = JSON.parse(fs.readFileSync(path.join(assets, 'models.json'), 'utf8'));
const fixture = {
  app:'LMA', version:'0.1.2', models:catalogue.models.map(m => ({...m, installed:false, installedBytes:0, partialBytes:0, download:{}})),
  settings:{lan:false,port:8080,threads:4,context:2048,maxTokens:512,temperature:0.7,source:'auto',boot:false,autoLoad:true,reasoning:'off',theme:'light',systemPrompt:'你是一个有帮助的本地助手。请优先使用用户的语言，准确、清楚地回答。',apiKey:'lma_DEMO_NOT_A_REAL_API_KEY'},
  engine:{state:'stopped',detail:'选择并下载一个模型，开始本地运行',modelId:'',generating:false,startedAt:0,localUrl:'http://127.0.0.1:8080/v1',addresses:['http://192.0.2.20:8080/v1']},
  device:{name:'UI 演示 · 非真机',android:'9',totalMemory:8*1073741824,availableMemory:4.3*1073741824,freeStorage:51.2e9,batteryExempt:false},
  chat:{sessionId:'',sessions:[],messages:[]},logs:[],error:'',commandResults:[]
};
let server, context;
const errors = [], shots = [], chapters = [];
let recordingStarted = Date.now();
function ffmpeg(args) {
  const result = cp.spawnSync(process.env.LMA_FFMPEG || 'ffmpeg', ['-hide_banner','-loglevel','error','-y',...args], {cwd:root,encoding:'utf8'});
  if (result.status !== 0) throw new Error('FFmpeg failed: '+result.stderr);
}
async function main() {
  server = http.createServer((req,res) => {
    const name = decodeURIComponent((req.url || '/').split('?')[0]).replace(/^\//,'') || 'index.html';
    const file = path.resolve(assets,name);
    if (!file.startsWith(assets+path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {res.writeHead(404);res.end();return;}
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':'text/html; charset=utf-8');
    res.end(fs.readFileSync(file));
  });
  // This host can allocate low ephemeral ports, including Chromium's blocked 6000.
  for (let attempt=0; ; attempt++) {
    try {
      await new Promise((resolve,reject) => {
        server.once('error',reject);
        server.listen(49152+crypto.randomInt(15000),'127.0.0.1',() => {server.removeListener('error',reject);resolve();});
      });
      break;
    } catch (error) {if(error.code!=='EADDRINUSE' || attempt>=9) throw error;}
  }
  const origin = 'http://127.0.0.1:'+server.address().port;
  const edge = process.env.LMA_BROWSER || path.join(process.env['ProgramFiles(x86)'] || 'C:/Program Files (x86)','Microsoft/Edge/Application/msedge.exe');
  context = await chromium.launchPersistentContext(path.join(temporary,'browser-profile'),{
    executablePath:edge,headless:true,viewport:{width:390,height:844},deviceScaleFactor:2,
    recordVideo:{dir:path.join(temporary,'raw'),size:{width:390,height:844}},
    args:['--no-first-run','--disable-background-networking','--disable-component-update','--disk-cache-dir='+path.join(temporary,'browser-cache')]
  });
  await context.route('**/*', route => route.request().url().startsWith(origin+'/') ? route.continue() : route.abort());
  const page = context.pages()[0] || await context.newPage();
  recordingStarted = Date.now();
  for (const extra of context.pages()) if (extra !== page) await extra.close();
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(({fixture}) => {
    window.__demo = fixture;
    const emit = () => window.LMA && window.LMA.receive(window.__demo);
    let downloadTimer;
    function beginDownload(m) {
      clearInterval(downloadTimer);
      m.download = {state:'downloading',received:m.bytes*0.12,total:m.bytes,speed:8000000};
      downloadTimer = setInterval(() => {
        m.download.received=Math.min(m.bytes*0.78,m.download.received+m.bytes*0.035);emit();
      },350);
    }
    window.Android = {
      getSnapshot:() => JSON.stringify(window.__demo), theme:() => {}, copy:() => {}, openLink:() => {},
      dispatch:raw => {
        const command=JSON.parse(raw), f=window.__demo, m=f.models.find(x=>x.id===command.id);
        setTimeout(() => {
          if (command.action==='download' || command.action==='resumeDownload') beginDownload(m);
          if (command.action==='pauseDownload') {clearInterval(downloadTimer);m.download.state='paused';}
          if (command.action==='load') {
            f.engine.modelId=m.id;f.engine.state='loading';f.engine.detail='演示状态：正在加载';
            setTimeout(() => {f.engine.state='ready';f.engine.detail='UI 演示状态 · 未执行真实推理';emit();},900);
          }
          if (command.action==='saveSettings') Object.assign(f.settings,command.settings);
          if (command.action==='send') {
            f.engine.generating=true;f.chat.sessionId='demo';
            f.chat.sessions=[{id:'demo',title:command.text,modelId:f.engine.modelId,updated:Date.now()}];
            f.chat.messages.push({id:'demo-user',role:'user',content:command.text,reasoning:'',status:'done',elapsed:0,tokens:0});
            const answer={id:'demo-answer',role:'assistant',content:'',reasoning:'',status:'generating',elapsed:0,tokens:0};
            f.chat.messages.push(answer);
            const text='【界面演示文本，非模型输出】\n\n1. 下载并加载一个无审查模型。\n2. 在“服务”页复制接口地址和 API 密钥。\n3. 通过 OpenAI 兼容客户端连接。\n\n```python\nbase_url = "http://PHONE_IP:8080/v1"\n```';
            let index=0;
            const timer=setInterval(() => {
              index+=5;answer.content=text.slice(0,index);emit();
              if (index>=text.length) {clearInterval(timer);f.engine.generating=false;answer.status='done';emit();}
            },80);
          }
          if (command.action==='stopEngine') {f.engine.state='stopped';f.engine.generating=false;}
          f.commandResults.push({requestId:command.requestId,action:command.action,ok:true,error:''});emit();
        },70);
      }
    };
    window.__finishDemoDownload=() => {
      clearInterval(downloadTimer);const m=window.__demo.models.find(x=>x.id==='m08');
      m.installed=true;m.installedBytes=m.bytes;m.download={state:'done',verification:'publisher-sha256'};emit();
    };
    document.addEventListener('DOMContentLoaded',() => {
      const banner=document.createElement('div');banner.id='demo-banner';
      banner.textContent='UI DEMO / 界面演示 · 非真机 / Simulated state';
      Object.assign(banner.style,{position:'fixed',top:'0',left:'0',right:'0',height:'26px',background:'#162238',color:'#fff',font:'10px/26px system-ui',textAlign:'center',zIndex:'99999',letterSpacing:'.1px'});
      document.body.prepend(banner);document.body.style.paddingTop='26px';
      document.querySelector('.app-shell').style.height='calc(100dvh - 26px)';
    });
  },{fixture});
  await page.goto(origin+'/index.html');
  await page.waitForSelector('.model-card');
  async function pause(ms=1000) {await page.waitForTimeout(ms);}
  async function shot(name,caption) {
    await page.evaluate(() => {document.getElementById('toast').hidden=true;});
    await page.screenshot({path:path.join(output,name)});shots.push({file:name,caption});
  }
  function chapter(name) {chapters.push({name,seconds:(Date.now()-recordingStarted)/1000});console.log('Recording: '+name);}
  chapter('Uncensored model library');
  await pause(1400);await shot('01-library.png','Built-in uncensored model recommendations / 内置无审查模型推荐');
  await page.locator('[data-filter="all"]').click();await pause(700);
  await page.locator('#modelSearch').fill('Qwen');await pause(900);
  await page.locator('#modelSearch').fill('');await page.locator('[data-filter="recommended"]').click();
  await page.locator('[data-action="modelInfo"][data-id="m08"]').click();await pause(1100);
  await shot('02-model-evidence.png','Pinned publisher evidence and weight SHA256 / 作者依据及权重哈希');
  await page.keyboard.press('Escape');
  chapter('Download, pause and resume — simulated transfer');
  await page.locator('[data-action="download"][data-id="m08"]').click();await pause(1800);
  await shot('03-download.png','Simulated native download progress / 模拟原生下载状态');
  await page.locator('[data-action="pauseDownload"][data-id="m08"]').click();await pause(1100);
  await page.locator('[data-action="resumeDownload"][data-id="m08"]').click();await pause(1000);
  await page.evaluate(() => window.__finishDemoDownload());
  await page.locator('[data-action="load"][data-id="m08"]').click();await pause(1600);
  chapter('Chat UI — scripted demonstration text');
  await page.locator('.nav-item[data-tab="chat"]').click();await pause(700);
  await page.locator('#chatInput').pressSequentially('请用三步说明如何连接 LMA 接口。',{delay:65});
  await pause(500);await page.locator('#sendButton').click();
  await page.waitForFunction(() => window.__demo.chat.messages.some(x=>x.role==='assistant' && x.status==='done'));
  await pause(800);await shot('04-chat.png','Scripted text rendered through real chat UI; no model run / 对话界面脚本文本展示');
  chapter('Local API and LAN setting');
  await page.locator('.nav-item[data-tab="server"]').click();await pause(1000);
  await page.locator('#lanToggle').check();await pause(1100);
  await shot('05-api.png','OpenAI-compatible API controls; example-only IP and key / API 服务界面，示例地址与密钥');
  await page.locator('[data-action="copyExample"]').click();await pause(900);
  chapter('Settings and dark theme');
  await page.locator('.nav-item[data-tab="settings"]').click();await pause(700);
  await page.locator('select[name="threads"]').scrollIntoViewIfNeeded();await pause(900);
  await page.evaluate(() => {
    const section=document.getElementById('page-settings'), panel=document.querySelectorAll('#settingsForm .panel')[1];
    section.scrollTop+=panel.getBoundingClientRect().top-section.getBoundingClientRect().top-12;
  });
  await pause(650);
  await shot('06-settings.png','CPU, context and output settings / CPU、上下文及输出参数');
  await page.locator('select[name="theme"]').selectOption('dark');
  await page.locator('#settingsForm button[type="submit"]').click();await pause(1100);
  await page.locator('.nav-item[data-tab="server"]').click();
  await page.evaluate(() => document.getElementById('page-server').scrollTop=0);await pause(1100);
  await shot('07-dark.png','Dark theme API service / 深色主题服务页');
  const video=page.video();
  await context.close();context=null;
  const raw=await video.path();
  ffmpeg(['-i',raw,'-an','-c:v','libx264','-crf','22','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart',path.join(output,'lma-walkthrough.mp4')]);
  ffmpeg(['-i',path.join(output,'lma-walkthrough.mp4'),'-vf','fps=8,scale=320:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',path.join(output,'lma-walkthrough.gif')]);
  const probe=cp.spawnSync(process.env.LMA_FFPROBE || 'ffprobe',['-v','error','-show_entries','format=duration:stream=width,height,codec_name','-of','json',path.join(output,'lma-walkthrough.mp4')],{encoding:'utf8'});
  if(probe.status!==0) throw new Error('FFprobe failed');
  const duration=Number(JSON.parse(probe.stdout).format.duration);
  ffmpeg(['-ss',String(Math.max(0,duration-9)),'-i',path.join(output,'lma-walkthrough.mp4'),'-t','9','-vf','fps=8,scale=320:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',path.join(output,'lma-api-theme.gif')]);
  if(errors.length) throw new Error('Browser errors: '+JSON.stringify(errors));
  const files=fs.readdirSync(output).filter(name=>/\.(png|mp4|gif)$/.test(name)).sort().map(name => {
    const bytes=fs.readFileSync(path.join(output,name));return {file:name,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
  });
  const inputs=Object.fromEntries(fs.readdirSync(assets,{recursive:true}).map(name=>path.join(assets,name)).filter(file=>fs.statSync(file).isFile()).concat(__filename).sort().map(file=>[path.relative(root,file).split(path.sep).join('/'),crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')]));
  fs.writeFileSync(path.join(output,'manifest.json'),JSON.stringify({version:'0.1.2',captured_at:new Date().toISOString(),kind:'actual shipped HTML/CSS/JS with explicit simulated native bridge',android_device:false,model_inference:false,downloads_simulated:true,scripted_chat:true,api_key:'demonstration placeholder only',viewport:{width:390,height:844},screenshots:shots,video:JSON.parse(probe.stdout),chapter_clock:'Approximate video offsets from recording page creation',chapters,files,input_fingerprint:inputs,browser_errors:errors,browser_closed:true},null,2)+'\n');
  console.log(JSON.stringify({screenshots:shots.length,files:files.length,duration,android_device:false,model_inference:false}));
}
main().catch(error=>{console.error(error);process.exitCode=1;}).finally(async()=>{
  if(context) await context.close();
  if(server) await new Promise(resolve=>server.close(resolve));
});
