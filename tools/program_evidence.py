"""Export/check program-only development evidence without running trained models.

Historical model records retain their original identity. This checkpoint does
not waive missing feature implementation or claim complete v0.3.0 readiness.
"""
import argparse
import hashlib
import json
from pathlib import Path
from evidence import current, fingerprint, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/program'
VERSION = '0.3.0-dev.44'
PRIOR_COMMIT = '1c0f5d3735d31913069cce64625a101c85c3b8cb'
CERTIFICATE = '90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17'
SOURCES = {
    'build.json': 'dist/build-info.json',
    'package.json': 'build/package-verification.json',
    'foundation.json': 'build/foundation-tests/results.json',
    'backend.json': 'build/backend-tests/results.json',
    'bundle-pause.json': 'build/bundle-pause-tests/results.json',
    'document-input.json': 'build/document-input-tests/results.json',
    'api.json': 'build/api-tests/results.json',
    'workbench.json': 'build/workbench-tests/results.json',
    'recovery.json': 'build/recovery-tests/results.json',
    'inputs.json': 'build/input-tests/results.json',
    'text.json': 'build/text-tests/results.json',
    'migration.json': 'build/migration-tests/results.json',
    'scheduler.json': 'build/scheduler-tests/results.json',
    'preparations.json': 'build/preparation-tests/results.json',
    'assemblies.json': 'build/assembly-tests/results.json',
    'diffusion.json': 'build/diffusion-tests/results.json',
    'mnn.json': 'build/mnn-tests/results.json',
    'hub.json': 'build/hub-tests/results.json',
    'recipe-suggestions.json': 'build/recipe-suggestion-tests/results.json',
    'speech-voices.json': 'build/speech-voice-tests/results.json',
    'ui.json': 'build/ui-qa/results.json',
    'lint.json': 'build/android-lint/results.json',
}
MINIMUM = dict(foundation=701, backend=138, **{'bundle-pause':22, 'document-input':15},
    api=68, workbench=44, recovery=47, inputs=64, text=66, migration=69, scheduler=151,
    preparations=44, assemblies=47, diffusion=197, mnn=101, hub=80,
    **{'recipe-suggestions':73, 'speech-voices':70}, ui=490)
MEDIA = ['workbench', 'preflight', 'recovery', 'lcm', 'audio', 'ltx', 'resources',
         'curated', 'speech', 'components', 'wan', 'openmoss']
UI_LOGIC = ['app/src/main/assets/' + name for name in (
    'index.html', 'app.css', 'app.js', 'foundation.css', 'foundation.js',
    'audio-preview.js', 'workbench.js', 'recipes.js', 'versions.js')]


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    return json.loads(path.read_text(encoding='utf-8'))


def identity(path):
    return dict(bytes=path.stat().st_size, sha256=sha(path))


def counted(name, value):
    passed = value.get('passed')
    assert passed, 'Program checks did not pass: ' + name
    if isinstance(passed, int) and not isinstance(passed, bool): return passed
    for key in ('count', 'checks', 'assertions'):
        count = value.get(key)
        if isinstance(count, int): return count
        if isinstance(count, list): return len(count)
        if isinstance(count, dict) and isinstance(count.get('passed'), int): return count['passed']
    raise AssertionError('Missing assertion count: ' + name)


def export():
    assert version() == VERSION
    OUT.mkdir(exist_ok=True)
    items = {}
    for name, original in SOURCES.items():
        data = (ROOT / original).read_bytes()
        (OUT / name).write_bytes(data)
        items[name] = dict(source=original, **identity(OUT / name))
    historical = ROOT / 'verification/development/status.json'
    assert record(historical)['version'] == '0.3.0-dev.43'
    media = {}
    for name in MEDIA:
        path = ROOT / 'docs/media/development' / name / 'manifest.json'
        media[name] = dict(path=path.relative_to(ROOT).as_posix(), **identity(path))
    status = dict(schema='lma.program-checkpoint/1', version=VERSION,
        validation_mode='program_only', sources=items, historical_ui_media=media,
        historical_media_comparison='unchanged_page_logic_only; original metadata/fixture/version retained',
        historical_ui_logic_paths=UI_LOGIC,
        prior_checkpoint=dict(commit=PRIOR_COMMIT, version='0.3.0-dev.43',
            path=historical.relative_to(ROOT).as_posix(), **identity(historical)),
        policy='docs/proposals/program-validation-policy.json',
        release_ready=False, full_scope_implementation_complete=False,
        known_implementation_gaps=[
            dict(selection_id='04', target='Sana text-to-image', existing_variant_is_not_substitute='Sana Edit'),
            dict(selection_id='17', target='original PixArt T5 / multiscale LTX 0.9.8',
                 existing_variant_is_not_substitute='Google T5 Q5 single-scale')],
        selected_ids=record(ROOT / 'docs/proposals/multimodal-release-scope.json')['selected_ids'],
        physical_device_tests=0, phone_inference_tested=False, model_inference_tested=False,
        all_selected_models_tested=False, model_quality_accepted=False, background_endurance_tested=False,
        historical_model_results_are_current_apk_validation=False,
        model_asset_downloads_for_validation=0, model_asset_copies_for_validation=0,
        model_weights_in_apk=False, automatic_model_asset_downloads=False,
        browser_closed=True, virtualization_used=False,
        input_fingerprint=fingerprint('tools/program_evidence.py', 'tools/check_repository.py',
            'docs/proposals/program-validation-policy.json', 'docs/proposals/multimodal-release-scope.json',
            'app/build.gradle', 'app/src/main/AndroidManifest.xml'))
    (OUT / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return check()


def check():
    assert version() == VERSION
    status = record(OUT / 'status.json'); current(status['input_fingerprint'])
    assert status['version'] == VERSION and status['validation_mode'] == 'program_only'
    policy = record(ROOT / status['policy'])
    assert policy['validation_mode'] == 'program_only' and not policy['full_model_execution_required']
    assert not policy['missing_feature_implementation_waived']
    scope = record(ROOT / 'docs/proposals/multimodal-release-scope.json')
    assert status['selected_ids'] == policy['selected_ids'] == scope['selected_ids']
    assert scope['preserved_recommendation_ids'] == ['m08', 'm06', 'm01']
    assert policy['lora_required_base_families'] == ['sd15', 'sdxl']
    assert not any(status[key] for key in ['release_ready', 'full_scope_implementation_complete',
        'phone_inference_tested', 'model_inference_tested', 'all_selected_models_tested',
        'model_quality_accepted', 'background_endurance_tested', 'model_weights_in_apk',
        'historical_model_results_are_current_apk_validation', 'automatic_model_asset_downloads',
        'virtualization_used', 'model_asset_downloads_for_validation', 'model_asset_copies_for_validation'])
    assert status['physical_device_tests'] == 0 and status['browser_closed']
    assert set(status['sources']) == set(SOURCES)
    records = {}
    for name, item in status['sources'].items():
        assert item['source'] == SOURCES[name] and identity(OUT / name) == {k:item[k] for k in ['bytes','sha256']}
        value = record(OUT / name); current(value['input_fingerprint']); records[name] = value
        for key in ['model_inference', 'model_inference_tested', 'modelInference']:
            assert not value.get(key, False), 'Unexpected neural execution in program evidence: ' + name
    counts = {name:counted(name, records[name+'.json']) for name in MINIMUM}
    for name, minimum in MINIMUM.items(): assert counts[name] >= minimum, name
    build, package, lint = (records[name+'.json'] for name in ['build', 'package', 'lint'])
    assert build['input_fingerprint'] == build_inputs() and build['version'] == VERSION
    apk = ROOT / 'dist' / build['apk']
    assert sha(apk) == build['sha256'] == package['sha256'] == lint['applicationApkSha256']
    assert apk.stat().st_size == build['bytes'] and build['signatures_verified']
    assert package['signing_certificate_sha256'] == CERTIFICATE
    assert package['native_libraries_verified'] == 35 and package['all_native_dependencies_resolved']
    assert package['all_elf_load_segments_16k_aligned'] and package['final_apk_zip_alignment_verified']
    assert package['packaged_ui_matches_source'] and package['apk_signatures_independently_verified']
    assert lint['errors'] == 0 and lint['java_source_files'] == len(list((ROOT/'app/src/main/java').rglob('*.java')))
    ui = records['ui.json']; assert not ui['errors'] and ui['passed'] == len(ui['checks'])
    # This validates unchanged page bytes and media identity, not fresh phone/model execution.
    assert set(status['historical_ui_media']) == set(MEDIA) and status['historical_ui_logic_paths'] == UI_LOGIC
    for item in status['historical_ui_media'].values():
        path = ROOT / item['path']; assert identity(path) == {k:item[k] for k in ['bytes','sha256']}
        media = record(path)
        # Build metadata changes when Java changes. Old recordings are explicitly
        # historical fixtures; only unchanged page logic is reused, not old data.
        current({name:media['input_fingerprint'][name] for name in UI_LOGIC})
        assert media['version'] == '0.3.0-dev.42' and media['browser_closed'] and not media['browser_errors']
        assert not media['android_device'] and not media['model_inference']
        for file in media['files']:
            assert identity(path.parent / file['file']) == {k:file[k] for k in ['bytes','sha256']}
    prior = status['prior_checkpoint']; assert prior['commit'] == PRIOR_COMMIT and prior['version'] == '0.3.0-dev.43'
    assert identity(ROOT / prior['path']) == {k:prior[k] for k in ['bytes','sha256']}
    # Preserve the first reproduced failure without evaluating old model acceptance gates.
    issue = ROOT / 'verification/research/input-opening-issue'
    capture = record(issue / 'capture.json'); assert not capture['host_contract_passed']
    for name, item in capture['files'].items():
        assert Path(name).name == name and identity(issue/name) == item
    for name, expected in {
        'license.js':'838317c7653ca35291e9e18f2a7e2d98ed46a10880dfe144176f04ad994433d0',
        'foundation.js':'a2bd9f0a92807a0d60a97884fb3dd123ddfc5cf42258b6577bff36b37f99cb14'}.items():
        assert sha(ROOT/'app/src/main/assets'/name) == expected
    result = dict(passed=True, version=VERSION, validation_mode='program_only',
        current_records=len(records), program_suites=len(counts), program_assertions=sum(counts.values()),
        checks=counts, historical_ui_manifests=len(MEDIA), original_failure_preserved=True,
        native_libraries=35, lint_errors=0, lint_warnings=len(lint['warnings']),
        apk=build['apk'], apk_sha256=build['sha256'], release_ready=False,
        model_inference_tested=False, phone_inference_tested=False)
    (ROOT/'build/program-evidence-check.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--export',action='store_true')
    args=parser.parse_args(); print(json.dumps(export() if args.export else check()))
