"""Compile unchanged production protocol/transport against bounded socket fixtures; no inference."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/openai-tools-tests'

def main():
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dependency.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/OpenAiToolsTest.java', 'tests/host/android/util/AtomicFile.java', 'tools/test_openai_tools.py')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'results.json').unlink(missing_ok=True)
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/OpenAiToolsTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    response = OUT / 'sources.rsp'
    response.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources), encoding='utf-8')
    classes = OUT / 'classes'
    classes.mkdir(exist_ok=True)
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@'+str(response)], cwd=ROOT, check=True)
    result = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp', str(classes)+os.pathsep+str(dependency), 'com.lma.app.core.OpenAiToolsTest'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
    (OUT / 'output.txt').write_text(result.stdout+result.stderr, encoding='utf-8')
    if result.returncode:
        print(result.stderr)
        raise RuntimeError('OpenAI function-tool contract checks failed')
    data = json.loads(result.stdout.strip().splitlines()[-1]); current(inputs); data['input_fingerprint'] = inputs
    (OUT / 'results.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:data[k] for k in ('passed','actual_socket_io','model_inference_tested','physical_device')}))

if __name__ == '__main__':
    main()
