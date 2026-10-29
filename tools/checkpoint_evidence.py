"""Current business-flow checks plus immutable, explicitly historical model experiments.

This is a development checkpoint format. It never satisfies the full Release exporter.
"""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from evidence import current, fingerprint, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '6b1f3459a80db8b7b6838e7d5e492b8ef42d9033'
BASE_VERSION = '0.3.0-dev.24'
CURRENT_VERSION = '0.3.0-dev.29'
PRIOR_COMMIT = '5abb90d3696b80f4b7c6963071e9ad625f551d6d'
PRIOR_VERSION = '0.3.0-dev.28'
CERTIFICATE = '90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17'
SOURCES = {
    'build-info.json': 'dist/build-info.json',
    'package.json': 'build/package-verification.json',
    'workbench.json': 'build/workbench-tests/results.json',
    'recovery.json': 'build/recovery-tests/results.json',
    'foundation.json': 'build/foundation-tests/results.json',
    'api.json': 'build/api-tests/results.json',
    'inputs.json': 'build/input-tests/results.json',
    'text.json': 'build/text-tests/results.json',
    'migration.json': 'build/migration-tests/results.json',
    'scheduler.json': 'build/scheduler-tests/results.json',
    'ui.json': 'build/ui-qa/results.json',
    'lint.json': 'build/android-lint/results.json',
    'workbench-media.json': 'docs/media/development/workbench/manifest.json',
    'preflight-media.json': 'docs/media/development/preflight/manifest.json',
    'recovery-media.json': 'docs/media/development/recovery/manifest.json',
    'preparation-core.json': 'build/preparation-tests/results.json',
    'assembly-core.json': 'build/assembly-tests/results.json',
    'diffusion.json': 'build/diffusion-tests/results.json',
    'lcm-media.json': 'docs/media/development/lcm/manifest.json',
    'moss-rq.json': 'build/moss-rq-tests/results.json',
    'moss-rq-arm64.json': 'build/moss_rq-arm64-evidence.json',
    'audio-media.json': 'docs/media/development/audio/manifest.json',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def baseline():
    run = subprocess.run(['git', 'archive', '--format=tar', BASELINE, 'verification/development'], cwd=ROOT, capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(run.stdout), mode='r:') as archive:
        records = {Path(item.name).name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile() and item.name.endswith('.json')}
    status = json.loads(records['status.json'])
    assert status['version'] == BASE_VERSION and len(status['sources']) == 117
    return status, records


def prior_checkpoint(write=False):
    run = subprocess.run(['git', 'archive', '--format=tar', PRIOR_COMMIT, 'verification/development'], cwd=ROOT, capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(run.stdout), mode='r:') as archive:
        records = {Path(item.name).name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile() and item.name.endswith('.json')}
    status = json.loads(records['status.json']); assert status['version'] == PRIOR_VERSION and len(status['sources']) == 21
    folder = ROOT / 'verification/history' / PRIOR_VERSION
    if write: folder.mkdir(parents=True, exist_ok=True)
    saved = {}
    for name in ['status.json', *status['sources']]:
        file = folder / name
        if write and not file.exists(): file.write_bytes(records[name])
        assert file.read_bytes() == records[name], 'Prior checkpoint changed: ' + name
        saved[name] = {'path': file.relative_to(ROOT).as_posix(), 'sha256': digest(records[name])}
    return {'commit': PRIOR_COMMIT, 'version': PRIOR_VERSION, 'sources': saved}, records


def export():
    assert version() == CURRENT_VERSION
    old_status, old = baseline()
    prior, _ = prior_checkpoint(write=True)
    directory = ROOT / 'verification/development'
    history = ROOT / 'verification/history' / BASE_VERSION
    history.mkdir(parents=True, exist_ok=True)
    # Keep the exact former status and every overwritten receipt, not reconstructed reports.
    for name in ['status.json', *[name for name in SOURCES if name in old]]:
        path = history / name
        if path.exists(): assert path.read_bytes() == old[name], 'Historical evidence cannot be overwritten: ' + name
        else: path.write_bytes(old[name])
    historical = {}
    for name in old_status['sources']:
        path = history / name if name in SOURCES else directory / name
        assert path.read_bytes() == old[name], 'Historical record changed: ' + name
        historical[name] = {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(old[name])}
    checked = {}
    records = {}
    for name, source in SOURCES.items():
        data = (ROOT / source).read_bytes(); record = json.loads(data)
        current(record['input_fingerprint'])
        for path, identity in record['input_fingerprint'].items():
            assert path not in checked or checked[path] == identity, 'Conflicting current source: ' + path
            checked[path] = identity
        records[name] = record
        (directory / name).write_bytes(data)
    assert records['build-info.json']['input_fingerprint'] == build_inputs()
    current(checked)
    status = {
        'schema': 'lma.development-checkpoint/2', 'version': CURRENT_VERSION,
        'sources': SOURCES, 'historical_sources': historical,
        'prior_checkpoint': prior,
        'historical_baseline': {'commit': BASELINE, 'version': BASE_VERSION, 'status': (history / 'status.json').relative_to(ROOT).as_posix(), 'sha256': digest(old['status.json'])},
        'release_ready': False, 'all_selected_models_supported': False,
        'physical_device_tests': 0, 'model_inference_tested': False,
        'historical_trained_results_apply_to_current_apk': False,
        'host_model_inference_tested': False, 'apk_model_inference_tested': False, 'historical_host_model_inference_tested': True,
        'model_inference_test_scope': 'Current PCM protocol, actual owned host children, authenticated sockets, real tiny codec graphs and UI; no trained Realtime speech or Android execution. Trained LCM host evidence is pinned to dev.28.',
        'scope': 'Opt-in per-model Realtime incremental PCM, transient previews, shared task/API/playback lifecycle, strict final-WAV agreement and model-free Android compilation; full frozen scope remains required',
        'required_release_scope': {'foundation': 'F01–F12', 'existing_text': True, 'selected_ids': ['01','02','03','04','05','06','07','08','09','10','11','12','13','14','16','17'], 'every_frozen_subtarget': True, 'sd15_and_sdxl_lora': True},
        'input_fingerprint': fingerprint('tools/checkpoint_evidence.py', 'tools/export_development.py', 'tools/check_repository.py', 'docs/proposals/multimodal-release-scope.json'),
    }
    (directory / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return check()


def check():
    directory = ROOT / 'verification/development'
    status = json.loads((directory / 'status.json').read_text(encoding='utf-8'))
    assert status['schema'] == 'lma.development-checkpoint/2' and status['version'] == version() == CURRENT_VERSION
    assert not status['release_ready'] and not status['all_selected_models_supported'] and not status['model_inference_tested']
    assert status['physical_device_tests'] == 0 and not status['historical_trained_results_apply_to_current_apk']
    current(status['input_fingerprint']); assert status['sources'] == SOURCES
    original, old = baseline(); assert set(status['historical_sources']) == set(original['sources'])
    prior, prior_records = prior_checkpoint(); assert status['prior_checkpoint'] == prior
    baseline_record = status['historical_baseline']
    assert baseline_record['commit'] == BASELINE and baseline_record['version'] == BASE_VERSION
    assert (ROOT / baseline_record['status']).read_bytes() == old['status.json'] and baseline_record['sha256'] == digest(old['status.json'])
    for name, item in status['historical_sources'].items():
        path = (ROOT / item['path']).resolve(); assert path.is_relative_to((ROOT / 'verification').resolve())
        assert path.read_bytes() == old[name] and item['sha256'] == digest(old[name]), 'Historical experiment changed: ' + name
    # The known failed experiment remains failed; history is never a current-APK pass.
    assert json.loads(old['lcm-overlay-trained.json'])['passed'] is False
    records = {name: json.loads((directory / name).read_text(encoding='utf-8')) for name in SOURCES}
    for name, record in records.items():
        current(record['input_fingerprint'])
        assert (directory / name).read_bytes() == (ROOT / SOURCES[name]).read_bytes(), 'Public receipt differs from its executed check: ' + name
    build, package = records['build-info.json'], records['package.json']
    assert build['version'] == CURRENT_VERSION and build['input_fingerprint'] == build_inputs()
    assert build['sha256'] == package['sha256'] == digest((ROOT / 'dist' / build['apk']).read_bytes())
    assert package['signing_certificate_sha256'] == CERTIFICATE and package['apk_signatures_independently_verified']
    assert package['native_libraries_verified'] == 30 and package['packaged_ui_matches_source'] and package['source_inputs_match_build']
    assert not package['physical_device_tested'] and not package['private_keys_in_apk']
    workbench = records['workbench.json']; assert workbench['passed'] and workbench['count'] >= 44 and workbench['actual_socket_io'] and workbench['actual_persistence_io']
    assert not workbench['android_execution_tested'] and not workbench['model_inference_tested']
    recovery = records['recovery.json']; assert recovery['passed'] and recovery['count'] >= 47 and recovery['actual_process_interruption'] and recovery['actual_persistence_io'] and recovery['actual_socket_io']
    assert not recovery['android_execution_tested'] and not recovery['model_inference_tested']
    for name, minimum in [('foundation.json',582),('api.json',67),('inputs.json',64),('text.json',66),('migration.json',69),('scheduler.json',88)]:
        assert records[name]['passed'] >= minimum, name
    ui = records['ui.json']; assert ui['passed'] >= 342 and not ui['errors'] and ui['bridge'] == 'test fixture only' and not ui['physicalDevice'] and not ui['emulatorUsed']
    lint = records['lint.json']; assert lint['errors'] == 0 and lint['applicationApkSha256'] == build['sha256']
    assert lint['java_source_files'] == len(list((ROOT / 'app/src/main/java').rglob('*.java')))
    media = records['workbench-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 5 and len(media['files']) == 7
    for item in media['files']:
        data = (ROOT / 'docs/media/development/workbench' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    media = records['preflight-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 4 and len(media['files']) == 6
    for item in media['files']:
        data = (ROOT / 'docs/media/development/preflight' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    media = records['recovery-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 4 and len(media['files']) == 6
    for item in media['files']:
        data = (ROOT / 'docs/media/development/recovery' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    assert not status['host_model_inference_tested'] and not status['apk_model_inference_tested'] and status['historical_host_model_inference_tested']
    preparation, assembly, diffusion = records['preparation-core.json'], records['assembly-core.json'], records['diffusion.json']
    assert preparation['passed'] and preparation['checks'] >= 44 and not preparation['physical_android']
    assert assembly['passed'] and assembly['checks'] >= 47 and not assembly['automatic_downloads'] and not assembly['physicalAndroid']
    assert diffusion['passed'] >= 100 and diffusion['production_sd_binding'] and not diffusion['model_inference'] and not diffusion['physical_android']
    lcm = json.loads(prior_records['lcm-app-host.json'])
    assert lcm['passed'] and lcm['production_preparation_association_generation_host_executed']
    assert lcm['java']['preparation_children'] == 1 and lcm['java']['generation_children'] == 4 and lcm['java']['network_calls'] == 0
    assert len(lcm['contracts']) == 26 and sum(c['java_accepted'] for c in lcm['contracts']) == 1
    assert all(c['no_output'] for c in lcm['contracts'])
    assert len(lcm['outputs']) == 2 and all(o['bitwise_equal_to_historical_native_prepared'] for o in lcm['outputs'])
    assert not any(lcm[k] for k in ['asset_download_attempted','physical_android','android_saf_tested','android_background_accepted','historical_pixel_comparison_passed','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
    media = records['lcm-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 4 and len(media['files']) == 6
    for item in media['files']:
        data = (ROOT / 'docs/media/development/lcm' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    media = json.loads(prior_records['lcm-trained-media.json'])
    assert media['actual_production_java_native_host'] and media['model_inference'] and not media['physical_android']
    assert not media['image_quality_accepted'] and not media['historical_pixel_comparison_passed'] and len(media['files']) == 2
    assert media['trained_report_sha256'] == digest(prior_records['lcm-app-host.json'])
    for item in media['files']:
        data = (ROOT / 'docs/media/development/lcm-app-trained' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    moss, arm = records['moss-rq.json'], records['moss-rq-arm64.json']
    assert moss['passed'] >= 304 and moss['actual_graph_processes'] == 3 and not moss['model_inference'] and not moss['physical_android']
    assert moss['incremental_audio']['actual_host_children'] == 8 and moss['incremental_audio']['before_final_wav_observations'] == 6
    assert moss['incremental_audio']['actual_authenticated_socket_io'] and moss['incremental_audio']['audio_is_synthetic_protocol_fixture']
    assert moss['codec_streaming']['sliding_window_crossed'] and moss['codec_streaming']['stream_vs_batch_max_abs_error'] <= 1e-3
    assert arm['engine'] == 'moss_rq_native' and arm['abi'] == 'arm64-v8a' and arm['android_api_notes'] == [28]
    assert arm['physical_device_tests'] == 0 and not arm['model_inference_tested'] and not arm['virtualization_used']
    assert arm['sha256'] == digest((ROOT / 'app/src/main/jniLibs/arm64-v8a/liblma-moss-rq.so').read_bytes())
    media = records['audio-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 3 and len(media['files']) == 5
    for item in media['files']:
        data = (ROOT / 'docs/media/development/audio' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    scope = json.loads((ROOT / 'docs/proposals/multimodal-release-scope.json').read_text(encoding='utf-8'))
    assert status['required_release_scope']['selected_ids'] == scope['selected_ids'] and scope['preserved_recommendation_ids'] == ['m08','m06','m01']
    return {'passed': True, 'current_records': len(SOURCES), 'historical_records': len(status['historical_sources']), 'prior_checkpoint_records': len(prior['sources']) - 1, 'version': CURRENT_VERSION, 'release_ready': False, 'physical_device_tests': 0}


if __name__ == '__main__': print(json.dumps(check()))
