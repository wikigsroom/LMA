"""Independently audit local LCM preparation and retained trained native output captures."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image
from build_lcm_prepare import inputs as build_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import sha
from generate_lcm_condition_contract import generate
from lcm_prepare_data import inspect
from test_lcm_overlay_trained import wire
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]
FILES = ['lcm-preparation-core.json', 'lcm-preparation-arm64.json', 'lcm-preparation-trained.json',
         'lcm-overlay-trained.json', 'lcm-preparation-capture-audit.json']


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def inputs():
    return build_inputs() | fingerprint('tools/check_lcm_preparation_evidence.py', 'tools/test_lcm_prepare.py',
        'tools/test_lcm_preparation_trained.py', 'tools/test_lcm_overlay_trained.py', 'tools/lcm_prepare_data.py',
        'tools/sd_variants_capture.py', 'research/lcm_overlay_trained')


def check(records, status, root=ROOT):
    core, arm, trained, overlay, audit = [records[name] for name in FILES]
    for record in [core, arm, trained, overlay, audit]:
        current(record['input_fingerprint'])
        assert not record['physical_android'] and not record.get('complete_release_accepted', False)
        assert not record.get('production_app_integrated', False) and not record.get('production_app_executed', False)
    assert core['passed'] and core['checks'] == 105 and core['actual_native_children'] == 24
    assert core['synthetic_parameters'] and not core['trained_weights_loaded'] and not core['model_inference']
    assert core['native_scalar_values_match_independent_oracle'] and core['numerical_max_abs_vs_torch'] <= 1e-6
    assert core['cancellation_after_native_progress'] and core['output_bytes'] == 5696 and core['payload_bytes'] == 5120
    assert arm['android_arm64_compiled'] and not arm['packaged_in_apk'] and not arm['learned_data_embedded']
    assert arm['mathematical_guidance_constants'] == 256 and arm['forbidden_network_process_imports'] == []
    elf = arm['elf']
    assert elf['machine'] == 'aarch64' and elf['16k_elf_aligned'] and elf['android_api_notes'] == [28]
    assert elf['interpreter'] == '/system/bin/linker64' and elf['entry_point']
    assert set(elf['needed']) <= {'libc.so', 'libm.so', 'libdl.so'}
    contract = load(root / 'research/lcm_prepare/contract.json')
    assert trained['passed'] and trained['source'] == contract['source'] and trained['source_complete_sha256_verified']
    assert trained['trained_parameters_used'] == 492800 and trained['source_parameter_bytes_selected'] == 1971200
    assert trained['native_scalar_values_match_independent_oracle'] and trained['numerical_max_abs_vs_torch'] <= 1e-6
    assert trained['nonlinear_subgraph_max_abs'] <= 2e-6 and trained['output']['bytes'] == 5696
    assert trained['output']['payload_bytes'] == 5120 and not trained['complete_unet_forward'] and not trained['model_inference']
    assert not trained['canonical_pipeline_equivalence_proven'] and not trained['image_quality_accepted']
    assert not overlay['passed'] and overlay['base'] == contract['base'] and overlay['base_whole_sha256_verified']
    assert overlay['preparation'] == trained['output'] and len(overlay['jobs']) == 5
    assert [j['name'] for j in overlay['jobs']] == ['original-bias-control','native-prepared','invalid-cfg','cancel-step1','recovery']
    assert all(j['passed'] and j['whitespace_tolerant_protocol_valid'] for j in overlay['jobs'])
    relation = overlay['comparisons']
    assert relation['recovery_exact'] and relation['differs_from_original']
    assert relation['mean_abs_gate'] == .1 and relation['max_abs_gate'] == 5
    assert relation['mean_abs_rgb_vs_previous'] <= .1 and relation['max_abs_rgb_vs_previous'] > 5
    assert not overlay['image_quality_accepted'] and not overlay['complete_target03_accepted'] and not overlay['canonical_pipeline_equivalence_proven']
    assert audit['passed'] and audit['negative_controls_rejected'] == 8
    assert audit['actual_native_children'] == 31 and audit['generated_native_pngs'] == 4
    assert audit['strict_observer_diagnostic_retained'] and audit['strict_diagnostic_png_matches_full_patch']
    assert audit['trained_output_matches_independent_oracle'] and audit['unlearned_guidance_regenerated']
    assert not audit['image_comparison_gate_passed'] and not audit['trained_candidate_accepted']
    assert not audit['model_data_published'] and audit['input_fingerprint'] == inputs()
    assert status['lcm_checkpoint_native_asset_preparation_host_tested']
    assert status['lcm_checkpoint_small_overlay_native_host_tested'] and status['lcm_checkpoint_preparer_arm64_compiled']
    assert not status['lcm_checkpoint_small_overlay_image_gate_passed']
    assert not status['lcm_checkpoint_product_preparation_implemented']
    assert not status['sd_distilled_complete_android_image_tested'] and not status['sd_distilled_image_quality_accepted']


def raw_capture(folder, name, record, allow_blank=False):
    raw = (folder / (name + '.stdout')).read_bytes()
    stderr = (folder / (name + '.stderr')).read_bytes()
    assert len(raw) < 2 * 1024 * 1024 and len(stderr) < 2 * 1024 * 1024
    blanks = wire(record, raw)
    if not allow_blank: assert blanks == 0 and not record['protocol_errors']
    assert not record['timed_out'] and not any(record['logs_truncated'])
    assert record['events'] == [json.loads(line) for line in raw.splitlines() if line.strip()]
    return blanks


def independent_payload(source, contract):
    with source.open('rb') as stream:
        count = struct.unpack('<Q', stream.read(8))[0]
        assert count == contract['source_header_bytes']
        raw = stream.read(count)
        assert hashlib.sha256(raw).hexdigest() == contract['source_header_sha256']
        header = json.loads(raw.decode('utf-8'))
        tensors = {}
        for short in ['cond_proj.weight','linear_1.weight','linear_1.bias']:
            record = header['time_embedding.' + short]
            assert record['dtype'] == 'F32'
            start, end = record['data_offsets'];stream.seek(8 + count + start)
            payload = stream.read(end - start)
            assert len(payload) == end - start
            tensors[short] = np.frombuffer(payload, dtype='<f4').copy().reshape(record['shape'])
    g = np.array(contract['guidance_u32_le'], dtype='<u4').view('<f4')
    cond = tensors['cond_proj.weight']
    w = tensors['linear_1.weight'].astype('f2').astype('f4')
    offset = np.array([sum(float(a) * float(b) for a,b in zip(row,g)) for row in cond], dtype='f4')
    delta = np.array([sum(float(a) * float(b) for a,b in zip(row,offset)) for row in w], dtype='f4')
    return (tensors['linear_1.bias'] + delta).astype('<f4').tobytes()


def capture_audit():
    before = inputs()
    core = load(ROOT / 'build/lcm-preparation-tests/results.json')
    arm = load(ROOT / 'build/lcm-prepare-arm64/receipt.json')
    trained = load(ROOT / 'build/lcm-preparation-trained/results.json')
    overlay = load(ROOT / 'build/lcm-overlay-trained/results.json')
    for report in [core, arm, trained, overlay]: current(report['input_fingerprint'])
    contract = load(ROOT / 'research/lcm_prepare/contract.json')
    assert generate() == contract
    raw_files = {}

    def add(path):
        path.resolve().relative_to((ROOT / 'build').resolve())
        assert path.is_file() and not path.is_symlink()
        raw_files[path.relative_to(ROOT).as_posix()] = dict(bytes=path.stat().st_size, sha256=sha(path))

    folder = ROOT / core['capture_directory']
    assert len(core['cases']) == 24 and core['cases'][-1]['name'] == 'recovery'
    rejected = 0
    for case in core['cases']:
        name = case['name']; assert load(folder / (name + '-capture.json')) == case
        raw_capture(folder, name, case)
        terminal = [e for e in case['events'] if 'ok' in e];assert len(terminal) == 1
        if case['expected_error'] is None:
            assert case['returncode'] == 0 and terminal[0]['ok']
            file = folder / ('success' if name == 'success' else name) / 'lcm-condition-bias.gguf'
            item = inspect(file.read_bytes())
            assert item['sha256'] == core['repeat_recovery_sha256'] and item['sha256'] == terminal[0]['output_sha256']
        else:
            rejected += 1; assert case['returncode'] == 1 and not terminal[0]['ok'] and case['expected_error'] in terminal[0]['error']
    assert rejected == 21 and not list(folder.glob('.ltx098-prepare-*'))
    assert next(c for c in core['cases'] if c['name']=='cancel-during-hash')['cancel_after_native_progress']
    for path in folder.rglob('*'):
        if path.is_file(): add(path)
    compile_logs = ['lcm-preparer-arm64-build.log', 'lcm-preparer-arm64-build-resume.log', 'lcm-preparer-arm64-build-final.log']
    for name in compile_logs: add(ROOT / 'build/sd-distilled-asset-probe' / name)
    assert 'TimeoutExpired' in (ROOT / 'build/sd-distilled-asset-probe' / compile_logs[0]).read_text(encoding='utf-8')
    assert 'android_arm64_compiled' in (ROOT / 'build/sd-distilled-asset-probe' / compile_logs[2]).read_text(encoding='utf-8')
    folder = ROOT / trained['capture_directory']
    case = trained['capture']; assert load(folder / 'capture.json') == case
    raw_capture(folder, 'prepare', case)
    receipt = [e for e in case['events'] if 'ok' in e][0]
    assert case['returncode'] == 0 and receipt['source_sha256_verified'] and not receipt['fixture']
    source = ROOT / 'build/sd-distilled-asset-probe/originals' / contract['source']['sha256'] / Path(contract['source']['path']).name
    assert source.stat().st_size == contract['source']['bytes'] and sha(source) == contract['source']['sha256']
    prepared = ROOT / trained['output']['path']; data = inspect(prepared.read_bytes())
    assert data['payload'] == independent_payload(source, contract)
    assert data['sha256'] == trained['output']['sha256'] == receipt['output_sha256']
    assert data['bytes'] == 5696 and data['metadata']['lma.overlay.base_sha256'] == contract['base']['sha256']
    assert data['metadata']['lma.overlay.source_sha256'] == contract['source']['sha256']
    for path in folder.rglob('*'):
        if path.is_file(): add(path)
    base = ROOT / 'build/sd-distilled-asset-probe/originals' / contract['base']['sha256'] / contract['base']['path']
    assert base.stat().st_size == contract['base']['bytes'] and sha(base) == contract['base']['sha256']
    folder = ROOT / overlay['capture_directory']; pngs = 0
    for job in overlay['jobs']:
        name = job['name']; assert load(folder / (name + '-capture.json')) == job
        blanks = raw_capture(folder, name, job, True); assert blanks == job['whitespace_only_stdout_lines']
        request = load(folder / (name + '.json')); assert request['parameters'] == job['parameters']
        assert request['pipeline'] == 'sd15_lcm' and request['samplingProfile'] == 'lcm' and request['loras'] == []
        assert job['resources']['observed'] and job['resources']['observed_peak_working_set_bytes'] > 0
        if 'image' in job:
            pngs += 1; path = folder / (name + '.png')
            assert json.loads(json.dumps(image_stats(path))) == job['image'] and job['returncode'] == 0
            assert len([e for e in job['events'] if e.get('event') == 'complete']) == 1
            steps = [e['step'] for e in job['events'] if e.get('event') == 'progress' and e.get('stage') == 'generating' and e.get('steps') == 4]
            assert steps == [0,1,2,3,4]
        elif name == 'invalid-cfg':
            assert job['returncode'] == 1 and not (folder / (name + '.png')).exists()
            assert [e['message'] for e in job['events'] if e.get('event') == 'error'] == ['Distilled sampling parameters do not match the frozen plan']
        else:
            assert name == 'cancel-step1' and job['forced_host_termination'] and job['cancel_trigger']['step'] == 1
            assert job['returncode'] != 0 and 0 <= job['cancel_to_exit_seconds'] < 10 and not (folder / (name + '.png')).exists()
    assert pngs == 3
    for path in folder.rglob('*'):
        if path.is_file(): add(path)
    a = np.asarray(Image.open(folder / 'native-prepared.png').convert('RGB'), dtype='i2')
    b = np.asarray(Image.open(ROOT / overlay['references']['folded']['path']).convert('RGB'), dtype='i2')
    delta = np.abs(a - b)
    assert float(delta.mean()) == overlay['comparisons']['mean_abs_rgb_vs_previous'] and int(delta.max()) == overlay['comparisons']['max_abs_rgb_vs_previous']
    assert float(delta.mean()) <= .1 and int(delta.max()) > 5 and not overlay['passed']
    diagnostic = load(ROOT / 'build/sd-distilled-asset-probe/lcm-overlay-probe-results.json')
    assert not diagnostic['host_checks_passed'] and len(diagnostic['jobs']) == 1
    snapshot = ROOT / 'research/lcm_overlay_trained/strict_probe_snapshot.py'
    assert sha(snapshot) == next(iter(diagnostic['input_fingerprint'].values()))
    folder = ROOT / diagnostic['capture_directory']; job = diagnostic['jobs'][0]
    assert not job['passed'] and job['returncode'] == 0 and job['protocol_errors'] == ['Non-protocol stdout']
    assert raw_capture(folder, job['name'], job, True) == 1
    assert sha(folder / (job['name'] + '.png')) == overlay['references']['folded']['sha256']
    for path in folder.rglob('*'):
        if path.is_file(): add(path)
    records = dict(zip(FILES[:4], [core, arm, trained, overlay]))
    audit = dict(schema='lma.lcm-preparation-capture-audit/1', passed=True, actual_native_children=31,
                 generated_native_pngs=4, raw_file_identities=raw_files, raw_files=len(raw_files),
                 strict_observer_diagnostic_retained=True, strict_diagnostic_png_matches_full_patch=True,
                 trained_output_matches_independent_oracle=True, unlearned_guidance_regenerated=True,
                 image_comparison_gate_passed=False, trained_candidate_accepted=False,
                 model_data_published=False, source_whole_objects_independently_rehashed=2,
                 timed_out_compile_diagnostic_retained=True, compile_log_files=compile_logs,
                 negative_controls_rejected=8, physical_android=False, production_app_integrated=False,
                 complete_release_accepted=False, input_fingerprint=before)
    records[FILES[4]] = audit
    status = dict(lcm_checkpoint_native_asset_preparation_host_tested=True, lcm_checkpoint_small_overlay_native_host_tested=True,
                  lcm_checkpoint_preparer_arm64_compiled=True, lcm_checkpoint_product_preparation_implemented=False,
                  lcm_checkpoint_small_overlay_image_gate_passed=False,
                  sd_distilled_complete_android_image_tested=False, sd_distilled_image_quality_accepted=False)
    check(records, status)
    for mutate in [lambda r:r[FILES[0]].update(actual_native_children=0), lambda r:r[FILES[0]].update(cancellation_after_native_progress=False),
                   lambda r:r[FILES[1]].update(packaged_in_apk=True), lambda r:r[FILES[2]].update(source_complete_sha256_verified=False),
                   lambda r:r[FILES[2]].update(numerical_max_abs_vs_torch=.1), lambda r:r[FILES[3]].update(passed=True),
                   lambda r:r[FILES[3]].update(image_quality_accepted=True), lambda r:r[FILES[4]].update(strict_observer_diagnostic_retained=False)]:
        incorrect=copy.deepcopy(records);mutate(incorrect)
        try: check(incorrect,status)
        except AssertionError: pass
        else: raise AssertionError('Incorrect LCM preparation evidence was accepted')
    current(before)
    out = ROOT / 'build/lcm-preparation-evidence';out.mkdir(exist_ok=True)
    for name, record in records.items(): (out / name).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, raw_files=len(raw_files), actual_native_children=31, generated_native_pngs=4, negative_controls_rejected=8)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--capture-audit',action='store_true');args=parser.parse_args()
    if args.capture_audit: capture_audit()
    else:
        directory=ROOT/'verification/development';records={name:load(directory/name) for name in FILES}
        check(records,load(directory/'status.json'));print('Current scoped LCM preparation evidence passed; no App / phone / Release acceptance.')
