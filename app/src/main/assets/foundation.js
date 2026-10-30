(function () {
  'use strict';
  var ui, pending = {}, editor = null, listSignature = '', artifactSignature = '', artifactKind = 'all', jobKind = 'all', jobSearch = '', jobLimit = 20;
  var $ = function (id) { return document.getElementById(id); };
  var labels = {text: '生文', image: '生图', video: '生视频', audio: '生音频'};
  var states = {queued: '排队中', loading: '加载中', running: '生成中', cancelling: '取消中', cancelled: '已取消', failed: '失败', succeeded: '已完成', interrupted: '已中断'};
  var stages = {queued: '等待执行', waiting_engine: '等待本机执行槽', validating_inputs: '校验本地素材', loading: '加载模型', loading_diffusion: '加载生图组件', sampling: '采样中', encoding: '编码媒体', synthesizing: '合成语音', text_encoding: '编码文本', encoding_text: '编码文本', decoding: '解码输出', generating: '生成文本', saving: '保存结果', associating_runtime_assets: '关联本地组件', video_noise: '准备视频噪声', video_text_encoding: '编码视频提示词', video_sampling: '生成视频', video_latent_layout: '整理视频潜变量', video_decoding: '解码视频', video_frames: '准备编码帧'};
  var paramNames = {width: '宽度', height: '高度', frames: '帧数', fps: '帧率', steps: '采样步数', cfg: '提示词引导', seed: '随机种子', threads: 'CPU 线程', sampler: '采样器', scheduler: '调度器', duration: '时长（秒）', speed: '语速', context: '上下文长度', maxTokens: '单次输出上限', temperature: '采样温度', reasoning: '思考模式', systemPrompt: '系统提示词', streamAudio: '流式试听'};
  function entries() { return ui.state() && ui.state().bundles || []; }
  function find(id) { return entries().filter(function (b) { return b.id === id; })[0]; }
  function e(value) { return ui.esc(value); }
  function button(action, id, text, style, disabled) { return '<button class="button ' + (style || 'secondary') + '" data-action="' + action + '" data-id="' + e(id) + '"' + (disabled ? ' disabled' : '') + '>' + text + '</button>'; }
  function engineAvailable(b) { return (b.manifest.capabilities || []).indexOf('source_assets') < 0 && !b.parameterError && (ui.state().localEngines || []).some(function (engine) { return engine.engine === b.manifest.engine && engine.available && (!engine.requiredModelCapability || (b.manifest.capabilities || []).indexOf(engine.requiredModelCapability) >= 0); }); }
  function isAdapter(b) { return !!(b.manifest.adapter && b.manifest.adapter.kind === 'lora'); }
  function compatible(base, adapter) {
    var m = base.manifest, a = adapter.manifest.adapter;
    if (m.conditionBias) return false;
    return !!a && !isAdapter(base) && m.engine === adapter.manifest.engine && m.backend === adapter.manifest.backend && tasks(base).indexOf('image') >= 0 && (a.baseArchitectures || []).indexOf(m.architecture) >= 0 && (a.basePipelines || []).indexOf(m.pipeline) >= 0 && (!a.baseModelIds || a.baseModelIds.indexOf(m.modelId) >= 0);
  }
  function tasks(b) { return (b.manifest.tasks || []).filter(function (tag) { return labels[tag]; }); }
  function taskTags(b) { return tasks(b).map(function (t) { return '<span class="tag task-tag task-' + t + '">' + labels[t] + '</span>'; }).join('') + (isAdapter(b) ? '<span class="tag">LoRA</span><span class="tag">需要基础模型</span>' : '') + (b.manifest.uncensored && b.manifest.uncensored.detected ? '<span class="tag">无审查线索 · 待核对</span>' : ''); }
  function embedded(c) {
    var labels = {text_tokenizer:'文本分词数据',code_predictor:'音频码预测器',speaker_assets:'说话人编码器'};
    return c.provides && c.provides.length ? '<p class="modal-help">此文件内含：' + c.provides.map(function (role) { return e(labels[role] || role); }).join('、') + '。这些依赖无需重复下载。</p>' : '';
  }
  function views() {
    var aliases = (ui.state().models || []).map(function (m) { return m.bundleId; }).filter(Boolean);
    return entries().filter(function (b) { var legacy = b.manifest.migration && b.manifest.migration.source === 'legacy_text_store' && b.manifest.migration.legacyId;
      return aliases.indexOf(b.id) < 0 && !(legacy && (ui.state().models || []).some(function (m) { return m.id === legacy; })); }).map(function (b) {
      var m = b.manifest, p = b.plan || {};
      return {id: 'bundle::' + b.id, bundleId: b.id, isBundle: true, name: m.name, family: m.architecture, repository: (m.components[0] || {}).repository || '', description: m.description || '', taskTags: tasks(b), tier: m.catalogue ? 'catalogue' : 'custom', installed: b.installed, hasPreparedAssets: (b.preparedAssets || []).length > 0, bytes: p.totalBytes, installedBytes: p.totalBytes, download: b.transfer, imported: !m.catalogue, bundle: b};
    });
  }
  function card(m) {
    var b = m.bundle, manifest = b.manifest, t = b.transfer || {}, plan = b.plan || {};
    var active = ['queued', 'downloading', 'verifying', 'installing'].indexOf(t.state) >= 0;
    var message = b.installed ? '已安装 · 设备待验证' : m.hasPreparedAssets ? '运行资产已准备 · 源文件未安装' : active ? ({queued: '等待下载', downloading: '下载组件', verifying: '校验组件', installing: '安装中'}[t.state]) : t.state === 'paused' ? '已暂停' : t.state === 'failed' ? '下载失败' : '尚未下载';
    return '<article class="model-card bundle-card" data-bundle="' + e(b.id) + '"><div class="model-top"><span class="model-symbol">' + ui.icon('cube') + '</span><div class="model-top-copy"><button class="model-name" data-action="bundleInfo" data-id="' + e(b.id) + '"><strong>' + e(manifest.name) + '</strong><span class="model-caption">' + e(manifest.architecture) + ' / ' + e(manifest.backend) + '</span></button></div></div><p class="model-description">' + e(manifest.description || '由用户选择的本地模型包') + '</p><div class="model-tags">' + taskTags(b) + window.LMAVersions.badge(b) + '<span class="tag">' + e(manifest.engine) + '</span><span class="tag">' + e(message) + '</span></div><div class="model-footer"><div class="model-size">' + ui.bytes(plan.totalBytes) + '<small>' + manifest.components.length + ' 个必需组件</small></div><div class="model-footer-actions">' + (b.installed ? (!engineAvailable(b) && (b.preparationPlans || []).length ? button('bundleInfo', b.id, '运行资产', 'primary', b.inUse) : button('bundleUse', b.id, isAdapter(b) ? '配对使用' : '使用', 'primary', b.inUse || !engineAvailable(b))) : active ? button('pauseBundle', b.id, '暂停') : button('bundleInfo', b.id, m.hasPreparedAssets ? '管理运行资产' : t.state === 'paused' || t.state === 'failed' ? '继续下载' : '查看并下载', 'primary')) + '</div></div>' + (active ? '<p class="form-help">' + e(t.role || '') + (t.received ? ' · ' + ui.bytes(t.received) : '') + '</p>' : '') + (t.error ? '<p class="download-error">' + e(t.error) + '</p>' : '') + '</article>';
  }
  function dependencySection(adapter) {
    if (!isAdapter(adapter)) return '';
    var bases = entries().filter(function (base) { return compatible(base, adapter); });
    return '<section class="bundle-dependencies"><h3>兼容基础模型</h3><p class="form-help">LoRA 需配合基础模型使用。查看后由你单独下载或导入；下载此 LoRA 不会自动下载基础模型。</p>' + (bases.length ? bases.map(function (base) {
      var status = base.installed ? (base.inUse ? '已安装 · 使用中' : '已安装') : base.transfer ? '传输未完成' : '尚未安装';
      return '<article class="hub-file"><strong>' + e(base.manifest.name) + '</strong><div class="model-tags"><span class="tag">' + e(status) + '</span><span class="tag">' + e(base.manifest.architecture) + '</span></div>' + button('bundleDependencyInfo', base.id, '查看基础模型').replace('data-id=', 'data-adapter="' + e(adapter.id) + '" data-id=') + '</article>';
    }).join('') : '<p class="empty-list">当前模型库没有声明兼容的基础模型。可在全部 / 搜索中选择，或导入完整模型包，再回来配对。</p>') + '</section>';
  }
  function info(id, returnAdapterId) {
    var b = find(id); if (!b) return; var m = b.manifest, p = b.plan || {};
    var files = p.components || [];
    var adapterHelp = isAdapter(b) ? '<p class="form-help">此包仅包含 LoRA。基础模型由你另外选择、安装；只与声明兼容的 ' + e(m.adapter.baseArchitectures.join(' / ')) + ' / ' + e(m.adapter.basePipelines.join(' / ')) + ' 配方配对。兼容声明仍需实际权重验证。</p>' : '';
    var html = '<div class="model-info"><div class="model-tags">' + taskTags(b) + '<span class="tag">' + e(m.engine) + '</span><span class="tag">' + e(m.pipeline) + '</span></div><p>' + e(m.description || '') + '</p><p>' + (b.parameterError ? e(b.parameterError) : (m.capabilities || []).indexOf('source_assets') >= 0 ? '这是用于准备运行资产的源模型。请选择下方的准备方案，再明确关联运行模型。' : engineAvailable(b) ? '运行引擎已随 App 安装，当前配方仍需手机实测。' : '当前基座缺少匹配引擎。下载文件不会安装引擎，请等待对应的 App 更新。') + '</p>' + adapterHelp + '<dl><dt>完整模型包</dt><dd>' + ui.bytes(p.totalBytes) + '</dd><dt>可复用资产</dt><dd>' + ui.bytes(p.reusableBytes) + '</dd><dt>剩余传输</dt><dd>' + ui.bytes(p.remainingBytes) + '</dd><dt>配方</dt><dd>' + e(m.recipeId) + '</dd><dt>许可</dt><dd>' + e(typeof m.license === 'string' ? m.license : m.license && m.license.name || '尚未声明，请核对来源') + '</dd></dl>' + dependencySection(b) + '<div class="bundle-components">' + files.map(function (c) { return '<details><summary>' + e(c.role) + ' · ' + ui.bytes(c.bytes) + (c.reusable ? ' · 可复用' : '') + '</summary><p>' + e(c.path) + '</p>' + embedded(c) + (c.importPath && c.importPath !== c.path ? '<p class="modal-help">文件夹导入路径：' + e(c.importPath) + '</p>' : '') + '<code>' + e(c.sha256 ? 'SHA256 ' + c.sha256 : 'Git blob SHA-1 ' + c.gitBlobSha1) + '</code>' + (c.verifiedSha256 ? '<code>已校验 SHA256 ' + e(c.verifiedSha256) + '</code>' : '') + '</details>'; }).join('') + '</div><p class="modal-help">只下载这套包及上面列出的必需组件。浏览、App 升级与缺失模型的生成请求均不会触发下载。所有生成步骤在这部手机上执行。</p><div class="modal-actions">';
    var returnAdapter = find(returnAdapterId);
    if (returnAdapter && isAdapter(returnAdapter) && compatible(b, returnAdapter)) html += button('bundleInfo', returnAdapter.id, '返回 LoRA');
    if (b.installed) html += button('bundleSettings', id, '模型设置') + button('bundleUse', id, isAdapter(b) ? '选择基础模型' : '使用模型', 'primary', !engineAvailable(b) || b.inUse);
    else html += button('bundleFolderPicker', id, '从文件夹导入') + button('downloadBundle', id, '下载所选模型包', 'primary', files.some(function (c) { return !c.reusable && !c.downloadable; }));
    html += '</div>' + (b.installed || (b.version || {}).groupId ? button('bundleVersions', id, '版本管理 / 独立更新') : '') + button('bundleRemove', id, '删除本地资产', 'danger', b.inUse) + '</div>';
    editor = null; ui.openModal(m.name, html + preparationSection(b), 'bundleInfo');
  }
  function schemaFor(b) { return b.parameterSchema || b.manifest.parameters || {}; }
  function preparationSection(b) {
    var plans = b.preparationPlans || [], prepared = b.preparedAssets || [];
    if (!plans.length && !prepared.length) return '';
    return '<section class="preparation-section"><h3>运行资产</h3><p>从已下载或导入的源模型准备运行文件。源文件与模型设置保留，准备后的文件可单独管理。</p>' + plans.map(function (plan) {
      return '<article class="hub-file"><strong>' + e(plan.name) + '</strong><p>' + ui.bytes(plan.outputBytes) + ' · ' + (plan.ready ? '已准备' : '待准备') + '</p><button class="button secondary" data-action="preparationInfo" data-id="' + e(b.id) + '" data-preparation="' + e(plan.id) + '"' + (!b.installed || b.inUse || plan.ready ? ' disabled' : '') + '>查看准备方案</button>' + (!b.installed ? '<small>先选择下载或文件夹导入，再准备运行资产。</small>' : '') + '</article>';
    }).join('') + prepared.map(function (record) {
      return '<article class="hub-file"><strong>' + (record.available ? '已准备的运行资产' : '运行资产缺失或已改变') + '</strong><p>' + ui.bytes(record.bytes) + ' · ' + new Date(record.createdAt).toLocaleString('zh-CN') + '</p>' + button('preparedRemove', record.id, '删除准备资产', 'danger', record.inUse) + (record.assemblyPlans || []).map(function (plan) { return '<p>' + button(plan.associated ? 'bundleInfo' : 'assemblyInfo', plan.associated ? plan.bundleId : record.id, plan.associated ? '管理运行模型' : '查看关联方案', 'secondary', !plan.associated && (!record.available || record.inUse)).replace('data-id=', 'data-assembly="' + e(plan.id) + '" data-id=') + '</p>'; }).join('') + '</article>';
    }).join('') + '</section>';
  }
  function assemblyInfo(id, planId) {
    var record, plan;
    entries().some(function (b) { record = (b.preparedAssets || []).filter(function (r) { return r.id === id; })[0]; return !!record; });
    if (!record || !record.available || record.inUse) return;
    plan = (record.assemblyPlans || []).filter(function (p) { return p.id === planId; })[0]; if (!plan || plan.associated) return;
    var target = find(plan.bundleId); if (!target) return;
    editor = null; ui.openModal('关联运行模型', '<div class="model-info"><h3>' + e(target.manifest.name) + '</h3><p>' + e(target.manifest.description) + '</p><dl><dt>复用本地组件</dt><dd>' + plan.linkedComponents + ' 个 · ' + ui.bytes(plan.linkedBytes) + '</dd><dt>仍需选择的依赖</dt><dd>' + (plan.remainingComponents || []).map(function (c) { return e(c.path) + ' · ' + ui.bytes(c.bytes); }).join('<br>') + '</dd></dl><p>点击后加入本机队列，校验并关联已有文件，不额外复制模型。缺少的依赖保持未安装、暂停状态，由你随后选择下载或导入。关联完成后可独立管理两份记录，生成能力和设备兼容性以模型状态为准。</p><div class="modal-actions"><button class="button primary" data-action="assembleAssets" data-id="' + e(id) + '" data-assembly="' + e(plan.id) + '" data-bundle="' + e(plan.bundleId) + '" data-fingerprint="' + e(plan.fingerprint) + '">开始关联</button></div></div>', 'assemblyInfo');
  }
  function preparationInfo(id, planId) {
    var b = find(id); if (!b) return;
    var plan = (b.preparationPlans || []).filter(function (p) { return p.id === planId; })[0]; if (!plan || !b.installed || plan.ready) return;
    editor = null; ui.openModal('准备运行资产', '<div class="model-info"><h3>' + e(b.manifest.name) + '</h3><p>' + e(plan.name) + '</p><dl><dt>保留源模型</dt><dd>' + ui.bytes(plan.sourceBytes) + '</dd><dt>新增运行资产</dt><dd>' + ui.bytes(plan.outputBytes) + '</dd><dt>所需额外可用空间</dt><dd>' + ui.bytes(plan.requiredFreeBytes) + '</dd></dl><p>点击后加入本机任务队列，离开页面后继续。可在任务页取消；中断后由你选择重试。准备完成后，生成能力和设备兼容性仍以模型状态为准。</p><div class="modal-actions"><button class="button primary" data-action="prepareAssets" data-id="' + e(id) + '" data-preparation="' + e(plan.id) + '" data-fingerprint="' + e(plan.fingerprint) + '">开始准备</button></div></div>', 'preparationInfo');
  }
  function numericChoices(f) {
    return (Array.isArray(f.choices) ? f.choices : []).slice(0, 128).filter(function (choice) { return choice && typeof choice.value === 'number' && isFinite(choice.value) && typeof choice.label === 'string' && choice.label.length <= 80; });
  }
  function numericDisplay(f, value) {
    var choice = numericChoices(f).filter(function (choice) { return choice.value === value; })[0];
    return choice ? String(value) + ' · ' + choice.label : String(value);
  }
  function numericValue(f, raw) {
    var text = raw.trim(), choices = numericChoices(f), match = choices.filter(function (choice) { return numericDisplay(f, choice.value) === text; });
    if (match.length === 1) return match[0].value;
    match = choices.filter(function (choice) { return choice.label === text; });
    return match.length === 1 ? match[0].value : Number(text);
  }
  function numericHint(f, values, all) {
    var maximum = f.maximum, bound = f.maximumFrom;
    if (bound && all[bound.field]) {
      var source = Object.prototype.hasOwnProperty.call(values, bound.field) ? values[bound.field] : all[bound.field].default;
      maximum = Math.min(maximum === undefined ? Infinity : maximum, Number(source) + (bound.offset || 0));
      if (f.type === 'integer') maximum = Math.floor(maximum);
      if (f.multipleOf) maximum = (f.alignmentOrigin || 0) + Math.floor((maximum - (f.alignmentOrigin || 0)) / f.multipleOf) * f.multipleOf;
    }
    return (f.minimum !== undefined ? '最低 ' + e(f.minimum) + ' · ' : '') + (maximum !== undefined && isFinite(maximum) ? (bound ? '当前上限 ' : f.limitSource === 'application_guard' ? '应用保护上限 ' : f.limitSource === 'publisher_metadata_unverified' ? '发布者声明上限（待核对）' : '上限 ') + e(maximum) : '模型上限未声明') + (bound ? ' · 受' + e(all[bound.field] && all[bound.field].label || paramNames[bound.field] || bound.field) + '约束' : '') + (f.multipleOf ? ' · 步长 ' + e(f.multipleOf) : '') + (f.actualVoiceCount ? ' · ' + e(f.actualVoiceCount) + ' 个音色' : '');
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
        var presets = (f.presets || []).filter(function (v) { return typeof v === 'number' && isFinite(v); }), choices = numericChoices(f);
        out += '<input type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" list="' + name + '" data-bundle-field="' + e(key) + '" data-numeric="true" value="' + e(numericDisplay(f, value)) + '" inputmode="' + (f.type === 'integer' ? 'numeric' : 'decimal') + '" autocomplete="off"><datalist id="' + name + '">' + (choices.length ? choices.map(function (choice) { return '<option value="' + e(numericDisplay(f, choice.value)) + '">' + e(choice.label) + '</option>'; }) : presets.map(function (v) { return '<option value="' + v + '"></option>'; })).join('') + '</datalist><small data-bundle-bound-caption="' + e(key) + '">' + numericHint(f, values, all) + '</small>';
      }
      if (f.help) out += '<small>' + e(f.help) + '</small>';
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
        var parsed = numericValue(f, input.value);
        if (!input.value.trim() || !isFinite(parsed)) throw new Error((f.label || paramNames[key] || key) + '需要有效数字或已列出的选项');
        value = parsed; if (f.type === 'integer') value = Math.floor(value);
        if (f.minimum !== undefined) value = Math.max(value, f.minimum);
        if (f.maximum !== undefined) value = Math.min(value, f.maximum);
        if (f.multipleOf) value = (f.alignmentOrigin || 0) + Math.floor((value - (f.alignmentOrigin || 0)) / f.multipleOf) * f.multipleOf;
        if (f.minimum !== undefined && value < f.minimum) throw new Error('参数没有满足约束的值');
        input.value = numericDisplay(f, value);
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
        form.querySelectorAll('[data-bundle-field]').forEach(function (input) { if (input.dataset.bundleField === key) input.value = numericDisplay(f, value); });
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
    var adapter = find(id); if (!adapter || !isAdapter(adapter)) return;
    var bases = entries().filter(function (base) { return base.installed && !base.inUse && engineAvailable(base) && compatible(base, adapter); });
    editor = {id: id, mode: 'pair'};
    ui.openModal('选择基础模型 · ' + adapter.manifest.name, '<form id="adapterPairForm"><p class="form-help">LoRA 需要与已安装的兼容基础模型配对。此操作不会下载或替换任何权重。</p>' + (bases.length ? '<label class="form-field"><span>已安装的兼容基础模型</span><select name="baseBundleId" required>' + bases.map(function (base) { return '<option value="' + e(base.id) + '">' + e(base.manifest.name) + '</option>'; }).join('') + '</select></label>' : '<p class="empty-list">尚未安装兼容的基础模型。请在模型库自行选择下载或导入，再回来配对。</p>' + dependencySection(adapter)) + '<div class="modal-actions">' + button('closeModal', '', '关闭') + (bases.length ? '<button class="button primary" type="submit">填写生成任务</button>' : '') + '</div></form>', 'adapterPair');
  }
  function adapterFields(base, selected) {
    if (base.manifest.conditionBias) return '<p class="form-help">此模型的条件组件固定，不支持叠加 LoRA。使用 LoRA 时请选择独立基础模型。</p>';
    var adapters = entries().filter(function (adapter) { return adapter.installed && !adapter.inUse && engineAvailable(adapter) && compatible(base, adapter); });
    if (!adapters.length) return '<p class="form-help">当前没有已安装的兼容 LoRA；可在模型库自行选择下载或导入。</p>';
    return '<fieldset id="taskAdapters" class="task-adapters"><legend>LoRA（可选，最多 8 个）</legend><p class="form-help">仅列出已安装且声明兼容的适配器。各自强度独立保存，本次修改只用于当前任务。</p>' + adapters.map(function (adapter, index) {
      var f = adapter.manifest.parameters.fields.scale, value = adapter.config && adapter.config.values && adapter.config.values.scale;
      if (value === undefined) value = f.default;
      return '<div class="task-adapter"><label class="adapter-choice"><input type="checkbox" data-adapter-select="' + e(adapter.id) + '"' + (adapter.id === selected ? ' checked' : '') + '><span>' + e(adapter.manifest.name) + '</span></label><label class="form-field"><span>强度</span><input type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" data-adapter-scale="' + e(adapter.id) + '" list="adapter-scale-' + index + '" inputmode="decimal" autocomplete="off" value="' + e(value) + '"' + (adapter.id === selected ? '' : ' disabled') + '><datalist id="adapter-scale-' + index + '">' + (f.presets || []).map(function (preset) { return '<option value="' + e(preset) + '"></option>'; }).join('') + '</datalist><small>' + e(f.minimum) + ' 至 ' + e(f.maximum) + '</small></label></div>';
    }).join('') + '</fieldset>';
  }
  function renderSamplingHint() {
    var form = $('localTaskForm'), b = editor && find(editor.id), hint = $('samplingHint'); if (!form || !b || !hint) return;
    var count = 0;
    form.querySelectorAll('[data-adapter-select]:checked').forEach(function (choice) { var a = find(choice.dataset.adapterSelect); if (a && a.manifest.adapter.sampling === 'lcm') count++; });
    var pipeline = b.manifest.pipeline, lcm = count > 0 || /_lcm$/.test(pipeline), z = pipeline === 'z_image_turbo', flux = pipeline === 'flux2_klein_4b', active = lcm || pipeline === 'sd21_turbo' || z || flux, limit = lcm || z ? 8 : 4;
    form.dataset.samplingProfile = active ? (lcm ? 'lcm' : z ? 'z_image_turbo' : flux ? 'flux2_klein' : 'sd_turbo') : '';
    hint.hidden = !active;
    hint.textContent = count > 1 || count && /_lcm$/.test(pipeline) ? '一次只使用一个 LCM 加速来源，请取消多余选择。' : (lcm ? 'LCM：采样器 lcm，调度器 lcm，1–8 步。' : z ? 'Z-Image-Turbo：采样器 euler，调度器 discrete，1–8 步。' : flux ? 'FLUX.2-klein：采样器 euler，调度器 flux2，1–4 步。' : 'SD-Turbo：采样器 euler_a，调度器 discrete，1–4 步。') + 'CFG 固定为 1，不使用负面提示词；仅影响本次任务，保存的模型设置保留。';
    if (form.elements.negativePrompt) { var fixed = ((b.inputSchemas || {})[form.elements.taskType.value] || {}).fixedPrompt; form.elements.negativePrompt.disabled = active || !!fixed; form.elements.negativePrompt.closest('label').hidden = active || !!fixed; }
    ['cfg', 'steps'].forEach(function (key) {
      var field = form.querySelector('[data-bundle-field="' + key + '"]'); if (!field) return;
      if (active) { if (field.dataset.beforeSampling === undefined) field.dataset.beforeSampling = field.value; field.value = key === 'cfg' ? 1 : Math.max(1, Math.min(limit, Math.floor(Number(field.value) || 4))); }
      else if (field.dataset.beforeSampling !== undefined) { field.value = field.dataset.beforeSampling; delete field.dataset.beforeSampling; }
      if (key === 'cfg') field.disabled = active;
    });
    ['sampler', 'scheduler'].forEach(function (key) { var f = form.querySelector('[data-bundle-field="' + key + '"]'); if (f) f.closest('label').hidden = active; });
    if (pipeline === 'sana_edit_mnn_v1') { hint.hidden = false; hint.textContent = 'Sana 图片风格转换：15 个配套组件；必选本地 PNG/JPEG，最多 16 MiB / 400 万像素；输出固定 512×512，1–50 步。使用配套固定提示词，不接收负面条件或 CFG。手机输出与资源尚待实测。'; }
    if (pipeline === 'sana_mnn_v1') { hint.hidden = false; hint.textContent = '旧 Sana 文生图配方不兼容此编辑模型。文件、设置和历史任务保留；请在全部 / HF 中明确选择新的 15 组件图片风格转换配方。'; }
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
    return a.available && (rule.mimes || []).indexOf(m.mime) >= 0 && a.bytes <= rule.maxBytes && (!rule.minDurationMs || m.durationMs >= rule.minDurationMs) && (!rule.maxDurationMs || m.durationMs > 0 && m.durationMs <= rule.maxDurationMs) && (!rule.maxPixels || m.width > 0 && m.height > 0 && m.width * m.height <= rule.maxPixels);
  }
  function renderInputFields() {
    var panel = $('taskInputs'), form = $('localTaskForm'), b = editor && find(editor.id); if (!panel || !form || !b) return;
    var selected = {}, transcripts = {}; panel.querySelectorAll('[data-input-role]').forEach(function (s) { selected[s.dataset.inputRole] = s.value; });
    panel.querySelectorAll('[data-input-transcript]').forEach(function (t) { transcripts[t.dataset.inputTranscript] = t.value; });
    var schema = (b.inputSchemas || {})[form.elements.taskType.value], roles = schema && schema.roles || {}, keys = Object.keys(roles);
    var fixed = schema && schema.fixedPrompt; form.elements.prompt.readOnly = !!fixed;
    if (fixed) form.elements.prompt.value = fixed;
    if (form.elements.negativePrompt) { form.elements.negativePrompt.disabled = !!fixed || !!form.dataset.samplingProfile; form.elements.negativePrompt.closest('label').hidden = form.elements.negativePrompt.disabled; }
    panel.innerHTML = (schema && schema.promptHelp ? '<p class="form-help">' + e(schema.promptHelp) + '</p>' : '') + (keys.length ? '<h3>本地输入素材</h3>' + keys.map(function (role) {
      var rule = roles[role], choices = (ui.state().artifacts || []).filter(function (a) { return inputRuleMatch(a, rule); });
      var active = choices.some(function (a) { return a.id === selected[role]; });
      return '<label class="form-field"><span>' + e(rule.label) + (rule.required ? '（必选）' : '（可选）') + '</span><select data-input-role="' + e(role) + '"' + (rule.required ? ' required' : '') + '><option value="">选择已导入素材或已有结果</option>' + choices.map(function (a) { var origin = a.origin || {}; return '<option value="' + e(a.id) + '"' + (selected[role] === a.id ? ' selected' : '') + '>' + e(origin.name || a.id) + ' · ' + ui.bytes(a.bytes) + '</option>'; }).join('') + '</select><small>' + e((rule.mimes || []).join(' / ')) + ' · ≤ ' + ui.bytes(rule.maxBytes) + (choices.length ? '' : ' · 暂无匹配素材') + '</small></label>' + (rule.transcript ? '<label class="form-field"><span>' + e(rule.transcript.label) + '</span><textarea rows="2" data-input-transcript="' + e(role) + '" maxlength="' + Number(rule.transcript.maxLength) + '"' + (active ? ' required' : ' disabled') + ' placeholder="填写这段参考音频实际说出的原文">' + e(transcripts[role] || '') + '</textarea><small>选择对应素材后必填；原文与素材一起固定到本次任务。</small></label>' : '');
    }).join('') + button('inputPicker', '', '导入新素材') : '<p class="form-help">当前配方仅接受文字。导入素材不会自动开启图像编辑或语音克隆。</p>');
    editor.inputSignature = inputSignature(b, form);
  }
  function inputSignature(b, form) { return JSON.stringify([form.elements.taskType.value, b.inputSchemas || {}, (ui.state().artifacts || []).map(function (a) { return [a.id, a.available, a.bytes, a.metadata, a.origin]; })]); }
  function refreshTaskInputs() {
    var form = $('localTaskForm'), b = editor && editor.mode === 'task' && find(editor.id); if (!form || !b || editor.inputSignature === inputSignature(b, form)) return;
    var selected = {}; form.querySelectorAll('[data-input-role]').forEach(function (input) { if (input.value) selected[input.dataset.inputRole] = input.value; });
    renderInputFields(); preflightChanged(form);
    var removed = Object.keys(selected).filter(function (role) { return !Array.from(form.querySelectorAll('[data-input-role]')).some(function (input) { return input.dataset.inputRole === role && input.value === selected[role]; }); });
    if (removed.length) {
      var notice = $('inputRefreshNotice'); if (!notice) { notice = document.createElement('div'); notice.id = 'inputRefreshNotice'; notice.className = 'restore-notice'; $('taskInputs').after(notice); }
      notice.innerHTML = '<p>已选参考素材已删除或不再符合输入要求，请重新选择。</p><label class="unmeasured-choice"><input type="checkbox" name="inputRefreshReview" required><span>我已检查本次参考素材，确认当前选择。</span></label>';
    }
  }
  function readInputs(form) {
    var result = [];
    form.querySelectorAll('[data-input-role]').forEach(function (select) { if (select.value) result.push({role: select.dataset.inputRole, artifactId: select.value}); });
    return result;
  }
  function readTranscripts(form) {
    var result = {};
    form.querySelectorAll('[data-input-transcript]').forEach(function (text) { if (!text.disabled) { if (!text.value.trim()) throw new Error('请填写参考音频实际说出的原文'); result[text.dataset.inputTranscript] = text.value; } });
    return result;
  }
  function taskRequest(form, b, draft) {
    var request = {bundleId: b.id, type: form.elements.taskType.value, input: {prompt: form.elements.prompt.value, negativePrompt: form.elements.negativePrompt && !form.elements.negativePrompt.disabled ? form.elements.negativePrompt.value : ''}, parameters: readFields(form, b), allowUnmeasured: !draft && form.elements.allowUnmeasured.checked};
    var inputs = readInputs(form), transcripts = {};
    if (inputs.length) request.input.artifacts = inputs;
    if (draft) form.querySelectorAll('[data-input-transcript]').forEach(function (text) { if (!text.disabled && text.value.trim()) transcripts[text.dataset.inputTranscript] = text.value; });
    else transcripts = readTranscripts(form);
    if (Object.keys(transcripts).length) request.input.transcripts = transcripts;
    if (request.type === 'image.generate') request.adapters = readAdapters(form, b);
    return request;
  }
  function preflightChanged(form) {
    if (!form || form.id !== 'localTaskForm') return;
    form.dataset.checkRevision = String(Number(form.dataset.checkRevision || 0) + 1);
    var panel = $('taskPreflight');
    if (panel && panel.textContent) { panel.className = 'task-preflight'; panel.textContent = '输入或参数已改变，请重新检查。提交时仍会重新校验。'; }
  }
  function showPreflight(report) {
    var panel = $('taskPreflight'); if (!panel) return;
    var names = {request:'请求格式',models:'模型能力',engine:'本地引擎',parameters:'模型参数',assets:'模型组件与 LoRA',inputs:'参考素材',recipe:'运行配方',resources:'资源预算',capacity:'队列与结果容量',consent:'试运行确认'};
    var resources = report.resources, issues = report.issues || [], changes = report.adjustments || [];
    panel.className = 'task-preflight ' + (report.canEnqueue ? 'preflight-ready' : 'preflight-blocked');
    panel.innerHTML = '<strong>' + (report.canEnqueue ? '可加入本机队列' : '需要处理后再提交') + '</strong><p class="form-help">这是当前条件下的提交检查。执行前会重新检查；尚无本机实测记录。</p>' +
      issues.map(function (issue) { return '<p class="download-error">' + e(names[issue.code] || '本地检查') + '：' + e(issue.message) + '</p>'; }).join('') +
      (report.warnings || []).map(function (warning) { return '<p class="form-help">' + e(warning.message) + '</p>'; }).join('') +
      (resources ? '<dl><dt>当前可用内存</dt><dd>' + ui.bytes(resources.availableRamBytes) + '</dd><dt>排队内存预算</dt><dd>' + ui.bytes(resources.budgetRamBytes) + '</dd><dt>峰值内存估算</dt><dd>' + (resources.estimateKnown ? ui.bytes(resources.estimatedPeakRamBytes) : '未知') + '</dd><dt>产物预留空间</dt><dd>' + ui.bytes(resources.outputReserveBytes) + '</dd><dt>可用存储</dt><dd>' + ui.bytes(resources.availableStorageBytes) + '</dd></dl>' : '') +
      (report.modelAssets || []).filter(function (asset) { return !asset.installed; }).map(function (asset) { var b = find(asset.bundleId); return '<p>' + e(b ? b.manifest.name : asset.bundleId) + '：' + (asset.components || []).filter(function (component) { return !component.present; }).map(function (component) { return e(component.role) + ' · ' + ui.bytes(component.bytes) + (component.downloadable ? '' : '（需导入）'); }).join('、') + '</p>'; }).join('') +
      (changes.length ? '<p>本次参数自动调整：' + changes.map(function (change) { return e(paramNames[change.field] || change.field) + ' → ' + e(change.effective); }).join('、') + '</p>' : '') +
      (report.effectiveParameters ? '<details><summary>查看本次有效参数</summary><dl>' + Object.keys(report.effectiveParameters).map(function (key) { return '<dt>' + e(paramNames[key] || key) + '</dt><dd>' + e(report.effectiveParameters[key]) + '</dd>'; }).join('') + '</dl></details>' : '') +
      '<p class="form-help">已检查：' + (report.checkedStages || []).map(function (stage) { return e(names[stage] || stage); }).join('、') + '</p>' +
      (issues.some(function (issue) { return issue.action === 'manage_models'; }) ? button('showLocal', '', '管理本地模型') : '') +
      (issues.some(function (issue) { return issue.action === 'manage_inputs'; }) ? button('preflightInputs', '', '管理本地素材') : '') +
      (issues.some(function (issue) { return issue.action === 'manage_tasks'; }) ? button('preflightHistory', '', '管理任务与结果') : '');
    panel.scrollIntoView({block:'start'});
  }
  function restoreForm(request, b) {
    var form = $('localTaskForm'), warnings = [], schema = schemaFor(b).fields || {}, input = request.input || {};
    if (Array.from(form.elements.taskType.options).some(function (o) { return o.value === request.type; })) form.elements.taskType.value = request.type;
    else warnings.push('原任务类型已不在当前配方内，请重新选择生成能力。');
    var fixed = ((b.inputSchemas || {})[form.elements.taskType.value] || {}).fixedPrompt;
    if (fixed && input.prompt !== fixed) warnings.push('\u5f53\u524d\u914d\u65b9\u4f7f\u7528\u56fa\u5b9a\u63d0\u793a\u8bcd\uff0c\u5df2\u663e\u793a\u5bf9\u5e94\u9ed8\u8ba4\u5185\u5bb9\u3002');
    form.elements.prompt.value = input.prompt || '';
    if (form.elements.negativePrompt) form.elements.negativePrompt.value = input.negativePrompt || '';
    else if (input.negativePrompt) warnings.push('当前配方不接受原负面提示词。');
    Object.keys(request.parameters || {}).forEach(function (key) {
      var field = schema[key], node = Array.from(form.querySelectorAll('[data-bundle-field]')).find(function (n) { return n.dataset.bundleField === key; }), value = request.parameters[key];
      if (!field || !node) { warnings.push('当前配方不再接受参数：' + (paramNames[key] || key)); return; }
      if (field.type === 'boolean') node.checked = !!value;
      else if (field.type === 'enum') { var index = field.values.indexOf(value); if (index < 0) warnings.push('参数选项已改变：' + (paramNames[key] || key)); else node.value = index; }
      else node.value = value;
    });
    (request.adapters || []).forEach(function (a) {
      var node = Array.from(form.querySelectorAll('[data-adapter-select]')).find(function (n) { return n.dataset.adapterSelect === a.bundleId; });
      if (!node) { warnings.push('LoRA 不可用或已不兼容：' + a.bundleId); return; }
      node.checked = true; var scale = node.closest('.task-adapter').querySelector('[data-adapter-scale]'); scale.disabled = false; if (a.scale !== undefined) scale.value = a.scale;
    });
    renderInputFields();
    (input.artifacts || []).forEach(function (ref) {
      var select = Array.from(form.querySelectorAll('[data-input-role]')).find(function (n) { return n.dataset.inputRole === ref.role; });
      if (!select || !Array.from(select.options).some(function (o) { return o.value === ref.artifactId; })) { warnings.push('参考素材不可用或不再符合配方：' + ref.role + ' / ' + ref.artifactId); return; }
      select.value = ref.artifactId;
      var transcript = Array.from(form.querySelectorAll('[data-input-transcript]')).find(function (t) { return t.dataset.inputTranscript === ref.role; });
      if (transcript) { transcript.disabled = false; transcript.required = true; transcript.value = (input.transcripts || {})[ref.role] || ''; }
    });
    var normalized;
    try { normalized = readFields(form, b); readAdapters(form, b); }
    catch (error) { warnings.push(error.message); }
    Object.keys(request.parameters || {}).forEach(function (key) { if (normalized && schema[key] && normalized[key] !== request.parameters[key]) warnings.push('参数已按当前约束调整：' + (paramNames[key] || key)); });
    renderSamplingHint(); form.elements.allowUnmeasured.checked = false;
    var note = document.createElement('div'); note.className = 'restore-notice';
    note.innerHTML = '<p>已恢复原输入及本次参数。模型设置保持独立；提交时重新检查文件和资源。</p>' + (warnings.length ? '<ul>' + warnings.map(function (w) { return '<li>' + e(w) + '</li>'; }).join('') + '</ul><label class="unmeasured-choice"><input type="checkbox" required name="reviewRestored"><span>我已检查未能恢复或已调整的项目，使用当前表单继续。</span></label>' : '');
    form.insertBefore(note, form.firstChild);
  }
  function use(id, selectedAdapter, restored, revision) {
    var b = find(id); if (!b || !b.installed) { ui.toast('请先选择并完整安装模型；草稿与任务记录仍然保留'); if (b) info(id); return; }
    if (!engineAvailable(b)) { ui.toast('当前基座缺少匹配引擎'); return; }
    if (isAdapter(b)) { pair(id); return; }
    var types = [];
    tasks(b).forEach(function (t) { if (t === 'image') types.push(['image.generate', '生图']); if (t === 'video') types.push(['video.generate', '生视频']); if (t === 'text') types.push(['text.generate', '生文']); if (t === 'audio') types.push([(b.manifest.capabilities || []).indexOf('text_to_speech') >= 0 ? 'speech.synthesize' : 'audio.generate', '生音频']); });
    var speechOnly = types.length === 1 && types[0][0] === 'speech.synthesize', textOnly = types.length === 1 && types[0][0] === 'text.generate';
    var noNegative = tasks(b).length === 1 && tasks(b)[0] === 'audio' && (b.manifest.capabilities || []).indexOf('negative_prompt') < 0;
    editor = {id: id, mode: 'task', draftRevision: revision === undefined ? ((window.LMAWorkbench.draft(id) || {}).revision || 0) : revision};
    ui.openModal(b.manifest.name, '<form id="localTaskForm"><label class="form-field"><span>生成能力</span><select name="taskType">' + types.map(function (t) { return '<option value="' + t[0] + '">' + t[1] + '</option>'; }).join('') + '</select></label><label class="form-field"><span>' + (speechOnly ? '朗读文本' : '提示词 / 文本') + '</span><textarea name="prompt" rows="4" required maxlength="' + (speechOnly ? '4000' : '16000') + '" placeholder="' + (speechOnly ? '填写所选语言词表覆盖的朗读文本' : '描述你希望生成的内容') + '"></textarea></label>' + (speechOnly ? '<p class="form-help">请使用此配方声明的语言与输入。缺失组件或不支持的能力会在本机报错，不会下载或转出执行。</p>' : textOnly || noNegative ? '' : '<label class="form-field"><span>负面提示词（可选）</span><textarea name="negativePrompt" rows="2" maxlength="16000"></textarea></label>') + (tasks(b).indexOf('image') >= 0 ? adapterFields(b, selectedAdapter) : '') + '<div id="taskInputs"></div><p id="samplingHint" class="form-help" hidden></p><details class="task-parameters"><summary>本次参数</summary>' + fields(b) + '</details><label class="unmeasured-choice"><input type="checkbox" name="allowUnmeasured" required><span>此配方尚无本机实测记录，我选择在当前手机上尝试。</span></label><p class="form-help">一次执行一个大型引擎。任务等待当前回复结束后自动切换，队列空闲时恢复此前加载的文本模型。任务在后台通知中执行，结果保存在本机；缺少组件不会自动下载。</p><section id="taskPreflight" class="task-preflight" role="status" aria-live="polite"></section><p id="bundleFormHint" role="status"></p><div class="modal-actions">' + button('preflightTask', id, '运行前检查') + button('closeModal', '', '取消') + button('saveTaskDraft', id, '保存草稿') + '<button type="submit" class="button primary">加入本机队列</button></div></form>', 'localTask');
    renderInputFields(); renderSamplingHint();
    if (restored) restoreForm(restored, b);
  }
  function renderJobs() {
    var s = ui.state(), all = s.jobs || [], jobs = all.filter(function (job) { var active = ['queued','loading','running','cancelling'].indexOf(job.state) >= 0, b = find(job.request.bundleId); return (jobKind === 'all' || jobKind === 'active' && active || jobKind === 'succeeded' && job.state === 'succeeded' || jobKind === 'issues' && ['failed','cancelled','interrupted'].indexOf(job.state) >= 0) && (!jobSearch || [job.id,b && b.manifest.name,job.request.bundleId,job.request.inputSummary,job.request.input && job.request.input.prompt].join(' ').toLowerCase().indexOf(jobSearch.toLowerCase()) >= 0); }).slice().reverse();
    var signature = JSON.stringify([all, s.audioStreams || [], jobKind, jobSearch, jobLimit, (s.artifacts || []).map(function (a) { return [a.id, a.available]; })]);
    if (signature === listSignature) return; listSignature = signature;
    $('jobCount').textContent = all.filter(function (j) { return ['queued', 'loading', 'running', 'cancelling'].indexOf(j.state) >= 0; }).length + ' 个待完成 · ' + jobs.length + ' 条匹配';
    document.querySelectorAll('[data-action="filterJobs"]').forEach(function (b) { var active = b.dataset.kind === jobKind; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active)); });
    $('jobList').innerHTML = jobs.length ? jobs.slice(0, jobLimit).map(function (job) {
      var b = find(job.request.bundleId), stream = window.LMAAudioPreview.summary(job.id), terminal = ['cancelled', 'failed', 'succeeded', 'interrupted'].indexOf(job.state) >= 0;
      var progress = typeof job.progress === 'number' ? '<progress max="1" value="' + Math.max(0, Math.min(1, job.progress)) + '" aria-label="任务进度"></progress>' : '';
      return '<article class="job-card"><div class="section-heading"><strong>' + e(b ? b.manifest.name : job.request.bundleId) + '</strong><span class="status-pill">' + e(job.stage === 'waiting_engine' && ['loading', 'running'].indexOf(job.state) >= 0 ? '排队中' : ['model.prepare', 'model.assemble'].indexOf(job.request.type) >= 0 && job.state === 'running' ? job.request.type === 'model.prepare' ? '准备中' : '关联中' : states[job.state] || job.state) + '</span></div><p class="job-prompt">' + e(job.request.type === 'model.prepare' ? '模型运行资产准备' : job.request.type === 'model.assemble' ? '模型运行资产关联' : job.request.inputSummary || job.request.input && job.request.input.prompt || '') + '</p><p class="form-help">' + e(job.stage && job.stage.indexOf('preparing_') === 0 ? '准备运行组件' : job.stage === 'verifying_prepared_assets' ? '校验准备资产' : stages[job.stage] || job.stage || '') + ' · ' + new Date(job.createdAt).toLocaleString('zh-CN') + '</p>' + progress + (job.outputRecovery ? '<p class="recovered-output">中断后找回已保存结果；任务未自动重跑。</p>' : '') + (job.error ? '<p class="download-error">' + e(job.error) + '</p>' : '') + '<div class="job-actions">' + button('jobInfo', job.id, '详情') + (stream ? button('audioPreview', job.id, stream.state === 'streaming' ? '边生成边听' : '试听缓存', 'secondary', stream.frames === 0) : '') + ((job.artifacts || []).length ? button('jobResults', job.id, '查看结果', 'primary') : '') + (window.LMAWorkbench.generation(job.request.type) && terminal ? button('editTask', job.id, '编辑再生成') : '') + (!terminal ? button('cancelTask', job.id, '取消任务', 'danger', job.state === 'cancelling') : ['failed', 'interrupted', 'cancelled'].indexOf(job.state) >= 0 ? button('retryTask', job.id, '重试') : '') + (terminal ? button('deleteTask', job.id, '删除记录') : '') + '</div></article>';
    }).join('') + (jobs.length > jobLimit ? button('moreJobs', '', '显示更多任务（还有 ' + (jobs.length - jobLimit) + ' 条）') : '') : all.length ? '<div class="empty-list"><h3>没有匹配的任务</h3>' + button('resetJobFilters', '', '重置筛选与搜索') + '</div>' : '<div class="empty-list"><h3>队列里还没有任务</h3><p>在本地模型中选择已安装的模型，填写提示词后加入队列。</p>' + button('showLocal', '', '选择本地模型', 'primary') + '</div>';
  }
  function renderArtifacts() {
    var all = ui.state().artifacts || [], artifacts = all.filter(function (a) { return artifactKind === 'all' || ((a.origin || {}).kind || 'generated') === artifactKind; }), imports = ui.state().inputImport || {}, signature = JSON.stringify([artifacts, artifactKind, imports]);
    if (signature === artifactSignature) return; artifactSignature = signature;
    $('artifactCount').textContent = artifacts.length + ' 项';
    $('inputImportStatus').innerHTML = imports.busy ? '<p class="form-help">正在导入 ' + e(imports.name || '所选素材') + ' · ' + Number(imports.pending || 1) + ' 项' + button('cancelInputImport', '', '取消导入') + '</p>' : '';
    document.querySelectorAll('[data-action="filterArtifacts"]').forEach(function (b) { var active = b.dataset.kind === artifactKind; b.classList.toggle('active', active); b.setAttribute('aria-pressed', String(active)); });
    refreshTaskInputs();
    $('artifactList').innerHTML = artifacts.length ? artifacts.slice().reverse().map(function (a) {
      var origin = a.origin || {}, imported = origin.kind === 'imported', m = a.metadata || {}, type = m.mime === 'application/vnd.lma.text+json' ? 'text' : (m.mime || '').split('/')[0];
      var cover = a.available && type === 'image' ? '<img class="artifact-thumb" src="/artifacts/' + e(a.id) + '" loading="lazy" alt="本地图片素材或结果">' : '<div class="artifact-placeholder">' + ui.icon(type === 'audio' ? 'play' : 'spark') + '<span>' + e(type === 'video' ? '视频' : type === 'audio' ? '音频' : type === 'text' ? '文本' : '生成结果') + '</span></div>';
      return '<article class="artifact-card">' + cover + '<div class="artifact-info"><strong>' + e(imported ? origin.name || '导入素材' : new Date(a.createdAt).toLocaleString('zh-CN')) + '</strong><p class="artifact-source">' + (imported ? '导入素材' : '生成结果') + (a.inUse ? ' · 任务正在引用' : '') + '</p><p>' + e(m.mime || '') + ' · ' + ui.bytes(a.bytes) + (m.width ? ' · ' + m.width + ' × ' + m.height : '') + '</p><div class="job-actions">' + button('artifactInfo', a.id, '打开', 'primary', !a.available) + button('exportArtifact', a.id, '导出', 'secondary', !a.available) + button('artifactInput', a.id, '用作素材', 'secondary', !a.available) + button('artifactRemove', a.id, '删除', 'secondary', a.inUse) + '</div></div></article>';
    }).join('') : '<div class="empty-list"><h3>这里还没有素材或结果</h3><p>导入本地素材，或选择模型生成结果。可预览、导出并查看文件来源。</p></div>';
  }
  function track(action, args, callback, failure) { var id = ui.dispatch(action, args); if (id) pending[id] = {success: callback || function () {}, failure: failure}; return id; }
  function showArtifact(id, data) {
    var a = data, mime = a.metadata.mime, path = '/artifacts/' + encodeURIComponent(id), text = mime === 'application/vnd.lma.text+json', media = mime.indexOf('image/') === 0 ? '<img src="' + path + '" alt="本地生成图片" class="artifact-preview">' : mime.indexOf('audio/') === 0 ? '<audio controls preload="metadata" src="' + path + '"></audio>' : mime.indexOf('video/') === 0 ? '<video controls playsinline preload="metadata" src="' + path + '"></video>' : '';
    if (text) media = '<div id="textArtifact" data-id="' + e(id) + '"><p role="status">正在读取本地文本结果…</p></div>';
    ui.openModal((a.origin || {}).kind === 'imported' ? '本地导入素材' : '本地生成结果', media + '<p>' + e(mime) + ' · ' + ui.bytes(a.bytes) + '</p><details><summary>文件来源与任务记录</summary><pre class="provenance">' + e(JSON.stringify({origin: a.origin || {kind: 'generated'}, provenance: a.provenance}, null, 2)) + '</pre></details><p class="form-help artifact-sha">SHA256：' + e(a.sha256) + '</p><div class="modal-actions">' + (text ? button('copyArtifactText', id, '复制正文') : '') + ((a.provenance || {}).request ? button('editArtifact', id, '恢复生成参数') : '') + (text ? '' : button('artifactInput', id, '用作下一次素材', 'secondary', !a.available)) + button('exportArtifactMetadata', id, '导出来源记录') + button('exportArtifact', id, '导出原文件', 'primary') + '</div>', 'artifact');
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
    if (window.LMAWorkbench.handle(action, el)) return true;
    if (window.LMAVersions.handle(action, el)) { editor = null; return true; }
    switch (action) {
      case 'filterJobs': jobKind = ['all','active','succeeded','issues'].indexOf(el.dataset.kind) >= 0 ? el.dataset.kind : 'all'; jobLimit = 20; renderJobs(); return true;
      case 'moreJobs': jobLimit += 20; renderJobs(); return true;
      case 'resetJobFilters': jobKind = 'all'; jobSearch = ''; jobLimit = 20; $('jobSearch').value = ''; renderJobs(); return true;
      case 'preflightHistory': ui.route('tasks'); $('taskCapacity').scrollIntoView({block:'start'}); return true;
      case 'preflightInputs': ui.route('tasks'); artifactKind = 'all'; renderArtifacts(); document.querySelector('.artifacts-heading').scrollIntoView({block:'start'}); return true;
      case 'preflightTask': {
        var form = $('localTaskForm'), b = editor && find(editor.id); if (!form || !b || editor.pending) return true;
        try {
          var request = taskRequest(form, b, true), editing = editor, revision = form.dataset.checkRevision || '0';
          request.allowUnmeasured = form.elements.allowUnmeasured.checked;
          el.disabled = true; $('taskPreflight').textContent = '正在检查本地模型与输入…';
          editor.pending = track('preflightTask', {request: request}, function (report) {
            if (editor !== editing) return; editor.pending = false; el.disabled = false;
            if ((form.dataset.checkRevision || '0') !== revision) { $('taskPreflight').textContent = '检查期间输入已改变，请重新检查。'; return; }
            showPreflight(report);
          });
        } catch (error) { el.disabled = false; $('bundleFormHint').textContent = error.message; }
        return true;
      }
      case 'saveTaskDraft': {
        var form = $('localTaskForm'), b = editor && find(editor.id); if (!form || !b || editor.pending) return true;
        try {
          var request = taskRequest(form, b, true), editing = editor; el.disabled = true;
          editor.pending = track('saveTaskDraft', {request: request, expectedRevision: editor.draftRevision}, function (record) {
            if (editor === editing) { editor.pending = false; editor.draftRevision = record.revision; el.disabled = false; $('bundleFormHint').textContent = '草稿已保存在本机；未创建任务，也未更改模型设置'; }
            ui.toast('草稿已保存');
          });
        } catch (error) { el.disabled = false; $('bundleFormHint').textContent = error.message; }
        return true;
      }
      case 'inputPicker': ui.dispatch(action); return true;
      case 'cancelInputImport': track(action); return true;
      case 'filterArtifacts': artifactKind = ['all', 'generated', 'imported'].indexOf(el.dataset.kind) >= 0 ? el.dataset.kind : 'all'; renderArtifacts(); return true;
      case 'bundleInfo': info(id); return true;
      case 'bundleDependencyInfo': info(id, el.dataset.adapter); return true;
      case 'assemblyInfo': assemblyInfo(id, el.dataset.assembly); return true;
      case 'assembleAssets':
        track('submitTask', {request: {type: 'model.assemble', bundleId: el.dataset.bundle, preparedAssetsId: id, assemblyId: el.dataset.assembly, assemblyFingerprint: el.dataset.fingerprint}}, function () { ui.closeModal(); ui.route('tasks'); ui.toast('运行模型关联已加入本机队列'); }); return true;
      case 'preparationInfo': preparationInfo(id, el.dataset.preparation); return true;
      case 'prepareAssets':
        track('submitTask', {request: {type: 'model.prepare', bundleId: id, preparationId: el.dataset.preparation, planFingerprint: el.dataset.fingerprint}}, function () { ui.closeModal(); ui.route('tasks'); ui.toast('运行资产准备已加入本机队列'); }); return true;
      case 'preparedRemove': ui.confirm('删除准备资产？', '只删除这次准备的运行文件；下载或导入的源模型和独立设置保留。', 'deletePreparedAssets', id, '删除准备资产'); return true;
      case 'deletePreparedAssets': track(action, {id: id}); return true;
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
      case 'jobInfo': track('inspectTask', {id: id}, window.LMAWorkbench.showJob); return true;
      default: return false;
    }
  }
  window.LMAFoundation = {
    init: function (bridge) {
      ui = bridge; window.LMAVersions.init(bridge);
      window.LMAWorkbench.init(bridge, {find: find, button: button, use: use, track: track, showArtifact: showArtifact, inputRuleMatch: inputRuleMatch, engineAvailable: engineAvailable, paramNames: paramNames, states: states});
      document.addEventListener('input', function (event) { preflightChanged(event.target.form); if (event.target.id === 'jobSearch') { jobSearch = event.target.value.slice(0,120); jobLimit = 20; renderJobs(); } });
      document.addEventListener('submit', function (event) {
        if (event.target.id === 'adapterPairForm') { event.preventDefault(); var adapter = editor && find(editor.id), base = find(event.target.elements.baseBundleId.value); if (adapter && base && base.installed && compatible(base, adapter)) use(base.id, adapter.id); return; }
        if (event.target.id !== 'bundleSettingsForm' && event.target.id !== 'localTaskForm') return;
        event.preventDefault(); if (!editor || editor.pending) return;
        var form = event.target, b = find(editor.id); if (!b) return;
        try {
          if (!form.reportValidity()) return;
          var parameters = readFields(form, b), submit = form.querySelector('[type="submit"]');
          var args = editor.mode === 'settings' ? {id: b.id, settings: parameters} : {request: taskRequest(form, b, false), idempotencyKey: 'ui-' + Date.now() + '-' + Math.random().toString(36).slice(2)};
          var editing = editor;
          editor.pending = track(editor.mode === 'settings' ? 'saveBundleSettings' : 'submitTask', args, function () { if (editor === editing) { ui.closeModal(); if (editing.mode === 'task') ui.route('tasks'); } ui.toast(editing.mode === 'task' ? '任务已加入本机队列' : '已保存此模型的独立设置'); });
          if (editor.pending) { submit.disabled = true; $('bundleFormHint').textContent = '正在提交…'; }
        } catch (error) { $('bundleFormHint').textContent = error.message; }
      });
      document.addEventListener('change', function (event) {
        preflightChanged(event.target.form);
        if (event.target.dataset.inputRole) { var panel = $('taskInputs'), text = panel && Array.from(panel.querySelectorAll('[data-input-transcript]')).find(function (t) { return t.dataset.inputTranscript === event.target.dataset.inputRole; }); if (text) { text.disabled = !event.target.value; text.required = !!event.target.value; } return; }
        if (event.target.dataset.adapterSelect) {
          var row = event.target.closest('.task-adapter'), scale = row.querySelector('[data-adapter-scale]'); scale.disabled = !event.target.checked; renderSamplingHint(); return;
        }
        if (event.target.dataset.bundleField === 'steps' && $('localTaskForm') && $('localTaskForm').dataset.samplingProfile) { renderSamplingHint(); return; }
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
      renderJobs(); renderArtifacts(); refreshTaskInputs(); window.LMAWorkbench.render(); window.LMAVersions.receive();
      Object.keys(pending).forEach(function (id) {
        var result = ui.result(id); if (!result) return; var callback = pending[id]; delete pending[id];
        if (result.ok) callback.success(result.data);
        else if (callback.failure) { callback.failure(result.error); ui.toast(result.error || '操作失败'); }
        else { if (editor) { editor.pending = false; var submit = $('modalContent').querySelector('[type="submit"]'); if (submit) submit.disabled = false; var save = $('modalContent').querySelector('[data-action="saveTaskDraft"]'); if (save) save.disabled = false; var check = $('modalContent').querySelector('[data-action="preflightTask"]'); if (check) check.disabled = false; } if ($('bundleFormHint')) $('bundleFormHint').textContent = result.error; ui.toast(result.error || '操作失败'); }
      });
    },
    close: function () { editor = null; window.LMAVersions.close(); window.LMAAudioPreview.close(); $('modalContent').querySelectorAll('audio,video').forEach(function (media) { media.pause(); media.removeAttribute('src'); media.load(); }); }
  };
})();
