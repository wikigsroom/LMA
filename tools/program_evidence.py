"""Export/check the current complete program release without running trained models.

Historical model records retain their original identity. Required program
implementation is traced separately; phone and model quality remain untested.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from evidence import current, fingerprint, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/program'
VERSION = version()
PRIOR_COMMIT = 'da179315377957a449d94817f0a2b7d2030aea44'
CERTIFICATE = '90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17'
SOURCES = {
    'community.json': 'build/community-tests/results.json',
    'expansion.json': 'build/expansion-tests/results.json',
    'speech-extra-android.json': 'build/speech_extra-build-info.json',
    'mesh-android.json': 'build/mesh-build-info.json',
    'tts-android.json': 'build/tts-build-info.json',
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
    'sana-sprint.json': 'build/sana-sprint-tests/results.json',
    'mnn-android.json': 'build/mnn-build-info.json',
    'hub.json': 'build/hub-tests/results.json',
    'recipe-suggestions.json': 'build/recipe-suggestion-tests/results.json',
    'speech-voices.json': 'build/speech-voice-tests/results.json',
    'ui.json': 'build/ui-qa/results.json',
    'lint.json': 'build/android-lint/results.json',
    'ltx-official.json': 'build/ltx098-official-tests/results.json',
    'ltx-multiscale-app.json': 'build/ltx098-multiscale-app-tests/results.json',
    'ltx-single-scale-app.json': 'build/ltx098-app-tests/results.json',
    'ltx-android.json': 'build/ltx098-app-build-info.json',
}
MINIMUM = dict(expansion=173, community=818, foundation=899, backend=138, **{'bundle-pause':22, 'document-input':15},
    api=68, workbench=44, recovery=47, inputs=64, text=66, migration=69, scheduler=151,
    preparations=44, assemblies=47, diffusion=197, mnn=101, hub=80,
    **{'recipe-suggestions':73, 'speech-voices':70, 'sana-sprint':448}, ui=597, **{'ltx-official':89, 'ltx-multiscale-app':280, 'ltx-single-scale-app':127})
MEDIA = ['workbench', 'preflight', 'recovery', 'lcm', 'audio', 'ltx', 'resources',
         'curated', 'speech', 'components', 'wan', 'openmoss', 'sana', 'v030-ltx-official', 'v030-release-workbench']
UI_LOGIC = ['app/src/main/assets/' + name for name in (
    'index.html', 'app.css', 'app.js', 'foundation.css', 'foundation.js',
    'audio-preview.js', 'workbench.js', 'recipes.js', 'versions.js', 'community.js', 'expansion.js', 'glb-preview.js')]


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
    historical = ROOT / 'verification/history/dev45-program/status.json'
    assert record(historical)['version'] == '0.3.0-dev.45'
    media = {}
    for name in MEDIA:
        path = (ROOT / 'docs/media/history/v0.3.0' / name[5:] if name.startswith('v030-') else ROOT / 'docs/media/development' / name) / 'manifest.json'
        media[name] = dict(path=path.relative_to(ROOT).as_posix(), **identity(path))
    fresh_media = {name:ROOT/'docs/media/development'/name/'manifest.json' for name in ['community','release-workbench','expansion']}
    from release_scope import check as check_scope
    check_scope()
    status = dict(schema='lma.program-release/1', version=VERSION,
        validation_mode='program_only', sources=items, historical_ui_media=media,
        historical_media_comparison='historical_identity_only; not current page or APK validation',
        current_ui_media={name:dict(path=path.relative_to(ROOT).as_posix(), **identity(path)) for name,path in fresh_media.items()},
        prior_checkpoint=dict(commit=PRIOR_COMMIT, version='0.3.0-dev.45',
            path=historical.relative_to(ROOT).as_posix(), **identity(historical)),
        prior_release_archive='verification/history/v0.3.0-program-archive.json',
        prior_additive_release_archive='verification/history/v0.3.1-program-archive.json',
        policy='docs/proposals/program-validation-policy.json',
        release_ready=True, full_scope_implementation_complete=True,
        implementation_matrix='catalogue/release-'+VERSION+'-implementation.json', known_implementation_gaps=[],
        selected_ids=record(ROOT / 'docs/proposals/multimodal-release-scope.json')['selected_ids'],
        physical_device_tests=0, phone_inference_tested=False, model_inference_tested=False,
        all_selected_models_tested=False, model_quality_accepted=False, background_endurance_tested=False,
        historical_model_results_are_current_apk_validation=False,
        complete_model_downloads_for_validation=0, complete_model_copies_for_validation=0,
        small_program_metadata_fetched=True, metadata_audit='research/community/metadata.json',
        sana_text_to_image_variant='matched Sana-Sprint 0.6B MNN; program adapter, not device or image-quality evidence',
        model_weights_in_apk=False, automatic_model_asset_downloads=False,
        browser_closed=True, virtualization_used=False,
        input_fingerprint=fingerprint('tools/program_evidence.py', 'tools/check_repository.py',
            'docs/proposals/program-validation-policy.json', 'docs/proposals/multimodal-release-scope.json',
            'app/build.gradle', 'app/src/main/AndroidManifest.xml', 'catalogue/release-'+VERSION+'-implementation.json',
            'tools/program_release.py', 'tools/package_delivery.py', 'tools/prepare_release.py'))
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
    assert status['release_ready'] and status['full_scope_implementation_complete'] and not status['known_implementation_gaps']
    from release_scope import check as check_scope
    check_scope()
    assert not any(status[key] for key in ['phone_inference_tested', 'model_inference_tested', 'all_selected_models_tested',
        'model_quality_accepted', 'background_endurance_tested', 'model_weights_in_apk',
        'historical_model_results_are_current_apk_validation', 'automatic_model_asset_downloads',
        'virtualization_used', 'complete_model_downloads_for_validation', 'complete_model_copies_for_validation'])
    assert status['physical_device_tests'] == 0 and status['browser_closed']
    assert set(status['sources']) == set(SOURCES)
    records = {}
    for name, item in status['sources'].items():
        assert item['source'] == SOURCES[name] and identity(OUT / name) == {k:item[k] for k in ['bytes','sha256']}
        value = record(OUT / name); current(value['source_inputs'] if name in ['mnn-android.json','ltx-android.json','speech-extra-android.json','mesh-android.json','tts-android.json'] else value['input_fingerprint']); records[name] = value
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
    assert package['native_libraries_verified'] == 37 and package['all_native_dependencies_resolved']
    assert package['all_elf_load_segments_16k_aligned'] and package['final_apk_zip_alignment_verified']
    assert package['packaged_ui_matches_source'] and package['apk_signatures_independently_verified']
    assert lint['errors'] == 0 and lint['java_source_files'] == len(list((ROOT/'app/src/main/java').rglob('*.java')))
    ui = records['ui.json']; assert not ui['errors'] and ui['passed'] == len(ui['checks'])
    sprint=records['sana-sprint.json']; arm=records['mnn-android.json']
    assert sprint['bounded_graphs'] == 2 and sprint['production_worker_handshake'] and sprint['production_parameter_rejection']
    assert not any(sprint[k] for k in ['trained_model_execution','complete_model_downloaded','physical_android','image_generation'])
    assert arm['abi'] == 'arm64-v8a' and arm['min_sdk'] == 28 and arm['android_api_notes'] == [28]
    assert arm['static_dependencies']['sentencepiece'] == '31646a467d2051eb904e0b45de3a73e91fe1c1e3'
    assert not arm['http_resources_compiled'] and not arm['logcat_compiled'] and not arm['virtualization_used']
    for name in ['speech-extra-android.json','mesh-android.json','tts-android.json']:
        arm_extra=records[name]
        assert arm_extra['abi']=='arm64-v8a' and arm_extra['android_api_notes']==[28]
        assert not arm_extra.get('model_data_embedded',False) and not arm_extra.get('deviceValidated',False)
    assert records['expansion.json']['java']['actual_host_child_processes'] and not records['expansion.json']['model_inference']
    ltx, official = records['ltx-android.json'], records['ltx-official.json']
    assert ltx['abi'] == 'arm64-v8a' and ltx['min_sdk'] == 28 and ltx['android_api_notes'] == [28]
    assert 'ltx098_pixart_multiscale_v1' in ltx['pipelines']
    assert not ltx['model_data_embedded'] and not ltx['deviceValidated']
    assert official['fixture_neural_graphs_only'] and official['complete_trained_model_runs'] == 0
    assert official['complete_model_downloads'] == official['complete_model_copies'] == 0
    for name, multiscale in [('ltx-multiscale-app.json', True), ('ltx-single-scale-app.json', False)]:
        case = records[name]
        assert case['productionEngineAndQueue'] and case['syntheticNeuralStages'] and case['multiscale'] == multiscale
        assert not any(case[k] for k in ['physicalAndroid', 'modelInference', 'qualityAccepted', 'numericalAccepted'])
    # Old fixture media retains identity; changed workbench code is checked by current UI tests.
    assert set(status['historical_ui_media']) == set(MEDIA)
    for item in status['historical_ui_media'].values():
        path = ROOT / item['path']; assert identity(path) == {k:item[k] for k in ['bytes','sha256']}
        media = record(path)
        assert media['version'] == ('0.3.0' if 'history/v0.3.0/' in path.as_posix() else '0.3.0-dev.45' if path.parent.name=='sana' else '0.3.0-dev.42') and media['browser_closed'] and not media['browser_errors']
        assert not media['android_device'] and not media['model_inference']
        for file in media['files']:
            assert identity(path.parent / file['file']) == {k:file[k] for k in ['bytes','sha256']}
    assert set(status['current_ui_media']) == {'community','release-workbench','expansion'}
    for item in status['current_ui_media'].values():
        path=ROOT/item['path']; assert identity(path)=={k:item[k] for k in ['bytes','sha256']}
        media=record(path); current(media['input_fingerprint'])
        assert media['version']==VERSION and media['browser_closed'] and not media['browser_errors']
        assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded']
        assert len(media['screenshots'])==5
        assert len(media['checks']) >= ({'community':25,'release-workbench':8,'expansion':32}[path.parent.name])
        for file in media['files']: assert identity(path.parent/file['file'])=={k:file[k] for k in ['bytes','sha256']}
    prior = status['prior_checkpoint']; assert prior['commit'] == PRIOR_COMMIT and prior['version'] == '0.3.0-dev.45'
    assert identity(ROOT / prior['path']) == {k:prior[k] for k in ['bytes','sha256']}
    tree = subprocess.run(['git', 'ls-tree', '-rz', PRIOR_COMMIT, 'verification/program'], cwd=ROOT, capture_output=True, check=True)
    archived = ROOT / 'verification/history/dev45-program'
    originals = {}
    for item in tree.stdout.decode('utf-8').strip('\0').split('\0'):
        metadata, path = item.split('\t'); originals[Path(path).name] = metadata.split()[2]
    assert set(originals) == {p.name for p in archived.iterdir() if p.is_file()}
    for name, blob in originals.items():
        data = (archived / name).read_bytes()
        assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest() == blob, 'Changed historical evidence: '+name
    # Preserve the first reproduced failure without evaluating old model acceptance gates.
    archived_release = record(ROOT / status['prior_release_archive'])
    assert archived_release['version'] == '0.3.0' and archived_release['commit'] == 'd659da11e3b3d81fedbfbd1ba54344612c5bf6da'
    archive_root = ROOT / archived_release['archivePath']
    assert set(archived_release['files']) == {p.name for p in archive_root.iterdir() if p.is_file()}
    for name, item in archived_release['files'].items():
        assert Path(name).name == name
        body = (archive_root / name).read_bytes()
        assert identity(archive_root / name) == {k:item[k] for k in ['bytes', 'sha256']}
        assert hashlib.sha1(('blob '+str(len(body))+'\0').encode()+body).hexdigest() == item['gitBlob']
        frozen_blob = subprocess.check_output(['git', 'rev-parse', archived_release['commit']+':verification/program/'+name], cwd=ROOT).decode('ascii').strip()
        assert frozen_blob == item['gitBlob'], 'Archived release identity changed: '+name
    previous=record(ROOT/status['prior_additive_release_archive'])
    assert previous['version']=='0.3.1'
    for name,item in previous['files'].items():
        path=ROOT/previous['directory']/name
        assert identity(path)=={k:item[k] for k in ['bytes','sha256']}
        data=path.read_bytes()
        assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==item['gitBlob']
        frozen=subprocess.check_output(['git','rev-parse',previous['commit']+':verification/program/'+name],cwd=ROOT).decode('ascii').strip()
        assert frozen==item['gitBlob'],'Changed v0.3.1 evidence: '+name
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
        checks=counts, historical_ui_manifests=len(MEDIA), current_ui_manifests=3, original_failure_preserved=True,
        native_libraries=37, lint_errors=0, lint_warnings=len(lint['warnings']),
        apk=build['apk'], apk_sha256=build['sha256'], release_ready=True, full_scope_implementation_complete=True,
        model_inference_tested=False, phone_inference_tested=False)
    (ROOT/'build/program-evidence-check.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--export',action='store_true')
    args=parser.parse_args(); print(json.dumps(export() if args.export else check()))
