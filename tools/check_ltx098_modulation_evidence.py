"""Validate scoped modulation evidence; optionally recompute retained arrays."""
import hashlib
import json
import math
import re
from pathlib import Path

from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
ANALYSES = ['ltx098-modulation-step0.json', 'ltx098-modulation-step7.json']
SAMPLERS = ['ltx098-modulation-reference-vulkan.json', 'ltx098-modulation-f32-vulkan.json']
SOURCES = {
    ANALYSES[0]: 'build/ltx098-modulation-analysis/case-1-step-0-results.json',
    ANALYSES[1]: 'build/ltx098-modulation-analysis/case-1-step-7-results.json',
    SAMPLERS[0]: 'build/ltx098-modulation-tests/publisher_modulation-vulkan-reference-case-1-results.json',
    SAMPLERS[1]: 'build/ltx098-modulation-tests/publisher_modulation-vulkan-f32-case-1-results.json',
}


def validate(records, root, digest):
    from analyze_ltx098_modulation import inputs as analysis_inputs
    from test_ltx098_modulation import inputs as sampler_inputs
    from build_ltx098_modulation import inputs as build_inputs
    baseline = records['ltx098-pipeline.json']; candidate = records['ltx098-accuracy-f32.json']
    original = baseline['original_oracle']['cases'][1]
    stages = ['block-' + str(i) + '-' + kind for i in range(28)
              for kind in ['attention', 'feedforward']] + ['output']
    for name, step in zip(ANALYSES, [0, 7]):
        record = records[name]; current(record['input_fingerprint'])
        assert record['input_fingerprint'] == analysis_inputs()
        assert record['schema'] == 'lma.ltx098-modulation-analysis/1' and record['case'] == 1 and record['step'] == step
        assert record['trained_tensors'] == 715 and record['trained_parameters'] == 1923385472
        assert record['parameter_paging']['loads'] == 32 and record['original_forward_seconds'] > 0
        assert record['frozen_trajectory_comparison'] == dict(max_abs=0., relative_rmse=0., bitwise_identical=True)
        assert record['original_oracle_sha256'] == candidate['original_oracle_sha256']
        assert record['caption_sha256'] == original['files']['caption.f32']['sha256']
        assert record['source_checkpoint_sha256'] == '76aa8c4786af752fa6f951947129d5290c3c6c0b2fadcadea6b5e114ae2cad8f'
        assert [metric['stage'] for metric in record['metrics']] == stages and len(record['files']) == 228
        assert set(record['files']) == {stage + '-' + role + '.f32' for stage in stages
                                      for role in ['normalized', 'scale', 'shift', 'expected']}
        for metric in record['metrics']:
            assert metric['ordered_max_abs'] == 0 and metric['ordered_bitwise_identical']
            assert 0 < metric['reassociated_different_elements'] <= metric['elements']
            assert math.isfinite(metric['reassociated_max_abs']) and metric['reassociated_max_abs'] > 0
        for identity in record['files'].values():
            assert identity['bytes'] == math.prod(identity['shape']) * 4
            assert re.fullmatch('[a-f0-9]{64}', identity['sha256'])
        assert record['reference_conditioned'] and record['torch_operator_analysis']
        assert not any(record[key] for key in ['original_forward_modified', 'native_replacement_executed',
                   'full_model_accepted', 'physical_android', 'packaged_in_apk', 'engine_registered', 'acceptance_gates_changed'])
    for name, context in zip(SAMPLERS, ['reference', 'f32']):
        record = records[name]; current(record['input_fingerprint'])
        assert record['input_fingerprint'] == sampler_inputs()
        assert record['schema'] == 'lma.ltx098-modulation-sampling/1'
        assert record['case'] == 1 and record['context'] == context and record['backend'] == 'vulkan'
        assert record['original_case'] == original and record['baseline_request'] == baseline['jobs'][1]['request']
        assert record['gates'] == baseline['gates'] and record['diagnostic_only']
        assert record['reference_caption_supplied'] is (context == 'reference')
        if context == 'reference':
            assert record['caption_sha256'] == original['files']['caption.f32']['sha256']
            assert record['candidate_record_sha256'] is None
        else:
            assert record['caption_sha256'] == candidate['jobs'][1]['caption_sha256']
            assert record['candidate_record_sha256'] == digest((root / 'verification/development/ltx098-accuracy-f32.json').read_bytes())
        assert record['captured_native_children'] == 1
        assert record['native_children_executed_this_invocation'] == (0 if record['capture_reused'] else 1)
        assert record['seconds'] > 0 and record['resources']['observed'] and record['resources']['samples'] > 0
        assert record['explicit_f32_matmul_operands'] and record['publisher_modulation_order']
        native = record['native']; compilation = record['compilation']; current(compilation['input_fingerprint'])
        assert compilation['input_fingerprint'] == build_inputs() and compilation['schema'] == 'lma.ltx098-modulation-build/1'
        assert compilation['mode'] == 'publisher_modulation' and compilation['publisher_modulation_order']
        assert compilation['executable_sha256'] == record['native_binary_sha256'] and len(compilation['linked_archives']) == 5
        assert not any(compilation[key] for key in ['android_compiled', 'packaged_in_apk', 'engine_registered'])
        assert native['ok'] and native['model_executed'] and not native['fixture'] and native['backend'] == 'vulkan'
        assert native['layers'] == 28 and native['parameters'] == 1923385472 and native['steps'] == 8
        assert native['explicit_f32_matmul_operands'] and native['publisher_modulation_order']
        assert native['precision_policy'] == 'explicit_f32_matmul_publisher_modulation'
        assert [metric['step'] for metric in record['metrics']] == list(range(8))
        for metric in record['metrics']:
            assert all(math.isfinite(metric[key]) for key in ['max_abs', 'relative_rmse', 'cosine'])
            assert metric['max_abs'] >= 0 and metric['relative_rmse'] >= 0 and -.00000001 <= metric['cosine'] <= 1.00000001
        assert set(record['files']) == {'request.json', 'native.log', 'latents.f32'} | {'trace/step-' + str(i) + '.f32' for i in range(8)}
        assert record['files']['latents.f32']['sha256'] == record['files']['trace/step-7.f32']['sha256']
        final = record['metrics'][-1]; gates = record['gates']
        accepted = final['max_abs'] <= gates['full_chain_max_absolute_error'] and final['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and final['cosine'] >= gates['full_chain_min_cosine']
        assert record['latent_gate_matched'] is accepted
        assert not any(record[key] for key in ['model_stage_accepted', 'full_pipeline_accepted', 'physical_android',
                    'packaged_in_apk', 'engine_registered', 'acceptance_gates_changed'])


def check(records, status, digest, root):
    validate(records, root, digest)
    audit = records['ltx098-modulation-capture-audit.json']; current(audit['input_fingerprint'])
    assert audit['schema'] == 'lma.ltx098-modulation-capture-audit/1'
    assert audit['recomputed_modulation_sites'] == 114 and audit['raw_files_verified'] == 478
    assert audit['recomputed_sampler_steps'] == 16 and audit['all_recorded_metrics_reproduced']
    assert audit['sources'] == {name: digest((root / 'verification/development' / name).read_bytes()) for name in SOURCES}
    assert not any(audit[key] for key in ['physical_android', 'model_reexecuted', 'complete_release_accepted'])
    assert status['ltx098_modulation_host_diagnosis_executed']
    assert not status['ltx098_t5_roundoff_repair_accepted'] and not status['ltx098_complete_android_video_tested']


def audit_captures():
    import numpy as np
    from fetch_ltx098_text import sha
    before = fingerprint('tools/check_ltx098_modulation_evidence.py')
    records = {name: json.loads((ROOT / path).read_text(encoding='utf-8')) for name, path in SOURCES.items()}
    for name in ['ltx098-pipeline.json', 'ltx098-accuracy-f32.json']:
        records[name] = json.loads((ROOT / 'verification/development' / name).read_text(encoding='utf-8'))
    validate(records, ROOT, lambda data: hashlib.sha256(data).hexdigest())
    sites = 0; steps = 0; raw_files = 0
    for name in ANALYSES:
        record = records[name]; directory = (ROOT / record['output_directory']).resolve()
        if not directory.is_relative_to(ROOT / 'build'): raise ValueError('Raw analysis path outside build')
        arrays = {}
        for file, identity in record['files'].items():
            path = (directory / file).resolve()
            if not path.is_relative_to(directory) or path.stat().st_size != identity['bytes'] or sha(path) != identity['sha256']:
                raise ValueError('Changed modulation array')
            array = np.fromfile(path, dtype='<f4').reshape(identity['shape'])
            if not np.isfinite(array).all(): raise ValueError('Nonfinite modulation array')
            arrays[file] = array; raw_files += 1
        for metric in record['metrics']:
            stage = metric['stage']
            x, scale, shift, expected = [arrays[stage + '-' + role + '.f32'] for role in ['normalized', 'scale', 'shift', 'expected']]
            ordered = x * (np.float32(1) + scale) + shift; reassociated = (x + x * scale) + shift
            assert np.array_equal(ordered, expected)
            assert float(abs(reassociated.astype(np.float64) - expected.astype(np.float64)).max()) == metric['reassociated_max_abs']
            assert int(np.count_nonzero(reassociated != expected)) == metric['reassociated_different_elements']
            sites += 1
        del arrays
    reference = ROOT / 'build/ltx098-pipeline-tests/run-s3z3urrv/original-reference'
    for name in SAMPLERS:
        record = records[name]; directory = (ROOT / record['capture_directory']).resolve()
        if not directory.is_relative_to(ROOT / 'build'): raise ValueError('Raw sampler path outside build')
        for file, identity in record['files'].items():
            path = (directory / file).resolve()
            if not path.is_relative_to(directory) or path.stat().st_size != identity['bytes'] or sha(path) != identity['sha256']:
                raise ValueError('Changed sampler capture')
            raw_files += 1
        assert json.loads((directory / 'native.log').read_text(encoding='utf-8').splitlines()[0]) == record['native']
        for metric in record['metrics']:
            file = 'sampling-step-' + str(metric['step']) + '.f32'
            expected = reference / record['original_case']['name'] / file
            assert sha(expected) == record['original_case']['files'][file]['sha256']
            right = np.fromfile(expected, dtype='<f4').astype(np.float64)
            left = np.fromfile(directory / 'trace' / ('step-' + str(metric['step']) + '.f32'), dtype='<f4').astype(np.float64)
            delta = left - right
            assert float(abs(delta).max()) == metric['max_abs']
            assert math.isclose(float(np.linalg.norm(delta) / np.linalg.norm(right)), metric['relative_rmse'], rel_tol=1e-12)
            assert math.isclose(float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right))), metric['cosine'], rel_tol=1e-12)
            steps += 1
    current(before)
    report = dict(schema='lma.ltx098-modulation-capture-audit/1', recomputed_modulation_sites=sites,
                  raw_files_verified=raw_files, recomputed_sampler_steps=steps,
                  all_recorded_metrics_reproduced=True, model_reexecuted=False,
                  sources={name: sha(ROOT / path) for name, path in SOURCES.items()},
                  physical_android=False, complete_release_accepted=False, input_fingerprint=before)
    path = ROOT / 'build/ltx098-modulation-tests/capture-audit.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ['recomputed_modulation_sites', 'raw_files_verified', 'recomputed_sampler_steps']}))


if __name__ == '__main__': audit_captures()
