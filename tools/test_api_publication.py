"""Run production publication, retry journal and OpenAI facade checks through actual native sockets."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/api-publication-tests'


def main():
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dependency.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/ApiPublicationTest.java', 'tests/host/android/util/AtomicFile.java', 'tools/test_api_publication.py')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results.json').unlink(missing_ok=True)
    run = OUT / 'run'
    if run.exists():
        assert run.resolve().parent == OUT.resolve()
        shutil.rmtree(run)
    run.mkdir()
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/ApiPublicationTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    classes = OUT / 'classes'
    classes.mkdir(exist_ok=True)
    response = OUT / 'sources.rsp'
    response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@'+str(response)], cwd=ROOT, check=True)
    p = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp', str(classes)+os.pathsep+str(dependency), 'com.lma.app.core.ApiPublicationTest', str(run)], cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=90)
    (OUT/'output.txt').write_text(p.stdout+p.stderr, encoding='utf-8')
    if p.returncode:
        print(p.stderr)
        raise RuntimeError('Publication contract checks failed')
    result = json.loads(p.stdout.strip().splitlines()[-1])
    current(inputs)
    result['input_fingerprint'] = inputs
    (OUT/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('passed', 'actual_socket_io', 'model_inference_tested', 'physical_device')}))


if __name__ == '__main__':
    main()
