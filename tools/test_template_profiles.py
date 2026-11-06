"""Weight-free tests against the pinned native Jinja renderer, grammar and parser.
Native Windows only; no model downloads, tensors, inference, device or virtualization.
"""
import hashlib,json,os,subprocess
from pathlib import Path
from evidence import ROOT,fingerprint,current
OUT=ROOT/'build/chat-template-native'
def inputs():
 return fingerprint('tools/test_template_profiles.py','tests/native/chat-template-probe','app/src/main/assets/chat-template-profiles.json','app/src/main/assets/chat-templates','third_party/BUILD_INFO.json')
def main():
 before=inputs();OUT.mkdir(exist_ok=True);binary=OUT/'lma_chat_template_probe.exe'
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT/'build/native-src/llama-soulx',text=True).strip()
 assert revision=='b29c606e28a01b1bc8c1351026a0fa6e616bf6c4'
 drive=next(c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists())
 subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
 try:
  cmake=drive+'/build/toolchain/cmake-3.31.6/bin/cmake.exe';base=drive+'/build/chat-template-native'
  commands=[[cmake,'-S',drive+'/tests/native/chat-template-probe','-B',base,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+drive+'/build/toolchain/cmake-3.31.6/bin/ninja.exe','-DCMAKE_BUILD_TYPE=Release','-DLMA_LLAMA_SOURCE='+drive+'/build/native-src/llama-soulx'],[cmake,'--build',base,'--target','lma_chat_template_probe','-j','4']]
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
 current(before)
 report={'passed':len(checks),'checks':checks,'native_revision':revision,'native_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'actual_native_renderer':True,'actual_native_parser':True,'actual_native_grammar':True,'model_inference_tested':False,'physical_device':False,'downloaded_model_weights':False,'input_fingerprint':before}
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps({k:report[k] for k in ['passed','actual_native_renderer','actual_native_parser','model_inference_tested']}))
if __name__=='__main__':main()
