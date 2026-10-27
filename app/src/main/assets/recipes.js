(function () {
  'use strict';
  var ui, mode = '', role = '', signature = '', epoch = 0, pending = {}, busy = false;
  function $(id) { return document.getElementById(id); }
  function hub() { return ui.state().hub || {}; }
  function draft() { return hub().recipeDraft || {}; }
  function e(value) { return ui.esc(value == null ? '' : String(value)); }
  function templates() { return hub().recipeTemplates || []; }
  function template() { return templates().filter(function (t) { return t.id === draft().templateId; })[0]; }
  function rule() { var t = template(); return t && t.requirements.filter(function (r) { return r.role === role; })[0]; }
  function owned() { return mode && !$('modalBackdrop').hidden && !!$('recipePanel'); }
  function run(action, values, callback) {
    if (busy) return; var id = ui.dispatch(action, values); if (!id) return;
    busy = true; var generation = epoch;
    pending[id] = {epoch: generation, callback: callback};
    if (owned()) $('recipePanel').querySelectorAll('button,select').forEach(function (b) { b.disabled = true; });
  }
  function open(next) { mode = next; signature = ''; render(true); }
  function digest(c) { return c.sha256 ? 'SHA256 ' + c.sha256 : 'Git blob SHA-1 ' + (c.gitBlobSha1 || '缺失'); }
  function component(c) {
    return '<details><summary>' + e(c.role || c.path) + ' · ' + ui.bytes(c.bytes) + '</summary><p class="hub-repository">' + e(c.repository) + ' / ' + e(c.path) + '</p><p class="modal-help">固定版本 ' + e(c.revision) + '</p><code>' + e(digest(c)) + '</code></details>';
  }
  function form() {
    var d = draft(), t = template(), bindings = d.bindings || {}, total = 0, complete = !!t;
    var html = '<p>从 HF 选择配套组件，加入本地后再确认下载。这里只保存选择，不下载文件。</p><label class="form-field">运行配方<select id="recipeTemplate"><option value="">请选择架构与组件配方</option>' + templates().map(function (v) { return '<option value="' + e(v.id) + '"' + (v.id === d.templateId ? ' selected' : '') + '>' + e(v.name) + '</option>'; }).join('') + '</select></label>';
    if (t) {
      var engine = (ui.state().localEngines || []).filter(function (v) { return v.engine === t.definition.engine; })[0];
      html += '<div class="model-tags">' + (t.definition.tasks || []).map(function (task) { return '<span class="tag">' + e({text: '生文', image: '生图', video: '生视频', audio: '生音频'}[task] || task) + '</span>'; }).join('') + '<span class="tag">' + e(t.definition.engine) + '</span><span class="tag">' + e(t.definition.backend) + '</span></div><p class="modal-help">' + e(t.help) + '</p><p class="modal-help">' + (engine && engine.available ? 'App 已包含这个引擎；所选文件的架构与手机运行仍需核对。' : '当前基座未提供可用引擎；登记或下载不能安装引擎。') + '</p>';
      html += '<div class="hub-files">' + t.requirements.map(function (r) {
        var c = bindings[r.role]; if (c) total += Number(c.bytes); else if (r.required !== false) complete = false;
        return '<article class="hub-file"><strong>' + e(r.label) + '</strong><small>' + e(r.formats.join(' / ')) + (r.required !== false ? ' · 必需' : ' · 可选') + '</small>' + (c ? component(Object.assign({role: r.role}, c)) : '<p>尚未选择</p>') + '<button class="button secondary" data-action="recipePick" data-role="' + e(r.role) + '">' + (c ? '更换组件' : '选择组件') + '</button></article>';
      }).join('') + '</div>';
      if (t.fixedComponents.length) html += '<p>这套配方还需要以下固定依赖；确认下载时一并展示：</p><div class="bundle-components">' + t.fixedComponents.map(function (c) { total += Number(c.bytes); return component(c); }).join('') + '</div>';
      html += '<p>已选总大小：' + ui.bytes(total) + '。实际剩余传输与可复用资产在下载计划中计算。</p>';
    }
    html += '<p id="recipeHint" class="form-help" role="status"></p><div class="modal-actions"><button class="button secondary" data-action="closeModal">关闭</button><button class="button primary" data-action="recipeDeclare"' + (!complete ? ' disabled' : '') + '>加入本地并查看下载计划</button></div>';
    return html;
  }
  function picker() {
    var d = draft(), r = rule(), f = hub().files || {}, repo = f.repository || {}, bound = (d.bindings || {})[role], origin = d.origin || {};
    if (!r) return '<p>配方已变化，请返回重新选择。</p><button class="button secondary" data-action="recipeBack">返回配方</button>';
    var html = '<p>' + e(r.label) + ' · ' + e(r.formats.join(' / ')) + '</p><label class="form-field">HF 仓库 ID<input id="recipeRepository" type="text" autocapitalize="off" spellcheck="false" value="' + e(repo.id || bound && bound.repository || origin.id || '') + '" placeholder="作者/仓库"></label><button class="button secondary" data-action="recipeLookup">查看仓库文件</button>';
    if (repo.revision) html += '<p class="modal-help">' + e(repo.id) + ' · 固定版本 ' + e(repo.revision) + '</p>';
    if (f.loading) html += '<p role="status">正在读取文件元数据…</p>';
    else if (f.error) html += '<p class="download-error">' + e(f.error) + '</p><button class="button secondary" data-action="recipePage" data-direction="retry">重试</button>';
    else {
      var assets = (f.assets || []).filter(function (c) { return r.formats.indexOf(c.format) >= 0; });
      html += assets.length ? '<div class="hub-files">' + assets.map(function (c) { return '<article class="hub-file"><strong>' + e(c.path) + '</strong><small>' + e(c.format) + ' · ' + ui.bytes(c.bytes) + (c.sha256 ? ' · SHA256' : ' · Git blob SHA-1') + '</small>' + (c.blocked ? '<p class="download-error">' + e(c.blocked) + '</p>' : '') + '<button class="button secondary" data-action="recipeBind" data-path="' + e(c.path) + '"' + (c.blocked ? ' disabled' : '') + '>选择此文件</button></article>'; }).join('') + '</div>' : '<p>本页没有此角色的文件。可翻页或输入其他配套仓库。</p>';
    }
    html += '<div class="hub-pagination"><button class="button secondary" data-action="recipePage" data-direction="previous"' + (!f.previous || f.loading ? ' disabled' : '') + '>上一页</button><span>第 ' + Number(f.page || 1) + ' 页</span><button class="button secondary" data-action="recipePage" data-direction="next"' + (!f.next || f.loading ? ' disabled' : '') + '>下一页</button></div><p class="modal-help">浏览只获取元数据。普通 Git 文件校验 Git blob SHA-1，并保存实际 SHA256；LFS 文件按发布者 SHA256 校验。文件扩展名不能证明架构、语言、许可或设备兼容。</p><p id="recipeHint" class="form-help" role="status"></p><button class="button secondary" data-action="recipeBack">返回配方</button>';
    return html;
  }
  function render(force) {
    if (!force && !owned()) return;
    var next = JSON.stringify([mode, role, hub().recipeDraft, mode === 'pick' ? hub().files : hub().recipeTemplates]);
    if (!force && next === signature) return; signature = next;
    var input = $('recipeRepository'), editing = input && document.activeElement === input, typed = input && input.value, selection = editing && input.selectionStart;
    ui.openModal(mode === 'pick' ? '选择 HF 组件文件' : '构建本地模型配方', '<div id="recipePanel">' + (mode === 'starting' ? '<p role="status">正在建立配方草稿…</p>' : mode === 'pick' ? picker() : form()) + '</div>', 'recipe');
    if (editing && $('recipeRepository')) { $('recipeRepository').value = typed; $('recipeRepository').focus(); $('recipeRepository').setSelectionRange(selection, selection); }
    if (busy) $('recipePanel').querySelectorAll('button,select').forEach(function (b) { b.disabled = true; });
  }
  function handle(action, el) {
    var d = draft(), f = hub().files || {}, repo = f.repository || {};
    switch (action) {
      case 'recipeStart':
        epoch++; busy = false; open('starting');
        run('hubRecipeStart', {repository: el.dataset.repository}, function () { open('form'); }); return true;
      case 'recipePick': role = el.dataset.role; open('pick'); return true;
      case 'recipeBack': open('form'); return true;
      case 'recipeLookup':
        run('hubFiles', {repository: $('recipeRepository').value.trim()}, function () { render(true); }); return true;
      case 'recipePage': run('hubFilePage', {direction: el.dataset.direction}, function () { render(true); }); return true;
      case 'recipeBind':
        run('hubRecipeBind', {draftId: d.draftId, role: role, repository: repo.id, revision: repo.revision, path: el.dataset.path}, function () { open('form'); }); return true;
      case 'recipeDeclare':
        run('hubRecipeDeclare', {draftId: d.draftId}, function (result) {
          if (!result || !result.bundleId) { ui.toast('配方登记结果不完整，请在本地检查'); return; }
          ui.closeModal(); ui.selectLocal(); window.LMAFoundation.handle('bundleInfo', {dataset: {id: result.bundleId}});
        }); return true;
      default: return false;
    }
  }
  window.LMARecipes = {
    init: function (bridge) {
      ui = bridge;
      document.addEventListener('change', function (event) {
        if (event.target.id === 'recipeTemplate' && owned() && event.target.value) run('hubRecipeTemplate', {draftId: draft().draftId, templateId: event.target.value}, function () { open('form'); });
      });
      document.addEventListener('keydown', function (event) { if (event.target.id === 'recipeRepository' && event.key === 'Enter') { event.preventDefault(); handle('recipeLookup', event.target); } });
    },
    handle: handle,
    receive: function () {
      Object.keys(pending).forEach(function (id) {
        var result = ui.result(id); if (!result) return;
        var entry = pending[id]; delete pending[id]; if (entry.epoch !== epoch || !owned()) return;
        busy = false;
        if (result.ok) entry.callback(result.data);
        else { if (mode === 'starting') open('form'); else render(true); if ($('recipeHint')) $('recipeHint').textContent = result.error || '选择失败，请重试'; ui.toast(result.error || '操作失败'); }
      });
      render(false);
    },
    close: function () { mode = ''; busy = false; epoch++; }
  };
}());
