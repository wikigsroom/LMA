(function () {
  'use strict';
  var ui, selected = [], availability = 'any', evidence = 'any';
  var names = {'input:text':'文字输入','input:image':'图片理解','input:video':'视频理解','input:audio':'音频理解','output:image':'生图','output:video':'生视频','output:audio':'生音频','output:3d':'生 3D','output:text':'生文','output:json':'结构化 JSON','tool:calling':'工具调用'};
  var support = {publisher_declared:'上游声明',publisher_metadata:'发布元数据',family_candidate:'家族候选',not_supported:'此变体不支持',unknown:'未知',engine_contract:'引擎输入输出合同'};
  function describe(m) {
    if (m.capabilities && !Array.isArray(m.capabilities)) return m.capabilities;
    var caps = Object.keys(names).map(function (tag) { return {tag:tag,support:'unknown',evidence:[]}; });
    if(m.inputSchemas){var ops=Object.keys(m.inputSchemas),outs={'text.generate':'output:text','image.generate':'output:image','video.generate':'output:video','speech.synthesize':'output:audio','audio.generate':'output:audio','mesh.generate':'output:3d'};ops.forEach(function(op){var schema=m.inputSchemas[op],tag=outs[op];if(tag)caps.find(function(c){return c.tag===tag;}).support='engine_contract';caps.find(function(c){return c.tag==='input:text';}).support='engine_contract';Object.keys(schema.roles||{}).forEach(function(role){(schema.roles[role].mimes||[]).forEach(function(mime){var tag=mime.indexOf('image/')===0?'input:image':mime.indexOf('video/')===0?'input:video':mime.indexOf('audio/')===0?'input:audio':'';if(tag)caps.find(function(c){return c.tag===tag;}).support='engine_contract';});});});}
    if (m.task === 'image-text-to-text') caps.find(function (c) {return c.tag === 'input:image';}).support = 'publisher_metadata';
    return {native:caps,lma:{operations:[],visionBridge:'unknown',modelToolReliability:'unknown'},evidence:{phoneOutput:false,quality:false}};
  }
  function available(m) {return m.installed || m.local || m.installedBytes > 0;}
  function matches(m) {
    var d=describe(m);
    if (!selected.every(function (tag) {return (d.native || []).some(function (c) {return c.tag === tag && ['publisher_declared','publisher_metadata','family_candidate','engine_contract'].indexOf(c.support)>=0;});})) return false;
    if (availability === 'local' && !available(m)) return false;
    if (availability === 'uninstalled' && available(m)) return false;
    if (evidence === 'declared' && !(d.native || []).some(function (c) {return c.support === 'publisher_declared' || c.support === 'publisher_metadata';})) return false;
    if (evidence === 'phone' && !(d.evidence || {}).phoneOutput) return false;
    return true;
  }
  function badges(m) {
    return (describe(m).native || []).filter(function (c) {return ['input:image','input:video','input:audio','tool:calling','output:json'].indexOf(c.tag)>=0 && ['publisher_declared','publisher_metadata','family_candidate','engine_contract'].indexOf(c.support)>=0;}).slice(0,4).map(function (c) {return '<span class="tag capability-tag" title="能力声明与本机接入、实跑证据独立">'+ui.esc(names[c.tag])+' · '+ui.esc(support[c.support])+'</span>';}).join('');
  }
  function details(m) {
    var d=describe(m);
    return '<details class="capability-details"><summary>全部能力与证据</summary><dl>'+ (d.native || []).map(function (c) {return '<dt>'+ui.esc(names[c.tag] || c.tag)+'</dt><dd>'+ui.esc(support[c.support] || c.support)+'</dd>';}).join('')+'</dl><p>本机视觉：'+ui.esc((d.lma || {}).visionBridge || '未知')+'；工具选择可靠性：'+ui.esc((d.lma || {}).modelToolReliability || '未知')+'。抽帧理解、调用生成工具与语音朗读属于组合能力。'+((d.evidence || {}).phoneOutput?'已有独立真机记录。':'当前标签不表示已在此手机实跑。')+'</p><pre>'+ui.esc(JSON.stringify(d,null,2))+'</pre></details>';
  }
  window.LMACapabilities={
    init:function (bridge, refresh) {ui=bridge; var host=document.createElement('details');host.className='capability-filters';host.innerHTML='<summary>按输入、工具和证据选型</summary><div class="capability-options">'+['input:text','input:image','input:video','input:audio','output:text','output:image','output:video','output:audio','output:3d','tool:calling','output:json'].map(function (tag) {return '<label><input type="checkbox" value="'+tag+'">'+names[tag]+'</label>';}).join('')+'</div><label>本地状态 <select id="capabilityAvailability"><option value="any">全部状态</option><option value="local">本地已有</option><option value="uninstalled">尚未安装</option></select></label><label>证据 <select id="capabilityEvidence"><option value="any">全部，含未知</option><option value="declared">发布者声明 / 元数据</option><option value="phone">独立真机记录</option></select></label><p class="form-help">勾选项按“同时满足”筛选。家族候选仍需适配；HF 页面只读取有界搜索元数据，离线保留缓存。</p>';document.getElementById('modelList').before(host);host.addEventListener('change',function () {selected=Array.from(host.querySelectorAll('input:checked')).map(function (el) {return el.value;});availability=document.getElementById('capabilityAvailability').value;evidence=document.getElementById('capabilityEvidence').value;refresh();});},
    signature:function(){return JSON.stringify([selected,availability,evidence]);},describe:describe,matches:matches,badges:badges,details:details,
    bind:function (m) {return m;}
  };
}());
