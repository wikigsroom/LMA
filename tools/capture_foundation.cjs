/* Record the actual development UI with a visible fixture banner, never phone inference. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const {chromium} = require(process.env.LMA_PLAYWRIGHT || 'playwright');
const {installFixture, installSpeechFixture, installAdapterFixture} = require('../tests/foundation-ui.cjs');
const recipeUI = require('../tests/recipes-ui.cjs');
const versionUI = require('../tests/versions-ui.cjs');
const textUI = require('../tests/text-ui.cjs');
const {hubFixture, installHubBridge} = require('../tests/hub-fixture.cjs');
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
      api: {state: 'stopped', detail: '接口尚未启动', textRequestActive: false},
      engine: {state: 'stopped', modelId: '', detail: '开发界面演示 · 未运行模型', generating: false, localUrl: 'http://127.0.0.1:8080/v1'},
      device: {name: '界面测试数据 · 非真机', totalMemory: 8 * 1073741824, freeStorage: 30e9, batteryExempt: false},
      chat: {sessionId: '', sessions: [], messages: []}, commandResults: [], logs: [], error: ''
    };
    window.Android = {
      getSnapshot: () => JSON.stringify(window.__fixture), copy: () => {}, theme: () => {},
      dispatch: raw => {
        const command = JSON.parse(raw);
        setTimeout(() => {
          if (command.action === 'startApi') window.__fixture.api.state = 'ready';
          if (command.action === 'stopApi') window.__fixture.api.state = 'stopped';
          if (window.__handleHub) window.__handleHub(command);
          const recipeData = window.__handleRecipe && window.__handleRecipe(command);
          const data = recipeData === undefined && window.__handleFoundation ? window.__handleFoundation(command) : recipeData;
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
  await page.locator('.nav-item[data-tab="server"]').click(); await page.locator('#serverToggle').click();
  await page.waitForFunction(() => document.getElementById('serverStatePill').textContent === '运行中');
  await shot('08-zero-model-api.png', 'API controls independent of model installation / 零模型状态独立启动接口，界面夹具');
  await page.locator('.nav-item[data-tab="models"]').click();
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
  const speech = JSON.parse(fs.readFileSync(path.join(assets, 'model-bundles.json'), 'utf8')).bundles.find(b => b.pipeline === 'kokoro');
  await page.evaluate(installSpeechFixture, speech);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="audio"]').click();
  await page.locator('[data-action="bundleUse"]').click();
  await page.locator('#localTaskForm [name="prompt"]').fill('Hello world. This screen demonstrates local speech settings only.');
  await page.locator('.task-parameters summary').click();
  await shot('09-tts-form.png', 'Speech-specific text, editable voice/rate controls; explicit UI fixture without audio / 语音专用表单，非实际语音输出');
  await page.locator('#localTaskForm [data-action="closeModal"]').click();
  await page.evaluate(installAdapterFixture);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-task="image"]').click();
  await page.locator('[data-bundle="ui_lora_sd15"] [data-action="bundleUse"]').click();
  await shot('10-lora-pairing.png', 'User explicitly selects an installed compatible base for a peer LoRA / 平级 LoRA 自主选择兼容基础模型');
  await page.locator('#adapterPairForm [type="submit"]').click();
  await page.locator('#localTaskForm [name="prompt"]').fill('一座山间小屋。仅演示用户选择基础模型与 LoRA，没有模型输出。');
  await page.locator('[data-adapter-scale="ui_lora_sd15"]').fill('1'); await page.locator('[data-adapter-scale="ui_lora_sd15"]').blur();
  await shot('11-lora-form.png', 'Explicit adapter and editable strength in a bounded local task form; UI fixture only / 自选适配器与独立强度，不代表模型输出');
  await page.locator('#modal [data-action="closeModal"]').first().click();
  await page.evaluate(hub => { window.__fixture.hub = hub; }, hubFixture);
  await page.evaluate(installHubBridge, {stateKey: '__fixture'});
  const templates = JSON.parse(fs.readFileSync(path.join(assets, 'recipe-templates.json'), 'utf8')).templates;
  await page.evaluate(recipeUI.installFixture, templates);
  await recipeUI.openRecipe(page); await recipeUI.selectTemplate(page, 'kokoro_en_cpu_v1');
  await recipeUI.bind(page, 'model', 'model.onnx');
  await recipeUI.bind(page, 'voices', 'voices.bin', 'fixture/voices');
  await page.locator('[data-action="recipePick"][data-role="tokens"]').click();
  await page.locator('#recipeRepository').fill('fixture/model'); await page.locator('[data-action="recipeLookup"]').click();
  await page.waitForSelector('[data-action="recipeBind"][data-path="tokens.txt"]');
  await shot('13-hf-component-files.png', 'Explicit role-specific HF file selection with frozen revisions and Git blob integrity; UI fixture only / 自选组件，不下载或执行模型');
  await page.locator('[data-action="recipeBind"][data-path="tokens.txt"]').click(); await page.waitForSelector('#recipeTemplate');
  await shot('12-hf-components.png', 'User-selected multi-component recipe with separately disclosed fixed dependencies; UI fixture only / 配方登记与下载分开');
  await page.locator('[data-action="recipeDeclare"]').scrollIntoViewIfNeeded();
  await page.waitForTimeout(800); await page.locator('[data-action="recipeDeclare"]').click();
  await page.waitForSelector('[data-action="downloadBundle"][data-id="ui_hf_recipe"]');
  await shot('14-hf-download-plan.png', 'Registration opens the chosen bundle plan without downloading; UI fixture only / 登记后独立确认下载与全部依赖');
  await page.locator('#modal [data-action="closeModal"]').first().click();
  await recipeUI.openRecipe(page); await recipeUI.selectTemplate(page, 'moss_nano_cpu_v1');
  for (const [role, file] of [['manifest', 'browser_poc_manifest.json'], ['tts_meta', 'tts_browser_onnx_meta.json'], ['codec_meta', 'codec_browser_onnx_meta.json'], ['text_tokenizer', 'tokenizer.model'], ['tts_prefill', 'moss_tts_prefill.onnx'], ['tts_decode', 'moss_tts_decode_step.onnx'], ['tts_local', 'moss_tts_local_fixed_sampled_frame.onnx'], ['codec_decode', 'moss_audio_tokenizer_decode_full.onnx'], ['tts_data_1', 'moss_tts_global_shared.data'], ['tts_data_2', 'moss_tts_local_shared.data'], ['codec_data_1', 'codec_weights.data']]) await recipeUI.bind(page, role, file, 'fixture/model');
  await page.locator('#recipeTemplate').scrollIntoViewIfNeeded();
  await shot('15-moss-nano-recipe.png', 'MOSS Nano audio recipe and user-selected tokenizer/metadata/codec; UI fixture only / Nano 组件由用户选择，未下载或推理');
  await page.locator('[data-action="recipePick"][data-role="codec_data_1"]').scrollIntoViewIfNeeded();
  await shot('16-moss-external-data.png', 'Explicit external ONNX weight data, separate from App foundation; UI fixture only / 外置权重独立选择，不随 App 更新');
  await page.keyboard.press('Escape'); await page.evaluate(installFixture); await page.evaluate(versionUI.installFixture);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="any"]').click();
  await page.locator('[data-bundle="ui_sd"] [data-action="bundleInfo"]').click(); await page.locator('[data-action="bundleVersions"]').click();
  await page.locator('#bundleVersionForm [name="target"]').selectOption('ui_sd_v2');
  await shot('17-model-version-choice.png', 'Independent user-selected version and parameter policy; UI fixture only / 模型独立更新，由用户选择版本与参数策略');
  await page.locator('#bundleVersionForm [type="submit"]').click(); await page.waitForSelector('[data-action="versionDownload"]');
  await page.locator('.bundle-components details').first().evaluate(el => {el.open = true;});
  await page.locator('.bundle-components').scrollIntoViewIfNeeded();
  await shot('18-model-version-components.png', 'Review pinned component sources/hashes and reuse before explicit download; UI fixture only / 确认下载前核对组件来源与校验');
  await page.locator('.bundle-components details').first().evaluate(el => {el.open = false;});
  await page.locator('.version-settings').scrollIntoViewIfNeeded();
  await shot('19-model-version-settings.png', 'Preview per-version limits and settings migration; UI fixture only / 参数随模型版本迁移，超限调整预先展示');
  await page.locator('[data-action="versionDownload"]').click(); await page.waitForSelector('[data-action="versionCancel"]');
  await page.evaluate(() => {for (const b of window.__fixture.bundles) if (b.version?.pending) b.version.pending.ready = true; const t=window.__fixture.bundles.find(b=>b.id==='ui_sd_v2');t.installed=true;t.transfer={state:'installed'};window.LMA.receive(window.__fixture);});
  await shot('20-model-version-ready.png', 'Verified download still needs separate activation; old version retained; UI fixture only / 校验后等待单独确认切换，旧版本保留');
  await page.locator('[data-action="versionPendingReview"]').click(); await page.waitForSelector('[data-action="versionActivate"]'); await page.locator('[data-action="versionActivate"]').click(); await page.waitForSelector('#bundleVersionForm');
  await page.locator('[data-action="versionHistory"]').click(); await page.waitForFunction(() => document.getElementById('modalTitle').textContent.includes('切换记录'));
  await shot('21-model-version-history.png', 'Explicit version switch history with retained old assets/profiles; UI fixture only / 显式切换记录，可自行选择旧版本回退');
  await page.locator('[data-action="closeModal"]').first().click();
  await textUI.install(page); await textUI.resultRoute(page);
  await page.locator('.nav-item[data-tab="models"]').click(); await page.locator('#modelSearch').fill(''); await page.locator('[data-filter="local"]').click(); await page.locator('[data-task="text"]').click();
  await page.locator('[data-bundle="ui_text"] [data-action="bundleInfo"]').click(); await page.locator('[data-action="bundleSettings"][data-id="ui_text"]').click();
  await page.locator('[data-bundle-field="context"]').fill('99999'); await page.locator('[data-bundle-field="context"]').blur();
  await page.locator('[data-bundle-field="maxTokens"]').fill('99999'); await page.locator('[data-bundle-field="maxTokens"]').blur();
  await shot('22-text-model-settings.png', 'Text bundle settings use inspected GGUF context and dependent output bounds; UI fixture only / 文本参数联动，元数据为测试数据');
  await page.locator('#bundleSettingsForm [type="submit"]').click(); await page.waitForFunction(() => document.getElementById('modalBackdrop').hidden);
  await page.locator('[data-bundle="ui_text"] [data-action="bundleUse"]').click(); await page.locator('[name="prompt"]').fill('介绍如何在同一基座选择本地模型。（界面测试，不执行推理）');
  await page.locator('.task-parameters').evaluate(el => {el.open = true;}); await page.locator('[name="allowUnmeasured"]').check();
  await shot('23-text-queue-form.png', 'Text joins the shared task form and queue, fixed model/settings; UI fixture only / 生文接入共用任务表单');
  await page.locator('#localTaskForm [type="submit"]').click(); await page.waitForSelector('#page-tasks.active .job-card');
  await page.locator('[data-action="artifactInfo"][data-id="ui_text_artifact"]').click(); await page.waitForSelector('#textArtifact pre'); await page.locator('#textArtifact details').evaluate(el => {el.open = true;});
  await shot('24-text-result.png', 'Literal fixture text and separate reasoning safely previewed with copy/export; no model output / 正文与思考分别显示，均为界面测试数据');
  if (errors.length) throw new Error(JSON.stringify(errors));
  const video = page.video(); await context.close(); context = null;
  const raw = await video.path();
  ffmpeg(['-i', raw, '-an', '-c:v', 'libx264', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path.join(out, 'foundation-ui.mp4')]);
  ffmpeg(['-i', path.join(out, 'foundation-ui.mp4'), '-vf', 'fps=6,scale=320:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3', '-loop', '0', path.join(out, 'foundation-ui.gif')]);
  const files = fs.readdirSync(out).filter(n => /\.(png|gif|mp4)$/.test(n)).sort().map(file => ({file, bytes: fs.statSync(path.join(out, file)).size, sha256: digest(path.join(out, file))}));
  const sourceFiles = fs.readdirSync(assets, {recursive: true}).map(n => path.join(assets, n)).filter(p => fs.statSync(p).isFile()).concat(__filename, path.join(root, 'tests/foundation-ui.cjs'), path.join(root, 'tests/recipes-ui.cjs'), path.join(root, 'tests/hub-fixture.cjs'), path.join(root, 'tests/versions-ui.cjs'), path.join(root, 'tests/text-ui.cjs'));
  const input_fingerprint = Object.fromEntries(sourceFiles.sort().map(file => [path.relative(root, file).split(path.sep).join('/'), digest(file)]));
  fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify({version, kind: 'development UI with explicit simulated native bridge', android_device: false, model_inference: false, weights_downloaded: false, browser_closed: true, browser_errors: errors, screenshots, files, input_fingerprint}, null, 2) + '\n');
  console.log(JSON.stringify({version, screenshots: screenshots.length, files: files.length, android_device: false, model_inference: false, browser_closed: true}));
}
main().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {
  if (context) await context.close();
  if (server) await new Promise(resolve => server.close(resolve));
});
