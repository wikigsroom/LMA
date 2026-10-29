"""Measure the publisher-modulation candidate using frozen eight-step inputs.

Reference-caption runs are explicitly diagnostic and never model acceptance.
They do not enter an App, native production pipeline, or candidate video gate.
"""
import argparse
import json
import time
import uuid
from pathlib import Path

from compare_ltx098_accuracy_sampling import candidate_details
from diagnose_ltx098_sampling_context import inputs as context_inputs
from build_ltx098_modulation import build, inputs as compute_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import sha
from ltx098_pipeline import DIT, SAMPLER
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**context_inputs(), **compute_inputs(), **fingerprint('tools/test_ltx098_modulation.py')}


def run(reference, case_index, context, backend, capture=None):
    before = inputs(); reference = reference.resolve()
    if not reference.is_relative_to(ROOT / 'build'): raise ValueError('Reference must stay below build/')
    baseline = json.loads((ROOT / 'verification/development/ltx098-pipeline.json').read_text(encoding='utf-8'))
    current(baseline['input_fingerprint'])
    oracle = json.loads((reference / 'references.json').read_text(encoding='utf-8'))
    current(oracle['input_fingerprint'])
    if oracle != baseline['original_oracle']: raise ValueError('Different original reference')
    original = oracle['cases'][case_index]
    source = ROOT / baseline['captured_native_pipelines'][case_index]
    if sha(source / 'pipeline.json') != baseline['captured_native_record_sha256'][case_index]: raise ValueError('Changed baseline capture')
    request = json.loads((source / 'sampling.json').read_text(encoding='utf-8')); request.pop('trace_dir', None)
    if context == 'reference':
        caption = reference / original['name'] / 'caption.f32'
        if sha(caption) != original['files']['caption.f32']['sha256']: raise ValueError('Changed original caption')
        caption_record = None
    else:
        candidate_path, expected_inputs = candidate_details(context)
        candidate = json.loads(candidate_path.read_text(encoding='utf-8')); current(candidate['input_fingerprint'])
        if candidate['input_fingerprint'] != expected_inputs or not candidate['aba_bitwise_identical']:
            raise ValueError('Require current trained caption')
        caption = ROOT / candidate['output_directory'] / ('case-' + str(case_index)) / 'caption.f32'
        if sha(caption) != candidate['jobs'][case_index]['caption_sha256']: raise ValueError('Changed native caption')
        caption_record = sha(candidate_path)
    import numpy as np
    request['context'] = np.fromfile(caption, dtype='<f4').tolist()
    identity = next(item for item in baseline['jobs'][case_index]['assets'] if item['file'] == DIT.name)
    if DIT.stat().st_size != identity['bytes'] or sha(DIT) != identity['sha256']: raise ValueError('Changed trained DiT')
    executable, compilation = build()
    binary = sha(executable)
    if capture:
        capture = capture.resolve()
        if not capture.is_relative_to(ROOT / 'build'): raise ValueError('Capture must stay below build/')
        raw = json.loads((capture / 'capture.json').read_text(encoding='utf-8'))
        if raw['native_binary_sha256'] != binary or raw['model_sha256'] != identity['sha256']:
            raise ValueError('Changed captured executable/model')
        native, seconds, resources = raw['native'], raw['seconds'], raw['resources']
        for name, file in raw['files'].items():
            path = capture / name
            if not path.resolve().is_relative_to(capture) or path.stat().st_size != file['bytes'] or sha(path) != file['sha256']: raise ValueError('Changed diagnostic capture')
        if json.loads((capture / 'native.log').read_text(encoding='utf-8').splitlines()[0]) != native:
            raise ValueError('Captured native metadata differs from log')
        reused = True
    else:
        capture = ROOT / 'build/ltx098-modulation-tests' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        capture.mkdir(parents=True, exist_ok=False)
        actual = dict(request, trace_dir=str(capture / 'trace'))
        (capture / 'request.json').write_text(json.dumps(actual), encoding='utf-8')
        print('Execute modulation-order candidate', compilation['mode'], backend, context, 'case', case_index, flush=True)
        process, seconds, resources = execute([str(executable), str(DIT), str(capture / 'request.json'),
                                             str(capture / 'latents.f32'), backend, '4'], timeout=3600, observe=True)
        (capture / 'native.log').write_bytes(process.stdout + process.stderr)
        if process.returncode: raise RuntimeError('Inspect diagnostic native.log')
        native = json.loads(process.stdout.decode('utf-8')); reused = False
    actual = json.loads((capture / 'request.json').read_text(encoding='utf-8'))
    if Path(actual.pop('trace_dir')).resolve() != (capture / 'trace').resolve() or actual != request:
        raise ValueError('Different diagnostic request')
    if (not native['ok'] or not native['model_executed'] or native['fixture'] or native['backend'] != backend or
        native['layers'] != 28 or native['steps'] != 8 or native['parameters'] != 1923385472):
        raise ValueError('Incomplete/wrong native diagnostic')
    if native.get('explicit_f32_matmul_operands') is not True or native['precision_policy'] != 'explicit_f32_matmul_' + compilation['mode']:
        raise ValueError('Wrong compute precision candidate')
    if native.get('publisher_modulation_order') is not True: raise ValueError('Wrong modulation order')
    metrics = []; files = {}
    for step in range(8):
        name = 'sampling-step-' + str(step) + '.f32'; expected = reference / original['name'] / name
        if sha(expected) != original['files'][name]['sha256']: raise ValueError('Changed original trajectory')
        path = capture / 'trace' / ('step-' + str(step) + '.f32')
        left = np.fromfile(path, dtype='<f4').astype(np.float64); right = np.fromfile(expected, dtype='<f4').astype(np.float64)
        if left.shape != right.shape or not left.size or not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError('Invalid diagnostic trajectory')
        delta = left - right
        metrics.append(dict(step=step, max_abs=float(abs(delta).max()), relative_rmse=float(np.linalg.norm(delta) / np.linalg.norm(right)),
                            cosine=float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))))
        files[path.relative_to(capture).as_posix()] = dict(bytes=path.stat().st_size, sha256=sha(path))
    if sha(capture / 'latents.f32') != files['trace/step-7.f32']['sha256']: raise ValueError('Final/trace mismatch')
    for name in ['request.json', 'native.log', 'latents.f32']:
        path = capture / name; files[name] = dict(bytes=path.stat().st_size, sha256=sha(path))
    raw = dict(native=native, seconds=seconds, resources=resources, files=files,
               native_binary_sha256=binary, model_sha256=identity['sha256'])
    (capture / 'capture.json').write_text(json.dumps(raw, indent=2) + '\n', encoding='utf-8')
    current(before); gates = baseline['gates']; final = metrics[-1]
    report = dict(schema='lma.ltx098-modulation-sampling/1', context=context, backend=backend, case=case_index,
                  metrics=metrics, gates=gates, native=native, seconds=seconds, resources=resources, files=files,
                  explicit_f32_matmul_operands=True, publisher_modulation_order=True, compilation=compilation,
                  original_case=original, baseline_request=baseline['jobs'][case_index]['request'],
                  latent_gate_matched=final['max_abs'] <= gates['full_chain_max_absolute_error'] and final['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and final['cosine'] >= gates['full_chain_min_cosine'],
                  reference_caption_supplied=context == 'reference', candidate_record_sha256=caption_record,
                  caption_sha256=sha(caption), native_binary_sha256=binary, model_sha256=identity['sha256'],
                  captured_native_children=1, native_children_executed_this_invocation=0 if reused else 1,
                  capture_reused=reused, capture_directory=capture.relative_to(ROOT).as_posix(),
                  diagnostic_only=True, model_stage_accepted=False, full_pipeline_accepted=False,
                  physical_android=False, packaged_in_apk=False, engine_registered=False,
                  acceptance_gates_changed=False, input_fingerprint=before)
    out = ROOT / 'build/ltx098-modulation-tests'
    name = compilation['mode'] + '-' + backend + '-' + context + '-case-' + str(case_index) + '-results.json'
    (out / name).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(backend=backend, context=context, case=case_index, final=final,
                          diagnostic_only=True, latent_gate_matched=report['latent_gate_matched'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--case', type=int, choices=[0, 1], required=True)
    parser.add_argument('--context', choices=['reference', 'f32', 'staging', 'order', 'activation'], required=True)
    parser.add_argument('--backend', choices=['cpu', 'vulkan'], required=True)
    parser.add_argument('--capture', type=Path)
    args = parser.parse_args()
    run(args.reference, args.case, args.context, args.backend, args.capture)
