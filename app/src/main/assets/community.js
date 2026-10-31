(function () {
  'use strict';
  var ui;
  var labels = {publisher_card: '来源声明', publisher_filename: '文件标记', publisher_rating: '分级词表', mirror_card: '镜像声明', hf_nsfw_tag: 'HF 标签', repository_hint: '名称提示', hf_sensitive_tag: 'HF 标签', none: '未标注'};
  function e(v) { return ui.esc(v); }
  function metadata(m) { return m.content || {classification: 'unclassified', basis: 'none'}; }
  function bind(m, state) {
    if (!m.isBundle) return m;
    var b = (state.bundles || []).find(function (b) { return b.id === (m.bundleId || m.id); });
    if (b) { m.manifest = b.manifest; m.taskTags = b.manifest.tasks; m.content = b.manifest.content; m.community = b.manifest.community; }
    return m;
  }
  function badge(m) {
    var c = metadata(m), label = c.classification === 'nsfw' ? 'NSFW · ' + (labels[c.basis] || '配方声明') : c.classification === 'sensitive' ? '敏感 · HF 标签' : '内容未标注';
    return '<span class="tag content-' + (c.classification === 'nsfw' ? 'nsfw' : c.classification === 'sensitive' ? 'sensitive' : 'unknown') + '" title="内容标记与运行兼容性、安装状态、效果验证相互独立">' + e(label) + '</span>';
  }
  function card(html, m) {
    var fragment = document.createElement('template'); fragment.innerHTML = html;
    var root = fragment.content.firstElementChild;
    if (!root) return html;
    var tags = root.querySelector('.model-tags');
    if (!tags) { tags = document.createElement('div'); tags.className = 'model-tags'; root.appendChild(tags); }
    if ((m.taskTags || []).indexOf('3d') >= 0) { tags.querySelectorAll('.tag').forEach(function (t) { if (t.textContent === 'undefined') t.remove(); }); tags.insertAdjacentHTML('beforeend', '<span class="tag task-tag task-3d">生 3D</span>'); }
    tags.insertAdjacentHTML('beforeend', badge(m));
    if (m.community) {
      tags.insertAdjacentHTML('beforeend', '<span class="tag">社区配方</span>');
      var action = document.createElement('button'); action.type = 'button'; action.className = 'text-button community-info';
      action.dataset.action = 'communityInfo'; action.dataset.id = m.bundleId || m.id; action.textContent = '来源、内容标记与兼容说明'; root.appendChild(action);
    }
    return fragment.innerHTML;
  }
  function accepts(m, content, source) {
    return (content === 'any' || metadata(m).classification === content) && (source === 'any' || (source === 'registered' ? !!m.isBundle : !m.isBundle));
  }
  function search(m, query) {
    var q = query.trim().toLowerCase();
    if (q === 'nsfw') return metadata(m).classification === 'nsfw';
    return !q || [m.name, m.family, m.repository, m.description, (m.community || {}).family, (m.community || {}).variant].join(' ').toLowerCase().indexOf(q) >= 0;
  }
  function info(m) {
    var manifest = m.manifest || {}, c = metadata(m), community = m.community || {}, evidence = manifest.evidence || {}, components = manifest.components || [];
    var html = '<div class="community-detail"><div class="model-tags">' + badge(m) + '<span class="tag">' + e(manifest.architecture || '架构待核对') + '</span></div>';
    html += '<p>' + e(c.summary || '来源没有明确内容声明。') + '</p><dl class="task-value-list"><dt>模型系列</dt><dd>' + e(community.family || m.name) + '</dd><dt>发布来源</dt><dd>' + e(community.sourceRole === 'mirror' ? '社区镜像；原作者身份与许可单独注明' : '发布者 HF 仓库') + '</dd><dt>仓库</dt><dd>' + e(community.repository || m.repository) + '</dd><dt>固定版本</dt><dd class="community-revision">' + e(c.sourceRevision || '未固定') + '</dd><dt>许可</dt><dd>' + e((manifest.license || {}).name || '请核对模型卡') + '</dd><dt>标记依据</dt><dd>' + e(labels[c.basis] || '配方声明') + ' · ' + e(c.checkedAt || '仓库元数据') + '</dd></dl>';
    html += '<h3>本机接入</h3><p>' + e(evidence.compatibilityNote || '按所选引擎检查配套组件。') + '</p><p class="form-help">已接入现有程序路线并核对文件头；未运行完整权重，未做手机推理、效果或后台耐久测试。文件体积不等于运行内存。</p>';
    if (community.family === 'NSFW Wan 1.3B') html += '<p class="form-help">EXP E01–E14 是同一系列的 14 个训练版本。作者建议 E14；目录保留版本选择。Wan 14B、I2V、Wan 2.2、视频 LoRA 与 LTX 2.x 不能套用此配方。</p>';
    html += '<details><summary>所需文件 · ' + components.length + ' 项</summary><dl class="task-value-list">' + components.map(function (v) { return '<dt>' + e(v.role) + '</dt><dd>' + e(v.path) + ' · ' + ui.bytes(v.bytes) + '</dd>'; }).join('') + '</dl></details><p class="form-help">仅在你确认后下载所选模型及列出的依赖；同一文件按哈希复用，切换版本仍需单独选择。内容标记不改变推荐、生成接口或模型独立参数。</p><div class="modal-actions">';
    if (c.sourceUrl) html += '<button class="button secondary" data-action="communitySource" data-url="' + e(c.sourceUrl) + '">核对来源 ↗</button>';
    html += '<button class="button primary" data-action="bundleInfo" data-id="' + e(m.bundleId || m.id) + '">管理此模型</button></div></div>';
    ui.openModal(m.name, html, 'communityInfo');
  }
  function annotateModal(m) {
    var content = document.getElementById('modalContent');
    if (!m || !m.community || !content || content.querySelector('.community-modal-note')) return;
    var note = document.createElement('div'); note.className = 'community-modal-note';
    note.innerHTML = '<div class="model-tags">' + badge(m) + '</div><button type="button" class="text-button" data-action="communityInfo" data-id="' + e(m.bundleId || m.id) + '">来源、内容标记与兼容说明</button>';
    content.insertBefore(note, content.firstChild);
  }
  window.LMACommunity = {init: function (bridge) { ui = bridge; }, bind: bind, badge: badge, card: card, accepts: accepts, search: search, info: info, annotateModal: annotateModal};
}());
