"""Reject conflicting shared runtimes while allowing exact baseline reuse."""
import copy,json
from pathlib import Path
from evidence import fingerprint,current
from verify_package import merged_native_files
ROOT=Path(__file__).resolve().parents[1]

def main():
    inputs=fingerprint('tools/native_payload.py','tools/verify_package.py','tools/test_native_payload.py','third_party/runtime-lock.json','third_party/engine-lock.json');passed=0
    runtime=[dict(name='libshared.so',size=12,sha256='a'*64)]
    engine=dict(engine='worker',file='libworker.so',bytes=16,sha256='b'*64,dependencies=[dict(file='libshared.so',bytes=12,sha256='a'*64,android_api_notes=[28])])
    merged=merged_native_files(runtime,[engine]);assert len(merged)==2 and len(runtime)==1;passed+=2
    for key,value in [('bytes',13),('sha256','c'*64),('android_api_notes',[29])]:
        bad=copy.deepcopy(engine);bad['dependencies'][0][key]=value
        try:merged_native_files(runtime,[bad])
        except RuntimeError:passed+=1
        else:raise AssertionError('Accepted conflicting '+key)
    for base,engines in [(runtime+runtime,[engine]),(runtime,[engine,engine]),(runtime,[dict(engine='alias',file='libshared.so',bytes=12,sha256='a'*64)])]:
        try:merged_native_files(base,engines)
        except RuntimeError:passed+=1
        else:raise AssertionError('Accepted duplicate or worker alias')
    base=json.loads((ROOT/'third_party/runtime-lock.json').read_text(encoding='utf-8'))['files'];engines=json.loads((ROOT/'third_party/engine-lock.json').read_text(encoding='utf-8'))['engines']
    actual=merged_native_files(base,engines);assert len(actual)==27 and len({f['name'] for f in actual})==27;passed+=2
    current(inputs);report=dict(passed=passed,native_files=len(actual),exact_shared_base_runtime_reuse=True,model_inference=False,physical_android=False,input_fingerprint=inputs);out=ROOT/'build/native-payload-tests';out.mkdir(exist_ok=True);(out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
