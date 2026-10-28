"""Production Java child contracts + actual LiteRT CPU tiny graphs + Arm sampler comparison."""
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_stable_audio import validate_sources,runtime
from stable_audio_fixture import host_runtime,graphs
ROOT=Path(__file__).resolve().parents[1]

def extract(source,name):
    start=source.index('static void '+name+'(');brace=source.index('{',start);level=1;end=brace+1
    while level:
        if source[end]=='{':level+=1
        elif source[end]=='}':level-=1
        end+=1
    return source[start:end]

def main():
    lock=json.loads((ROOT/'third_party/stable-audio-source-lock.json').read_text(encoding='utf-8'));validate_sources(lock);runtime(lock)
    inputs=fingerprint('app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/StableAudioEngine.java','app/src/main/java/com/lma/app/LocalEngine.java','app/src/main/java/com/lma/app/NativeWorker.java','native/stable_audio','tests/stable-audio-host','tests/native/stable_audio_test.cpp','tests/tts-host/com/lma/app/LmaApp.java','tests/host/android/util/AtomicFile.java','tools/test_stable_audio.py','tools/stable_audio_fixture.py','tools/fetch_stable_audio.py','third_party/stable-audio-source-lock.json','app/src/main/assets/recipe-templates.json')
    out,schema=host_runtime(lock);(out/'results.json').unlink(missing_ok=True);fixtures=graphs(schema,out);run=out/'run'
    if run.exists():assert run.resolve().parent==out.resolve();shutil.rmtree(run)
    classes=out/'classes';classes.mkdir(exist_ok=True);dep=ROOT/'build/test-deps/json-20250517.jar'
    if hashlib.sha256(dep.read_bytes()).hexdigest()!='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':raise RuntimeError('Host JSON library differs')
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+list((ROOT/'tests/stable-audio-host').rglob('*.java'))+[ROOT/'app/src/main/java/com/lma/app'/(n+'.java') for n in ['StableAudioEngine','LocalEngine','NativeWorker']]+[ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=out/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8');subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','8','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],check=True)
    result=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dstderr.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.StableAudioTest',str(run),str(ROOT/'app/src/main/assets/recipe-templates.json')],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90);(out/'java-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    java=json.loads(result.stdout.strip().splitlines()[-1]);arm=(ROOT/'build/native-src/arm-audiogen/kleidiai-examples/audiogen/app/audiogen.cpp').read_text(encoding='utf-8');reference='// Copyright Arm 2026. SPDX-License-Identifier: Apache-2.0\nnamespace arm_reference {\nconstexpr float k_sigma_min=0;\n'+'\n'.join(extract(arm,n) for n in ['fill_random_norm_dist','fill_sigmas','sampler_ping_pong'])+'\n}\n';(out/'arm_sampler_reference.hpp').write_text(reference,encoding='utf-8')
    sdk=ROOT/'build/litert-probe/litert_cc_sdk';config=out/'include/litert/build_common/build_config.h';config.parent.mkdir(parents=True,exist_ok=True);config.write_text('#pragma once\n#define LITERT_BUILD_CONFIG_DISABLE_GPU 1\n#define LITERT_BUILD_CONFIG_DISABLE_NPU 1\n#define LITERT_DISABLE_GPU\n#define LITERT_DISABLE_NPU\n',encoding='ascii')
    readobj=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-readobj.exe';exports=subprocess.check_output([str(readobj),'--coff-exports',str(out/'libLiteRt.dll')],text=True,encoding='utf-8');names=re.findall(r'  Name: (\S+)',exports);assert 'LiteRtCreateCompiledModel' in names
    (out/'litert.def').write_text('LIBRARY libLiteRt.dll\nEXPORTS\n'+'\n'.join(names)+'\n',encoding='ascii')
    setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'));assert setup.is_file()
    command=out/'compile.cmd';command.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\nlib /nologo /def:litert.def /machine:x64 /out:LiteRt.lib\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 /O2 /I"'+str(sdk)+'" /Iinclude /I. "../../tests/native/stable_audio_test.cpp" LiteRt.lib /Fe:stable-audio-test.exe /Fo:stable-audio-test.obj\n',encoding='utf-8')
    # A temporary ASCII alias lets MSVC handle this repository's Chinese path.
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None);assert drive;subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias=drive+'/build/stable-audio-tests';command.write_text(command.read_text(encoding='utf-8').replace(str(ROOT),drive+'/').replace('\\build\\','/build/'),encoding='utf-8');result=subprocess.run(['cmd','/d','/c','compile.cmd'],cwd=alias,capture_output=True,timeout=120);(out/'native-compile.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Inspect build/stable-audio-tests/native-compile.log')
        result=subprocess.run([alias+'/stable-audio-test.exe',alias],cwd=alias,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60);(out/'native-output.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    native=json.loads(result.stdout.strip().splitlines()[-1]);current(inputs)
    report=dict(passed=java['passed']+native['passed'],java=java,native=native,actual_litert_graph_runs=native['actual_litert_graph_runs'],tiny_graphs=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),trained_checkpoint=False) for p in fixtures],production_stable_audio_binding=True,actual_host_children=java['actual_host_children'],model_inference=False,physical_android=False,generated_audio_outputs=False,structural_wav_fixture=True,input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
