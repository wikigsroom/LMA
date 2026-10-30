"""Verify task interrupted output recovery and bounded history and actual authenticated HTTP using production Java."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]


def main():
    dep = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dep.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/TaskRecoveryTest.java', 'tests/host/android/util/AtomicFile.java', 'tools/test_recovery.py')
    out = ROOT / 'build/recovery-tests'; out.mkdir(exist_ok=True)
    (out / 'results.json').unlink(missing_ok=True)
    run = out / 'run'
    if run.exists():
        assert run.resolve().parent == out.resolve()
        shutil.rmtree(run)
    run.mkdir()
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/TaskRecoveryTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    rsp = out / 'sources.rsp'; rsp.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '--release', '11', '-cp', str(dep), '-d', str(classes), '@' + str(rsp)], cwd=ROOT, check=True)
    # Record real host phase timing without changing the existing 90-second deadline.
    started = time.monotonic()
    completed = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dep), 'com.lma.app.TaskRecoveryTest', str(run)], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=90)
    (out / 'output.txt').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    if completed.returncode: raise RuntimeError(completed.stdout + completed.stderr)
    report = json.loads(completed.stdout.strip().splitlines()[-1]); report['host_elapsed_seconds'] = time.monotonic() - started; current(inputs); report['input_fingerprint'] = inputs
    (out / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'input_fingerprint')}))


if __name__ == '__main__': main()
