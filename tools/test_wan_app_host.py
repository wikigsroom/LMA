"""Production Java + actual Wan Vulkan worker: import, settings, jobs and results.

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

from build_sd_vulkan import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_wan_trained import inputs as asset_inputs, sha, verify
from test_wan_trained import frame_stats

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint(
        'tools/test_wan_app_host.py', 'tools/test_wan_trained.py',
        'tests/wan-trained', 'research/wan_trained', 'app/src/main/java/com/lma/app/core',
        'app/src/main/java/com/lma/app/SdEngine.java', 'app/src/main/java/com/lma/app/NativeWorker.java',
        'app/src/main/java/com/lma/app/LocalEngine.java', 'tests/tts-host/com/lma/app/LmaApp.java',
        'tests/host/android/util/AtomicFile.java',
        'app/src/main/assets/recipe-templates.json')}


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument('--execute-only',action='store_true')
    group.add_argument('--verify-run',help='Owned run folder with complete actual execution.json')
    args=parser.parse_args()
    ffmpeg=Path(shutil.which('ffmpeg') or '').resolve()
    if not ffmpeg.is_file():raise RuntimeError('Native Windows FFmpeg is required for host media evidence')
    if os.name!='nt': raise RuntimeError('Native Windows host only')
    before=inputs();encoder_info=dict(sha256=sha(ffmpeg),bytes=ffmpeg.stat().st_size);verify();binary,compilation=build()
    parent=ROOT/'build/wan-app-host-tests'
    if args.verify_run:
        folder=(ROOT/args.verify_run).resolve()
        if folder.parent!=parent.resolve() or not folder.name.startswith('run-'): raise ValueError('Not an owned capture folder')
        saved=json.loads((folder/'execution.json').read_text(encoding='utf-8'));current(saved['input_fingerprint'])
        if saved['host_encoder']!=encoder_info:raise ValueError('Host encoder changed')
        if saved['input_fingerprint']!=before or saved['compilation']!=compilation: raise ValueError('Execution source/build changed')
        if saved['java_report_sha256']!=sha(folder/'data/java-results.json'): raise ValueError('Actual Java report changed')
        drive=saved['owned_alias']
        if drive not in [c+':' for c in 'TUVWXYZ']: raise ValueError('Unexpected capture alias')
    else:
        folder=parent/('run-'+str(time.time_ns()));classes=folder/'classes';classes.mkdir(parents=True)
        dependency=ROOT/'build/test-deps/json-20250517.jar'
        if sha(dependency)!='3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':raise ValueError('Changed Java dependency')
        sources=sorted((ROOT/'app/src/main/java/com/lma/app/core').glob('*.java'))+sorted((ROOT/'tests/wan-trained').rglob('*.java'))
        sources+=[ROOT/'app/src/main/java/com/lma/app'/(n+'.java') for n in ['SdEngine','NativeWorker','LocalEngine']]
        sources+=[ROOT/'tests/tts-host/com/lma/app/LmaApp.java',ROOT/'tests/host/android/util/AtomicFile.java']
        rsp=folder/'sources.rsp';rsp.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources),encoding='utf-8')
        result=subprocess.run([shutil.which('javac'),'-encoding','UTF-8','--release','8','-cp',str(dependency),'-d',str(classes),'@'+str(rsp)],capture_output=True,timeout=90)
        (folder/'compile.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError('Inspect retained actual Java compile log: '+str(folder.relative_to(ROOT)))
        drive=next((c+':' for c in 'UVWXYZT' if not Path(c+':/').exists()),None)
        if not drive:raise RuntimeError('No free owned ASCII alias')
        subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
        try:
            def alias(path):return drive+'/'+path.relative_to(ROOT).as_posix()
            command=[shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dlma.host.ffmpeg='+str(ffmpeg),'-cp',str(classes)+os.pathsep+str(dependency),
                     'com.lma.app.WanTrainedAppTest',alias(folder/'data'),alias(ROOT/'build/wan-trained/originals'),
                     alias(ROOT/'research/wan_trained/catalogue-bundle.json'),alias(ROOT/'app/src/main/assets/recipe-templates.json'),alias(binary)]
            print('Import all four complete selected components; execute actual production Java/native jobs',flush=True)
            with (folder/'java.stdout').open('xb') as stdout,(folder/'java.stderr').open('xb') as stderr:
                result=subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=21600)
            if result.returncode:raise RuntimeError('Inspect retained actual Java/native logs: '+str(folder.relative_to(ROOT)))
        finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
        current(before)
        if sha(ffmpeg)!=encoder_info['sha256']:raise ValueError('Host encoder changed')
        saved=dict(schema='lma.wan-app-host-execution/1',actual_execution_completed=True,compilation=compilation,
                   owned_alias=drive,java_report_sha256=sha(folder/'data/java-results.json'),host_encoder=encoder_info,input_fingerprint=before,
                   direct_comparison_accepted=False,physical_android=False,complete_release_accepted=False)
        (folder/'execution.json').write_text(json.dumps(saved,indent=2)+'\n',encoding='utf-8')
        if args.execute_only:
            print(json.dumps(dict(capture_directory=folder.relative_to(ROOT).as_posix(),actual_execution_completed=True,direct_comparison_accepted=False)),flush=True);return
    java=json.loads((folder/'data/java-results.json').read_text(encoding='utf-8'))
    direct_path=ROOT/'build/wan-trained-tests/results.json';direct=json.loads(direct_path.read_text(encoding='utf-8'));current(direct['input_fingerprint'])
    if not direct['host_execution_checks_passed']:raise ValueError('Direct trained host evidence has unresolved failures')
    reference=next(r for r in direct['runs'] if r['name']=='a')['frames'];outputs=[]
    if len(java['host_encoder_receipts'])!=2:raise ValueError('Missing real native host encoder receipts')
    for run,encoded in zip([r for r in java['runs'] if 'output' in r],java['host_encoder_receipts']):
        normalized=run['output'].replace('\\','/')
        if not normalized.startswith(drive+'/'):raise ValueError('Unexpected actual output alias')
        path=(ROOT/normalized[len(drive)+1:]).resolve();path.relative_to(folder.resolve())
        if sha(path)!=run['sha256'] or path.stat().st_size!=run['bytes'] or sha(path)!=encoded['output_sha256']:raise ValueError('Actual output changed')
        if encoded['input_raw_sha256']!=reference['sha256']:raise ValueError('Actual Java/direct raw frames differ with identical parameters')
        probe=Path(shutil.which('ffprobe') or '').resolve()
        if not probe.is_file():raise RuntimeError('Native FFprobe is required')
        result=subprocess.run([str(probe),'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,width,height,nb_read_frames,r_frame_rate','-of','json',str(path)],capture_output=True,check=True,timeout=60)
        media=json.loads(result.stdout)['streams'][0]
        if media.get('codec_name')!='h264' or (media.get('width'),media.get('height'),media.get('nb_read_frames'),media.get('r_frame_rate'))!=(256,256,'5','8/1'):raise ValueError('Actual encoded video geometry differs')
        outputs.append(dict(name=run['name'],file=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path),media=media,raw_frames_bitwise_equal_to_direct_native=True,host_ffmpeg=True,android_codec_tested=False))
    if len(outputs)!=2 or java['actual_host_children']!=3 or java['network_calls']!=0:raise ValueError('Incomplete actual Java lifecycle')
    current(before)
    if sha(ffmpeg)!=encoder_info['sha256']:raise ValueError('Host encoder changed')
    files={p.relative_to(folder).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.rglob('*'))
           if p.is_file() and '/classes/' not in p.as_posix() and '/bundles/objects/' not in p.as_posix()}
    report=dict(schema='lma.wan-app-host/1',capture_directory=folder.relative_to(ROOT).as_posix(),java=java,outputs=outputs,
                files=files,compilation=compilation,direct_trained_report_sha256=sha(direct_path),production_java_native_host_executed=True,
                physical_android=False,android_saf_tested=False,android_background_accepted=False,
                independent_numerics_accepted=False,video_quality_accepted=False,complete_target16_accepted=False,android_codec_tested=False,host_ffmpeg=True,
                complete_release_accepted=False,host_encoder=encoder_info,input_fingerprint=before)
    for path in [folder/'results.json',parent/'results.json']:path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=java['passed'],actual_host_children=3,complete_objects=4,outputs=2,network_calls=0)),flush=True)


if __name__=='__main__':main()
