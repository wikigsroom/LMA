"""Check production cancellable document opening with explicit host Android ports."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java'))
    sources += sorted((ROOT / 'tests/document-input').rglob('*.java'))
    sources += [ROOT / name for name in ('app/src/main/java/com/lma/app/DocumentInput.java',
                'tests/host/android/net/Uri.java', 'tests/host/android/util/AtomicFile.java')]
    inputs = fingerprint(*(str(path.relative_to(ROOT)) for path in sources), 'tools/test_document_input.py')
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dependency.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    out = ROOT / 'build/document-input-tests'; out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').unlink(missing_ok=True)
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    rsp = out / 'sources.rsp'; rsp.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    compiled = subprocess.run([shutil.which('javac'), '-encoding', 'UTF-8', '--release', '8', '-cp', str(dependency),
        '-d', str(classes), '@' + str(rsp)], capture_output=True, timeout=60)
    (out / 'compile.log').write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode: raise RuntimeError('Inspect build/document-input-tests/compile.log')
    result = subprocess.run([shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dependency),
        'com.lma.app.DocumentInputTest'], capture_output=True, timeout=20)
    (out / 'output.txt').write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    report = json.loads(result.stdout.strip()); current(inputs); report['input_fingerprint'] = inputs
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key != 'input_fingerprint'}))


if __name__ == '__main__': main()
