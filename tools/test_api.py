"""Exercise the production authenticated gateway with real native-host sockets and durable stores."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/api-tests'


def main():
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    if hashlib.sha256(dependency.read_bytes()).hexdigest() != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796':
        raise RuntimeError('Run tools/test_backend.py for the pinned host JSON dependency')
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/ApiTest.java', 'tests/host/android/util/AtomicFile.java', 'tools/test_api.py')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results.json').unlink(missing_ok=True)
    run = OUT / 'run'
    if run.exists():
        assert run.resolve().parent == OUT.resolve()
        shutil.rmtree(run)
    run.mkdir()
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java'))
    sources += [ROOT / 'tests/ApiTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    classes = OUT / 'classes'
    classes.mkdir(exist_ok=True)
    response = OUT / 'sources.rsp'
    response.write_text('\n'.join('"' + path.as_posix() + '"' for path in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@' + str(response)], cwd=ROOT, check=True)
    completed = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-Dsun.net.useExclusiveBind=false', '-cp', str(classes) + os.pathsep + str(dependency), 'com.lma.app.ApiTest', str(run)], cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=75)
    (OUT / 'output.txt').write_text(completed.stdout + completed.stderr, encoding='utf-8')
    if completed.returncode:
        print(completed.stderr)
        raise RuntimeError('Gateway checks failed')
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    current(inputs)
    result['input_fingerprint'] = inputs
    (OUT / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'actual_socket_io': True, 'android_execution_tested': False, 'model_inference_tested': False}))


if __name__ == '__main__':
    main()
