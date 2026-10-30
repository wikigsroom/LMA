"""Bounded production voice metadata tests; actual files are headers only, never inference."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/speech-voice-tests'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = fingerprint('app/src/main/java/com/lma/app/core', 'tests/SpeechVoicesTest.java',
                         'tests/fixtures/speech-voices.json', 'tests/host/android/util/AtomicFile.java',
                         'tools/test_speech_voices.py', 'tools/evidence.py', 'catalogue/model-bundles.json',
                         'catalogue/moss-nano-100m-onnx.bundle.json', 'verification/development/tts-assets.json',
                         'verification/development/moss-nano-assets.json')
    fixture = json.loads((ROOT / 'tests/fixtures/speech-voices.json').read_text(encoding='utf-8'))
    paths = {}
    for model in fixture['models']:
        receipt = json.loads((ROOT / model['receipt']).read_text(encoding='utf-8'))
        item = next(c for c in receipt['components'] if c['sha256'] == model['sha256'])
        assert item['role'] == model['role'] and item['bytes'] == model['bytes'] and item['path'] == model['path']
        file = ROOT / item['local_path']
        with file.open('rb') as stream:
            identity = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert file.stat().st_size == model['bytes'] and identity == model['sha256'], 'Actual header asset identity mismatch'
        paths[model['id']] = str(file)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    assert hashlib.sha256(dependency.read_bytes()).hexdigest() == '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796'
    run = OUT / 'run'
    if run.exists():
        assert run.resolve().parent == OUT.resolve()
        shutil.rmtree(run)
    run.mkdir()
    classes = OUT / 'classes'
    classes.mkdir(exist_ok=True)
    pathfile = OUT / 'actual-files.json'
    pathfile.write_text(json.dumps(paths), encoding='utf-8')
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java'))
    sources += [ROOT / 'tests/SpeechVoicesTest.java', ROOT / 'tests/host/android/util/AtomicFile.java']
    response = OUT / 'sources.rsp'
    response.write_text('\n'.join('"'+p.as_posix()+'"' for p in sources), encoding='utf-8')
    subprocess.run([shutil.which('javac'), '-encoding', 'UTF-8', '--release', '8', '-cp', str(dependency), '-d', str(classes), '@'+str(response)], cwd=ROOT, check=True)
    result = subprocess.run([shutil.which('java'), '-Xmx48m', '-Dfile.encoding=UTF-8', '-cp', str(classes)+os.pathsep+str(dependency), 'com.lma.app.SpeechVoicesTest', str(run), str(ROOT/'tests/fixtures/speech-voices.json'), str(pathfile), str(ROOT/'catalogue/model-bundles.json'), str(ROOT/'catalogue/moss-nano-100m-onnx.bundle.json')], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60)
    if result.returncode:
        raise RuntimeError(result.stdout+'\n'+result.stderr)
    report = json.loads(result.stdout.strip().splitlines()[-1])
    report.update(scope='Production Java metadata parser, numeric suggestions, asset-store upgrade and four exact local model headers. Full SHA verified before metadata inspection; no neural execution or Android acceptance.', max_java_heap_bytes=48*1024*1024, weights_downloaded=False, input_fingerprint=inputs)
    current(inputs)
    (OUT/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('passed','checks','actual_local_headers','model_inference','android_device')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
