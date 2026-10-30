"""Production Java + actual Z-Image-Turbo worker: import, settings, jobs and results.

No downloads or simulated inference. --execute-only retains a nonaccepting capture;
--verify-run validates it against current direct evidence without another model run.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_zimage_trained import inputs as asset_inputs, sha, verify
from test_sd_variants_trained import image_stats

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint(
        'tools/test_zimage_app_host.py', 'tools/test_sd_variants_trained.py',
        'tests/zimage-trained', 'research/zimage_trained', 'app/src/main/java/com/lma/app/core',
        'app/src/main/java/com/lma/app/SdEngine.java', 'app/src/main/java/com/lma/app/NativeWorker.java',
        'app/src/main/java/com/lma/app/LocalEngine.java', 'tests/tts-host/com/lma/app/LmaApp.java',
        'tests/sd-host/com/lma/app/VideoEncoder.java', 'tests/host/android/util/AtomicFile.java',
        'app/src/main/assets/recipe-templates.json')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument('--execute-only',action='store_true')
    group.add_argument('--verify-run',help='Owned run folder with complete actual execution.json')
    args=parser.parse_args()
    if os.name!='nt': raise RuntimeError('Native Windows host only')
    before=inputs();verify();binary,compilation=build()
    parent=ROOT/'build/zimage-app-host-tests'
    if args.verify_run:
        folder=(ROOT/args.verify_run).resolve()
        if folder.parent!=parent.resolve() or not folder.name.startswith('run-'): raise ValueError('Not an owned capture folder')
        saved=json.loads((folder/'execution.json').read_text(encoding='utf-8'));current(saved['input_fingerprint'])
        if saved['input_fingerprint']!=before or saved['compilation']!=compilation: raise ValueError('Execution source/build changed')
        if saved['java_report_sha256']!=sha(folder/'data/java-results.json'): raise ValueError('Actual Java report changed')
        drive=saved['owned_alias']
        if drive not in [c+':' for c in 'TUVWXYZ']: raise ValueError('Unexpected capture alias')
    else:
        folder=parent/('run-'+str(time.time_ns()));classes=folder/'classes';classes.mkdir(parents=True)
        dependency=ROOT/'build/test-deps/json-20250517.jar'
        if sha(dependency)!='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':raise ValueError('Changed Java dependency')
        sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+sorted((ROOT/'tests/zimage-trained').rglob('*.java'))
        sources+=[ROOT/'app/src/main/java/com/lma/app'/(n+'.java') for n in ['SdEngine','NativeWorker','LocalEngine']]
        sources+=[ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/sd-host/com/lma/app/VideoEncoder.java',ROOT/'tests/host/android/util/AtomicFile.java']
        rsp=folder/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
        result=subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','8','-cp',str(dependency),'-d',str(classes),'@'+str(rsp)],capture_output=True,timeout=90)
        (folder/'compile.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Inspect retained actual Java compile log: '+str(folder.relative_to(ROOT)))
        drive=next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
        if not drive:raise RuntimeError('No free owned ASCII alias')
        subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
        try:
            def alias(path):return drive+'/'+path.relative_to(ROOT).as_posix()
            command=[shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-cp',str(classes)+os.pathsep+str(dependency),
                     'com.lma.app.ZImageTrainedAppTest',alias(folder/'data'),alias(ROOT/'build/zimage-trained/originals'),
                     alias(ROOT/'research/zimage_trained/catalogue-bundle.json'),alias(ROOT/'app/src/main/assets/recipe-templates.json'),alias(binary)]
            print('Import all four complete selected components; execute actual production Java/native jobs',flush=True)
            with (folder/'java.stdout').open('xb') as stdout,(folder/'java.stderr').open('xb') as stderr:
                result=subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=21600)
            if result.returncode:raise RuntimeError('Inspect retained actual Java/native logs: '+str(folder.relative_to(ROOT)))
        finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
        current(before)
        saved=dict(schema='lma.zimage-app-host-execution/1',actual_execution_completed=True,compilation=compilation,
                   owned_alias=drive,java_report_sha256=sha(folder/'data/java-results.json'),input_fingerprint=before,
                   direct_comparison_accepted=False,physical_android=False,complete_release_accepted=False)
        (folder/'execution.json').write_text(json.dumps(saved,indent=2)+'\n',encoding='utf-8')
        if args.execute_only:
            print(json.dumps(dict(capture_directory=folder.relative_to(ROOT).as_posix(),actual_execution_completed=True,direct_comparison_accepted=False)),flush=True);return
    java=json.loads((folder/'data/java-results.json').read_text(encoding='utf-8'))
    direct_path=ROOT/'build/zimage-trained-tests/results.json';direct=json.loads(direct_path.read_text(encoding='utf-8'));current(direct['input_fingerprint'])
    if not direct['host_execution_checks_passed']:raise ValueError('Direct trained host evidence has unresolved failures')
    reference=next(r for r in direct['runs'] if r['name']=='a')['image'];outputs=[]
    for run in java['runs']:
        if 'output' not in run:continue
        normalized=run['output'].replace('\\','/')
        if not normalized.startswith(drive+'/'):raise ValueError('Unexpected actual output alias')
        path=(ROOT/normalized[len(drive)+1:]).resolve();path.relative_to(folder.resolve());image=image_stats(path)
        if image['sha256']!=run['sha256'] or image['bytes']!=run['bytes']:raise ValueError('Actual output changed')
        if image['width']!=512 or image['height']!=512 or image['sha256']!=reference['sha256']:raise ValueError('Actual Java/direct output differs with identical parameters')
        outputs.append(dict(name=run['name'],file=path.relative_to(ROOT).as_posix(),image=image,bitwise_equal_to_direct_native=True))
    if len(outputs)!=2 or java['actual_host_children']!=3 or java['network_calls']!=0:raise ValueError('Incomplete actual Java lifecycle')
    current(before)
    files={p.relative_to(folder).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.rglob('*'))
           if p.is_file() and '/classes/' not in p.as_posix() and '/bundles/objects/' not in p.as_posix()}
    report=dict(schema='lma.zimage-app-host/1',capture_directory=folder.relative_to(ROOT).as_posix(),java=java,outputs=outputs,
                files=files,compilation=compilation,direct_trained_report_sha256=sha(direct_path),production_java_native_host_executed=True,
                physical_android=False,android_saf_tested=False,android_background_accepted=False,
                independent_numerics_accepted=False,image_quality_accepted=False,complete_target06_accepted=False,
                complete_release_accepted=False,input_fingerprint=before)
    for path in [folder/'results.json',parent/'results.json']:path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=java['passed'],actual_host_children=3,complete_objects=4,outputs=2,network_calls=0)),flush=True)


if __name__=='__main__':main()
