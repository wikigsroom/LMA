(function () {
  'use strict';
  var ui, pending = {}, editor = null, listSignature = '', artifactSignature = '', artifactKind = 'all';
  var $ = function (id) { return document.getElementById(id); };
  var labels = {text: '生文', image: '生图', video: '生视频', audio: '生音频'};
  var states = {queued: '排队中', loading: '加载中', running: '生成中', cancelling: '取消中', cancelled: '已取消', failed: '失败', succeeded: '已完成', interrupted: '已中断'};
  var stages = {queued: '等待执行', waiting_engine: '等待本机执行槽', validating_inputs: '校验本地素材', loading: '加载模型', sampling: '采样中', encoding: '编码媒体', synthesizing: '合成语音', text_encoding: '编码文本', decoding: '解码输出', generating: '生成文本', saving: '保存结果'};
  var paramNames = {width: '宽度', height: '高度', frames: '帧数', fps: '帧率', steps: '采样步数', cfg: '提示词引导', seed: '随机种子', threads: 'CPU 线程', sampler: '采样器', scheduler: '调度器', duration: '时长（秒）', speed: '语速', context: '上下文长度', maxTokens: '单次输出上限', temperature: '采样温度', reasoning: '思考模式', systemPrompt: '系统提示词'};
  function entries() { return ui.state() && ui.state().bundles || []; }
  function find(id) { return entries().filter(function (b) { return b.id === id; })[0]; }
  function e(value) { return ui.esc(value); }
  function button(action, id, text, style, disabled) { return '<button class="button ' + (style || 'secondary') + '" data-action="' + action + '" data-id="' + e(id) + '"' + (disabled ? ' disabled' : '') + '>' + text + '</button>'; }
  function engineAvailable(b) { return !b.parameterError && (ui.state().localEngines || []).some(function (engine) { return engine.engine === b.manifest.engine && engine.available; }); }
  function isAdapter(b) { return !!(b.manifest.adapter && b.manifest.adapter.kind === 'lora'); }
  function compatible(base, adapter) {
    var m = base.manifest, a = adapter.manifest.adapter;
    return !!a && !isAdapter(base) && m.engine === adapter.manifest.engine && m.backend === adapter.manifest.backend && tasks(base).indexOf('image') >= 0 && (a.baseArchitectures || []).indexOf(m.architecture) >= 0 && (a.basePipelines || []).indexOf(m.pipeline) >= 0 && (!a.baseModelIds || a.baseModelIds.indexOf(m.modelId) >= 0);
  }
  function tasks(b) { return (b.manifest.tasks || []).filter(function (tag) { return labels[tag]; }); }
  function taskTags(b) { return tasks(b).map(function (t) { return '<span class="tag task-tag task-' + t + '">' + labels[t] + '</span>'; }).join('') + (isAdapter(b) ? '<span class="tag">LoRA</span><span class="tag">需要基础模型</span>' : '') + (b.manifest.uncensored && b.manifest.uncensored.detected ? '<span class="tag">无审查线索 · 待核对</span>' : ''); }
  function views() {
    var aliases = (ui.state().models || []).map(function (m) { return m.bundleId; }).filter(Boolean);
    return entries().filter(function (b) { var legacy = b.manifest.migration && b.manifest.migration.source === 'legacy_text_store' && b.manifest.migration.legacyId;
      return aliases.indexOf(b.id) < 0 && !(legacy && (ui.state().models || []).some(function (m) { return m.id === legacy; })); }).map(function (b) {
      var m = b.manifest, p = b.plan || {};
      return {id: 'bundle::' + b.id, bundleId: b.id, isBundle: true, name: m.name, family: m.architecture, repository: (m.components[0] || {}).repository || '', description: m.description || '', taskTags: tasks(b), tier: m.catalogue ? 'catalogue' : 'custom', installed: b.installed, bytes: p.totalBytes, installedBytes: p.totalBytes, download: b.transfer, imported: !m.catalogue, bundle: b};
    });
  }
  function card(m) {
    var b = m.bundle, manifest = b.manifest, t = b.transfer || {}, plan = b.plan || {};
    var active = ['queued', 'downloading', 'verifying', 'installing'].indexOf(t.state) >= 0;
    var message = b.installed ? '已安装 · 设备待验证' : active ? ({queued: '等待下载', downloading: '下载组件', verifying: '校验组件', installing: '安装中'}[t.state]) : t.state === 'paused' ? '已暂停' : t.state === 'failed' ? '下载失败' : '尚未下载';
    return '<article class="model-card bundle-card" data-bundle="' + e(b.id) + '"><div class="model-top"><span class="model-symbol">' + ui.icon('cube') + '</span><div class="model-top-copy"><button class="model-name" data-action="bundleInfo" data-id="' + e(b.id) + '"><strong>' + e(manifest.name) + '</strong><span class="model-caption">' + e(manifest.architecture) + ' / ' + e(manifest.backend) + '</span></button></div></div><p class="model-description">' + e(manifest.description || '由用户选择的本地模型包') + '</p><div class="model-tags">' + taskTags(b) + window.LMAVersions.badge(b) + '<span class="tag">' + e(manifest.engine) + '</span><span class="tag">' + e(message) + '</span></div><div class="model-footer"><div class="model-size">' + ui.bytes(plan.totalBytes) + '<small>' + manifest.components.length + ' 个必需组件</small></div><div class="model-footer-actions">' + (b.installed ? button('bundleUse', b.id, isAdapter(b) ? '配对使用' : '使用', 'primary', b.inUse || !engineAvailable(b)) : active ? button('pauseBundle', b.id, '暂停') : button('bundleInfo', b.id, t.state === 'paused' || t.state === 'failed' ? '继续下载' : '查看并下载', 'primary')) + '</div></div>' + (active ? '<p class="form-help">' + e(t.role || '') + (t.received ? ' · ' + ui.bytes(t.received) : '') + '</p>' : '') + (t.error ? '<p class="download-error">' + e(t.error) + '</p>' : '') + '</article>';
  }
  function info(id) {
    var b = find(id); if (!b) return; var m = b.manifest, p = b.plan || {};
    var files = p.components || [];
    var adapterHelp = isAdapter(b) ? '<p class="form-help">此包仅包含 LoRA。基础模型由你另外选择、安装；只与声明兼容的 ' + e(m.adapter.baseArchitectures.join(' / ')) + ' / ' + e(m.adapter.basePipelines.join(' / ')) + ' 配方配对。兼容声明仍需实际权重验证。</p>' : '';
    var html = '<div class="model-info"><div class="model-tags">' + taskTags(b) + '<span class="tag">' + e(m.engine) + '</span><span class="tag">' + e(m.pipeline) + '</span></div><p>' + e(m.description || '') + '</p><p>' + (b.parameterError ? e(b.parameterError) : engineAvailable(b) ? '运行引擎已随 App 安装，当前配方仍需手机实测。' : '当前基座缺少匹配引擎。下载文件不会安装引擎，请等待对应的 App 更新。') + '</p>' + adapterHelp + '<dl><dt>完整模型包</dt><dd>' + ui.bytes(p.totalBytes) + '</dd><dt>可复用资产</dt><dd>' + ui.bytes(p.reusableBytes) + '</dd><dt>剩余传输</dt><dd>' + ui.bytes(p.remainingBytes) + '</dd><dt>配方</dt><dd>' + e(m.recipeId) + '</dd><dt>许可</dt><dd>' + e(typeof m.license === 'string' ? m.license : m.license && m.license.name || '尚未声明，请核对来源') + '</dd></dl><div class="bundle-components">' + files.map(function (c) { return '<details><summary>' + e(c.role) + ' · ' + ui.bytes(c.bytes) + (c.reusable ? ' · 可复用' : '') + '</summary><p>' + e(c.path) + '</p>' + (c.importPath && c.importPath !== c.path ? '<p class="modal-help">文件夹导入路径：' + e(c.importPath) + '</p>' : '') + '<code>' + e(c.sha256 ? 'SHA256 ' + c.sha256 : 'Git blob SHA-1 ' + c.gitBlobSha1) + '</code>' + (c.verifiedSha256 ? '<code>已校验 SHA256 ' + e(c.verifiedSha256) + '</code>' : '') + '</details>'; }).join('') + '</div><p class="modal-help">只下载这套包及上面列出的必需组件。浏览、App 升级与缺失模型的生成请求均不会触发下载。所有生成步骤在这部手机上执行。</p><div class="modal-actions">';
    if (b.installed) html += button('bundleSettings', id, '模型设置') + button('bundleUse', id, isAdapter(b) ? '选择基础模型' : '使用模型', 'primary', !engineAvailable(b) || b.inUse);
    else html += button('bundleFolderPicker', id, '从文件夹导入') + button('downloadBundle', id, '下载所选模型包', 'primary', files.some(function (c) { return !c.reusable && !c.downloadable; }));
    html += '</div>' + (b.installed || (b.version || {}).groupId ? button('bundleVersions', id, '版本管理 / 独立更新') : '') + button('bundleRemove', id, '删除本地资产', 'danger', b.inUse) + '</div>';
    editor = null; ui.openModal(m.name, html, 'bundleInfo');
  }
  function schemaFor(b) { return b.parameterSchema || b.manifest.parameters || {}; }
  function numericHint(f, values, all) {
    var maximum = f.maximum, bound = f.maximumFrom;
    if (bound && all[bound.field]) {
      var source = Object.prototype.hasOwnProperty.call(values, bound.field) ? values[bound.field] : all[bound.field].default;
      maximum = Math.min(maximum === undefined ? Infinity : maximum, Number(source) + (bound.offset || 0));
      if (f.type === 'integer') maximum = Math.floor(maximum);
      if (f.multipleOf) maximum = (f.alignmentOrigin || 0) + Math.floor((maximum - (f.alignmentOrigin || 0)) / f.multipleOf) * f.multipleOf;
    }
    return (f.minimum !== undefined ? '最低 ' + e(f.minimum) + ' · ' : '') + (maximum !== undefined && isFinite(maximum) ? (bound ? '当前上限 ' : f.limitSource === 'application_guard' ? '应用保护上限 ' : f.limitSource === 'publisher_metadata_unverified' ? '发布者声明上限（待核对）' : '上限 ') + e(maximum) : '模型上限未声明') + (bound ? ' · 受' + e(all[bound.field] && all[bound.field].label || paramNames[bound.field] || bound.field) + '约束' : '') + (f.multipleOf ? ' · 步长 ' + e(f.multipleOf) : '');
  }
  function fields(b) {
    var schema = schemaFor(b), values = b.config && b.config.values || {}, all = schema.fields || {};
    var out = '<div class="form-grid bundle-fields">';
    Object.keys(all).forEach(function (key, i) {
      var f = all[key], value = Object.prototype.hasOwnProperty.call(values, key) ? values[key] : f.default;
      var name = 'bp-' + i, caption = f.label || paramNames[key] || key;
      out += '<label class="form-field"><span>' + e(caption) + '</span>';
      if (f.type === 'boolean') out += '<input data-bundle-field="' + e(key) + '" type="checkbox"' + (value ? ' checked' : '') + '>';
      else if (f.type === 'enum') out += '<select data-bundle-field="' + e(key) + '">' + f.values.map(function (v, index) { return '<option value="' + index + '"' + (v === value ? ' selected' : '') + '>' + e(v) + '</option>'; }).join('') + '</select>';
      else if (f.type === 'string') out += '<input data-bundle-field="' + e(key) + '" value="' + e(value) + '" maxlength="' + (f.maxLength === undefined ? 16000 : f.maxLength) + '">';
      else {
        var presets = (f.presets || []).filter(function (v) { return typeof v === 'number' && isFinite(v); });
        out += '<input type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" list="' + name + '" data-bundle-field="' + e(key) + '" data-numeric="true" value="' + e(value) + '" inputmode="' + (f.type === 'integer' ? 'numeric' : 'decimal') + '" autocomplete="off"><datalist id="' + name + '">' + presets.map(function (v) { return '<option value="' + v + '"></option>'; }).join('') + '</datalist><small data-bundle-bound-caption="' + e(key) + '">' + numericHint(f, values, all) + '</small>';
      }
      out += '</label>';
    });
    out += '</div>';
    if (schema.allowedShapes && schema.allowedShapes.length) out += '<label class="form-field"><span>已编译尺寸组合</span><select id="bundleShape"><option value="">选择一个完整组合</option>' + schema.allowedShapes.map(function (s, i) { return '<option value="' + i + '">' + Object.keys(s).map(function (key) { return e(paramNames[key] || key) + ' ' + e(s[key]); }).join(' / ') + '</option>'; }).join('') + '</select></label>';
    return out;
  }
  function readFields(form, b) {
    var out = {}, all = schemaFor(b).fields || {};
    form.querySelectorAll('[data-bundle-field]').forEach(function (input) {
      var key = input.dataset.bundleField, f = all[key], value;
      if (f.type === 'boolean') value = input.checked;
      else if (f.type === 'enum') value = f.values[Number(input.value)];
      else if (f.type === 'string') value = input.value;
      else {
        if (!input.value.trim() || !isFinite(Number(input.value))) throw new Error((f.label || paramNames[key] || key) + '需要有效数字');
        value = Number(input.value); if (f.type === 'integer') value = Math.floor(value);
        if (f.minimum !== undefined) value = Math.max(value, f.minimum);
        if (f.maximum !== undefined) value = Math.min(value, f.maximum);
        if (f.multipleOf) value = (f.alignmentOrigin || 0) + Math.floor((value - (f.alignmentOrigin || 0)) / f.multipleOf) * f.multipleOf;
        if (f.minimum !== undefined && value < f.minimum) throw new Error('参数没有满足约束的值');
        input.value = value;
      }
      out[key] = value;
    });
    var complete = {}, visiting = {};
    function dependent(key) {
      if (complete[key]) return;
      if (visiting[key]) throw new Error('参数联合约束存在循环');
      visiting[key] = true;
      var f = all[key], bound = f.maximumFrom;
      if (bound) {
        if (!all[bound.field] || typeof out[bound.field] !== 'number') throw new Error('参数联合约束无效');
        dependent(bound.field);
        var value = Math.min(out[key], out[bound.field] + (bound.offset || 0));
        if (f.type === 'integer') value = Math.floor(value);
        if (f.multipleOf) value = (f.alignmentOrigin || 0) + Math.floor((value - (f.alignmentOrigin || 0)) / f.multipleOf) * f.multipleOf;
        if (!isFinite(value) || f.minimum !== undefined && value < f.minimum) throw new Error('参数联合约束没有合法值');
        out[key] = value;
        form.querySelectorAll('[data-bundle-field]').forEach(function (input) { if (input.dataset.bundleField === key) input.value = value; });
      }
      delete visiting[key]; complete[key] = true;
    }
    Object.keys(all).forEach(dependent);
    form.querySelectorAll('[data-bundle-bound-caption]').forEach(function (caption) { var key = caption.dataset.bundleBoundCaption; caption.innerHTML = numericHint(all[key], out, all); });
    var shapes = schemaFor(b).allowedShapes;
    if (shapes && shapes.length && !shapes.some(function (s) { return Object.keys(s).every(function (key) { return out[key] === s[key]; }); })) throw new Error('请使用一个完整的已编译尺寸组合');
    return out;
  }
  function settings(id) {
    var b = find(id); if (!b) return;
    editor = {id: id, mode: 'settings'};
    ui.openModal('模型设置 · ' + b.manifest.name, '<form id="bundleSettingsForm">' + fields(b) + '<p class="form-help">参数随此模型和配方独立保存。超过已声明上限会自动归位；尺寸、帧数仍须满足联合约束。修改只影响之后提交的任务。</p><p id="bundleFormHint" role="status"></p><div class="modal-actions">' + button('closeModal', '', '关闭') + '<button class="button primary" type="submit"' + (b.inUse ? ' disabled' : '') + '>保存模型设置</button></div></form>', 'bundleSettings');
  }
  function pair(id) {
    var adapter = find(id), bases = entries().filter(function (base) { return base.installed && !base.inUse && engineAvailable(base) && compatible(base, adapter); });
    editor = {id: id, mode: 'pair'};
    ui.openModal('选择基础模型 · ' + adapter.manifest.name, '<form id="adapterPairForm"><p class="form-help">LoRA 需要与已安装的兼容基础模型配对。此操作不会下载或替换任何权重。</p>' + (bases.length ? '<label class="form-field"><span>已安装的兼容基础模型</span><select name="baseBundleId" required>' + bases.map(function (base) { return '<option value="' + e(base.id) + '">' + e(base.manifest.name) + '</option>'; }).join('') + '</select></label>' : '<p class="empty-list">尚未安装兼容的基础模型。请在模型库自行选择下载或导入，再回来配对。</p>') + '<div class="modal-actions">' + button('closeModal', '', '关闭') + (bases.length ? '<button class="button primary" type="submit">填写生成任务</button>' : '') + '</div></form>', 'adapterPair');
  }
  function adapterFields(base, selected) {
    var adapters = entries().filter(function (adapter) { return adapter.installed && !adapter.inUse && engineAvailable(adapter) && compatible(base, adapter); });
    if (!adapters.length) return '<p class="form-help">当前没有已安装的兼容 LoRA；可在模型库自行选择下载或导入。</p>';
    return '<fieldset id="taskAdapters" class="task-adapters"><legend>LoRA（可选，最多 8 个）</legend><p class="form-help">仅列出已安装且声明兼容的适配器。各自强度独立保存，本次修改只用于当前任务。</p>' + adapters.map(function (adapter, index) {
      var f = adapter.manifest.parameters.fields.scale, value = adapter.config && adapter.config.values && adapter.config.values.scale;
      if (value === undefined) value = f.default;
      return '<div class="task-adapter"><label class="adapter-choice"><input type="checkbox" data-adapter-select="' + e(adapter.id) + '"' + (adapter.id === selected ? ' checked' : '') + '><span>' + e(adapter.manifest.name) + '</span></label><label class="form-field"><span>强度</span><input type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" data-adapter-scale="' + e(adapter.id) + '" list="adapter-scale-' + index + '" inputmode="decimal" autocomplete="off" value="' + e(value) + '"' + (adapter.id === selected ? '' : ' disabled') + '><datalist id="adapter-scale-' + index + '">' + (f.presets || []).map(function (preset) { return '<option value="' + e(preset) + '"></option>'; }).join('') + '</datalist><small>' + e(f.minimum) + ' 至 ' + e(f.maximum) + '</small></label></div>';
    }).join('') + '</fieldset>';
  }
  function readAdapters(form, base) {
    var selected = [];
    form.querySelectorAll('[data-adapter-select]:checked').forEach(function (choice) {
      var adapter = find(choice.dataset.adapterSelect);
      if (!adapter || !adapter.installed || !compatible(base, adapter)) throw new Error('所选 LoRA 已不可用，请重新选择');
      var input = Array.from(form.querySelectorAll('[data-adapter-scale]')).filter(function (field) { return field.dataset.adapterScale === adapter.id; })[0];
      if (!input.value.trim() || !isFinite(Number(input.value))) throw new Error('LoRA 强度需要有效数字');
      var f = adapter.manifest.parameters.fields.scale, value = Number(input.value);
      if (f.type === 'integer') value = Math.floor(value);
      value = Math.max(-4, Math.min(4, Math.max(f.minimum, Math.min(f.maximum, value))));
      if (f.multipleOf) value = (f.alignmentOrigin || 0) + Math.floor((value - (f.alignmentOrigin || 0)) / f.multipleOf) * f.multipleOf;
      if (value < f.minimum || value > f.maximum) throw new Error('LoRA 强度没有满足约束的值');
      input.value = value; selected.push({bundleId: adapter.id, scale: value});
    });
    if (selected.length > 8) throw new Error('一次最多选择 8 个 LoRA');
    return selected;
  }
  function inputRuleMatch(a, rule) {
    var m = a.metadata || {};
    return a.available && (rule.mimes || []).indexOf(m.mime) >= 0 && a.bytes <= rule.maxBytes && (!rule.maxDurationMs || m.durationMs > 0 && m.durationMs <= rule.maxDurationMs) && (!rule.maxPixels || m.width > 0 && m.height > 0 && m.width * m.height <= rule.maxPixels);
  }
  function renderInputFields() {
    var panel = $('taskInputs'), form = $('localTaskForm'), b = editor && find(editor.id); if (!panel || !form || !b) return;
    var selected = {}; panel.querySelectorAll('[data-input-role]').forEach(function (s) { selected[s.dataset.inputRole] = s.value; });
    var schema = (b.inputSchemas || {})[form.elements.taskType.value], roles = schema && schema.roles || {}, keys = Object.keys(roles);
    panel.innerHTML = keys.length ? '<h3>本地输入素材</h3>' + keys.map(function (role) {
      var rule = roles[role], choices = (ui.state().artifacts || []).filter(function (a) { return inputRuleMatch(a, rule); });
      return '<label class="form-field"><span>' + e(rule.label) + (rule.required ? '（必选）' : '（可选）') + '</span><select data-input-role="' + e(role) + '"' + (rule.required ? ' required' : '') + '><option value="">选择已导入素材或已有结果</option>' + choices.map(function (a) { var origin = a.origin || {}; return '<option value="' + e(a.id) + '"' + (selected[role] === a.id ? ' selected' : '') + '>' + e(origin.name || a.id) + ' · ' + ui.bytes(a.bytes) + '</option>'; }).join('') + '</select><small>' + e((rule.mimes || []).join(' / ')) + ' · ≤ ' + ui.bytes(rule.maxBytes) + (choices.length ? '' : ' · 暂无匹配素材') + '</small></label>';
    }).join('') + button('inputPicker', '', '导入新素材') : '<p class="form-help">当前配方仅接受文字。导入素材不会自动开启图像编辑或语音克隆。</p>';
  }
  function readInputs(form) {
    var result = [];
    form.querySelectorAll('[data-input-role]').forEach(function (select) { if (select.value) result.push({role: select.dataset.inputRole, artifactId: select.value}); });
    return result;
  }
  function use(id, selectedAdapter) {
    var b = find(id); if (!b || !b.installed) { ui.toast('请先选择并完整安装模型'); return; }
    if (!engineAvailable(b)) { ui.toast('当前基座缺少匹配引擎'); return; }
    if (isAdapter(b)) { pair(id); return; }
    var types = [];
    tasks(b).forEach(function (t) { if (t === 'image') types.push(['image.generate', '生图']); if (t === 'video') types.push(['video.generate', '生视频']); if (t === 'text') types.push(['text.generate', '生文']); if (t === 'audio') types.push([(b.manifest.capabilities || []).indexOf('text_to_speech') >= 0 ? 'speech.synthesize' : 'audio.generate', '生音频']); });
    var speechOnly = types.length === 1 && types[0][0] === 'speech.synthesize', textOnly = types.length === 1 && types[0][0] === 'text.generate';
    editor = {id: id, mode: 'task'};
    ui.openModal(b.manifest.name, '<form id="localTaskForm"><label class="form-field"><span>生成能力</span><select name="taskType">' + types.map(function (t) { return '<option value="' + t[0] + '">' + t[1] + '</option>'; }).join('') + '</select></label><label class="form-field"><span>' + (speechOnly ? '朗读文本' : '提示词 / 文本') + '</span><textarea name="prompt" rows="4" required maxlength="' + (speechOnly ? '4000' : '16000') + '" placeholder="' + (speechOnly ? '填写所选语言词表覆盖的朗读文本' : '描述你希望生成的内容') + '"></textarea></label>' + (speechOnly ? '<p class="form-help">请使用此配方声明的语言与输入。缺失组件或不支持的能力会在本机报错，不会下载或转出执行。</p>' : textOnly ? '' : '<label class="form-field"><span>负面提示词（可选）</span><textarea name="negativePrompt" rows="2" maxlength="16000"></textarea></label>') + (tasks(b).indexOf('image') >= 0 ? adapterFields(b, selectedAdapter) : '') + '<div id="taskInputs"></div><details class="task-parameters"><summary>本次参数</summary>' + fields(b) + '</details><label class="unmeasured-choice"><input type="checkbox" name="allowUnmeasured" required><span>此配方尚无本机实测记录，我选择在当前手机上尝试。</span></label><p class="form-help">一次执行一个大型引擎。任务等待当前回复结束后自动切换，队列空闲时恢复此前加载的文本模型。任务在后台通知中执行，结果保存在本机；缺少组件不会自动下载。</p><p id="bundleFormHint" role="status"></p><div class="modal-actions">' + button('closeModal', '', '取消') + '<button type="submit" class="button primary">加入本机队列</button></div></form>', 'localTask');
    renderInputFields();
  }
  function renderJobs() {
    var s = ui.state(), jobs = s.jobs || [], signature = JSON.stringify(jobs);
    if (signature === listSignature) return; listSignature = signature;
    $('jobCount').textContent = jobs.filter(function (j) { return ['queued', 'loading', 'running', 'cancelling'].indexOf(j.state) >= 0; }).length + ' 个待完成';
    $('jobList').innerHTML = jobs.length ? jobs.slice().reverse().map(function (job) {
      var b = find(job.request.bundleId), terminal = ['cancelled', 'failed', 'succeeded', 'interrupted'].indexOf(job.state) >= 0;
      var progress = typeof job.progress === 'number' ? '<progress max="1" value="' + Math.max(0, Math.min(1, job.progress)) + '" aria-label="生成进度"></progress>' : '';
      return '<article class="job-card"><div class="section-heading"><strong>' + e(b ? b.manifest.name : job.request.bundleId) + '</strong><span class="status-pill">' + e(job.stage === 'waiting_engine' && ['loading', 'running'].indexOf(job.state) >= 0 ? '排队中' : states[job.state] || job.state) + '</span></div><p class="job-prompt">' + e(job.request.inputSummary || job.request.input && job.request.input.prompt || '') + '</p><p class="form-help">' + e(stages[job.stage] || job.stage || '') + ' · ' + new Date(job.createdAt).toLocaleString('zh-CN') + '</p>' + progress + (job.error ? '<p class="download-error">' + e(job.error) + '</p>' : '') + '<div class="job-actions">' + button('jobInfo', job.id, '详情') + (!terminal ? button('cancelTask', job.id, '取消任务', 'danger', job.state === 'cancelling') : ['failed', 'interrupted', 'cancelled'].indexOf(job.state) >= 0 ? button('retryTask', job.id, '重试') : '') + (terminal ? button('deleteTask', job.id, '删除记录') : '') + '</div></article>';
    }).join('') : '<div class="empty-list"><h3>队列里还没有任务</h3><p>在本地模型中选择已安装的模型，填写提示词后加入队列。</p>' + button('showLocal', '', '选择本地模型', 'primary') + '</div>';
  }
  function renderArtifacts() {
    var all = ui.state().artifacts || [], artifacts = all.filter(function (a) { return artifactKind === 'all' || ((a.origin || {}).kind || 'generated') === artifactKind; }), imports = ui.state().inputImport || {}, signature = JSON.stringify([artifacts, artifactKind, imports]);
    if (signature === artifactSignature) return; artifactSignature = signature;
    $('artifactCount').textContent = artifacts.length + ' 项';
    $('inputImportStatus').innerHTML = imports.busy ? '<p class="form-help">正在导入 ' + e(imports.name || '所选素材') + ' · ' + Number(imports.pending || 1) + ' 项' + button('cancelInputImport', '', '取消导入') + '</p>' : '';
    document.querySelectorAll('[data-action="filterArtifacts"]').forEach(function (b) { var active = b.dataset.kind === artifactKind; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active)); });
    renderInputFields();
    $('artifactList').innerHTML = artifacts.length ? artifacts.slice().reverse().map(function (a) {
      var origin = a.origin || {}, imported = origin.kind === 'imported', m = a.metadata || {}, type = m.mime === 'application/vnd.lma.text+json' ? 'text' : (m.mime || '').split('/')[0];
      var cover = a.available && type === 'image' ? '<img class="artifact-thumb" src="/artifacts/' + e(a.id) + '" loading="lazy" alt="本地图片素材或结果">' : '<div class="artifact-placeholder">' + ui.icon(type === 'audio' ? 'play' : 'spark') + '<span>' + e(type === 'video' ? '视频' : type === 'audio' ? '音频' : type === 'text' ? '文本' : '生成结果') + '</span></div>';
      return '<article class="artifact-card">' + cover + '<div class="artifact-info"><strong>' + e(imported ? origin.name || '导入素材' : new Date(a.createdAt).toLocaleString('zh-CN')) + '</strong><p class="artifact-source">' + (imported ? '导入素材' : '生成结果') + (a.inUse ? ' · 任务正在引用' : '') + '</p><p>' + e(m.mime || '') + ' · ' + ui.bytes(a.bytes) + (m.width ? ' · ' + m.width + ' × ' + m.height : '') + '</p><div class="job-actions">' + button('artifactInfo', a.id, '打开', 'primary', !a.available) + button('exportArtifact', a.id, '导出', 'secondary', !a.available) + button('artifactRemove', a.id, '删除', 'secondary', a.inUse) + '</div></div></article>';
    }).join('') : '<div class="empty-list"><h3>这里还没有素材或结果</h3><p>导入本地素材，或选择模型生成结果。可预览、导出并查看文件来源。</p></div>';
  }
  function track(action, args, callback) { var id = ui.dispatch(action, args); if (id) pending[id] = callback || function () {}; return id; }
  function showArtifact(id, data) {
    var a = data, mime = a.metadata.mime, path = '/artifacts/' + encodeURIComponent(id), text = mime === 'application/vnd.lma.text+json', media = mime.indexOf('image/') === 0 ? '<img src="' + path + '" alt="本地生成图片" class="artifact-preview">' : mime.indexOf('audio/') === 0 ? '<audio controls preload="metadata" src="' + path + '"></audio>' : mime.indexOf('video/') === 0 ? '<video controls playsinline preload="metadata" src="' + path + '"></video>' : '';
    if (text) media = '<div id="textArtifact" data-id="' + e(id) + '"><p role="status">正在读取本地文本结果…</p></div>';
    ui.openModal((a.origin || {}).kind === 'imported' ? '本地导入素材' : '本地生成结果', media + '<p>' + e(mime) + ' · ' + ui.bytes(a.bytes) + '</p><details><summary>文件来源与任务记录</summary><pre class="provenance">' + e(JSON.stringify({origin: a.origin || {kind: 'generated'}, provenance: a.provenance}, null, 2)) + '</pre></details><p class="form-help artifact-sha">SHA256：' + e(a.sha256) + '</p><div class="modal-actions">' + (text ? button('copyArtifactText', id, '复制正文') : '') + button('exportArtifactMetadata', id, '导出来源记录') + button('exportArtifact', id, '导出原文件', 'primary') + '</div>', 'artifact');
    if (text) fetch(path, {cache: 'no-store'}).then(function (response) { if (!response.ok) throw new Error('无法读取本地文本结果'); return response.text(); }).then(function (raw) {
      if (raw.length > 8 * 1024 * 1024) throw new Error('文本结果过大');
      var value = JSON.parse(raw), panel = $('textArtifact');
      if (!panel || panel.dataset.id !== id) return;
      if (value.schema !== 'lma.text-result/1' || typeof value.content !== 'string' || typeof value.reasoning !== 'string') throw new Error('文本结果格式无效');
      panel.innerHTML = '<pre class="artifact-text"></pre><details class="artifact-reasoning"><summary>思考内容</summary><pre class="artifact-text"></pre></details><p class="form-help"></p>';
      var copy = $('modalContent').querySelector('[data-action="copyArtifactText"]'); if (copy) copy.disabled = !value.content;
      panel.querySelector('pre').textContent = value.content || '（本次仅输出思考内容）';
      panel.querySelector('details').hidden = !value.reasoning; panel.querySelector('details pre').textContent = value.reasoning;
      panel.querySelector('p').textContent = value.finishReason === 'length' ? '已达到本次输出上限' : '文本生成结束';
    }).catch(function (error) { var panel = $('textArtifact'); if (panel && panel.dataset.id === id) panel.textContent = error.message; });
  }
  function handle(action, el) {
    var id = el.dataset.id;
    if (window.LMAVersions.handle(action, el)) { editor = null; return true; }
    switch (action) {
      case 'inputPicker': ui.dispatch(action); return true;
      case 'cancelInputImport': track(action); return true;
      case 'filterArtifacts': artifactKind = ['all', 'generated', 'imported'].indexOf(el.dataset.kind) >= 0 ? el.dataset.kind : 'all'; renderArtifacts(); return true;
      case 'bundleInfo': info(id); return true;
      case 'bundleSettings': settings(id); return true;
      case 'bundleUse': use(id); return true;
      case 'downloadBundle': track(action, {id: id}, function () { ui.closeModal(); ui.selectLocal(); }); return true;
      case 'pauseBundle': case 'resumeBundle': case 'cancelTask': case 'deleteTask': case 'retryTask': track(action, {id: id}); return true;
      case 'bundleFolderPicker': ui.dispatch(action, {id: id}); return true;
      case 'bundleManifestPicker': ui.selectLocal(); ui.dispatch(action); return true;
      case 'bundleRemove': ui.confirm('删除本地模型资产？', '删除本机文件并保留此模型的独立设置。其他模型正在使用的共享组件会保留。', 'deleteBundle', id, '删除资产'); return true;
      case 'artifactRemove': ui.confirm('删除本地素材或结果？', '删除此原文件，历史任务记录保留。排队或运行中的任务引用、预览和导出会阻止删除；重试仍需要原素材。', 'deleteArtifact', id, '删除文件'); return true;
      case 'exportArtifact': case 'exportArtifactMetadata': ui.dispatch(action, {id: id}); return true;
      case 'copyArtifactText': { var panel = $('textArtifact'); if (panel && panel.dataset.id === id && panel.querySelector('pre')) ui.copy(panel.querySelector('pre').textContent); return true; }
      case 'artifactInfo': track('inspectArtifact', {id: id}, function (data) { showArtifact(id, data); }); return true;
      case 'jobInfo': track('inspectTask', {id: id}, function (data) { ui.openModal('任务详情', '<pre class="provenance">' + e(JSON.stringify(data, null, 2)) + '</pre>', 'job'); }); return true;
      default: return false;
    }
  }
  window.LMAFoundation = {
    init: function (bridge) {
      ui = bridge; window.LMAVersions.init(bridge);
      document.addEventListener('submit', function (event) {
        if (event.target.id === 'adapterPairForm') { event.preventDefault(); var adapter = editor && find(editor.id), base = find(event.target.elements.baseBundleId.value); if (adapter && base && base.installed && compatible(base, adapter)) use(base.id, adapter.id); return; }
        if (event.target.id !== 'bundleSettingsForm' && event.target.id !== 'localTaskForm') return;
        event.preventDefault(); if (!editor || editor.pending) return;
        var form = event.target, b = find(editor.id); if (!b) return;
        try {
          if (!form.reportValidity()) return;
          var parameters = readFields(form, b), submit = form.querySelector('[type="submit"]');
          var args = editor.mode === 'settings' ? {id: b.id, settings: parameters} : {request: {bundleId: b.id, type: form.elements.taskType.value, input: {prompt: form.elements.prompt.value, negativePrompt: form.elements.negativePrompt ? form.elements.negativePrompt.value : ''}, parameters: parameters, allowUnmeasured: form.elements.allowUnmeasured.checked}, idempotencyKey: 'ui-' + Date.now() + '-' + Math.random().toString(36).slice(2)};
          if (editor.mode === 'task') { var inputs = readInputs(form); if (inputs.length) args.request.input.artifacts = inputs; }
          if (editor.mode === 'task' && form.elements.taskType.value === 'image.generate') args.request.adapters = readAdapters(form, b);
          var editing = editor;
          editor.pending = track(editor.mode === 'settings' ? 'saveBundleSettings' : 'submitTask', args, function () { if (editor === editing) { ui.closeModal(); if (editing.mode === 'task') ui.route('tasks'); } ui.toast(editing.mode === 'task' ? '任务已加入本机队列' : '已保存此模型的独立设置'); });
          if (editor.pending) { submit.disabled = true; $('bundleFormHint').textContent = '正在提交…'; }
        } catch (error) { $('bundleFormHint').textContent = error.message; }
      });
      document.addEventListener('change', function (event) {
        if (event.target.dataset.adapterSelect) {
          var row = event.target.closest('.task-adapter'), scale = row.querySelector('[data-adapter-scale]'); scale.disabled = !event.target.checked; return;
        }
        if (event.target.name === 'taskType') { renderInputFields(); if ($('taskAdapters')) { $('taskAdapters').disabled = event.target.value !== 'image.generate'; $('taskAdapters').hidden = event.target.value !== 'image.generate'; } return; }
        if (event.target.id !== 'bundleShape' || !editor || event.target.value === '') return;
        var b = find(editor.id), shape = schemaFor(b).allowedShapes[Number(event.target.value)];
        $('modalContent').querySelectorAll('[data-bundle-field]').forEach(function (input) { if (Object.prototype.hasOwnProperty.call(shape, input.dataset.bundleField)) input.value = shape[input.dataset.bundleField]; });
      });
      document.addEventListener('focusout', function (event) {
        if (editor && event.target.dataset.adapterScale) { try { readAdapters(event.target.form, find(editor.id)); $('bundleFormHint').textContent = 'LoRA 强度已按各自约束检查'; } catch (error) { $('bundleFormHint').textContent = error.message; } return; }
        if (!editor || !event.target.dataset.numeric || !event.target.dataset.bundleField) return;
        try { readFields(event.target.form, find(editor.id)); $('bundleFormHint').textContent = '参数已按此配方的约束检查'; } catch (error) { $('bundleFormHint').textContent = error.message; }
      });
    },
    views: views, card: card, handle: handle,
    receive: function () {
      renderJobs(); renderArtifacts(); window.LMAVersions.receive();
      Object.keys(pending).forEach(function (id) {
        var result = ui.result(id); if (!result) return; var callback = pending[id]; delete pending[id];
        if (result.ok) callback(result.data);
        else { if (editor) { editor.pending = false; var submit = $('modalContent').querySelector('[type="submit"]'); if (submit) submit.disabled = false; } if ($('bundleFormHint')) $('bundleFormHint').textContent = result.error; ui.toast(result.error || '操作失败'); }
      });
    },
    close: function () { editor = null; window.LMAVersions.close(); $('modalContent').querySelectorAll('audio,video').forEach(function (media) { media.pause(); media.removeAttribute('src'); media.load(); }); }
  };
})();
