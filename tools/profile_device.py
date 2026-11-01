"""Bounded zero-model performance profiling on an authorized physical Android device."""
import argparse,datetime,hashlib,json,re,subprocess
from pathlib import Path
from evidence import ROOT,current,fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--label',required=True,choices=['baseline','optimized'])
    parser.add_argument('--existing-models',action='store_true',help='Measure idle UI with installed assets preserved; no generation')
    args=parser.parse_args()
    adb=Path('C:/Users/carzy/AppData/Local/Android/Sdk/platform-tools/adb.exe')
    def run(*values,timeout=60):
        return subprocess.run([str(adb),'-s',args.serial,*map(str,values)],cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',check=True,timeout=timeout).stdout
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    acceptance=json.loads((ROOT/'build/device-tests/acceptance-build.json').read_text('utf8'))
    current(acceptance['input_fingerprint'])
    assert acceptance['applicationApkSha256']==build['sha256']
    assert hashlib.sha256((ROOT/acceptance['apk']).read_bytes()).hexdigest()==acceptance['sha256']
    run('install','-r',acceptance['apk'],timeout=150)
    raw=run('shell','am','instrument','-w','-e','allow_existing_models',str(args.existing_models).lower(),'com.lma.app.acceptance/com.lma.app.DevicePerformance',timeout=240)
    match=re.search(r'INSTRUMENTATION_RESULT: lma_performance=(\{[^\r\n]+\})',raw)
    assert match,'No structured performance result'
    data=json.loads(match.group(1))
    assert data['status']=='passed',data.get('error','Performance instrumentation failed')
    assert data['version']==build['version']
    data.update(schema='lma.physical-ui-performance/1',label=args.label,apk_sha256=build['sha256'],
        checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        input_fingerprint=fingerprint('tests/android/com/lma/app/DevicePerformance.java','tools/profile_device.py'),
        measurement_scope=('Repeated warm idle snapshots and UI updates with existing assets preserved' if args.existing_models else 'Repeated warm zero-model snapshots and UI updates')+'; not FPS, trained-model performance or sustained endurance')
    out=ROOT/'build/device-tests'/('performance-'+args.label+'.json')
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(data,ensure_ascii=False))


if __name__=='__main__':main()
