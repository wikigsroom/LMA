"""Production Java/actual-host-child contracts and pinned native math; no model inference."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_openmoss import validate_sources,sound_primitives
from openmoss_pipeline import guarded_pipeline,prompt_primitives

ROOT=Path(__file__).resolve().parents[1]


def main():
    lock=json.loads((ROOT/'third_party/openmoss-source-lock.json').read_text(encoding='utf-8'));source=validate_sources(lock)
    inputs=fingerprint('app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/OpenMossEngine.java','app/src/main/java/com/lma/app/LocalEngine.java','app/src/main/java/com/lma/app/NativeWorker.java','app/src/main/assets/recipe-templates.json','native/openmoss','tests/openmoss-host','tests/native/openmoss_policy_test.cpp','tests/tts-host/com/lma/app/LmaApp.java','tests/host/android/util/AtomicFile.java','tools/test_openmoss.py','tools/openmoss_pipeline.py','tools/fetch_openmoss.py','third_party/openmoss-source-lock.json')
    out=ROOT/'build/openmoss-tests';out.mkdir(parents=True,exist_ok=True);(out/'results.json').unlink(missing_ok=True)
    run=out/'run'
    if run.exists():
        assert run.resolve().parent==out.resolve();shutil.rmtree(run)
    run.mkdir();classes=out/'classes';classes.mkdir(exist_ok=True)
    dep=ROOT/'build/test-deps/json-20250517.jar';assert hashlib.sha256(dep.read_bytes()).hexdigest()=='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+sorted((ROOT/'tests/openmoss-host').rglob('*.java'))+[ROOT/'app/src/main/java/com/lma/app'/(n+'.java') for n in ('OpenMossEngine','LocalEngine','NativeWorker')]+[ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=out/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
    subprocess.run([shutil.which('javac'),'-J-Duser.language=en','-encoding','UTF-8','--release','8','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],cwd=ROOT,check=True)
    r=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.OpenMossTest',str(run),str(ROOT/'app/src/main/assets/recipe-templates.json')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120);(out/'java-output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    java=json.loads(r.stdout.strip().splitlines()[-1]);(out/'openmoss-prompt-primitives.inc').write_text(prompt_primitives(source),encoding='utf-8');(out/'openmoss-sound-primitives.inc').write_text(sound_primitives(source),encoding='utf-8')
    setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'));assert setup.is_file(),'Set LMA_VCVARS to native Windows C++ tools'
    command=out/'compile-native.cmd';command.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 /O2 /I. /I../../build/native-src/openmoss/include "../../tests/native/openmoss_policy_test.cpp" /Fe:openmoss-policy-test.exe /Fo:openmoss-policy-test.obj\n',encoding='ascii')
    r=subprocess.run(['cmd','/d','/c',command.name],cwd=out,capture_output=True,timeout=90);(out/'native-compile.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('Inspect build/openmoss-tests/native-compile.log')
    r=subprocess.run([str(out/'openmoss-policy-test.exe')],cwd=out,capture_output=True,text=True,timeout=20)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    native=json.loads(r.stdout.strip());current(inputs)
    pipeline=guarded_pipeline(source);assert pipeline.count('lma_openmoss::validate_generation_budget(')==1 and pipeline.index('lma_openmoss::validate_generation_budget(')<pipeline.index('// Chunking the prefill')
    report=dict(generation_budget_in_actual_pipeline=True,passed=java['passed']+native['passed'],java=java,native=native,production_openmoss_binding=True,actual_host_children=True,model_inference=False,physical_android=False,generated_audio_outputs=False,structural_wav_fixture=True,input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))


if __name__=='__main__':main()
