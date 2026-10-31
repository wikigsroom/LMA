(function () {
  'use strict';
  var ui, pending = {}, editor = null;
  function e(v) { return ui.esc(v); }
  function call(action, values, done, failed) { var id = ui.dispatch(action, values); if (id) pending[id] = {done:done || function () {},failed:failed}; return id; }
  function find(id) { return (ui.state().bundles || []).find(function (b) { return b.id === id; }); }
  function message(text) { var el = document.getElementById('meshHint'); if (el) el.textContent = text; else ui.toast(text); }
  function button(action, label, primary) { return '<button type="button" class="button ' + (primary ? 'primary' : 'secondary') + '" data-action="' + action + '">' + label + '</button>'; }
  function choices(selected,mimes) {
    mimes = mimes || ['image/png','image/jpeg'];
    return '<option value="">选择已导入的图片</option>' + (ui.state().artifacts || []).filter(function (a) { return a.available && a.metadata && mimes.indexOf(a.metadata.mime) >= 0; }).map(function (a) {
      return '<option value="' + e(a.id) + '"' + (a.id === selected ? ' selected' : '') + '>' + e((a.origin || {}).name || a.id) + '</option>';
    }).join('');
  }
  function field(key, rule, value) {
    var id = 'mesh-' + key, input;
    if (rule.type === 'boolean') input = '<input type="checkbox" name="' + key + '"' + (value ? ' checked' : '') + '>';
    else if (rule.type === 'string') input = '<textarea name="' + key + '" maxlength="' + (rule.maxLength || 16000) + '" rows="4">' + e(value || '') + '</textarea>';
    else input = '<input name="' + key + '" type="number" inputmode="decimal" list="' + id + '" step="' + (rule.type === 'integer' ? '1' : 'any') + '" min="' + rule.minimum + '" max="' + rule.maximum + '" value="' + e(value) + '" required><datalist id="' + id + '">' + (rule.presets || [rule.default]).map(function (v) { return '<option value="' + v + '"></option>'; }).join('') + '</datalist>';
    return '<label class="form-field' + (rule.type === 'string' ? ' mesh-wide' : '') + '"><span>' + e(rule.label || key) + '</span>' + input + '</label>';
  }
  function use(id, request, revision) {
    var b = find(id); if (!b || ['trellis_native','pixal_multiview','rf_shape_ort'].indexOf(b.manifest.engine) < 0) return false;
    var values = Object.assign({}, (b.config || {}).values || {}, (request || {}).parameters || {}), fields = b.parameterSchema.fields;
    var inputSchema = (b.inputSchemas || {})['mesh.generate'] || {fixedPrompt:'Generate a 3D asset from the selected local image.',roles:{reference_image:{label:'参考图片（PNG / JPEG，最多 4 百万像素）',mimes:['image/png','image/jpeg'],required:true}}};
    var selected = (((request || {}).input || {}).artifacts || []), roles = Object.keys(inputSchema.roles || {});
    var multi = b.manifest.pipeline === 'pixal3d_mv';
    var html = '<form id="meshTaskForm"><div class="model-tags"><span class="tag">生 3D</span><span class="tag">本机 CPU</span><span class="tag">实验配方</span></div><h3>' + e(b.manifest.name) + '</h3><p>' + (multi ? '按正面、右侧、背面、左侧选择同一物体的四张已去背景 RGBA PNG。视图必须符合相机标定；单图权重不能代替 MV 权重。' : '选择一张本地图片，生成可导出的 GLB 网格。建议使用主体清晰、透明背景的物体图。') + '</p>' + roles.map(function (role) {
      var rule = inputSchema.roles[role], receipt = selected.find(function (v) { return v.role === role; });
      return '<label class="form-field"><span>' + e(rule.label || role) + '</span><select name="' + (role === 'reference_image' ? 'reference' : role) + '" data-mesh-role="' + e(role) + '"' + (rule.required ? ' required' : '') + '>' + choices(receipt && receipt.artifactId,rule.mimes) + '</select></label>';
    }).join('') + '<div class="modal-actions">' + button('meshImport','从设备导入图片') + button('meshRefresh','刷新图片列表') + '</div><div class="form-grid">' + Object.keys(fields).map(function (key) { return field(key,fields[key],values[key] === undefined ? fields[key].default : values[key]); }).join('') + '</div><p class="form-help">' + e(inputSchema.promptHelp || (multi ? '标准转台：20° 水平视角、零仰角、距离 3.119204998。相机参数留空采用此约定，其他拍摄方式需要提供正确的四个相机变换；不是自动相机估计。' : '512 / 1024 是生成阶段分辨率。Pixal3D 的 512 模式只支持几何；贴图需选择 1024 并配齐对应组件。')) + ' 权重大小不代表运行内存。</p><label class="unmeasured-choice"><input type="checkbox" name="allowUnmeasured"><span>允许尝试尚无本机实测记录的配方</span></label><p id="meshHint" role="status">可先检查组件、图片、参数与当前资源。此检查不会运行模型。</p><div class="modal-actions">' + button('meshSaveSettings','保存为此模型的设置') + button('meshDraft','保存草稿') + button('meshPreflight','运行前检查') + button('meshSubmit','加入任务队列',true) + '</div></form>';
    ui.openModal('本地生 3D',html,'mesh');
    editor = {id:id,inputSchema:inputSchema,revision:revision === undefined ? (((ui.state().taskDrafts || []).find(function (d) { return d.bundleId === id; }) || {}).revision || 0) : revision};
    var form = document.getElementById('meshTaskForm');
    form.addEventListener('submit',function (ev) { ev.preventDefault(); });
    form.addEventListener('change',function () { normalize(form,b); });
    normalize(form,b); return true;
  }
  function normalize(form,b) {
    var adjusted = [], fields = b.parameterSchema.fields;
    Object.keys(fields).forEach(function (key) {
      var f = fields[key], el = form.elements[key]; if (!el || f.type === 'boolean' || f.type === 'string' || !Number.isFinite(Number(el.value)) || el.value.trim() === '') return;
      var value = Math.max(f.minimum,Math.min(f.maximum,Number(el.value)));
      if (f.type === 'integer') value = Math.floor(value);
      if (f.multipleOf) value = Math.max(f.minimum,Math.floor(value / f.multipleOf) * f.multipleOf);
      if (String(value) !== el.value) adjusted.push(f.label || key); el.value = value;
    });
    if (b.manifest.pipeline === 'pixal3d' && Number(form.elements.resolution.value) === 512 && form.elements.texture.checked) { form.elements.texture.checked = false; adjusted.push('512 模式关闭贴图'); }
    if (adjusted.length) message('已按当前配方约束归位：' + adjusted.join('、'));
  }
  function request(requireInput) {
    var form = document.getElementById('meshTaskForm'), b = editor && find(editor.id);
    if (!form || !b) throw new Error('请重新打开此模型');
    normalize(form,b); var values = {};
    Object.keys(b.parameterSchema.fields).forEach(function (key) { var f = b.parameterSchema.fields[key], el = form.elements[key]; if (f.type !== 'boolean' && f.type !== 'string' && (el.value.trim() === '' || !Number.isFinite(Number(el.value)))) throw new Error('请填写有效的模型参数'); values[key] = f.type === 'boolean' ? el.checked : f.type === 'string' ? el.value : Number(el.value); });
    var artifacts = [];
    form.querySelectorAll('[data-mesh-role]').forEach(function (select) {
      var role = select.dataset.meshRole, rule = editor.inputSchema.roles[role];
      if (requireInput && rule.required && !select.value) throw new Error('请先选择：' + rule.label);
      if (select.value) artifacts.push({role:role,artifactId:select.value});
    });
    return {bundleId:b.id,type:'mesh.generate',input:{prompt:editor.inputSchema.fixedPrompt,artifacts:artifacts.length ? artifacts : undefined},parameters:values,allowUnmeasured:form.elements.allowUnmeasured.checked};
  }

  function showArtifact(id,data) {
    if (!data.metadata || data.metadata.mime !== 'model/gltf-binary') return false;
    var m = data.metadata;
    ui.openModal('3D 结果 · GLB','<p>' + e(m.vertices) + ' 个顶点 · ' + e(m.triangles) + ' 个三角面 · ' + e(m.textures) + ' 份嵌入贴图</p><canvas id="glbPreview" class="glb-preview" width="640" height="480" aria-label="拖动旋转三维网格预览"></canvas><p id="glbPreviewStatus" role="status">正在读取本地几何…</p><p class="form-help">拖动旋转，滚轮或双指缩放。预览显示几何光照；完整 PBR 材质保存在 GLB 中，可导出至 3D 编辑器查看。</p><div class="modal-actions"><button class="button primary" data-action="exportArtifact" data-id="' + e(id) + '">导出 GLB</button><button class="button secondary" data-action="exportArtifactMetadata" data-id="' + e(id) + '">导出生成记录</button><button class="button secondary" data-action="editArtifact" data-id="' + e(id) + '">编辑后再次生成</button></div><details><summary>来源与参数</summary><pre class="provenance">' + e(JSON.stringify(data.provenance || {},null,2)) + '</pre></details>','meshArtifact');
    window.LMAGlbPreview.open(document.getElementById('glbPreview'),document.getElementById('glbPreviewStatus'),'/artifacts/' + encodeURIComponent(id),data.bytes); return true;
  }
  window.LMAExpansion = {
    init:function (bridge) { ui = bridge; }, use:use, showArtifact:showArtifact,
    close:function () { editor = null; window.LMAGlbPreview.close(); },
    receive:function () { Object.keys(pending).forEach(function (id) { var result = ui.result(id); if (!result) return; var callback = pending[id]; delete pending[id]; if (result.ok) callback.done(result.data); else { if (callback.failed) callback.failed(result.error); message(result.error); } }); },
    handle:function (action,el) {
      if (action === 'expansionNotices') { fetch('expansion-notices.json').then(function (r) { if (!r.ok) throw new Error('无法读取说明'); return r.json(); }).then(function (v) { ui.openModal('新增原生引擎开源说明',Object.keys(v).map(function (name) { return '<details><summary>' + e(name) + '</summary><pre class="provenance">' + e(v[name]) + '</pre></details>'; }).join(''),'notices'); }).catch(function (err) { ui.toast(err.message); }); return true; }
      if (action === 'bundleUse' && use(el.dataset.id)) return true;
      if (action.indexOf('mesh') !== 0) return false;
      try {
        if (action === 'meshImport') { call('inputPicker',{}); return true; }
        var form = document.getElementById('meshTaskForm');
        if (action === 'meshRefresh') { form.querySelectorAll('[data-mesh-role]').forEach(function (select) { var selected = select.value; select.innerHTML = choices(selected,editor.inputSchema.roles[select.dataset.meshRole].mimes); }); return true; }
        var value = request(action === 'meshPreflight' || action === 'meshSubmit'), current = editor;
        if (action === 'meshSaveSettings') call('saveBundleSettings',{id:current.id,settings:value.parameters},function () { message('此模型的设置已保存；其他模型的参数独立保留'); });
        if (action === 'meshDraft') call('saveTaskDraft',{request:value,expectedRevision:current.revision},function (saved) { if (editor === current) editor.revision = saved.revision; message('3D 草稿已保存'); });
        if (action === 'meshPreflight') call('preflightTask',{request:value},function (report) { message((report.canEnqueue ? '检查通过，可加入队列。' : '当前无法加入队列。') + (report.issues || []).concat(report.warnings || []).map(function (i) { return i.message; }).join(' ')); });
        if (action === 'meshSubmit') {
          if (current.submitting) return true;
          if (!value.allowUnmeasured) throw new Error('请明确选择是否允许尝试此未测配方');
          current.submitting = true; el.disabled = true;
          var key = 'mesh_' + Date.now() + '_' + Math.random().toString(16).slice(2);
          call('submitTask',{request:value,idempotencyKey:key},function () {
            if (editor === current) { ui.closeModal(); ui.route('tasks'); } ui.toast('3D 任务已加入本机队列');
          },function () { current.submitting = false; if (editor === current) el.disabled = false; });
        }
      } catch (err) { message(err.message); }
      return true;
    }
  };
}());
