/* Explicit simulated HF/native state, shared by browser tests and labeled media. */
const revision = '0123456789abcdef0123456789abcdef01234567';
const repositories = [
  {id:'Qwen/Qwen3-0.6B-GGUF',task:'text-generation',downloads:120000,likes:230,license:'apache-2.0',uncensored:{declared:false,detected:false}},
  {id:'community/Dolphin-1B-GGUF',task:'text-generation',downloads:22000,likes:42,uncensored:{declared:false,detected:true,summary:'根据仓库名称或标签识别，作者声明未核对'}},
  {id:'example/Other-Format-Model',task:'text-generation',downloads:1200,likes:12,uncensored:{declared:false,detected:false}}
];
const files = [
  {path:'Qwen3-0.6B-Q8_0.gguf',quant:'Q8_0',bytes:639446688,sha256:'a'.repeat(64),blocked:''},
  {path:'mmproj-F16.gguf',quant:'F16',bytes:100000000,sha256:'b'.repeat(64),blocked:'视觉投影文件不能单独作为文本模型加载'}
];
const hubFixture = {items:[],next:'',previous:false,page:1,initialized:false,searching:false,error:'',query:'',format:'gguf',sort:'downloads',files:{items:[],loading:false,error:''},fixtureRepositories:repositories,fixtureFiles:files,fixtureRevision:revision};
function installHubBridge({stateKey}) {
  window.__handleHub = function (command) {
    const f = window[stateKey], h = f.hub;
    if (command.action === 'inspectModel' || command.action === 'saveModelSettings') {
      const model = f.models.find(m => m.id === command.id);
      if (!model || window.__rejectNextAction === command.action) return;
      model.config ||= {values:{threads:4,context:2048,maxTokens:512,temperature:0.7,reasoning:'off',systemPrompt:'你是一个有帮助的本地助手。'},limits:{threadsMax:8,contextMax:model.id==='m06'?16384:8192,contextKnown:true,maxTokensMax:2047,temperatureMax:2},metadata:{source:'gguf',architecture:'qwen3',contextLength:model.id==='m06'?16384:8192}};
      if (command.action === 'saveModelSettings') {
        const v = {...model.config.values,...command.settings}, l = model.config.limits;
        v.context=Math.max(2,Math.min(l.contextMax,Math.floor(v.context))); v.maxTokens=Math.max(1,Math.min(v.context-1,Math.floor(v.maxTokens)));
        v.threads=Math.max(1,Math.min(l.threadsMax,Math.floor(v.threads)));v.temperature=Math.max(0,Math.min(2,v.temperature));
        model.config.values=v; l.maxTokensMax=v.context-1;
      }
    }
    if (command.action === 'hubSearch') {
      const q = command.query.toLowerCase().replace('https://huggingface.co/', '');
      h.query = command.query; h.format = command.format; h.sort = command.sort;
      h.items = h.fixtureRepositories.filter(m => (!q || m.id.toLowerCase().includes(q)) && (command.format === 'all' || !m.id.startsWith('example/')));
      h.initialized = true; h.searching = false; h.error = ''; h.page = 1; h.previous = false; h.next = q ? '' : 'fixture-page-2';
    }
    if (command.action === 'hubPage') { h.page = command.direction === 'next' ? 2 : 1; h.previous = h.page === 2; h.next = h.previous ? '' : 'fixture-page-2'; h.error = ''; }
    if (command.action === 'hubFiles') {
      const repo = h.fixtureRepositories.find(m => m.id === command.repository);
      h.files = {repository:{...repo,revision:h.fixtureRevision},items:repo.id.startsWith('example/') ? [] : h.fixtureFiles,next:'fixture-file-page-2',previous:false,page:1,loading:false,error:''};
    }
    if (command.action === 'hubFilePage') { h.files.page = command.direction === 'next' ? 2 : 1; h.files.previous = h.files.page === 2; h.files.next = h.files.previous ? '' : 'fixture-file-page-2'; h.files.error = ''; }
    if (command.action === 'hubDownload') {
      const file = h.files.items.find(x => x.path === command.path), repo = h.files.repository;
      if (!f.models.some(m => m.id === 'hf_ui_test')) f.models.push({id:'hf_ui_test',name:'Qwen3-0.6B-GGUF · Q8_0',family:'Hugging Face',tier:'hub',hub:true,recommended:false,repository:repo.id,revision:repo.revision,filename:file.path,quant:file.quant,bytes:file.bytes,description:'HF 固定版本 GGUF · 模拟下载状态',tags:['HF'],uncensored:repo.uncensored,download:{state:'queued'},installed:false});
    }
    if (command.action === 'hubToken') f.settings.hfTokenSet = !!command.token;
    if (command.action === 'deleteModel') {
      const model = f.models.find(m => m.id === command.id);
      if (model && model.hub) f.models.splice(f.models.indexOf(model), 1);
      else if (model) {model.installed=false;model.partialBytes=0;model.download={};}
    }
  };
}
module.exports = {hubFixture, installHubBridge};
