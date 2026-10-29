"""Audit public old-LTX pipeline evidence without promoting host to phone gates."""
import json
import re
from evidence import current


def check(records, status, root, digest):
    tensors = records['ltx098-tensors.json']
    assert tensors['checks'] >= 157 and tensors['native_children'] >= 43 and len(tensors['guards']) >= 31
    assert tensors['original_patchifier_compared'] and tensors['original_diffusers_normalization_compared']
    assert tensors['rng_matches_frozen_definition'] and not tensors['matches_pytorch_seed']
    assert not any(tensors[x] for x in ('model_inference', 'model_data_embedded', 'engine_registered', 'packaged_in_apk', 'physical_android'))
    assert len(tensors['metrics']) == 8
    for metric in tensors['metrics']:
        if metric['kind'] == 'noise': assert metric['max_abs'] <= 1e-6
        else: assert metric['kind'] == 'frames' and metric['rgb_max_error'] == 0
    host = records['ltx098-tensors-host.json']; arm = records['ltx098-tensors-arm64.json']
    assert tensors['executable_sha256'] == host['executable_sha256']
    assert arm['android_arm64_compiled'] and arm['android_platform'] == 28
    assert arm['elf']['machine'] == 'aarch64' and arm['elf']['16k_elf_aligned'] and arm['elf']['android_api_notes'] == [28]
    assert arm['elf']['interpreter'] == '/system/bin/linker64' and set(arm['elf']['needed']) <= {'libm.so', 'libdl.so', 'libc.so'}
    for receipt in (host, arm):
        assert not any(receipt[x] for x in ('model_inference', 'model_data_embedded', 'engine_registered', 'packaged_in_apk', 'physical_android', 'virtualization_used'))
    pipeline = records['ltx098-pipeline.json']
    lock = json.loads((root / 'third_party/ltx098-pipeline-source-lock.json').read_text(encoding='utf-8'))
    assert pipeline['checks'] >= 120 and len(pipeline['guards']) >= 18
    assert pipeline['gates'] == lock['host_gates'] and pipeline['actual_trained_jobs'] == 3 and pipeline['distinct_prompts'] == 2
    assert pipeline['native_children'] == 18 and pipeline['host_media_children'] == 6
    assert pipeline['geometry'] == dict(width=256, height=256, frames=33, fps=24)
    assert pipeline['real_prompt_to_video_host_executed'] and pipeline['original_forward_comparison_executed'] and pipeline['host_mp4_generated']
    assert pipeline['real_prompt_to_video_host_tested'] == pipeline['full_chain_original_forward_parity'] == pipeline['numerical_acceptance_passed']
    assert pipeline['checks'] == pipeline['passed_checks'] + pipeline['failed_checks'] and pipeline['failed_checks'] == len(pipeline['failures'])
    assert pipeline['reused_native_jobs'] + pipeline['native_jobs_executed_this_invocation'] == 3
    assert pipeline['single_scale'] and pipeline['aba_bitwise_neural_reproducibility']
    assert pipeline['prompt_change_rgb_mean_absolute_difference'] > 3
    for key in ('video_quality_accepted', 'original_unquantized_t5_compared', 'official_pixart_weight_identity_compared',
                'official_multiscale_default_reproduced', 'matches_pytorch_seed', 'physical_android', 'engine_registered',
                'packaged_in_apk', 'remote_inference', 'virtualization_used'): assert not pipeline[key]
    assert len(pipeline['metrics']) == 13
    failures = []
    for metric in pipeline['metrics']:
        if metric['kind'] == 'full_chain':
            accepted = metric['max_abs'] <= lock['host_gates']['full_chain_max_absolute_error'] and metric['relative_rmse'] <= lock['host_gates']['full_chain_max_relative_rmse'] and metric['cosine'] >= lock['host_gates']['full_chain_min_cosine']
            if not accepted: failures.append('case-' + str(metric['case']) + ': frozen original-forward full-chain gate failed: ' + metric['file'])
        elif metric['kind'] == 'full_chain_rgb':
            accepted = metric['max_error'] <= lock['host_gates']['rgb_max_byte_error'] and metric['mean_error'] <= lock['host_gates']['rgb_mean_byte_error']
            if not accepted: failures.append('case-' + str(metric['case']) + ': frozen full-chain RGB gate failed')
        else:
            assert metric['kind'] == 'structural_rgb' and metric['minimum_frame_std'] > 3 and metric['mean_adjacent_frame_mad'] > .1
    assert failures == pipeline['failures'] and pipeline['numerical_acceptance_passed'] is (not failures)
    oracle = pipeline['original_oracle']; current(oracle['input_fingerprint'])
    assert oracle['trained_t5_tensors'] == 219 and oracle['trained_dit_tensors'] == 715 and oracle['trained_decoder_tensors'] == 132
    assert oracle['quantized_t5_dequantized'] and oracle['converted_dit_f16_equivalent'] and oracle['explicit_noise_shared_as_inputs']
    assert not any(oracle[x] for x in ('native_inference_called', 'physical_android', 'video_quality_accepted', 'original_unquantized_t5_compared', 'official_multiscale_default_reproduced', 'official_pixart_weight_identity_compared', 'matches_pytorch_seed'))
    assert len(oracle['cases']) == 2 and sum(len(x['files']) for x in oracle['cases']) == pipeline['original_oracle_files'] == 26
    for reference in oracle['cases']:
        assert len(reference['sampling_steps']) == 8 and all(x['finite'] for x in reference['sampling_steps'])
        for name, item in reference['files'].items():
            assert '/' not in name and '\\' not in name and item['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', item['sha256'])
    for job in pipeline['jobs']:
        current(job['input_fingerprint'])
        assert job['shape'] == pipeline['geometry'] and job['assets'] == pipeline['jobs'][0]['assets'] and len(job['assets']) == 21
        assert job['actual_prompt_conditioning'] and job['full_trained_host_text_to_frames'] and job['host_mp4_generated'] and not job['prompt_truncated']
        assert [x['stage'] for x in job['stages']] == ['noise', 'text', 'sampling', 'unpatchify', 'vae', 'frames']
        text = job['stages'][1]['native']; sample = job['stages'][2]['native']; vae = job['stages'][4]['native']
        assert text['layers'] == 24 and not text['fixture'] and text['model_loads'] == text['model_unloads'] == 1
        assert sample['model_executed'] and not sample['fixture'] and sample['layers'] == 28 and sample['steps'] == 8 and sample['parameters'] == 1923385472 and sample['backend'] == 'vulkan'
        assert vae['session_loads'] == vae['session_unloads'] == vae['graph_runs'] == 9 and vae['max_live_sessions'] == 1
        assert job['media']['backend'] == 'host_ffmpeg_libx264_not_android_mediacodec'
        for stage in job['stages']:
            resource = stage['resources']
            assert resource['observed'] and resource['samples'] > 0 and resource['observed_peak_working_set_bytes'] > 0 and not resource['gpu_memory_measured']
        for key in ('official_pixart_weight_identity_compared', 'official_multiscale_default_reproduced', 'video_quality_accepted', 'engine_registered', 'packaged_in_apk', 'physical_android', 'remote_inference', 'virtualization_used'): assert not job[key]
    diagnostic = pipeline['conditioning_diagnostic']
    if diagnostic:
        assert diagnostic['case'] == 0 and diagnostic['same_reference_caption'] and diagnostic['captured_native_children'] == 1 and diagnostic['capture_reused']
        assert len(diagnostic['metrics']) == 8 and len(diagnostic['files']) == 12
        final = diagnostic['metrics'][-1]
        assert diagnostic['final_within_latent_gates'] == (final['max_abs'] <= lock['host_gates']['full_chain_max_absolute_error'] and final['relative_rmse'] <= lock['host_gates']['full_chain_max_relative_rmse'])
        assert not diagnostic['physical_android'] and not diagnostic['full_pipeline_acceptance']
        assert diagnostic['resources']['observed'] and diagnostic['resources']['samples'] > 0 and not diagnostic['resources']['gpu_memory_measured']
        for artifact in diagnostic['files'].values(): assert artifact['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', artifact['sha256'])
    assert status['ltx098_complete_prompt_to_video_host_executed'] and status['ltx098_tensor_primitives_host_tested'] and status['ltx098_tensor_primitives_android_compiled']
    assert status['ltx098_complete_prompt_to_video_host_tested'] == status['ltx098_full_chain_numeric_accepted'] == pipeline['numerical_acceptance_passed']
    assert not any(status[x] for x in ('ltx098_trained_video_tested', 'ltx098_complete_android_video_tested', 'ltx098_video_quality_accepted', 'ltx098_app_engine_registered'))
    media_dir = root / 'docs/media/development'
    media = json.loads((media_dir / 'ltx098-host-media.json').read_text(encoding='utf-8')); current(media['input_fingerprint'])
    assert media['kind'] == 'actual_trained_host_output' and media['source_evidence'] == 'verification/development/ltx098-pipeline.json'
    assert digest((root / media['source_evidence']).read_bytes()) == media['source_evidence_sha256']
    assert media['gif_frame_duration_ms'] == 40 and media['gif_duration_seconds'] == 1.32 and media['mp4_fps'] == 24 and media['mp4_duration_seconds'] == 1.375
    assert not any(media[x] for x in ('physical_android', 'app_screen_recording', 'video_quality_accepted', 'official_multiscale_default_reproduced', 'official_pixart_weight_identity_compared'))
    assert media['numerical_acceptance_passed'] == pipeline['numerical_acceptance_passed']
    assert len(media['raw_source_frames']) == 2 and len(media['files']) == 3
    for name, asset in media['files'].items():
        path = media_dir / name
        assert path.parent == media_dir and path.stat().st_size == asset['bytes'] and digest(path.read_bytes()) == asset['sha256']
