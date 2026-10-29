"""Test production preparation lifecycle; optional full trained native conversion, no downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('app/src/main/java/com/lma/app/core', 'tests/PreparationTest.java', 'tests/host/android/util/AtomicFile.java',
                       'tools/test_preparations.py', 'catalogue/asset-preparations.json', 'catalogue/model-bundles.json')


def main(trained=False):
    before = inputs(); out = ROOT / 'build/preparation-tests'; out.mkdir(exist_ok=True)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dependency.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/PreparationTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    response = out / 'sources.rsp'; response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-J-Dfile.encoding=UTF-8', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@' + str(response)], cwd=ROOT, check=True)
    run = out / ('trained-' if trained else 'contracts-'); run = run.with_name(run.name + str(time.time_ns())); run.mkdir()
    command = [shutil.which('java'), '-Duser.language=en', '-Dfile.encoding=UTF-8', '-Dsun.stdout.encoding=UTF-8', '-Dsun.stderr.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dependency), 'com.lma.app.PreparationTest']
    identities = {}
    if trained:
        for stem in ['ltx098-prepare', 'ltx098-vae-prepare']:
            receipt = json.loads((ROOT / f'build/{stem}-host/receipt.json').read_text(encoding='utf-8')); current(receipt['input_fingerprint'])
            name = 'lma_' + stem.replace('-', '_') + '.exe'; binary = ROOT / f'build/{stem}-host/bin/{name}'
            assert hashlib.sha256(binary.read_bytes()).hexdigest() == receipt['executable_sha256']; identities[stem] = receipt
        command += ['--trained', str(run), str(ROOT / 'catalogue/asset-preparations.json'), str(ROOT / 'catalogue/model-bundles.json'),
                    str(ROOT / 'build/ltx098-trained/originals/ltxv-2b-0.9.8-distilled.safetensors'),
                    str(ROOT / 'build/ltx098-prepare-host/bin/lma_ltx098_prepare.exe'), str(ROOT / 'build/ltx098-vae-prepare-host/bin/lma_ltx098_vae_prepare.exe'), str(ROOT / 'research/ltx098_vae_prepare/graphs')]
    else: command += [str(run)]
    (out / ('trained-results.json' if trained else 'results.json')).unlink(missing_ok=True)
    started = time.monotonic()
    with (run / 'stdout.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, encoding='utf-8', timeout=2400 if trained else 120)
    if result.returncode:
        lines=(run / 'stdout.log').read_text(encoding='utf-8',errors='replace').splitlines(); print('\n'.join(lines[:5] + lines[-11:])); raise RuntimeError('Preparation lifecycle checks failed')
    record = json.loads((run / 'stdout.log').read_text(encoding='utf-8').strip().splitlines()[-1]); current(before)
    record.update(schema='lma.preparation-core-tests/1', input_fingerprint=before, artifacts_directory=run.relative_to(ROOT).as_posix(),
                  actual_trained_preparations=int(trained), model_inference=False, physical_android=False, release_ready=False, seconds=time.monotonic() - started,
                  builds=identities, component_inference_validation_reused=trained, app_service_or_saf_executed=False)
    if trained:
        details=json.loads((run / 'trained-result.json').read_text(encoding='utf-8')); record['prepared_assets']=details
        assert details['outputs'] and len(details['outputs']) == 20 and record['nativeChildren'] == 2
    (out / ('trained-results.json' if trained else 'results.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['input_fingerprint','builds','prepared_assets']}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--trained', action='store_true'); main(parser.parse_args().trained)
