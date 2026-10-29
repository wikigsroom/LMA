"""Run full trained import/settings/adapter leases and real production Java/native diffusion."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import inputs as sd15_inputs, sha, verify as verify_sd15
from fetch_sd_variants_trained import inputs as asset_inputs, verify
from sd_variants_manifests import inputs as manifest_inputs
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **sd15_inputs(), **asset_inputs(), **manifest_inputs(), **fingerprint(
        'tools/test_sd_variants_app_host.py', 'tools/test_sd_variants_trained.py', 'tools/sd_variants_capture.py',
        'tools/sd_variants_inspect.py', 'tests/sd-trained', 'research/sd_variants_trained',
        'app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/SdEngine.java',
        'app/src/main/java/com/lma/app/NativeWorker.java', 'app/src/main/java/com/lma/app/LocalEngine.java',
        'tests/tts-host/com/lma/app/LmaApp.java',
        'tests/sd-host/com/lma/app/VideoEncoder.java')}


def compile_java(output):
    classes = output / 'classes'; classes.mkdir(parents=True, exist_ok=False)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    if sha(dependency) != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796': raise ValueError('Changed Java dependency')
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + sorted((ROOT / 'tests/sd-trained').rglob('*.java'))
    sources += [ROOT / 'app/src/main/java/com/lma/app' / (name + '.java') for name in ['SdEngine', 'NativeWorker', 'LocalEngine']]
    sources += [ROOT / 'tests/tts-host/com/lma/app/LmaApp.java', ROOT / 'tests/sd-host/com/lma/app/VideoEncoder.java']
    response = output / 'sources.rsp'; response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    result = subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8',
        '-cp', str(dependency), '-d', str(classes), '@' + str(response)], capture_output=True, timeout=90)
    (output / 'compile.log').write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError('Inspect trained diffusion Java compilation log: ' + str(output.relative_to(ROOT)))
    return classes, dependency


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows host only')
    before = inputs(); verify_sd15(); verify(); binary, compilation = build()
    direct_path = ROOT / 'build/sd-variants-trained-tests/results.json'; direct = json.loads(direct_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint'])
    if not direct['host_execution_checks_passed']: raise ValueError('Complete the actual direct trained checks first')
    output = ROOT / 'build/sd-variants-app-host-tests' / ('run-' + str(time.time_ns())); output.mkdir(parents=True, exist_ok=False)
    classes, dependency = compile_java(output)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        command = [shutil.which('java'), '-Dfile.encoding=UTF-8', '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', '-Duser.language=en',
            '-cp', alias(classes) + os.pathsep + alias(dependency), 'com.lma.app.SdTrainedAppTest', alias(output / 'data'),
            alias(ROOT / 'build/sd-variants-trained/originals'), alias(ROOT / 'research/sd_variants_trained/manifests'),
            alias(ROOT / 'catalogue/model-bundles.json'), alias(binary), alias(ROOT / 'build/sd15-trained/originals'),
            alias(ROOT / 'research/sd_variants_trained/assets.json'), alias(ROOT / 'app/src/main/assets/recipe-templates.json')]
        print('Import seven complete trained objects and execute production Java/native diffusion', flush=True)
        with (output / 'java.stdout').open('xb') as stdout, (output / 'java.stderr').open('xb') as stderr:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=21600)
        if result.returncode: raise RuntimeError('Inspect actual trained Java/native logs: ' + str(output.relative_to(ROOT)))
    finally: subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    java = json.loads((output / 'data/java-results.json').read_text(encoding='utf-8')); current(before); outputs = []
    by_name = {j['name']: j for j in direct['jobs']}
    for run in java['runs']:
        if 'output' not in run: continue
        normalized = run['output'].replace('\\', '/')
        if not normalized.startswith(drive + '/'): raise ValueError('Output escaped owned alias')
        path = (ROOT / normalized[len(drive) + 1:]).resolve(); path.relative_to(output.resolve())
        image = image_stats(path)
        if image['sha256'] != run['sha256'] or image['bytes'] != run['bytes'] or image['width'] != 512 or image['height'] != 512:
            raise ValueError('Changed actual Java-produced PNG')
        reference = by_name[run['family'] + '-lcm-style']['image']['sha256']
        if image['sha256'] != reference: raise ValueError('Java output differs from identical direct native parameters and adapter order')
        outputs.append(dict(file=path.relative_to(ROOT).as_posix(), family=run['family'], name=run['name'], image=image,
                            bitwise_equal_to_direct_native=True))
    files = {p.relative_to(output).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(output.rglob('*'))
             if p.is_file() and ('data/files/bundles/objects/' not in p.relative_to(output).as_posix())
             and ('/classes/' not in p.as_posix())}
    report = dict(schema='lma.sd-variants-app-host/1', java=java, compilation=compilation, outputs=outputs, files=files,
        direct_trained_report_sha256=sha(direct_path), capture_directory=output.relative_to(ROOT).as_posix(),
        production_java_native_host_executed=True, physical_android=False, android_saf_tested=False, android_background_accepted=False,
        image_quality_accepted=False, complete_target02_accepted=False, complete_target03_accepted=False,
        complete_target05_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    for path in [output / 'results.json', output.parent / 'results.json']: path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=java['passed'], actual_host_children=java['actual_host_children'], imported_objects=java['imported_objects'], outputs=len(outputs))), flush=True)


if __name__ == '__main__': main()
