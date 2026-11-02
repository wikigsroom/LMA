"""Bounded physical UI font sweep; restores the user's font setting in finally."""
import argparse, json, os, re, subprocess, time
from pathlib import Path
from evidence import ROOT, fingerprint, version


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serial',required=True);args=parser.parse_args()
    adb=Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe'
    def run(*a,timeout=150):
        p=subprocess.run([str(adb),'-s',args.serial,*map(str,a)],capture_output=True,timeout=timeout)
        if p.returncode:raise RuntimeError('Physical font operation failed')
        return p.stdout.decode('utf8',errors='replace')
    original=run('shell','settings','get','system','font_scale').strip()
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    apk=run('shell','pm','path','com.lma.app').strip().removeprefix('package:')
    assert run('shell','sha256sum',apk).split()[0]==build['sha256']
    private=ROOT/'build/mica-v100';private.mkdir(parents=True,exist_ok=True)
    records=[];restored=False
    try:
        for scale in (1.3,1.5,2.0):
            run('shell','settings','put','system','font_scale',scale);time.sleep(1)
            raw=run('shell','am','instrument','-w','-e','mode','fonts','com.lma.app.acceptance/com.lma.app.DeviceUiProbe')
            (private/('font-'+str(scale)+'-private.txt')).write_text(raw,'utf8')
            match=re.search(r'lma_ui=(\{[^\r\n]+\})',raw);assert match,'Missing physical font result'
            data=json.loads(match.group(1));assert data['status']=='passed',data.get('error')
            records.append(dict(font_scale=scale,status='passed',checks=data['checks'],passed=len(data['checks'])))
            print(json.dumps(dict(font_scale=scale,passed=len(data['checks']))),flush=True)
    finally:
        if original=='null':run('shell','settings','delete','system','font_scale')
        else:run('shell','settings','put','system','font_scale',original)
        restored=run('shell','settings','get','system','font_scale').strip()==original
    assert restored
    record=dict(schema='lma.mica-physical-fonts/1',version=version(),apk_sha256=build['sha256'],physicalDevice=True,modelInference=False,restored=restored,runs=records,
        input_fingerprint=fingerprint('tools/probe_mica_fonts.py','tests/android/com/lma/app/DeviceUiProbe.java','app/src/main/java/com/lma/app/MainActivity.java','app/src/main/assets/mica.css','app/src/main/assets/mica.js'))
    out=ROOT/'verification/releases'/('v'+version())/'mica-fonts.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n','utf8')


if __name__=='__main__':main()
