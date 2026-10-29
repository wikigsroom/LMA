"""Audit host text diagnostics without overriding frozen pipeline failures."""
import json
import math
import re

from evidence import current


def check(records, status, root, digest):
    diagnosis = records['ltx098-text-diagnosis.json']
    operators = records['ltx098-text-operators.json']
    review = records['ltx098-text-diagnosis-review.json']
    pipeline = records['ltx098-pipeline.json']
    assert diagnosis['schema'] == 'lma.ltx098-text-diagnosis/1'
    assert diagnosis['tensors'] == 219 and diagnosis['baseline_native_caption_bitwise_identical']
    assert diagnosis['original_attention_implementation'] == 'sdpa'
    assert diagnosis['retained_intermediates_change_memory'] and not diagnosis['production_performance_measured']
    native = diagnosis['native']
    assert native['model_inference'] and not native['fixture'] and native['layers'] == 24 and native['width'] == 4096
    assert native['model_loads'] == native['model_unloads'] == native['encode_calls'] == 1
    fields = ['attn-norm', 'q', 'k', 'v', 'mixed', 'attn-o', 'attn-residual',
              'ffn-norm', 'gate', 'up', 'geglu', 'down', 'residual']
    expected = {'embedding', 'final'} | {'block-' + str(i) + '-' + key for i in range(24) for key in fields}
    assert len(diagnosis['metrics']) == 314 and {item['name'] for item in diagnosis['metrics']} == expected
    count = len(diagnosis['tokens'])
    for item in diagnosis['metrics']:
        width = 10240 if item['name'].endswith(('-gate', '-up', '-geglu')) else 4096
        assert item['shape'] == [1, count, width]
        assert math.isfinite(item['max_abs']) and math.isfinite(item['relative_rmse'])
        assert min(item['max_abs'], item['relative_rmse']) >= 0
        assert all(re.fullmatch('[a-f0-9]{64}', item[key]) for key in ['native_sha256', 'reference_sha256'])
    final = next(item for item in diagnosis['metrics'] if item['name'] == 'final')
    assert final['native_sha256'] == pipeline['jobs'][0]['files']['caption.f32']['sha256']
    assert final['reference_sha256'] == pipeline['original_oracle']['cases'][0]['files']['caption.f32']['sha256']
    assert diagnosis['baseline_record_sha256'] == pipeline['captured_native_record_sha256'][0]
    expected = {'block-' + str(i) + '-' + key for i in range(24) for key in
                ['attn-norm-same-input', 'ffn-norm-same-input', 'geglu-same-input',
                 'sdpa-same-input', 'eager-attention-same-input']}
    assert operators['schema'] == 'lma.ltx098-text-operators/1'
    assert len(operators['metrics']) == 120 and {item['name'] for item in operators['metrics']} == expected
    assert operators['matched_native_input_comparisons'] and not operators['full_model_rerun']
    assert operators['dense_act_fn'] == 'gelu_new' and operators['activation_class'] == 'NewGELUActivation'
    assert operators['original_attention_implementation'] == 'sdpa'
    for item in operators['metrics']:
        assert math.isfinite(item['max_abs']) and math.isfinite(item['relative_rmse'])
        assert min(item['max_abs'], item['relative_rmse']) >= 0
    for record in [diagnosis, operators]:
        assert not any(record[key] for key in ['physical_android', 'apk_changed', 'original_forward_modified', 'acceptance_gates_changed'])
    directory = root / 'verification/development'
    diagnosis_hash = digest((directory / 'ltx098-text-diagnosis.json').read_bytes())
    operators_hash = digest((directory / 'ltx098-text-operators.json').read_bytes())
    assert operators['native_capture_sha256'] == review['diagnosis_sha256'] == diagnosis_hash
    assert review['operators_sha256'] == operators_hash
    assert review['baseline_pipeline_sha256'] == digest((directory / 'ltx098-pipeline.json').read_bytes())
    assert review['recomputed_tensor_comparisons'] == 314 and review['hashed_raw_tensor_files'] == 628
    assert review['reviewed_local_operator_comparisons'] == 120
    assert review['native_output_matches_existing_baseline'] and review['reference_output_matches_existing_baseline']
    assert not any(review[key] for key in ['physical_android', 'apk_changed', 'full_chain_numeric_accepted'])
    assert status['ltx098_t5_intermediate_diagnostic_executed'] and not status['ltx098_t5_roundoff_repair_accepted']
    media_dir = root / 'docs/media/development'
    media = json.loads((media_dir / 'ltx098-text-roundoff.json').read_text(encoding='utf-8'))
    current(media['input_fingerprint'])
    assert media['kind'] == 'actual_host_numerical_diagnostic' and media['renderer'] == 'Matplotlib/Agg'
    assert media['sources'] == {'verification/development/ltx098-text-diagnosis.json': diagnosis_hash,
                                'verification/development/ltx098-text-operators.json': operators_hash}
    assert media['blocks'] == list(range(24)) and len(media['plotted_relative_rmse']) == 8
    propagated = {item['name']: item['relative_rmse'] for item in diagnosis['metrics']}
    local = {item['name']: item['relative_rmse'] for item in operators['metrics']}
    for key, values in media['plotted_relative_rmse'].items():
        source = local if key.endswith('-same-input') else propagated
        assert values == [source['block-' + str(i) + '-' + key] for i in range(24)]
    path = media_dir / media['file']
    assert path.parent == media_dir and path.name == 'ltx098-text-roundoff.png'
    assert path.stat().st_size == media['bytes'] and digest(path.read_bytes()) == media['sha256']
    assert not any(media[key] for key in ['baseline_full_chain_numeric_accepted', 'physical_android',
                                         'app_screen_recording', 'video_quality_accepted'])
