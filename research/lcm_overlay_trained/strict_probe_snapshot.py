"""Private real-weight partial-tensor override proof; no App or Android acceptance."""
import json
from hashlib import sha256
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
directory = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'tools'))
from build_sd_host import build
from evidence import current, fingerprint
from fetch_sd15_trained import sha, bundle, asset_path
from sd_variants_capture import execute
from test_sd_variants_trained import image_stats

before = fingerprint('build/sd-distilled-asset-probe/probe_lcm_overlay.py')
derivation = json.loads((directory / 'lcm-fixed-guidance-derivation.json').read_text(encoding='utf-8'))
header = json.loads((directory / 'lcm-checkpoint-header.json').read_text(encoding='utf-8'))
previous = json.loads((directory / 'lcm-checkpoint-probe-results.json').read_text(encoding='utf-8'))
asset = derivation['source_assets'][1]
base = directory / 'originals' / asset['sha256'] / asset['path']
prepared = root / derivation['output']['path']
for path, identity in [(base, asset), (prepared, derivation['output'])]:
    assert path.stat().st_size == identity['bytes'] and sha(path) == identity['sha256']
merges = next(c for c in bundle()['components'] if c['role'] == 'clip_merges')
vocab = asset_path(merges)
assert vocab.stat().st_size == merges['bytes'] and sha(vocab) == merges['sha256']
tensor = next(t for t in header['tensors'] if t['name'] == derivation['changed_tensor'])
assert tensor['shape'] == [1280] and tensor['ggml_type'] == 0 and tensor['bytes'] == 5120
offset = header['data_offset'] + tensor['offset']
binary, compilation = build()
output = directory / ('lcm-overlay-private-' + str(time.time_ns()))
output.mkdir()
print('Private actual trained overlay capture: ' + output.relative_to(root).as_posix(), flush=True)
records = []
for name, source in [('fixed-guidance8p5', prepared), ('original-bias-control', base)]:
    with source.open('rb') as stream:
        stream.seek(offset)
        raw = stream.read(5120)
    assert len(raw) == 5120
    encoded = tensor['name'].encode('utf-8')
    metadata = b'GGUF' + struct.pack('<IQQ', 3, 1, 0)
    metadata += struct.pack('<Q', len(encoded)) + encoded + struct.pack('<IQIQ', 1, 1280, 0, 0)
    metadata += bytes((-len(metadata)) % 32)
    overlay = output / (name + '.gguf')
    overlay.write_bytes(metadata + raw)
    records.append(dict(name=name, path=overlay.relative_to(root).as_posix(), bytes=overlay.stat().st_size,
                        sha256=sha(overlay), learned_payload_bytes=5120, tensors=1, source_bias_sha256=sha256(raw).hexdigest()))

drive = next(c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists())
subprocess.run(['subst', drive, str(root)], capture_output=True, check=True)
jobs = []
try:
    def alias(path): return drive + '/' + path.relative_to(root).as_posix()
    environment = os.environ.copy()
    environment['LMA_VOCAB_CLIP_MERGES'] = alias(vocab)
    for record in records:
        name = record['name']
        image = output / (name + '.png')
        request = dict(schema='lma.engine-request/1', pipeline='sd15_lcm', architecture='sd15',
            samplingProfile='lcm', type='image.generate',
            input=dict(prompt='A small red fox sitting beside a blue ceramic teapot on a wooden table, clean composition', negativePrompt=''),
            parameters=dict(width=512, height=512, steps=4, cfg=1, sampler='lcm', scheduler='lcm', seed=42,
                            threads=6, vaeTiling=True, flowShift=0),
            components=dict(model=alias(base), diffusion=alias(root / record['path']), clip_merges=alias(vocab)),
            loras=[], output=alias(image))
        request_path = output / (name + '.json')
        request_path.write_text(json.dumps(request, indent=2) + '\n', encoding='utf-8')
        result, logs = execute([alias(binary), alias(request_path)], environment, 4, None)
        for suffix, raw in zip(['stdout', 'stderr'], logs): (output / (name + '.' + suffix)).write_bytes(raw)
        expected = previous['jobs'][1 if name == 'fixed-guidance8p5' else 0]['image']['sha256']
        valid = (result['returncode'] == 0 and not result['timed_out'] and not result['protocol_errors']
                 and not any(result['logs_truncated']) and image.exists()
                 and any(e.get('event') == 'complete' for e in result['events']))
        if valid: result['image'] = image_stats(image)
        result.update(name=name, parameters=request['parameters'], overlay=record,
                      expected_previous_image_sha256=expected,
                      matches_full_checkpoint_image=result.get('image', {}).get('sha256') == expected)
        result['passed'] = valid and result['matches_full_checkpoint_image']
        (output / (name + '-capture.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        jobs.append(result)
        print(json.dumps(dict(name=name, passed=result['passed'], seconds=result['seconds'], returncode=result['returncode'],
                              sha256=result.get('image', {}).get('sha256'), expected=expected)), flush=True)
        if not result['passed']: break
finally:
    subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
current(before)
report = dict(schema='lma.private-lcm-partial-overlay/1', asset=asset, derivation=derivation, compilation=compilation,
              source_whole_sha256_verified=True, overlays=records, jobs=jobs,
              host_checks_passed=len(jobs) == 2 and all(j['passed'] for j in jobs),
              production_app_executed=False, physical_android=False, image_quality_accepted=False,
              complete_target03_accepted=False, complete_release_accepted=False,
              input_fingerprint=before, capture_directory=output.relative_to(root).as_posix())
(output / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(directory / 'lcm-overlay-probe-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if not report['host_checks_passed']: raise RuntimeError('Inspect retained partial overlay captures; no acceptance')
