"""Exercise the actual Java Qwen speech binding and shared native policy on Windows; no model inference."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]


def main():
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/QwenTtsEngine.java', 'app/src/main/java/com/lma/app/LocalEngine.java', 'app/src/main/java/com/lma/app/NativeWorker.java', 'native/qwen_tts', 'tools/build_qwen_tts.py', 'third_party/qwen-tts-source-lock.json', 'tests/qwen-host', 'tests/native/qwen_policy_test.cpp', 'tests/tts-host/com/lma/app/LmaApp.java', 'tests/host/android/util/AtomicFile.java', 'app/src/main/assets/recipe-templates.json', 'tools/test_qwen_tts.py')
    out = ROOT / 'build/qwen-tts-tests'; out.mkdir(parents=True, exist_ok=True); (out/'results.json').unlink(missing_ok=True)
    run = out/'run'
    if run.exists():
        assert run.resolve().parent == out.resolve(); shutil.rmtree(run)
    run.mkdir(); classes=out/'classes'; classes.mkdir(exist_ok=True)
    dep=ROOT/'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dep.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+sorted((ROOT/'tests/qwen-host').rglob('*.java'))
    sources += [ROOT/'app/src/main/java/com/lma/app'/(name+'.java') for name in ('QwenTtsEngine','LocalEngine','NativeWorker')]
    sources += [ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=out/'sources.rsp'; rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
    subprocess.run([shutil.which('javac'),'-J-Duser.language=en','-encoding','UTF-8','--release','8','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],cwd=ROOT,check=True)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.QwenTtsTest',str(run),str(ROOT/'app/src/main/assets/recipe-templates.json')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    (out/'java-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    java=json.loads(result.stdout.strip().splitlines()[-1])
    setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
    if not setup.is_file(): raise RuntimeError('Set LMA_VCVARS to native Windows C++ tools')
    command=out/'compile-native.cmd'
    command.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 "../../tests/native/qwen_policy_test.cpp" /Fe:qwen-policy-test.exe /Fo:qwen-policy-test.obj\n',encoding='ascii')
    result=subprocess.run(['cmd','/d','/c',command.name],cwd=out,capture_output=True,timeout=90); (out/'native-compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError('Native Qwen policy compile failed; inspect build/qwen-tts-tests/native-compile.log')
    result=subprocess.run([str(out/'qwen-policy-test.exe')],cwd=out,capture_output=True,text=True,timeout=20)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    native=json.loads(result.stdout.strip()); current(inputs)
    report=dict(passed=java['passed']+native['passed'],java=java,native=native,production_qwen_binding=True,actual_host_children=True,model_inference=False,physical_android=False,generated_audio_outputs=False,structural_wav_fixture=True,input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))


if __name__ == '__main__': main()
