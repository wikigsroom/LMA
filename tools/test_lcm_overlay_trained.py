"""Run actual trained LCM images with a small native-prepared condition overlay."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

import numpy as np
from PIL import Image
from build_sd_host import build
from evidence import current, fingerprint
from fetch_sd15_trained import asset_path, bundle, sha
from lcm_prepare_data import inspect
from sd_variants_capture import execute
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'build/sd-distilled-asset-probe'


def wire(capture, raw):
    events = []
    blanks = 0
    for line in raw.splitlines():
        if not line.strip(): blanks += 1; continue
        item = json.loads(line)
        if not isinstance(item, dict): raise ValueError('Non-object worker protocol line')
        events.append(item)
    if events != capture['events'] or capture['protocol_errors'] != ['Non-protocol stdout'] * blanks:
        raise ValueError('Unexpected worker stdout; only whitespace-only lines are tolerated')
    return blanks


def main():
    before = fingerprint('tools/test_lcm_overlay_trained.py', 'tools/lcm_prepare_data.py', 'tools/sd_variants_capture.py',
                         'tools/build_sd_host.py', 'native/sd_worker.cpp', 'native/sd_policy.hpp', 'native/vocab_external.cpp',
                         'research/lcm_prepare/contract.json')
    trained = json.loads((ROOT / 'build/lcm-preparation-trained/results.json').read_text(encoding='utf-8'))
    current(trained['input_fingerprint'])
    if not trained['passed'] or trained['physical_android'] or trained['production_app_integrated']:
        raise ValueError('Current bounded trained preparation receipt required')
    contract = json.loads((ROOT / 'research/lcm_prepare/contract.json').read_text(encoding='utf-8'))
    asset = contract['base']
    base = PRIVATE / 'originals' / asset['sha256'] / asset['path']
    if base.stat().st_size != asset['bytes'] or sha(base) != asset['sha256']:
        raise ValueError('Complete matching base required; no implicit download')
    stamp = (base.stat().st_size, base.stat().st_mtime_ns)
    prepared = ROOT / trained['output']['path']
    overlay = inspect(prepared.read_bytes())
    if overlay['sha256'] != trained['output']['sha256'] or overlay['metadata']['lma.overlay.base_sha256'] != asset['sha256']:
        raise ValueError('Prepared component identity / base binding')
    merges = next(c for c in bundle()['components'] if c['role'] == 'clip_merges')
    vocab = asset_path(merges)
    if vocab.stat().st_size != merges['bytes'] or sha(vocab) != merges['sha256']:
        raise ValueError('Matching separately acquired CLIP merges required')
    previous = json.loads((PRIVATE / 'lcm-checkpoint-probe-results.json').read_text(encoding='utf-8'))
    previous_folder = ROOT / previous['capture_directory']
    references = {}
    for label, index in [('original', 0), ('folded', 1)]:
        job = previous['jobs'][index]
        image = previous_folder / (job['name'] + '.png')
        if sha(image) != job['image']['sha256']: raise ValueError('Changed reference image')
        references[label] = dict(path=image.relative_to(ROOT).as_posix(), sha256=job['image']['sha256'])
    parent = ROOT / 'build/lcm-overlay-trained'
    parent.mkdir(exist_ok=True)
    directory = parent / ('run-' + str(time.time_ns()))
    directory.mkdir()
    # The negative-effect control overrides exactly the same bias with its original values.
    header = json.loads((PRIVATE / 'lcm-checkpoint-header.json').read_text(encoding='utf-8'))
    tensor = next(t for t in header['tensors'] if t['name'] == overlay['name'])
    if tensor['shape'] != [1280] or tensor['bytes'] != 5120 or tensor['ggml_type'] != 0:
        raise ValueError('Unexpected base bias layout')
    with base.open('rb') as stream:
        stream.seek(header['data_offset'] + tensor['offset'])
        raw = stream.read(5120)
    encoded = overlay['name'].encode('utf-8')
    small_header = b'GGUF' + struct.pack('<IQQQ', 3, 1, 0, len(encoded)) + encoded + struct.pack('<IQIQ', 1, 1280, 0, 0)
    small_header += bytes((-len(small_header)) % 32)
    original_overlay = directory / 'original-bias-control.gguf'
    original_overlay.write_bytes(small_header + raw)
    inspect(original_overlay.read_bytes())
    binary, compilation = build()
    drive = next(c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists())
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    jobs = []
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        environment = os.environ.copy(); environment['LMA_VOCAB_CLIP_MERGES'] = alias(vocab)
        for name, component, cfg, cancel in [('original-bias-control', original_overlay, 1, None),
                                             ('native-prepared', prepared, 1, None), ('invalid-cfg', prepared, 7, None),
                                             ('cancel-step1', prepared, 1, 1), ('recovery', prepared, 1, None)]:
            image = directory / (name + '.png')
            request = dict(schema='lma.engine-request/1', pipeline='sd15_lcm', architecture='sd15', samplingProfile='lcm', type='image.generate',
                input=dict(prompt='A small red fox sitting beside a blue ceramic teapot on a wooden table, clean composition', negativePrompt=''),
                parameters=dict(width=512, height=512, steps=4, cfg=cfg, sampler='lcm', scheduler='lcm', seed=42,
                                threads=6, vaeTiling=True, flowShift=0),
                components=dict(model=alias(base), diffusion=alias(component), clip_merges=alias(vocab)), loras=[], output=alias(image))
            path = directory / (name + '.json');path.write_text(json.dumps(request, indent=2) + '\n', encoding='utf-8')
            capture, logs = execute([alias(binary), alias(path)], environment, 4, cancel)
            for suffix, data in zip(['stdout', 'stderr'], logs): (directory / (name + '.' + suffix)).write_bytes(data)
            blanks = wire(capture, logs[0])
            valid = not capture['timed_out'] and not any(capture['logs_truncated'])
            if cancel is not None:
                valid = valid and capture['forced_host_termination'] and capture['cancel_trigger'] is not None and capture['returncode'] != 0 and not image.exists()
            elif cfg != 1:
                valid = valid and capture['returncode'] == 1 and not image.exists() and [e['message'] for e in capture['events'] if e.get('event') == 'error'] == ['Distilled sampling parameters do not match the frozen plan']
            else:
                valid = valid and capture['returncode'] == 0 and image.exists() and len([e for e in capture['events'] if e.get('event') == 'complete']) == 1
                if valid: capture['image'] = image_stats(image)
                if valid and name == 'original-bias-control': valid = capture['image']['sha256'] == references['original']['sha256']
            capture.update(name=name, parameters=request['parameters'], whitespace_only_stdout_lines=blanks,
                           whitespace_tolerant_protocol_valid=True, component_sha256=sha(component), passed=bool(valid))
            (directory / (name + '-capture.json')).write_text(json.dumps(capture, indent=2) + '\n', encoding='utf-8')
            jobs.append(capture)
            print(json.dumps(dict(name=name, passed=bool(valid), seconds=capture['seconds'], returncode=capture['returncode'])), flush=True)
            if not valid: break
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    complete = len(jobs) == 5 and all(j['passed'] for j in jobs)
    comparisons = {}
    if complete:
        recovered = jobs[1]['image']['sha256'] == jobs[4]['image']['sha256']
        changed = jobs[0]['image']['sha256'] != jobs[1]['image']['sha256']
        a = np.asarray(Image.open(directory / 'native-prepared.png').convert('RGB'), dtype='i2')
        b = np.asarray(Image.open(ROOT / references['folded']['path']).convert('RGB'), dtype='i2')
        delta = np.abs(a - b)
        comparisons = dict(recovery_exact=recovered, differs_from_original=changed,
                           previous_torch_folded_image_exact=jobs[1]['image']['sha256'] == references['folded']['sha256'],
                           mean_abs_rgb_vs_previous=float(delta.mean()), max_abs_rgb_vs_previous=int(delta.max()),
                           mean_abs_gate=.1, max_abs_gate=5)
        complete = complete and recovered and changed and comparisons['mean_abs_rgb_vs_previous'] <= .1 and comparisons['max_abs_rgb_vs_previous'] <= 5
    if stamp != (base.stat().st_size, base.stat().st_mtime_ns): raise ValueError('Base changed during capture')
    current(before)
    report = dict(schema='lma.lcm-native-prepared-overlay-trained/1', passed=bool(complete), compilation=compilation,
                  base=asset, base_whole_sha256_verified=True, preparation=trained['output'], references=references,
                  jobs=jobs, comparisons=comparisons, capture_directory=directory.relative_to(ROOT).as_posix(), input_fingerprint=before,
                  production_app_executed=False, physical_android=False, canonical_pipeline_equivalence_proven=False,
                  image_quality_accepted=False, complete_target03_accepted=False, complete_release_accepted=False)
    (directory / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (parent / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if not complete: raise RuntimeError('Inspect retained trained overlay captures; no acceptance')
    print(json.dumps(dict(passed=True, actual_native_children=len(jobs), comparisons=comparisons)))


if __name__ == '__main__': main()
