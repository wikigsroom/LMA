"""Publish explicitly authorized, bounded phone probes separately from program gates.

Only reports made by device_model_probe with its fixed owned fixtures are accepted.
No user task history, input paths, credentials, serials or model contents are exported.
"""
import argparse
import hashlib
import json
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def inputs():
    return fingerprint('tools/physical_model_evidence.py', 'tools/device_model_probe.py')


def check_media(data):
    base = ROOT/'docs/media/models'/('v'+version())
    if not (base/'manifest.json').exists(): return False
    media = read(base/'manifest.json')
    assert media['schema'] == 'lma.physical-model-media/1' and media['version'] == version()
    assert media['apk_sha256'] == read(ROOT/'dist/build-info.json')['sha256']
    assert media['same_android_phone'] and media['model_inference'] and media['owned_benign_input']
    assert not any(media[k] for k in ('desktop_fixture', 'quality_accepted', 'remote_inference'))
    comparisons = media.get('video_comparisons', [])
    assert len(comparisons) <= 1
    assert all(c['file'] == 'wan-cpu-128-four-steps.mp4' for c in comparisons)
    assert {f['file'] for f in media['files']} == {'wan-cpu-128.'+s for s in ('mp4', 'gif', 'png')} | {c['file'] for c in comparisons}
    for item in media['files']:
        path = base/item['file']
        assert path.parent == base and path.stat().st_size == item['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
    video = next(f for f in media['files'] if f['file'] == 'wan-cpu-128.mp4')
    assert video['sha256'] == media['original_video_sha256'] and video['bytes'] == media['original_video_bytes']
    matches = [p for p in data['attempts'] if p['apk_sha256'] == media['apk_sha256']
               and p['bundle_id'] == media['bundle_id'] and p['state'] == 'succeeded'
               and p['parameters'] == media['parameters'] and p['device'] == media['device']
               and any(o['sha256'] == video['sha256'] and o['bytes'] == video['bytes']
                       and o['metadata'] == media['video'] for o in p['outputs'])]
    assert len(matches) == 1, 'Media must match an exact successful phone probe and its APK'
    for comparison in comparisons:
        assert not comparison['quality_accepted'] and comparison['apk_sha256'] == media['apk_sha256']
        file = next(f for f in media['files'] if f['file'] == comparison['file'])
        assert file['bytes'] == comparison['bytes'] and file['sha256'] == comparison['sha256']
        assert sum(p['state'] == 'succeeded' and p['apk_sha256'] == comparison['apk_sha256']
                   and p['bundle_id'] == comparison['bundle_id'] and p['parameters'] == comparison['parameters']
                   and p['device'] == comparison['device'] and any(o['sha256'] == file['sha256']
                   and o['bytes'] == file['bytes'] and o['metadata'] == comparison['video']
                   for o in p['outputs']) for p in data['attempts']) == 1
    return True


def check(directory):
    path = Path(directory)/'physical-models.json'
    if not path.exists():
        return dict(phone_inference_tested=False, model_inference_tested=False,
                    authorized_phone_model_attempts=0, authorized_phone_model_successes=0,
                    complete_trained_model_runs=0)
    data = read(path)
    assert data['schema'] == 'lma.authorized-physical-model-probes/1'
    assert data['version'] == version() and data['user_authorized_partial_model_validation']
    current(data['input_fingerprint'])
    assert data['input_fingerprint'] == inputs()
    assert not any(data[key] for key in ('quality_accepted', 'all_models_tested',
        'background_endurance_tested', 'new_model_downloads', 'model_weights_copied', 'remote_inference'))
    assert data['attempts']
    successes = 0
    for probe in data['attempts']:
        assert probe['state'] in ('succeeded', 'failed', 'cancelled', 'interrupted')
        assert 15 <= probe['budget_seconds'] <= 600 and probe['same_android_phone']
        assert len(probe['apk_sha256']) == 64
        assert set(probe['device']) == {'model', 'manufacturer', 'android', 'api'}
        assert probe['bundle_id'] in ('trellis2_pbr512_cpu_v1', 'pixal3d_geometry512_cpu_v1',
                                     'wan21_13b_q4_vulkan_catalogue_v1')
        if probe['state'] == 'succeeded':
            assert probe['outputs'] and probe['engine_execution']['workerCompleteEvent']
            assert probe['engine_execution']['workerExitCode'] == 0
            for output in probe['outputs']:
                assert output['bytes'] > 0 and len(output['sha256']) == 64
            successes += 1
    assert data['successful_generations'] == successes
    if 'owned_test_cleanup' in data:
        cleanup = data['owned_test_cleanup']
        assert cleanup['removed_owned_terminal_jobs'] >= 0 and cleanup['removed_owned_inputs'] >= 0
        assert cleanup['original_successes_preserved'] == 2
        assert cleanup['original_artifacts_preserved'] == cleanup['original_installed_models_preserved'] == 5
        assert cleanup['original_parameter_values_preserved']
    check_media(data)
    return dict(phone_inference_tested=True, model_inference_tested=True,
                authorized_phone_model_attempts=len(data['attempts']),
                authorized_phone_model_successes=successes, complete_trained_model_runs=successes)


def export(reports):
    attempts = []
    for report in reports:
        path = Path(report).resolve()
        assert path.is_relative_to((ROOT/'build/device-model-probes').resolve())
        data = read(path)
        assert data['physical_device'] and data['existing_trained_model']
        assert data['user_authorized_partial_model_validation']
        assert not data['new_model_downloads'] and not data['model_weights_copied']
        job = data['last_job']
        expected = ('Generate a 3D asset from the selected local image.'
                    if job['request']['type'] == 'mesh.generate'
                    else 'An orange cube rotating slowly on a plain white background.')
        assert job['request']['input']['prompt'] == expected, 'Only the owned probe fixtures may be published'
        execution = job.get('engineExecution', {})
        allowed = ('pipeline', 'selectedBackend', 'workerEngine', 'workerFile', 'workerSha256',
                   'workerBytes', 'diffusionBackend', 'runtimeBackend', 'textBackend', 'vaeBackend',
                   'vulkanGraphObserved', 'workerExitCode', 'workerCompleteEvent', 'workerDiagnosticCode',
                   'backend', 'runtimeMeasurements')
        outputs = []
        for output in data.get('verified_artifacts', []):
            content = path.parent/output['local_file']
            assert content.parent == path.parent and content.stat().st_size == output['bytes']
            assert hashlib.sha256(content.read_bytes()).hexdigest() == output['sha256']
            metadata = output['metadata']['metadata']
            outputs.append(dict(bytes=output['bytes'], sha256=output['sha256'], metadata=metadata))
        attempts.append(dict(bundle_id=data['bundle_id'], device=data['device'],
            apk_sha256=data['apk_sha256'], state=job['state'], outcome=data['outcome'],
            budget_seconds=data['budget_seconds'], elapsed_seconds=data.get('elapsed_seconds'),
            same_android_phone=True, parameters=job['request']['parameters'],
            stages=data['stages'], engine_execution={key:execution[key] for key in allowed if key in execution},
            outputs=outputs, resource_observations=job.get('runtimeResources', {})))
    directory = ROOT/'verification/releases'/('v'+version())
    directory.mkdir(parents=True, exist_ok=True)
    data = dict(schema='lma.authorized-physical-model-probes/1', version=version(),
        user_authorized_partial_model_validation=True,
        authority='User: 允许你做部分真机和模型验证。自行决定。',
        scope='Selected installed models with owned benign fixtures and a time budget; separate from program gate counts',
        input_fingerprint=inputs(), attempts=attempts,
        successful_generations=sum(probe['state']=='succeeded' for probe in attempts),
        quality_accepted=False, all_models_tested=False, background_endurance_tested=False,
        new_model_downloads=False, model_weights_copied=False, remote_inference=False)
    cleanup_path = ROOT/'build/device-task-audit/v0311-cleanup-private.json'
    if version() == '0.3.11' and cleanup_path.exists():
        cleanup = read(cleanup_path)
        data['owned_test_cleanup'] = {
            'removed_owned_terminal_jobs': len(cleanup['removed_owned_terminal_jobs']),
            'removed_owned_inputs': len(cleanup['removed_owned_inputs']),
            **{k: cleanup[k] for k in ('original_successes_preserved', 'original_artifacts_preserved',
                'original_installed_models_preserved', 'original_parameter_values_preserved')}}
    (directory/'physical-models.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return check(directory)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='append', required=True)
    print(json.dumps(export(parser.parse_args().report), ensure_ascii=False))
