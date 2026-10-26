/* Browser UI checks with an explicit test-only native bridge. No Android emulator. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');
const http = require('node:http');
const {chromium} = require(process.env.LMA_PLAYWRIGHT || 'playwright');
const root = path.resolve(__dirname, '..');
const assets = path.join(root, 'app/src/main/assets');
const output = path.join(root, 'build/ui-qa');
fs.mkdirSync(output, {recursive: true});
if (fs.existsSync(path.join(output, 'results.json'))) fs.unlinkSync(path.join(output, 'results.json'));
function inputFingerprint() {
  const files = fs.readdirSync(assets, {recursive: true}).map(name => path.join(assets, name)).filter(file => fs.statSync(file).isFile()).concat(__filename);
  return Object.fromEntries(files.sort().map(file => [path.relative(root, file).split(path.sep).join('/'), crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')]));
}
const verifiedInputs = inputFingerprint();
const catalogue = JSON.parse(fs.readFileSync(path.join(assets, 'models.json'), 'utf8'));
const checks = [], errors = [];
let context, server;
function checked(name) { checks.push(name); console.log('PASS ' + name); }
const fixture = {
  app: 'LMA', version: '0.1.2', models: catalogue.models.map(m => ({...m, installed: false, installedBytes: 0, partialBytes: 0, download: {}})),
  settings: {lan: false, port: 8080, threads: 4, context: 2048, maxTokens: 512, temperature: 0.7, source: 'auto', boot: false, autoLoad: true, reasoning: 'off', theme: 'light', systemPrompt: '你是一个有帮助的本地助手。', apiKey: 'lma_TEST_ONLY_NOT_A_REAL_KEY'},
  engine: {state: 'stopped', detail: '选择并下载一个模型，开始本地运行', modelId: '', generating: false, startedAt: 0, localUrl: 'http://127.0.0.1:8080/v1', addresses: ['http://192.168.1.20:8080/v1']},
  device: {name: 'nubia Z20 · UI 测试数据', android: '9', totalMemory: 8 * 1073741824, availableMemory: 4.3 * 1073741824, freeStorage: 51.2 * 1e9, batteryExempt: false},
  chat: {sessionId: '', sessions: [], messages: []}, logs: [], error: '', commandResults: []
};
async function setState(page, mutation) { await page.evaluate(mutation); await page.evaluate(() => window.LMA.receive(window.__fixture)); }
async function checkOverflow(page, name) {
  const overflow = await page.evaluate(() => {
    const active = document.querySelector('.page.active');
    return {document: document.documentElement.scrollWidth - innerWidth, page: active.scrollWidth - active.clientWidth};
  });
  assert(overflow.document <= 1 && overflow.page <= 1, name + ': horizontal overflow ' + JSON.stringify(overflow)); checked(name);
}
async function main() {
  server = http.createServer((req, res) => {
    const name = decodeURIComponent((req.url || '/').split('?')[0]).replace(/^\//, '') || 'index.html';
    const file = path.resolve(assets, name);
    if (!file.startsWith(assets + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); res.end(); return; }
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript; charset=utf-8' : file.endsWith('.css') ? 'text/css; charset=utf-8' : 'text/html; charset=utf-8');
    res.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port;
  const edge = process.env.LMA_BROWSER || path.join(process.env['ProgramFiles(x86)'] || 'C:/Program Files (x86)', 'Microsoft/Edge/Application/msedge.exe');
  context = await chromium.launchPersistentContext(path.join(root, 'build/ui-browser-profile'), {
    executablePath: edge, headless: true, viewport: {width: 375, height: 812}, deviceScaleFactor: 1,
    reducedMotion: 'reduce', args: ['--no-first-run', '--disable-background-networking', '--disable-component-update', '--disk-cache-dir=' + path.join(root, 'build/ui-browser-cache')]
  });
  await context.route('**/*', route => route.request().url().startsWith(origin + '/') ? route.continue() : route.abort());
  const page = context.pages()[0] || await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(({fixture}) => {
    window.__fixture = fixture; window.__commands = []; window.__copied = ''; window.__pwned = false;
    window.Android = {
      getSnapshot: () => JSON.stringify(window.__fixture),
      copy: text => { window.__copied = text; }, openLink: url => { window.__openedUrl = url; },
      dispatch: raw => {
        const command = JSON.parse(raw); window.__commands.push(command);
        setTimeout(() => {
          const f = window.__fixture, m = f.models.find(x => x.id === command.id);
          if (window.__rejectNextAction === command.action) {
            window.__rejectNextAction = null; f.error = '原生测试端拒绝了这次操作';
            f.commandResults.push({requestId: command.requestId, action: command.action, ok: false, error: f.error});
            window.LMA.receive(f); return;
          }
          if (command.action === 'download' || command.action === 'resumeDownload') m.download = {state: 'downloading', received: 100000000, total: m.bytes, speed: 8000000};
          if (command.action === 'pauseDownload') m.download.state = 'paused';
          if (command.action === 'load') { f.engine.modelId = m.id; f.engine.state = 'ready'; f.engine.detail = '模型已就绪，可以对话或连接 API'; }
          if (command.action === 'stopEngine') { f.engine.state = 'stopped'; f.engine.generating = false; }
          if (command.action === 'saveSettings') { Object.assign(f.settings, command.settings); f.engine.localUrl = 'http://127.0.0.1:' + f.settings.port + '/v1'; }
          if (command.action === 'send') {
            f.engine.generating = true; f.chat.sessionId = 'test-session';
            f.chat.sessions = [{id: 'test-session', title: command.text, modelId: f.engine.modelId, updated: Date.now()}];
            f.chat.messages.push({id: 'user-1', role: 'user', content: command.text, reasoning: '', status: 'done', error: '', elapsed: 0, tokens: 0});
            f.chat.messages.push({id: 'answer-1', role: 'assistant', content: '', reasoning: '', status: 'generating', error: '', elapsed: 0, tokens: 0});
            if (window.__instantReply) { f.engine.generating = false; f.chat.messages[f.chat.messages.length - 1].status = 'done'; }
          }
          if (command.action === 'cancelChat') { f.engine.generating = false; const last = f.chat.messages[f.chat.messages.length - 1]; if (last) last.status = 'stopped'; }
          if (command.action === 'deleteSession') { f.chat.sessions = []; f.chat.messages = []; f.chat.sessionId = ''; }
          if (command.action === 'dismissError') f.error = '';
          if (command.action === 'addModel') f.models.push({id: 'custom_test', name: command.name, family: '自定义', description: '测试模型', installed: false, tier: 'custom', quant: 'GGUF', bytes: 0, tags: [], url: command.url, download: {state: 'queued'}});
          f.commandResults.push({requestId: command.requestId, action: command.action, ok: true, error: ''});
          f.commandResults = f.commandResults.slice(-24);
          window.LMA.receive(f);
        }, 30);
      }
    };
  }, {fixture});
  await page.goto(origin + '/index.html');
  await page.waitForSelector('.model-card');
  assert.equal(await page.locator('.model-card').count(), 3); checked('Initial curated recommendations');
  await checkOverflow(page, '375px model library layout');
  await page.screenshot({path: path.join(output, '01-models-phone.png')});
  await page.locator('[data-filter="all"]').click(); assert.equal(await page.locator('.model-card').count(), 14); checked('Full model catalogue');
  assert.equal(await page.locator('.model-tags .tag').filter({hasText: /^无审查$/}).count(), 14); checked('Every built-in model visibly declares uncensored selection');
  await page.locator('#modelSearch').fill('dolphin'); assert((await page.locator('.model-card').count()) >= 1); checked('Model search');
  await page.locator('#modelSearch').fill(''); await page.locator('[data-filter="recommended"]').click();
  await page.locator('[data-action="download"][data-id="m08"]').click();
  await page.waitForSelector('[data-action="pauseDownload"][data-id="m08"]');
  assert(await page.locator('[data-model="m08"] .progress-track').getAttribute('aria-valuenow') !== '0'); checked('Download progress from native bridge');
  await page.locator('[data-action="pauseDownload"][data-id="m08"]').click();
  await page.waitForSelector('[data-action="resumeDownload"][data-id="m08"]'); checked('Pause and resume actions');
  await page.locator('[data-action="resumeDownload"][data-id="m08"]').click();
  await setState(page, () => { const m = window.__fixture.models[0]; m.installed = true; m.installedBytes = m.bytes; m.download = {state: 'done', verification: 'publisher-sha256'}; });
  await page.locator('[data-action="load"][data-id="m08"]').click();
  await page.waitForSelector('.runtime-dot.ready'); checked('Select downloaded model');
  await page.locator('.nav-item[data-tab="chat"]').click();
  await page.locator('#chatInput').fill('请介绍本地模型的使用方式。'); await page.locator('#sendButton').click();
  await page.waitForSelector('#sendButton.stop');
  await page.waitForFunction(() => document.getElementById('chatInput').value === '');
  await setState(page, () => { const a = window.__fixture.chat.messages[1]; a.content = '模型在你的手机上运行。\n\n**三个步骤**\n1. 选择并下载模型\n2. 点击加载\n3. 开始对话或连接 API\n\n```python\nprint("Hello LMA")\n```'; a.reasoning = '检查本地模型的可用状态。'; a.elapsed = 12400; a.tokens = 62; });
  await page.locator('.reasoning summary').click();
  await setState(page, () => { window.__fixture.chat.messages[1].content += '\n对话与文件均保存在当前设备。'; });
  assert(await page.locator('.reasoning').getAttribute('open') !== null); checked('Reasoning disclosure survives streaming updates');
  await page.locator('[data-action="copyCode"]').click(); assert.equal(await page.evaluate(() => window.__copied), 'print("Hello LMA")\n'); checked('Copy code without markdown wrappers');
  await page.locator('#sendButton').click(); await page.waitForFunction(() => !window.__fixture.engine.generating);
  assert.equal(await page.locator('.message-footer').last().textContent(), '12.4 秒 · 62 tokens · 已停止'); checked('Cancel retains partial reply');
  await checkOverflow(page, '375px chat layout'); await page.screenshot({path: path.join(output, '02-chat-phone.png')});
  await page.evaluate(() => { window.__instantReply = true; window.__rejectNextAction = 'send'; });
  await page.locator('#chatInput').fill('失败后保留这条草稿'); await page.locator('#sendButton').click();
  await page.waitForFunction(() => window.__fixture.commandResults.some(x => x.action === 'send' && !x.ok));
  assert.equal(await page.locator('#chatInput').inputValue(), '失败后保留这条草稿'); checked('Rejected native send preserves draft');
  await page.evaluate(() => { const n = window.__commands.filter(x => x.action === 'send').length; window.__sendCount = n; document.getElementById('sendButton').click(); document.getElementById('sendButton').click(); });
  await page.waitForFunction(() => document.getElementById('chatInput').value === '');
  assert.equal(await page.evaluate(() => window.__commands.filter(x => x.action === 'send').length - window.__sendCount), 1); checked('Fast completed reply clears draft without duplicate send');
  await page.locator('.nav-item[data-tab="server"]').click();
  await page.locator('#lanToggle').check(); await page.waitForFunction(() => document.getElementById('apiUrl').textContent.includes('192.168.1.20'));
  await page.locator('[data-action="copyExample"]').click();
  const curl = await page.evaluate(() => window.__copied); assert(curl.includes('/v1/chat/completions') && curl.includes('Bearer lma_TEST_ONLY')); checked('LAN endpoint and authenticated API example');
  await checkOverflow(page, '375px server layout'); await page.screenshot({path: path.join(output, '03-server-phone.png')});
  await page.locator('.nav-item[data-tab="settings"]').click();
  await page.locator('select[name="threads"]').selectOption('3');
  await page.evaluate(() => window.LMA.receive(window.__fixture)); assert.equal(await page.locator('select[name="threads"]').inputValue(), '3'); checked('Unsaved settings survive native updates');
  await page.locator('select[name="reasoning"]').selectOption('auto'); await page.locator('select[name="theme"]').selectOption('dark');
  await page.locator('#settingsForm button[type="submit"]').click();
  await page.waitForFunction(() => document.documentElement.dataset.theme === 'dark');
  assert.equal(await page.locator('#settingsHint').textContent(), '设置已保存'); checked('Persist settings and dark theme');
  await page.locator('select[name="threads"]').selectOption('2');
  await page.evaluate(() => { window.__rejectNextAction = 'saveSettings'; });
  await page.locator('#settingsForm button[type="submit"]').click();
  await page.waitForFunction(() => document.getElementById('settingsHint').textContent.includes('原生测试端拒绝'));
  assert.equal(await page.locator('select[name="threads"]').inputValue(), '2'); checked('Rejected settings remain editable with matching command error');
  await page.locator('select[name="source"]').selectOption('auto');
  await page.locator('#settingsForm button[type="submit"]').click();
  await page.waitForFunction(() => document.getElementById('settingsHint').textContent === '设置已保存');
  assert.equal(await page.evaluate(() => window.__fixture.settings.source), 'auto'); checked('Unrelated earlier error cannot fail successful settings acknowledgement');
  await page.locator('[data-action="about"]').click(); await page.locator('[data-action="notices"]').click();
  assert.equal(await page.locator('.license-notice').count(), 12); await page.keyboard.press('Escape'); checked('Bundled third-party license reader');
  await page.locator('.nav-item[data-tab="server"]').click(); await page.evaluate(() => { document.getElementById('page-server').scrollTop = 0; document.getElementById('toast').hidden = true; }); await page.screenshot({path: path.join(output, '04-server-dark.png')});
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('#addModelButton').click();
  await page.locator('[data-action="addUrl"]').click();
  await page.locator('#customModelForm input[name="name"]').fill('自己的 GGUF');
  await page.locator('#customModelForm input[name="url"]').fill('https://example.com/model.gguf');
  await page.locator('#customModelForm button[type="submit"]').click();
  await page.waitForSelector('[data-model="custom_test"]'); checked('Custom HTTPS model entry');
  assert((await page.locator('[data-model="custom_test"] .model-tags').textContent()).includes('属性未核对'));
  await page.locator('[data-action="modelInfo"][data-id="m08"]').click();
  assert((await page.locator('.model-info').textContent()).includes('Abliterated 去拒答'));
  await page.locator('[data-action="uncensoredSource"]').click();
  assert.equal(await page.evaluate(() => window.__openedUrl), catalogue.models.find(m => m.id === 'm08').uncensored.evidenceUrl); checked('Original publisher evidence opens and custom imports stay unclassified');
  assert.equal(await page.locator('#modal').getAttribute('role'), 'dialog'); await page.keyboard.press('Escape');
  assert(await page.locator('#modalBackdrop').isHidden()); checked('Accessible modal and Escape close');
  await setState(page, () => { window.__fixture.models[0].name = '<img src=x onerror="window.__pwned=true">'; window.__fixture.chat.messages[1].content = '<script>window.__pwned=true</script>\n```html\n<img src=x onerror="window.__pwned=true">\n```'; });
  assert.equal(await page.locator('#modelList img').count(), 0);
  await page.locator('.nav-item[data-tab="chat"]').click(); assert.equal(await page.locator('#messages script, #messages img').count(), 0);
  assert.equal(await page.evaluate(() => window.__pwned), false); checked('Model and message HTML remain inert');
  await page.locator('[data-action="history"]').click(); await page.locator('[data-action="deleteSession"]').click();
  await page.locator('[data-action="confirmed"]').click(); await page.waitForSelector('.chat-empty'); checked('Delete persistent chat via native action');
  await setState(page, () => { window.__fixture.models[0].name = 'Qwen 3 · 1.7B Abliterated'; window.__fixture.settings.theme = 'light'; });
  await page.locator('.nav-item[data-tab="models"]').click();
  await page.setViewportSize({width: 1024, height: 768}); await checkOverflow(page, 'Tablet library layout');
  await page.screenshot({path: path.join(output, '05-tablet.png')});
  await page.setViewportSize({width: 812, height: 375}); await page.locator('.nav-item[data-tab="server"]').click();
  await checkOverflow(page, 'Short landscape server layout'); await page.screenshot({path: path.join(output, '06-landscape.png')});
  await page.setViewportSize({width: 320, height: 720}); await page.locator('.nav-item[data-tab="models"]').click();
  await checkOverflow(page, '320px narrow phone layout');
  await page.setViewportSize({width: 375, height: 812});
  await page.evaluate(() => { const fonts = Array.from(document.querySelectorAll('body *')).map(el => [el, parseFloat(getComputedStyle(el).fontSize)]); fonts.forEach(([el, size]) => { if (size) el.style.fontSize = size * 1.5 + 'px'; }); document.getElementById('page-models').scrollTop = 0; document.getElementById('toast').hidden = true; });
  await checkOverflow(page, '150 percent text scale'); await page.screenshot({path: path.join(output, '07-text-scale.png')});
  assert.deepEqual(errors, []); checked('No browser JavaScript exceptions');
}
main().then(() => {
  assert.deepEqual(inputFingerprint(), verifiedInputs, 'UI inputs changed while testing');
  fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify({passed: checks.length, checks, errors, bridge: 'test fixture only', physicalDevice: false, emulatorUsed: false, input_fingerprint: verifiedInputs}, null, 2) + '\n');
}).catch(error => { console.error(error); fs.writeFileSync(path.join(output, 'failure.txt'), String(error.stack)); process.exitCode = 1; }).finally(async () => {
  if (context) await context.close(); // Closes every test tab and the browser process.
  if (server) await new Promise(resolve => server.close(resolve));
});
