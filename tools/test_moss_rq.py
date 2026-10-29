"""Production RQ Java, actual host children, and two pinned tiny GGML graph fixtures."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_moss_rq import validate_sources
from moss_rq_pipeline import generated_sources
ROOT=Path(__file__).resolve().parents[1]

def main():
    lock=json.loads((ROOT/'third_party/moss-rq-source-lock.json').read_text(encoding='utf-8'));source=validate_sources(lock)
    inputs=fingerprint('native/audio_pcm.hpp','tests/native/audio_pcm_test.cpp','tests/native/moss_codec_stream_test.cpp','app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/MossRqEngine.java','app/src/main/java/com/lma/app/LocalEngine.java','app/src/main/java/com/lma/app/NativeWorker.java','app/src/main/assets/recipe-templates.json','native/moss-rq','native/openmoss','tests/moss-rq-host','tests/native/moss_rq_policy_test.cpp','tests/native/moss_rq_layout_test.cpp','tests/tts-host/com/lma/app/LmaApp.java','tests/host/android/util/AtomicFile.java','tools/test_moss_rq.py','tools/moss_rq_pipeline.py','tools/fetch_moss_rq.py','third_party/moss-rq-source-lock.json')
    out=ROOT/'build/moss-rq-tests';out.mkdir(parents=True,exist_ok=True);(out/'results.json').unlink(missing_ok=True);run=out/'run'
    if run.exists():assert run.resolve().parent==out.resolve();shutil.rmtree(run)
    run.mkdir();classes=out/'classes';classes.mkdir(exist_ok=True);dep=ROOT/'build/test-deps/json-20250517.jar';assert hashlib.sha256(dep.read_bytes()).hexdigest()=='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+sorted((ROOT/'tests/moss-rq-host').rglob('*.java'))+[ROOT/'app/src/main/java/com/lma/app'/(n+'.java') for n in ('MossRqEngine','LocalEngine','NativeWorker')]+[ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
    rsp=out/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
    subprocess.run([shutil.which('javac'),'-J-Duser.language=en','-Xlint:-options','-encoding','UTF-8','--release','8','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],cwd=ROOT,check=True)
    r=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.MossRqTest',str(run),str(ROOT/'app/src/main/assets/recipe-templates.json')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120);(out/'java-output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    java=json.loads(r.stdout.strip().splitlines()[-1])
    r=subprocess.run([shutil.which('java'),'-Dfile.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.AudioStreamingTest',str(run/'audio-streaming')],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120);(out/'audio-streaming-output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    audio=json.loads(r.stdout.strip().splitlines()[-1]);setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'));assert setup.is_file()
    command=out/'compile-native.cmd';command.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 /O2 "../../tests/native/moss_rq_policy_test.cpp" /Fe:rq-policy-test.exe /Fo:rq-policy-test.obj\nif errorlevel 1 exit /b %errorlevel%\ncl /nologo /std:c++17 /EHsc /W4 /O2 "../../tests/native/audio_pcm_test.cpp" /Fe:audio-pcm-test.exe /Fo:audio-pcm-test.obj\n',encoding='ascii')
    r=subprocess.run(['cmd','/d','/c',command.name],cwd=out,capture_output=True,timeout=90);(out/'native-compile.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('Inspect build/moss-rq-tests/native-compile.log')
    r=subprocess.run([str(out/'rq-policy-test.exe')],cwd=out,capture_output=True,text=True,timeout=20)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    native=json.loads(r.stdout.strip())
    r=subprocess.run([str(out/'audio-pcm-test.exe')],cwd=out,capture_output=True,text=True,timeout=20)
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    pcm=json.loads(r.stdout.strip());drive=next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None);assert drive
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    graphs=[]
    try:
        alias=drive+'/';generated=ROOT/'build/moss_rq-generated';generated.mkdir(parents=True,exist_ok=True)
        for name,data in generated_sources(source).items():
            target=generated/name
            if not target.is_file() or target.read_text(encoding='utf-8')!=data:target.write_text(data,encoding='utf-8')
        script=out/'build-graphs.cmd';cmake=alias+'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        options=['-DLMA_MOSS_RQ_SOURCE='+alias+'build/native-src/moss-tts-cpp','-DLMA_MOSS_RQ_GENERATED='+alias+'build/moss_rq-generated','-DBUILD_SHARED_LIBS=OFF','-DGGML_NATIVE=OFF','-DGGML_OPENMP=OFF','-DGGML_BACKEND_DL=OFF','-DGGML_CCACHE=OFF','-DGGML_BUILD_TESTS=OFF','-DGGML_BUILD_EXAMPLES=OFF']
        script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n"'+cmake+'" --fresh -S '+alias+'native/moss-rq -B '+alias+'build/moss-rq-host-native -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM='+alias+'build/toolchain/cmake-3.31.6/bin/ninja.exe '+' '.join(options)+'\nif errorlevel 1 exit /b %errorlevel%\n"'+cmake+'" --build '+alias+'build/moss-rq-host-native --target test_local_block test_rt_depth_loop test_rq_layout test_codec_stream -j 4\n',encoding='ascii')
        r=subprocess.run(['cmd','/d','/c',str(script)],cwd=alias,capture_output=True,timeout=240);(out/'graphs-build.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Inspect build/moss-rq-tests/graphs-build.log')
        r=subprocess.run([alias+'build/moss-rq-host-native/test_rq_layout.exe'],cwd=out,capture_output=True,text=True,timeout=30);(out/'layout-output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
        if r.returncode:raise RuntimeError('Production GGUF layout policy failed: '+r.stdout+r.stderr)
        layout=json.loads(r.stdout.strip())
        for name in ('local_block','rt_depth_loop'):
            r=subprocess.run([alias+'build/moss-rq-host-native/test_'+name+'.exe'],cwd=source,capture_output=True,text=True,timeout=30);(out/('graph-'+name+'.txt')).write_text(r.stdout+r.stderr,encoding='utf-8')
            if r.returncode!=0:raise RuntimeError('Real tiny graph did not pass (skips fail): '+name+' '+r.stdout+r.stderr)
            graphs.append(dict(test=name,exit_code=0,fixture_sha256=hashlib.sha256((source/'tests/fixtures'/('local_block.gguf' if name=='local_block' else 'rt_tiny_model.gguf')).read_bytes()).hexdigest(),model_checkpoint=False))
        r=subprocess.run([alias+'build/moss-rq-host-native/test_codec_stream.exe',alias+'build/native-src/moss-tts-cpp/tests/fixtures/nano_codec.gguf'],cwd=source,capture_output=True,text=True,timeout=45);(out/'codec-stream-output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
        if r.returncode:raise RuntimeError('Actual codec streaming graph failed: '+r.stdout+r.stderr)
        codec=json.loads(r.stdout.strip().splitlines()[-1])
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    current(inputs);report=dict(passed=java['passed']+native['passed']+layout['passed']+len(graphs)+audio['passed']+pcm['passed']+codec['passed'],java=java,native=native,layout=layout,incremental_audio=audio,native_pcm=pcm,codec_streaming=codec,actual_tiny_graphs=graphs,actual_graph_processes=len(graphs)+1,production_rq_binding=True,actual_host_children=True,model_inference=False,physical_android=False,generated_audio_outputs=False,structural_wav_fixture=True,input_fingerprint=inputs)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
