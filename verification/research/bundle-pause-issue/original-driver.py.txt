"""Exercise production pause/shutdown against actual blocking local input streams."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    before = fingerprint('app/src/main/java/com/lma/app/core', 'tests/BundlePauseTest.java',
                         'tests/host/android/util/AtomicFile.java', 'tools/test_bundle_pause.py')
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert sha(dependency) == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    folder = ROOT / 'build/bundle-pause-tests' / ('run-' + str(time.time_ns()))
    classes = folder / 'classes'
    classes.mkdir(parents=True)
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java'))
    sources += [ROOT / 'tests/BundlePauseTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    response = folder / 'sources.rsp'
    response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    compiled = subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8',
        '--release', '8', '-cp', str(dependency), '-d', str(classes), '@' + str(response)], capture_output=True, timeout=60)
    (folder / 'compile.log').write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise RuntimeError('Inspect bundle-pause compilation: ' + str(folder.relative_to(ROOT)))
    run = folder / 'data'
    run.mkdir()
    result = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp',
        str(classes) + os.pathsep + str(dependency), 'com.lma.app.BundlePauseTest', str(run)], capture_output=True, timeout=30)
    (folder / 'stdout.txt').write_bytes(result.stdout)
    (folder / 'stderr.txt').write_bytes(result.stderr)
    current(before)
    checks = json.loads(result.stdout.strip().splitlines()[-1]) if result.returncode == 0 else None
    report = dict(schema='lma.bundle-pause-contract/1', passed=result.returncode == 0,
        checks=checks, returncode=result.returncode, input_fingerprint=before,
        capture_directory=folder.relative_to(ROOT).as_posix(), physical_android=False,
        model_inference=False, network_requests=0)
    for path in [folder / 'results.json', folder.parent / 'results.json']:
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], checks=checks, capture_directory=report['capture_directory'])))
    if result.returncode:
        print(result.stderr.decode('utf-8', errors='replace'))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
