"""Production SoulX Java process/input contracts and native bounded WAV policy.

This suite uses structural fixtures, not model quality/device evidence. The
separate --trained suite executes the same full production native worker.
"""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]

def main():
    inputs=fingerprint('app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/SoulxEngine.java','app/src/main/java/com/lma/app/LocalEngine.java','app/src/main/java/com/lma/app/NativeWorker.java','native/soulx','tests/soulx-host','tests/native/soulx_contract_test.cpp','tests/tts-host/com/lma/app/LmaApp.java','tests/host/android/util/AtomicFile.java','tools/test_soulx.py','tools/soulx_recipe.py','app/src/main/assets/recipe-templates.json')
    out=ROOT/'build/soulx-tests';out.mkdir(exist_ok=True);(out/'results.json').unlink(missing_ok=True);run=out/'run'
    if run.exists():
        if run.resolve().parent!=out.resolve():raise RuntimeError('Unsafe own fixture cleanup')
        shutil.rmtree(run)
    classes=out/'classes';classes.mkdir(exist_ok=True);dep=ROOT/'build/test-deps/json-20250517.jar'
    if hashlib.sha256(dep.read_bytes()).hexdigest()!='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':raise RuntimeError('Changed host JSON dependency')
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+list((ROOT/'tests/soulx-host').rglob('*.java'))+[ROOT/'app/src/main/java/com/lma/app'/(name+'.java') for name in ['SoulxEngine','LocalEngine','NativeWorker']]+[ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=out/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8');subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','8','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],check=True)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dstderr.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.SoulxTest',str(run),str(ROOT/'app/src/main/assets/recipe-templates.json')],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90);(out/'java-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    java=json.loads(result.stdout.strip().splitlines()[-1]);host=ROOT/'build/soulx-worker-host';receipt=json.loads((host/'receipt.json').read_text(encoding='utf-8'));current(receipt['source_inputs'])
    native=host/'lma_soulx_contract_test.exe';native=native if native.is_file() else host/'bin/lma_soulx_contract_test.exe';directory=out/'native'
    if directory.exists():
        if directory.resolve().parent!=out.resolve():raise RuntimeError('Unsafe own contract cleanup')
        shutil.rmtree(directory)
    result=subprocess.run([str(native),str(directory)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30);(out/'native-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    native_report=json.loads(result.stdout.strip().splitlines()[-1]);current(inputs)
    report=dict(passed=java['passed']+native_report['passed'],java=java,native=native_report,actual_host_children=java['actual_host_children'],production_soulx_binding=True,model_inference=False,physical_android=False,structural_wav_fixture=True,native_contract_binary_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
