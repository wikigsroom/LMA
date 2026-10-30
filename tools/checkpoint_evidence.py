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
CURRENT_VERSION = '0.3.0-dev.42'
PRIOR_COMMIT = 'd4ce9a6e46c6be3402ed515c2ab1324af1a4c3be'
PRIOR_VERSION = '0.3.0-dev.41'
CERTIFICATE = '90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17'
SOURCES = {
    'build-info.json': 'dist/build-info.json',
    'package.json': 'build/package-verification.json',
    'workbench.json': 'build/workbench-tests/results.json',
    'recovery.json': 'build/recovery-tests/results.json',
    'foundation.json': 'build/foundation-tests/results.json',
    'bundle-pause.json': 'build/bundle-pause-tests/results.json',
    'speech-intelligibility.json': 'build/speech-intelligibility-tests/results.json',
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
    'wan-media.json': 'docs/media/development/wan/manifest.json',
    'qwen-tokenizer.json': 'build/qwen-tokenizer-tests/results.json',
    'openmoss-assets.json': 'build/openmoss-trained/receipt.json',
    'openmoss-arm64.json': 'build/openmoss-build-info.json',
    'openmoss-core.json': 'build/openmoss-tests/results.json',
    'openmoss-mapping.json': 'build/openmoss-mapping-tests/results.json',
    'openmoss-trained.json': 'build/openmoss-trained-tests/results.json',
    'openmoss-media.json': 'docs/media/development/openmoss/manifest.json',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def receipt_inputs(name, record):
    key = 'source_inputs' if name == 'openmoss-arm64.json' else 'input_fingerprint'
    inputs = record.get(key)
    assert isinstance(inputs, dict) and inputs, 'Missing current verification inputs: ' + name
    return inputs


def archived_checkpoint(target_version, starting_status):
    """Read an exact older receipt chain; never refresh historical fingerprints."""
    status=json.loads(starting_status)
    for _ in range(32):
        link=status['prior_checkpoint']; records={}
        for name,item in link['sources'].items():
            path=(ROOT/item['path']).resolve();path.relative_to(ROOT.resolve())
            data=path.read_bytes();assert digest(data)==item['sha256'],'Historical checkpoint bytes changed: '+name
            records[name]=data
        status=json.loads(records['status.json']);assert status['version']==link['version']
        if status['version']==target_version:return records
    raise AssertionError('Required frozen historical checkpoint missing')


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
    status = json.loads(status_data); assert status['version'] == PRIOR_VERSION and len(status['sources']) == 44
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
    serialized = {}
    for name, source in SOURCES.items():
        data = (ROOT / source).read_bytes(); record = json.loads(data)
        for path, identity in receipt_inputs(name, record).items():
            assert path not in checked or checked[path] == identity, 'Conflicting current source: ' + path
            checked[path] = identity
        records[name] = record
        serialized[name] = data
    assert records['build-info.json']['input_fingerprint'] == build_inputs()
    # Hash each shared source once, retaining every receipt's exact expectations.
    current(checked)
    for name, data in serialized.items():
        (directory / name).write_bytes(data)
    status = {
        'schema': 'lma.development-checkpoint/2', 'version': CURRENT_VERSION,
        'sources': SOURCES, 'historical_sources': historical,
        'prior_checkpoint': prior,
        'historical_baseline': {'commit': BASELINE, 'version': BASE_VERSION, 'status': (history / 'status.json').relative_to(ROOT).as_posix(), 'sha256': digest(old['status.json'])},
        'release_ready': False, 'all_selected_models_supported': False,
        'physical_device_tests': 0, 'model_inference_tested': False,
        'historical_trained_results_apply_to_current_apk': False,
        'host_model_inference_tested': True, 'current_trained_host_engines': ['openmoss_native'], 'apk_model_inference_tested': False, 'historical_host_model_inference_tested': True,
        'model_inference_test_scope': 'Unchanged dev.41 MOSS native binary/assets and explicitly reused original cases. The 87-check production Java model run and actual media are immutable dev.41 history after the shared importer source changed. Current blocked-input regression covers 13 checks; foundation covers 692. Independent offline ASR on original WAVs passes two controls but fails reference text following. No Android inference, speech quality or complete MOSS-family acceptance.',
        'current_failed_model_gates': {'moss_tts_v15_reference_natural_completion': 'failed_at_max_new_tokens_375', 'moss_tts_v15_reference_text_following': 'failed_original_wav_asr_35_errors_over_2_words', 'moss_prompt_candidate': 'experiment_timed_out_1800s_at_step332_of375_no_wav'},
        'scope': 'Shared bundle imports close the active input on pause/shutdown and release the queue. Explicit file reselection restarts an incomplete local component, while HTTP resume keeps range validation. Original failure and independent offline prompt/ASR diagnostics are retained; the semantic prompt candidate is not adopted. Optional MOSS native assets and inference are unchanged. Foundation-only APK, preserved recommendations and HF search, no automatic model downloads, ROOT, off-device inference or ComfyUI graph ecosystem. Full frozen v0.3.0 requirements and all failed gates remain required.',
        'required_release_scope': {'foundation': 'F01–F12', 'existing_text': True, 'selected_ids': ['01','02','03','04','05','06','07','08','09','10','11','12','13','14','16','17'], 'every_frozen_subtarget': True, 'sd15_and_sdxl_lora': True},
        'input_fingerprint': fingerprint('tools/checkpoint_evidence.py', 'tools/export_development.py', 'tools/check_repository.py', 'docs/proposals/multimodal-release-scope.json', 'research/openmoss_trained/reference-investigation.json', 'verification/research/bundle-pause-issue', 'verification/research/openmoss-prompt-issue', 'verification/research/openmoss-reference-asr', 'verification/research/openmoss-prompt-candidate'),
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
    checked = {}
    for name, record in records.items():
        for path, identity in receipt_inputs(name, record).items():
            assert path not in checked or checked[path] == identity, 'Conflicting current source: ' + path
            checked[path] = identity
        assert (directory / name).read_bytes() == (ROOT / SOURCES[name]).read_bytes(), 'Public receipt differs from its executed check: ' + name
    current(checked)
    build, package = records['build-info.json'], records['package.json']
    assert build['version'] == CURRENT_VERSION and build['input_fingerprint'] == build_inputs()
    assert build['sha256'] == package['sha256'] == digest((ROOT / 'dist' / build['apk']).read_bytes())
    assert package['signing_certificate_sha256'] == CERTIFICATE and package['apk_signatures_independently_verified']
    assert package['native_libraries_verified'] == 35 and package['packaged_ui_matches_source'] and package['source_inputs_match_build']
    assert not package['physical_device_tested'] and not package['private_keys_in_apk']
    workbench = records['workbench.json']; assert workbench['passed'] and workbench['count'] >= 44 and workbench['actual_socket_io'] and workbench['actual_persistence_io']
    assert not workbench['android_execution_tested'] and not workbench['model_inference_tested']
    recovery = records['recovery.json']; assert recovery['passed'] and recovery['count'] >= 47 and recovery['actual_process_interruption'] and recovery['actual_persistence_io'] and recovery['actual_socket_io']
    assert not recovery['android_execution_tested'] and not recovery['model_inference_tested']
    for name, minimum in [('foundation.json',692),('api.json',67),('inputs.json',64),('text.json',66),('migration.json',69),('scheduler.json',151)]:
        assert records[name]['passed'] >= minimum, name
    pause=records['bundle-pause.json']
    assert pause['passed'] and pause['checks']['passed']==13 and pause['checks']['blocked_provider_cases']==2 and pause['returncode']==0
    assert pause['network_requests']==0 and not pause['physical_android'] and not pause['model_inference']
    first=json.loads((ROOT/'verification/research/bundle-pause-issue/first-run.json').read_text(encoding='utf-8'))
    assert not first['passed'] and first['returncode']!=0
    asr=records['speech-intelligibility.json']
    assert asr['passed']==2 and asr['expected_cases']==3 and not asr['all_exact_words']
    assert asr['model_inference'] and not asr['remote_inference'] and not asr['apk_model_data']
    assert not any(asr[k] for k in ['physical_android','speech_quality_accepted','voice_similarity_accepted','release_accepted'])
    assert [c['exact_words'] for c in asr['cases']]==[True,True,False]
    assert asr['cases'][2]['word_errors']==35 and asr['cases'][2]['normalized_reference']==['hello','world']
    for case in asr['cases']: assert digest((ROOT/case['path']).read_bytes())==case['sha256'] and not case['prompt_hint_supplied']
    prompt=json.loads((ROOT/'verification/research/openmoss-prompt-issue/first-run.json').read_text(encoding='utf-8'))
    assert prompt['passed']==0 and prompt['expected_cases']==7 and not prompt['all_exact']
    assert not prompt['model_inference'] and not prompt['codec_executed']
    candidate=json.loads((ROOT/'verification/research/openmoss-prompt-candidate/results.json').read_text(encoding='utf-8'))
    assert candidate['timed_out'] and candidate['experiment_not_production'] and candidate['parameters_unchanged']
    assert digest((ROOT/'verification/research/openmoss-prompt-candidate/candidate-pipeline.cpp.txt').read_bytes())==candidate['pipeline_sha256']
    assert not candidate['execution'] and not any(e.get('event')=='complete' for e in candidate['events'])
    assert candidate['events'][-1]==dict(event='progress',stage='generating_speech',step=332,steps=375)
    assert not candidate['physical_android'] and not candidate['release_accepted']
    ui = records['ui.json']; assert ui['passed'] >= 486 and not ui['errors'] and ui['bridge'] == 'test fixture only' and not ui['physicalDevice'] and not ui['emulatorUsed']
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
    assert diffusion['passed'] >= 197 and diffusion['production_sd_binding'] and not diffusion['model_inference'] and not diffusion['physical_android']
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
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots']) == 8 and len(media['files']) == 10 and len(media['checks']) >= 58
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
    assert suggestions['passed'] and suggestions['checks'] >= 69 and suggestions['production_metadata_client_controller']
    assert not suggestions['model_inference'] and not suggestions['physical_android'] and suggestions['asset_downloads']==0
    assert suggestions['historical_identity_source_commit']=='bb10c11714ab715258e20a904dd11a049e685701'
    assert records['backend.json']['passed']>=98 and records['hub.json']['passed']>=80
    media=records['components-media.json'];assert media['version']==CURRENT_VERSION and media['browser_closed'] and not media['browser_errors']
    assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded'] and len(media['screenshots'])==4 and len(media['files'])==6 and len(media['checks'])>=16
    for item in media['files']:
        data=(ROOT/'docs/media/development/components'/item['file']).read_bytes()
        assert len(data)==item['bytes'] and digest(data)==item['sha256']
    assert status['host_model_inference_tested'] and status['current_trained_host_engines']==['openmoss_native'] and not status['apk_model_inference_tested']
    mnn=records['mnn.json']; assert mnn['passed']>=101 and mnn['production_mnn_binding'] and not mnn['model_inference']
    mnn_history=archived_checkpoint('0.3.0-dev.36',prior_records['status.json'])
    assets=json.loads(mnn_history['mnn-assets.json']);assert assets['developer_assets_only'] and assets['explicit_download'] and not assets['model_executed']
    assert len(assets['components'])==15 and sum(i['bytes'] for i in assets['components'])==1661730284
    trained=json.loads(mnn_history['mnn-trained.json']);bridge=json.loads(mnn_history['mnn-app-host.json']);arm=json.loads(mnn_history['mnn-arm64.json'])
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
    assert len(bridge['outputs'])==2 and bridge['direct_report_sha256']==digest(mnn_history['mnn-trained.json'])
    assert all(i['maximum']==0 for i in bridge['comparisons'].values())
    assert arm['identical_host_android_generated_pipeline'] and len(arm['generated_pipeline'])==2
    assert arm['native']['sha256']==digest((ROOT/'app/src/main/jniLibs/arm64-v8a/liblma-mnn.so').read_bytes())
    assert bridge['compilation']['sha256']==trained['compilation']['sha256']==arm['host_worker_sha256']
    assert assets['components']==trained['assets']
    assert not any(r[k] for r in [trained,bridge] for k in ['physical_android','independent_reference_numerics_accepted','image_quality_accepted','complete_target04_accepted','complete_release_accepted'])
    media=json.loads(mnn_history['mnn-trained-media.json']);assert media['version']=='0.3.0-dev.36' and media['real_trained_host_execution'] and not media['android_recording'] and not media['image_quality_accepted']
    assert len(media['products'])==3 and len(media['files'])==8 and media['task']=='image_to_image' and media['fixed_style']
    assert media['direct_report_sha256']==digest(mnn_history['mnn-trained.json']) and media['java_report_sha256']==digest(mnn_history['mnn-app-host.json'])
    for item in media['files']:
        data=(ROOT/'docs/media/development/sana-edit-trained'/item['file']).read_bytes(); assert len(data)==item['bytes'] and digest(data)==item['sha256']
    # Preserve the complete dev.37 FLUX experiment at its original bytes and scope.
    flux_history=archived_checkpoint('0.3.0-dev.37',prior_records['status.json'])
    assets=json.loads(flux_history['flux2-assets.json']); trained=json.loads(flux_history['flux2-trained.json']); bridge=json.loads(flux_history['flux2-app-host.json'])
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
    assert bridge['direct_trained_report_sha256']==digest(flux_history['flux2-trained.json'])
    assert bridge['compilation']==trained['compilation']
    assert not any(r[k] for r in [trained,bridge] for k in ['physical_android','independent_numerics_accepted','image_quality_accepted','complete_target07_accepted','complete_release_accepted'])
    media=json.loads(flux_history['flux2-trained-media.json']); assert media['version']=='0.3.0-dev.37' and media['real_trained_host_execution'] and not media['android_recording']
    assert media['direct_report_sha256']==digest(flux_history['flux2-trained.json']) and media['java_report_sha256']==digest(flux_history['flux2-app-host.json'])
    assert not media['image_quality_accepted'] and len(media['products'])==3
    for item in media['files']:
        data=(ROOT/'docs/media/development/flux2-trained'/item['file']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    # Preserve complete dev.38 Z-Image execution as historical, never retimestamp it.
    zimage_history=archived_checkpoint('0.3.0-dev.38',prior_records['status.json'])
    assets=json.loads(zimage_history['zimage-assets.json']); trained=json.loads(zimage_history['zimage-trained.json']); bridge=json.loads(zimage_history['zimage-app-host.json'])
    zimage_lock=json.loads((ROOT/'research/zimage_trained/assets.json').read_text(encoding='utf-8'))
    assert zimage_lock['reference_tokenizer']['sha256']==records['qwen-tokenizer.json']['reference']['sha256']
    assert assets['developer_assets_only'] and assets['explicit_download'] and not assets['model_executed']
    assert len(assets['components'])==4 and sum(c['bytes'] for c in assets['components'])==6349991011
    assert trained['host_execution_checks_passed'] and trained['passed']>=35 and len(trained['runs'])==7
    assert trained['components']==assets['components'] and all(c['passed'] for c in trained['checks'])
    for run in trained['runs']:
        assert not run['process']['protocol_errors'] and not run['process']['timed_out']
        if 'image' in run:
            assert run['process']['returncode']==0
            path=ROOT/trained['capture_directory']/(run['name']+'.png');assert digest(path.read_bytes())==run['image']['sha256']
    first=next(r for r in trained['runs'] if r['name']=='a')['process']['events']
    eighth=[e for e in first if e.get('event')=='progress' and e.get('step',0)>0 and e.get('steps')==8*e['step']]
    assert [(e['step'],e['steps']) for e in eighth]==[(1,8)]
    cancel=next(r for r in trained['runs'] if r['name']=='cancel-step1')['process']
    assert cancel['forced_host_termination'] and cancel['cancel_trigger']['steps']==8 and cancel['cancel_trigger']['step']==1
    assert trained['comparisons']['recovery-a']['maximum']==0 and all(trained['comparisons'][n]['maximum']>0 for n in ['b','one-step'])
    assert bridge['production_java_native_host_executed'] and bridge['java']['passed']>=100
    assert bridge['java']['actual_host_children']==3 and bridge['java']['imported_objects']==4 and bridge['java']['network_calls']==0
    assert len(bridge['outputs'])==2 and all(i['bitwise_equal_to_direct_native'] for i in bridge['outputs'])
    assert bridge['direct_trained_report_sha256']==digest(zimage_history['zimage-trained.json'])
    assert bridge['compilation']==trained['compilation']
    assert not any(r[k] for r in [trained,bridge] for k in ['physical_android','independent_numerics_accepted','image_quality_accepted','complete_target06_accepted','complete_release_accepted'])
    tokenizer=records['qwen-tokenizer.json']
    assert tokenizer['passed'] and tokenizer['check_count']>=117 and tokenizer['official_base_vocabulary_ids']>=150000
    assert tokenizer['actual_production_tokenizer'] and tokenizer['independent_reference']=='Hugging Face tokenizer.json + Rust tokenizers'
    assert tokenizer['variants']==3 and tokenizer['texts']==33 and tokenizer['network_calls']==0 and not tokenizer['bundled_tokenizer_data']
    assert tokenizer['compilation']['source_revision']==trained['compilation']['source_revision'] and not tokenizer['model_inference'] and not tokenizer['physical_android']
    media=json.loads(zimage_history['zimage-trained-media.json']); assert media['version']=='0.3.0-dev.38' and media['real_trained_host_execution'] and not media['android_recording']
    assert media['direct_report_sha256']==digest(zimage_history['zimage-trained.json']) and media['java_report_sha256']==digest(zimage_history['zimage-app-host.json'])
    assert not media['image_quality_accepted'] and len(media['products'])==3
    for item in media['files']:
        data=(ROOT/'docs/media/development/zimage-trained'/item['file']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    # Exact dev.40 Wan evidence, including original failed quality gates.
    wan_records=archived_checkpoint('0.3.0-dev.40',prior_records['status.json'])
    wan_history={name:json.loads(wan_records[name]) for name in ['wan-assets.json','wan-trained.json','wan-app-host.json','wan-quality.json','wan-trained-media.json']}
    assets=wan_history['wan-assets.json'];trained=wan_history['wan-trained.json'];bridge=wan_history['wan-app-host.json']
    assert assets['developer_assets_only'] and assets['explicit_download'] and not assets['model_executed']
    assert len(assets['components'])==4 and sum(c['bytes'] for c in assets['components'])==4741874667
    assert trained['components']==assets['components'] and trained['host_execution_checks_passed'] and len(trained['runs'])==9
    assert all(c['passed'] for c in trained['checks']) and trained['passed']>=49
    for run in trained['runs']:
        assert not run['process']['protocol_errors'] and not run['process']['timed_out']
        if 'frames' in run:
            path=ROOT/trained['capture_directory']/(run['name']+'.rgb')
            assert digest(path.read_bytes())==run['frames']['sha256'] and run['frames']['changed_from_first']>0
            details=[e['details'] for e in run['process']['events'] if e.get('event')=='execution']
            assert len(details)==1 and details[0]['vulkanGraphObserved'] and details[0]['diffusionBackend']=='vulkan0'
            assert details[0]['textBackend']==details[0]['vaeBackend']=='cpu' and not details[0]['remoteInference']
    cancel=next(r for r in trained['runs'] if r['name']=='cancel-step1')['process']
    assert cancel['forced_host_termination'] and cancel['cancel_trigger']['step']==1 and cancel['cancel_trigger']['steps']==4
    assert bridge['production_java_native_host_executed'] and bridge['java']['passed']>=102
    assert bridge['java']['actual_host_children']==3 and bridge['java']['imported_objects']==4 and bridge['java']['network_calls']==0
    assert len(bridge['outputs'])==2 and all(i['raw_frames_bitwise_equal_to_direct_native'] for i in bridge['outputs'])
    assert bridge['direct_trained_report_sha256']==digest(wan_records['wan-trained.json'])
    assert bridge['compilation']==trained['compilation'] and bridge['host_ffmpeg'] and not bridge['android_codec_tested']
    assert not any(r[k] for r in [trained,bridge] for k in ['physical_android','independent_numerics_accepted','video_quality_accepted','complete_target16_accepted','complete_release_accepted'])
    quality=wan_history['wan-quality.json']
    assert quality['version']=='0.3.0-dev.40' and quality['aggregation_current'] and not quality['original_captures_are_current_validation']
    assert len(quality['experiments'])==5 and len(quality['original_captures'])==7
    assert quality['default_decoder']==dict(vaeTileSize=128,vaeTemporalTiling=False)
    assert quality['official_vae_revision']=='9737cba9c1c3c4d04b33fcad41c111989865d315'
    assert not any(quality[k] for k in ['physical_android','android_codec_tested','independent_diffusion_numerics_accepted','video_quality_accepted','resource_acceptance','complete_target16_accepted','complete_release_accepted'])
    for item in quality['original_captures'].values():
        assert not item['current_execution'] and item['original_provenance_preserved']
        data=(ROOT/item['path']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    for item in quality['media']:
        data=(ROOT/'docs/media/development/wan-quality'/item['file']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    for name,folder in [('wan-media.json','wan'),('wan-trained-media.json','wan-trained')]:
        media=records[name] if name=='wan-media.json' else wan_history[name];assert media['version']==(CURRENT_VERSION if name=='wan-media.json' else '0.3.0-dev.40')
        if name=='wan-media.json':
            assert media['browser_closed'] and not media['browser_errors'] and not media['android_device'] and not media['model_inference']
            assert len(media['screenshots'])==4 and len(media['checks'])>=9 and not media['weights_downloaded']
        else:
            assert media['real_trained_host_execution'] and not media['android_recording'] and not media['video_quality_accepted']
            assert media['direct_report_sha256']==digest(wan_records['wan-trained.json'])
            assert media['java_report_sha256']==digest(wan_records['wan-app-host.json'])
        for item in media['files']:
            data=(ROOT/'docs/media/development'/folder/item['file']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    # Current, complete MOSS-TTS 1.5 only; no other family or phone is inferred.
    moss_assets=records['openmoss-assets.json'];moss_core=records['openmoss-core.json']
    moss_arm=records['openmoss-arm64.json'];moss=records['openmoss-trained.json'];moss_app=json.loads(prior_records['openmoss-app-host.json'])
    assert moss_assets['explicit_download'] and moss_assets['developer_assets_only'] and not moss_assets['bundled_model_data']
    assert len(moss_assets['components'])==2 and sum(c['bytes'] for c in moss_assets['components'])==13430589376
    assert moss_core['passed']>=530 and moss_core['production_openmoss_binding'] and not moss_core['model_inference']
    assert moss_arm['engine']=='openmoss_native' and moss_arm['backend']=='cpu' and moss_arm['physical_device_tests']==0
    assert moss_arm['sha256']==next(e for e in json.loads((ROOT/'third_party/engine-lock.json').read_text(encoding='utf-8'))['engines'] if e['engine']=='openmoss_native')['sha256']
    assert moss['host_business_checks_passed'] and not moss['host_execution_checks_passed'] and not moss['smoke_only']
    assert moss['failures']==['Natural completion failed: reference reached the explicit output limit']
    assert not moss['reference_natural_completion_accepted']
    assert len(moss['jobs'])==5 and len(moss['controls'])==6 and all(j['business_passed'] for j in moss['jobs']+moss['controls'])
    assert [j['name'] for j in moss['jobs']+moss['controls'] if not j['passed']]==['reference']
    assert status['current_failed_model_gates']['moss_tts_v15_reference_natural_completion']=='failed_at_max_new_tokens_375'
    # A source review is metadata supporting the retained failure, not a new executed test.
    reference=json.loads((ROOT/'research/openmoss_trained/reference-investigation.json').read_text(encoding='utf-8'))
    assert not reference['reference_natural_completion_accepted'] and not reference['cause_established']
    original_report=ROOT/reference['original_failure_report'];original_moss=json.loads(original_report.read_text(encoding='utf-8'))
    assert digest(original_report.read_bytes())==reference['original_failure_report_sha256']==moss['resumed_report_sha256']
    assert not original_moss['host_execution_checks_passed'] and original_moss['jobs'][-1]['name']=='reference'
    original_driver=original_report.parent/'original-driver.py.txt'
    assert digest(original_driver.read_bytes())==original_moss['input_fingerprint']['tools/test_openmoss_trained.py']
    assert original_moss['compilation']['sha256']==moss['compilation']['sha256']
    assert len(moss['reused_original_cases'])==8 and moss['asset_verification_mode']=='reuse_original_full_sha_receipt'
    for case in moss['jobs']+moss['controls']:
        origin=case['capture_origin']
        assert origin['native_build_and_exact_request_unchanged']
        assert origin['reexecuted']==(case['name'] not in moss['reused_original_cases'])
        if not origin['reexecuted']:
            assert origin['report_sha256']==reference['original_failure_report_sha256']
            assert origin['original_capture_directory']==original_moss['capture_directory']
            assert origin['original_capture_sha256']==original_moss['files'][case['name']+'-capture.json']['sha256']
    assert moss['recovery_bitwise_identical'] and moss['production_worker_source_unmodified'] and not moss['fixture']
    mapping=records['openmoss-mapping.json']
    assert mapping['passed']>=20 and mapping['mapped_cpu_graph_bitwise_equal'] and mapping['copy_on_write_preserves_file']
    assert mapping['sparse_offset_above_4gib'] and mapping['all_mappings_released'] and not mapping['model_weights_used']
    assert mapping['executable_sha256']==moss['mapping_contract']['executable_sha256']
    assert moss['pre_mapping_pcm_bitwise_identical'] and moss_arm['private_weight_mapping']
    baseline_path=ROOT/'verification/research/openmoss-memory/baseline.json'
    baseline_moss=json.loads(baseline_path.read_text(encoding='utf-8'))
    assert digest(baseline_path.read_bytes())==moss['memory_baseline_sha256']
    assert not baseline_moss['full_run_passed'] and baseline_moss['interrupted_after_two_successes_for_memory_optimization']
    for name,item in baseline_moss['files'].items():
        data=(baseline_path.parent/name).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    for job in moss['jobs']:
        assert job['audio']['sample_rate']==24000 and job['audio']['channels']==1 and job['audio']['sample_width']==2
        assert job['sampled_progress']==list(range(job['execution']['generationSteps']+1))
        assert job['execution']['truncated']==(job['name'] in ['frame-limit','reference'])
        assert job['execution']['auxWeightStorage']=='private_file_mapping' and job['execution']['auxWeightMappingsReleased']
        assert not job['execution']['mappedBytesAreResidentMemory']
        path=ROOT/moss['capture_directory']/(job['name']+'.wav')
        assert digest(path.read_bytes())==job['audio']['sha256']
    assert moss_app['production_java_native_host_executed'] and moss_app['java']['passed']>=80
    assert not moss_app['reference_natural_completion_accepted']
    assert moss_app['java']['actual_host_children']==5 and moss_app['java']['registered_objects']==2 and moss_app['java']['network_calls']==0
    assert moss_app['java']['selected_asset_bytes']==13430589376
    assert moss_app['java']['asset_registration_mode']=='explicit_existing_local_full_sha_adoption'
    assert not moss_app['java']['full_stream_import_tested'] and moss_app['java']['copied_import_bytes']==0
    import_attempt_path=ROOT/'verification/research/openmoss-import-issue/attempt.json'
    import_attempt=json.loads(import_attempt_path.read_text(encoding='utf-8'))
    assert not import_attempt['host_stream_import_passed'] and not import_attempt['android_saf_tested']
    assert import_attempt['deadline_seconds']==900 and import_attempt['actual_model_children']==0 and import_attempt['partial_bytes']==3565027328
    for name,item in import_attempt['files'].items():
        original=(import_attempt_path.parent/name).read_bytes()
        assert len(original)==item['bytes'] and digest(original)==item['sha256'],'Original import timeout changed: '+name
    assert len(moss_app['outputs'])==3 and moss_app['direct_trained_report_sha256']==digest((ROOT/SOURCES['openmoss-trained.json']).read_bytes())
    for output in moss_app['outputs']:
        job=next(j for j in moss_app['java']['runs'] if j['name']==output['name'])
        assert job['execution']['auxWeightStorage']=='private_file_mapping' and job['execution']['auxWeightMappingsReleased']
        if output['name'] in ['initial-a','recovery-a']:
            assert output['audio']['sha256']==next(j for j in moss['jobs'] if j['name']=='english')['audio']['sha256']
    assert not any(r['physical_android'] for r in [moss,moss_app]) and not moss_app['complete_target12_accepted'] and not moss_app['complete_release_accepted']
    media=json.loads(prior_records['openmoss-trained-media.json'])
    # Exact dev.41 bytes above establish history; this media schema has no version field.
    assert media['original_wav_bytes_unchanged'] and not media['waveform_amplitude_normalized']
    assert not media['reference_natural_completion_accepted']
    assert not media['physical_android'] and not media['app_screen_recording'] and not media['speech_quality_accepted']
    assert media['gif_frames']==3 and len(media['source_audio'])==3 and len(media['files'])==6
    for name,expected in media['sources'].items():
        data=prior_records['openmoss-app-host.json'] if name=='verification/development/openmoss-app-host.json' else (ROOT/name).read_bytes()
        assert digest(data)==expected
    for name,item in media['files'].items():
        data=(ROOT/'docs/media/development'/name).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    for item in media['source_audio']:
        original_job=next(j for j in moss['jobs'] if j['name']==item['case'])
        assert item['audio']['sha256']==original_job['audio']['sha256']==media['files'][item['file']]['sha256']
    ui=records['openmoss-media.json'];assert ui['version']==CURRENT_VERSION and ui['browser_closed'] and not ui['browser_errors']
    assert len(ui['screenshots'])==5 and len(ui['checks'])>=56 and not ui['model_inference'] and not ui['android_device']
    for item in ui['files']:
        data=(ROOT/'docs/media/development/openmoss'/item['file']).read_bytes();assert len(data)==item['bytes'] and digest(data)==item['sha256']
    scope = json.loads((ROOT / 'docs/proposals/multimodal-release-scope.json').read_text(encoding='utf-8'))
    assert status['required_release_scope']['selected_ids'] == scope['selected_ids'] and scope['preserved_recommendation_ids'] == ['m08','m06','m01']
    return {'passed': True, 'current_records': len(SOURCES), 'historical_records': len(status['historical_sources']), 'prior_checkpoint_records': len(prior['sources']) - 1, 'version': CURRENT_VERSION, 'release_ready': False, 'physical_device_tests': 0}


if __name__ == '__main__': print(json.dumps(check()))
