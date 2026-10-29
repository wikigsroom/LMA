"""Exercise production HF selection, complete local import and real SD-Turbo Java/native inference.

Developer Windows CPU evidence only; no downloads, Android application or phone acceptance.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import asset_path as sd15_path, bundle, sha
from fetch_sd_distilled_trained import asset_path, selected, inputs as asset_inputs
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint(
        'tools/test_sd_turbo_app_host.py', 'tools/test_sd_variants_trained.py',
        'research/sd_distilled_trained/sd_turbo_q8_0.json', 'tests/sd-distilled', 'tests/sd-trained',
        'app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/SdEngine.java',
        'app/src/main/java/com/lma/app/NativeWorker.java', 'app/src/main/java/com/lma/app/LocalEngine.java',
        'tests/tts-host/com/lma/app/LmaApp.java', 'tests/sd-host/com/lma/app/VideoEncoder.java',
        'app/src/main/assets/recipe-templates.json')}


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows host only')
    before = inputs(); item = selected()['assets'][0]; model = asset_path(item)
    merges = next(c for c in bundle()['components'] if c['role'] == 'clip_merges'); vocab = sd15_path(merges)
    for path, asset in [(model, item), (vocab, merges)]:
        if path.stat().st_size != asset['bytes'] or sha(path) != asset['sha256']: raise ValueError('Complete selected asset differs')
    binary, compilation = build()
    direct_path = ROOT / 'build/sd-distilled-asset-probe/sd-turbo-probe-results.json'
    direct = json.loads(direct_path.read_text(encoding='utf-8')); current(direct['input_fingerprint'])
    if not direct['host_checks_passed'] or direct['asset']['sha256'] != item['sha256']: raise ValueError('Inspect complete actual native SD-Turbo capture first')
    output = ROOT / 'build/sd-turbo-app-host-tests' / ('run-' + str(time.time_ns())); output.mkdir(parents=True, exist_ok=False)
    classes = output / 'classes'; classes.mkdir()
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    if sha(dependency) != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796': raise ValueError('Changed Java dependency')
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java'))
    sources += sorted((ROOT / 'tests/sd-trained').rglob('*.java')) + sorted((ROOT / 'tests/sd-distilled').rglob('*.java'))
    sources += [ROOT / 'app/src/main/java/com/lma/app' / (name + '.java') for name in ['SdEngine', 'NativeWorker', 'LocalEngine']]
    sources += [ROOT / 'tests/tts-host/com/lma/app/LmaApp.java', ROOT / 'tests/sd-host/com/lma/app/VideoEncoder.java']
    response = output / 'sources.rsp'; response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    compiled = subprocess.run([shutil.which('javac'), '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dependency),
        '-d', str(classes), '@' + str(response)], capture_output=True, timeout=90)
    (output / 'compile.log').write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode: raise RuntimeError('Inspect retained SD-Turbo Java compile log: ' + str(output.relative_to(ROOT)))
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        command = [shutil.which('java'), '-Dfile.encoding=UTF-8', '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', '-Duser.language=en',
            '-cp', alias(classes) + os.pathsep + alias(dependency), 'com.lma.app.SdTurboTrainedAppTest', alias(output / 'data'),
            alias(ROOT / 'research/sd_distilled_trained/sd_turbo_q8_0.json'), alias(ROOT / 'app/src/main/assets/recipe-templates.json'),
            alias(ROOT / 'catalogue/model-bundles.json'), alias(model), alias(vocab), alias(binary)]
        print('Import two complete objects and execute five real SD-Turbo Java/native cases: ' + output.relative_to(ROOT).as_posix(), flush=True)
        with (output / 'java.stdout').open('xb') as stdout, (output / 'java.stderr').open('xb') as stderr:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=21600)
        if result.returncode: raise RuntimeError('Inspect retained actual Java/native logs: ' + str(output.relative_to(ROOT)))
    finally: subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    java = json.loads((output / 'data/java-results.json').read_text(encoding='utf-8')); outputs = []
    by_name = {j['name']: j for j in direct['jobs']}
    for run in java['runs']:
        if 'output' not in run: continue
        normalized = run['output'].replace('\\', '/')
        if not normalized.startswith(drive + '/'): raise ValueError('Output escaped owned alias')
        path = (ROOT / normalized[len(drive) + 1:]).resolve(); path.relative_to(output.resolve())
        image = image_stats(path)
        if image['sha256'] != run['sha256'] or image['bytes'] != run['bytes'] or image['width'] != 512 or image['height'] != 512:
            raise ValueError('Actual production output differs')
        if image['sha256'] != by_name[run['name']]['image']['sha256']: raise ValueError('Production PNG differs from identical direct request')
        outputs.append(dict(name=run['name'], file=path.relative_to(ROOT).as_posix(), image=image, bitwise_equal_to_direct_native=True))
    files = {p.relative_to(output).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(output.rglob('*'))
             if p.is_file() and 'data/files/bundles/objects/' not in p.relative_to(output).as_posix() and '/classes/' not in p.as_posix()}
    current(before)
    report = dict(schema='lma.sd-turbo-app-host/1', java=java, compilation=compilation, outputs=outputs, files=files,
        capture_directory=output.relative_to(ROOT).as_posix(), direct_trained_report_sha256=sha(direct_path),
        production_java_native_host_executed=True, asset_download_attempted=False, physical_android=False, android_saf_tested=False,
        android_background_accepted=False, image_quality_accepted=False, complete_target03_accepted=False,
        complete_release_accepted=False, input_fingerprint=before)
    for path in [output / 'results.json', output.parent / 'results.json']: path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=java['passed'], binding_checks=java['binding_checks'], actual_host_children=java['actual_host_children'], outputs=len(outputs))), flush=True)


if __name__ == '__main__': main()
