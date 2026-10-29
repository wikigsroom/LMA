"""Run actual production Java asset import, settings and trained native worker on Windows."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from build_moss_nano_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_moss_nano_trained import verify
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **fingerprint('tools/test_moss_nano_app_host.py', 'tests/nano-trained',
        'app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/MossNanoEngine.java',
        'app/src/main/java/com/lma/app/NativeWorker.java', 'app/src/main/java/com/lma/app/LocalEngine.java',
        'tests/tts-host/com/lma/app/LmaApp.java', 'tests/host/android/util/AtomicFile.java',
        'catalogue/moss-nano-100m-onnx.bundle.json', 'research/moss_nano_trained/assets.json')}


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows only')
    before = inputs(); verify(); binary, compilation = build()
    direct_path = ROOT / 'build/moss-nano-trained-tests/results.json'; direct = json.loads(direct_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint'])
    if not direct['host_execution_checks_passed']: raise ValueError('Complete actual direct worker checks first')
    expected = next(x['audio']['sha256'] for x in direct['jobs'] if x['name'] == 'prompt-a')
    output = ROOT / 'build/moss-nano-app-host-tests' / ('run-' + str(time.time_ns())); classes = output / 'classes'; classes.mkdir(parents=True)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    if sha(dependency) != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796': raise ValueError('Changed Java dependency')
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + sorted((ROOT / 'tests/nano-trained').rglob('*.java'))
    sources += [ROOT / 'app/src/main/java/com/lma/app' / (name + '.java') for name in ['MossNanoEngine', 'NativeWorker', 'LocalEngine']]
    sources += [ROOT / 'tests/tts-host/com/lma/app/LmaApp.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    response = output / 'sources.rsp'; response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    result = subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8',
        '-cp', str(dependency), '-d', str(classes), '@' + str(response)], capture_output=True, timeout=90)
    (output / 'compile.log').write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError('Inspect Nano trained Java compilation log')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII test alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        command = [shutil.which('java'), '-Dfile.encoding=UTF-8', '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', '-Duser.language=en',
            '-cp', alias(classes) + os.pathsep + alias(dependency), 'com.lma.app.NanoTrainedAppTest', alias(output / 'data'),
            alias(ROOT / 'build/moss-nano-trained/originals'), alias(ROOT / 'catalogue/moss-nano-100m-onnx.bundle.json'), alias(binary), expected]
        print('Import full Nano assets and execute actual production Java/native binding', flush=True)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=600)
        (output / 'java.stdout').write_bytes(result.stdout); (output / 'java.stderr').write_bytes(result.stderr)
        if result.returncode: raise RuntimeError('Inspect actual Nano Java/native host execution logs: ' + str(output.relative_to(ROOT)))
    finally: subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    java = json.loads((output / 'data/java-results.json').read_text(encoding='utf-8')); current(before)
    outputs = []
    for run in java['runs']:
        if 'output' in run:
            normalized = run['output'].replace('\\', '/')
            if not normalized.startswith(drive + '/'): raise ValueError('Output escaped owned test alias')
            path = (ROOT / normalized[len(drive) + 1:]).resolve()
            path.relative_to(output.resolve())
            if path.stat().st_size != run['bytes'] or sha(path) != run['sha256'] or run['sha256'] != expected: raise ValueError('Changed actual Java-produced audio')
            outputs.append(dict(file=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size, sha256=sha(path)))
    report = dict(schema='lma.moss-nano-app-host/1', java=java, compilation=compilation, outputs=outputs,
        direct_trained_report_sha256=sha(direct_path), standalone_bundle_sha256=sha(ROOT / 'catalogue/moss-nano-100m-onnx.bundle.json'),
        capture_directory=output.relative_to(ROOT).as_posix(), production_java_native_host_executed=True,
        physical_android=False, android_saf_tested=False, android_background_accepted=False,
        speech_quality_accepted=False, complete_target09_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    for path in [output / 'results.json', output.parent / 'results.json']: path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=java['passed'], actual_host_children=java['actual_host_children'], imported_components=java['imported_components'], outputs=len(outputs))), flush=True)


if __name__ == '__main__': main()
