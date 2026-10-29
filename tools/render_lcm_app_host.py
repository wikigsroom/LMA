"""Publish only verified current Windows production-binding PNGs, never model data."""
import json
from pathlib import Path
from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'build/lcm-app-host-tests/results.json'
    report=json.loads(source.read_text(encoding='utf-8'));current(report['input_fingerprint'])
    assert report['passed'] and not report['physical_android'] and len(report['outputs'])==2
    destination=ROOT/'docs/media/development/lcm-app-trained';destination.mkdir(exist_ok=True)
    files=[]
    for item in report['outputs']:
        original=(ROOT/item['path']).resolve();original.relative_to((ROOT/report['capture_directory']).resolve())
        assert original.suffix=='.png' and sha(original)==item['image']['sha256'] and original.stat().st_size==item['image']['bytes']
        name=item['name']+'.png';target=destination/name;target.write_bytes(original.read_bytes())
        files.append(dict(file=name,bytes=target.stat().st_size,sha256=sha(target),source=item['path']))
    record=dict(schema='lma.lcm-app-trained-media/1',actual_production_java_native_host=True,physical_android=False,
        model_inference=True,image_quality_accepted=False,historical_pixel_comparison_passed=False,
        trained_report_sha256=sha(source),files=files,input_fingerprint=report['input_fingerprint']|fingerprint('tools/render_lcm_app_host.py'))
    (destination/'manifest.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,actual_host_pngs=len(files),physical_android=False,image_quality_accepted=False)))


if __name__=='__main__':main()
