"""Compile production Java contracts and native frontend; use synthetic GLB, no neural inference."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]

def main():
    inputs=fingerprint('app/src/main/java/com/lma/app/core','app/src/main/java/com/lma/app/ExpansionEngine.java',
        'app/src/main/java/com/lma/app/NativeWorker.java','native/speech_extra','native/worker_common.hpp','native/runtime_metrics.hpp',
        'tests/expansion-host','tests/expansion-native','tools/test_expansion.py','tools/expansion_catalogue.py',
        'catalogue/expansion-bundles.json','catalogue/expansion-bundle-evidence.json','research/expansion',
        'catalogue/multiview-bundles.json','catalogue/multiview-bundle-evidence.json','tools/multiview_catalogue.py','research/multiview')
    out=ROOT/'build/expansion-tests';out.mkdir(parents=True,exist_ok=True)
    run=out/'run'
    if run.exists():assert run.resolve().parent==out.resolve();shutil.rmtree(run)
    classes=out/'classes';classes.mkdir(exist_ok=True)
    dep=ROOT/'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dep.read_bytes()).hexdigest()=='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    sources=list((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+list((ROOT/'tests/expansion-host').rglob('*.java'))
    sources += [ROOT/'tests/host/android/util/AtomicFile.java',ROOT/'tests/tts-host/com/lma/app/LmaApp.java']
    sources += [ROOT/'app/src/main/java/com/lma/app'/(s+'.java') for s in ['LocalEngine','NativeWorker','ExpansionEngine']]
    rsp=out/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
    subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','8','-Xlint:-options','-cp',str(dep),'-d',str(classes),'@'+str(rsp)],check=True)
    command=[shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dstderr.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dep),'com.lma.app.ExpansionTest',str(ROOT),str(run)]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    java=json.loads(result.stdout.strip().splitlines()[-1])
    # MSVC native host, no emulator. This tiny executable contains no model or learned tensors.
    setup=r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
    alias=None
    for letter in 'UVWXYZT':
        if not Path(letter+':/').exists() and subprocess.run(['subst',letter+':',str(ROOT)],capture_output=True).returncode==0:alias=letter+':';break
    assert alias
    try:
        cmd=out/'frontend.cmd';cmd.write_text('@echo off\ncall "'+setup+'" >nul\ncl /nologo /std:c++17 /utf-8 /EHsc /O2 /I '+alias+'/build/native-src/sd-cpp/thirdparty /Fe:'+alias+'/build/expansion-tests/frontend.exe /Fo:'+alias+'/build/expansion-tests/frontend.obj '+alias+'/tests/expansion-native/frontend.cpp\n',encoding='utf-8')
        compiled=subprocess.run(['cmd','/d','/c',str(cmd)],capture_output=True)
        (out/'native-build.log').write_bytes(compiled.stdout+compiled.stderr)
        assert compiled.returncode==0,'Inspect build/expansion-tests/native-build.log'
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    native=json.loads(subprocess.check_output([str(out/'frontend.exe')],text=True,encoding='utf-8'))
    report=dict(passed=java['passed']+native['passed'],java=java,native=native,model_inference=False,complete_model_downloads=0,physical_device=False,input_fingerprint=inputs)
    current(inputs);(out/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
