(function () {
  'use strict';
  var state = null, tab = 'models', filter = 'recommended', taskFilter = 'any', query = '', keyVisible = false;
  var modelSignature = '', chatSignature = '', settingsDirty = false, settingsFilled = false;
  var pendingSettings = null, pendingDraft = null, modalKind = '', returnFocus = null, toastTimer, requestSequence = 0;
  var searchTimer, hubStarted = false, hubFileSignature = '', pendingHubToken = null;
  var modelEditor = null;
  var $ = function (id) { return document.getElementById(id); };
  var paths = {
    plus: '<path d="M12 5v14M5 12h14"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    cube: '<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Zm0 10 9-5M12 13 3 8m9 5v9M7.5 5.5l9 5"/>',
    chevron: '<path d="m8 10 4 4 4-4"/>',
    history: '<path d="M3 11a9 9 0 1 1 2.7 7M3 4v7h7m2-4v5l3 2"/>',
    compose: '<path d="M13 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M17 3l4 4-10 10-5 1 1-5L17 3Z"/>',
    send: '<path d="m4 4 17 8-17 8 3-8-3-8Zm3 8h14"/>',
    copy: '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3"/>',
    play: '<path d="m8 4 13 8-13 8V4Z"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    pause: '<path d="M8 4v16M16 4v16"/>',
    arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    battery: '<rect x="2" y="6" width="18" height="12" rx="2"/><path d="M22 10v4M7 9v6m4-6v6m4-6v6"/>',
    download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4"/>',
    upload: '<path d="M12 16V4m-5 5 5-5 5 5M4 16v4h16v-4"/>',
    sliders: '<path d="M4 6h6m4 0h6M4 12h10m4 0h2M4 18h2m4 0h10"/><circle cx="12" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
    spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    chat: '<path d="M21 11a8 8 0 0 1-8 8H8l-5 3v-7a8 8 0 0 1 8-12h2a8 8 0 0 1 8 8Z"/><path d="M7 9h10M7 13h6"/>',
    server: '<rect x="3" y="3" width="18" height="8" rx="2"/><rect x="3" y="13" width="18" height="8" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
    alert: '<path d="m12 3 10 18H2L12 3Zm0 6v5m0 3h.01"/>',
    trash: '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    link: '<path d="m9 15 6-6m-7 8-1 1a4.2 4.2 0 0 1-6-6l4-4a4.2 4.2 0 0 1 6 0m2 8a4.2 4.2 0 0 0 6 0l4-4a4.2 4.2 0 0 0-6-6l-1 1"/>'
  };
  function esc(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]; }); }
  function icon(name) { return '<span class="icon" aria-hidden="true"><svg viewBox="0 0 24 24">' + (paths[name] || paths.cube) + '</svg></span>'; }
  function hydrateIcons(root) { root.querySelectorAll('[data-icon]').forEach(function (el) { el.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24">' + (paths[el.dataset.icon] || paths.cube) + '</svg>'; }); }
  function bytes(value) {
    value = Number(value) || 0;
    if (!value) return '—';
    if (value >= 1000000000) return (value / 1000000000).toFixed(2).replace(/0$/, '') + ' GB';
    if (value >= 1000000) return Math.round(value / 1000000) + ' MB';
    if (value >= 1000) return (value / 1000).toFixed(1).replace(/\.0$/, '') + ' kB';
    return Math.round(value) + ' B';
  }
  function memory(value) { return value ? (value / 1073741824).toFixed(1) + ' GiB' : '—'; }
  function models() { return state ? (state.models || []).concat(window.LMAFoundation.views()) : []; }
  function modelById(id) { return models().filter(function (m) { return m.id === id; })[0]; }
  function engine() { return state ? state.engine || {} : {}; }
  function textQueued() { return ['waiting', 'suspended'].indexOf(engine().state) >= 0; }
  function textAvailable() { return engine().state === 'ready' || textQueued(); }
  function replyWaiting() { var s = state && state.foundation && state.foundation.execution || {}, a = s.active || {}; return !!engine().generating && ['chat', 'api'].indexOf(a.kind) < 0 && textQueued(); }
  var taskNames = {text: '生文', image: '生图', video: '生视频', audio: '生音频'};
  function outputTags(m) {
    if (Array.isArray(m.taskTags)) return m.taskTags;
    return m.task ? { 'text-generation': ['text'], 'text2text-generation': ['text'], 'image-text-to-text': ['text'], conversational: ['text'], 'text-to-image': ['image'], 'image-to-image': ['image'], 'text-to-video': ['video'], 'image-to-video': ['video'], 'video-to-video': ['video'], 'text-to-speech': ['audio'], 'text-to-audio': ['audio'], 'audio-to-audio': ['audio'] }[m.task] || [] : m.hub === undefined && m.family ? ['text'] : [];
  }
  function taskBadges(m, metadata) {
    return outputTags(m).filter(function (task) { return taskNames[task]; }).map(function (task) { return '<span class="tag task-tag task-' + task + '"' + (metadata ? ' title="来自 HF 任务元数据，尚未验证本机运行能力"' : '') + '>' + taskNames[task] + (metadata ? ' · 元数据' : '') + '</span>'; }).join('');
  }
  function matchesTask(m) { return taskFilter === 'any' || outputTags(m).indexOf(taskFilter) >= 0; }
  function nativeAction(action, values) {
    if (!window.Android) { toast('请在 Android 应用中使用此功能'); return false; }
    var requestId = Date.now().toString(36) + '-' + (++requestSequence);
    var command = Object.assign({action: action, requestId: requestId}, values || {});
    try { window.Android.dispatch(JSON.stringify(command)); return requestId; }
    catch (e) { toast('操作失败：' + e.message); return false; }
  }
  function copy(text) {
    if (window.Android) window.Android.copy(String(text));
    else if (navigator.clipboard) navigator.clipboard.writeText(String(text)).then(function () { toast('已复制'); }, function () { toast('请在 Android 应用中复制'); });
  }
  function toast(message) { clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false; toastTimer = setTimeout(function () { $('toast').hidden = true; }, 3200); }
  function route(next) {
    if (['models', 'chat', 'tasks', 'server', 'settings'].indexOf(next) < 0) return;
    closeModal(); tab = next;
    document.querySelectorAll('.page').forEach(function (el) { el.hidden = el.id !== 'page-' + next; el.classList.toggle('active', !el.hidden); });
    document.querySelectorAll('.nav-item').forEach(function (el) { var active = el.dataset.tab === next; el.classList.toggle('active', active); if (active) el.setAttribute('aria-current', 'page'); else el.removeAttribute('aria-current'); });
    if (next === 'settings' && !settingsDirty) fillSettings();
    if (next === 'chat') { renderChat(); resizeInput(); requestAnimationFrame(function () { $('messages').scrollTop = $('messages').scrollHeight; }); }
  }
  function applyTheme() {
    var preference = state && state.settings ? state.settings.theme : 'system';
    var dark = preference === 'dark' || (preference === 'system' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    if (window.Android && window.Android.theme) window.Android.theme(dark);
  }
  function receive(raw) {
    try {
      state = typeof raw === 'string' ? JSON.parse(raw) : raw;
      if (!state || !Array.isArray(state.models) || !state.settings || !state.engine) throw new Error('状态数据不完整');
      applyTheme(); renderRuntime(); renderModels(); renderChat(); renderServer(); renderHubFiles(); window.LMAFoundation.receive(); window.LMARecipes.receive();
      $('hfTokenStatus').textContent = state.settings.hfTokenSet ? '已设置令牌' : '未设置令牌';
      if (pendingHubToken) {
        var tokenResult = commandResult(pendingHubToken);
        if (tokenResult) { pendingHubToken = null; $('hfTokenHint').textContent = tokenResult.ok ? (state.settings.hfTokenSet ? '令牌已保存，后续 HF 请求使用官方源' : '令牌已清除') : tokenResult.error; }
      }
      if (!settingsFilled || (!settingsDirty && tab === 'settings')) fillSettings();
      if (pendingSettings) {
        var settingsResult = commandResult(pendingSettings.requestId);
        if (settingsResult) {
          pendingSettings = null;
          if (settingsResult.ok) { settingsDirty = false; fillSettings(); $('settingsHint').textContent = '设置已保存'; toast('设置已保存'); }
          else $('settingsHint').textContent = '保存失败：' + settingsResult.error;
        }
      }
      if (pendingDraft) {
        var sendResult = commandResult(pendingDraft.requestId);
        if (sendResult) {
          if (sendResult.ok && $('chatInput').value.trim() === pendingDraft.text) { $('chatInput').value = ''; resizeInput(); }
          pendingDraft = null; renderChat();
        }
      }
      receiveModelSettings();
      $('errorBanner').hidden = !state.error; $('errorText').textContent = state.error || '';
    } catch (e) { $('runtimeDetail').textContent = '状态读取失败：' + e.message; }
  }
  function commandResult(requestId) {
    var results = state.commandResults || (state.commandResult ? [state.commandResult] : []);
    return results.filter(function (result) { return result.requestId === requestId; })[0];
  }
  function renderRuntime() {
    var e = engine(), m = modelById(e.modelId), loading = e.state === 'loading' || e.state === 'recovering' || textQueued();
    $('runtimeDot').className = 'runtime-dot' + (e.state === 'ready' ? ' ready' : loading ? ' loading' : e.state === 'error' ? ' error' : '');
    $('runtimeName').textContent = m && e.state !== 'stopped' ? m.name : e.state === 'error' ? '模型加载失败' : '尚未加载模型';
    $('runtimeDetail').textContent = replyWaiting() ? '回复已排队 · 等待本机执行槽' : e.generating ? '正在本地生成 · 切到后台后继续' : e.detail || '下载一个模型，开始本地运行';
    var d = state.device || {};
    $('deviceName').textContent = d.name || 'Android · 本地运行';
    $('deviceMemory').textContent = memory(d.totalMemory);
    $('deviceStorage').textContent = bytes(d.freeStorage);
    $('installedCount').textContent = models().filter(function (x) { return x.installed; }).length;
  }
  function modelCard(m) {
    if (m.isBundle) return window.LMAFoundation.card(m);
    var d = m.download || {}, s = d.state || '', running = engine().modelId === m.id && ['ready', 'loading', 'recovering', 'waiting', 'suspended'].indexOf(engine().state) >= 0;
    var active = ['queued', 'downloading', 'verifying', 'pausing'].indexOf(s) >= 0, partial = m.partialBytes || d.received || 0;
    var total = d.total || m.bytes || 0, progress = total ? Math.min(100, Math.floor(partial * 100 / total)) : 0;
    var action = m.installed ? (running ? '' : 'load') : s === 'pausing' ? '' : active ? 'pauseDownload' : (partial || s === 'paused' || s === 'error') ? 'resumeDownload' : 'download';
    var label = m.installed ? (running ? engine().state === 'ready' ? '运行中' : textQueued() ? '等待执行' : '加载中' : '加载模型') : active ? s === 'pausing' ? '暂停中' : s === 'verifying' ? '校验中' : '暂停' : partial || s === 'paused' || s === 'error' ? '继续下载' : '下载';
    var glyph = m.family === 'LFM' ? 'L' : m.family === 'Gemma' ? 'G' : m.family === 'Llama' ? 'L' : m.family === '自定义' ? '+' : 'Q';
    var tags = (m.tags || []).slice(0, 4).map(function (tag) { return '<span class="tag' + (tag === '推荐' ? ' recommended' : m.tier === 'experimental' ? ' experimental' : '') + '">' + esc(tag) + '</span>'; }).join('');
    tags = taskBadges(m, false) + uncensoredTag(m.uncensored) + tags;
    if (m.recommended && (m.tags || []).indexOf('推荐') < 0) tags = '<span class="tag recommended">推荐</span>' + tags;
    var size = m.installed ? m.installedBytes : total;
    var out = '<article class="model-card' + (running ? ' is-running' : '') + '" data-model="' + esc(m.id) + '"><div class="model-top"><span class="model-symbol" data-family="' + esc(m.family) + '">' + glyph + '</span><div class="model-top-copy"><button class="model-name" data-action="modelInfo" data-id="' + esc(m.id) + '"><strong>' + esc(m.name) + '</strong><span class="model-caption">' + esc(m.family) + ' <span aria-hidden="true"> / </span> ' + esc(m.quant || 'GGUF') + '</span></button></div></div>';
    if (running) out += '<span class="running-mark">' + (engine().state === 'ready' ? '已加载' : textQueued() ? '等待执行' : '加载中') + '</span>';
    out += '<p class="model-description">' + esc(m.description) + '</p><div class="model-tags">' + tags + '</div><div class="model-footer"><div class="model-size">' + bytes(size) + '<small>' + (m.installed ? '已下载到设备' : m.sizeIsApproximate && !d.total ? '预估下载体积' : 'GGUF 模型文件') + '</small></div><div class="model-footer-actions"><button class="button ' + (m.installed || active ? 'subtle' : 'primary') + '" data-action="' + action + '" data-id="' + esc(m.id) + '"' + (!action ? ' disabled' : '') + '>' + icon(m.installed ? running ? 'check' : 'play' : active ? 'pause' : 'download') + '<span>' + label + '</span></button>';
    if (m.installed) out += '<button class="icon-button" data-action="modelSettings" data-id="' + esc(m.id) + '" aria-label="设置 ' + esc(m.name) + '" title="模型设置">' + icon('sliders') + '</button>';
    if ((m.installed || partial || m.id.indexOf('custom_') === 0 || m.hub || s === 'error') && !active) out += '<button class="icon-button" data-action="deleteModel" data-id="' + esc(m.id) + '" aria-label="删除 ' + esc(m.name) + '">' + icon('trash') + '</button>';
    out += '</div></div>';
    if (!m.installed && (active || partial || s === 'paused')) {
      var status = s === 'queued' ? '等待下载' : s === 'verifying' ? '校验 SHA256…' : s === 'paused' ? '已暂停' : s === 'error' ? '下载中断' : d.speed ? bytes(d.speed) + '/s' : '正在连接…';
      out += '<div class="download-progress"><div class="progress-track" role="progressbar" aria-label="下载进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + progress + '"><span style="width:' + progress + '%"></span></div><div class="download-meta"><span>' + status + '</span><span>' + (partial ? bytes(partial) : '0 MB') + (total ? ' / ' + bytes(total) : '') + '</span></div></div>';
    }
    if (!m.installed && d.error) out += '<div class="download-error">' + esc(d.error) + '</div>';
    return out + '</article>';
  }
  function renderModels() {
    $('hubControls').hidden = filter !== 'all'; $('hubPagination').hidden = filter !== 'all';
    $('modelSearch').placeholder = filter === 'local' ? '搜索本地模型' : '搜索 HF 模型、owner/model 或仓库链接';
    if (filter === 'all') { renderHub(); return; }
    var all = models().filter(function (m) {
      var included = filter === 'recommended' && m.recommended || filter === 'light' && m.tier === 'light' || filter === 'quality' && (m.tier === 'quality' || m.tier === 'experimental') || filter === 'local' && (m.installed || m.hasPreparedAssets || m.partialBytes || m.download && m.download.state || m.hub || m.imported || m.tier === 'custom');
      return included && matchesTask(m) && (!query || [m.name, m.family, m.repository, m.description, (m.tags || []).join(' ')].join(' ').toLowerCase().indexOf(query.toLowerCase()) >= 0);
    });
    var signature = JSON.stringify([all, engine().state, engine().modelId, filter, query, taskFilter]);
    if (signature === modelSignature) return; modelSignature = signature;
    var focused = document.activeElement && document.activeElement.closest('#modelList button'), focusAction = focused && focused.dataset.action, focusId = focused && focused.dataset.id;
    $('modelListTitle').textContent = query ? '本地搜索结果' : {recommended: '适合先试的模型', light: '先从轻量开始', quality: '更高容量的选择', local: '你的本地模型'}[filter];
    $('modelResultCount').textContent = filter === 'local' ? all.filter(function (m) { return m.installed; }).length + ' 已下载 · ' + all.filter(function (m) { return !m.installed && !m.hasPreparedAssets; }).length + ' 下载任务' + (all.some(function (m) { return !m.installed && m.hasPreparedAssets; }) ? ' · ' + all.filter(function (m) { return !m.installed && m.hasPreparedAssets; }).length + ' 仅运行资产' : '') : all.length + ' 个模型';
    $('modelList').innerHTML = all.length ? all.map(modelCard).join('') : '<div class="empty-list"><h3>' + (filter === 'local' && !query ? '还没有下载模型' : '没有匹配的模型') + '</h3><p>' + (filter === 'local' ? '下载、导入的模型和未完成的下载会出现在这里。' : '尝试其他关键词，或添加自己的 GGUF 文件。') + '</p><button class="button subtle" data-action="showAll">浏览全部模型</button></div>';
    if (focusId) $('modelList').querySelectorAll('button').forEach(function (b) { if (b.dataset.action === focusAction && b.dataset.id === focusId) b.focus({preventScroll: true}); });
  }
  function uncensoredTag(u) {
    if (u && u.declared) return '<span class="tag uncensored" title="已核对作者声明；未测量拒答率">无审查</span>';
    if (u && u.detected) return '<span class="tag uncensored" title="由仓库名称或标签识别，作者声明尚未核对">无审查 · 元数据</span>';
    return '';
  }
  function hub() { return state && state.hub || {items: [], files: {}}; }
  function startHub() {
    clearTimeout(searchTimer); hubStarted = true;
    nativeAction('hubSearch', {query: query, format: $('hubFormat').value, sort: $('hubSort').value});
  }
  function selectFilter(next) {
    clearTimeout(searchTimer); filter = next; query = ''; $('modelSearch').value = ''; updateFilters(); modelSignature = ''; renderModels();
    if (next === 'all' && (!hubStarted && !hub().initialized || hub().query)) startHub();
  }
  function pagination(previous, next, page, action, loading) {
    return '<button class="button secondary" data-action="' + action + '" data-direction="previous"' + (!previous || loading ? ' disabled' : '') + '>上一页</button><span>第 ' + esc(page || 1) + ' 页</span><button class="button secondary" data-action="' + action + '" data-direction="next"' + (!next || loading ? ' disabled' : '') + '>下一页</button>';
  }
  function renderHub() {
    var h = hub(), items = (h.items || []).filter(matchesTask), bundles = models().filter(function (m) { return m.isBundle && matchesTask(m) && (!query || [m.name, m.family, m.repository, m.description].join(' ').toLowerCase().indexOf(query.toLowerCase()) >= 0); }), signature = JSON.stringify(['hub', h, models(), taskFilter, query]);
    if (signature === modelSignature) return; modelSignature = signature;
    $('modelListTitle').textContent = query ? 'Hugging Face 搜索结果' : '探索 Hugging Face';
    $('modelResultCount').textContent = (h.searching ? '正在连接…' : '本页 ' + items.length + ' 个仓库') + (bundles.length ? ' · ' + bundles.length + ' 套已登记配方' : '');
    $('modelList').innerHTML = h.searching ? '<div class="empty-list" role="status"><h3>正在获取 HF 模型…</h3><p>推荐和本地模型可随时离线浏览。</p></div>' : h.error ? '<div class="empty-list"><h3>暂时无法获取列表</h3><p>' + esc(h.error) + '</p><button class="button primary" data-action="hubRetry">重试</button></div>' : items.length ? items.map(function (m) {
      return '<article class="model-card hub-card" data-repository="' + esc(m.id) + '"><span class="eyebrow">HUGGING FACE</span><h3 class="hub-repository">' + esc(m.id) + '</h3><div class="model-tags">' + taskBadges(m, true) + uncensoredTag(m.uncensored) + (m.gated ? '<span class="tag">需 HF 授权</span>' : '') + '<span class="tag">' + esc(m.task || '任务待核对') + '</span></div><p class="model-description">' + Number(m.downloads || 0).toLocaleString() + ' 次下载 · ' + Number(m.likes || 0).toLocaleString() + ' 喜欢' + (m.license ? ' · ' + esc(m.license) : '') + '</p><div class="hub-actions"><button class="button primary" data-action="hubFiles" data-repository="' + esc(m.id) + '">' + icon('download') + '选择文件</button><button class="text-button" data-action="hubSource" data-repository="' + esc(m.id) + '">仓库 ↗</button></div></article>';
    }).join('') : '<div class="empty-list"><h3>' + (h.initialized ? '没有匹配的仓库' : '浏览完整 HF 模型库') + '</h3><p>尝试关键词、owner/model 或 HF 仓库链接。其他格式可切换“HF 全部格式”查看。</p><button class="button subtle" data-action="hubRefresh">获取列表</button></div>';
    if (bundles.length) $('modelList').innerHTML = bundles.map(modelCard).join('') + $('modelList').innerHTML;
    $('hubPagination').innerHTML = pagination(h.previous, h.next, h.page, 'hubPage', h.searching);
  }
  function renderHubFiles() {
    if (modalKind !== 'hubFiles') return;
    var f = hub().files || {}, repo = f.repository || {}, items = f.items || [], signature = JSON.stringify([f, models()]);
    if (signature === hubFileSignature) return; hubFileSignature = signature;
    var html = '<p class="hub-repository">' + esc(repo.id || 'Hugging Face') + '</p>' + uncensoredTag(repo.uncensored);
    if (repo.revision) html += '<p class="modal-help">固定版本 ' + esc(repo.revision.slice(0, 12)) + ' · ' + esc(repo.task || '任务待核对') + '</p>';
    html += '<p class="modal-help">单文件 GGUF 可按下方流程加入文本模型；图像、LoRA、语音请明确选择配套组件配方。格式与目录登记不代表手机运行兼容。</p>';
    if (repo.revision && !f.loading && !f.error && (hub().recipeTemplates || []).length) html += '<button class="button secondary" data-action="recipeStart" data-repository="' + esc(repo.id) + '">构建模型包 / LoRA 配方</button>';
    if (hub().recipeError) html += '<p class="download-error">' + esc(hub().recipeError) + '</p>';
    if (f.loading) html += '<p role="status">正在获取文件…</p>';
    else if (f.error) html += '<p class="download-error">' + esc(f.error) + '</p><button class="button secondary" data-action="hubFilePage" data-direction="retry">重试</button>';
    else if (!items.length) html += '<p>本页没有 GGUF 文件。可继续翻页，或查看原仓库与对应 GGUF 转换版本。</p>';
    else html += '<div class="hub-files">' + items.map(function (file, index) {
      var existing = models().filter(function (m) { return m.repository === repo.id && m.revision === repo.revision && m.filename === file.path; })[0];
      var label = file.blocked ? '暂不支持' : existing ? existing.installed ? '已下载 · 本地管理' : '查看下载任务' : '下载';
      return '<article class="hub-file"><strong>' + esc(file.path) + '</strong><small>' + bytes(file.bytes) + ' · ' + esc(file.quant) + (file.sha256 ? ' · SHA256' : ' · 未提供发布者哈希') + '</small>' + (file.blocked ? '<p>' + esc(file.blocked) + '</p>' : '') + '<button class="button ' + (file.blocked || existing ? 'secondary' : 'primary') + '" data-action="' + (existing ? 'showLocal' : 'hubDownload') + '" data-index="' + index + '"' + (file.blocked ? ' disabled' : '') + '>' + label + '</button></article>';
    }).join('') + '</div>';
    html += '<div class="hub-pagination">' + pagination(f.previous, f.next, f.page, 'hubFilePage', f.loading) + '</div><button class="text-button" data-action="hubSource" data-repository="' + esc(repo.id || '') + '">在 HF 查看来源与许可 ↗</button>';
    var focus = document.activeElement, action = focus && focus.dataset.action, direction = focus && focus.dataset.direction;
    $('modalContent').innerHTML = html;
    if (action) $('modalContent').querySelectorAll('button:not(:disabled)').forEach(function (button) { if (button.dataset.action === action && button.dataset.direction === direction) button.focus({preventScroll: true}); });
  }
  function richText(text) {
    // No model-supplied HTML or links are executed. Fenced code is always escaped.
    return String(text || '').split('```').map(function (part, index) {
      if (index % 2) {
        var newline = part.indexOf('\n'), language = newline >= 0 ? part.substring(0, newline).trim().slice(0, 24) : '';
        var code = newline >= 0 ? part.substring(newline + 1) : part;
        return '<div class="code-block"><div class="code-heading"><span>' + esc(language || '代码') + '</span><button data-action="copyCode" class="text-button">复制</button></div><pre><code>' + esc(code) + '</code></pre></div>';
      }
      return '<span>' + esc(part).replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>') + '</span>';
    }).join('');
  }
  function renderChat() {
    var e = engine(), m = modelById(e.modelId), chat = state && state.chat || {messages: []};
    $('chatModelName').textContent = m ? m.name : '选择模型';
    $('composerHint').textContent = replyWaiting() ? '回复已排队 · 点击方块取消' : e.generating ? '后台继续生成 · 点击方块停止' : textQueued() ? '发送后排队，轮到此回复时自动加载原模型' : e.state === 'ready' ? '回复在当前手机生成' : e.state === 'loading' || e.state === 'recovering' ? '模型正在加载，请稍候…' : '先加载一个模型，再开始对话';
    $('sendButton').classList.toggle('stop', !!e.generating);
    $('sendButton').setAttribute('aria-label', e.generating ? '停止生成' : '发送消息');
    $('sendButton').innerHTML = icon(e.generating ? 'stop' : 'send');
    $('sendButton').disabled = !e.generating && (!!pendingDraft || !textAvailable() || !$('chatInput').value.trim());
    var signature = JSON.stringify([chat, replyWaiting()]);
    if (signature === chatSignature) return; chatSignature = signature;
    var box = $('messages'), nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 120, oldScroll = box.scrollTop;
    var opened = {};
    box.querySelectorAll('details[open]').forEach(function (d) { opened[d.dataset.message] = true; });
    if (!(chat.messages || []).length) {
      box.innerHTML = '<div class="chat-empty"><div class="empty-symbol">' + icon('spark') + '</div><span class="eyebrow">YOUR DEVICE. YOUR MODELS.</span><h2>从一句话开始。</h2><p>模型与对话留在当前手机。<br>下载并加载模型后，即可离线使用。</p><div class="suggestions"><button class="suggestion" data-action="suggest" data-text="用简单的例子解释一下什么是大语言模型。">解释一个概念' + icon('arrow') + '</button><button class="suggestion" data-action="suggest" data-text="帮我写一封简洁、礼貌的工作邮件。请先问我需要提供哪些信息。">一起写点内容' + icon('arrow') + '</button></div></div>';
    } else box.innerHTML = chat.messages.map(function (message) {
      var user = message.role === 'user', status = message.status, footer = [];
      if (!user && message.elapsed) footer.push((message.elapsed / 1000).toFixed(1) + ' 秒');
      if (!user && message.tokens) footer.push(message.tokens + ' tokens');
      if (status === 'stopped') footer.push('已停止');
      if (status === 'interrupted') footer.push('已中断');
      if (status === 'generating') footer.push(replyWaiting() ? '等待执行' : '生成中');
      var out = '<article class="message' + (user ? ' user' : '') + '"><div class="message-heading"><strong>' + (user ? '你' : 'LMA') + '</strong>' + (!user ? '<button class="text-button" data-action="copyMessage" data-id="' + esc(message.id) + '">复制</button>' : '') + '</div>';
      if (message.reasoning) out += '<details class="reasoning" data-message="' + esc(message.id) + '"' + (opened[message.id] ? ' open' : '') + '><summary>思考过程</summary><div>' + esc(message.reasoning) + '</div></details>';
      out += '<div class="message-content">' + (user ? esc(message.content) : richText(message.content)) + (status === 'generating' ? '<span class="generating-mark" aria-label="正在生成"></span>' : '') + '</div>';
      if (message.error) out += '<p class="message-error">' + esc(message.error) + '</p>';
      return out + (footer.length ? '<div class="message-footer">' + footer.join(' <span aria-hidden="true">·</span> ') + '</div>' : '') + '</article>';
    }).join('');
    if (nearBottom || oldScroll === 0) box.scrollTop = box.scrollHeight; else box.scrollTop = oldScroll;
  }
  function endpoint() { var e = engine(); return state && state.settings.lan && (e.addresses || []).length ? e.addresses[0] : e.localUrl || 'http://127.0.0.1:8080/v1'; }
  function example(includeKey) {
    var key = includeKey && state ? state.settings.apiKey : 'YOUR_LMA_API_KEY';
    return 'curl ' + endpoint() + '/chat/completions \\\n  -H "Authorization: Bearer ' + key + '" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"model":"' + (engine().modelId || 'MODEL_ID') + '","messages":[{"role":"user","content":"你好"}],"stream":true}\'';
  }
  function renderServer() {
    var e = engine(), api = state.api || {state: 'stopped'}, ready = api.state === 'ready', active = ready, m = modelById(e.modelId);
    $('serverStateLabel').textContent = ready ? '本地模型接口运行中' : api.state === 'error' ? '接口启动失败' : '接口尚未启动';
    $('serverStatePill').textContent = ready ? '运行中' : api.state === 'error' ? '启动失败' : '未启动';
    $('serverStatePill').className = 'status-pill' + (ready ? ' ready' : active ? ' loading' : '');
    $('serverModelName').textContent = m && textAvailable() ? '文本：' + m.name + (textQueued() ? ' · 队列等待' : '') : '加载或管理文本模型';
    $('apiUrl').textContent = endpoint();
    $('serverToggle').innerHTML = icon(active ? 'stop' : 'play') + '<span>' + (active ? '关闭接口' : '启动接口') + '</span>';
    $('serverToggle').className = 'button ' + (active ? 'danger' : 'primary');
    $('lanToggle').checked = !!state.settings.lan;
    $('lanToggle').disabled = !!e.generating;
    $('apiKeyDisplay').textContent = keyVisible ? state.settings.apiKey : '••••••••••••••••••••';
    var exempt = state.device && state.device.batteryExempt;
    $('batteryTitle').textContent = exempt ? '已允许不受电池优化限制' : '允许锁屏后继续服务';
    $('batteryDescription').textContent = exempt ? '部分手机还需要在系统管家中允许后台运行和自启动。' : '首次使用时，允许 LMA 不受电池优化限制。';
    $('apiExample').textContent = example(false);
    var logBox = $('runtimeLogs'), nearBottom = logBox.scrollHeight - logBox.scrollTop - logBox.clientHeight < 70;
    var logs = (state.logs || []).slice(-65).map(function (line) { var d = new Date(line.time); return d.toLocaleTimeString('zh-CN', {hour12: false}) + '  ' + line.text; }).join('\n');
    logBox.textContent = logs || '启动模型后，这里会显示加载与运行记录。';
    if (nearBottom) logBox.scrollTop = logBox.scrollHeight;
  }
  function fillSettings() {
    if (!state) return;
    var form = $('settingsForm');
    ['source', 'autoLoad', 'boot', 'port', 'theme'].forEach(function (key) {
      var field = form.elements.namedItem(key); if (!field) return;
      if (field.type === 'checkbox') field.checked = !!state.settings[key];
      else field.value = key === 'temperature' ? Number(state.settings[key]).toFixed(1) : state.settings[key] == null ? key === 'reasoning' ? 'off' : '' : state.settings[key];
    });
    settingsFilled = true;
  }
  function openModal(title, content, kind) {
    if ($('modalBackdrop').hidden) returnFocus = document.activeElement;
    modalKind = kind || ''; $('modalTitle').textContent = title; $('modalContent').innerHTML = content; $('modalBackdrop').hidden = false;
    $('modal').scrollTop = 0; $('modal').focus();
    document.querySelector('.app-shell').setAttribute('aria-hidden', 'true');
  }
  var configPresets = {threads: [1, 2, 3, 4, 6, 8, 12, 16, 32], context: [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072], maxTokens: [128, 256, 512, 1024, 2048, 4096, 8192], temperature: [0, 0.3, 0.5, 0.7, 1, 1.5, 2]};
  var configLabels = {threads: 'CPU 线程', context: '上下文长度', maxTokens: '单次输出上限', temperature: '温度'};
  function configMaximum(key) {
    if (key === 'maxTokens') return Math.min(modelEditor.limits.outputGuardMax || Number.MAX_SAFE_INTEGER, Math.max(1, Number($('cfg-context').value) - 1));
    return modelEditor.limits[{threads: 'threadsMax', context: 'contextMax', temperature: 'temperatureMax'}[key]];
  }
  function comboField(key, value) {
    return '<div class="form-field config-field"><label for="cfg-' + key + '">' + configLabels[key] + '</label><div class="editable-combo"><input id="cfg-' + key + '" name="' + key + '" type="text" inputmode="' + (key === 'temperature' ? 'decimal' : 'numeric') + '" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="presets-' + key + '" autocomplete="off" spellcheck="false" data-config-number="' + key + '" data-previous="' + value + '" value="' + value + '"><button type="button" data-action="configPresets" data-field="' + key + '" aria-label="选择' + configLabels[key] + '预设">' + icon('chevron') + '</button><div id="presets-' + key + '" class="combo-options" role="listbox" aria-label="' + configLabels[key] + '预设" hidden></div></div><small id="limit-' + key + '"></small></div>';
  }
  function openModelSettings(id) {
    var m = modelById(id); if (!m || !m.installed) return;
    openModal('模型设置', '<p role="status">正在读取此模型的 GGUF 约束…</p>', 'modelSettings');
    modelEditor = {id: id, inspect: nativeAction('inspectModel', {id: id}), pending: null};
    if (!modelEditor.inspect) $('modalContent').innerHTML = '<p>请在 Android 应用中读取模型参数。</p>';
  }
  function fillModelSettings(config) {
    var m = modelById(modelEditor.id), v = config.values; modelEditor.limits = config.limits;
    $('modalContent').innerHTML = '<div class="config-model"><span class="eyebrow">PER-MODEL SETTINGS</span><h3>' + esc(m.name) + '</h3><p>' + esc(m.quant || 'GGUF') + ' · 参数随此模型独立保存</p></div><form id="modelSettingsForm"><fieldset class="config-fieldset"><legend>加载参数</legend><div class="form-grid">' + comboField('context', v.context) + comboField('threads', v.threads) + '</div><label class="form-field"><span>思考模式</span><select name="reasoning"><option value="off">关闭 · 优先快速回复</option><option value="auto">由模型决定</option><option value="on">开启</option></select></label></fieldset><fieldset class="config-fieldset"><legend>生成参数</legend><div class="form-grid">' + comboField('maxTokens', v.maxTokens) + comboField('temperature', v.temperature) + '</div><label class="form-field"><span>系统提示词</span><textarea name="systemPrompt" rows="3" maxlength="4000"></textarea></label></fieldset><p class="form-help">修改当前运行模型的上下文、线程或思考模式会重新加载；生成参数用于下一次应用内对话。其他模型的参数独立保存。</p><p class="form-help">输出与输入共用上下文；实际可生成的 token 还取决于提示词、历史记录和模型。较大的上下文需要更多内存。</p><p id="modelSettingsHint" class="save-hint" role="status"></p><div class="modal-actions"><button class="button secondary" type="button" data-action="closeModal">关闭</button><button class="button primary" type="submit">保存模型设置</button></div></form>';
    var form = $('modelSettingsForm'); form.elements.reasoning.value = v.reasoning; form.elements.systemPrompt.value = v.systemPrompt;
    updateConfigLimits();
  }
  function updateConfigLimits() {
    if (!modelEditor || !$('modelSettingsForm')) return;
    var limits = modelEditor.limits;
    $('limit-context').textContent = limits.contextKnown ? (limits.contextLimitSource === 'application_or_recipe' ? '应用 / 配方上限：' + limits.contextMax + '（GGUF 声明 ' + limits.contextMetadataMax + '）' : 'GGUF 声明上限：' + limits.contextMax + ' tokens') : '未读取到模型上限，暂用应用上限 ' + limits.contextMax + ' tokens';
    $('limit-threads').textContent = '设备最多 ' + limits.threadsMax + ' 个线程';
    $('limit-maxTokens').textContent = '当前最多 ' + configMaximum('maxTokens') + ' tokens（上下文 − 1；输入也占用上下文）';
    $('limit-temperature').textContent = '应用支持 0–' + limits.temperatureMax;
  }
  function clampConfigField(field) {
    var key = field.dataset.configNumber, raw = field.value.trim(), min = key === 'temperature' ? 0 : key === 'context' ? 2 : 1;
    var max = configMaximum(key), number = Number(raw), hint = $('modelSettingsHint');
    if (!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?$/i.test(raw) || Number.isNaN(number)) {
      field.value = field.dataset.previous; hint.textContent = configLabels[key] + '需要有效数值，已恢复原值'; return;
    }
    var adjusted = Math.max(min, Math.min(max, key === 'temperature' ? number : Math.floor(number)));
    field.value = String(adjusted); field.dataset.previous = field.value;
    if (number !== adjusted) hint.textContent = configLabels[key] + '已自动调整为 ' + adjusted + (number > max ? '（可用上限）' : '（可用范围内）');
    if (key === 'context') { clampConfigField($('cfg-maxTokens')); updateConfigLimits(); }
  }
  function closeConfigPresets() {
    document.querySelectorAll('.combo-options').forEach(function (list) { list.hidden = true; });
    document.querySelectorAll('[data-config-number]').forEach(function (input) { input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); });
  }
  function showConfigPresets(key) {
    var input = $('cfg-' + key), list = $('presets-' + key), wasOpen = !list.hidden; closeConfigPresets(); if (wasOpen) return;
    // Commit a custom context first so the output presets use its new bound.
    if (key === 'maxTokens') clampConfigField($('cfg-context'));
    var max = configMaximum(key), values = configPresets[key].filter(function (n) { return n <= max; });
    if (values.indexOf(max) < 0) values.push(max);
    list.innerHTML = values.map(function (value, index) { return '<button type="button" tabindex="-1" role="option" aria-selected="' + (Number(input.value) === value) + '" id="preset-' + key + '-' + index + '" data-action="configValue" data-field="' + key + '" data-value="' + value + '">' + value + (value === max ? ' · 上限' : '') + '</button>'; }).join('');
    list.hidden = false; input.setAttribute('aria-expanded', 'true'); input.focus({preventScroll: true});
  }
  function receiveModelSettings() {
    if (modalKind !== 'modelSettings' || !modelEditor) return;
    var result = modelEditor.inspect && commandResult(modelEditor.inspect);
    if (result) {
      modelEditor.inspect = null;
      if (result.ok) fillModelSettings(modelById(modelEditor.id).config);
      else $('modalContent').innerHTML = '<p role="alert">读取失败：' + esc(result.error) + '</p><button class="button secondary" data-action="modelSettings" data-id="' + esc(modelEditor.id) + '">重试</button>';
    }
    result = modelEditor.pending && commandResult(modelEditor.pending);
    if (result) {
      modelEditor.pending = null;
      if (result.ok) { fillModelSettings(modelById(modelEditor.id).config); $('modelSettingsHint').textContent = '此模型的设置已保存'; toast('模型设置已保存'); }
      else { $('modelSettingsHint').textContent = '保存失败：' + result.error; $('modelSettingsForm').querySelector('[type="submit"]').disabled = false; }
    }
  }
  function closeModal() {
    if ($('modalBackdrop').hidden) return;
    window.LMAFoundation.close(); window.LMARecipes.close(); $('modalBackdrop').hidden = true; modalKind = ''; modelEditor = null;
    document.querySelector('.app-shell').removeAttribute('aria-hidden');
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus({preventScroll: true}); returnFocus = null;
  }
  function confirmAction(title, message, action, id, button) {
    openModal(title, '<p>' + esc(message) + '</p><div class="modal-actions"><button class="button secondary" data-action="closeModal">取消</button><button class="button danger" data-action="confirmed" data-command="' + esc(action) + '" data-id="' + esc(id) + '">' + esc(button || '确认删除') + '</button></div>', 'confirm');
  }
  function pickModel() {
    var installed = models().filter(function (m) { return m.installed && !m.isBundle; });
    openModal('选择本地模型', installed.length ? '<p>加载后开启本机接口。文本回复与生成任务共用队列，自动切换引擎；队列空闲后恢复已选文本模型。</p>' + (['ready', 'loading', 'recovering', 'waiting', 'suspended'].indexOf(engine().state) >= 0 ? '<button class="button danger" data-action="stopTextModel">停止文本模型</button>' : '') + '<div class="modal-list">' + installed.map(function (m) { return '<div class="modal-list-item"><button data-action="load" data-id="' + esc(m.id) + '"><strong>' + esc(m.name) + '</strong><small>' + esc(m.quant) + ' · ' + bytes(m.installedBytes) + '</small></button>' + icon('arrow') + '</div>'; }).join('') + '</div>' : '<p>先下载一个模型，或从设备导入 GGUF 文件。</p><button class="button primary" data-action="tab" data-tab="models">前往模型库</button>', 'pickModel');
  }
  function modelInfo(id) {
    var m = modelById(id); if (!m) return; var d = m.download || {}, u = m.uncensored || {};
    var declaration = u.declared ? '<p><strong>无审查 · ' + esc(u.method === 'abliterated' ? 'Abliterated 去拒答' : u.method === 'uncensored-instruct' ? 'Dolphin 微调' : 'Uncensored 权重') + '</strong></p><p>' + esc(u.summary) + '</p>' : u.detected ? '<p><strong>无审查 · 元数据</strong></p><p>' + esc(u.summary) + '</p>' : '<p>本地模型 · 未标记无审查属性。</p>';
    var shared = m.bundleId && m.installed ? '<p class="modal-help">可创建生成任务或管理模型版本，复用已下载文件。</p><div class="modal-actions"><button class="button primary" data-action="bundleUse" data-id="' + esc(m.bundleId) + '">创建生成任务</button><button class="button secondary" data-action="bundleVersions" data-id="' + esc(m.bundleId) + '">模型版本管理</button></div>' : '';
    var source = m.sourceUrl || m.url ? '<button class="button secondary" data-action="sourceLink" data-id="' + esc(m.id) + '">' + icon('link') + '查看 GGUF 来源与许可</button>' : '';
    var evidence = u.declared && u.evidenceUrl ? '<p><button class="text-button" data-action="uncensoredSource" data-id="' + esc(m.id) + '">查看作者的无审查说明 ↗</button></p>' : '';
    openModal(m.name, '<div class="model-info"><p>' + esc(m.description) + '</p>' + declaration + '<dl><dt>文件</dt><dd>' + esc(m.filename || m.name + '.gguf') + '</dd><dt>格式</dt><dd>' + esc(m.quant || 'GGUF') + '</dd><dt>模型 ID</dt><dd>' + esc(m.id) + '</dd><dt>发布者哈希</dt><dd>' + esc(m.sha256 || '未提供，可对照原始模型仓库') + '</dd>' + (d.sha256 ? '<dt>本地 SHA256</dt><dd>' + esc(d.sha256) + '</dd>' : '') + '<dt>文件验证</dt><dd>' + (d.verification === 'publisher-sha256' ? '与发布者 SHA256 一致' : m.installed ? 'GGUF 格式与传输完整性检查' : '下载完成后校验') + '</dd></dl>' + source + evidence + shared + '<p class="modal-help">无审查属性依据作者说明核对，实际拒答率与手机运行表现尚未实测。应用不额外过滤提示词或模型回复；系统提示词可在本地模型的独立设置中修改。</p></div>', 'modelInfo');
  }
  function history() {
    var sessions = state && state.chat ? state.chat.sessions || [] : [];
    openModal('对话历史', sessions.length ? '<div class="modal-list">' + sessions.map(function (s) { var m = modelById(s.modelId); return '<div class="modal-list-item"><button data-action="selectSession" data-id="' + esc(s.id) + '"><strong>' + esc(s.title) + '</strong><small>' + new Date(s.updated).toLocaleDateString('zh-CN') + (m ? ' · ' + esc(m.name) : '') + '</small></button><button class="icon-button" data-action="deleteSession" data-id="' + esc(s.id) + '" aria-label="删除这段对话">' + icon('trash') + '</button></div>'; }).join('') + '</div>' : '<p>还没有对话。生成的回复会自动保存在手机上。</p>', 'history');
  }
  function handleAction(action, el) {
    var id = el.dataset.id, m;
    if (window.LMAFoundation.handle(action, el) || window.LMARecipes.handle(action, el)) return;
    switch (action) {
      case 'tab': route(el.dataset.tab); break;
      case 'showAll': selectFilter('all'); break;
      case 'showLocal': route('models'); selectFilter('local'); break;
      case 'hubRefresh': startHub(); break;
      case 'hubRetry': nativeAction('hubPage', {direction: 'retry'}); break;
      case 'hubPage': case 'hubFilePage': nativeAction(action, {direction: el.dataset.direction}); break;
      case 'hubFiles':
        hubFileSignature = ''; openModal('选择 HF 模型文件', '<p role="status">正在获取文件…</p>', 'hubFiles');
        nativeAction('hubFiles', {repository: el.dataset.repository}); break;
      case 'hubDownload': {
        var files = hub().files || {}, repo = files.repository || {}, file = (files.items || [])[Number(el.dataset.index)];
        if (file && !file.blocked && nativeAction('hubDownload', {repository: repo.id, revision: repo.revision, path: file.path})) { closeModal(); selectFilter('local'); toast('已提交下载，可在本地管理进度'); }
        break;
      }
      case 'hubSource': if (window.Android && el.dataset.repository) window.Android.openLink('https://huggingface.co/' + el.dataset.repository); break;
      case 'clearHubToken': $('hfTokenInput').value = ''; pendingHubToken = nativeAction('hubToken', {token: ''}); break;
      case 'download': case 'resumeDownload': if (nativeAction(action, {id: id})) toast('已提交下载任务'); break;
      case 'pauseDownload': nativeAction(action, {id: id}); break;
      case 'load': if (nativeAction(action, {id: id})) { closeModal(); toast('正在加载模型'); } break;
      case 'deleteModel': m = modelById(id); if (m) confirmAction('删除模型文件', '删除“' + m.name + '”的本地文件和下载记录。需要时可以重新下载。', action, id); break;
      case 'confirmed': nativeAction(el.dataset.command, {id: id}); closeModal(); break;
      case 'modelInfo': modelInfo(id); break;
      case 'modelSettings': openModelSettings(id); break;
      case 'configPresets': showConfigPresets(el.dataset.field); break;
      case 'configValue': {
        var field = $('cfg-' + el.dataset.field); field.value = el.dataset.value; clampConfigField(field); closeConfigPresets(); field.focus({preventScroll: true}); break;
      }
      case 'sourceLink': m = modelById(id); if (m && window.Android) window.Android.openLink(m.sourceUrl || m.url); break;
      case 'uncensoredSource': m = modelById(id); if (m && m.uncensored && window.Android) window.Android.openLink(m.uncensored.evidenceUrl); break;
      case 'pickModel': pickModel(); break;
      case 'toggleServer': nativeAction(state.api && state.api.state === 'ready' ? 'stopApi' : 'startApi'); break;
      case 'stopTextModel': nativeAction('stopEngine'); closeModal(); break;
      case 'copyUrl': copy(endpoint()); break;
      case 'copyKey': if (state) copy(state.settings.apiKey); break;
      case 'copyExample': copy(example(true)); break;
      case 'revealKey': keyVisible = !keyVisible; if (state) renderServer(); break;
      case 'copyMessage': if (state && state.chat) { var message = state.chat.messages.filter(function (x) { return x.id === id; })[0]; if (message) copy(message.content); } break;
      case 'copyCode': copy(el.closest('.code-block').querySelector('code').textContent); break;
      case 'history': history(); break;
      case 'newChat': if (nativeAction('newChat')) route('chat'); break;
      case 'selectSession': nativeAction(action, {id: id}); closeModal(); route('chat'); break;
      case 'deleteSession': confirmAction('删除这段对话', '删除后无法恢复。这项操作只影响当前对话记录。', action, id); break;
      case 'suggest': $('chatInput').value = el.dataset.text; resizeInput(); $('chatInput').focus(); renderChat(); break;
      case 'battery': case 'exportLogs': case 'dismissError': nativeAction(action); break;
      case 'closeModal': closeModal(); break;
      case 'addMenu': openModal('添加你的模型', '<div class="modal-list"><div class="modal-list-item"><button data-action="browseHub"><strong>从 Hugging Face 下载</strong><small>搜索模型并选择 GGUF 量化文件</small></button>' + icon('search') + '</div><div class="modal-list-item"><button data-action="addUrl"><strong>从下载链接添加</strong><small>输入 GGUF 的 HTTPS 直链，支持断点续传</small></button>' + icon('link') + '</div><div class="modal-list-item"><button data-action="importPicker"><strong>从设备导入</strong><small>选择已下载的 .gguf 文件</small></button>' + icon('upload') + '</div><div class="modal-list-item"><button data-action="bundleManifestPicker"><strong>导入模型包清单</strong><small>查看完整组件、标签与下载计划，确认后再下载或导入</small></button>' + icon('cube') + '</div></div>', 'add'); break;
      case 'browseHub': closeModal(); selectFilter('all'); break;
      case 'addUrl': openModal('添加 GGUF 下载链接', '<form id="customModelForm"><label class="form-field"><span>模型名称</span><input name="name" required maxlength="160" placeholder="例如：我的 Qwen 1.7B"></label><label class="form-field"><span>HTTPS 下载链接</span><input name="url" type="url" required placeholder="https://huggingface.co/…/resolve/main/….gguf" autocapitalize="off" spellcheck="false"></label><label class="form-field"><span>SHA256（可选）</span><input name="sha256" pattern="[a-fA-F0-9]{64}" maxlength="64" placeholder="发布者提供的 64 位哈希" autocapitalize="off" spellcheck="false"></label><p class="modal-help">请确认模型使用当前推理组件支持的架构，且适合手机的内存容量。</p><button type="submit" class="button primary">添加并下载</button></form>', 'addUrl'); break;
      case 'importPicker': nativeAction(action); closeModal(); break;
      case 'about': openModal('关于 LMA', '<p>LMA 0.3.0-dev.13 是本地模型工作台，由 Android 前台服务持有本机接口、任务和原生引擎。无需 ROOT；模型由你选择下载或导入。</p><p>界面、对话记录和推理在设备本地运行。模型下载会连接你选择的仓库；开启局域网后，持有 API 密钥的同网设备可以请求推理。</p><p>前台通知、唤醒锁与电池设置可帮助后台运行。系统强行停止、内存不足、厂商省电策略、发热或重启仍会影响服务。模型输出和速度尚需目标手机实测。</p><p>推理引擎：llama.cpp（MIT），由 ServLlama v1.2.2 分发的 Android ARM64 预编译组件。扩散 worker 使用 sd.cpp（MIT）和 MNN（Apache-2.0，仅匹配的 Sana 移动管线）；语音基座包含 sherpa-onnx（Apache-2.0）、MOSS Nano / SentencePiece（Apache-2.0）和 ONNX Runtime（MIT）。当前开发构建尚未完成真机验收。各模型按其来源仓库许可使用。</p><div class="modal-list"><div class="modal-list-item"><button data-action="engineLicense"><strong>llama.cpp MIT 许可证</strong><small>查看随应用附带的许可全文</small></button>' + icon('arrow') + '</div><div class="modal-list-item"><button data-action="notices"><strong>LMA 与其他依赖许可</strong><small>查看第三方许可全文</small></button>' + icon('arrow') + '</div></div>', 'about'); break;
      case 'engineLicense': openModal('llama.cpp · MIT License', '<div class="license-text">' + esc(window.LMA_LICENSE || 'MIT License\n\nCopyright (c) 2023-2026 The ggml authors\n\n完整许可证随 APK 的 licenses/LLAMA_CPP_LICENSE 一同分发，也位于项目 third_party/LLAMA_CPP_LICENSE。') + '</div>', 'license'); break;
      case 'notices': openModal('LMA 与第三方许可', Object.keys(window.LMA_NOTICES || {}).map(function (name) { return '<details class="license-notice"><summary>' + esc(name) + '</summary><div class="license-text">' + esc(window.LMA_NOTICES[name]) + '</div></details>'; }).join(''), 'license'); break;
    }
  }
  function updateFilters() { document.querySelectorAll('[data-filter]').forEach(function (b) { var active = b.dataset.filter === filter; b.classList.toggle('active', active); b.setAttribute('aria-pressed', active ? 'true' : 'false'); }); }
  function resizeInput() { var input = $('chatInput'); input.style.height = 'auto'; input.style.height = Math.min(150, Math.max(30, input.scrollHeight)) + 'px'; }
  document.addEventListener('click', function (event) {
    if (!event.target.closest('.editable-combo')) closeConfigPresets();
    var el = event.target.closest('[data-action]');
    if (el) { event.preventDefault(); handleAction(el.dataset.action, el); return; }
    var f = event.target.closest('[data-filter]'); if (f) selectFilter(f.dataset.filter);
    var t = event.target.closest('[data-task]');
    if (t) { taskFilter = t.dataset.task; document.querySelectorAll('[data-task]').forEach(function (b) { var active = b.dataset.task === taskFilter; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active)); }); modelSignature = ''; renderModels(); }
    if (event.target === $('modalBackdrop')) closeModal();
    if (event.target.closest('.brand')) { event.preventDefault(); route('models'); }
  });
  $('modelSearch').addEventListener('input', function () {
    query = this.value.trim(); clearTimeout(searchTimer);
    if (filter !== 'local') { filter = 'all'; updateFilters(); searchTimer = setTimeout(startHub, 550); }
    modelSignature = ''; renderModels();
  });
  $('modelSearch').addEventListener('keydown', function (event) { if (event.key === 'Enter' && filter === 'all') { event.preventDefault(); startHub(); } });
  ['hubFormat', 'hubSort'].forEach(function (id) { $(id).addEventListener('change', startHub); });
  $('hfTokenForm').addEventListener('submit', function (event) {
    event.preventDefault(); var token = $('hfTokenInput').value.trim();
    if (!token) { $('hfTokenHint').textContent = '请填写令牌，或点击清除'; return; }
    pendingHubToken = nativeAction('hubToken', {token: token});
    if (pendingHubToken) { $('hfTokenInput').value = ''; $('hfTokenHint').textContent = '正在保存…'; }
  });
  $('chatInput').addEventListener('input', function () { resizeInput(); renderChat(); });
  $('chatInput').addEventListener('keydown', function (event) { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) { event.preventDefault(); send(); } });
  function send() {
    if (engine().generating) { nativeAction('cancelChat'); return; }
    if (pendingDraft) return;
    var text = $('chatInput').value.trim();
    if (!text || !textAvailable()) return;
    var requestId = nativeAction('send', {text: text});
    if (requestId) { pendingDraft = {requestId: requestId, text: text}; renderChat(); }
  }
  $('chatForm').addEventListener('submit', function (event) { event.preventDefault(); send(); });
  $('lanToggle').addEventListener('change', function () { if (!nativeAction('saveSettings', {settings: {lan: this.checked}})) this.checked = !this.checked; });
  $('settingsForm').addEventListener('input', function () { settingsDirty = true; $('settingsHint').textContent = '有尚未保存的修改'; });
  $('settingsForm').addEventListener('change', function () { settingsDirty = true; $('settingsHint').textContent = '有尚未保存的修改'; });
  $('settingsForm').addEventListener('submit', function (event) {
    event.preventDefault(); if (!this.reportValidity()) return;
    var form = this, values = {};
    ['source', 'autoLoad', 'boot', 'port', 'theme'].forEach(function (key) { var f = form.elements.namedItem(key); values[key] = f.type === 'checkbox' ? f.checked : key === 'port' ? Number(f.value) : f.value; });
    var requestId = nativeAction('saveSettings', {settings: values});
    if (requestId) { pendingSettings = {requestId: requestId, values: values}; $('settingsHint').textContent = '正在保存…'; }
    else $('settingsHint').textContent = '请在 Android 应用中保存设置';
  });
  document.addEventListener('submit', function (event) {
    if (event.target.id === 'modelSettingsForm') {
      event.preventDefault(); if (!modelEditor || modelEditor.pending) return;
      ['context', 'threads', 'maxTokens', 'temperature'].forEach(function (key) { clampConfigField($('cfg-' + key)); });
      if (!event.target.reportValidity()) return;
      var values = {}, modelForm = event.target;
      ['threads', 'context', 'maxTokens', 'temperature', 'reasoning', 'systemPrompt'].forEach(function (key) { var field = modelForm.elements.namedItem(key); values[key] = configPresets[key] ? Number(field.value) : field.value; });
      modelEditor.pending = nativeAction('saveModelSettings', {id: modelEditor.id, settings: values});
      if (modelEditor.pending) { modelForm.querySelector('[type="submit"]').disabled = true; $('modelSettingsHint').textContent = '正在保存此模型的参数…'; }
      return;
    }
    if (event.target.id !== 'customModelForm') return;
    event.preventDefault(); var form = event.target;
    if (!form.reportValidity()) return;
    var url = form.elements.url.value.trim(); if (url.indexOf('https://') !== 0) { toast('请使用 HTTPS 下载链接'); return; }
    if (nativeAction('addModel', {name: form.elements.name.value.trim(), url: url, sha256: form.elements.sha256.value.trim()})) { closeModal(); route('models'); selectFilter('local'); }
  });
  document.addEventListener('focusout', function (event) {
    if (event.target.dataset.configNumber && modelEditor) clampConfigField(event.target);
    var combo = event.target.closest('.editable-combo'); if (combo && (!event.relatedTarget || !combo.contains(event.relatedTarget))) closeConfigPresets();
  });
  document.addEventListener('input', function (event) { if (event.target.closest('#modelSettingsForm')) $('modelSettingsHint').textContent = '有尚未保存的模型参数'; });
  document.addEventListener('keydown', function (event) {
    var input = event.target.closest('[data-config-number]');
    if (input && modelEditor) {
      var list = $('presets-' + input.dataset.configNumber), options = Array.prototype.slice.call(list.querySelectorAll('[role="option"]'));
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault(); if (list.hidden) { showConfigPresets(input.dataset.configNumber); options = Array.prototype.slice.call(list.querySelectorAll('[role="option"]')); }
        var current = options.findIndex(function (option) { return option.id === input.getAttribute('aria-activedescendant'); });
        var next = Math.max(0, Math.min(options.length - 1, current + (event.key === 'ArrowDown' ? 1 : -1)));
        if (options[next]) { options.forEach(function (option, index) { option.classList.toggle('focused', index === next); }); input.setAttribute('aria-activedescendant', options[next].id); options[next].scrollIntoView({block: 'nearest'}); } return;
      }
      if (event.key === 'Enter') {
        event.preventDefault(); var active = $(input.getAttribute('aria-activedescendant'));
        if (!list.hidden && active) handleAction('configValue', active); else { clampConfigField(input); closeConfigPresets(); } return;
      }
      if (event.key === 'Escape' && !list.hidden) { event.preventDefault(); closeConfigPresets(); return; }
      if (event.key === 'Tab') closeConfigPresets();
    }
    if (!$('modalBackdrop').hidden) {
      if (event.key === 'Escape') { event.preventDefault(); closeModal(); }
      if (event.key === 'Tab') {
        var focusable = Array.prototype.slice.call($('modal').querySelectorAll('button:not(:disabled):not([tabindex="-1"]), input, select, textarea, [tabindex="0"]')).filter(function (node) { return node.getClientRects().length; });
        var first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === $('modal'))) { event.preventDefault(); if (last) last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); if (first) first.focus(); }
      }
    } else if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { event.preventDefault(); route('models'); $('modelSearch').focus(); }
  });
  var themeMedia = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  if (themeMedia) { if (themeMedia.addEventListener) themeMedia.addEventListener('change', applyTheme); else if (themeMedia.addListener) themeMedia.addListener(applyTheme); }
  var bridge = {state: function () { return state || {}; }, esc: esc, copy: copy, bytes: bytes, icon: icon, dispatch: nativeAction, result: commandResult, openModal: openModal, closeModal: closeModal, toast: toast, route: route, selectLocal: function () { route('models'); selectFilter('local'); }, confirm: confirmAction};
  window.LMAFoundation.init(bridge); window.LMARecipes.init(bridge);
  window.LMA = {receive: receive, back: function () { if (!$('modalBackdrop').hidden) { closeModal(); return true; } if (tab !== 'models') { route('models'); return true; } return false; }};
  hydrateIcons(document); updateFilters();
  if (window.Android) { try { receive(window.Android.getSnapshot()); } catch (e) { $('runtimeDetail').textContent = '等待原生服务连接…'; } }
  else { $('runtimeDetail').textContent = '界面预览 · 下载和推理请使用 Android 应用'; renderModels(); renderChat(); }
}());
