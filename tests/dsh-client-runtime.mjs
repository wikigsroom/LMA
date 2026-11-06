// Runs the pinned client's actual adapter, Models layer and wire codec; no DSH app/server/agent/tool runs.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync, readdirSync, mkdirSync} from 'node:fs';
import {resolve, join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';

const [runtimeInput, outputInput, java, classpath] = process.argv.slice(2);
const runtimeRoot=resolve(runtimeInput), outputRoot=resolve(outputInput);
const modules = join(runtimeRoot, 'lib/node_modules');
const checks = [];
const check = (ok, message) => { assert.ok(ok, message); checks.push(message); };
const load = (name, file='lib/index.js') => import(pathToFileURL(join(modules, name, file)));
const {PiAiAdapter} = await load('@deepseek-ai/dsh-llm-pi-ai');
const pi = await load('@earendil-works/pi-ai', 'dist/api/openai-completions.js');
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');

async function collectToolSchemas() {
    const definitions = [], plugins = [];
    for (const name of readdirSync(join(modules, '@deepseek-ai')).filter(name=>name.startsWith('dsh-tool-')).sort()) {
        const registered = [], injections = [], effects = [];
        const ctx = {
            tools:{register(tool) { registered.push(tool); return ()=>{}; }},
            systemPrompt:{section(){},context(){},getSectionOrder(){return 1;},getContextOrder(){return 1;}},
            shell:{sandboxMode:undefined},fs:{sandboxMode:undefined},fiber:{state:2},
            sessionProjections:{register(){}},
            jobs:{attachController(){},events:{subscribe(){return ()=>{};}}},
            subagents:{resolveMaxDepth(){return 2;},getProvider(){return {name:'fixture',inheritsParentContext:false,capabilities:{depthLimit:true,agentOptions:true}};}},
            get(){return undefined;},on(){},logger:{info(){},warn(){}},
            effect(fn){effects.push(fn);return ()=>{};},
            inject(names,fn){injections.push({names,fn});}
        };
        const configInput = {
            'dsh-tool-fs-search':{sampleOverCapGlobResults:false},
            'dsh-tool-todo':{allowParallelInProgress:false},
            'dsh-tool-subagent':{provider:'fixture'},
            'dsh-tool-workspace-dependencies':{source:join(outputRoot,'synthetic-dependencies.json')}
        }[name] ?? {};
        const plugin = await load('@deepseek-ai/'+name);
        await plugin.apply(ctx, typeof plugin.Config==='function' ? plugin.Config(configInput) : configInput);
        // Audited registration callbacks only: no handlers, timers, startup effects, providers or tools execute.
        if (['dsh-tool-bash','dsh-tool-pwsh','dsh-tool-schedule','dsh-tool-fs'].includes(name)) {
            for (const injection of injections) injection.fn(ctx);
        }
        if (name==='dsh-tool-subagent') {
            assert.equal(effects.length,1,'The pinned subagent effect must remain registration-only');
            const dispose = effects[0]();
            if (typeof dispose==='function') dispose();
        }
        plugins.push({plugin:name,tools:registered.map(tool=>tool.name)});
        for (const tool of registered) {
            assert.equal(typeof tool.name,'string');
            definitions.push({plugin:name,name:tool.name,description:tool.description,parameters:tool.parameters});
        }
    }
    return {definitions,plugins};
}

const {definitions,plugins} = await collectToolSchemas();
const uniqueTools = [...new Map(definitions.map(tool=>[tool.name,tool])).values()];
check(plugins.length===25,'All 25 pinned tool packages loaded for declaration-only review');
check(uniqueTools.some(tool=>tool.name==='subagent') && uniqueTools.some(tool=>tool.name==='read_image') && uniqueTools.some(tool=>tool.name==='job_output'),'Subagent, attachment and background-job declarations are included without executing tools');

const sum = {name:'lma_sum',description:'Synthetic two-integer addition tool',parameters:{type:'object',properties:{a:{type:'integer'},b:{type:'integer'}},required:['a','b'],additionalProperties:false}};
const echo = {name:'lma_echo',description:'Synthetic Unicode echo tool',parameters:{type:'object',properties:{text:{type:'string'}},required:['text'],additionalProperties:false}};
const event = (delta,finish=null) => 'data: '+JSON.stringify({id:'chatcmpl-client-fixture',object:'chat.completion.chunk',model:'m15',created:1,choices:[{index:0,delta,finish_reason:finish}]})+'\n\n';
const usage = 'data: '+JSON.stringify({choices:[],usage:{prompt_tokens:20,completion_tokens:10,total_tokens:30}})+'\n\n';
const end = finish => event({},finish)+usage+'data: [DONE]\n\n';
const answer = (text='42',finish='stop') => event({role:'assistant'})+event({content:text})+end(finish);
const call = (index,id,name,args) => ({index,id,type:'function',function:{name,arguments:args}});
const single = event({role:'assistant'})+event({reasoning_content:'Use the client-owned tool.'})+event({tool_calls:[call(0,'call_sum','lma_sum','{"a":20,')]})+event({tool_calls:[{index:0,function:{arguments:'"b":22}'}}]})+end('tool_calls');
const parallel = event({role:'assistant'})+event({tool_calls:[call(0,'call_sum','lma_sum','{"a":20,'),call(1,'call_echo','lma_echo','{"text":"台')]})+event({tool_calls:[{index:1,function:{arguments:'北🦊"}'}},{index:0,function:{arguments:'"b":22}'}}]})+end('tool_calls');
const cases = Object.fromEntries(definitions.map((_,index)=>['schema-'+index,{sse:answer()}]));
for (const id of ['all-tools','resume','parallel-resume','third-round','updated-tools','large','tool-error','child-a','child-b','new-model']) cases[id]={sse:answer()};
Object.assign(cases,{
    single:{sse:single},parallel:{sse:parallel},
    'second-round':{sse:event({role:'assistant'})+event({tool_calls:[call(0,'call_second','lma_echo','{"text":"42"}')]})+end('tool_calls')},
    'bad-native':{sse:event({role:'assistant'})+event({tool_calls:[call(0,'bad','undeclared_fixture','{}')]})+end('tool_calls')},
    truncated:{sse:single.replace('data: [DONE]\n\n','')},
    length:{sse:answer('partial','length')},
    'idle-comments':{sse:answer(),comment_delay_ms:400},
    'advanced-name':{sse:answer()},'too-large':{sse:answer()}
});
mkdirSync(outputRoot,{recursive:true});
const casesFile = join(outputRoot,'synthetic-cases.json');
writeFileSync(casesFile,JSON.stringify(cases));
const requestsRoot = join(outputRoot,'client-wire-private');
const child = spawn(java,['-Dfile.encoding=UTF-8','-cp',classpath,'com.lma.app.core.DshClientFixture',requestsRoot,casesFile],{stdio:['pipe','pipe','pipe']});
const reader = createInterface({input:child.stdout});
let serverErrors=''; child.stderr.on('data',data=>serverErrors+=data.toString());
const realFetch = globalThis.fetch;
let baseUrl;
const exchanges = [];

function makeAdapter(id,{compat,timeout=300000,tools=[sum,echo]}={}) {
    const model={id:'m15',name:'Synthetic LMA contract model',provider:'lma-fixture',api:'openai-completions',baseUrl,reasoning:false,input:['text'],contextWindow:131072,maxTokens:512,cost:{input:0,output:0,cacheRead:0,cacheWrite:0},...compat?{compat}:{}};
    const fetch = async (url,init) => {
        assert.equal(String(url),baseUrl+'/chat/completions','The client may call only the owned loopback fixture');
        const request=JSON.parse(init.body);
        const headers=new Headers(init.headers);headers.set('X-LMA-Fixture-Case',id);
        const response=await realFetch(url,{...init,headers});
        exchanges.push({id,request,status:response.status});
        return response;
    };
    const provider={id:'lma-fixture',name:'Synthetic LMA fixture',baseUrl,auth:{apiKey:{name:'fixture',resolve:async({credential})=>({auth:{apiKey:credential?.key},source:'fixture'})}},getModels:()=>[model],streamSimple:(model,context,options)=>pi.streamSimple(model,context,{...options,fetch})};
    const profile={modelErrors:new Map(),piProvider:provider,streamIdleTimeoutMs:timeout};
    const profiles=new Map([['lma-fixture',profile]]);
    const adapter=new PiAiAdapter({profiles:()=>profiles,resolveApiKey:async()=> 'fixture-not-a-secret'});
    const options={provider:'lma-fixture',model:'m15',system:'LMA/DSH synthetic interoperability test; no actual tools execute.',maxTokens:512,tools,messages:[{role:'user',content:[{type:'text',text:'Use the supplied function for 20 plus 22.'}]}]};
    return {adapter,options};
}
async function generate(id,options={},customize=()=>{}) {
    const setup=makeAdapter(id,options); customize(setup.options);
    const chunks=[];
    for await(const chunk of setup.adapter.stream(setup.options)) chunks.push(chunk);
    const finish=chunks.find(chunk=>chunk.type==='finish');
    return {chunks,finish,content:chunks.filter(chunk=>chunk.type==='block-end').map(chunk=>chunk.block)};
}
const wire = id => exchanges.findLast(exchange=>exchange.id===id);
const saved = id => JSON.parse(readFileSync(join(requestsRoot,id+'-normalized.json'),'utf8'));
function assistant(result) { return {role:'assistant',content:result.content,source:{provider:'lma-fixture',model:'m15',replayState:result.finish.replayState}}; }
const resultMessage=(id,text,isError=false)=>({role:'tool',toolCallId:id,isError,content:[{type:'text',text}]});

try {
    const line=await Promise.race([new Promise((resolve,reject)=>{reader.once('line',resolve);child.once('error',reject);child.once('exit',code=>reject(Error('Fixture exited before ready: '+code+' '+serverErrors)));}),new Promise((_,reject)=>{const timer=setTimeout(()=>reject(Error('Fixture startup timed out')),15000);timer.unref();})]);
    baseUrl='http://127.0.0.1:'+JSON.parse(line).port+'/v1';
    // Any unexpected global network operation fails. The sole owned server request is checked again above.
    globalThis.fetch=async(url,init)=>{assert.equal(new URL(String(url)).origin,new URL(baseUrl).origin);return realFetch(url,init);};
    for (const [index,tool] of definitions.entries()) {
        const response=await generate('schema-'+index,{tools:[tool]});
        check(response.finish?.reason.kind==='stop' && wire('schema-'+index).status===200,'Actual DSH tool schema accepted: '+tool.plugin+'/'+tool.name+' variant '+index);
    }
    await generate('all-tools',{tools:uniqueTools});
    check(saved('all-tools').tools.length===uniqueTools.length,'All unique DSH function declarations coexist in one request');
    const first=await generate('single');
    check(first.finish.reason.kind==='tool-calls','The real DSH adapter maps streamed tool_calls to its tool-calls finish');
    check(first.content.find(block=>block.type==='tool-call').arguments==='{"a":20,"b":22}','Real DSH parsing reconstructs fragmented function arguments');
    check(first.content.some(block=>block.type==='reasoning'),'Actual reasoning_content is preserved as a DSH reasoning block');
    check(first.chunks.some(chunk=>chunk.type==='tool-call-delta'),'DSH receives executable tool-call events, rather than a text rewrite');
    check(first.finish.replayState?.response.version===2,'The real adapter produces versioned durable replay metadata');
    check(wire('single').request.store===false && !saved('single').store,'The actual default client store:false is accepted and consumed');
    check(wire('single').request.max_completion_tokens===512 && saved('single').max_tokens===512,'The actual default completion-token field is normalized');
    check(first.chunks.find(chunk=>chunk.type==='usage').usage.outputTokens===10,'Usage-only SSE reaches the real client');
    const history=[{role:'user',content:[{type:'text',text:'Use the supplied tool.'}]},assistant(first),resultMessage('call_sum','42')];
    const resume=await generate('resume',{},options=>options.messages=history);
    check(resume.finish.reason.kind==='stop' && resume.content.some(block=>block.text==='42'),'Client tool result resumes a normal assistant response');
    const resumed=wire('resume').request.messages;
    check(resumed.some(message=>message.role==='assistant' && message.content===null && message.tool_calls?.[0].id==='call_sum'),'Real DSH history sends assistant content:null with tool_calls');
    check(resumed.some(message=>message.role==='assistant' && message.reasoning_content),'Durable client reasoning replay survives the LMA validator');
    check(resumed.some(message=>message.role==='tool' && message.tool_call_id==='call_sum' && message.content==='42'),'Actual tool result IDs and content survive the full wire round trip');
    const second=await generate('second-round',{},options=>options.messages=history);
    const third=await generate('third-round',{},options=>options.messages=[...history,assistant(second),resultMessage('call_second','42')]);
    check(third.finish.reason.kind==='stop' && wire('third-round').request.messages.filter(message=>message.role==='tool').length===2,'Two successive client-executed tool rounds keep their full history');
    const multi=await generate('parallel');
    check(multi.content.filter(block=>block.type==='tool-call').length===2,'Interleaved native tool indexes yield two client calls');
    check(multi.content.some(block=>block.type==='tool-call' && JSON.parse(block.arguments).text==='台北🦊'),'Three-byte native reads preserve CJK and emoji arguments');
    const resumedMulti=await generate('parallel-resume',{},options=>options.messages=[history[0],assistant(multi),resultMessage('call_echo','台北🦊'),resultMessage('call_sum','42')]);
    check(resumedMulti.finish.reason.kind==='stop','Multiple tool results may return in a different order with their IDs intact');
    const erroredTool=await generate('tool-error',{},options=>options.messages=[history[0],assistant(first),resultMessage('call_sum','Synthetic client tool failed',true)]);
    check(erroredTool.finish.reason.kind==='stop' && wire('tool-error').request.messages.some(message=>message.role==='tool' && message.content.includes('failed')),'A client tool failure remains a tool-role result and permits continuation');
    await generate('updated-tools',{},options=>{options.tools=[sum,echo];options.messages=[...history,{role:'developer',content:[{type:'text',text:'The available tools changed.'},{type:'tool-removal',toolName:'lma_sum'}]}];});
    check(!saved('updated-tools').tools.some(tool=>tool.function.name==='lma_sum'),'DSH dynamic tool removal keeps past call history without redeclaring the removed function');
    await generate('large',{},options=>{options.messages=[{role:'user',content:[{type:'text',text:'x'.repeat(300000)}]}];for(let index=0;index<130;index++)options.messages.push({role:index%2?'user':'assistant',content:[{type:'text',text:'Synthetic bounded history '+index}],...index%2?{}:{source:{provider:'lma-fixture',model:'m15'}}});});
    check(wire('large').status===200 && saved('large').messages.length>128,'Actual DSH serialization crosses the old 256 KiB and 128-message limits');
    check(wire('large').request.messages[1].content?.length>64000 || wire('large').request.messages[0].content?.length>64000,'A real client message can exceed the former 64000-unit limit');
    const children=await Promise.all(['child-a','child-b'].map(id=>generate(id)));
    check(children.every(child=>child.finish.reason.kind==='stop'),'Two independent real client adapters can complete concurrent loopback requests');
    const invalid=await generate('bad-native');
    check(invalid.finish.reason.kind==='error' && !invalid.content.some(block=>block.type==='tool-call'),'Invalid native function output is a DSH error and never completes an executable block');
    const truncated=await generate('truncated');
    check(truncated.finish.reason.kind==='error','An incomplete guarded native stream is reported as failure to DSH');
    const limited=await generate('length');
    check(limited.finish.reason.kind==='max-tokens','Native output length remains max-tokens, rather than false success');
    let idle;
    try { await generate('idle-comments',{timeout:120}); } catch(error) { idle=error; }
    check(idle?.code==='TIMEOUT','The real DSH idle watchdog expires despite ongoing SSE comments; default is a separate client limit');
    const advanced=await generate('advanced-name',{compat:{requiresToolResultName:true}},options=>options.messages=history);
    check(advanced.finish.reason.kind==='error' && wire('advanced-name').status===400,'Nondefault provider-specific tool-result names are explicitly outside the baseline profile: '+JSON.stringify({finish:advanced.finish.reason,status:wire('advanced-name').status}));
    const oversized=await generate('too-large',{},options=>options.messages=[{role:'user',content:[{type:'text',text:'x'.repeat(4*1024*1024)}]}]);
    check(oversized.finish.reason.kind==='error' && wire('too-large').status===413,'Oversized actual client requests retain an explicit HTTP capacity error');
    const report={passed:checks.length,checks,tool_schema_variants:definitions.length,unique_tool_names:uniqueTools.length,tool_plugins:plugins,schemas:definitions.map(({plugin,name,parameters})=>({plugin,name,parameters_sha256:hash(parameters)})),actual_client_code:true,actual_socket_io:true,fixture_native_response:true,client_tools_executed:false,model_inference_tested:false,physical_device:false,dsh_android_app_tested:false,phone_interactions_during_audit:false,client_default_stream_idle_timeout_ms:300000,boundaries:['Client idle watchdog is not reset by SSE comments','Nondefault vendor compatibility flags are outside the baseline OpenAI profile','Native fixture has no model or template/context evaluation; prior v1.1.0 phone evidence stays separate','Concurrent adapter sockets are not actual DSH subagents or a repeat of the production scheduler test']};
    writeFileSync(join(outputRoot,'client-results.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,tool_schema_variants:definitions.length,unique_tool_names:uniqueTools.length}));
} finally {
    globalThis.fetch=realFetch;
    child.stdin.end(); reader.close();
    await Promise.race([new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('exit',resolve);}),new Promise(resolve=>{const timer=setTimeout(()=>{child.kill();resolve();},3000);timer.unref();})]);
}
