"""Exercise the actual Java MossDelay speech binding and shared native policy on Windows; no model inference."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current
from fetch_moss_delay import validate_sources, primitives

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock=json.loads((ROOT/'third_party/moss-delay-source-lock.json').read_text(encoding='utf-8')); source=validate_sources(lock)
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/MossDelayEngine.java', 'app/src/main/java/com/lma/app/LocalEngine.java', 'app/src/main/java/com/lma/app/NativeWorker.java', 'native/moss_delay', 'native/qwen_tts/policy.hpp', 'native/qwen_tts/wave.hpp', 'tools/fetch_moss_delay.py', 'tools/build_moss_delay.py', 'third_party/moss-delay-source-lock.json', 'tests/moss-delay-host', 'tests/native/moss_delay_policy_test.cpp', 'tests/tts-host/com/lma/app/LmaApp.java', 'tests/host/android/util/AtomicFile.java', 'app/src/main/assets/recipe-templates.json', 'tools/test_moss_delay.py')
    out = ROOT / 'build/moss-delay-tests'; out.mkdir(parents=True, exist_ok=True); (out/'results.json').unlink(missing_ok=True)
    run = out/'run'
    if run.exists():
        assert run.resolve().parent == out.resolve(); shutil.rmtree(run)
    run.mkdir(); classes=out/'classes'; classes.mkdir(exist_ok=True)
    dep=ROOT/'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dep.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+sorted((ROOT/'tests/moss-delay-host').rglob('*.java'))
    sources += [ROOT/'app/src/main/java/com/lma/app'/(name+'.java') for name in ('MossDelayEngine','LocalEngine','NativeWorker')]
    sources += [ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=out/'sources.rsp'; rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
    subprocess.run([shutil.which('javac'),'-J-Duser.language=en','-encoding','UTF-8','--release','8','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],cwd=ROOT,check=True)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.MossDelayTest',str(run),str(ROOT/'app/src/main/assets/recipe-templates.json')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    (out/'java-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    java=json.loads(result.stdout.strip().splitlines()[-1])
    (out/'moss-primitives.inc').write_text(primitives(source, include_self_test=True),encoding='utf-8')
    setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
    if not setup.is_file(): raise RuntimeError('Set LMA_VCVARS to native Windows C++ tools')
    command=out/'compile-native.cmd'
    command.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 /O2 /Gy /I. /I"../native-src/moss-delay/include" /I"../native-src/moss-delay/ggml/include" "../../tests/native/moss_delay_policy_test.cpp" /Fe:moss-delay-policy-test.exe /Fo:moss-delay-policy-test.obj /link /OPT:REF\n',encoding='ascii')
    result=subprocess.run(['cmd','/d','/c',command.name],cwd=out,capture_output=True,timeout=90); (out/'native-compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError('Native MossDelay policy compile failed; inspect build/moss-delay-tests/native-compile.log')
    result=subprocess.run([str(out/'moss-delay-policy-test.exe')],cwd=out,capture_output=True,text=True,timeout=20)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    native=json.loads(result.stdout.strip()); current(inputs)
    report=dict(passed=java['passed']+native['passed'],java=java,native=native,production_moss_delay_binding=True,actual_host_children=True,model_inference=False,physical_android=False,generated_audio_outputs=False,structural_wav_fixture=True,input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))


if __name__ == '__main__': main()
