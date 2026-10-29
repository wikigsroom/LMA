"""Exercise user-selected model association with fixture or existing real trained local outputs."""
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
    return fingerprint('app/src/main/java/com/lma/app/core', 'tests/PreparationTest.java', 'tests/AssemblyTest.java',
                       'tests/host/android/util/AtomicFile.java', 'tools/test_assemblies.py',
                       'catalogue/asset-preparations.json', 'catalogue/model-assemblies.json', 'catalogue/model-bundles.json')


def main(trained=False):
    before = inputs(); out = ROOT / 'build/assembly-tests'; out.mkdir(exist_ok=True)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dependency.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    classes = out / 'classes'; classes.mkdir(exist_ok=True)
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + [ROOT / 'tests/PreparationTest.java', ROOT / 'tests/AssemblyTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    rsp = out / 'sources.rsp'; rsp.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-J-Duser.language=en', '-encoding', 'UTF-8', '-Xlint:-options', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@' + str(rsp)], cwd=ROOT, check=True)
    run = out / (('trained-' if trained else 'contracts-') + str(time.time_ns())); run.mkdir()
    command = [shutil.which('java'), '-Dfile.encoding=UTF-8', '-cp', str(classes) + os.pathsep + str(dependency), 'com.lma.app.AssemblyTest']
    if trained:
        preparation = json.loads((ROOT / 'build/preparation-tests/trained-results.json').read_text(encoding='utf-8')); current(preparation['input_fingerprint'])
        prepared_root = ROOT / preparation['artifacts_directory'] / 'prepared'
        command += ['--trained', str(run), str(prepared_root), str(ROOT / 'catalogue/asset-preparations.json'), str(ROOT / 'catalogue/model-bundles.json'), str(ROOT / 'catalogue/model-assemblies.json')]
    else: command += [str(run)]
    result_path = out / ('trained-results.json' if trained else 'results.json'); result_path.unlink(missing_ok=True)
    started = time.monotonic()
    with (run / 'stdout.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800 if trained else 120)
    output = (run / 'stdout.log').read_text(encoding='utf-8', errors='replace')
    if result.returncode: raise RuntimeError(output[-5000:])
    record = json.loads(output.strip().splitlines()[-1]); current(before)
    record.update(schema='lma.assembly-core-tests/1', input_fingerprint=before, artifacts_directory=run.relative_to(ROOT).as_posix(),
                  seconds=time.monotonic() - started, automatic_downloads=False, model_bytes_copied=0, release_ready=False,
                  app_service_or_saf_executed=False)
    if trained: record['association'] = json.loads((run / 'trained-result.json').read_text(encoding='utf-8'))
    result_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ('input_fingerprint', 'association')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--trained', action='store_true'); main(parser.parse_args().trained)
