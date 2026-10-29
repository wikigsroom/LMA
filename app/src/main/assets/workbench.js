(function () {
  'use strict';
  var ui, host, signature = '';
  var names = {'text.generate': '生文', 'image.generate': '生图', 'video.generate': '生视频', 'speech.synthesize': '语音合成', 'audio.generate': '生音频', 'model.prepare': '准备运行资产', 'model.assemble': '关联运行模型'};
  function e(v) { return ui.esc(v); }
  function button(action, id, label, style, disabled) { return host.button(action, id, label, style, disabled); }
  function draft(id) { return (ui.state().taskDrafts || []).find(function (d) { return d.bundleId === id; }); }
  function generation(type) { return ['text.generate', 'image.generate', 'video.generate', 'speech.synthesize', 'audio.generate'].indexOf(type) >= 0; }
  function artifact(id) { return (ui.state().artifacts || []).find(function (a) { return a.id === id; }); }
  function showJob(job) {
    var r = job.request, b = host.find(r.bundleId), input = r.input || {}, outputs = job.artifacts || [];
    var html = '<div class="task-detail"><div class="model-tags"><span class="tag">' + e(names[r.type] || r.type) + '</span><span class="tag">' + e(host.states[job.state] || job.state) + '</span></div><h3>' + e(b ? b.manifest.name : r.bundleId) + '</h3>';
    if (input.prompt) html += '<h4>提示词 / 文本</h4><pre class="task-prompt-text">' + e(input.prompt) + '</pre>';
    if (input.negativePrompt) html += '<h4>负面提示词</h4><pre class="task-prompt-text">' + e(input.negativePrompt) + '</pre>';
    if (r.parameters) html += '<details open><summary>本次参数</summary><dl class="task-value-list">' + Object.keys(r.parameters).map(function (key) { return '<dt>' + e(host.paramNames[key] || key) + '</dt><dd>' + e(r.parameters[key]) + '</dd>'; }).join('') + '</dl></details>';
    if ((r.adapters || []).length) html += '<h4>LoRA</h4><ul>' + r.adapters.map(function (a) { var model = host.find(a.bundleId); return '<li>' + e(model ? model.manifest.name : a.bundleId) + ' · ' + e(a.scale) + '</li>'; }).join('') + '</ul>';
    if ((input.artifacts || []).length) html += '<h4>参考素材</h4><div class="job-actions">' + input.artifacts.map(function (ref) { var a = artifact(ref.artifactId); return button('artifactInfo', ref.artifactId, ref.role + (a && a.available ? ' · 打开' : ' · 文件不可用'), 'secondary', !a || !a.available); }).join('') + '</div>';
    if (job.error) html += '<p class="download-error">' + e(job.error) + '</p>';
    html += '<div class="job-actions task-next-actions">';
    outputs.forEach(function (id, index) { var a = artifact(id); html += button('artifactInfo', id, '打开结果' + (outputs.length > 1 ? ' ' + (index + 1) : ''), 'primary', !a || !a.available); });
    if (generation(r.type)) html += button('editTask', job.id, '编辑后再次生成');
    if (b) html += button('bundleInfo', b.id, generation(r.type) ? '管理此模型' : '继续管理运行资产', generation(r.type) ? 'secondary' : 'primary');
    html += '</div><details><summary>完整执行记录</summary><pre class="provenance">' + e(JSON.stringify(job, null, 2)) + '</pre></details></div>';
    ui.openModal('任务详情', html, 'job');
  }
  function render() {
    var drafts = (ui.state().taskDrafts || []).slice().sort(function (a, b) { return b.savedAt - a.savedAt; });
    var next = JSON.stringify([drafts, (ui.state().bundles || []).map(function (b) { return [b.id, b.installed, b.inUse]; })]);
    if (next === signature) return; signature = next;
    document.getElementById('draftSection').hidden = !drafts.length;
    document.getElementById('draftCount').textContent = drafts.length + ' 份';
    document.getElementById('draftList').innerHTML = drafts.map(function (d) {
      var b = host.find(d.bundleId);
      return '<article class="draft-card"><div><strong>' + e(b ? b.manifest.name : d.bundleId) + '</strong><p class="form-help">' + e(names[d.type] || d.type) + ' · ' + new Date(d.savedAt).toLocaleString('zh-CN') + '</p><p class="job-prompt">' + e(d.inputSummary || '尚未填写提示词') + '</p></div><div class="job-actions">' + button('restoreTaskDraft', d.bundleId, '继续编辑', 'primary') + button('removeTaskDraft', d.bundleId, '删除草稿') + '</div></article>';
    }).join('');
  }
  function reference(id) {
    var a = artifact(id); if (!a || !a.available) { ui.toast('所选素材不可用，请重新导入'); return; }
    var choices = [];
    (ui.state().bundles || []).forEach(function (b) {
      if (!b.installed || b.inUse || !host.engineAvailable(b)) return;
      Object.keys(b.inputSchemas || {}).forEach(function (type) {
        var roles = b.inputSchemas[type].roles || {};
        Object.keys(roles).forEach(function (role) { if (host.inputRuleMatch(a, roles[role])) choices.push({b: b, type: type, role: role, label: roles[role].label}); });
      });
    });
    var html = '<p>选择接收此素材的本地模型。只会填入生成表单，由你填写提示词、确认参数后提交。</p>';
    if (!choices.length) html += '<p class="form-help">当前没有已安装且接受此类素材的可用模型。可在模型库选择相应配方及必需组件。</p>' + button('showLocal', '', '管理本地模型');
    html += choices.map(function (choice) { return '<article class="draft-card"><strong>' + e(choice.b.manifest.name) + '</strong><p>' + e(names[choice.type]) + ' · ' + e(choice.label || choice.role) + '</p><button class="button primary" data-action="useArtifactInput" data-id="' + e(id) + '" data-bundle="' + e(choice.b.id) + '" data-type="' + e(choice.type) + '" data-role="' + e(choice.role) + '">填入此模型</button></article>'; }).join('');
    ui.openModal('用作下一次生成的素材', html, 'artifactInput');
  }
  window.LMAWorkbench = {
    init: function (bridge, callbacks) { ui = bridge; host = callbacks; },
    render: render, showJob: showJob, draft: draft,
    generation: generation,
    handle: function (action, el) {
      var id = el.dataset.id;
      if (action === 'restoreTaskDraft') { host.track('inspectTaskDraft', {id: id}, function (data) { host.use(data.request.bundleId, null, data.request, data.revision); }); return true; }
      if (action === 'removeTaskDraft') {
        var current = draft(id); if (!current) return true;
        ui.openModal('删除生成草稿？', '<p>模型设置、已提交任务与产物均独立保存。</p><div class="modal-actions">' + button('closeModal', '', '取消') + '<button class="button danger" data-action="deleteTaskDraft" data-id="' + e(id) + '" data-revision="' + current.revision + '">删除草稿</button></div>', 'confirm'); return true;
      }
      if (action === 'deleteTaskDraft') { host.track(action, {id: id, expectedRevision: Number(el.dataset.revision)}, function () { ui.closeModal(); ui.toast('草稿已删除'); }); return true; }
      if (action === 'editTask' || action === 'editArtifact') { host.track(action, {id: id}, function (request) { host.use(request.bundleId, null, request); }); return true; }
      if (action === 'jobResults') { var job = (ui.state().jobs || []).find(function (j) { return j.id === id; }); if (job && (job.artifacts || []).length === 1) host.track('inspectArtifact', {id: job.artifacts[0]}, function (a) { host.showArtifact(a.id, a); }); else host.track('inspectTask', {id: id}, showJob); return true; }
      if (action === 'artifactInput') { reference(id); return true; }
      if (action === 'useArtifactInput') {
        var a = artifact(id), b = host.find(el.dataset.bundle), schema = b && (b.inputSchemas || {})[el.dataset.type], rule = schema && (schema.roles || {})[el.dataset.role];
        if (!a || !b || !rule || !host.inputRuleMatch(a, rule)) { ui.toast('素材或配方已改变，请重新选择'); return true; }
        host.use(b.id, null, {bundleId: b.id, type: el.dataset.type, input: {prompt: '', artifacts: [{role: el.dataset.role, artifactId: id}]}}); return true;
      }
      return false;
    }
  };
})();
