"""Exercise real native preparation transactions, numerical folding and rejection paths."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import numpy as np
import torch

from build_lcm_prepare import build, inputs
from evidence import current, fingerprint
from lcm_prepare_data import inspect
from sd_variants_capture import execute

ROOT = Path(__file__).resolve().parents[1]


def source_file(path, arrays, edit=None):
    header = {'__metadata__': {'format': 'pt'}}
    payload = bytearray()
    for name, array in arrays.items():
        raw = array.astype('<f4').tobytes()
        header[name] = dict(dtype='F32', shape=list(array.shape), data_offsets=[len(payload), len(payload) + len(raw)])
        payload.extend(raw)
    if edit: edit(header)
    encoded = json.dumps(header, separators=(',', ':')).encode('utf-8')
    path.write_bytes(struct.pack('<Q', len(encoded)) + encoded + payload)
    return dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    torch.set_num_threads(1)
    before = inputs() | fingerprint('tools/test_lcm_prepare.py', 'tools/lcm_prepare_data.py', 'tools/sd_variants_capture.py')
    binary, compilation = build()
    parent = ROOT / 'build/lcm-preparation-tests'
    parent.mkdir(exist_ok=True)
    directory = parent / ('run-' + str(time.time_ns()))
    directory.mkdir()
    fixture = directory / 'conditioned.safetensors'
    rng = np.random.default_rng(42)
    arrays = {'time_embedding.cond_proj.weight': rng.normal(0, .025, (320, 256)).astype('f4'),
              'time_embedding.linear_1.weight': rng.normal(0, .02, (1280, 320)).astype('f4'),
              'time_embedding.linear_1.bias': rng.normal(0, .01, 1280).astype('f4')}
    identity = source_file(fixture, arrays)
    command = dict(operation='fold_condition_bias', checkpoint=str(fixture), expected_source_bytes=identity['bytes'],
                   expected_source_sha256=identity['sha256'], storage_root=str(directory), output_name='success', max_output_bytes=64 * 1024)
    cases = []
    checks = 0

    def require(ok, message):
        nonlocal checks
        checks += 1
        if not ok: raise AssertionError(message)

    def run(name, request=None, error=None, fixture_mode=True, raw=None, cancel=False):
        request = copy.deepcopy(command if request is None else request)
        request['output_name'] = request.get('output_name', name)
        path = directory / (name + '.json')
        path.write_text(json.dumps(request) if raw is None else raw, encoding='utf-8')
        arguments = [str(binary)] + (['--fixture'] if fixture_mode else []) + [str(path)]
        if cancel:
            start = time.perf_counter()
            child = subprocess.Popen(arguments, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                first = child.stderr.readline()
                event = json.loads(first)
                require(event['phase'] == 'verify_source', 'Cancellation must follow an actual native progress event')
                Path(request['cancel_file']).write_text('cancel', encoding='utf-8')
                stdout, stderr = child.communicate(timeout=15)
                logs = [stdout, first + stderr]
                result = dict(returncode=child.returncode, seconds=time.perf_counter() - start, timed_out=False, protocol_errors=[],
                              logs_truncated=[False, False], events=[json.loads(line) for line in stdout.splitlines()],
                              cancel_after_native_progress=True)
            finally:
                if child.poll() is None: child.kill(); child.wait(timeout=10)
                if child.stdout: child.stdout.close()
                if child.stderr: child.stderr.close()
        else:
            result, logs = execute(arguments, os.environ.copy(), timeout=120)
        for suffix, data in zip(['stdout', 'stderr'], logs): (directory / (name + '.' + suffix)).write_bytes(data)
        require(not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated']), name + ' protocol / timeout')
        terminal = [e for e in result['events'] if 'ok' in e]
        require(len(terminal) == 1, name + ' terminal receipt')
        receipt = terminal[0]
        if error is None:
            require(result['returncode'] == 0 and receipt['ok'], name + ' success')
            output = directory / request['output_name'] / receipt['output_file']
            parsed = inspect(output.read_bytes())
            require(parsed['sha256'] == receipt['output_sha256'] and parsed['bytes'] == receipt['output_bytes'], 'Output hash / bytes')
            require(receipt['source_sha256_verified'] and receipt['source_sha256'] == identity['sha256'], 'Whole source identity')
        else:
            require(result['returncode'] == 1 and not receipt['ok'] and error in receipt['error'], name + ' expected rejection: ' + str(receipt))
        result.update(name=name, expected_error=error, passed=True)
        (directory / (name + '-capture.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        cases.append(result)
        return receipt

    receipt = run('success')
    output = inspect((directory / 'success/lcm-condition-bias.gguf').read_bytes())
    contract = json.loads((ROOT / 'research/lcm_prepare/contract.json').read_text(encoding='utf-8'))
    guidance = np.array(contract['guidance_u32_le'], dtype='<u4').view('<f4')
    cond = arrays['time_embedding.cond_proj.weight']
    weight = arrays['time_embedding.linear_1.weight'].astype('f2').astype('f4')
    bias = arrays['time_embedding.linear_1.bias']
    # An independent F64 accumulation oracle; all products of two F32s are exact in F64.
    offset = np.array([sum(float(v) * float(g) for v, g in zip(row, guidance)) for row in cond], dtype='f4')
    delta = np.array([sum(float(v) * float(g) for v, g in zip(row, offset)) for row in weight], dtype='f4')
    expected = (bias + delta).astype('<f4')
    measured = np.frombuffer(output['payload'], dtype='<f4')
    require(np.array_equal(expected.view('u4'), measured.view('u4')), 'Every native output scalar matches independent fixed-order oracle')
    torch_reference = torch.from_numpy(bias) + torch.nn.functional.linear(
        torch.nn.functional.linear(torch.from_numpy(guidance.copy()), torch.from_numpy(cond)), torch.from_numpy(weight))
    maximum = float(np.max(np.abs(torch_reference.numpy().astype('f8') - measured.astype('f8'))))
    require(maximum <= 1e-6, 'Equivalent two-linear conditioning fold tolerance')
    require(len(output['metadata']) == 6 and output['metadata']['lma.overlay.base_sha256'] == contract['base']['sha256'], 'Source-bound metadata')
    require(receipt['payload_bytes'] == 5120 and not receipt['whole_checkpoint_allocated'], 'Small derived output')
    repeat = copy.deepcopy(command); repeat['output_name'] = 'repeat'
    again = run('repeat', repeat)
    require(receipt['output_sha256'] == again['output_sha256'], 'Deterministic repeated preparation')

    controls = [
        ('unknown-operation', {'operation': 'other'}, 'Unknown preparation operation'),
        ('unknown-field', {'remote': 'https://example.invalid'}, 'Unknown field'),
        ('wrong-bytes', {'expected_source_bytes': identity['bytes'] + 1}, 'Source byte/hash identity mismatch'),
        ('wrong-sha', {'expected_source_sha256': '0' * 64}, 'Source SHA-256 mismatch'),
        ('bad-sha', {'expected_source_sha256': 'g' * 64}, 'Source byte/hash identity mismatch'),
        ('small-budget', {'max_output_bytes': 1}, 'Output exceeds selected storage budget'),
        ('large-budget', {'max_output_bytes': 65537}, 'Integer outside budget'),
        ('unsafe-output', {'output_name': '../escape'}, 'Invalid output basename'),
        ('reserved-output', {'output_name': 'CON'}, 'Reserved output basename'),
        ('remote-source', {'checkpoint': 'https://example.invalid/model'}, 'Expected local path'),
        ('remote-storage', {'storage_root': 'https://example.invalid/output'}, 'Expected local path'),
        ('existing-output', {'output_name': 'success'}, 'Output directory already exists')]
    for name, patch, error in controls:
        request = copy.deepcopy(command);request['output_name'] = name;request.update(patch)
        run(name, request, error)
    run('unsigned-production-source', error='No signed conditioning contract for this source', fixture_mode=False)
    raw = json.dumps(command)[:-1] + ',"operation":"fold_condition_bias"}'
    run('duplicate-field', error='Duplicate JSON key', raw=raw)
    for name, mutation, error in [
        ('wrong-shape', lambda h: h['time_embedding.cond_proj.weight'].update(shape=[256,320]), 'Conditioning tensor shape mismatch'),
        ('wrong-dtype', lambda h: h['time_embedding.linear_1.bias'].update(dtype='F16'), 'Conditioned source must contain original F32 tensors'),
        ('overlap', lambda h: h['time_embedding.linear_1.bias'].update(data_offsets=[0,5120]), 'Tensor ranges overlap'),
        ('missing-tensor', lambda h: h.pop('time_embedding.linear_1.bias'), 'Missing conditioning tensor')]:
        changed = directory / (name + '.safetensors'); record = source_file(changed, arrays, mutation)
        request = copy.deepcopy(command);request.update(checkpoint=str(changed), expected_source_bytes=record['bytes'], expected_source_sha256=record['sha256'], output_name=name)
        run(name, request, error)
    nonfinite = {name: value.copy() for name, value in arrays.items()};nonfinite['time_embedding.linear_1.bias'][0] = np.nan
    changed = directory / 'nonfinite.safetensors'; record = source_file(changed, nonfinite)
    request = copy.deepcopy(command);request.update(checkpoint=str(changed), expected_source_bytes=record['bytes'], expected_source_sha256=record['sha256'], output_name='nonfinite')
    run('nonfinite', request, 'Non-finite trained parameter')
    cancel_file = directory / 'cancel'
    request = copy.deepcopy(command);request.update(cancel_file=str(cancel_file), output_name='cancel-during-hash')
    run('cancel-during-hash', request, 'Cancelled', cancel=True)
    run('cancel-before-start', request, 'Cancelled')
    recovery = copy.deepcopy(command);recovery['output_name'] = 'recovery'
    recovered = run('recovery', recovery)
    require(recovered['output_sha256'] == receipt['output_sha256'], 'Failure / cancellation recovery')
    require(hashlib.sha256(fixture.read_bytes()).hexdigest() == identity['sha256'], 'Source retained unchanged')
    require(not list(directory.glob('.ltx098-prepare-*')), 'No owned incomplete transaction remains')
    for case in cases:
        if case['expected_error'] is not None and case['name'] not in ('existing-output','unsigned-production-source','duplicate-field'):
            require(not (directory / case['name']).exists(), 'Rejected operation left a committed output')
    current(before)
    report = dict(schema='lma.lcm-native-preparation-tests/1', passed=True, checks=checks, actual_native_children=len(cases),
                  synthetic_parameters=True, trained_weights_loaded=False, numerical_max_abs_vs_torch=maximum,
                  native_scalar_values_match_independent_oracle=True, cancellation_after_native_progress=True,
                  output_bytes=output['bytes'], payload_bytes=5120, repeat_recovery_sha256=receipt['output_sha256'],
                  cases=cases, compilation=compilation, capture_directory=directory.relative_to(ROOT).as_posix(),
                  input_fingerprint=before, production_app_integrated=False, physical_android=False,
                  model_inference=False, complete_release_accepted=False)
    (directory / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (parent / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, checks=checks, actual_native_children=len(cases), numerical_max_abs_vs_torch=maximum)))


if __name__ == '__main__': main()
