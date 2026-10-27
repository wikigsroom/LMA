/* Record the actual development UI with a visible fixture banner, never phone inference. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const {chromium} = require(process.env.LMA_PLAYWRIGHT || 'playwright');
const {installFixture} = require('../tests/foundation-ui.cjs');
const root = path.resolve(__dirname, '..');
const assets = path.join(root, 'app/src/main/assets');
const out = path.join(root, 'docs/media/development');
const work = path.join(root, 'build/foundation-media');
fs.mkdirSync(out, {recursive: true}); fs.mkdirSync(work, {recursive: true});
const version = fs.readFileSync(path.join(root, 'app/src/main/AndroidManifest.xml'), 'utf8').match(/android:versionName="([^"]+)"/)[1];
let context, server;
const errors = [], screenshots = [];
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function ffmpeg(args) {
  const result = cp.spawnSync(process.env.LMA_FFMPEG || 'ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', ...args], {cwd: root, encoding: 'utf8'});
  if (result.status !== 0) throw new Error(result.stderr || 'FFmpeg failed');
}
async function main() {
  server = http.createServer((req, res) => {
    const file = path.resolve(assets, decodeURIComponent((req.url || '/').split('?')[0]).replace(/^\//, '') || 'index.html');
    if (!file.startsWith(assets + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {res.writeHead(404); res.end(); return;}
    res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript; charset=utf-8' : file.endsWith('.css') ? 'text/css; charset=utf-8' : 'text/html; charset=utf-8'); res.end(fs.readFileSync(file));
  });
  for (let attempt = 0; ; attempt++) {
    try { await new Promise((resolve, reject) => {server.once('error', reject); server.listen(49152 + crypto.randomInt(15000), '127.0.0.1', () => {server.removeListener('error', reject); resolve();});}); break; }
    catch (error) {if (error.code !== 'EADDRINUSE' || attempt >= 9) throw error;}
  }
  const origin = 'http://127.0.0.1:' + server.address().port;
  context = await chromium.launchPersistentContext(path.join(work, 'profile'), {
    executablePath: process.env.LMA_BROWSER || path.join(process.env['ProgramFiles(x86)'] || 'C:/Program Files (x86)', 'Microsoft/Edge/Application/msedge.exe'), headless: true,
    viewport: {width: 390, height: 844}, deviceScaleFactor: 1, reducedMotion: 'reduce',
    recordVideo: {dir: path.join(work, 'raw'), size: {width: 390, height: 844}},
    args: ['--no-first-run', '--disable-background-networking', '--disable-component-update', '--disk-cache-dir=' + path.join(work, 'cache')]
  });
  await context.route('**/*', route => route.request().url().startsWith(origin + '/') ? route.continue() : route.abort());
  const page = context.pages()[0] || await context.newPage();
  for (const extra of context.pages()) if (extra !== page) await extra.close();
  page.on('pageerror', error => errors.push(error.message));
  const catalogue = JSON.parse(fs.readFileSync(path.join(assets, 'models.json'), 'utf8'));
  await page.addInitScript(({catalogue, version}) => {
    window.__fixture = {
      app: 'LMA', version, models: catalogue.models.map(m => ({...m, installed: false, download: {}})),
      settings: {lan: false, port: 8080, source: 'auto', boot: false, autoLoad: true, theme: 'light', hfTokenSet: false, apiKey: 'lma_UI_FIXTURE_ONLY'},
      engine: {state: 'stopped', modelId: '', detail: '开发界面演示 · 未运行模型', generating: false, localUrl: 'http://127.0.0.1:8080/v1'},
      device: {name: '界面测试数据 · 非真机', totalMemory: 8 * 1073741824, freeStorage: 30e9, batteryExempt: false},
      chat: {sessionId: '', sessions: [], messages: []}, commandResults: [], logs: [], error: ''
    };
    window.Android = {
      getSnapshot: () => JSON.stringify(window.__fixture), copy: () => {}, theme: () => {},
      dispatch: raw => {
        const command = JSON.parse(raw);
        setTimeout(() => {
          const data = window.__handleFoundation && window.__handleFoundation(command);
          window.__fixture.commandResults.push({requestId: command.requestId, action: command.action, ok: true, error: '', data});
          window.LMA.receive(window.__fixture);
        }, 100);
      }
    };
    document.addEventListener('DOMContentLoaded', () => {
      const banner = document.createElement('div'); banner.textContent = '开发界面演示 / UI FIXTURE · 非真机 · 非模型输出';
      Object.assign(banner.style, {position: 'fixed', top: '0', left: '0', right: '0', height: '26px', zIndex: '99999', color: 'white', background: '#162238', textAlign: 'center', font: '10px/26px system-ui'});
      document.body.prepend(banner); document.body.style.paddingTop = '26px'; document.querySelector('.app-shell').style.height = 'calc(100dvh - 26px)';
    });
  }, {catalogue, version});
  await page.goto(origin + '/index.html'); await page.waitForSelector('.model-card');
  async function shot(file, caption) {await page.waitForTimeout(1000); await page.evaluate(() => {document.getElementById('toast').hidden = true;}); await page.screenshot({path: path.join(out, file)}); screenshots.push({file, caption});}
  await shot('01-recommended.png', 'Preserved recommendations and independent output filters / 原推荐与功能筛选');
  await page.evaluate(installFixture);
  await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="image"]').click();
  await shot('02-local-tags.png', 'Flat Local model list with output, engine and installation tags / 平级本地模型与独立标签');
  await page.locator('[data-action="bundleInfo"]').first().click();
  await shot('03-bundle-plan.png', 'Explicit component plan before any transfer / 开始传输前展示完整组件');
  await page.locator('[data-action="downloadBundle"]').click(); await page.waitForSelector('[data-action="pauseBundle"]'); await page.waitForTimeout(700);
  await page.locator('[data-action="pauseBundle"]').click(); await page.waitForTimeout(500);
  await page.evaluate(() => {window.__fixture.bundles[0].installed = true; delete window.__fixture.bundles[0].transfer; window.LMA.receive(window.__fixture);});
  await page.locator('[data-action="bundleInfo"]').first().click(); await page.locator('[data-action="bundleSettings"]').click();
  await page.locator('[data-bundle-field="width"]').fill('99999'); await page.locator('[data-bundle-field="width"]').blur(); await page.locator('#bundleShape').selectOption('1');
  await shot('04-model-settings.png', 'Per-recipe editable parameters and compiled shape selection / 模型独立参数与联合尺寸');
  await page.locator('#bundleSettingsForm [type="submit"]').click(); await page.waitForFunction(() => document.getElementById('modalBackdrop').hidden);
  await page.locator('[data-action="bundleUse"]').click(); await page.locator('#localTaskForm [name="prompt"]').fill('一座山间小屋，清晨薄雾。此处仅演示输入表单。');
  await page.locator('#localTaskForm [name="allowUnmeasured"]').check();
  await shot('05-task-form.png', 'User-selected local task and explicit unmeasured-device choice / 用户选择任务与未测配方确认');
  await page.locator('#localTaskForm [type="submit"]').click(); await page.waitForSelector('#page-tasks.active .job-card');
  await page.evaluate(() => {Object.assign(window.__fixture.jobs[0], {state: 'running', stage: 'sampling', progress: 0.5}); window.LMA.receive(window.__fixture);});
  await shot('06-queue-results.png', 'Simulated queue progress and local result-library entry / 明确模拟的队列进度与结果库');
  await page.locator('[data-action="cancelTask"]').click(); await page.waitForSelector('[data-action="retryTask"]');
  await shot('07-cancelled.png', 'Cancellation preserves a retriable record; no generated artifact claimed / 取消后保留任务，不伪造生成结果');
  if (errors.length) throw new Error(JSON.stringify(errors));
  const video = page.video(); await context.close(); context = null;
  const raw = await video.path();
  ffmpeg(['-i', raw, '-an', '-c:v', 'libx264', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path.join(out, 'foundation-ui.mp4')]);
  ffmpeg(['-i', path.join(out, 'foundation-ui.mp4'), '-vf', 'fps=6,scale=320:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3', '-loop', '0', path.join(out, 'foundation-ui.gif')]);
  const files = fs.readdirSync(out).filter(n => /\.(png|gif|mp4)$/.test(n)).sort().map(file => ({file, bytes: fs.statSync(path.join(out, file)).size, sha256: digest(path.join(out, file))}));
  const sourceFiles = fs.readdirSync(assets, {recursive: true}).map(n => path.join(assets, n)).filter(p => fs.statSync(p).isFile()).concat(__filename, path.join(root, 'tests/foundation-ui.cjs'));
  const input_fingerprint = Object.fromEntries(sourceFiles.sort().map(file => [path.relative(root, file).split(path.sep).join('/'), digest(file)]));
  fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify({version, kind: 'development UI with explicit simulated native bridge', android_device: false, model_inference: false, weights_downloaded: false, browser_closed: true, browser_errors: errors, screenshots, files, input_fingerprint}, null, 2) + '\n');
  console.log(JSON.stringify({version, screenshots: screenshots.length, files: files.length, android_device: false, model_inference: false, browser_closed: true}));
}
main().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {
  if (context) await context.close();
  if (server) await new Promise(resolve => server.close(resolve));
});
