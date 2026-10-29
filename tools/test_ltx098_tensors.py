"""Independent host checks for portable old-LTX RNG/layout/frame primitives.

No learned weights, model inference, APK integration or physical phone test.
The original publisher patchifier and Diffusers pixel normalization are oracles.
"""
import json
import math
import struct
import subprocess
from pathlib import Path
import numpy as np
from evidence import current, fingerprint
from build_ltx098_tensors import inputs as build_inputs
from ltx098_vae import sha

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build/ltx098-tensors-host/bin/lma_ltx098_tensors.exe'
OUT = ROOT / 'build/ltx098-tensors-tests'


def normal_reference(seed, count):
    """Scalar double-precision version of the frozen, public RNG definition."""
    state = seed
    mask = (1 << 64) - 1
    def uniform():
        nonlocal state
        state = (state + 0x9e3779b97f4a7c15) & mask
        value = state
        value = ((value ^ (value >> 30)) * 0xbf58476d1ce4e5b9) & mask
        value = ((value ^ (value >> 27)) * 0x94d049bb133111eb) & mask
        value ^= value >> 31
        return ((value >> 32) + .5) / (1 << 32)
    result = []
    for _ in range(count // 2):
        radius = math.sqrt(-2 * math.log(uniform()))
        angle = math.tau * uniform()
        result.extend((radius * math.cos(angle), radius * math.sin(angle)))
    return np.asarray(result, dtype='<f4')


def run():
    OUT.mkdir(exist_ok=True)
    receipt = OUT / 'results.json'; receipt.unlink(missing_ok=True)
    before = {**build_inputs(), **fingerprint('tools/test_ltx098_tensors.py',
              'tools/ltx098_fixture.py', 'tools/ltx098_vae.py', 'tools/ltx098_assets.py',
              'tools/build_ltx098.py', 'third_party/ltx098-source-lock.json',
              'third_party/ltx098-vae-source-lock.json')}
    build = json.loads((ROOT / 'build/ltx098-tensors-host/receipt.json').read_text(encoding='utf-8'))
    current(build['input_fingerprint'])
    assert build['input_fingerprint'] == build_inputs() and sha(EXE) == build['executable_sha256']
    # A fresh directory retains failed test outputs for diagnosis, without deleting
    # existing work or ever allowing a helper to overwrite another run's files.
    import tempfile
    directory = Path(tempfile.mkdtemp(prefix='run-', dir=OUT))
    checks = 0; children = 0; guards = []; metrics = []
    def check(ok, message):
        nonlocal checks
        if not ok: raise AssertionError(message)
        checks += 1
    def native(name, request, success=True, raw=None):
        nonlocal children
        path = directory / (name + '.json')
        path.write_text(raw if raw is not None else json.dumps(request, ensure_ascii=False), encoding='utf-8')
        result = subprocess.run([str(EXE), str(path)], capture_output=True, timeout=30, cwd=ROOT)
        children += 1
        (directory / (name + '.log')).write_bytes(result.stdout + result.stderr)
        data = json.loads(result.stdout)
        check(result.returncode == (0 if success else 1), name + ': wrong process exit')
        check(data['ok'] is success, name + ': wrong protocol outcome')
        if not success: guards.append(name)
        return data
    base = dict(width=64, height=64, frames=9, fps=24)
    def noise(name, seed=42, **shape):
        a = directory / (name + '-initial.f32'); b = directory / (name + '-decode.f32')
        request = dict(operation='noise', **(base | shape), seed=seed, latents=str(a), noise=str(b))
        return request, a, b

    distributions = []
    for i, (seed, shape) in enumerate([(0, {}), (42, {}), (2147483647, {}),
                                      (42, dict(width=256, height=256, frames=33)),
                                      (17, dict(width=96, height=128, frames=1, fps=60))]):
        request, a, b = noise('noise-' + str(i), seed, **shape)
        record = native('noise-' + str(i), request)
        count = 128 * ((request['frames'] - 1) // 8 + 1) * (request['height'] // 32) * (request['width'] // 32)
        actual = np.concatenate([np.fromfile(a, dtype='<f4'), np.fromfile(b, dtype='<f4')])
        expected = normal_reference(seed, count * 2)
        error = float(np.max(np.abs(actual - expected)))
        check(actual.size == count * 2 and np.isfinite(actual).all(), 'Noise size/finite check')
        check(error <= 1e-6, 'Frozen RNG definition differs from scalar reference')
        check(record['values_each'] == count and record['matches_pytorch_seed'] is False, 'Noise identity claim')
        check(record['initial_shape'] == [1, count // 128, 128], 'Initial noise layout')
        check(record['decode_noise_shape'] == [1, 128, (request['frames'] - 1) // 8 + 1, request['height'] // 32, request['width'] // 32], 'Decode noise layout')
        metrics.append(dict(kind='noise', seed=seed, shape={k: request[k] for k in base}, max_abs=error,
                            mean=float(actual.mean()), std=float(actual.std())))
        if i == 3:
            check(abs(float(actual.mean())) < .02 and abs(float(actual.std()) - 1) < .02, 'Normal distribution moment gate')
            distributions = actual
        if i == 1: baseline = (a.read_bytes(), b.read_bytes())
    request, a, b = noise('repeat')
    native('repeat', request)
    check((a.read_bytes(), b.read_bytes()) == baseline, 'Same seed/shape not byte-identical')
    check(not np.array_equal(distributions[:1024], distributions[40960:41984]), 'Initial and decoder streams were reused')

    print('Importing pinned original layout/pixel oracles; no model weights', flush=True)
    from ltx098_vae import environment
    environment()
    import torch
    from ltx_video.models.transformers.symmetric_patchifier import SymmetricPatchifier
    from diffusers.image_processor import VaeImageProcessor
    for i, shape in enumerate([base, dict(width=96, height=128, frames=17, fps=30),
                                dict(width=256, height=256, frames=33, fps=60)]):
        n = ((shape['frames'] - 1) // 8 + 1) * (shape['height'] // 32) * (shape['width'] // 32)
        tokens = np.arange(n * 128, dtype='<f4').reshape(1, n, 128) / 31
        source = directory / f'layout-{i}-input.f32'; target = directory / f'layout-{i}-output.f32'
        tokens.tofile(source)
        native(f'layout-{i}', dict(operation='unpatchify', **shape, input=str(source), output=str(target)))
        expected = SymmetricPatchifier(1).unpatchify(torch.from_numpy(tokens), shape['height'] // 32, shape['width'] // 32, 128).numpy()
        check(np.array_equal(np.fromfile(target, dtype='<f4'), expected.flatten()), 'Original patchifier layout differs')

    generator = np.random.default_rng(98349)
    for i, shape in enumerate([base, dict(width=96, height=64, frames=17, fps=30),
                                dict(width=256, height=256, frames=33, fps=60)]):
        floats = generator.uniform(-2, 2, (1, 3, shape['frames'], shape['height'], shape['width'])).astype('<f4')
        floats.flat[:7] = [-1, 0, 1, -2, 2, -.5, .5]
        source = directory / f'rgb-{i}-input.f32'; target = directory / f'rgb-{i}.lma'
        floats.tofile(source)
        record = native(f'rgb-{i}', dict(operation='frames', **shape, input=str(source), output=str(target)))
        expected = (VaeImageProcessor.denormalize(torch.from_numpy(floats))[0].permute(1, 2, 3, 0).numpy() * 255).astype(np.uint8)
        raw = target.read_bytes()
        check(raw[:8] == b'LMAFRM1\0' and struct.unpack('<5I', raw[8:28]) == (shape['width'], shape['height'], shape['frames'], shape['fps'], 3), 'Wrong portable frame header')
        check(raw[28:] == expected.tobytes(), 'Original normalization/uint8 conversion differs')
        check(record['bytes'] == len(raw) and record['clipped_low'] == int((floats < -1).sum()) and record['clipped_high'] == int((floats > 1).sum()), 'Frame size/clipping diagnostics differ')
        metrics.append(dict(kind='frames', shape=shape, rgb_max_error=0, bytes=len(raw)))

    for key, value in [('width', 32), ('width', 257), ('height', 65), ('frames', 0), ('frames', 10),
                       ('frames', 41), ('fps', 0), ('fps', 61), ('fps', True), ('width', 64.0),
                       ('seed', -1), ('seed', 2147483648), ('seed', True), ('cancel_file', ''),
                       ('operation', 'remote'), ('unknown', 1)]:
        name = 'invalid-' + key + '-' + str(len(guards)); request, a, b = noise(name)
        request[key] = value; native(name, request, False)
        check(not a.exists() and not b.exists(), 'Invalid request wrote noise outputs')
    request, a, b = noise('duplicate-key')
    raw = json.dumps(request)[:-1] + ',"seed":0}'
    native('duplicate-key', request, False, raw=raw)
    check(not a.exists() and not b.exists(), 'Duplicate key wrote outputs')
    request, a, b = noise('pre-cancel'); flag = directory / 'cancel.flag'; flag.touch(); request['cancel_file'] = str(flag)
    native('pre-cancel', request, False)
    check(not a.exists() and not b.exists(), 'Pre-cancel wrote outputs')
    request, a, b = noise('same-output'); request['noise'] = str(a)
    native('same-output', request, False); check(not a.exists(), 'Aliased outputs were created')
    request, a, b = noise('existing-output'); a.write_bytes(b'preserve-existing')
    native('existing-output', request, False)
    check(a.read_bytes() == b'preserve-existing' and not b.exists(), 'Existing output changed')
    request, a, b = noise('transaction-rollback'); request['noise'] = str(directory / 'absent' / 'output.f32')
    native('transaction-rollback', request, False)
    check(not a.exists(), 'Failed second noise write leaked first output')
    for operation, count in [('unpatchify', 1024), ('frames', 3 * 9 * 64 * 64)]:
        for kind in ('short', 'long', 'nan', 'infinity'):
            name = operation + '-' + kind; source = directory / (name + '.f32'); target = directory / (name + '.output')
            values = np.zeros(count + (1 if kind == 'long' else -1 if kind == 'short' else 0), dtype='<f4')
            if kind == 'nan': values[-1] = np.nan
            if kind == 'infinity': values[-1] = np.inf
            values.tofile(source)
            native(name, dict(operation=operation, **base, input=str(source), output=str(target)), False)
            check(not target.exists(), 'Invalid tensor wrote output')
        target = directory / (operation + '-preserve.output'); target.write_bytes(b'keep')
        native(operation + '-preserve', dict(operation=operation, **base, input=str(source), output=str(target)), False)
        check(target.read_bytes() == b'keep', 'Invalid tensor changed an existing output')
    current(before)
    result = dict(schema='lma.ltx098-tensors-tests/1', checks=checks, native_children=children, guards=guards,
                  metrics=metrics, executable_sha256=sha(EXE), original_patchifier_compared=True,
                  original_diffusers_normalization_compared=True, rng_matches_frozen_definition=True,
                  matches_pytorch_seed=False, model_inference=False, model_data_embedded=False,
                  engine_registered=False, packaged_in_apk=False, physical_android=False,
                  input_fingerprint=before)
    receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('checks', 'native_children', 'model_inference', 'physical_android')}), flush=True)


if __name__ == '__main__': run()
