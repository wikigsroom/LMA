"""Independently audit trained Nano outputs, production Java binding and scope."""
import argparse
import array
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import wave

from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
PATHS = {'moss-nano-assets.json': 'build/moss-nano-trained/receipt.json',
         'moss-nano-trained.json': 'build/moss-nano-trained-tests/results.json',
         'moss-nano-app-host.json': 'build/moss-nano-app-host-tests/results.json',
         'moss-nano-capture-audit.json': 'build/moss-nano-trained-tests/capture-audit.json'}
FALSE_DIRECT = ['fixture', 'asset_download_attempted', 'physical_android', 'app_executed',
    'android_cooperative_cancellation_tested', 'speech_quality_accepted', 'android_background_accepted',
    'device_resource_fit_accepted', 'complete_target09_accepted', 'complete_release_accepted']
FALSE_APP = ['physical_android', 'android_saf_tested', 'android_background_accepted',
             'speech_quality_accepted', 'complete_target09_accepted', 'complete_release_accepted']


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(data): return hashlib.sha256(data).hexdigest()


def identity(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''): h.update(block)
    return dict(bytes=path.stat().st_size, sha256=h.hexdigest())


def check(records, status, digest, root, with_audit=True, with_media=True):
    from build_moss_nano_host import inputs as build_inputs
    from fetch_moss_nano_trained import inputs as asset_inputs, selected
    from test_moss_nano_trained import inputs as direct_inputs, CASES
    from test_moss_nano_app_host import inputs as app_inputs
    assets, trained, app, compilation = [records[name] for name in
        ['moss-nano-assets.json', 'moss-nano-trained.json', 'moss-nano-app-host.json', 'moss-nano-host-build.json']]
    for value, expected in [(assets, asset_inputs()), (trained, direct_inputs()), (app, app_inputs()), (compilation, build_inputs())]:
        current(value['input_fingerprint']); assert value['input_fingerprint'] == expected
    lock = selected(); components = lock['components']
    assert assets['schema'] == 'lma.moss-nano-trained-assets/1'
    assert assets['explicit_download'] and assets['developer_assets_only'] and not assets['model_executed'] and not assets['app_assets_modified']
    assert assets['download_origin'] in ['https://huggingface.co', 'https://hf-mirror.com']
    assert [{k: v for k, v in x.items() if k != 'local_path'} for x in assets['components']] == components
    assert len(components) == 11 and sum(x['bytes'] for x in components) == 717414286
    assert compilation['schema'] == 'lma.moss-nano-host-build/1' and compilation['backend'] == 'cpu'
    assert compilation['production_worker_source_unmodified'] and compilation['windows_crt_compatibility'] and compilation['external_tokenizer_and_voice_data']
    assert not any(compilation[k] for k in ['bundled_model_data', 'physical_android', 'android_compiled', 'packaged_in_apk', 'model_executed'])
    runtime = load(root / 'research/moss_nano_host/runtime.json')
    assert compilation['runtime'] == runtime and runtime['version'] == '1.28.0' and runtime['api'] == 28
    assert runtime['headers_version'] == runtime['production_android_version'] == '1.28.2' and runtime['host_only']
    assert compilation['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', compilation['sha256'])
    bundle_path = root / 'catalogue/moss-nano-100m-onnx.bundle.json'; bundle = load(bundle_path)
    assert bundle['schema'] == 'lma.model-bundle/2' and not bundle['catalogue']
    assert (bundle['engine'], bundle['pipeline'], bundle['backend'], bundle['tasks']) == ('moss_nano_ort', 'moss_nano', 'cpu', ['audio'])
    assert len(bundle['components']) == 11
    for declared, pinned in zip(bundle['components'], components):
        assert all(declared[k] == v for k, v in pinned.items())
        assert declared['importPath'] == ('codec/' if pinned['role'].startswith('codec_') else 'tts/') + pinned['path']
    fields = bundle['parameters']['fields']
    assert fields['speaker']['maximum'] == 17 and fields['speaker']['limitSource'] == 'verified_external_manifest_voice_count'
    assert all(fields[k]['limitSource'] == 'application_guard' for k in ['threads', 'maxFrames', 'maxInputTokens', 'seed'])
    assert trained['schema'] == 'lma.moss-nano-trained-host/1' and trained['compilation'] == app['compilation'] == compilation
    assert trained['acquisition'] == assets
    assert trained['acquisition_receipt_sha256'] == digest((root / 'verification/development/moss-nano-assets.json').read_bytes()) if (root / 'verification/development/moss-nano-assets.json').exists() else trained['acquisition_receipt_sha256'] == digest((root / PATHS['moss-nano-assets.json']).read_bytes())
    assert trained['host_execution_checks_passed'] and trained['trained_production_worker_executed'] and trained['aba_bitwise_identical']
    assert trained['production_worker_source_unmodified'] and trained['hardlinked_user_style_workspace'] and trained['backend'] == 'cpu' and trained['failures'] == []
    assert not any(trained[k] for k in FALSE_DIRECT)
    info = trained['info']
    assert info['returncode'] == 0 and not info['protocol_errors'] and not info['timed_out']
    assert info['events'] == [dict(schema='lma.native-worker/1', engine='moss_nano_ort', pipeline='moss_nano', backend='cpu',
        modelData='user_selected_components', sourceRevision=compilation['sources']['moss-nano'], onnxruntime='1.28.0')]
    assert len(trained['jobs']) == len(trained['controls']) == 7 and len(trained['files']) == 65
    cases = CASES + [('frame-limit', 0, CASES[0][2]), ('recovery-a', 0, CASES[0][2])]
    for job, (name, speaker, prompt) in zip(trained['jobs'], cases):
        params = dict(threads=4, speaker=speaker, maxFrames=1 if name == 'frame-limit' else 375, maxInputTokens=1024, seed=1234)
        assert job['name'] == name and job['prompt'] == prompt and job['parameters'] == params
        assert job['passed'] and job['returncode'] == 0 and job['output_exists'] and job['seconds'] > 0
        assert not job['protocol_errors'] and not job['timed_out'] and not any(job['logs_truncated']) and not job['forced_host_termination']
        assert not job['android_cooperative_cancellation_tested']
        events = job['events']; execution = job['execution']; audio = job['audio']
        assert [x['details'] for x in events if x.get('event') == 'execution'] == [execution]
        complete = [x for x in events if x.get('event') == 'complete']; assert len(complete) == 1
        assert not any(x.get('event') == 'error' for x in events)
        assert execution['engine'] == 'moss_nano_ort' and execution['nativeSource'] == compilation['sources']['moss-nano']
        assert execution['effectiveParameters'] == params and execution['effectiveMaxFrames'] == params['maxFrames']
        assert execution['finishReason'] == ('length' if name == 'frame-limit' else 'stop')
        assert execution['sourceChannels'] == 2 and execution['channels'] == audio['channels'] == 1
        assert execution['sampleRate'] == audio['sample_rate'] == 48000 and audio['sample_width'] == 2 and audio['format'] == 'WAV'
        assert execution['samples'] == audio['samples'] == execution['generatedFrames'] * 3840
        assert 0 < execution['generatedFrames'] <= params['maxFrames'] and 0 < execution['inputTokens'] <= 1024 and execution['prefillRows'] > 0
        assert audio['seconds'] == audio['samples'] / 48000 and 0 < audio['seconds'] <= 60
        assert audio['bytes'] == audio['samples'] * 2 + 44
        assert all(math.isfinite(audio[k]) for k in ['seconds', 'rms', 'peak', 'clipping_fraction'])
        assert .00001 < audio['rms'] < 1 and 0 < audio['peak'] <= 1 and 0 <= audio['clipping_fraction'] <= 1 and audio['nonzero_samples'] > 10
        assert trained['files'][name + '.wav'] == {k: audio[k] for k in ['bytes', 'sha256']}
        memory = job['resources']; assert memory['observed'] and memory['samples'] > 0 and memory['interval_ms'] == 20
        assert memory['observed_peak_working_set_bytes'] > 256 * 1024**2 and memory['sampled_peak_private_bytes'] > 0
        assert not memory['gpu_memory_measured'] and not memory['physical_device_memory_measured']
    by_name = {x['name']: x for x in trained['jobs']}
    assert by_name['prompt-a']['audio'] == by_name['recovery-a']['audio']
    assert all(by_name['prompt-a']['audio']['sha256'] != by_name[k]['audio']['sha256'] for k in ['prompt-b', 'voice-change'])
    errors = ['Unsupported MOSS Nano worker request', "Selected voice exceeds this model's actual voice count",
        'Narration exceeds the selected token budget or cannot be tokenized', 'MOSS Nano parameter exceeds application bounds',
        'Component is outside its private execution workspace', None]
    for control, name, expected_error in zip(trained['controls'], ['bad-schema', 'bad-speaker', 'token-budget', 'bad-frame-limit', 'outside-workspace', 'missing-global-data'], errors):
        assert control['name'] == name and control['passed'] and control['returncode'] == 1
        error_events = [x for x in control['events'] if x.get('event') == 'error']
        assert len(error_events) == 1 and control['events'][-1] == error_events[0]
        assert not any(x.get('event') in ['execution', 'complete'] for x in control['events'])
        if expected_error is not None: assert error_events[0]['message'] == expected_error
        assert not control['timed_out'] and not control['protocol_errors'] and not any(control['logs_truncated'])
    cancel = trained['controls'][-1]
    assert cancel['name'] == 'cancel-after-frame' and cancel['passed'] and cancel['forced_host_termination'] and cancel['returncode'] != 0
    assert not cancel['timed_out'] and not cancel['protocol_errors'] and not cancel['output_exists']
    assert cancel['cancel_trigger']['stage'] == 'synthesizing' and 5 <= cancel['cancel_trigger']['step'] < 375
    assert cancel['cancel_trigger'] in cancel['events'] and cancel['cancel_to_exit_seconds'] >= 0
    assert not any(x.get('event') in ['execution', 'complete', 'error'] for x in cancel['events'])
    assert app['schema'] == 'lma.moss-nano-app-host/1' and app['production_java_native_host_executed']
    assert not any(app[k] for k in FALSE_APP)
    assert app['standalone_bundle_sha256'] == digest(bundle_path.read_bytes())
    trained_public = root / 'verification/development/moss-nano-trained.json'
    assert app['direct_trained_report_sha256'] == digest((trained_public if trained_public.exists() else root / PATHS['moss-nano-trained.json']).read_bytes())
    java = app['java']; assert java['passed'] >= 38 and java['actual_host_children'] == 3 and java['network_calls'] == 0
    assert java['imported_components'] == 11 and java['imported_bytes'] == 717414286 and java['same_wav_as_direct_production_worker'] and java['host_java_production_binding']
    assert not any(java[k] for k in ['android_application_executed', 'android_saf_tested', 'android_background_tested', 'speech_quality_accepted'])
    assert len(java['launches']) == len(java['runs']) == 3 and len(app['outputs']) == 2
    for run, name in zip(java['runs'], ['initial-a', 'cancel-after-progress', 'recovery-a']):
        assert run['name'] == name and run['seconds'] > 0
        assert any(x['stage'] == 'synthesizing' and isinstance(x.get('fraction'), (int, float)) and x['fraction'] > 0 for x in run['progress'])
        if name == 'cancel-after-progress': assert run['cancelled'] and 'output' not in run
        else:
            assert run['sha256'] == by_name['prompt-a']['audio']['sha256'] and run['bytes'] == by_name['prompt-a']['audio']['bytes']
            assert run['execution']['finishReason'] == 'stop' and run['execution']['sampleRate'] == 48000
    assert all(x['sha256'] == by_name['prompt-a']['audio']['sha256'] for x in app['outputs'])
    assert status['moss_nano_trained_production_source_host_executed'] and status['moss_nano_production_java_native_host_executed']
    assert not any(status[k] for k in ['moss_nano_complete_android_speech_tested', 'moss_nano_speech_quality_accepted', 'release_ready', 'all_selected_models_supported'])
    if with_audit:
        audit = records['moss-nano-capture-audit.json']; current(audit['input_fingerprint'])
        assert audit['input_fingerprint'] == fingerprint('tools/check_moss_nano_trained_evidence.py')
        assert audit['schema'] == 'lma.moss-nano-capture-audit/1' and audit['raw_files'] == 65 and audit['protocol_streams'] == 15
        assert audit['independent_wav_recalculations'] == 9 and audit['production_java_native_children'] == 3 and audit['imported_objects_verified'] == 11
        assert audit['trained_report_sha256'] == app['direct_trained_report_sha256']
        app_public = root / 'verification/development/moss-nano-app-host.json'
        assert audit['app_report_sha256'] == digest((app_public if app_public.exists() else root / PATHS['moss-nano-app-host.json']).read_bytes())
        assert audit['physical_android'] is False and audit['complete_release_accepted'] is False
    if with_media:
        media = load(root / 'docs/media/development/moss-nano-trained-media.json'); current(media['input_fingerprint'])
        assert media['schema'] == 'lma.moss-nano-trained-media/1' and media['kind'] == 'actual_trained_host_wav_and_waveform_slideshow'
        assert len(media['files']) == 6 and len(media['source_audio']) == 3
        assert not any(media[k] for k in ['physical_android', 'app_screen_recording', 'speech_quality_accepted', 'complete_release_accepted'])
        for name, expected in media['sources'].items(): assert digest((root / name).read_bytes()) == expected
        for name, expected in media['files'].items(): assert identity(root / 'docs/media/development' / name) == expected
        for item, case in zip(media['source_audio'], ['prompt-a', 'english', 'japanese']):
            assert item['case'] == case and item['audio'] == by_name[case]['audio']


def wav_audit(path, expected):
    assert identity(path) == {k: expected[k] for k in ['bytes', 'sha256']}
    with wave.open(str(path), 'rb') as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (1, 2, 48000, expected['samples'])
        pcm = array.array('h', stream.readframes(stream.getnframes()))
    if sys.byteorder != 'little': pcm.byteswap()
    assert len(pcm) == expected['samples']
    actual = dict(rms=math.sqrt(math.fsum(int(x)*int(x) for x in pcm)/len(pcm))/32768,
        peak=max(abs(x) for x in pcm)/32768, clipping_fraction=sum(abs(x)>=32767 for x in pcm)/len(pcm),
        nonzero_samples=sum(x!=0 for x in pcm))
    assert all(math.isclose(actual[k], expected[k], rel_tol=0, abs_tol=1e-12) for k in actual)


def raw_audit(records):
    from fetch_moss_nano_trained import path_for, verify
    trained = records['moss-nano-trained.json']; app = records['moss-nano-app-host.json']; compilation = records['moss-nano-host-build.json']
    folder = (ROOT / trained['capture_directory']).resolve(); folder.relative_to(ROOT / 'build/moss-nano-trained-tests')
    lock = verify()
    for name, expected in trained['files'].items():
        assert Path(name).name == name and identity(folder / name) == expected
    streams = [dict(name='info', **trained['info'])] + trained['jobs'] + trained['controls']
    for run in streams:
        events = [json.loads(line) for line in (folder / (run['name'] + '.stdout')).read_text(encoding='utf-8').splitlines()]
        assert events == run['events']
        if run['name'] == 'info': continue
        assert load(folder / (run['name'] + '-capture.json')) == run
        request_path = folder / (run['name'] + '.json'); request = load(request_path)
        assert identity(request_path)['sha256'] == run['request_sha256']
        assert request['parameters'] == run['parameters'] and request['input']['prompt'] == run['prompt']
        if run.get('audio'): wav_audit(folder / (run['name'] + '.wav'), run['audio'])
        else: assert not (folder / (run['name'] + '.wav')).exists()
    for item in lock['components']:
        group = 'codec' if item['role'].startswith('codec_') else 'tts'
        assert identity(folder / 'workspace' / group / item['path']) == {k: item[k] for k in ['bytes', 'sha256']}
    binary = ROOT / compilation['executable']; assert identity(binary) == {k: compilation[k] for k in ['bytes', 'sha256']}
    for name, expected in compilation['runtime']['files'].items(): assert identity(binary.parent / name) == expected
    app_folder = (ROOT / app['capture_directory']).resolve(); app_folder.relative_to(ROOT / 'build/moss-nano-app-host-tests')
    assert load(app_folder / 'data/java-results.json') == app['java']
    assert json.loads((app_folder / 'java.stdout').read_text(encoding='utf-8')) == app['java']
    assert not (app_folder / 'data/files/engine-work').exists() or not list((app_folder / 'data/files/engine-work').iterdir())
    expected_audio = trained['jobs'][0]['audio']
    for output in app['outputs']: wav_audit(ROOT / output['file'], expected_audio)
    for item in lock['components']:
        objects = list((app_folder / 'data/files/bundles/objects').glob(item['sha256'] + '*'))
        assert len(objects) == 1 and identity(objects[0]) == {k: item[k] for k in ['bytes', 'sha256']}
    audit = dict(schema='lma.moss-nano-capture-audit/1', raw_files=len(trained['files']), protocol_streams=len(streams),
        independent_wav_recalculations=9, production_java_native_children=3, imported_objects_verified=11,
        trained_report_sha256=identity(ROOT / PATHS['moss-nano-trained.json'])['sha256'],
        app_report_sha256=identity(ROOT / PATHS['moss-nano-app-host.json'])['sha256'],
        physical_android=False, complete_release_accepted=False,
        input_fingerprint=fingerprint('tools/check_moss_nano_trained_evidence.py'))
    (ROOT / PATHS['moss-nano-capture-audit.json']).write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return audit


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--raw', action='store_true'); parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    records = {name: load(ROOT / path) for name, path in PATHS.items() if name != 'moss-nano-capture-audit.json'}
    records['moss-nano-host-build.json'] = records['moss-nano-trained.json']['compilation']
    status = dict(moss_nano_trained_production_source_host_executed=True, moss_nano_production_java_native_host_executed=True,
        moss_nano_complete_android_speech_tested=False, moss_nano_speech_quality_accepted=False, release_ready=False, all_selected_models_supported=False)
    check(records, status, digest, ROOT, with_audit=False, with_media=False)
    if args.raw: text = raw_audit(records); print(json.dumps(text, indent=2))
    if args.self_test:
        mutations = [('moss-nano-trained.json', 'physical_android', True), ('moss-nano-trained.json', 'speech_quality_accepted', True),
            ('moss-nano-trained.json', 'complete_target09_accepted', True), ('moss-nano-trained.json', 'complete_release_accepted', True),
            ('moss-nano-app-host.json', 'android_saf_tested', True), ('moss-nano-app-host.json', 'android_background_accepted', True),
            ('moss-nano-app-host.json', 'speech_quality_accepted', True), ('moss-nano-app-host.json', 'complete_release_accepted', True)]
        for filename, key, value in mutations:
            changed = copy.deepcopy(records); changed[filename][key] = value
            try: check(changed, status, digest, ROOT, with_audit=False, with_media=False)
            except AssertionError: continue
            raise AssertionError('Accepted false scope promotion: ' + filename + ':' + key)
        receipt = dict(rejected_false_scope_promotions=len(mutations), input_fingerprint=fingerprint('tools/check_moss_nano_trained_evidence.py'))
        (ROOT / 'build/moss-nano-trained-tests/adversarial-audit.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        print('Rejected eight false Android/quality/target/Release claims')
    print('Nano trained/Java host evidence scopes and identities passed')


if __name__ == '__main__': main()
