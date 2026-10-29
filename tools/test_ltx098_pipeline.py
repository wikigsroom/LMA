"""Real-prompt trained single-scale pipeline A/B/A and original-forward parity.

Host development evidence only. Never promotes the pipeline to an APK engine or
claims Android resource limits, default multi-scale fidelity, or video quality.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
import numpy as np
from evidence import current, fingerprint
from ltx098_pipeline import Runner, inputs as pipeline_inputs, validate, sha, SAMPLER
from ltx098_pipeline_oracle import generate as original_references, inputs as oracle_inputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/ltx098-pipeline-tests'
PROMPT_A = 'A bright red balloon floats slowly from left to right against a clear blue sky. The camera stays still. Soft daylight illuminates the round balloon. Its thin white string sways gently in the breeze. Continuous smooth motion, realistic lighting.'
PROMPT_B = 'A small blue toy car drives slowly from right to left across a flat white tabletop. The camera stays still. Soft daylight illuminates the blue body and black wheels. A plain pale grey wall fills the background. Continuous smooth motion, realistic lighting.'


def run(initial=None, reuse=None, reference=None, conditioning_capture=None):
    OUT.mkdir(exist_ok=True); result_path = OUT / 'results.json'; result_path.unlink(missing_ok=True)
    before = {**oracle_inputs(), **fingerprint('tools/test_ltx098_pipeline.py')}
    directory = Path(tempfile.mkdtemp(prefix='run-', dir=OUT))
    checks = 0; guards = []; metrics = []; failures = []
    def check(value, message):
        nonlocal checks
        if not value: raise AssertionError(message)
        checks += 1
    def numerical_check(value, message):
        nonlocal checks
        checks += 1
        if not value: failures.append(message)
    base = dict(prompt=PROMPT_A, seed=42, width=256, height=256, frames=33, fps=24)
    for key, value in [('prompt', ''), ('prompt', ' '), ('prompt', 'a' * 65537), ('prompt', 5),
                       ('seed', -1), ('seed', 2147483648), ('seed', True), ('width', 32), ('width', 257),
                       ('height', 65), ('frames', 1), ('frames', 10), ('frames', 41),
                       ('fps', 0), ('fps', 61), ('fps', 24.0), ('cancel_file', ''), ('unknown', 'remote')]:
        try: validate(base | {key: value})
        except ValueError: guards.append(key + '-' + str(len(guards)))
        else: raise AssertionError('Unsafe request accepted: ' + key)
        checks += 1
    if reuse and len(reuse) != 3: raise ValueError('Replay requires exactly three captured A/B/A jobs')
    runner = None if reuse else Runner(); cases = []; paths = []
    if runner:
        for name, target in [('outside-build', ROOT / 'docs'), ('existing-directory', directory)]:
            try: runner.generate(base, target)
            except (ValueError, FileExistsError): guards.append(name)
            else: raise AssertionError('Unsafe output directory accepted: ' + name)
            checks += 1
        flag = directory / 'pre-cancel.flag'; flag.touch()
        cancelled_output = directory / 'cancelled-job'
        try: runner.generate(base | dict(cancel_file=str(flag)), cancelled_output)
        except RuntimeError: guards.append('pre-cancel')
        else: raise AssertionError('Pre-cancelled pipeline executed')
        check(not list(cancelled_output.iterdir()), 'Pre-cancelled pipeline wrote artifacts')
    for i, prompt in enumerate((PROMPT_A, PROMPT_B, PROMPT_A)):
        print('Actual trained pipeline A/B/A', i, flush=True)
        request = base | dict(prompt=prompt)
        if reuse or i == 0 and initial is not None:
            path = (reuse[i] if reuse else initial).resolve()
            if not path.is_relative_to((ROOT / 'build').resolve()): raise ValueError('Unexpected initial pipeline location')
            result = json.loads((path / 'pipeline.json').read_text(encoding='utf-8'))
            current(result['input_fingerprint'])
            check(result['input_fingerprint'] == pipeline_inputs() and result['request'] == request, 'Initial run inputs differ')
            for name, asset in result['files'].items():
                asset_path = path / name
                check(asset_path.parent == path and asset_path.stat().st_size == asset['bytes'] and sha(asset_path) == asset['sha256'], 'Changed initial pipeline output')
        else:
            path = directory / ('native-' + str(i)); result = runner.generate(request, path)
        check(result['full_trained_host_text_to_frames'] and result['actual_prompt_conditioning'] and result['host_mp4_generated'], 'Incomplete actual pipeline')
        check(not any(result[x] for x in ('physical_android', 'packaged_in_apk', 'engine_registered', 'video_quality_accepted', 'remote_inference', 'virtualization_used')), 'Pipeline scope overclaim')
        expected_assets = runner.assets if runner else (cases[0]['assets'] if cases else result['assets'])
        check(result['assets'] == expected_assets and len(result['assets']) == 21 and not result['prompt_truncated'], 'Unexpected assets or truncated acceptance prompt')
        check([x['stage'] for x in result['stages']] == ['noise', 'text', 'sampling', 'unpatchify', 'vae', 'frames'], 'Incomplete native stage order')
        text = result['stages'][1]['native']; sample = result['stages'][2]['native']; vae = result['stages'][4]['native']
        check(text['vocabulary_loads'] == text['vocabulary_unloads'] == 1, 'Tokenizer leak')
        check(text['model_loads'] == text['model_unloads'] == 1, 'T5 model leak')
        check(sample['steps'] == 8 and sample['layers'] == 28 and not sample['fixture'], 'Incomplete trained trajectory')
        check(vae['graph_runs'] == vae['session_loads'] == vae['session_unloads'] == 9 and vae['max_live_sessions'] == 1, 'VAE lifetime mismatch')
        for stage in result['stages']:
            memory = stage['resources']
            check(memory['observed'] and memory['samples'] > 0 and memory['observed_peak_working_set_bytes'] > 0 and not memory['gpu_memory_measured'], 'Missing honest host resource observations')
        cases.append(result); paths.append(path)
    for name in cases[0]['files']:
        if name == 'video.mp4': continue  # MP4 metadata is not neural reproducibility.
        check(cases[0]['files'][name] == cases[2]['files'][name], 'A/B/A failed bitwise reproducibility: ' + name)
    check(cases[0]['files']['initial-tokens.f32'] == cases[1]['files']['initial-tokens.f32'] and cases[0]['files']['decode-noise.f32'] == cases[1]['files']['decode-noise.f32'], 'Changed noise confounds prompt comparison')
    check(cases[0]['files']['caption.f32'] != cases[1]['files']['caption.f32'], 'Different prompts produced identical captions')
    rgbs = [np.frombuffer((path / 'frames.lma').read_bytes(), dtype=np.uint8, offset=28).reshape(33, 256, 256, 3) for path in paths]
    delta = float(np.abs(rgbs[0].astype(float) - rgbs[1].astype(float)).mean())
    # Structural evidence only; these cannot establish semantic or motion quality.
    check(delta > 3, 'Prompt change did not materially change RGB output')
    for i, rgb in enumerate(rgbs):
        deviations = rgb.std(axis=(1, 2, 3))
        movement = np.abs(np.diff(rgb.astype(float), axis=0)).mean(axis=(1, 2, 3))
        check(float(deviations.min()) > 3 and float(movement.mean()) > .1, 'Flat/static diagnostic output')
        metrics.append(dict(kind='structural_rgb', case=i, minimum_frame_std=float(deviations.min()), mean_adjacent_frame_mad=float(movement.mean())))
    reference_dir = reference.resolve() if reference else directory / 'original-reference'
    reference_reused = reference is not None
    if reference and not reference_dir.is_relative_to((ROOT / 'build').resolve()): raise ValueError('Reference must stay below project build/')
    if not reference: original_references(paths[:2], reference_dir)
    oracle = json.loads((reference_dir / 'references.json').read_text(encoding='utf-8'))
    current(oracle['input_fingerprint']); check(oracle['input_fingerprint'] == oracle_inputs(), 'Stale independent full-chain oracle')
    gates = json.loads((ROOT / 'third_party/ltx098-pipeline-source-lock.json').read_text(encoding='utf-8'))['host_gates']
    for case_index, reference in enumerate(oracle['cases']):
        check(reference['native_pipeline'] == paths[case_index].relative_to(ROOT).as_posix() and reference['native_record_sha256'] == sha(paths[case_index] / 'pipeline.json'), 'Independent reference belongs to different native inputs')
        for name, asset in reference['files'].items():
            path = reference_dir / reference['name'] / name
            check(path.stat().st_size == asset['bytes'] and sha(path) == asset['sha256'], 'Changed full-chain reference file')
        case = cases[case_index]
        check(reference['tokens'] == case['stages'][1]['native']['items'][0]['tokens'], 'Original tokenizer IDs differ')
        for native_name, expected_name in [('caption.f32', 'caption.f32'), ('denoised-tokens.f32', 'sampling-step-7.f32'),
                                           ('denoised-ncthw.f32', 'denoised-ncthw.f32'), ('decoded-ncthw.f32', 'decoded-ncthw.f32')]:
            actual = np.fromfile(paths[case_index] / native_name, dtype='<f4').astype(float)
            expected = np.fromfile(reference_dir / reference['name'] / expected_name, dtype='<f4').astype(float)
            check(actual.shape == expected.shape and actual.size > 0 and np.isfinite(actual).all() and np.isfinite(expected).all(), 'Full-chain shape/finite failure')
            error = actual - expected; maximum = float(np.max(np.abs(error)))
            relative = float(np.linalg.norm(error) / max(np.linalg.norm(expected), 1e-30))
            cosine = float(np.dot(actual, expected) / max(np.linalg.norm(actual) * np.linalg.norm(expected), 1e-30))
            metrics.append(dict(kind='full_chain', case=case_index, file=native_name, max_abs=maximum, relative_rmse=relative, cosine=cosine))
            numerical_check(maximum <= gates['full_chain_max_absolute_error'] and relative <= gates['full_chain_max_relative_rmse'] and cosine >= gates['full_chain_min_cosine'], 'case-' + str(case_index) + ': frozen original-forward full-chain gate failed: ' + native_name)
        expected = np.fromfile(reference_dir / reference['name'] / 'rgb.bin', dtype=np.uint8).reshape(rgbs[case_index].shape)
        error = np.abs(rgbs[case_index].astype(float) - expected.astype(float))
        metrics.append(dict(kind='full_chain_rgb', case=case_index, max_error=float(error.max()), mean_error=float(error.mean())))
        numerical_check(float(error.max()) <= gates['rgb_max_byte_error'] and float(error.mean()) <= gates['rgb_mean_byte_error'], 'case-' + str(case_index) + ': frozen full-chain RGB gate failed')
    diagnostic = None
    if conditioning_capture:
        capture = conditioning_capture.resolve()
        check(capture.is_relative_to((ROOT / 'build').resolve()), 'Conditioning capture outside project')
        data = json.loads((capture / 'oracle-caption.json').read_text(encoding='utf-8'))
        expected = json.loads((paths[0] / 'sampling.json').read_text(encoding='utf-8'))
        expected['context'] = np.fromfile(reference_dir / oracle['cases'][0]['name'] / 'caption.f32', dtype='<f4').tolist()
        expected['trace_dir'] = str(capture / 'oracle-caption-trace')
        check(data == expected, 'Diagnostic changed more than the reference caption and trace path')
        native = json.loads((capture / 'oracle-caption.log').read_text(encoding='utf-8').splitlines()[0])
        check(native['model_executed'] and native['backend'] == 'vulkan' and native['steps'] == 8 and native['layers'] == 28 and not native['fixture'] and native['parameters'] == 1923385472, 'Incomplete captured same-caption DiT')
        process = json.loads((capture / 'oracle-caption-metrics.json').read_text(encoding='utf-8'))
        check(process['same_t5_context'] and process['resources']['observed'] and process['resources']['samples'] > 0, 'Missing actual diagnostic resource capture')
        build = json.loads((ROOT / 'build/ltx098-host-vulkan/receipt.json').read_text(encoding='utf-8'))
        current(build['input_fingerprint']); check(sha(SAMPLER) == build['sampler_binary_sha256'], 'Changed native diagnostic executable')
        diagnostic_metrics = []
        for step in range(8):
            actual = np.fromfile(capture / 'oracle-caption-trace' / f'step-{step}.f32', dtype='<f4').astype(float)
            expected = np.fromfile(reference_dir / oracle['cases'][0]['name'] / f'sampling-step-{step}.f32', dtype='<f4').astype(float)
            check(actual.shape == expected.shape and np.isfinite(actual).all(), 'Invalid diagnostic trajectory')
            error = actual - expected
            diagnostic_metrics.append(dict(step=step, max_abs=float(np.abs(error).max()), relative_rmse=float(np.linalg.norm(error) / np.linalg.norm(expected))))
        check(np.array_equal(np.fromfile(capture / 'oracle-caption-latents.f32', dtype='<f4'), np.fromfile(capture / 'oracle-caption-trace/step-7.f32', dtype='<f4')), 'Diagnostic final/trace mismatch')
        files = ['oracle-caption.json', 'oracle-caption.log', 'oracle-caption-metrics.json', 'oracle-caption-latents.f32'] + [f'oracle-caption-trace/step-{i}.f32' for i in range(8)]
        final = diagnostic_metrics[-1]
        diagnostic = dict(case=0, same_reference_caption=True, captured_native_children=1, capture_reused=True,
                          metrics=diagnostic_metrics, resources=process['resources'], seconds=process['seconds'],
                          native=native, native_executable_sha256=sha(SAMPLER),
                          final_within_latent_gates=final['max_abs'] <= gates['full_chain_max_absolute_error'] and final['relative_rmse'] <= gates['full_chain_max_relative_rmse'],
                          files={name: dict(bytes=(capture / name).stat().st_size, sha256=sha(capture / name)) for name in files},
                          physical_android=False, full_pipeline_acceptance=False)
    current(before)
    result = dict(schema='lma.ltx098-pipeline-tests/1', checks=checks, guards=guards, metrics=metrics, gates=gates,
                  actual_trained_jobs=3, distinct_prompts=2, geometry=dict(width=256, height=256, frames=33, fps=24),
                  native_children=sum(len(x['stages']) for x in cases), host_media_children=6, jobs=cases,
                  original_oracle=oracle, original_oracle_files=sum(len(x['files']) for x in oracle['cases']),
                  prompt_change_rgb_mean_absolute_difference=delta, aba_bitwise_neural_reproducibility=True,
                  real_prompt_to_video_host_executed=True, original_forward_comparison_executed=True,
                  numerical_acceptance_passed=not failures, failures=failures,
                  passed_checks=checks-len(failures), failed_checks=len(failures),
                  conditioning_diagnostic=diagnostic,
                  real_prompt_to_video_host_tested=not failures, full_chain_original_forward_parity=not failures,
                  reused_native_jobs=len(reuse) if reuse else (1 if initial else 0),
                  native_jobs_executed_this_invocation=0 if reuse else (2 if initial else 3),
                  original_reference_reused=reference_reused,
                  captured_native_pipelines=[path.relative_to(ROOT).as_posix() for path in paths],
                  captured_native_record_sha256=[sha(path / 'pipeline.json') for path in paths],
                  host_mp4_generated=True, single_scale=True, video_quality_accepted=False,
                  original_unquantized_t5_compared=False, official_pixart_weight_identity_compared=False,
                  official_multiscale_default_reproduced=False, matches_pytorch_seed=False,
                  physical_android=False, engine_registered=False, packaged_in_apk=False,
                  remote_inference=False, virtualization_used=False, input_fingerprint=before)
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('checks', 'actual_trained_jobs', 'native_children', 'real_prompt_to_video_host_tested', 'physical_android')}), flush=True)
    if failures: print(json.dumps(dict(numerical_acceptance_passed=False, failures=failures)), file=sys.stderr, flush=True)
    return not failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--initial', type=Path)
    parser.add_argument('--reuse-native', type=Path, action='append', help='Validate three captured current jobs without rerunning inference')
    parser.add_argument('--reference', type=Path, help='Replay a current complete independent reference; every output is rehashed')
    parser.add_argument('--conditioning-capture', type=Path, help='Review a captured same-reference-caption native diagnostic separately')
    args = parser.parse_args()
    sys.exit(0 if run(args.initial, args.reuse_native, args.reference, args.conditioning_capture) else 1)
