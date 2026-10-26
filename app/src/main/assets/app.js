(function () {
  'use strict';
  var state = null, tab = 'models', filter = 'recommended', query = '', keyVisible = false;
  var modelSignature = '', chatSignature = '', settingsDirty = false, settingsFilled = false;
  var pendingSettings = null, pendingDraft = null, modalKind = '', returnFocus = null, toastTimer, requestSequence = 0;
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
    return Math.max(1, Math.round(value / 1000000)) + ' MB';
  }
  function memory(value) { return value ? (value / 1073741824).toFixed(1) + ' GiB' : '—'; }
  function models() { return state ? state.models || [] : []; }
  function modelById(id) { return models().filter(function (m) { return m.id === id; })[0]; }
  function engine() { return state ? state.engine || {} : {}; }
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
    if (['models', 'chat', 'server', 'settings'].indexOf(next) < 0) return;
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
      applyTheme(); renderRuntime(); renderModels(); renderChat(); renderServer();
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
      $('errorBanner').hidden = !state.error; $('errorText').textContent = state.error || '';
    } catch (e) { $('runtimeDetail').textContent = '状态读取失败：' + e.message; }
  }
  function commandResult(requestId) {
    var results = state.commandResults || (state.commandResult ? [state.commandResult] : []);
    return results.filter(function (result) { return result.requestId === requestId; })[0];
  }
  function renderRuntime() {
    var e = engine(), m = modelById(e.modelId), loading = e.state === 'loading' || e.state === 'recovering';
    $('runtimeDot').className = 'runtime-dot' + (e.state === 'ready' ? ' ready' : loading ? ' loading' : e.state === 'error' ? ' error' : '');
    $('runtimeName').textContent = m && e.state !== 'stopped' ? m.name : e.state === 'error' ? '模型加载失败' : '尚未加载模型';
    $('runtimeDetail').textContent = e.generating ? '正在本地生成 · 切到后台后继续' : e.detail || '下载一个模型，开始本地运行';
    var d = state.device || {};
    $('deviceName').textContent = d.name || 'Android · 本地运行';
    $('deviceMemory').textContent = memory(d.totalMemory);
    $('deviceStorage').textContent = bytes(d.freeStorage);
    $('installedCount').textContent = models().filter(function (x) { return x.installed; }).length;
  }
  function modelCard(m) {
    var d = m.download || {}, s = d.state || '', running = engine().modelId === m.id && ['ready', 'loading', 'recovering'].indexOf(engine().state) >= 0;
    var active = ['queued', 'downloading', 'verifying', 'pausing'].indexOf(s) >= 0, partial = m.partialBytes || d.received || 0;
    var total = d.total || m.bytes || 0, progress = total ? Math.min(100, Math.floor(partial * 100 / total)) : 0;
    var action = m.installed ? (running ? '' : 'load') : s === 'pausing' ? '' : active ? 'pauseDownload' : (partial || s === 'paused' || s === 'error') ? 'resumeDownload' : 'download';
    var label = m.installed ? (running ? engine().state === 'ready' ? '运行中' : '加载中' : '加载模型') : active ? s === 'pausing' ? '暂停中' : s === 'verifying' ? '校验中' : '暂停' : partial || s === 'paused' || s === 'error' ? '继续下载' : '下载';
    var glyph = m.family === 'LFM' ? 'L' : m.family === 'Gemma' ? 'G' : m.family === 'Llama' ? 'L' : m.family === '自定义' ? '+' : 'Q';
    var tags = (m.tags || []).slice(0, 4).map(function (tag) { return '<span class="tag' + (tag === '推荐' ? ' recommended' : m.tier === 'experimental' ? ' experimental' : '') + '">' + esc(tag) + '</span>'; }).join('');
    tags = '<span class="tag">' + (m.uncensored && m.uncensored.declared ? '无审查' : '属性未核对') + '</span>' + tags;
    if (m.recommended && (m.tags || []).indexOf('推荐') < 0) tags = '<span class="tag recommended">推荐</span>' + tags;
    var size = m.installed ? m.installedBytes : total;
    var out = '<article class="model-card' + (running ? ' is-running' : '') + '" data-model="' + esc(m.id) + '"><div class="model-top"><span class="model-symbol" data-family="' + esc(m.family) + '">' + glyph + '</span><div class="model-top-copy"><button class="model-name" data-action="modelInfo" data-id="' + esc(m.id) + '"><strong>' + esc(m.name) + '</strong><span class="model-caption">' + esc(m.family) + ' <span aria-hidden="true"> / </span> ' + esc(m.quant || 'GGUF') + '</span></button></div></div>';
    if (running) out += '<span class="running-mark">' + (engine().state === 'ready' ? '已加载' : '加载中') + '</span>';
    out += '<p class="model-description">' + esc(m.description) + '</p><div class="model-tags">' + tags + '</div><div class="model-footer"><div class="model-size">' + bytes(size) + '<small>' + (m.installed ? '已下载到设备' : m.sizeIsApproximate && !d.total ? '预估下载体积' : 'GGUF 模型文件') + '</small></div><div class="model-footer-actions"><button class="button ' + (m.installed || active ? 'subtle' : 'primary') + '" data-action="' + action + '" data-id="' + esc(m.id) + '"' + (!action ? ' disabled' : '') + '>' + icon(m.installed ? running ? 'check' : 'play' : active ? 'pause' : 'download') + '<span>' + label + '</span></button>';
    if ((m.installed || partial || m.id.indexOf('custom_') === 0 || s === 'error') && !active) out += '<button class="icon-button" data-action="deleteModel" data-id="' + esc(m.id) + '" aria-label="删除 ' + esc(m.name) + '">' + icon('trash') + '</button>';
    out += '</div></div>';
    if (!m.installed && (active || partial || s === 'paused')) {
      var status = s === 'queued' ? '等待下载' : s === 'verifying' ? '校验 SHA256…' : s === 'paused' ? '已暂停' : s === 'error' ? '下载中断' : d.speed ? bytes(d.speed) + '/s' : '正在连接…';
      out += '<div class="download-progress"><div class="progress-track" role="progressbar" aria-label="下载进度" aria-valuemin="0" aria-valuemax="100" aria-valuenow="' + progress + '"><span style="width:' + progress + '%"></span></div><div class="download-meta"><span>' + status + '</span><span>' + (partial ? bytes(partial) : '0 MB') + (total ? ' / ' + bytes(total) : '') + '</span></div></div>';
    }
    if (!m.installed && d.error) out += '<div class="download-error">' + esc(d.error) + '</div>';
    return out + '</article>';
  }
  function renderModels() {
    var all = models().filter(function (m) {
      var included = filter === 'all' || filter === 'recommended' && m.recommended || filter === 'light' && m.tier === 'light' || filter === 'quality' && (m.tier === 'quality' || m.tier === 'experimental') || filter === 'installed' && m.installed;
      return included && (!query || [m.name, m.family, m.description, (m.tags || []).join(' ')].join(' ').toLowerCase().indexOf(query) >= 0);
    });
    var signature = JSON.stringify([all, engine().state, engine().modelId, filter, query]);
    if (signature === modelSignature) return; modelSignature = signature;
    var focused = document.activeElement && document.activeElement.closest('#modelList button'), focusAction = focused && focused.dataset.action, focusId = focused && focused.dataset.id;
    $('modelListTitle').textContent = query ? '搜索结果' : {recommended: '适合先试的模型', light: '先从轻量开始', quality: '更高容量的选择', installed: '你的本地模型', all: '全部模型'}[filter];
    $('modelResultCount').textContent = all.length + ' 个模型';
    $('modelList').innerHTML = all.length ? all.map(modelCard).join('') : '<div class="empty-list"><h3>' + (filter === 'installed' && !query ? '还没有下载模型' : '没有匹配的模型') + '</h3><p>' + (filter === 'installed' ? '在模型库中选择模型，下载后就能离线使用。' : '尝试其他关键词，或添加自己的 GGUF 文件。') + '</p><button class="button subtle" data-action="showAll">浏览全部模型</button></div>';
    if (focusId) $('modelList').querySelectorAll('button').forEach(function (b) { if (b.dataset.action === focusAction && b.dataset.id === focusId) b.focus({preventScroll: true}); });
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
    $('composerHint').textContent = e.generating ? '后台继续生成 · 点击方块停止' : e.state === 'ready' ? '回复在当前手机生成' : e.state === 'loading' || e.state === 'recovering' ? '模型正在加载，请稍候…' : '先加载一个模型，再开始对话';
    $('sendButton').classList.toggle('stop', !!e.generating);
    $('sendButton').setAttribute('aria-label', e.generating ? '停止生成' : '发送消息');
    $('sendButton').innerHTML = icon(e.generating ? 'stop' : 'send');
    $('sendButton').disabled = !e.generating && (!!pendingDraft || e.state !== 'ready' || !$('chatInput').value.trim());
    var signature = JSON.stringify(chat);
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
      if (status === 'generating') footer.push('生成中');
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
    var e = engine(), ready = e.state === 'ready', active = ready || e.state === 'loading' || e.state === 'recovering', m = modelById(e.modelId);
    $('serverStateLabel').textContent = ready ? '接口正在运行' : active ? '正在启动接口' : e.state === 'error' ? '模型加载失败' : '接口尚未启动';
    $('serverStatePill').textContent = ready ? '运行中' : active ? '加载中' : e.state === 'error' ? '启动失败' : '未启动';
    $('serverStatePill').className = 'status-pill' + (ready ? ' ready' : active ? ' loading' : '');
    $('serverModelName').textContent = m ? m.name : '选择已下载的模型';
    $('apiUrl').textContent = endpoint();
    $('serverToggle').innerHTML = icon(active ? 'stop' : 'play') + '<span>' + (active ? '停止服务' : '启动服务') + '</span>';
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
    ['source', 'autoLoad', 'boot', 'threads', 'context', 'maxTokens', 'temperature', 'port', 'reasoning', 'systemPrompt', 'theme'].forEach(function (key) {
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
  function closeModal() {
    if ($('modalBackdrop').hidden) return;
    $('modalBackdrop').hidden = true; modalKind = '';
    document.querySelector('.app-shell').removeAttribute('aria-hidden');
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus({preventScroll: true}); returnFocus = null;
  }
  function confirmAction(title, message, action, id, button) {
    openModal(title, '<p>' + esc(message) + '</p><div class="modal-actions"><button class="button secondary" data-action="closeModal">取消</button><button class="button danger" data-action="confirmed" data-command="' + esc(action) + '" data-id="' + esc(id) + '">' + esc(button || '确认删除') + '</button></div>', 'confirm');
  }
  function pickModel() {
    var installed = models().filter(function (m) { return m.installed; });
    openModal('选择本地模型', installed.length ? '<p>加载后会同时开启本机 API 服务。</p><div class="modal-list">' + installed.map(function (m) { return '<div class="modal-list-item"><button data-action="load" data-id="' + esc(m.id) + '"><strong>' + esc(m.name) + '</strong><small>' + esc(m.quant) + ' · ' + bytes(m.installedBytes) + '</small></button>' + icon('arrow') + '</div>'; }).join('') + '</div>' : '<p>先下载一个模型，或从设备导入 GGUF 文件。</p><button class="button primary" data-action="tab" data-tab="models">前往模型库</button>', 'pickModel');
  }
  function modelInfo(id) {
    var m = modelById(id); if (!m) return; var d = m.download || {}, u = m.uncensored || {};
    var declaration = u.declared ? '<p><strong>无审查 · ' + esc(u.method === 'abliterated' ? 'Abliterated 去拒答' : u.method === 'uncensored-instruct' ? 'Dolphin 微调' : 'Uncensored 权重') + '</strong></p><p>' + esc(u.summary) + '</p>' : '<p>自定义模型尚未核对无审查属性。</p>';
    var source = m.sourceUrl || m.url ? '<button class="button secondary" data-action="sourceLink" data-id="' + esc(m.id) + '">' + icon('link') + '查看 GGUF 来源与许可</button>' : '';
    var evidence = u.declared && u.evidenceUrl ? '<p><button class="text-button" data-action="uncensoredSource" data-id="' + esc(m.id) + '">查看作者的无审查说明 ↗</button></p>' : '';
    openModal(m.name, '<div class="model-info"><p>' + esc(m.description) + '</p>' + declaration + '<dl><dt>文件</dt><dd>' + esc(m.filename || m.name + '.gguf') + '</dd><dt>格式</dt><dd>' + esc(m.quant || 'GGUF') + '</dd><dt>模型 ID</dt><dd>' + esc(m.id) + '</dd><dt>发布者哈希</dt><dd>' + esc(m.sha256 || '未提供，可对照原始模型仓库') + '</dd>' + (d.sha256 ? '<dt>本地 SHA256</dt><dd>' + esc(d.sha256) + '</dd>' : '') + '<dt>文件验证</dt><dd>' + (d.verification === 'publisher-sha256' ? '与发布者 SHA256 一致' : m.installed ? 'GGUF 格式与传输完整性检查' : '下载完成后校验') + '</dd></dl>' + source + evidence + '<p class="modal-help">无审查属性依据作者说明核对，实际拒答率与手机运行表现尚未实测。应用不额外过滤提示词或模型回复；系统提示词可在设置中修改。</p></div>', 'modelInfo');
  }
  function history() {
    var sessions = state && state.chat ? state.chat.sessions || [] : [];
    openModal('对话历史', sessions.length ? '<div class="modal-list">' + sessions.map(function (s) { var m = modelById(s.modelId); return '<div class="modal-list-item"><button data-action="selectSession" data-id="' + esc(s.id) + '"><strong>' + esc(s.title) + '</strong><small>' + new Date(s.updated).toLocaleDateString('zh-CN') + (m ? ' · ' + esc(m.name) : '') + '</small></button><button class="icon-button" data-action="deleteSession" data-id="' + esc(s.id) + '" aria-label="删除这段对话">' + icon('trash') + '</button></div>'; }).join('') + '</div>' : '<p>还没有对话。生成的回复会自动保存在手机上。</p>', 'history');
  }
  function handleAction(action, el) {
    var id = el.dataset.id, m;
    switch (action) {
      case 'tab': route(el.dataset.tab); break;
      case 'showAll': filter = 'all'; query = ''; $('modelSearch').value = ''; updateFilters(); renderModels(); break;
      case 'download': case 'resumeDownload': if (nativeAction(action, {id: id})) toast('已提交下载任务'); break;
      case 'pauseDownload': nativeAction(action, {id: id}); break;
      case 'load': if (nativeAction(action, {id: id})) { closeModal(); toast('正在加载模型'); } break;
      case 'deleteModel': m = modelById(id); if (m) confirmAction('删除模型文件', '删除“' + m.name + '”的本地文件和下载记录。需要时可以重新下载。', action, id); break;
      case 'confirmed': nativeAction(el.dataset.command, {id: id}); closeModal(); break;
      case 'modelInfo': modelInfo(id); break;
      case 'sourceLink': m = modelById(id); if (m && window.Android) window.Android.openLink(m.sourceUrl || m.url); break;
      case 'uncensoredSource': m = modelById(id); if (m && m.uncensored && window.Android) window.Android.openLink(m.uncensored.evidenceUrl); break;
      case 'pickModel': pickModel(); break;
      case 'toggleServer':
        if (['ready', 'loading', 'recovering'].indexOf(engine().state) >= 0) nativeAction('stopEngine');
        else { m = modelById(engine().modelId); if (m && m.installed) nativeAction('load', {id: m.id}); else pickModel(); }
        break;
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
      case 'addMenu': openModal('添加你的模型', '<div class="modal-list"><div class="modal-list-item"><button data-action="addUrl"><strong>从下载链接添加</strong><small>输入 GGUF 的 HTTPS 直链，支持断点续传</small></button>' + icon('link') + '</div><div class="modal-list-item"><button data-action="importPicker"><strong>从设备导入</strong><small>选择已下载的 .gguf 文件</small></button>' + icon('upload') + '</div></div>', 'add'); break;
      case 'addUrl': openModal('添加 GGUF 下载链接', '<form id="customModelForm"><label class="form-field"><span>模型名称</span><input name="name" required maxlength="160" placeholder="例如：我的 Qwen 1.7B"></label><label class="form-field"><span>HTTPS 下载链接</span><input name="url" type="url" required placeholder="https://huggingface.co/…/resolve/main/….gguf" autocapitalize="off" spellcheck="false"></label><label class="form-field"><span>SHA256（可选）</span><input name="sha256" pattern="[a-fA-F0-9]{64}" maxlength="64" placeholder="发布者提供的 64 位哈希" autocapitalize="off" spellcheck="false"></label><p class="modal-help">请确认模型使用当前推理组件支持的架构，且适合手机的内存容量。</p><button type="submit" class="button primary">添加并下载</button></form>', 'addUrl'); break;
      case 'importPicker': nativeAction(action); closeModal(); break;
      case 'about': openModal('关于 LMA', '<p>LMA 0.1.2 是本地模型工作台，使用 Android 前台服务运行 llama.cpp。无需 ROOT；首次使用需要下载或导入模型。</p><p>界面、对话记录和推理在设备本地运行。模型下载会连接你选择的仓库；开启局域网后，持有 API 密钥的同网设备可以请求推理。</p><p>前台通知、唤醒锁与电池设置可帮助后台运行。系统强行停止、内存不足、厂商省电策略、发热或重启仍会影响服务。模型输出和速度尚需目标手机实测。</p><p>推理引擎：llama.cpp（MIT），由 ServLlama v1.2.2 分发的 Android ARM64 预编译组件。各模型按其来源仓库许可使用。</p><div class="modal-list"><div class="modal-list-item"><button data-action="engineLicense"><strong>llama.cpp MIT 许可证</strong><small>查看随应用附带的许可全文</small></button>' + icon('arrow') + '</div><div class="modal-list-item"><button data-action="notices"><strong>LMA 与其他依赖许可</strong><small>查看第三方许可全文</small></button>' + icon('arrow') + '</div></div>', 'about'); break;
      case 'engineLicense': openModal('llama.cpp · MIT License', '<div class="license-text">' + esc(window.LMA_LICENSE || 'MIT License\n\nCopyright (c) 2023-2026 The ggml authors\n\n完整许可证随 APK 的 licenses/LLAMA_CPP_LICENSE 一同分发，也位于项目 third_party/LLAMA_CPP_LICENSE。') + '</div>', 'license'); break;
      case 'notices': openModal('LMA 与第三方许可', Object.keys(window.LMA_NOTICES || {}).map(function (name) { return '<details class="license-notice"><summary>' + esc(name) + '</summary><div class="license-text">' + esc(window.LMA_NOTICES[name]) + '</div></details>'; }).join(''), 'license'); break;
    }
  }
  function updateFilters() { document.querySelectorAll('[data-filter]').forEach(function (b) { var active = b.dataset.filter === filter; b.classList.toggle('active', active); b.setAttribute('aria-pressed', active ? 'true' : 'false'); }); }
  function resizeInput() { var input = $('chatInput'); input.style.height = 'auto'; input.style.height = Math.min(150, Math.max(30, input.scrollHeight)) + 'px'; }
  document.addEventListener('click', function (event) {
    var el = event.target.closest('[data-action]');
    if (el) { event.preventDefault(); handleAction(el.dataset.action, el); return; }
    var f = event.target.closest('[data-filter]'); if (f) { filter = f.dataset.filter; updateFilters(); renderModels(); }
    if (event.target === $('modalBackdrop')) closeModal();
    if (event.target.closest('.brand')) { event.preventDefault(); route('models'); }
  });
  $('modelSearch').addEventListener('input', function () { query = this.value.trim().toLowerCase(); renderModels(); });
  $('chatInput').addEventListener('input', function () { resizeInput(); renderChat(); });
  $('chatInput').addEventListener('keydown', function (event) { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) { event.preventDefault(); send(); } });
  function send() {
    if (engine().generating) { nativeAction('cancelChat'); return; }
    if (pendingDraft) return;
    var text = $('chatInput').value.trim();
    if (!text || engine().state !== 'ready') return;
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
    ['source', 'autoLoad', 'boot', 'threads', 'context', 'maxTokens', 'temperature', 'port', 'reasoning', 'systemPrompt', 'theme'].forEach(function (key) { var f = form.elements.namedItem(key); values[key] = f.type === 'checkbox' ? f.checked : ['threads', 'context', 'maxTokens', 'temperature', 'port'].indexOf(key) >= 0 ? Number(f.value) : f.value; });
    var requestId = nativeAction('saveSettings', {settings: values});
    if (requestId) { pendingSettings = {requestId: requestId, values: values}; $('settingsHint').textContent = '正在保存…'; }
    else $('settingsHint').textContent = '请在 Android 应用中保存设置';
  });
  document.addEventListener('submit', function (event) {
    if (event.target.id !== 'customModelForm') return;
    event.preventDefault(); var form = event.target;
    if (!form.reportValidity()) return;
    var url = form.elements.url.value.trim(); if (url.indexOf('https://') !== 0) { toast('请使用 HTTPS 下载链接'); return; }
    if (nativeAction('addModel', {name: form.elements.name.value.trim(), url: url, sha256: form.elements.sha256.value.trim()})) { closeModal(); route('models'); filter = 'all'; updateFilters(); renderModels(); }
  });
  document.addEventListener('keydown', function (event) {
    if (!$('modalBackdrop').hidden) {
      if (event.key === 'Escape') { event.preventDefault(); closeModal(); }
      if (event.key === 'Tab') {
        var focusable = Array.prototype.slice.call($('modal').querySelectorAll('button:not(:disabled), input, select, textarea, [tabindex="0"]'));
        var first = focusable[0], last = focusable[focusable.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === $('modal'))) { event.preventDefault(); if (last) last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); if (first) first.focus(); }
      }
    } else if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) { event.preventDefault(); route('models'); $('modelSearch').focus(); }
  });
  var themeMedia = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
  if (themeMedia) { if (themeMedia.addEventListener) themeMedia.addEventListener('change', applyTheme); else if (themeMedia.addListener) themeMedia.addListener(applyTheme); }
  window.LMA = {receive: receive, back: function () { if (!$('modalBackdrop').hidden) { closeModal(); return true; } if (tab !== 'models') { route('models'); return true; } return false; }};
  hydrateIcons(document); updateFilters();
  if (window.Android) { try { receive(window.Android.getSnapshot()); } catch (e) { $('runtimeDetail').textContent = '等待原生服务连接…'; } }
  else { $('runtimeDetail').textContent = '界面预览 · 下载和推理请使用 Android 应用'; renderModels(); renderChat(); }
}());
