"""Allowlisted physical SDK/benchmark evidence, separate from program-gate counts.

No credentials, phone serials, private gateway state, user history or device paths
are exported. Candidate APK attempts retain their original APK identity.
"""
import argparse
import hashlib
import json
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inputs():
    return fingerprint('app/src/main/java', 'app/src/main/assets/app.js', 'integrations/sub2api', 'tools/physical_api_evidence.py', 'tools/device_sdk_integration.py',
                       'tools/device_api_benchmark.py', 'tools/device_model_probe.py')


def check(directory):
    path = Path(directory)/'physical-api.json'
    if not path.exists():
        return dict(physical_api_integration_tested=False, physical_api_checks=0,
                    final_video_over_five_seconds=False)
    data = read(path)
    build = read(ROOT/'dist/build-info.json')
    assert data['schema'] == 'lma.physical-multimodal-api/1'
    assert data['version'] == version() and data['apk_sha256'] == build['sha256']
    current(data['input_fingerprint'])
    assert data['input_fingerprint'] == inputs()
    sdk = data['sdk']
    current(sdk['input_fingerprint'])
    assert sdk['status'] == 'passed' and sdk['passed'] == len(sdk['checks']) >= 28
    assert all(item['passed'] for item in sdk['checks'])
    assert not data['production_sub2api_deployment_tested']
    assert not any(data[k] for k in ('quality_accepted', 'background_endurance_tested',
                                    'new_model_downloads', 'remote_inference', 'virtualization_used'))
    attempts = [b for group in data['benchmarks'] if group['apk_sha256'] == build['sha256']
                for b in group['attempts']]
    videos = [b for b in attempts if b['operation'] == 'video.generate' and b['outcome'] == 'succeeded']
    assert videos and all(any(o['metadata']['durationMs'] > 5000 for o in b['outputs']) for b in videos)
    for b in attempts:
        assert b['outcome'] in ('succeeded', 'failed', 'cancelled', 'interrupted', 'preflight_rejected', 'api_error', 'test_error')
        assert b['generation_budget_seconds'] == 0
    media_path = ROOT/'docs/media/benchmarks'/('v'+version())/'manifest.json'
    if media_path.exists():
        media = read(media_path)
        assert media['apk_sha256'] == build['sha256'] and media['same_android_phone']
        assert not media['quality_accepted'] and media['reviewed_owned_inputs_only']
        observed = {o['sha256'] for b in attempts for o in b.get('outputs', [])} | {o['sha256'] for o in sdk['outputs']}
        original = next(f for f in media['files'] if f['file'] == 'wan-cpu-6s.mp4')
        assert original['sha256'] == media['original_video_sha256'] and original['sha256'] in observed
        assert media['video']['duration_seconds'] > 5 and not any(media['video'][k] for k in ('interpolated', 'repeated_clip', 'retimed'))
        for item in media['files']:
            f = media_path.parent/item['file']
            assert f.parent == media_path.parent and f.stat().st_size == item['bytes']
            assert digest(f) == item['sha256']
    successes = sum(b['outcome'] == 'succeeded' for b in attempts) + len(sdk['outputs'])
    return dict(physical_api_integration_tested=True, physical_api_checks=sdk['passed'],
                final_video_over_five_seconds=True, phone_inference_tested=True,
                model_inference_tested=True, authorized_phone_model_attempts=len(attempts)+len(sdk['outputs']),
                authorized_phone_model_successes=successes, complete_trained_model_runs=successes)


def export(sdk_path, benchmark_paths):
    sdk_raw = read(sdk_path)
    apk = read(ROOT/'dist/build-info.json')['sha256']
    assert sdk_raw['apk_sha256'] == apk and sdk_raw['version'] == version()
    current(sdk_raw['input_fingerprint'])
    sdk_keys = ('input_fingerprint', 'status', 'passed', 'checks', 'device', 'openai_sdk_version', 'outputs',
                'catalogue_latency_ms', 'screen_off_api_seconds', 'gateway_implementation',
                'production_sub2api_deployment_tested', 'gateway_authentication')
    sdk = {k: sdk_raw[k] for k in sdk_keys}
    groups = []
    for report in benchmark_paths:
        raw = read(report)
        assert raw['physical_device'] and raw['inference_location'] == 'same_android_phone'
        assert raw['version'] == version() and not raw['model_downloads'] and not raw['virtualization_used']
        attempts = []
        for b in raw['benchmarks']:
            allowed = ('model', 'operation', 'outcome', 'elapsed_seconds', 'error', 'effective_parameters',
                       'outputs', 'stages', 'initial_http_status', 'replay_http_status',
                       'screen_off_during_inference', 'issues', 'preflight_can_enqueue', 'worker_diagnostics')
            attempt = {k:b[k] for k in allowed if k in b}
            attempt['quality_accepted'] = False
            attempt['generation_budget_seconds'] = 0 if raw['apk_sha256'] == apk else (
                1200 if b.get('bounded_timeout') else None)
            attempts.append(attempt)
        groups.append(dict(apk_sha256=raw['apk_sha256'], final_apk=raw['apk_sha256']==apk,
            device=raw['device'], source_report_sha256=digest(report), attempts=attempts,
            checks=raw['checks'], catalogue_latency_ms=raw['catalogue_latency_ms'],
            screen_off_service=raw.get('screen_off_service'), baseline_resources=raw.get('baseline_resources'),
            resource_samples=raw.get('resource_samples', []), resource_measurement_scope=raw.get('resource_measurement_scope'),
            missing_generation_operations=raw.get('missing_generation_operations', []),
            history_preserved=raw.get('history_preserved', False)))
    data = dict(schema='lma.physical-multimodal-api/1', version=version(), apk_sha256=apk,
        input_fingerprint=inputs(), sdk=sdk, benchmarks=groups, same_android_phone=True,
        quality_accepted=False, background_endurance_tested=False, new_model_downloads=0,
        remote_inference=False, virtualization_used=False, production_sub2api_deployment_tested=False,
        evidence_scope='Actual final-APK OpenAI SDK and native gateway forwarding; separately identified candidate attempts. '
                       'No production database/billing, all-model quality or endurance acceptance.')
    output = ROOT/'verification/releases'/('v'+version());output.mkdir(parents=True, exist_ok=True)
    (output/'physical-api.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return check(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', required=True)
    parser.add_argument('--benchmark', action='append', required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.sdk, args.benchmark), ensure_ascii=False))
