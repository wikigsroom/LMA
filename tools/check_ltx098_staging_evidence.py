"""Audit published operation-staging evidence without accepting model failures."""
import json
import math
import re


def check(records, status, digest, root):
    baseline = records['ltx098-pipeline.json']
    analysis = records['ltx098-staging-analysis.json']
    assert analysis['schema'] == 'lma.ltx098-staging-analysis/1'
    assert analysis['input_capture_sha256'] == digest((root / 'verification/development/ltx098-text-diagnosis.json').read_bytes())
    assert len(analysis['metrics']) == 72 and analysis['mean_values'] == 2544
    assert analysis['mean_bitwise_identical'] and analysis['activation_order_bitwise_identical']
    assert analysis['retained_trained_intermediates'] and analysis['mean_simulation_is_numpy'] and analysis['activation_order_analysis_is_torch']
    assert not any(analysis[key] for key in ['native_replacement_executed', 'full_model_rerun', 'original_forward_modified', 'acceptance_gates_changed', 'physical_android'])
    for kind in ['attn_mean', 'ffn_mean', 'geglu_order']:
        items = [item for item in analysis['metrics'] if item['kind'] == kind]
        assert [item['layer'] for item in items] == list(range(24))
        assert all(item['max_abs'] == 0 and item['bitwise_identical'] and item['elements'] > 0 for item in items)
    assert max(item['original_baseline_max_abs'] for item in analysis['metrics'] if item['kind'] == 'geglu_order') == 7.62939453125e-6
    assert len(analysis['files']) == 120
    for item in analysis['files'].values():
        assert item['bytes'] == math.prod(item['shape']) * 4 and re.fullmatch('[a-f0-9]{64}', item['sha256'])
    names = {
        'activation': ('lma.ltx098-text-accuracy/1', 'independent_ggml_f64_attention_linear_norm_geglu'),
        'order': ('lma.ltx098-text-order/1', 'independent_ggml_f64_attention_linear_norm_original_geglu_order'),
        'staging': ('lma.ltx098-text-staging/1', 'independent_ggml_f64_attention_linear_norm_baseline_original_geglu_order'),
        'f32': ('lma.ltx098-text-f32/1', 'independent_ggml_f64_attention_linear_f32_staged_norm_original_geglu_order')}
    for variant, (schema, implementation) in names.items():
        candidate = records['ltx098-accuracy-' + variant + '.json']
        assert candidate['schema'] == schema and candidate['implementation'] == implementation
        assert candidate['linear_f64'] and candidate['normalization_f64'] is (variant in ['activation', 'order'])
        assert candidate['activation_f64'] is (variant == 'activation')
        if variant != 'activation': assert candidate['activation_original_order']
        if variant == 'f32': assert candidate['normalization_f32_staged']
        if variant == 'staging': assert candidate['normalization'] == 'baseline'
        assert candidate['actual_trained_jobs'] == candidate['native_children'] == 3
        assert candidate['distinct_prompts'] == 2 and candidate['aba_bitwise_identical']
        assert candidate['trained_t5_tensors'] == 219 and candidate['trained_t5_parameters'] == 4762310656
        assert re.fullmatch('[a-f0-9]{64}', candidate['binary_sha256']) and len(candidate['linked_archives']) == 4
        assert len(candidate['jobs']) == 3
        for job, case in zip(candidate['jobs'], [0, 1, 0]):
            native = job['native']; original = baseline['original_oracle']['cases'][case]
            assert job['case'] == case and job['prompt'] == baseline['jobs'][case]['request']['prompt']
            assert job['tokens'] == original['tokens'] and job['caption_bytes'] == len(original['tokens']) * 4096 * 4
            assert job['reference_sha256'] == original['files']['caption.f32']['sha256']
            assert re.fullmatch('[a-f0-9]{64}', job['caption_sha256'])
            assert native['encoder_implementation'] == implementation and native['model_inference'] and not native['fixture']
            assert native['layers'] == 24 and native['width'] == 4096
            assert native['model_loads'] == native['model_unloads'] == native['encode_calls'] == 1
            assert native['vocabulary_loads'] == native['vocabulary_unloads'] == 1
            assert len(native['items']) == 1 and native['items'][0]['tokens'] == original['tokens']
            assert native['items'][0]['mask'] == [1] * len(original['tokens'])
            assert native['items'][0]['shape'] == [1, len(original['tokens']), 4096]
            assert job['seconds'] > 0 and all(math.isfinite(value) and value >= 0 for value in job['metric'].values())
            assert job['resources']['observed'] and job['resources']['samples'] > 0
        assert candidate['jobs'][0]['caption_sha256'] == candidate['jobs'][2]['caption_sha256']
        assert not any(candidate[key] for key in ['production_source_changed', 'acceptance_gates_changed',
                      'complete_pipeline_numeric_accepted', 'physical_android', 'packaged_in_apk', 'engine_registered'])
    candidate = records['ltx098-accuracy-f32.json']
    candidate_hash = digest((root / 'verification/development/ltx098-accuracy-f32.json').read_bytes())
    chain = records['ltx098-accuracy-trajectory-f32.json']
    assert chain['schema'] == 'lma.ltx098-accuracy-trajectory/1' and chain['variant'] == 'f32'
    assert chain['candidate_sha256'] == candidate_hash and chain['original_oracle_sha256'] == candidate['original_oracle_sha256']
    assert chain['distinct_prompts'] == 2 and chain['aba_bitwise_identical']
    assert chain['captured_trained_text_children'] == chain['captured_trained_sampling_children'] == 3
    assert chain['captured_native_decode_children'] == 12
    assert chain['native_children_executed_this_invocation'] == (0 if chain['capture_reused'] else 14 if chain['first_sampling_recovered'] else 15)
    assert len(chain['jobs']) == 3
    failures = []
    for index, (job, case) in enumerate(zip(chain['jobs'], [0, 1, 0])):
        assert job['index'] == index and job['case'] == case and job['text'] == candidate['jobs'][index]
        sampled = job['sampling']; decoded = job['decode']; gates = baseline['gates']
        assert sampled['schema'] == 'lma.ltx098-accuracy-sampling/1' and sampled['variant'] == 'f32' and sampled['case'] == case
        assert sampled['candidate_sha256'] == candidate_hash and sampled['candidate_caption_sha256'] == job['text']['caption_sha256']
        assert sampled['gates'] == gates and len(sampled['metrics']) == sampled['original_trajectory_files_verified'] == 8
        assert [item['step'] for item in sampled['metrics']] == list(range(8))
        native = sampled['native']
        assert native['ok'] and native['model_executed'] and not native['fixture'] and native['backend'] == 'vulkan'
        assert native['steps'] == 8 and native['layers'] == 28 and native['parameters'] == 1923385472
        final = sampled['metrics'][-1]
        accepted = final['max_abs'] <= gates['full_chain_max_absolute_error'] and final['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and final['cosine'] >= gates['full_chain_min_cosine']
        assert sampled['latent_gate_passed'] is accepted
        assert sampled['files']['latents.f32']['sha256'] == sampled['files']['trace/step-7.f32']['sha256']
        assert not any(sampled[key] for key in ['vae_executed', 'full_pipeline_accepted', 'physical_android', 'packaged_in_apk', 'acceptance_gates_changed'])
        assert decoded['schema'] == 'lma.ltx098-accuracy-decode/1' and decoded['binding']['candidate_sha256'] == candidate_hash
        assert decoded['binding']['candidate_caption_sha256'] == job['text']['caption_sha256']
        assert decoded['binding']['sampling_latents_sha256'] == sampled['files']['latents.f32']['sha256']
        assert decoded['gates'] == gates and decoded['t5_sampling_bound_to_native_captures']
        assert [stage['stage'] for stage in decoded['stages']] == ['noise', 'unpatchify', 'vae', 'frames']
        vae = decoded['stages'][2]['native']
        assert vae['graph_runs'] == vae['session_loads'] == vae['session_unloads'] == 9 and vae['max_live_sessions'] == 1
        assert decoded['captured_native_decode_children'] == 4 and len(decoded['assets']) == 21
        assert [metric['file'] for metric in decoded['metrics']] == ['caption.f32', 'denoised-tokens.f32', 'denoised-ncthw.f32', 'decoded-ncthw.f32']
        failed = []
        for metric in decoded['metrics']:
            assert all(math.isfinite(metric[key]) for key in ['max_abs', 'relative_rmse', 'cosine'])
            ok = metric['max_abs'] <= gates['full_chain_max_absolute_error'] and metric['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and metric['cosine'] >= gates['full_chain_min_cosine']
            assert metric['passed'] is ok
            if not ok: failed.append(metric['file'])
        rgb = decoded['rgb']; ok = rgb['max_error'] <= gates['rgb_max_byte_error'] and rgb['mean_error'] <= gates['rgb_mean_byte_error']
        assert rgb['passed'] is ok
        if not ok: failed.append('rgb')
        assert decoded['failures'] == failed and decoded['full_chain_numeric_gate_passed'] is (not failed)
        if failed: failures.append(dict(job=index, files=failed))
        assert not any(decoded[key] for key in ['reference_tensors_used_as_native_inputs', 'full_pipeline_accepted', 'video_quality_accepted', 'physical_android', 'packaged_in_apk', 'engine_registered', 'acceptance_gates_changed'])
    assert chain['numeric_failures'] == failures and chain['full_chain_original_numeric_gates_passed'] is (not failures)
    assert not any(chain[key] for key in ['production_source_changed', 'acceptance_gates_changed', 'engine_registered', 'packaged_in_apk', 'physical_android', 'video_quality_accepted', 'complete_release_accepted'])
    assert chain['jobs'][0]['sampling']['capture_directory'] != chain['jobs'][2]['sampling']['capture_directory']
    assert chain['jobs'][0]['decode']['capture_directory'] != chain['jobs'][2]['decode']['capture_directory']
    for name in ['initial-tokens.f32', 'decode-noise.f32', 'denoised-ncthw.f32', 'decoded-ncthw.f32', 'frames.lma']:
        assert chain['jobs'][0]['decode']['files'][name]['sha256'] == chain['jobs'][2]['decode']['files'][name]['sha256']
    assert status['ltx098_f32_staging_analysis_host_checked'] and status['ltx098_staged_t5_candidates_host_executed'] and status['ltx098_staged_full_chain_host_executed']
    assert status['ltx098_staged_full_chain_numerical_passed'] is (not failures)
    assert not status['ltx098_t5_roundoff_repair_accepted']
    media = json.loads((root / 'docs/media/development/ltx098-staging-media.json').read_text(encoding='utf-8'))
    from evidence import current
    current(media['input_fingerprint'])
    assert media['schema'] == 'lma.ltx098-staging-media/1'
    assert media['candidate_numeric_gates_passed'] is (not failures)
    assert media['frames'] == 33 and media['mp4_fps'] == 24 and media['gif_duration_ms'] == 1320
    assert len(media['sources']) == 8 and len(media['raw_source_frames']) == 6 and len(media['files']) == 4
    for name, identity in media['sources'].items():
        assert digest((root / name).read_bytes()) == identity
    for name, identity in media['files'].items():
        data = (root / 'docs/media/development' / name).read_bytes()
        assert len(data) == identity['bytes'] and digest(data) == identity['sha256']
    assert not any(media[key] for key in ['physical_android', 'app_screen_recording', 'video_quality_accepted',
                                         'engine_registered', 'official_multiscale_default_reproduced'])
    diagnostic_names = ['ltx098-context-reference-vulkan.json', 'ltx098-context-reference-cpu.json',
                        'ltx098-compute-f32-reference-cpu.json', 'ltx098-compute-f32-reference-vulkan.json',
                        'ltx098-compute-f32-rms-reference-cpu.json']
    captions = set()
    for name in diagnostic_names:
        item = records[name]; compute = name.startswith('ltx098-compute-')
        assert item['schema'] == ('lma.ltx098-compute-precision/1' if compute else 'lma.ltx098-sampling-context-diagnosis/1')
        assert item['case'] == 1 and item['context'] == 'reference' and item['reference_caption_supplied']
        assert item['original_case'] == baseline['original_oracle']['cases'][1]
        assert item['baseline_request'] == baseline['jobs'][1]['request']
        assert item['caption_sha256'] == item['original_case']['files']['caption.f32']['sha256']
        captions.add(item['caption_sha256'])
        assert item['candidate_record_sha256'] is None and item['diagnostic_only']
        assert item['gates'] == baseline['gates'] and len(item['metrics']) == 8 and len(item['files']) == 11
        assert [metric['step'] for metric in item['metrics']] == list(range(8))
        assert set(item['files']) == {'request.json', 'native.log', 'latents.f32'} | {'trace/step-' + str(i) + '.f32' for i in range(8)}
        for metric in item['metrics']:
            assert all(math.isfinite(metric[key]) for key in ['max_abs', 'relative_rmse', 'cosine'])
            assert metric['max_abs'] >= 0 and metric['relative_rmse'] >= 0 and -1.00000001 <= metric['cosine'] <= 1.00000001
        for identity in item['files'].values():
            assert identity['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', identity['sha256'])
        assert item['seconds'] > 0 and re.fullmatch('[a-f0-9]{64}', item['native_binary_sha256'])
        assert item['model_sha256'] == next(asset['sha256'] for asset in baseline['jobs'][1]['assets'] if asset['file'] == 'ltx098-dit.gguf')
        native = item['native']
        assert native['ok'] and native['model_executed'] and not native['fixture'] and native['backend'] == item['backend']
        assert native['steps'] == 8 and native['layers'] == 28 and native['parameters'] == 1923385472
        assert item['files']['latents.f32']['sha256'] == item['files']['trace/step-7.f32']['sha256']
        assert item['captured_native_children'] == 1 and item['native_children_executed_this_invocation'] == (0 if item['capture_reused'] else 1)
        assert item['resources']['observed'] and item['resources']['samples'] > 0
        final = item['metrics'][-1]; gates = item['gates']
        matched = final['max_abs'] <= gates['full_chain_max_absolute_error'] and final['relative_rmse'] <= gates['full_chain_max_relative_rmse'] and final['cosine'] >= gates['full_chain_min_cosine']
        assert item['latent_gate_matched'] is matched
        assert not any(item[key] for key in ['model_stage_accepted', 'full_pipeline_accepted', 'physical_android',
                                            'packaged_in_apk', 'engine_registered', 'acceptance_gates_changed'])
        if compute:
            compilation = item['compilation']; current(compilation['input_fingerprint'])
            assert compilation['schema'] == 'lma.ltx098-compute-precision-build/1'
            assert compilation['executable_sha256'] == item['native_binary_sha256'] and len(compilation['linked_archives']) == 5
            assert item['explicit_f32_matmul_operands'] and native['explicit_f32_matmul_operands']
            assert compilation['mode'] == ('f32-rms' if item['staged_rms'] else 'f32')
            assert native['precision_policy'] == 'explicit_f32_matmul_' + compilation['mode']
            assert not any(compilation[key] for key in ['android_compiled', 'packaged_in_apk', 'engine_registered'])
    assert len(captions) == 1
    assert status['ltx098_same_caption_sampler_diagnosis_host_executed'] and status['ltx098_cpu_f32_operands_diagnostic_host_executed']
    assert status['ltx098_cpu_f32_operands_diagnostic_latent_matched'] is records['ltx098-compute-f32-reference-cpu.json']['latent_gate_matched']
    assert status['ltx098_cpu_staged_rms_diagnostic_host_executed']
    assert status['ltx098_cpu_staged_rms_diagnostic_latent_matched'] is records['ltx098-compute-f32-rms-reference-cpu.json']['latent_gate_matched']
    assert all(isinstance(value, str) and value for value in status['scope_definitions'].values())
