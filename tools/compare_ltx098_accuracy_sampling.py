"""Run/review one high-accuracy candidate's partial original video trajectory.

The frozen latent gate is evaluated and a failure returns exit 1 after evidence
is saved. This does not execute VAE, accept a complete video, or change App code.
"""
import argparse
import json
import time
import uuid
from pathlib import Path

from evidence import current, fingerprint
from experiment_ltx098_text_accuracy import inputs as precision_inputs
from experiment_ltx098_text_order import inputs as order_inputs
from experiment_ltx098_text_staging import inputs as staging_inputs
from experiment_ltx098_text_f32 import inputs as f32_inputs
from fetch_ltx098_text import sha
from ltx098_pipeline import SAMPLER, DIT, inputs as pipeline_inputs
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**pipeline_inputs(), **precision_inputs(), **order_inputs(), **staging_inputs(), **f32_inputs(),
            **fingerprint('tools/compare_ltx098_accuracy_sampling.py')}


def candidate_details(variant):
    if variant == 'f32':
        return ROOT / 'build/ltx098-text-f32-experiments/results.json', f32_inputs()
    if variant == 'staging':
        return ROOT / 'build/ltx098-text-staging-experiments/baseline-results.json', staging_inputs()
    if variant == 'order':
        return ROOT / 'build/ltx098-text-order-experiments/results.json', order_inputs()
    if variant in ['norm', 'activation']:
        return ROOT / 'build/ltx098-text-accuracy-experiments' / (variant + '-results.json'), precision_inputs()
    raise ValueError('Unsupported numerical candidate')


def compare(variant, reference, case_index=0, capture=None):
    before = inputs(); reference = reference.resolve()
    if not reference.is_relative_to(ROOT / 'build'): raise ValueError('Reference must stay below build/')
    baseline = json.loads((ROOT / 'verification/development/ltx098-pipeline.json').read_text(encoding='utf-8'))
    candidate_path, expected_inputs = candidate_details(variant)
    candidate = json.loads(candidate_path.read_text(encoding='utf-8'))
    current(baseline['input_fingerprint']); current(candidate['input_fingerprint'])
    if candidate['input_fingerprint'] != expected_inputs or not candidate['aba_bitwise_identical']:
        raise ValueError('Require current trained A/B/A candidate')
    if (not candidate['linear_f64'] or candidate['normalization_f64'] != (variant not in ['staging', 'f32']) or
        candidate['activation_f64'] != (variant == 'activation')): raise ValueError('Wrong accuracy candidate variant')
    if variant in ['order', 'staging', 'f32'] and not candidate['activation_original_order']: raise ValueError('Wrong activation order')
    if variant == 'staging' and candidate['normalization'] != 'baseline': raise ValueError('Wrong normalization staging')
    if variant == 'f32' and not candidate['normalization_f32_staged']: raise ValueError('Wrong F32 normalization')
    oracle = json.loads((reference / 'references.json').read_text(encoding='utf-8'))
    current(oracle['input_fingerprint'])
    if oracle != baseline['original_oracle']: raise ValueError('Wrong original video oracle')
    source = ROOT / baseline['captured_native_pipelines'][case_index]
    if sha(source / 'pipeline.json') != baseline['captured_native_record_sha256'][case_index]:
        raise ValueError('Changed baseline real-prompt case')
    import numpy as np
    expected = json.loads((source / 'sampling.json').read_text(encoding='utf-8'))
    caption = ROOT / candidate['output_directory'] / ('case-' + str(case_index) + '/caption.f32')
    if sha(caption) != candidate['jobs'][case_index]['caption_sha256']: raise ValueError('Changed candidate caption')
    expected['context'] = np.fromfile(caption, dtype='<f4').tolist()
    expected.pop('trace_dir', None)
    model_identity = next(item for item in baseline['jobs'][case_index]['assets'] if item['file'] == DIT.name)
    model_hash = sha(DIT); binary_hash = sha(SAMPLER)
    if DIT.stat().st_size != model_identity['bytes'] or model_hash != model_identity['sha256']:
        raise ValueError('Changed frozen trained DiT asset')
    if capture is None:
        capture = ROOT / 'build/ltx098-text-accuracy-sampling' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
        capture.mkdir(parents=True, exist_ok=False)
        request = dict(expected, trace_dir=str(capture / 'trace'))
        (capture / 'request.json').write_text(json.dumps(request), encoding='utf-8')
        result, seconds, resources = execute([str(SAMPLER), str(DIT), str(capture / 'request.json'),
                                             str(capture / 'latents.f32'), 'vulkan', '4'], timeout=1800, observe=True)
        (capture / 'native.log').write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError('Inspect captured sampler native.log')
        native = json.loads(result.stdout.decode('utf-8'))
        reused = False
    else:
        capture = capture.resolve()
        if not capture.is_relative_to(ROOT / 'build'): raise ValueError('Capture must stay below build/')
        record = json.loads((capture / 'results.json').read_text(encoding='utf-8'))
        native, seconds, resources = record['native'], record['seconds'], record['resources']
        if record['native_binary_sha256'] != binary_hash or record['model_sha256'] != model_hash:
            raise ValueError('Changed captured sampler/model')
        for name, identity in record['files'].items():
            path = capture / name
            if not path.is_relative_to(capture) or path.stat().st_size != identity['bytes'] or sha(path) != identity['sha256']:
                raise ValueError('Changed native sampling capture')
        logged = json.loads((capture / 'native.log').read_text(encoding='utf-8').splitlines()[0])
        if logged != native: raise ValueError('Captured sampler metadata differs from native log')
        reused = True
    request = json.loads((capture / 'request.json').read_text(encoding='utf-8'))
    if Path(request.pop('trace_dir')).resolve() != (capture / 'trace').resolve() or request != expected:
        raise ValueError('Captured sampler request differs from frozen baseline plus candidate caption')
    build = json.loads((ROOT / 'build/ltx098-host-vulkan/receipt.json').read_text(encoding='utf-8'))
    current(build['input_fingerprint'])
    if binary_hash != build['sampler_binary_sha256']: raise ValueError('Wrong native sampler')
    if not native['ok'] or not native['model_executed'] or native['backend'] != 'vulkan' or native['fixture']:
        raise ValueError('Incomplete trained Vulkan execution')
    if native['layers'] != 28 or native['steps'] != 8 or native['parameters'] != 1923385472:
        raise ValueError('Wrong old-LTX architecture/trajectory')
    metrics = []; artifacts = {}
    original = oracle['cases'][case_index]
    for step in range(8):
        name = 'sampling-step-' + str(step) + '.f32'; original_path = reference / original['name'] / name
        identity = original['files'][name]
        if original_path.stat().st_size != identity['bytes'] or sha(original_path) != identity['sha256']:
            raise ValueError('Changed original trajectory')
        path = capture / 'trace' / ('step-' + str(step) + '.f32')
        if path.stat().st_size != identity['bytes']: raise ValueError('Wrong native trajectory shape')
        left = np.fromfile(path, dtype='<f4').astype(np.float64)
        right = np.fromfile(original_path, dtype='<f4').astype(np.float64)
        if not np.isfinite(left).all() or not np.isfinite(right).all(): raise ValueError('Nonfinite trajectory')
        delta = left - right
        metrics.append(dict(step=step, max_abs=float(abs(delta).max()),
                            relative_rmse=float(np.linalg.norm(delta) / np.linalg.norm(right)),
                            cosine=float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))))
        artifacts[path.relative_to(capture).as_posix()] = dict(bytes=path.stat().st_size, sha256=sha(path))
    if sha(capture / 'latents.f32') != artifacts['trace/step-7.f32']['sha256']:
        raise ValueError('Final output differs from final traced step')
    for name in ['request.json', 'latents.f32', 'native.log']:
        path = capture / name; artifacts[name] = dict(bytes=path.stat().st_size, sha256=sha(path))
    gates = baseline['gates']; final = metrics[-1]
    accepted = (final['max_abs'] <= gates['full_chain_max_absolute_error'] and
                final['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and
                final['cosine'] >= gates['full_chain_min_cosine'])
    current(before)
    report = dict(schema='lma.ltx098-accuracy-sampling/1', variant=variant, case=case_index, metrics=metrics,
                  gates=gates, latent_gate_passed=accepted, native=native, seconds=seconds, resources=resources,
                  capture_directory=capture.relative_to(ROOT).as_posix(), captured_native_children=1, capture_reused=reused, native_children_executed_this_invocation=0 if reused else 1,
                  candidate_sha256=sha(candidate_path), candidate_caption_sha256=sha(caption),
                  native_binary_sha256=binary_hash, model_sha256=model_hash, files=artifacts, original_case=original,
                  original_trajectory_files_verified=8, vae_executed=False, different_prompt_video_checked=False,
                  full_pipeline_accepted=False, physical_android=False, packaged_in_apk=False,
                  acceptance_gates_changed=False, input_fingerprint=before)
    out = ROOT / 'build/ltx098-text-accuracy-sampling'; out.mkdir(exist_ok=True)
    (capture / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (out / (variant + '-case-' + str(case_index) + '-results.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(variant=variant, case=case_index, latent_gate_passed=accepted, final=final, capture_reused=reused)), flush=True)
    return 0 if accepted else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', choices=['norm', 'activation', 'order', 'staging', 'f32'], required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--case', type=int, choices=[0, 1], default=0)
    parser.add_argument('--capture', type=Path, help='Validate an existing worker capture instead of executing again')
    args = parser.parse_args()
    raise SystemExit(compare(args.variant, args.reference, args.case, args.capture))
