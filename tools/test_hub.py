"""Check production HF discovery against deterministic host fixtures and optional live public APIs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Also query live HF mirror metadata through the production client')
    args = parser.parse_args()
    out = ROOT / 'build/hub-tests'
    out.mkdir(parents=True, exist_ok=True)
    backend = json.loads((ROOT / 'build/backend-tests/results.json').read_text(encoding='utf-8'))
    current(backend['input_fingerprint'])
    inputs = fingerprint('app/src/main/java', 'tests/host', 'app/src/main/assets/recipe-templates.json', 'tools/test_hub.py')
    classes = ROOT / 'build/backend-tests/classes'
    dep = ROOT / 'build/test-deps/json-20250517.jar'
    def run(name):
        subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dep), 'com.lma.app.' + name, str(ROOT)], cwd=ROOT, check=True, timeout=180)
    run('HubTest')
    for name in ['results.json']:
        record = json.loads((out / name).read_text(encoding='utf-8')); record['input_fingerprint'] = inputs
        (out / name).write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.live:
        run('HubLiveTest')
        record = json.loads((out / 'live-results.json').read_text(encoding='utf-8')); record['input_fingerprint'] = inputs
        (out / 'live-results.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    current(inputs)


if __name__ == '__main__':
    main()
