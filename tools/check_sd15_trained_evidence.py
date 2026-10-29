"""Audit actual SD1.5 host execution without promoting Android acceptance."""
import json
import math
import re

from evidence import current


def check(records, status, digest, root):
    from build_sd_host import inputs as build_inputs
    from fetch_sd15_trained import bundle, inputs as asset_inputs
    from test_sd15_trained import inputs as test_inputs, PROMPTS
    assets = records['sd15-assets.json']; compilation = records['sd15-host-build.json']; trained = records['sd15-trained.json']
    for record in [assets, compilation, trained]: current(record['input_fingerprint'])
    assert assets['input_fingerprint'] == asset_inputs() and compilation['input_fingerprint'] == build_inputs()
    assert trained['input_fingerprint'] == test_inputs()
    assert assets['schema'] == 'lma.sd15-trained-assets/1' and assets['bundle_id'] == bundle()['id']
    assert assets['developer_assets_only'] and assets['explicit_download']
    assert assets['download_origin'] in ['https://huggingface.co', 'https://hf-mirror.com']
    assert not assets['model_executed'] and not assets['app_assets_modified']
    assert [item['role'] for item in assets['components']] == ['model', 'clip_merges']
    assert [{k: v for k, v in item.items() if k != 'local_path'} for item in assets['components']] == bundle()['components']
    assert sum(item['bytes'] for item in assets['components']) == 1567293035
    assert compilation['schema'] == 'lma.sd-host-build/1' and compilation['backend'] == 'cpu'
    assert compilation['source_revision'] == 'be486498eadc29dc3cd234d944c2180ed42b1415'
    assert compilation['ggml_revision'] == 'a5915eb0e47adef21c3f25b889a008925ea838c2'
    assert compilation['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', compilation['sha256'])
    assert compilation['production_worker_source_unmodified'] and compilation['production_vocabulary_source_unmodified']
    assert compilation['windows_parent_guard'] and compilation['external_vocabulary']
    assert not any(compilation[key] for key in ['bundled_model_data', 'android_compiled', 'physical_android', 'packaged_in_apk', 'model_executed'])
    assert trained['schema'] == 'lma.sd15-trained-host/1' and trained['compilation'] == compilation
    assert trained['bundle'] == bundle() and trained['acquisition'] == assets
    assert trained['acquisition_receipt_sha256'] == digest((root / 'verification/development/sd15-assets.json').read_bytes())
    assert trained['trained_model_executed'] and trained['host_execution_checks_passed'] and trained['failures'] == []
    assert trained['production_worker_source_unmodified'] and trained['production_vocabulary_source_unmodified']
    assert trained['external_vocabulary'] and trained['backend'] == 'cpu' and trained['all_assets_already_present']
    assert not any(trained[key] for key in ['asset_download_attempted', 'fixture', 'android_compiled', 'physical_android',
        'app_executed', 'semantic_quality_accepted', 'device_resource_fit_accepted', 'android_background_accepted', 'complete_release_accepted'])
    expected_info = dict(schema='lma.engine/1', engine='sd_cpp', revision=compilation['source_revision'],
                         backend='cpu', bundled_model_data=False, generation_tested=False)
    assert trained['info']['events'] == [expected_info] and trained['info']['returncode'] == 0
    assert not trained['info']['protocol_errors'] and not trained['info']['timed_out']
    assert len(trained['jobs']) == 3 and len(trained['controls']) == 4
    parameters = dict(width=512, height=512, steps=20, cfg=7., sampler='euler', scheduler='discrete',
                      seed=42, threads=4, vaeTiling=True, flowShift=0)
    for job, case, name in zip(trained['jobs'], [0, 1, 0], ['prompt-a', 'prompt-b', 'recovery-a']):
        assert job['case'] == case and job['name'] == name and job['prompt'] == PROMPTS[case] and job['parameters'] == parameters
        assert job['passed'] and job['returncode'] == 0 and job['output_exists']
        assert not job['protocol_errors'] and not any(job['logs_truncated']) and not job['cancelled'] and not job['timed_out']
        assert job['sampling_steps_observed'] == list(range(21))
        assert job['progress_phase_consistent'] and job['loading_progress_events'] > 0 and job['generation_progress_events'] > 21
        phase = None
        for event in job['events']:
            if event.get('event') == 'stage': phase = event['stage']
            elif event.get('event') == 'progress': assert phase in ['loading', 'generating'] and event['stage'] == phase
        assert [event['stage'] for event in job['events'] if event.get('event') == 'stage'] == ['loading', 'generating']
        complete = [event for event in job['events'] if event.get('event') == 'complete']
        assert len(complete) == 1 and complete[0]['format'] == 'png' and complete[0]['width'] == complete[0]['height'] == 512
        image = job['image']; assert image['width'] == image['height'] == 512 and image['mode'] == 'RGB' and image['format'] == 'PNG'
        assert image['bytes'] > 10000 and re.fullmatch('[a-f0-9]{64}', image['sha256'])
        assert trained['files'][name + '.png'] == {key: image[key] for key in ['bytes', 'sha256']}
        assert all(math.isfinite(value) and 1 < value <= 128 for value in image['channel_stddev'])
        assert math.isfinite(image['entropy']) and image['entropy'] > 0 and job['seconds'] > 0
        resources = job['resources']; assert resources['observed'] and resources['samples'] > 0
        assert resources['observed_peak_working_set_bytes'] > 256 * 1024 * 1024 and resources['sampled_peak_private_bytes'] > 0
        assert not resources['gpu_memory_measured'] and not resources['physical_device_memory_measured']
    assert trained['aba_bitwise_identical'] and trained['distinct_prompt_images']
    assert trained['jobs'][0]['image']['sha256'] == trained['jobs'][2]['image']['sha256']
    assert trained['jobs'][0]['image']['sha256'] != trained['jobs'][1]['image']['sha256']
    expected_errors = ['Unsupported engine request version', 'Invalid prompt or output', 'Native parameter out of bounds: threads']
    for control, name, error in zip(trained['controls'][:3], ['bad-schema', 'empty-prompt', 'bad-threads'], expected_errors):
        assert control['name'] == name and control['passed'] and control['returncode'] == 1
        assert control['events'] == [dict(event='error', message=error)]
    cancel = trained['controls'][3]
    assert cancel['name'] == 'cancel-after-step' and cancel['passed'] and cancel['cancelled'] and cancel['returncode'] != 0
    assert cancel['progress_phase_consistent'] and cancel['loading_progress_events'] > 0
    assert not cancel['timed_out'] and not cancel['protocol_errors'] and not cancel['output_exists']
    assert cancel['cancel_trigger']['stage'] == 'generating' and cancel['cancel_trigger']['steps'] == 20 and 1 <= cancel['cancel_trigger']['step'] < 20
    assert cancel['cancel_to_exit_seconds'] >= 0
    assert not any(event.get('event') == 'complete' for event in cancel['events'])
    assert all(identity['bytes'] >= 0 and re.fullmatch('[a-f0-9]{64}', identity['sha256']) for identity in trained['files'].values())
    assert status['sd15_trained_production_source_host_executed'] and status['sd15_trained_host_execution_checks_passed']
    assert not status['sd15_complete_android_image_tested'] and not status['release_ready'] and not status['all_selected_models_supported']
    for filename, schema, expected_count in [('ltx098-modulation-media.json', 'lma.ltx098-modulation-media/1', 1),
                                              ('sd15-trained-media.json', 'lma.sd15-trained-media/1', 3)]:
        media = json.loads((root / 'docs/media/development' / filename).read_text(encoding='utf-8'))
        current(media['input_fingerprint']); assert media['schema'] == schema and len(media['files']) == expected_count
        assert not media['physical_android'] and not media['app_screen_recording'] and not media['complete_release_accepted']
        for name, expected in media['sources'].items(): assert digest((root / name).read_bytes()) == expected
        for name, identity in media['files'].items():
            data = (root / 'docs/media/development' / name).read_bytes()
            assert len(data) == identity['bytes'] and digest(data) == identity['sha256']
        if filename.startswith('ltx'):
            assert not media['candidate_numeric_gates_passed'] and not media['new_video_generated'] and not media['video_quality_accepted']
        else:
            assert media['kind'] == 'actual_trained_host_png_outputs' and media['source_images'] == [job['image'] for job in trained['jobs']]
            assert not media['semantic_quality_accepted'] and not media['android_background_accepted']
