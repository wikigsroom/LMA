"""Recompute captured T5 errors and publish only hashes/metrics, never tensors."""
import argparse
import json
import math
import shutil
from pathlib import Path

from analyze_ltx098_text import inputs as operator_inputs
from diagnose_ltx098_text import inputs as diagnosis_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import sha

ROOT = Path(__file__).resolve().parents[1]


def review(directory):
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT / 'build'): raise ValueError('Capture must stay below build/')
    before = fingerprint('tools/review_ltx098_text_diagnosis.py')
    diagnosis_path = directory / 'results.json'; operators_path = directory / 'operators.json'
    diagnosis = json.loads(diagnosis_path.read_text(encoding='utf-8'))
    operators = json.loads(operators_path.read_text(encoding='utf-8'))
    current(diagnosis['input_fingerprint']); current(operators['input_fingerprint'])
    if diagnosis['input_fingerprint'] != diagnosis_inputs() or operators['input_fingerprint'] != operator_inputs():
        raise ValueError('Changed capture/analysis source')
    if operators['native_capture_sha256'] != sha(diagnosis_path): raise ValueError('Wrong operator capture')
    baseline = json.loads((ROOT / 'verification/development/ltx098-pipeline.json').read_text(encoding='utf-8'))
    current(baseline['input_fingerprint'])
    if diagnosis['baseline_record_sha256'] != baseline['captured_native_record_sha256'][0]:
        raise ValueError('Diagnostic does not match original real-prompt A')
    fields = ['attn-norm', 'q', 'k', 'v', 'mixed', 'attn-o', 'attn-residual',
              'ffn-norm', 'gate', 'up', 'geglu', 'down', 'residual']
    expected = {'embedding', 'final'} | {'block-' + str(i) + '-' + field for i in range(24) for field in fields}
    if {item['name'] for item in diagnosis['metrics']} != expected or len(diagnosis['metrics']) != 314:
        raise ValueError('Incomplete intermediate coverage')
    if not diagnosis['baseline_native_caption_bitwise_identical'] or diagnosis['tensors'] != 219:
        raise ValueError('Incomplete trained capture or changed baseline caption')
    import numpy as np
    count = len(diagnosis['tokens']); checked = 0; artifacts = 0
    for item in diagnosis['metrics']:
        name = item['name']; width = 10240 if name.endswith(('-gate', '-up', '-geglu')) else 4096
        shape = [1, count, width]
        if item['shape'] != shape: raise ValueError('Wrong original intermediate shape')
        values = []
        for kind in ('native', 'reference'):
            path = directory / kind / (name + '.f32')
            if path.stat().st_size != count * width * 4 or sha(path) != item[kind + '_sha256']:
                raise ValueError('Changed intermediate: ' + name)
            value = np.fromfile(path, dtype='<f4').astype(np.float64)
            if not np.isfinite(value).all(): raise ValueError('Nonfinite intermediate')
            values.append(value); artifacts += 1
        delta = values[0] - values[1]
        maximum = float(abs(delta).max()); relative = float(np.linalg.norm(delta) / max(np.linalg.norm(values[1]), 1e-12))
        if maximum != item['max_abs'] or not math.isclose(relative, item['relative_rmse'], rel_tol=1e-12, abs_tol=1e-16):
            raise ValueError('Incorrect intermediate error: ' + name)
        checked += 1
    final = next(item for item in diagnosis['metrics'] if item['name'] == 'final')
    original = baseline['original_oracle']['cases'][0]['files']['caption.f32']
    if final['reference_sha256'] != original['sha256']:
        raise ValueError('Forward hooks changed original reference output')
    if final['native_sha256'] != baseline['jobs'][0]['files']['caption.f32']['sha256']:
        raise ValueError('Diagnostic changed accepted native output')
    expected_operators = {'block-' + str(i) + '-' + field for i in range(24) for field in
                          ['attn-norm-same-input', 'ffn-norm-same-input', 'geglu-same-input',
                           'sdpa-same-input', 'eager-attention-same-input']}
    if {item['name'] for item in operators['metrics']} != expected_operators or len(operators['metrics']) != 120:
        raise ValueError('Incomplete matched-input comparisons')
    for item in operators['metrics']:
        if not math.isfinite(item['max_abs']) or not math.isfinite(item['relative_rmse']) or min(item['max_abs'], item['relative_rmse']) < 0:
            raise ValueError('Invalid matched-input metric')
    if not operators['matched_native_input_comparisons'] or operators['full_model_rerun']:
        raise ValueError('Incorrect local analysis scope')
    for record in (diagnosis, operators):
        if record['physical_android'] or record['apk_changed'] or record['original_forward_modified'] or record['acceptance_gates_changed']:
            raise ValueError('Incorrect host diagnostic scope')
    out = ROOT / 'build/ltx098-text-diagnosis'
    report = dict(schema='lma.ltx098-text-diagnosis-review/1', recomputed_tensor_comparisons=checked,
                  hashed_raw_tensor_files=artifacts, reviewed_local_operator_comparisons=120,
                  native_output_matches_existing_baseline=True, reference_output_matches_existing_baseline=True,
                  diagnosis_sha256=sha(diagnosis_path), operators_sha256=sha(operators_path),
                  baseline_pipeline_sha256=sha(ROOT / 'verification/development/ltx098-pipeline.json'),
                  physical_android=False, apk_changed=False, full_chain_numeric_accepted=False,
                  input_fingerprint=before)
    current(before)
    shutil.copyfile(diagnosis_path, out / 'current-results.json')
    shutil.copyfile(operators_path, out / 'current-operators.json')
    (out / 'review.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(recomputed_tensor_comparisons=checked, hashed_raw_tensor_files=artifacts,
                          reviewed_local_operator_comparisons=120, full_chain_numeric_accepted=False)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    review(parser.parse_args().directory)
