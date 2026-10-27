(function () {
  'use strict';
  var ui, panel = null, pending = {};
  var reasons = {retained: '沿用', clamped: '按新版本上限归位', new_default: '新增参数使用默认值', removed: '新版本已移除此参数', type_reset: '类型变化，使用默认值', selection_reset: '原选项不可用，使用默认值', length_reset: '文本超过新限制，使用默认值', joint_shape_reset: '尺寸组合不兼容，使用新默认组合', target_settings: '保留目标版本设置'};
  var changes = {added: '新增', removed: '移除', changed: '内容变化', unchanged: '内容与来源一致', source_changed: '内容相同，来源或路径变化'};
  function e(v) { return ui.esc(v); }
  function entries() { return ui.state().bundles || []; }
  function find(id) { return entries().filter(function (b) { return b.id === id; })[0]; }
  function button(action, text, primary, disabled, extra) { return '<button type="button" class="button ' + (primary ? 'primary' : 'secondary') + '" data-action="' + action + '" data-version-submit' + (disabled ? ' disabled' : '') + (extra || '') + '>' + text + '</button>'; }
  function canonical(value) { if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']'; if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(function (k) { return JSON.stringify(k) + ':' + canonical(value[k]); }).join(',') + '}'; return JSON.stringify(value === undefined ? null : value); }
  function compatible(a, b) { var x = a.manifest, y = b.manifest; return a.id !== b.id && ['engine', 'architecture', 'pipeline', 'backend'].every(function (key) { return x[key] === y[key]; }) && canonical((x.tasks || []).slice().sort()) === canonical((y.tasks || []).slice().sort()) && canonical(x.adapter) === canonical(y.adapter) && (!b.version || !b.version.groupId || b.version.groupId === (a.version || {}).groupId); }
  function call(action, args, callback) {
    var editing = panel, id = ui.dispatch(action, args); if (!id) return;
    var enabled = [];
    if (editing) { editing.busy = true; document.querySelectorAll('#modalContent [data-version-submit]').forEach(function (b) { if (!b.disabled) { enabled.push(b); b.disabled = true; } }); }
    pending[id] = {editing: editing, callback: callback, enabled: enabled};
  }
  function value(v) { return v === null || v === undefined ? '—' : typeof v === 'object' ? JSON.stringify(v) : String(v); }
  function pendingHelp(source) {
    var p = (source.version || {}).pending; if (!p) return '';
    var target = find(p.toBundleId), t = target && target.transfer || {};
    var status = p.stale ? '模型设置或版本发生变化，请取消计划后重新核对。' : p.ready ? '新版本组件已校验，等待你确认切换。' : ({queued: '新版本等待下载。', downloading: '正在下载新版本组件。', verifying: '正在校验新版本。', installing: '正在安装新版本。', paused: '新版本下载已暂停。', failed: '新版本下载失败，旧版本保留。'}[t.state] || '更新计划已保留，等待下载或导入。');
    return '<div class="version-pending"><strong>待更新：' + e(p.targetName || p.toBundleId) + '</strong><p role="status">' + e(status) + '</p>' + (t.error ? '<p class="download-error">' + e(t.error) + '</p>' : '') + '<div class="modal-actions">' + button('versionPendingReview', '核对更新', p.ready, p.stale) + (!p.stale && !p.ready && ['queued', 'downloading', 'verifying', 'installing'].indexOf(t.state) < 0 ? button('resumeBundle', '继续下载', false, false, ' data-id="' + e(p.toBundleId) + '"') : '') + button('versionCancel', '取消更新计划') + '</div></div>';
  }
  function signature(b, choices) {
    var update = (b.version || {}).pending, target = update && find(update.toBundleId);
    return canonical(b.version) + canonical(choices.map(function (x) { return [x.id, x.installed]; })) + canonical(target && [target.transfer && target.transfer.state, target.transfer && target.transfer.error]);
  }
  function overview(id, selected, mode) {
    var b = find(id); if (!b) return;
    var active = (b.version || {}).activeBundleId || id; b = find(active); if (!b) return;
    var choices = entries().filter(function (other) { return compatible(b, other); });
    var v = b.version || {}, html = '<div class="version-manager"><p class="eyebrow">MODEL VERSIONS</p><p>当前版本：<strong>' + e(b.manifest.name) + '</strong></p><code>' + e(b.id) + '</code><p class="form-help">先在“全部 / 搜索”的 HF 配方中登记新版本，或导入新的模型清单，再选择更新目标。登记不下载；下方只列相同架构、引擎、管线、后端和功能的候选。目标由你指定，不代表发布者已确认版本关系。</p>' + pendingHelp(b);
    if (!v.pending) html += '<form id="bundleVersionForm"><label class="form-field"><span>更新目标 / 保留的旧版本</span><select name="target" required>' + (choices.length ? '<option value="">请选择版本</option>' : '<option value="">尚无兼容候选，请先登记新清单</option>') + choices.map(function (c) { return '<option value="' + e(c.id) + '"' + (c.id === selected ? ' selected' : '') + '>' + e(c.manifest.name) + (c.installed ? ' · 已安装' : ' · 尚未下载') + ' · ' + e(c.id) + '</option>'; }).join('') + '</select></label><label class="form-field"><span>新版本参数</span><select name="settingsMode"><option value="copy"' + (mode !== 'keep' ? ' selected' : '') + '>沿用当前版本参数，按新约束调整</option><option value="keep"' + (mode === 'keep' ? ' selected' : '') + '>保留目标版本原有参数 / 默认值</option></select></label><div class="modal-actions"><button class="button primary" type="submit" data-version-submit' + (!choices.length ? ' disabled' : '') + '>核对组件与参数差异</button></div></form>';
    html += '<p class="modal-help">下载、安装和切换是不同操作。校验完成后仍需确认切换；旧版本及其参数会保留，既有任务使用原固定版本。回退时可选择“保留目标版本原有参数”。</p>' + button('versionHistory', '查看切换记录', false, !v.historyCount) + '<p id="versionHint" class="save-hint" role="status"></p></div>';
    ui.openModal('模型版本管理', html, 'bundleVersions'); panel = {mode: 'overview', from: active, signature: signature(b, choices), busy: false};
  }
  function source(c) {
    if (!c) return '无';
    return '<span>' + e(c.repository || '本地 / 直链资产') + '</span><code>' + e(c.revision || '按内容校验固定') + '</code><code>' + e(c.path) + '</code>' + (c.importPath && c.importPath !== c.path ? '<code>导入路径：' + e(c.importPath) + '</code>' : '') + '<code>' + e(c.sha256 ? 'SHA256 ' + c.sha256 : 'Git blob SHA-1 ' + c.gitBlobSha1) + '</code><small>' + e(c.format || '') + ' · ' + ui.bytes(c.bytes) + '</small>';
  }
  function review(plan) {
    var from = find(plan.fromBundleId), to = find(plan.toBundleId); if (!from || !to) return;
    var d = plan.download || {}, active = ['queued', 'downloading', 'verifying', 'installing'].indexOf((to.transfer || {}).state) >= 0;
    var html = '<div class="version-manager"><p class="eyebrow">REVIEW MODEL UPDATE</p><h3>' + e(from.manifest.name) + ' → ' + e(to.manifest.name) + '</h3><p>这是你选择的版本关系。所有组件仍在同一手机运行，不从模型下载可执行代码。</p><dl><dt>新版本完整大小</dt><dd>' + ui.bytes(d.totalBytes) + '</dd><dt>可复用资产</dt><dd>' + ui.bytes(d.reusableBytes) + '</dd><dt>剩余传输</dt><dd>' + ui.bytes(d.remainingBytes) + '</dd><dt>可用存储</dt><dd>' + ui.bytes(d.availableBytes) + '</dd></dl><p class="form-help">下载期间保留旧文件。新版本需要额外空间，不会通过自动删除旧模型腾出空间。</p><div class="bundle-components">' + plan.components.map(function (c) { return '<details><summary>' + e(c.role) + ' · ' + e(changes[c.change] || c.change) + '</summary><p>当前版本</p>' + source(c.from) + '<p>目标版本</p>' + source(c.to) + '</details>'; }).join('') + '</div><details class="version-settings" open><summary>参数：' + (plan.settingsMode === 'copy' ? '沿用当前版本并校验新约束' : '保留目标版本设置') + '</summary><dl>' + plan.settings.changes.map(function (c) { return '<dt>' + e(c.field) + '</dt><dd>' + e(value(c.from)) + ' → ' + e(value(c.to)) + '<small>' + e(reasons[c.reason] || c.reason) + '</small></dd>'; }).join('') + '</dl></details>';
    if (plan.metadataChanges.length) html += '<p class="form-help">元数据变化：' + plan.metadataChanges.map(e).join('、') + '。功能、许可和内容标签以目标清单为准，不继承旧版本的核对标记。</p>';
    html += '<details><summary>核对两版许可与能力</summary><p>当前许可：' + e(value(from.manifest.license)) + '</p><p>目标许可：' + e(value(to.manifest.license)) + '</p><p>目标功能：' + e((to.manifest.tasks || []).join(' / ')) + '</p><p>目标能力：' + e((to.manifest.capabilities || []).join(' / ') || '未声明') + '</p></details><p id="versionHint" class="save-hint" role="status"></p><div class="modal-actions">' + button('versionBack', '返回选择') + (d.installed ? button('versionActivate', '确认设为当前版本', true, from.inUse || to.inUse) : button('versionImport', '确认并从文件夹导入', false, active) + button('versionDownload', '确认并下载新版本', true, active || (d.components || []).some(function (c) { return !c.reusable && !c.downloadable; }))) + '</div><p class="modal-help">下载完成后再次核对并确认切换。失败或取消不替换旧版本。设置变化后须重新核对；切换不启动推理、不改变已提交任务。</p></div>';
    ui.openModal('核对模型更新', html, 'bundleVersionReview'); panel = {mode: 'review', from: from.id, plan: plan, busy: false};
  }
  function planArgs() { var p = panel.plan; return {from: p.fromBundleId, to: p.toBundleId, settingsMode: p.settingsMode, review: p.review}; }
  window.LMAVersions = {
    init: function (bridge) {
      ui = bridge;
      document.addEventListener('submit', function (event) {
        if (event.target.id !== 'bundleVersionForm') return; event.preventDefault(); if (!panel || panel.busy || !event.target.reportValidity()) return;
        call('planBundleUpdate', {from: panel.from, to: event.target.elements.target.value, settingsMode: event.target.elements.settingsMode.value}, review);
      });
    },
    badge: function (b) { var v = b.version || {}; return v.groupId ? '<span class="tag">' + (v.isActive ? '当前版本' : (v.members || []).indexOf(b.id) >= 0 ? '保留版本' : '待更新版本') + '</span>' : ''; },
    handle: function (action, el) {
      if (action === 'bundleVersions') { overview(el.dataset.id); return true; }
      if (action.indexOf('version') !== 0) return false;
      if (!panel || panel.busy) return true;
      var from = panel.from, b = find(from), update = b && (b.version || {}).pending;
      if (action === 'versionBack') overview(from, panel.plan && panel.plan.toBundleId, panel.plan && panel.plan.settingsMode);
      if (action === 'versionPendingReview' && update) call('planBundleUpdate', {from: from, to: update.toBundleId, settingsMode: update.settingsMode}, review);
      if (action === 'versionCancel' && update) call('cancelBundleUpdate', {id: from, review: update.review}, function () { overview(from); });
      if (action === 'versionDownload') call('downloadBundleUpdate', planArgs(), function () { overview(from); ui.toast('已下载的旧版本保留，等待你确认切换'); });
      if (action === 'versionImport') { var args = planArgs(); call('prepareBundleUpdate', args, function () { overview(from); ui.dispatch('bundleFolderPicker', {id: args.to}); }); }
      if (action === 'versionActivate') call('activateBundleUpdate', planArgs(), function (data) { overview(data.bundleId); ui.toast('已设为当前版本，旧版本和参数保留'); });
      if (action === 'versionHistory') call('inspectBundleVersions', {id: from}, function (data) { ui.openModal('模型切换记录', '<p>仅记录你明确确认的切换，既有任务保持原版本。</p><div class="version-manager">' + data.history.slice().reverse().map(function (h) { return '<p>' + e(new Date(h.at).toLocaleString('zh-CN')) + '</p><code>' + e(h.fromBundleId) + ' → ' + e(h.toBundleId) + '</code><p class="form-help">' + (h.settingsMode === 'copy' ? '沿用来源参数' : '保留目标参数') + '</p>'; }).join('') + '</div>', 'bundleVersionHistory'); panel = null; });
      return true;
    },
    receive: function () {
      Object.keys(pending).forEach(function (id) {
        var result = ui.result(id); if (!result) return;
        var request = pending[id]; delete pending[id]; if (panel !== request.editing) return;
        if (panel) panel.busy = false;
        if (result.ok) request.callback(result.data);
        else { request.enabled.forEach(function (b) { if (b.isConnected) b.disabled = false; }); var hint = document.getElementById('versionHint'); if (hint) hint.textContent = result.error; ui.toast(result.error || '更新操作失败'); }
      });
      if (panel && panel.mode === 'overview' && !panel.busy) {
        var b = find(panel.from), choices = b && entries().filter(function (c) { return compatible(b, c); }); if (!b) return;
        var updated = signature(b, choices);
        if (updated !== panel.signature) { var form = document.getElementById('bundleVersionForm'); overview(panel.from, form && form.elements.target.value, form && form.elements.settingsMode.value); }
      }
    },
    close: function () { panel = null; }
  };
})();
