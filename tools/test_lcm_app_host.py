"""Actual model preparation, association and generation through production Java/native code.

Native Windows only, explicit existing user files, no downloads and no Android claims.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time
from build_sd_host import build, inputs as host_inputs
from build_lcm_prepare import build as prepare_build, inputs as prepare_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import asset_path, bundle, sha
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return host_inputs() | prepare_inputs() | fingerprint(
        'tools/test_lcm_app_host.py', 'tests/lcm-app', 'tests/sd-trained',
        'app/src/main/java/com/lma/app/core', 'app/src/main/java/com/lma/app/SdEngine.java',
        'app/src/main/java/com/lma/app/NativeWorker.java', 'app/src/main/java/com/lma/app/LocalEngine.java',
        'tests/tts-host/com/lma/app/LmaApp.java', 'tests/sd-host/com/lma/app/VideoEncoder.java',
        'catalogue/asset-preparations.json', 'catalogue/model-bundles.json', 'catalogue/model-assemblies.json')


def contracts(directory, java, runtime, overlay, worker, alias):
    """Rehash each corrupted file so Java must validate layout beyond its SHA guard."""
    encoded = overlay.read_bytes(); position = 24; fields = []
    for _ in range(6):
        size = struct.unpack_from('<Q', encoded, position)[0]; position += 8
        key = encoded[position:position + size].decode('ascii'); position += size
        type_offset = position; position += 4
        size = struct.unpack_from('<Q', encoded, position)[0]; position += 8
        fields.append((key, position, size, type_offset)); position += size
    name_offset = position + 8; name_size = struct.unpack_from('<Q', encoded, position)[0]
    rank = name_offset + name_size; shape = rank + 4; dtype = shape + 8; offset = dtype + 4
    payload = (offset + 8 + 31) // 32 * 32
    def patch(offset, value):
        result = bytearray(encoded); result[offset:offset + len(value)] = value; return bytes(result)
    cases = [('valid', encoded, runtime, True), ('truncated', encoded[:-1], runtime, False),
             ('suffix', encoded + b'\0', runtime, False), ('wrong-version', patch(4, struct.pack('<I', 2)), runtime, False),
             ('extra-tensor', patch(8, struct.pack('<Q', 2)), runtime, False),
             ('missing-metadata', patch(16, struct.pack('<Q', 5)), runtime, False),
             ('wrong-name', patch(name_offset, b'X'), runtime, False), ('wrong-rank', patch(rank, struct.pack('<I', 2)), runtime, False),
             ('wrong-width', patch(shape, struct.pack('<Q', 1279)), runtime, False),
             ('wrong-type', patch(dtype, struct.pack('<I', 1)), runtime, False), ('wrong-offset', patch(offset, struct.pack('<Q', 32)), runtime, False),
             ('nonzero-padding', patch(payload - 1, b'\x01'), runtime, False),
             ('nan', patch(payload, struct.pack('<I', 0x7fc00000)), runtime, False),
             ('infinity', patch(payload, struct.pack('<I', 0x7f800000)), runtime, False)]
    for key, start, size, type_offset in fields:
        cases.append(('metadata-' + key.split('.')[-1], patch(start, b'X'), runtime, False))
    for key, value in [('sourceSha256', '0' * 64), ('baseSha256', '0' * 64), ('distilledGuidance', 7.), ('algorithm', 'unknown')]:
        manifest = copy.deepcopy(runtime); manifest['conditionBias'][key] = value
        cases.append(('binding-' + key, encoded, manifest, False))
    missing = copy.deepcopy(runtime); del missing['conditionBias']; cases.append(('missing-binding', encoded, missing, False))
    extra = copy.deepcopy(runtime); extra['conditionBias']['path'] = 'untrusted'; cases.append(('extra-binding', encoded, extra, False))
    reports = []
    for name, data, manifest, accepted in cases:
        selected = directory / name; selected.mkdir(); file = selected / 'condition.gguf'; file.write_bytes(data)
        model = selected / 'model.json'; model.write_text(json.dumps(manifest), encoding='utf-8')
        result = subprocess.run(java + ['com.lma.app.LcmConditionContractTest', alias(model), alias(file)], capture_output=True, timeout=30, check=True)
        if result.stdout.strip() != (b'ACCEPT' if accepted else b'REJECT'): raise ValueError('Java condition contract: ' + name)
        native = dict(schema='lma.engine-request/1', type='image.generate', pipeline='sd15_lcm', architecture='sd15', samplingProfile='lcm',
                      input=dict(prompt='Contract validation', negativePrompt=''), parameters=dict(width=512,height=512,steps=4,cfg=1,sampler='lcm',scheduler='lcm',seed=42,threads=1),
                      components=dict(model='missing-base.gguf', clip_merges='missing-merges.txt', condition_bias=alias(file)), loras=[], output=alias(selected / 'unexpected.png'))
        if 'conditionBias' in manifest: native['conditionBias'] = manifest['conditionBias']
        command = selected / 'request.json'; command.write_text(json.dumps(native), encoding='utf-8')
        run = subprocess.run([alias(worker), alias(command)], capture_output=True, timeout=30)
        (selected / 'native.stdout').write_bytes(run.stdout); (selected / 'native.stderr').write_bytes(run.stderr)
        events = [json.loads(line) for line in run.stdout.splitlines() if line.strip()]
        errors = [item['message'] for item in events if item.get('event') == 'error']
        if run.returncode != 1 or (selected / 'unexpected.png').exists() or len(errors) != 1: raise ValueError('Native condition contract: ' + name)
        if not accepted and not ('LCM' in errors[0] or 'condition' in errors[0] or 'source' in errors[0]): raise ValueError('Invalid condition reached base loading: ' + name + ': ' + errors[0])
        reports.append(dict(name=name, java_accepted=accepted, native_error=errors[0], no_output=True))
    return reports


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows required')
    before = inputs(); contract = json.loads((ROOT / 'research/lcm_prepare/contract.json').read_text(encoding='utf-8'))
    trained = json.loads((ROOT / 'build/lcm-preparation-trained/results.json').read_text(encoding='utf-8'))
    historical = json.loads((ROOT / 'build/lcm-overlay-trained/results.json').read_text(encoding='utf-8'))
    assert trained['passed'] and not historical['passed']
    source = ROOT / 'build/sd-distilled-asset-probe/originals' / contract['source']['sha256'] / Path(contract['source']['path']).name
    base = ROOT / 'build/sd-distilled-asset-probe/originals' / contract['base']['sha256'] / contract['base']['path']
    merges = next(c for c in bundle()['components'] if c['role'] == 'clip_merges'); vocab = asset_path(merges)
    for path, asset in [(source,contract['source']), (base,contract['base']), (vocab,merges)]:
        if path.stat().st_size != asset['bytes'] or sha(path) != asset['sha256']: raise ValueError('Complete explicit local asset required')
    worker, worker_build = build(); preparer, preparer_build = prepare_build()
    directory = ROOT / 'build/lcm-app-host-tests' / ('run-' + str(time.time_ns())); directory.mkdir(parents=True)
    dependency = ROOT / 'build/test-deps/json-20250517.jar'
    if sha(dependency) != '3ea61b2a06e31edf1c91134fe9106b0ebb16628be169f3db75bc7a2b06b45796': raise ValueError('Changed Java dependency')
    classes = directory / 'classes'; classes.mkdir()
    sources = sorted((ROOT / 'app/src/main/java/com/lma/app/core').glob('*.java')) + sorted((ROOT / 'tests/lcm-app').rglob('*.java')) + sorted((ROOT / 'tests/sd-trained').rglob('*.java'))
    sources += [ROOT / 'app/src/main/java/com/lma/app' / (n + '.java') for n in ['SdEngine','NativeWorker','LocalEngine']]
    sources += [ROOT / 'tests/tts-host/com/lma/app/LmaApp.java', ROOT / 'tests/sd-host/com/lma/app/VideoEncoder.java']
    response = directory / 'sources.rsp'; response.write_text('\n'.join('"' + p.as_posix() + '"' for p in sources), encoding='utf-8')
    compiled = subprocess.run([shutil.which('javac'), '-encoding','UTF-8','-Xlint:-options','--release','8','-cp',str(dependency),'-d',str(classes),'@'+str(response)],capture_output=True,timeout=90)
    (directory / 'compile.log').write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode: raise RuntimeError('Inspect ' + str(directory.relative_to(ROOT)) + '/compile.log')
    runtime = next(b for b in json.loads((ROOT / 'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['id']=='lcm_dreamshaper_guidance85_runtime_v1')
    drive = next(c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()); subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
    try:
        def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
        java = [shutil.which('java'),'-Dfile.encoding=UTF-8','-Dstdout.encoding=UTF-8','-Dstderr.encoding=UTF-8','-Duser.language=en','-cp',alias(classes)+os.pathsep+alias(dependency)]
        checks = directory / 'contracts'; checks.mkdir(); controls = contracts(checks,java,runtime,ROOT / trained['output']['path'],worker,alias)
        args = [directory / 'data', ROOT / 'catalogue/model-bundles.json', ROOT / 'catalogue/asset-preparations.json', ROOT / 'catalogue/model-assemblies.json', source,base,vocab,preparer,worker]
        print('Run full-source preparation, explicit association and four trained generation cases: ' + directory.relative_to(ROOT).as_posix(),flush=True)
        with (directory/'java.stdout').open('xb') as stdout,(directory/'java.stderr').open('xb') as stderr:
            result = subprocess.run(java+['com.lma.app.LcmTrainedAppTest']+[alias(p) for p in args],cwd=ROOT,stdout=stdout,stderr=stderr,timeout=21600)
        if result.returncode: raise RuntimeError('Inspect ' + directory.relative_to(ROOT).as_posix() + '/java.stderr')
    finally: subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    record = json.loads((directory/'data/java-results.json').read_text(encoding='utf-8')); outputs=[]
    reference=next(j for j in historical['jobs'] if j['name']=='native-prepared')['image']['sha256']
    for run in record['runs']:
        if 'output' not in run: continue
        normalized=run['output'].replace('\\','/'); assert normalized.startswith(drive+'/')
        path=ROOT/normalized[len(drive)+1:]; path.resolve().relative_to(directory.resolve()); stats=image_stats(path)
        assert stats['sha256']==run['sha256']==reference and stats['width']==stats['height']==512
        outputs.append(dict(name=run['name'],path=path.relative_to(ROOT).as_posix(),image=stats,bitwise_equal_to_historical_native_prepared=True))
    current(before)
    report=dict(schema='lma.lcm-app-host/1',passed=True,java=record,contracts=controls,outputs=outputs,compilation=worker_build,preparer_build=preparer_build,
        capture_directory=directory.relative_to(ROOT).as_posix(),production_preparation_association_generation_host_executed=True,
        asset_download_attempted=False,physical_android=False,android_saf_tested=False,android_background_accepted=False,
        historical_pixel_comparison_passed=False,image_quality_accepted=False,complete_target03_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    for path in [directory/'results.json',directory.parent/'results.json']: path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,java_checks=record['passed'],binding_checks=record['binding_checks'],contract_cases=len(controls),outputs=len(outputs))),flush=True)


if __name__=='__main__': main()
