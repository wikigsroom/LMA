"""Validate community source metadata, production Java contracts and content provenance offline."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import current, fingerprint
from community_catalogue import build

ROOT = Path(__file__).resolve().parents[1]


def main():
    build()
    inputs = fingerprint('tools/community_catalogue.py', 'tools/test_community.py', 'catalogue/community-sources.json',
        'catalogue/community-bundles.json', 'catalogue/community-bundle-evidence.json', 'research/community',
        'app/src/main/java', 'tests/community', 'app/src/main/assets/model-bundles.json', 'app/src/main/assets/recipe-templates.json')
    backend = json.loads((ROOT / 'build/backend-tests/results.json').read_text(encoding='utf-8'))
    current(backend['input_fingerprint'])
    evidence = json.loads((ROOT / 'research/community/metadata.json').read_text(encoding='utf-8'))
    spec = json.loads((ROOT / 'catalogue/community-sources.json').read_text(encoding='utf-8'))
    assert evidence['sourceSpecSha256'] == hashlib.sha256((ROOT / 'catalogue/community-sources.json').read_bytes()).hexdigest()
    count = 0
    for source in spec['repositories']:
        checked = evidence['repositories'][source['repository']]
        assert checked['cardMarkers'] == source['cardMarkers']
        for variant in source['variants']:
            file = checked['files'][variant['file']]
            assert file['bytes'] > 0 and len(file['sha256']) == 64 and file['header']['bytes'] <= 4*1024*1024
            assert not file['header']['trainedWeightBytesFetched'] and not file['header']['inferenceTested']
            count += 2
    out = ROOT / 'build/community-tests'; out.mkdir(parents=True, exist_ok=True)
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    dependencies = os.pathsep.join([str(ROOT / 'build/backend-tests/classes'), str(ROOT / 'build/test-deps/json-20250517.jar')])
    subprocess.run([shutil.which('javac'), '-encoding', 'UTF-8', '--release', '8', '-cp', dependencies, '-d', str(classes), str(ROOT / 'tests/community/CommunityTest.java')], check=True)
    result = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp', str(classes) + os.pathsep + dependencies,
        'com.lma.app.CommunityTest', str(ROOT)], capture_output=True, text=True, encoding='utf-8', check=True, timeout=90)
    report = json.loads(result.stdout.strip().splitlines()[-1]); report['javaChecks'] = report['passed']; report['passed'] += count
    report.update(metadataChecks=count, completeModelDownloads=0, browserUsed=False, input_fingerprint=inputs)
    (out / 'results.json').write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in report.items() if k != 'input_fingerprint'}))
    current(inputs)


if __name__ == '__main__': main()
