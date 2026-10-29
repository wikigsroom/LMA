"""Validate isolated trained precision evidence separately from full-chain gates."""
import math
import re


def check(records, status, digest, root):
    pipeline = records['ltx098-pipeline.json']
    for name, linear in [('ltx098-text-precision-attention.json', False),
                         ('ltx098-text-precision-linear.json', True)]:
        candidate = records[name]
        assert candidate['schema'] == 'lma.ltx098-text-precision/1'
        expected = 'independent_ggml_f32_with_f64_attention' + ('_and_linear' if linear else '')
        assert candidate['implementation'] == expected and candidate['linear_f64'] is linear
        assert candidate['actual_trained_jobs'] == candidate['native_children'] == 3
        assert candidate['distinct_prompts'] == 2 and candidate['aba_bitwise_identical']
        assert candidate['trained_t5_tensors'] == 219 and candidate['trained_t5_parameters'] == 4762310656
        assert re.fullmatch('[a-f0-9]{64}', candidate['binary_sha256'])
        assert len(candidate['linked_archives']) == 4
        assert all(re.fullmatch('[a-f0-9]{64}', value) for value in candidate['linked_archives'].values())
        assert len(candidate['jobs']) == 3
        for job, case in zip(candidate['jobs'], [0, 1, 0]):
            native = job['native']; original = pipeline['original_oracle']['cases'][case]
            assert job['case'] == case and job['prompt'] == pipeline['jobs'][case]['request']['prompt']
            assert job['tokens'] == original['tokens'] and job['caption_bytes'] == len(original['tokens']) * 4096 * 4
            assert job['reference_sha256'] == original['files']['caption.f32']['sha256']
            assert re.fullmatch('[a-f0-9]{64}', job['caption_sha256'])
            assert native['encoder_implementation'] == expected and native['model_inference']
            assert native['layers'] == 24 and native['width'] == 4096 and not native['fixture']
            assert native['model_loads'] == native['model_unloads'] == native['encode_calls'] == 1
            assert len(native['items']) == 1
            item = native['items'][0]
            assert item['tokens'] == original['tokens'] and item['mask'] == [1] * len(original['tokens'])
            assert item['shape'] == [1, len(original['tokens']), 4096] and not item['truncated']
            assert item['bytes'] == job['caption_bytes'] and item['offset_bytes'] == 0
            assert job['seconds'] > 0 and math.isfinite(job['seconds'])
            assert all(math.isfinite(value) and value >= 0 for value in job['metric'].values())
            resource = job['resources']
            assert resource['observed'] and resource['samples'] > 0 and resource['observed_peak_working_set_bytes'] > 0
            assert not resource['gpu_memory_measured']
        assert candidate['jobs'][0]['caption_sha256'] == candidate['jobs'][2]['caption_sha256']
        assert not any(candidate[key] for key in ['production_source_changed', 'acceptance_gates_changed',
                                                 'complete_pipeline_numeric_accepted', 'physical_android',
                                                 'packaged_in_apk', 'engine_registered'])
    assert status['ltx098_t5_precision_candidates_host_executed']
    assert not status['ltx098_t5_roundoff_repair_accepted']
    for variant in ['attention', 'linear']:
        sample = records['ltx098-precision-sampling-' + variant + '.json']
        candidate_name = 'ltx098-text-precision-' + variant + '.json'
        candidate = records[candidate_name]
        assert sample['schema'] == 'lma.ltx098-precision-sampling/1' and sample['variant'] == variant and sample['case'] == 0
        assert sample['candidate_sha256'] == digest((root / 'verification/development' / candidate_name).read_bytes())
        assert sample['candidate_caption_sha256'] == candidate['jobs'][0]['caption_sha256']
        assert sample['gates'] == pipeline['gates'] and sample['original_case'] == pipeline['original_oracle']['cases'][0]
        assert sample['original_trajectory_files_verified'] == len(sample['metrics']) == 8
        assert [item['step'] for item in sample['metrics']] == list(range(8))
        for item in sample['metrics']:
            assert all(math.isfinite(item[key]) for key in ['max_abs', 'relative_rmse', 'cosine'])
            assert min(item['max_abs'], item['relative_rmse']) >= 0
        final = sample['metrics'][-1]; gates = pipeline['gates']
        accepted = (final['max_abs'] <= gates['full_chain_max_absolute_error'] and
                    final['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and
                    final['cosine'] >= gates['full_chain_min_cosine'])
        assert sample['latent_gate_passed'] is accepted
        native = sample['native']
        assert native['ok'] and native['model_executed'] and native['layers'] == 28 and native['steps'] == 8
        assert native['parameters'] == 1923385472 and native['backend'] == 'vulkan' and not native['fixture']
        assert sample['captured_native_children'] == 1
        assert sample['native_children_executed_this_invocation'] == (0 if sample['capture_reused'] else 1)
        assert len(sample['files']) == 11
        for name, artifact in sample['files'].items():
            assert artifact['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', artifact['sha256'])
        assert sample['files']['latents.f32']['sha256'] == sample['files']['trace/step-7.f32']['sha256']
        asset = next(item for item in pipeline['jobs'][0]['assets'] if item['file'] == 'ltx098-dit.gguf')
        assert sample['model_sha256'] == asset['sha256']
        assert sample['resources']['observed'] and sample['resources']['samples'] > 0 and not sample['resources']['gpu_memory_measured']
        assert not any(sample[key] for key in ['vae_executed', 'different_prompt_video_checked',
                                              'full_pipeline_accepted', 'physical_android',
                                              'packaged_in_apk', 'acceptance_gates_changed'])
