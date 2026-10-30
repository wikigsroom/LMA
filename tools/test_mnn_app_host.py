"""Run production Java user import/settings/cancellation/recovery with real Sana assets."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from build_mnn_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_mnn_trained import verify, inputs as asset_inputs, sha
from test_mnn_trained import image_stats, difference

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_mnn_app_host.py', 'tools/test_mnn_trained.py',
        'tests/mnn-trained', 'app/src/main/java/com/lma/app/core',
        'app/src/main/java/com/lma/app/MnnEngine.java', 'app/src/main/java/com/lma/app/NativeWorker.java',
        'app/src/main/java/com/lma/app/LocalEngine.java', 'tests/tts-host/com/lma/app/LmaApp.java',
        'tests/host/android/util/AtomicFile.java', 'app/src/main/assets/recipe-templates.json')}


def main():
    before = inputs(); verify(); binary, compilation = build()
    direct_path = ROOT / 'build/mnn-trained-tests/results.json'; direct = json.loads(direct_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint'])
    if not direct['passed']: raise ValueError('Complete the actual native component execution checks first')
    folder = ROOT / 'build/mnn-app-host-tests' / ('run-' + str(time.time_ns())); classes = folder / 'classes'; classes.mkdir(parents=True)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    if sha(dependency) != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796': raise ValueError('Different Java dependency')
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + sorted((ROOT / 'tests/mnn-trained').rglob('*.java'))
    sources += [ROOT / 'app/src/main/java/com/lma/app' / (n + '.java') for n in ['MnnEngine', 'NativeWorker', 'LocalEngine']]
    sources += [ROOT / 'tests/tts-host/com/lma/app/LmaApp.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    rsp = folder / 'sources.rsp'; rsp.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    result = subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '--release', '8',
                             '-cp', str(dependency), '-d', str(classes), '@' + str(rsp)], capture_output=True, timeout=90)
    (folder / 'compile.log').write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError('Inspect actual Sana Java compilation log: ' + str(folder.relative_to(ROOT)))
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        command = [shutil.which('java'), '-Dfile.encoding=UTF-8', '-Dstdout.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dependency),
                   'com.lma.app.MnnTrainedAppTest', alias(folder / 'data'), alias(ROOT / 'build/mnn-trained/originals'),
                   alias(ROOT / 'research/mnn_trained/assets.json'), alias(ROOT / 'app/src/main/assets/recipe-templates.json'), alias(binary)]
        print('Import all thirteen selected assets and execute production Java/native Sana pipeline', flush=True)
        result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=1200)
        (folder / 'java.stdout').write_bytes(result.stdout); (folder / 'java.stderr').write_bytes(result.stderr)
        if result.returncode: raise RuntimeError('Inspect actual Sana Java/native logs: ' + str(folder.relative_to(ROOT)))
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    java = json.loads((folder / 'data/java-results.json').read_text(encoding='utf-8')); outputs = []; comparisons = {}
    for run in java['runs']:
        if 'output' not in run: continue
        name = run['output'].replace('\\', '/')
        if not name.startswith(drive + '/'): raise ValueError('Output escaped owned alias')
        path = ROOT / name[len(drive) + 1:]; path.resolve().relative_to(folder.resolve())
        image = image_stats(path)
        if image['sha256'] != run['sha256'] or image['bytes'] != run['bytes'] or image['width'] != 512 or image['height'] != 512 or max(image['stddev']) <= 1:
            raise ValueError('Actual image identity, dimensions or nonuniform-pixel control differs')
        reference = next(i for i in direct['runs'] if i['name'] == ('cfg-a' if run['name'] == 'cfg' else 'a'))
        comparison = difference(ROOT / direct['capture_directory'] / (reference['name'] + '.png'), path)
        if comparison['maximum'] != 0: raise ValueError('Production Java and direct same-host pipeline differ: ' + run['name'])
        comparisons[run['name']] = comparison
        outputs.append(dict(name=run['name'], file=path.relative_to(ROOT).as_posix(), image=image))
    if len(outputs) != 3 or java['actual_host_children'] != 4 or java['network_calls'] != 0: raise ValueError('Incomplete real pipeline coverage')
    current(before); verify()
    report = dict(schema='lma.mnn-app-host/1', passed=True, java=java, compilation=compilation, outputs=outputs,
                  comparisons=comparisons, direct_report_sha256=sha(direct_path), capture_directory=folder.relative_to(ROOT).as_posix(),
                  production_java_native_host_executed=True, model_data_bundled=False, physical_android=False,
                  android_saf_tested=False, android_background_accepted=False, independent_reference_numerics_accepted=False,
                  image_quality_accepted=False, complete_target04_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    for path in [folder / 'results.json', folder.parent / 'results.json']:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=java['passed'], actual_host_children=java['actual_host_children'], imported_objects=13, outputs=len(outputs))), flush=True)


if __name__ == '__main__': main()
