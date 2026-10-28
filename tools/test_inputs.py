"""Exercise actual input files, production WAV/storage contracts and authenticated chunked HTTP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]


def main():
    dep = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dep.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/InputTest.java', 'tests/host/android/util/AtomicFile.java', 'tools/test_inputs.py')
    out = ROOT / 'build/input-tests'; out.mkdir(exist_ok=True)
    (out / 'results.json').unlink(missing_ok=True)
    run = out / 'run'
    if run.exists():
        assert run.resolve().parent == out.resolve()
        shutil.rmtree(run)
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/InputTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    rsp = out / 'sources.rsp'; rsp.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dep), '-d', str(classes), '@' + str(rsp)], cwd=ROOT, check=True)
    command = [shutil.which('java'), '-Dsun.net.http.allowRestrictedHeaders=true', '-Dfile.encoding=UTF-8', '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dep), 'com.lma.app.InputTest', str(run)]
    done = subprocess.run(command, cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=90)
    (out / 'output.txt').write_text(done.stdout + done.stderr, encoding='utf-8')
    if done.returncode:
        raise RuntimeError(done.stdout + done.stderr)
    report = json.loads(done.stdout.strip().splitlines()[-1]); current(inputs); report['input_fingerprint'] = inputs
    (out / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks', 'input_fingerprint')}))


if __name__ == '__main__': main()
