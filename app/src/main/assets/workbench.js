(function () {
  'use strict';
  var ui, host, signature = '', historyPlan = null, historyPending = null;
  var names = {'text.generate': '生文', 'image.generate': '生图', 'video.generate': '生视频', 'speech.synthesize': '语音合成', 'audio.generate': '生音频', 'mesh.generate': '生 3D', 'model.prepare': '准备运行资产', 'model.assemble': '关联运行模型'};
  function e(v) { return ui.esc(v); }
  function button(action, id, label, style, disabled) { return host.button(action, id, label, style, disabled); }
  function draft(id) { return (ui.state().taskDrafts || []).find(function (d) { return d.bundleId === id; }); }
  function generation(type) { return ['text.generate', 'image.generate', 'video.generate', 'speech.synthesize', 'audio.generate', 'mesh.generate'].indexOf(type) >= 0; }
  function artifact(id) { return (ui.state().artifacts || []).find(function (a) { return a.id === id; }); }
  // Engine-owned input rules apply equally to any model using this capability.
  function applyInputConstraints(id) {
    var form = document.getElementById('localTaskForm'), b = host.find(id);
    if (!form || !b) return;
    function apply() {
      var type = form.elements.taskType && form.elements.taskType.value, schema = (b.inputSchemas || {})[type] || {};
      var negative = form.elements.negativePrompt;
      if (!negative) return;
      var label = negative.closest('label');
      if (schema.negativePrompt === false) {
        if (!negative.dataset.inputConstraint) { negative.dataset.inputConstraint = 'true'; negative.dataset.previousDisabled = String(negative.disabled); if (label) negative.dataset.previousHidden = String(label.hidden); }
        negative.value = ''; negative.disabled = true; if (label) label.hidden = true;
      } else if (negative.dataset.inputConstraint) {
        negative.disabled = negative.dataset.previousDisabled === 'true'; if (label) label.hidden = negative.dataset.previousHidden === 'true'; delete negative.dataset.inputConstraint;
      }
    }
    apply(); form.addEventListener('change', apply);
  }
  function use(id, adapter, request, revision) { if (window.LMAExpansion.use(id, request, revision)) return; host.use(id, adapter, request, revision); applyInputConstraints(id); }
  var limitMessage = '本次输出已达到所选上限，内容可能不完整。可调整此模型的输出上限后再次生成。';
  function limitedOutput(data) {
    var details = ((((data || {}).provenance || {}).engineExecution || {}).details || {});
    return details.truncated === true || details.stopReason === 'max_new_tokens';
  }
  function showOutputArtifact(id, data) {
    if (window.LMAExpansion.showArtifact(id, data)) return;
    host.showArtifact(id, data);
    var content = document.getElementById('modalContent');
    if (!content || !limitedOutput(data)) return;
    var notice = document.createElement('p'); notice.id = 'artifactCompletionNotice';
    notice.className = 'output-limit-notice'; notice.setAttribute('role', 'status'); notice.textContent = limitMessage;
    content.insertBefore(notice, content.firstChild);
  }
  function resourceText(r) {
    if (!r) return '';
    var text = r.message || (r.status === 'waiting' ? '等待执行时开始检查运行资源。' : r.status === 'ended' ? r.samples ? '本次运行资源检查已结束。' : '本次执行未取得系统资源读数。' : !r.samples ? '等待系统资源读数。' : '正在检查运行资源。');
    if (r.samples) text += ' 最低系统可用内存 ' + ui.bytes(r.minimumAvailableRamBytes) + ' · 最低可用存储 ' + ui.bytes(r.minimumAvailableStorageBytes) + ' · 最高温控等级 ' + (r.thermalKnown ? r.maximumThermalStatus + ' / 6' : '未知（系统未提供）') + '。';
    if (r.probeErrors) text += ' 有 ' + r.probeErrors + ' 次系统读数不可用。';
    return text;
  }
  function showJob(job) {
    var r = job.request, b = host.find(r.bundleId), input = r.input || {}, outputs = job.artifacts || [];
    var html = '<div class="task-detail"><div class="model-tags"><span class="tag">' + e(names[r.type] || r.type) + '</span><span class="tag">' + e(host.states[job.state] || job.state) + '</span></div><h3>' + e(b ? b.manifest.name : r.bundleId) + '</h3>';
    html += '<p id="taskCompletionNotice" class="output-limit-notice" role="status" data-job="' + e(job.id) + '" hidden></p>';
    if (input.prompt) html += '<h4>提示词 / 文本</h4><pre class="task-prompt-text">' + e(input.prompt) + '</pre>';
    if (input.negativePrompt) html += '<h4>负面提示词</h4><pre class="task-prompt-text">' + e(input.negativePrompt) + '</pre>';
    if (r.parameters) html += '<details open><summary>本次参数</summary><dl class="task-value-list">' + Object.keys(r.parameters).map(function (key) { return '<dt>' + e(host.paramNames[key] || key) + '</dt><dd>' + e(r.parameters[key]) + '</dd>'; }).join('') + '</dl></details>';
    if ((r.adapters || []).length) html += '<h4>LoRA</h4><ul>' + r.adapters.map(function (a) { var model = host.find(a.bundleId); return '<li>' + e(model ? model.manifest.name : a.bundleId) + ' · ' + e(a.scale) + '</li>'; }).join('') + '</ul>';
    if ((input.artifacts || []).length) html += '<h4>参考素材</h4><div class="job-actions">' + input.artifacts.map(function (ref) { var a = artifact(ref.artifactId); return button('artifactInfo', ref.artifactId, ref.role + (a && a.available ? ' · 打开' : ' · 文件不可用'), 'secondary', !a || !a.available); }).join('') + '</div>';
    if (job.outputRecovery) html += '<p class="recovered-output">中断后找回了已保存的结果。任务仍为已中断，未自动续步或重新生成。</p>';
    if (job.error) html += '<p class="download-error">' + e(job.error) + '</p>';
    if (job.runtimeResources) html += '<details open><summary>运行资源</summary><p class="form-help">' + e(resourceText(job.runtimeResources)) + '</p><p class="form-help">这是系统可用资源记录；模型峰值内存和速度需单独测量。重试会创建新任务，保留本次记录。</p></details>';
    html += '<div class="job-actions task-next-actions">';
    var stream = window.LMAAudioPreview.summary(job.id); if (stream) html += button('audioPreview', job.id, stream.state === 'streaming' ? '边生成边听' : '试听缓存', 'primary', stream.frames === 0);
    outputs.forEach(function (id, index) { var a = artifact(id); html += button('artifactInfo', id, '打开结果' + (outputs.length > 1 ? ' ' + (index + 1) : ''), 'primary', !a || !a.available); });
    if (generation(r.type)) html += button('editTask', job.id, '编辑后再次生成');
    if (b) html += button('bundleInfo', b.id, generation(r.type) ? '管理此模型' : '继续管理运行资产', generation(r.type) ? 'secondary' : 'primary');
    html += '</div><details><summary>完整执行记录</summary><pre class="provenance">' + e(JSON.stringify(job, null, 2)) + '</pre></details></div>';
    ui.openModal('任务详情', html, 'job');
    var firstOutput = outputs.find(function (id) { var a = artifact(id); return a && a.available; });
    if (generation(r.type) && firstOutput) host.track('inspectArtifact', {id: firstOutput}, function (data) {
      var target = document.getElementById('taskCompletionNotice');
      if (!target || target.dataset.job !== String(job.id)) return;
      var limited = limitedOutput(data);
      target.hidden = !limited;
      target.textContent = limited ? limitMessage : '';
    });
  }
  function render() {
    renderStatus();
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
  function renderStatus() {
    var s = ui.state(), jobs = s.jobs || [], c = s.taskCapacity && s.taskCapacity.jobs || {}, outputs = s.taskCapacity && s.taskCapacity.artifacts || {}, recovery = s.outputRecovery || {};
    var execution = (s.foundation || {}).execution || {}, observed = execution.active || execution.lastResourceStop, resourcePanel = document.getElementById('runtimeResourceStatus');
    resourcePanel.hidden = !observed || !observed.runtimeResources || !observed.runtimeResources.enabled;
    resourcePanel.textContent = observed ? (execution.active ? '当前执行 · ' : '最近停止 · ') + resourceText(observed.runtimeResources) : '';
    var pending = jobs.filter(function (job) { return ['queued','loading','running','cancelling'].indexOf(job.state) >= 0; }).length;
    document.getElementById('taskCapacity').textContent = '任务记录 ' + (c.history === undefined ? jobs.length : c.history) + ' / ' + (c.historyLimit || 256) + ' · 待处理 ' + (c.pending === undefined ? pending : c.pending) + ' / ' + (c.pendingLimit || 64) + ' · 素材与结果 ' + (outputs.count === undefined ? (s.artifacts || []).length : outputs.count) + ' / ' + (outputs.limit || 2048);
    document.getElementById('clearTaskHistoryButton').disabled = !!historyPending || jobs.length === pending;
    var messages = [];
    if (recovery.error) messages.push(recovery.error);
    if (recovery.recoveredOutputs) messages.push('中断后找回 ' + recovery.recoveredOutputs + ' 个已保存结果；原任务保持已中断，未自动重跑。');
    if (recovery.discardedStagingFiles || recovery.discardedUncommittedFiles) messages.push('已回收上次中断遗留的未提交临时文件，释放 ' + ui.bytes(recovery.reclaimedBytes) + '。');
    if (recovery.missingOutputs) messages.push(recovery.missingOutputs + ' 个已有结果文件不可用，请检查文件记录。');
    if (recovery.rejectedBindings) messages.push(recovery.rejectedBindings + ' 个结果来源与原任务不符，文件已保留，请检查来源。');
    if (recovery.cleanupFailures) messages.push('部分临时文件未能回收，已保留并记录，后续启动会再次检查。');
    var panel = document.getElementById('outputRecoveryStatus'); panel.hidden = !messages.length; panel.textContent = messages.join(' ');
  }
  function planHistory() {
    if (historyPending) return;
    historyPending = host.track('planTaskHistory', {}, function (plan) {
      historyPending = null; historyPlan = plan; renderStatus();
      var jobs = ui.state().jobs || [], count = (plan.ids || []).length;
      var html = '<form id="clearTaskHistoryForm"><p>将清理你本次检查的 <strong>' + count + '</strong> 条已结束任务记录。</p><p>结果文件、模型、独立设置与草稿保留；排队或运行任务不在清理范围内。检查之后结束的新任务也会保留。</p><p class="form-help">清理后，这些记录和对应幂等键不再保留；已有结果仍可查看来源并恢复生成输入。</p><details><summary>查看所选记录</summary><ul class="history-review-list">' + (plan.ids || []).map(function (id) { var job = jobs.find(function (j) { return j.id === id; }), b = job && host.find(job.request.bundleId); return '<li>' + e(job ? (b ? b.manifest.name : job.request.bundleId) + ' · ' + (host.states[job.state] || job.state) + ' · ' + new Date(job.createdAt).toLocaleString('zh-CN') : id) + '</li>'; }).join('') + '</ul></details><label class="unmeasured-choice"><input name="confirmHistory" type="checkbox" required><span>我确认清理这 ' + count + ' 条任务记录，保留结果文件。</span></label><p id="historyCleanupHint" role="status"></p><div class="modal-actions">' + button('closeModal', '', '取消') + button('planTaskHistory', '', '重新检查范围') + button('clearTaskHistory', '', '清理所选记录', 'danger', count === 0) + '</div></form>';
      ui.openModal('清理已结束的任务记录', html, 'taskHistory');
    }, function (error) { historyPending = null; renderStatus(); var hint = document.getElementById('historyCleanupHint'); if (hint) hint.textContent = error; });
    renderStatus();
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
    init: function (bridge, callbacks) { ui = bridge; host = callbacks; window.LMAAudioPreview.init(bridge, callbacks); },
    render: render, showJob: showJob, draft: draft,
    generation: generation,
    handle: function (action, el) {
      if (window.LMAAudioPreview.handle(action, el)) return true;
      var id = el.dataset.id;
      if (action === 'bundleUse') {
        var selected = host.find(id);
        if (selected && Object.keys(selected.inputSchemas || {}).some(function (type) { return selected.inputSchemas[type].negativePrompt === false; })) { use(id); return true; }
      }
      if (action === 'planTaskHistory') { planHistory(); return true; }
      if (action === 'clearTaskHistory') {
        var form = document.getElementById('clearTaskHistoryForm'); if (!historyPlan || !form || historyPending) return true;
        if (!form.reportValidity()) return true; el.disabled = true;
        historyPending = host.track(action, {selection:{ids:historyPlan.ids,review:historyPlan.review}}, function (result) {
          historyPending = null; historyPlan = null; if (document.getElementById('clearTaskHistoryForm')) ui.closeModal(); renderStatus(); ui.toast('已清理 ' + result.removed + ' 条任务记录，结果文件保留');
        }, function (error) { historyPending = null; renderStatus(); var hint = document.getElementById('historyCleanupHint'); if (hint) { hint.textContent = error + '。请重新检查清理范围。'; form.elements.confirmHistory.checked = false; } });
        renderStatus(); return true;
      }
      if (action === 'restoreTaskDraft') { host.track('inspectTaskDraft', {id: id}, function (data) { use(data.request.bundleId, null, data.request, data.revision); }); return true; }
      if (action === 'removeTaskDraft') {
        var current = draft(id); if (!current) return true;
        ui.openModal('删除生成草稿？', '<p>模型设置、已提交任务与产物均独立保存。</p><div class="modal-actions">' + button('closeModal', '', '取消') + '<button class="button danger" data-action="deleteTaskDraft" data-id="' + e(id) + '" data-revision="' + current.revision + '">删除草稿</button></div>', 'confirm'); return true;
      }
      if (action === 'deleteTaskDraft') { host.track(action, {id: id, expectedRevision: Number(el.dataset.revision)}, function () { ui.closeModal(); ui.toast('草稿已删除'); }); return true; }
      if (action === 'editTask' || action === 'editArtifact') { host.track(action, {id: id}, function (request) { use(request.bundleId, null, request); }); return true; }
      if (action === 'artifactInfo') { host.track('inspectArtifact', {id: id}, function (a) { showOutputArtifact(id, a); }); return true; }
      if (action === 'jobResults') { var job = (ui.state().jobs || []).find(function (j) { return j.id === id; }); if (job && (job.artifacts || []).length === 1) host.track('inspectArtifact', {id: job.artifacts[0]}, function (a) { showOutputArtifact(a.id, a); }); else host.track('inspectTask', {id: id}, showJob); return true; }
      if (action === 'artifactInput') { reference(id); return true; }
      if (action === 'useArtifactInput') {
        var a = artifact(id), b = host.find(el.dataset.bundle), schema = b && (b.inputSchemas || {})[el.dataset.type], rule = schema && (schema.roles || {})[el.dataset.role];
        if (!a || !b || !rule || !host.inputRuleMatch(a, rule)) { ui.toast('素材或配方已改变，请重新选择'); return true; }
        use(b.id, null, {bundleId: b.id, type: el.dataset.type, input: {prompt: '', artifacts: [{role: el.dataset.role, artifactId: id}]}}); return true;
      }
      return false;
    }
  };
})();
