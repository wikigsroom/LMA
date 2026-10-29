"""Run the native preparer on the complete trained UNet, then inspect its small output."""
import hashlib
import json
import os
from pathlib import Path
import struct
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


def main():
    torch.set_num_threads(1)
    before = inputs() | fingerprint('tools/test_lcm_preparation_trained.py', 'tools/lcm_prepare_data.py', 'tools/sd_variants_capture.py')
    contract = json.loads((ROOT / 'research/lcm_prepare/contract.json').read_text(encoding='utf-8'))
    asset = contract['source']
    source = ROOT / 'build/sd-distilled-asset-probe/originals' / asset['sha256'] / Path(asset['path']).name
    if source.stat().st_size != asset['bytes']:
        raise ValueError('Explicitly acquired complete trained source required; no implicit download')
    initial = (source.stat().st_size, source.stat().st_mtime_ns)
    with source.open('rb') as stream:
        prefix = stream.read(8)
        count = struct.unpack('<Q', prefix)[0]
        if count != contract['source_header_bytes']:
            raise ValueError('Source header byte contract')
        encoded = stream.read(count)
    if hashlib.sha256(encoded).hexdigest() != contract['source_header_sha256']:
        raise ValueError('Source header identity')
    header = json.loads(encoded.decode('utf-8'))
    tensors = {}
    for name in ['time_embedding.cond_proj.weight', 'time_embedding.linear_1.weight', 'time_embedding.linear_1.bias']:
        tensor = header[name]
        if tensor['dtype'] != 'F32': raise ValueError('Original source F32 required')
        start, end = tensor['data_offsets']
        with source.open('rb') as stream:
            stream.seek(8 + count + start)
            raw = stream.read(end - start)
        tensors[name] = np.frombuffer(raw, dtype='<f4').copy().reshape(tensor['shape'])
    binary, compilation = build()
    parent = ROOT / 'build/lcm-preparation-trained'
    parent.mkdir(exist_ok=True)
    directory = parent / ('run-' + str(time.time_ns()))
    directory.mkdir()
    request = dict(operation='fold_condition_bias', checkpoint=str(source), expected_source_bytes=asset['bytes'],
                   expected_source_sha256=asset['sha256'], storage_root=str(directory), output_name='prepared', max_output_bytes=65536)
    path = directory / 'request.json'
    path.write_text(json.dumps(request, indent=2) + '\n', encoding='utf-8')
    print('Stream and verify complete trained UNet: ' + directory.relative_to(ROOT).as_posix(), flush=True)
    capture, logs = execute([str(binary), str(path)], os.environ.copy(), timeout=7200)
    for suffix, data in zip(['stdout', 'stderr'], logs): (directory / ('prepare.' + suffix)).write_bytes(data)
    receipts = [e for e in capture['events'] if 'ok' in e]
    if (capture['returncode'] != 0 or capture['timed_out'] or capture['protocol_errors'] or any(capture['logs_truncated'])
            or len(receipts) != 1 or not receipts[0].get('ok')):
        (directory / 'failed-capture.json').write_text(json.dumps(capture, indent=2) + '\n', encoding='utf-8')
        raise RuntimeError('Inspect retained trained preparation capture')
    receipt = receipts[0]
    if (not receipt['source_sha256_verified'] or receipt['source_sha256'] != asset['sha256']
            or receipt['source_streamed_bytes'] != asset['bytes'] or receipt['fixture']):
        raise ValueError('Complete trained source was not verified')
    output_path = directory / 'prepared/lcm-condition-bias.gguf'
    output = inspect(output_path.read_bytes())
    if output['sha256'] != receipt['output_sha256'] or output['bytes'] != receipt['output_bytes']:
        raise ValueError('Native output read-back identity')
    guidance = np.array(contract['guidance_u32_le'], dtype='<u4').view('<f4')
    cond = tensors['time_embedding.cond_proj.weight']
    weight = tensors['time_embedding.linear_1.weight'].astype('f2').astype('f4')
    bias = tensors['time_embedding.linear_1.bias']
    offset = np.array([sum(float(v) * float(g) for v, g in zip(row, guidance)) for row in cond], dtype='f4')
    delta = np.array([sum(float(v) * float(g) for v, g in zip(row, offset)) for row in weight], dtype='f4')
    expected = (bias + delta).astype('<f4')
    measured = np.frombuffer(output['payload'], dtype='<f4')
    if not np.array_equal(expected.view('u4'), measured.view('u4')):
        raise ValueError('Native trained folding differs from independent fixed-order oracle')
    torch_reference = torch.from_numpy(bias) + torch.nn.functional.linear(
        torch.nn.functional.linear(torch.from_numpy(guidance.copy()), torch.from_numpy(cond)), torch.from_numpy(weight))
    maximum = float(np.max(np.abs(torch_reference.numpy().astype('f8') - measured.astype('f8'))))
    if maximum > 1e-6:
        raise ValueError('Trained folded bias differs from official-equation FP32 reference')
    # Check the nonlinear first time-MLP stage at deterministic inputs. Full official
    # UNet/image equivalence remains a separate gate, never inferred from this subgraph.
    samples = np.random.default_rng(42).normal(size=(6, 320)).astype('f4')
    with torch.inference_mode():
        x = torch.from_numpy(samples)
        w = torch.from_numpy(weight)
        b = torch.from_numpy(bias)
        condition = torch.nn.functional.linear(torch.from_numpy(guidance.copy()), torch.from_numpy(cond))
        conditioned = torch.nn.functional.silu(torch.nn.functional.linear(x + condition, w, b))
        folded = torch.nn.functional.silu(torch.nn.functional.linear(x, w, torch.from_numpy(measured.copy())))
    nonlinear_max = float((conditioned - folded).abs().max())
    if nonlinear_max > 2e-6:
        raise ValueError('Trained nonlinear time projection tolerance')
    if initial != (source.stat().st_size, source.stat().st_mtime_ns):
        raise ValueError('Original source changed during preparation')
    current(before)
    capture.update(name='complete-trained-source-preparation', passed=True)
    (directory / 'capture.json').write_text(json.dumps(capture, indent=2) + '\n', encoding='utf-8')
    report = dict(schema='lma.lcm-native-preparation-trained/1', passed=True, compilation=compilation, source=asset,
                  source_complete_sha256_verified=True, source_retained=True, trained_parameters_used=492800,
                  source_parameter_bytes_selected=1971200, output=dict(path=output_path.relative_to(ROOT).as_posix(),
                      bytes=output['bytes'], sha256=output['sha256'], payload_sha256=output['payload_sha256'], payload_bytes=5120),
                  native_scalar_values_match_independent_oracle=True, numerical_max_abs_vs_torch=maximum,
                  nonlinear_subgraph_max_abs=nonlinear_max, numerical_gate=1e-6, nonlinear_gate=2e-6,
                  capture=capture, capture_directory=directory.relative_to(ROOT).as_posix(), input_fingerprint=before,
                  production_app_integrated=False, physical_android=False, model_inference=False,
                  complete_unet_forward=False, canonical_pipeline_equivalence_proven=False,
                  image_quality_accepted=False, complete_release_accepted=False)
    (directory / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (parent / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, output=report['output'], numerical_max_abs_vs_torch=maximum, nonlinear_subgraph_max_abs=nonlinear_max)))


if __name__ == '__main__': main()
