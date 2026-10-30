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
CURRENT_VERSION = '0.3.0-dev.37'
PRIOR_COMMIT = '77d95dbc838d4bc573478265d68b647c3a2c864b'
PRIOR_VERSION = '0.3.0-dev.36'
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
    'ltx-app.json': 'build/ltx098-app-tests/results.json',
    'ltx-app-arm64.json': 'build/ltx098-app-arm64/receipt.json',
    'ltx-media.json': 'docs/media/development/ltx/manifest.json',
    'resources-media.json': 'docs/media/development/resources/manifest.json',
    'curated-media.json': 'docs/media/development/curated/manifest.json',
    'speech-voices.json': 'build/speech-voice-tests/results.json',
    'speech-media.json': 'docs/media/development/speech/manifest.json',
    'backend.json': 'build/backend-tests/results.json',
    'hub.json': 'build/hub-tests/results.json',
    'recipe-suggestions.json': 'build/recipe-suggestion-tests/results.json',
    'components-media.json': 'docs/media/development/components/manifest.json',
    'mnn.json': 'build/mnn-tests/results.json',
    'flux2-assets.json': 'build/flux2-trained/receipt.json',
    'flux2-trained.json': 'build/flux2-trained-tests/results.json',
    'flux2-app-host.json': 'build/flux2-app-host-tests/results.json',
    'flux2-trained-media.json': 'docs/media/development/flux2-trained/manifest.json',
    'qwen-tokenizer.json': 'build/qwen-tokenizer-tests/results.json',
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
    # Only archive this checkpoint's own records. Older model experiments have
    # separate immutable pointers and are not inputs to this incremental copy.
    status_data = subprocess.check_output(['git','show',PRIOR_COMMIT + ':verification/development/status.json'], cwd=ROOT)
    status = json.loads(status_data); assert status['version'] == PRIOR_VERSION and len(status['sources']) == 39
    selected = ['status.json', *status['sources']]
    assert all(Path(name).name == name and name.endswith('.json') for name in selected)
    run = subprocess.run(['git', 'archive', '--format=tar', PRIOR_COMMIT, *['verification/development/' + name for name in selected]], cwd=ROOT, capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(run.stdout), mode='r:') as archive:
        records = {Path(item.name).name: archive.extractfile(item).read() for item in archive.getmembers() if item.isfile() and item.name.endswith('.json')}
    assert records['status.json'] == status_data and set(records) == set(selected)
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
        'host_model_inference_tested': True, 'current_trained_host_engines': ['sd_cpp'], 'apk_model_inference_tested': False, 'historical_host_model_inference_tested': True,
        'model_inference_test_scope': 'Current complete FLUX.2-klein 4B native Windows CPU and production Java execution; four user-owned pinned components and independent official Qwen tokenizer IDs. Sana Edit trained execution remains exact dev.36 history. No Android model inference, image quality or full numerical acceptance.',
        'scope': 'Optional FLUX.2-klein 4B catalogue/HF selection, explicit complete-asset lifecycle, independent settings, immutable jobs, real generation/cancellation/recovery and managed outputs; shared external Qwen merge header correction with complete vocabulary/reference checks. Foundation-only APK, preserved recommendations, no automatic downloads, no ROOT or off-device inference, no ComfyUI graph ecosystem. Full frozen v0.3.0 requirements and failed gates remain unchanged.',
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
    assert package['native_libraries_verified'] == 34 and package['packaged_ui_matches_source'] and package['source_inputs_match_build']
    assert not package['physical_device_tested'] and not package['private_keys_in_apk']
    workbench = records['workbench.json']; assert workbench['passed'] and workbench['count'] >= 44 and workbench['actual_socket_io'] and workbench['actual_persistence_io']
    assert not workbench['android_execution_tested'] and not workbench['model_inference_tested']
    recovery = records['recovery.json']; assert recovery['passed'] and recovery['count'] >= 47 and recovery['actual_process_interruption'] and recovery['actual_persistence_io'] and recovery['actual_socket_io']
    assert not recovery['android_execution_tested'] and not recovery['model_inference_tested']
    for name, minimum in [('foundation.json',666),('api.json',67),('inputs.json',64),('text.json',66),('migration.json',69),('scheduler.json',151)]:
        assert records[name]['passed'] >= minimum, name
    ui = records['ui.json']; assert ui['passed'] >= 457 and not ui['errors'] and ui['bridge'] == 'test fixture only' and not ui['physicalDevice'] and not ui['emulatorUsed']
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
    assert status['host_model_inference_tested'] and not status['apk_model_inference_tested'] and status['historical_host_model_inference_tested']
    preparation, assembly, diffusion = records['preparation-core.json'], records['assembly-core.json'], records['diffusion.json']
    assert preparation['passed'] and preparation['checks'] >= 44 and not preparation['physical_android']
    assert assembly['passed'] and assembly['checks'] >= 47 and not assembly['automatic_downloads'] and not assembly['physicalAndroid']
    assert diffusion['passed'] >= 100 and diffusion['production_sd_binding'] and not diffusion['model_inference'] and not diffusion['physical_android']
    # dev.29 did not rerun trained LCM. Validate the immutable dev.28 pointer,
    # rather than presenting an old leftover public file as current evidence.
    lcm_history = json.loads(prior_records['status.json'])['prior_checkpoint']
    while lcm_history['version'] != '0.3.0-dev.28':
        item = lcm_history['sources']['status.json']; data = (ROOT / item['path']).read_bytes()
        assert digest(data) == item['sha256'], 'Historical checkpoint pointer changed'
        lcm_history = json.loads(data)['prior_checkpoint']
    assert lcm_history['version'] == '0.3.0-dev.28' and lcm_history['commit'] == '5abb90d3696b80f4b7c6963071e9ad625f551d6d'
    def lcm_historical(name):
        item = lcm_history['sources'][name]
        path = (ROOT / item['path']).resolve()
        assert path.is_relative_to((ROOT / 'verification/history/0.3.0-dev.28').resolve())
        data = path.read_bytes(); assert digest(data) == item['sha256']
        return data
    lcm = json.loads(lcm_historical('lcm-app-host.json'))
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
    media = json.loads(lcm_historical('lcm-trained-media.json'))
    assert media['actual_production_java_native_host'] and media['model_inference'] and not media['physical_android']
    assert not media['image_quality_accepted'] and not media['historical_pixel_comparison_passed'] and len(media['files']) == 2
    assert media['trained_report_sha256'] == digest(lcm_historical('lcm-app-host.json'))
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
    ltx_history = json.loads(prior_records['status.json'])['prior_checkpoint']
    while ltx_history['version'] != '0.3.0-dev.31':
        item = ltx_history['sources']['status.json']; data = (ROOT / item['path']).read_bytes()
        assert digest(data) == item['sha256'], 'Historical LTX checkpoint pointer changed'
        ltx_history = json.loads(data)['prior_checkpoint']
    assert ltx_history['commit'] == '251c69db9c19bafb7416d023053600643109995c'
    def ltx_historical(name):
        item = ltx_history['sources'][name]; path = (ROOT / item['path']).resolve()
        assert path.is_relative_to((ROOT / 'verification/history/0.3.0-dev.31').resolve())
        data = path.read_bytes(); assert digest(data) == item['sha256']
        return data
    app, trained, arm = records['ltx-app.json'], json.loads(ltx_historical('ltx-app-trained.json')), records['ltx-app-arm64.json']
    assert app['passed'] and app['assertions'] >= 127 and app['productionEngineAndQueue'] and app['syntheticNeuralStages'] and not app['modelInference']
    assert len(app['runs']) == 9 and [run['actualChildren'] for run in app['runs']] == [6,2,3,5,2,2,6,2,2]
    assert trained['passed'] and trained['productionEngineAndQueue'] and trained['modelInference'] and trained['actual_trained_jobs'] == 1
    assert trained['runs'][0]['actualChildren'] == 6 and len(trained['asset_receipts']) == 22
    assert trained['assertions'] >= 38 and not trained['syntheticNeuralStages'] and trained['hostMediaPort'] == 'ffmpeg_libx264_not_android'
    assert len(trained['prior_original_native_chain_comparison']) == 7 and all(c['byte_identical'] for c in trained['prior_original_native_chain_comparison'].values())
    assert not trained['original_numerical_acceptance_passed'] and trained['original_failures_preserved']
    assert all(not r[k] for r in [app,trained] for k in ['physicalAndroid','numericalAccepted','qualityAccepted'])
    assert arm['android_arm64_compiled'] and arm['min_sdk'] == 28 and len(arm['stages']) == 4
    assert not any(arm[k] for k in ['model_inference','physical_android','numerical_accepted','quality_accepted','virtualization_used'])
    for stage in arm['stages']:
        data = (ROOT / stage['path']).read_bytes(); assert len(data) == stage['bytes'] and digest(data) == stage['sha256']
    media = records['ltx-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 4 and len(media['files']) == 6
    for item in media['files']:
        data = (ROOT / 'docs/media/development/ltx' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    media = json.loads(ltx_historical('ltx-trained-media.json'))
    assert media['model_inference'] and media['actual_production_java_native_host'] and not media['physical_android'] and not media['numerical_accepted'] and not media['quality_accepted']
    assert media['trained_report_sha256'] == digest(ltx_historical('ltx-app-trained.json')) and len(media['files']) == 3
    for item in media['files']:
        data = (ROOT / 'docs/media/development/ltx-app-trained' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    media = records['resources-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 3 and len(media['files']) == 5 and len(media['checks']) >= 9
    for item in media['files']:
        data = (ROOT / 'docs/media/development/resources' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    media = records['curated-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 6 and len(media['files']) == 8 and len(media['checks']) >= 49
    for item in media['files']:
        data = (ROOT / 'docs/media/development/curated' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    voices = records['speech-voices.json']
    assert voices['passed'] and voices['checks'] >= 70 and voices['max_java_heap_bytes'] == 50331648
    assert not voices['model_inference'] and not voices['android_device'] and not voices['weights_downloaded']
    assert [(m['id'],m['voices'],m['names']) for m in voices['actual_local_headers']] == [('kokoro',54,54),('piper',1,0),('matcha',1,0),('nano',18,18)]
    media = records['speech-media.json']; assert media['version'] == CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 4 and len(media['files']) == 6 and len(media['checks']) >= 20
    for item in media['files']:
        data = (ROOT / 'docs/media/development/speech' / item['file']).read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256']
    suggestions=records['recipe-suggestions.json']
    assert suggestions['passed'] and suggestions['checks'] >= 57 and suggestions['production_metadata_client_controller']
    assert not suggestions['model_inference'] and not suggestions['physical_android'] and suggestions['asset_downloads']==0
    assert suggestions['historical_identity_source_commit']=='bb10c11714ab715258e20a904dd11a049e685701'
    assert records['backend.json']['passed']>=98 and records['hub.json']['passed']>=80
    media=records['components-media.json'];assert media['version']==CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots'])==4 and len(media['files'])==6 and len(media['checks'])>=16
    for item in media['files']:
        data=(ROOT/'docs/media/development/components'/item['file']).read_bytes()
        assert len(data)==item['bytes'] and digest(data)==item['sha256']
    assert status['host_model_inference_tested'] and status['current_trained_host_engines']==['sd_cpp'] and not status['apk_model_inference_tested']
    mnn=records['mnn.json']; assert mnn['passed']>=101 and mnn['production_mnn_binding'] and not mnn['model_inference']
    assets=json.loads(prior_records['mnn-assets.json']);assert assets['developer_assets_only'] and assets['explicit_download'] and not assets['model_executed']
    assert len(assets['components'])==15 and sum(i['bytes'] for i in assets['components'])==1661730284
    trained=json.loads(prior_records['mnn-trained.json']);bridge=json.loads(prior_records['mnn-app-host.json']);arm=json.loads(prior_records['mnn-arm64.json'])
    assert trained['passed'] and trained['real_trained_host_execution'] and len(trained['runs'])==14 and len(trained['assets'])==15 and trained['task']=='image_to_image' and trained['fixed_style']
    assert all(c['passed'] for c in trained['checks']) and len(trained['checks'])>=52
    success=['a','jpeg-crop','single-step','recovery-a']
    for run in trained['runs']:
        events=run['process']['events'];completed=[e for e in events if e.get('event')=='complete'];errors=[e for e in events if e.get('event')=='error']
        assert not run['process']['protocol_errors'] and not run['process']['timed_out']
        if run['name'] in success:
            assert run['process']['returncode']==0 and len(completed)==1 and not errors
            path=ROOT/trained['capture_directory']/(run['name']+'.png'); assert digest(path.read_bytes())==run['image']['sha256']
            progress=[e['fraction'] for e in events if e.get('event')=='progress'];steps=run['request']['parameters']['steps']
            assert progress==[(i+1)/steps for i in range(steps)]
        else:
            assert run['process']['returncode']!=0 and not completed and len(errors)==1 and errors[0]['message']
    assert trained['comparisons']['recovery']['maximum']==0 and all(trained['comparisons'][n]['maximum']>0 for n in ['source-effect','step-effect'])
    assert bridge['passed'] and bridge['production_java_native_host_executed'] and bridge['java']['actual_host_children']==3 and bridge['java']['imported_objects']==15 and bridge['java']['network_calls']==0
    assert len(bridge['outputs'])==2 and bridge['direct_report_sha256']==digest(prior_records['mnn-trained.json'])
    assert all(i['maximum']==0 for i in bridge['comparisons'].values())
    assert arm['identical_host_android_generated_pipeline'] and len(arm['generated_pipeline'])==2
    assert arm['native']['sha256']==digest((ROOT/'app/src/main/jniLibs/arm64-v8a/liblma-mnn.so').read_bytes())
    assert bridge['compilation']['sha256']==trained['compilation']['sha256']==arm['host_worker_sha256']
    assert assets['components']==trained['assets']
    assert not any(r[k] for r in [trained,bridge] for k in ['physical_android','independent_reference_numerics_accepted','image_quality_accepted','complete_target04_accepted','complete_release_accepted'])
    media=json.loads(prior_records['mnn-trained-media.json']);assert media['version']==PRIOR_VERSION and media['real_trained_host_execution'] and not media['android_recording'] and not media['image_quality_accepted']
    assert len(media['products'])==3 and len(media['files'])==8 and media['task']=='image_to_image' and media['fixed_style']
    assert media['direct_report_sha256']==digest(prior_records['mnn-trained.json']) and media['java_report_sha256']==digest(prior_records['mnn-app-host.json'])
    for item in media['files']:
        data=(ROOT/'docs/media/development/sana-edit-trained'/item['file']).read_bytes(); assert len(data)==item['bytes'] and digest(data)==item['sha256']
    # Current FLUX execution is distinct from the byte-exact historical Sana experiment.
    assets=records['flux2-assets.json']; trained=records['flux2-trained.json']; bridge=records['flux2-app-host.json']
    assert assets['developer_assets_only'] and assets['explicit_download'] and not assets['model_executed']
    assert len(assets['components'])==4 and sum(c['bytes'] for c in assets['components'])==5127452603
    assert trained['host_execution_checks_passed'] and trained['passed']>=35 and len(trained['runs'])==7
    assert trained['components']==assets['components'] and all(c['passed'] for c in trained['checks'])
    for run in trained['runs']:
        assert not run['process']['protocol_errors'] and not run['process']['timed_out']
        if 'image' in run:
            assert run['process']['returncode']==0
            path=ROOT/trained['capture_directory']/(run['name']+'.png');assert digest(path.read_bytes())==run['image']['sha256']
    cancel=next(r for r in trained['runs'] if r['name']=='cancel-step1')['process']
    assert cancel['forced_host_termination'] and cancel['cancel_trigger']['steps']==4 and cancel['cancel_trigger']['step']==1
    assert trained['comparisons']['recovery-a']['maximum']==0 and all(trained['comparisons'][n]['maximum']>0 for n in ['b','one-step'])
    assert bridge['production_java_native_host_executed'] and bridge['java']['passed']>=50
    assert bridge['java']['actual_host_children']==3 and bridge['java']['imported_objects']==4 and bridge['java']['network_calls']==0
    assert len(bridge['outputs'])==2 and all(i['bitwise_equal_to_direct_native'] for i in bridge['outputs'])
    assert bridge['direct_trained_report_sha256']==digest((ROOT/SOURCES['flux2-trained.json']).read_bytes())
    assert bridge['compilation']==trained['compilation']
    assert not any(r[k] for r in [trained,bridge] for k in ['physical_android','independent_numerics_accepted','image_quality_accepted','complete_target07_accepted','complete_release_accepted'])
    tokenizer=records['qwen-tokenizer.json']
    assert tokenizer['passed'] and tokenizer['check_count']>=117 and tokenizer['official_base_vocabulary_ids']>=150000
    assert tokenizer['actual_production_tokenizer'] and tokenizer['independent_reference']=='Hugging Face tokenizer.json + Rust tokenizers'
    assert tokenizer['variants']==3 and tokenizer['texts']==33 and tokenizer['network_calls']==0 and not tokenizer['bundled_tokenizer_data']
    assert tokenizer['compilation']==trained['compilation'] and not tokenizer['model_inference'] and not tokenizer['physical_android']
    media=records['flux2-trained-media.json']; assert media['version']==CURRENT_VERSION and media['real_trained_host_execution'] and not media['android_recording']
    assert media['direct_report_sha256']==digest((ROOT/SOURCES['flux2-trained.json']).read_bytes()) and media['java_report_sha256']==digest((ROOT/SOURCES['flux2-app-host.json']).read_bytes())
    assert not media['image_quality_accepted'] and len(media['products'])==3
    for item in media['files']:
        data=(ROOT/'docs/media/development/flux2-trained'/item['file']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    scope = json.loads((ROOT / 'docs/proposals/multimodal-release-scope.json').read_text(encoding='utf-8'))
    assert status['required_release_scope']['selected_ids'] == scope['selected_ids'] and scope['preserved_recommendation_ids'] == ['m08','m06','m01']
    return {'passed': True, 'current_records': len(SOURCES), 'historical_records': len(status['historical_sources']), 'prior_checkpoint_records': len(prior['sources']) - 1, 'version': CURRENT_VERSION, 'release_ready': False, 'physical_device_tests': 0}


if __name__ == '__main__': print(json.dumps(check()))
