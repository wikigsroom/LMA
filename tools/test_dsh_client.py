"""Optional pinned DSH client interoperability audit. No ADB, downloads, trained models or client tools."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile
from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/dsh-client-verification'
LOCK = ROOT / 'tests/dsh-client-lock.json'


def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def extract(apk, lock):
    assert apk.stat().st_size == lock['apk_bytes'] and digest(apk) == lock['apk_sha256'], 'DSH APK differs from the pinned installed client'
    OUT.mkdir(parents=True, exist_ok=True)
    runtime = OUT / 'runtime.zip'
    if not runtime.is_file() or digest(runtime) != lock['runtime_sha256']:
        with zipfile.ZipFile(apk) as package, package.open('assets/runtime.zip') as source, runtime.open('wb') as target:
            shutil.copyfileobj(source, target)
    assert runtime.stat().st_size == lock['runtime_bytes'] and digest(runtime) == lock['runtime_sha256']
    target_root = OUT / 'dsh-runtime-src'
    with zipfile.ZipFile(runtime) as package:
        for member in package.infolist():
            path = PurePosixPath(member.filename)
            # Only static modules needed by the codec; never extract/inspect protected files or execute the app.
            if not member.filename.startswith('lib/node_modules/') or member.is_dir() or path.suffix not in ('.js', '.mjs', '.cjs', '.json'):
                continue
            if path.name in ('foundation.js', 'license.js') or path.name.endswith('.header.json') or 'devtools' in path.parts:
                continue
            assert not path.is_absolute() and '..' not in path.parts
            target = target_root.joinpath(*path.parts)
            data = package.read(member)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.is_file() or target.read_bytes() != data:
                target.write_bytes(data)
    return target_root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, default=OUT / 'dsh-installed.apk', help='Explicitly obtained local DSH 1.4.76 APK; never downloaded by this test')
    parser.add_argument('--node', default=shutil.which('node'))
    args = parser.parse_args()
    assert args.apk.is_file(), 'Provide --apk for the pinned, legitimately obtained DSH APK (not included in LMA)'
    assert args.node, 'Node.js 22+ is required'
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    runtime = extract(args.apk.resolve(), lock)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert digest(dependency) == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/DshClientFixture.java', 'tests/dsh-client-runtime.mjs', 'tests/dsh-client-lock.json', 'tests/host/android/util/AtomicFile.java', 'tools/test_dsh_client.py')
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/DshClientFixture.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    classes = OUT / 'classes'
    classes.mkdir(exist_ok=True)
    response = OUT / 'sources.rsp'
    response.write_text('\n'.join('"' + path.as_posix() + '"' for path in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@' + str(response)], cwd=ROOT, check=True)
    report = OUT / 'client-results.json'
    report.unlink(missing_ok=True)
    command = [args.node, str(ROOT / 'tests/dsh-client-runtime.mjs'), str(runtime), str(OUT), shutil.which('java'), str(classes) + os.pathsep + str(dependency)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=150)
    (OUT / 'client-output.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError('Actual DSH client compatibility audit failed')
    data = json.loads(report.read_text(encoding='utf-8'))
    current(inputs)
    data.update(input_fingerprint=inputs, client=lock)
    report.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: data[key] for key in ('passed', 'tool_schema_variants', 'unique_tool_names', 'actual_client_code', 'actual_socket_io', 'physical_device', 'model_inference_tested')}))


if __name__ == '__main__':
    main()
