"""Cross-check native preparation evidence without treating conversion as inference."""
import json
import re
from evidence import current


def check(records, status, digest, root):
    result = records['ltx098-prepare.json']
    assert result['schema'] == 'lma.ltx098-native-prepare-tests/1'
    assert result['passed'] and result['actual_trained_conversions'] == 1
    assert result['checks'] >= 156 and result['guards'] >= 45
    assert result['native_children'] == len(result['jobs']) and result['native_children'] >= 50
    assert len({job['name'] for job in result['jobs']}) == len(result['jobs'])
    coverage = result['fixture_coverage']
    assert coverage['finite_half_patterns'] == 63488 and coverage['finite_bf16_patterns'] == 65280
    assert coverage['float32_rounding_values'] == 190462 and coverage['tensor_header_order_differs_from_payload']
    trained = result['trained']; native = trained['native']
    assert native['schema'] == 'lma.ltx098-native-prepare/1' and native['operation'] == 'convert_dit' and native['ok']
    assert not native['fixture'] and native['source_sha256_verified'] and native['source_retained']
    assert native['source_bytes'] == native['source_streamed_bytes'] == 6340744492
    assert native['output_bytes'] == native['output_written_bytes'] == 3849516416
    assert native['tensors'] == 715 and native['parameters'] == 1923385472 and native['source_tensor_count'] == 944
    assert native['source_header_bytes'] == 145216
    lock = json.loads((root / 'third_party/ltx098-source-lock.json').read_text(encoding='utf-8'))
    assert native['source_header_sha256'] == lock['checkpoint_header_sha256']
    assert native['layout_sha256'] == lock['checkpoint_transformer_layout_sha256']
    original = records['ltx098-sampling.json']['trained']['conversion']
    assert native['source_sha256'] == native['expected_source_sha256'] == original['source_sha256']
    assert native['output_sha256'] == trained['python_output_sha256'] == original['sha256']
    assert trained['whole_output_sha256_independently_recomputed']
    assert native['dense_storage'] == 'F16' and native['other_storage'] == 'F32'
    assert native['input_chunk_bytes'] == 4*1024*1024 and native['output_chunk_capacity_bytes'] == 8*1024*1024
    assert not native['complete_tensor_allocated']
    assert trained['seconds'] > 0
    memory = trained['resources']
    assert memory['observed'] and memory['samples'] > 0 and not memory['gpu_memory_measured']
    assert 0 < memory['observed_peak_working_set_bytes'] < 128*1024*1024
    jobs = {job['name']: job for job in result['jobs']}
    assert jobs['trained-convert']['native'] == native and jobs['trained-convert']['resources'] == memory
    assert jobs['trained-inspect']['success'] and not jobs['trained-inspect']['native']['source_sha256_verified']
    assert jobs['fixture-convert']['native']['output_sha256'] == jobs['fixture-repeat']['native']['output_sha256']
    assert jobs['inspect-only']['success'] and not jobs['inspect-only']['native']['source_sha256_verified']
    for name in ['mid-cancel','commit-race','wrong-source-sha','existing-file','existing-directory',
                 'nonfinite-parameter','f16-overflow','duplicate-header','duplicate-config',
                 'shape-overflow','overlap','disk-budget','fixture-not-production','missing-storage']:
        assert not jobs[name]['success'] and not jobs[name]['native']['ok'] and jobs[name]['native']['error']
    assert jobs['mid-cancel']['native']['error'] == 'Cancelled'
    assert result['guards'] == sum(not job['success'] for job in result['jobs'])
    for platform in ['host','arm64']:
        build = records[f'ltx098-prepare-{platform}.json']
        assert result['builds'][platform] == build
        assert build['kind'] == ('host_compile' if platform == 'host' else 'android_compile')
        assert build['executable_bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', build['executable_sha256'])
        assert not any(build[key] for key in ['model_data_embedded','model_inference','engine_registered','packaged_in_apk','physical_android','virtualization_used'])
    arm = records['ltx098-prepare-arm64.json']
    assert arm['android_arm64_compiled'] and arm['android_platform'] == 28
    assert arm['elf']['16k_elf_aligned'] and arm['elf']['machine'] == 'aarch64'
    assert arm['elf']['android_api_notes'] == [28] and arm['elf']['interpreter'] == '/system/bin/linker64'
    assert set(arm['elf']['needed']) <= {'libc.so','libm.so','libdl.so'} and not arm['forbidden_network_process_imports']
    assert not any(result[key] for key in ['source_inference','model_data_embedded','engine_registered','packaged_in_apk',
                                         'physical_android','complete_video_pipeline','release_ready','virtualization_used'])
    assert not any(native[key] for key in ['model_inference','model_data_embedded','engine_registered','packaged_in_apk','physical_android','complete_video_pipeline'])
    assert status['ltx098_native_asset_prepare_host_tested'] and status['ltx098_native_asset_prepare_android_compiled']
    assert not status['ltx098_app_engine_registered'] and not status['release_ready']
    media_dir = root / 'docs/media/development'
    media = json.loads((media_dir / 'ltx098-native-prepare.json').read_text(encoding='utf-8'))
    current(media['input_fingerprint'])
    assert media['schema'] == 'lma.ltx098-native-prepare-media/1'
    assert media['evidence_sha256'] == digest((root / 'verification/development/ltx098-prepare.json').read_bytes())
    assert media['source_bytes'] == native['source_bytes'] and media['output_bytes'] == native['output_bytes']
    assert media['host_peak_working_set_bytes'] == memory['observed_peak_working_set_bytes']
    assert not any(media[key] for key in ['ui_recording','physical_android','inference_acceptance','release_ready'])
    png = media_dir / 'ltx098-native-prepare.png'
    assert png.stat().st_size == media['png_bytes'] and digest(png.read_bytes()) == media['png_sha256']
