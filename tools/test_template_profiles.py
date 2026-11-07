"""Weight-free tests against the pinned native Jinja renderer, grammar and parser.
Native Windows only; no model downloads, tensors, inference, device or virtualization.
"""
import hashlib,json,os,subprocess
from pathlib import Path
from evidence import ROOT,fingerprint,current
from build_llama_chat_runtime import prepare_source
OUT=ROOT/'build/chat-template-native'
def inputs():
 return fingerprint('tools/test_template_profiles.py','tools/build_llama_chat_runtime.py','native/chat-runtime','third_party/patches/0002-bare-json-parallel-tools.patch','tests/native/chat-template-probe','app/src/main/assets/chat-template-profiles.json','app/src/main/assets/chat-templates','third_party/BUILD_INFO.json')
def main():
 prepare_source()
 before=inputs();OUT.mkdir(exist_ok=True);binary=OUT/'lma_chat_template_probe.exe'
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'build/native-src/llama-chat-runtime',text=True).strip()
 assert revision=='b29c606e28a01b1bc8c1351026a0fa6e616bf6c4'
 drive=next(c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists())
 subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
 try:
  cmake=drive+'/build/toolchain/cmake-3.31.6/bin/cmake.exe';base=drive+'/build/chat-template-native'
  commands=[[cmake,'-S',drive+'/tests/native/chat-template-probe','-B',base,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+drive+'/build/toolchain/cmake-3.31.6/bin/ninja.exe','-DCMAKE_BUILD_TYPE=Release','-DLMA_LLAMA_SOURCE='+drive+'/build/native-src/llama-chat-runtime'],[cmake,'--build',base,'--target','lma_chat_template_probe','-j','4']]
  for i,command in enumerate(commands):
   script=OUT/('gate-build-'+str(i)+'.cmd');script.write_text('@echo off\ncall "C:/Program Files (x86)/Microsoft Visual Studio/2019/BuildTools/VC/Auxiliary/Build/vcvars64.bat" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n','utf8')
   result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True,timeout=600);(OUT/('gate-build-'+str(i)+'.log')).write_bytes(result.stdout+result.stderr)
   assert result.returncode==0,'Inspect native template compile log'
 finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
 profile=json.loads((ROOT/'app/src/main/assets/chat-template-profiles.json').read_text())['profiles'][0];template=ROOT/'app/src/main/assets'/profile['asset']
 assert hashlib.sha256(template.read_bytes()).hexdigest()==profile['sha256']
 checks=[]
 def check(condition,label):
  assert condition,label
  checks.append(label)
 def run(name,request,target=template):
  path=OUT/(name+'-request.json');path.write_text(json.dumps(request),'utf8')
  p=subprocess.run([str(binary),str(target),str(path)],capture_output=True,timeout=30)
  (OUT/(name+'-output.json')).write_bytes(p.stdout);(OUT/(name+'-stderr.txt')).write_bytes(p.stderr)
  assert p.returncode==0,'Native render/parser failed: '+name
  return json.loads(p.stdout)
 schema={'type':'object','properties':{'value':{'type':'integer'}},'required':['value'],'additionalProperties':False}
 tools=[{'type':'function','function':{'name':'lma_tool_'+str(i),'description':'LMA_DEFINITION_'+str(i),'parameters':schema}} for i in range(41)]
 base={'messages':[{'role':'user','content':'Call lma_tool_40 with value=42'}],'tools':tools,'tool_choice':'auto','generated':'{"name":"lma_tool_40","arguments":{"value":42}}'}
 for mode in ['auto','required','named']:
  q=json.loads(json.dumps(base));q['tool_choice']='auto' if mode=='auto' else 'required'
  if mode=='named':q['chat_template_kwargs']={'tools':q['tools']};q['tools']=[q['tools'][-1]]
  d=run(mode,q)
  check(d['template_source'].encode()==template.read_bytes(),mode+': native effective template source matches the packaged bytes after lexer normalization')
  check(all(t['function']['description'] in d['prompt'] for t in tools),mode+': every one of 41 complete declarations is rendered')
  check(d['parsed']['tool_calls'][0]['function']=={'name':'lma_tool_40','arguments':'{"value":42}'},mode+': actual native parser extracts function name and JSON arguments')
  check(d['format']=='peg-native' and (mode=='auto' or bool(d['grammar'])),mode+': native tool parser and grammar are active')
  if mode=='named':check('lma_tool_40' in d['grammar'] and 'lma_tool_0' not in d['grammar'],'Named grammar selects only the target while the prompt retains all 41')
 old=ROOT/'tests/native/chat-template-probe/embedded.jinja'
 check(hashlib.sha256(old.read_bytes()).hexdigest()==profile['embeddedTemplateSha256'],'The retained ordinary-chat branch matches the pinned GGUF template bytes')
 plain={'messages':[{'role':'system','content':'Keep this system instruction'},{'role':'user','content':'17+26'}]}
 check(run('plain',plain)['prompt']==run('plain-original',plain,old)['prompt'],'Ordinary chat rendering is unchanged by the model-bound repair')
 long=json.loads(json.dumps(base));long['tools'][0]['function']['description']='LMA_DEFINITION_0'+('long-description '*2100)
 check(len(run('expanded',long)['prompt'])>len(run('one',base|{'tools':tools[:1],'generated':base['generated'].replace('lma_tool_40','lma_tool_0')})['prompt'])+30000,'A 30KB tool description changes actual native input')
 history=json.loads(json.dumps(base));history['messages'] += [{'role':'assistant','content':None,'tool_calls':[{'id':'call_native_roundtrip','type':'function','function':{'name':'lma_tool_40','arguments':'{"value":42}'}}]},{'role':'tool','tool_call_id':'call_native_roundtrip','content':'LMA_RESULT_42'}]
 for with_tools in [True,False]:
  q=json.loads(json.dumps(history))
  if not with_tools:q.pop('tools');q.pop('generated')
  d=run('history-'+str(with_tools),q)
  check('<tool_response>' in d['prompt'] and 'LMA_RESULT_42' in d['prompt'] and 'lma_tool_40' in d['prompt'],'Native history retains the assistant call and result; tools present='+str(with_tools))
  check('"arguments": "{' not in d['prompt'],'Native history keeps arguments as a JSON object, not an escaped string; tools present='+str(with_tools))
 v1=ROOT/'tests/native/chat-template-probe/dolphin3-chatml-tools-v1.jinja'
 check(run('ordinary-tool-v2',base)['prompt']==run('ordinary-tool-v1',base,v1)['prompt'],'Tool conversations without recognized DSH background retain their original rendering')
 runtime='Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\nLMA_RUNTIME_FIXTURE'
 clock='Time sampled while preparing turn 1, step 1: LMA_CLOCK_FIXTURE'
 reminder='<system-reminder>\nLMA_WORKSPACE_FIXTURE\n</system-reminder>'
 context=json.loads(json.dumps(base));context['messages']=[{'role':'system','content':'LMA_SYSTEM_FIXTURE'},{'role':'user','content':'LMA_PENDING_TASK_FIXTURE'},{'role':'user','content':reminder},{'role':'user','content':runtime},{'role':'user','content':clock}]
 focused=run('dsh-task-focus',context);prompt=focused['prompt']
 check(all(prompt.count(m['content'])==1 for m in context['messages']),'DSH task focus retains every original message content exactly once, including workspace/runtime/time')
 check(prompt.index(reminder)<prompt.index(runtime)<prompt.index(clock)<prompt.index('LMA_PENDING_TASK_FIXTURE'),'Recognized trailing DSH metadata precedes the pending user task without changing metadata order')
 check(all(t['function']['description'] in prompt for t in tools) and focused['parsed']['tool_calls'][0]['function']['name']=='lma_tool_40','All 41 tools and real native call parsing survive task focus')
 for mode in ['auto','required','none']:
  q=json.loads(json.dumps(context));q['tool_choice']=mode
  if mode=='none':q['generated']='LMA_PLAIN_FIXTURE'
  d=run('dsh-focus-'+mode,q)
  check((not d['grammar']) if mode=='none' else (bool(d['grammar']) if mode=='required' else d['parsed']['tool_calls'][0]['function']['name']=='lma_tool_40'),'Task focus retains tool_choice semantics: '+mode)
  if mode=='none':check(d['parsed']['content']=='LMA_PLAIN_FIXTURE' and not d['parsed'].get('tool_calls'),'None choice accepts ordinary text without manufacturing a call')
 results=json.loads(json.dumps(context));results['messages'] += [history['messages'][1],{'role':'tool','tool_call_id':'call_native_roundtrip','content':'LMA_RESULT_FOCUS_FIXTURE'},{'role':'user','content':'Time sampled while preparing turn 2, step 1: LMA_CLOCK_AFTER_RESULT_FIXTURE'}]
 for with_tools in [True,False]:
  q=json.loads(json.dumps(results))
  if not with_tools:q.pop('tools');q.pop('generated')
  d=run('dsh-result-focus-'+str(with_tools),q);s=d['prompt']
  check(s.count('LMA_RESULT_FOCUS_FIXTURE')==1 and s.index('LMA_CLOCK_AFTER_RESULT_FIXTURE')<s.index('LMA_RESULT_FOCUS_FIXTURE'),'Tool result stays intact after trailing DSH time metadata; current tools='+str(with_tools))
  check('lma_tool_40' in s and '<tool_response>' in s and '"arguments": "{' not in s,'Focused continuation retains the actual call/JSON arguments/result; current tools='+str(with_tools))
  if with_tools:check(s.startswith(prompt),'Later turns preserve the established rendered prefix so task placement and KV reuse stay consistent')
 for name,messages in [('no-runtime',[{'role':'user','content':'LMA_PENDING_TASK_FIXTURE'},{'role':'user','content':clock}]),('no-task',[context['messages'][0],context['messages'][3],context['messages'][4]])]:
  q=json.loads(json.dumps(base));q['messages']=messages
  check(run('focus-boundary-'+name,q)['prompt']==run('focus-boundary-v1-'+name,q,v1)['prompt'],'Metadata placement preserves other message ordering: '+name)
 later=json.loads(json.dumps(context));later['messages'].append({'role':'user','content':'LMA_LATER_TASK_FIXTURE'});s=run('later-task',later)['prompt']
 check(s.index('LMA_PENDING_TASK_FIXTURE')<s.index('LMA_LATER_TASK_FIXTURE') and all(s.count(m['content'])==1 for m in later['messages']),'A later real user message remains after the earlier real task; every original content occurs once')
 q={'messages':context['messages']}
 check(run('plain-with-runtime',q)['prompt']==run('plain-with-runtime-original',q,old)['prompt'],'Ordinary chat with runtime-like text is still byte-equivalent to the embedded GGUF template')
 first=base['generated'];second=first.replace('lma_tool_40','lma_tool_0').replace('42','43')
 def reject(name,q):
  path=OUT/(name+'-request.json');path.write_text(json.dumps(q),'utf8')
  p=subprocess.run([str(binary),str(template),str(path)],capture_output=True,timeout=30)
  (OUT/(name+'-stderr.txt')).write_bytes(p.stderr)
  check(p.returncode!=0,name+': malformed or disallowed output is rejected without a successful final call')
 for label,separator in [('space',' '),('newline','\n'),('double-newline','\n\n'),('adjacent',''),('comma',', ')]:
  q=base|{'generated':first+separator+second}
  d=run('parallel-'+label,q)['parsed']['tool_calls']
  check([c['function'] for c in d]==[{'name':'lma_tool_40','arguments':'{"value":42}'},{'name':'lma_tool_0','arguments':'{"value":43}'}],label+': both bare native JSON records retain exact function names, arguments and order')
  reject('parallel-disabled-'+label,q|{'parallel_tool_calls':False})
 for label,generated in [('invalid-separator',first+';'),('malformed-second',first+'\n{"name":"lma_tool_0","arguments":!}'),('unknown-second',first+'\n'+second.replace('lma_tool_0','unknown_fixture_tool'))]:
  reject(label,base|{'generated':generated,'builder_fixture':{}})
 for label,generated,expected in [
  ('final-open-envelope',first[:-1],[42]),
  ('final-envelope-comma',first[:-1]+',',[42]),
  ('final-envelope-whitespace',first[:-1]+', \n\t',[42]),
  ('parallel-final-envelope',first+'\n'+second[:-1]+',',[42,43])]:
  parsed=run(label,base|{'generated':generated})['parsed']['tool_calls']
  check([json.loads(c['function']['arguments'])['value'] for c in parsed]==expected,
   label+': only the final bare envelope delimiter is optional; complete names and argument JSON are retained')
 for label,generated in [
  ('final-envelope-missing-name','{"arguments":{"value":42},'),
  ('final-envelope-missing-arguments','{"name":"lma_tool_40",'),
  ('final-envelope-incomplete-arguments',first[:-2]),
  ('final-envelope-incomplete-string','{"name":"lma_tool_40","arguments":{"value":"unfinished'),
  ('final-envelope-extra-result',first[:-1]+',"result":"invented"}'),
  ('final-envelope-before-another-call',first[:-1]+'\n'+second),
  ('final-envelope-unknown-name',first[:-1].replace('lma_tool_40','unknown_fixture_tool')+',')]:
  reject(label,base|{'generated':generated})
 for label,fixture in [('array',{'array_wrapped':True}),('marked',{'start':'<calls>','end':'</calls>'})]:
  start='[' if label=='array' else '<calls>';end=']' if label=='array' else '</calls>'
  q=base|{'builder_fixture':fixture,'generated':start+first+', '+second+end}
  d=run(label+'-comma',q)['parsed']['tool_calls']
  reject(label+'-unclosed-envelope',base|{'builder_fixture':fixture,'generated':start+first[:-1]+end})
  check([c['function']['name'] for c in d]==['lma_tool_40','lma_tool_0'],label+': valid comma-separated format remains supported')
  reject(label+'-missing-comma',q|{'generated':start+first+'\n'+second+end})
 for label,suffix in [('partial-name','{"name":"lma_tool_0"'),('partial-args','{"name":"lma_tool_0","arguments":{"value":4')]:
  d=run(label,base|{'generated':first+'\n'+suffix,'partial':True})['parsed']['tool_calls']
  check(d[0]['function']=={'name':'lma_tool_40','arguments':'{"value":42}'} and all(c['function']['name'] in ('lma_tool_40','lma_tool_0') for c in d),label+': incremental parsing preserves the completed first call and does not rename functions')
 current(before)
 report={'passed':len(checks),'checks':checks,'native_revision':revision,'native_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'actual_native_renderer':True,'actual_native_parser':True,'actual_native_grammar':True,'model_inference_tested':False,'physical_device':False,'downloaded_model_weights':False,'input_fingerprint':before}
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps({k:report[k] for k in ['passed','actual_native_renderer','actual_native_parser','model_inference_tested']}))
if __name__=='__main__':main()
