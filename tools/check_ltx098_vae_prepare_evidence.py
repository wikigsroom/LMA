"""Audit model-free graphs, native preparation and independently decoded assets."""
import hashlib
import json
import math
import re
import sys
from evidence import current


def check(records,status,digest,root):
    audit=records['ltx098-vae-templates.json'];result=records['ltx098-vae-prepare.json']
    assert audit['schema']=='lma.ltx098-vae-templates/1' and audit['passed']
    current(audit['input_fingerprint']);current(audit['output_fingerprint'])
    assert audit['source_parameters_observed']==134 and audit['external_initializers']==138
    assert audit['folded_reshape_tables']==21 and audit['architecture_frequency_vectors']==5
    assert audit['constant_tensor_types']=={'7':1073,'1':129}
    assert audit['all_external_parameters_match_original_source'] and audit['all_graph_constants_classified']
    assert not any(audit[k] for k in ['source_full_sha_verified_by_this_tool','inline_learned_data','model_inference','packaged_in_apk','physical_android'])
    contract_path=root/'research/ltx098_vae_prepare/contract.json';contract=json.loads(contract_path.read_text(encoding='utf-8'))
    assert contract['schema']=='lma.ltx098-vae-prepare-contract/1' and not contract['model_data_embedded']
    assert contract['graphs']==audit['graphs'] and len(contract['layout'])==134 and len(contract['routes'])==138
    assert {r['source'] for r in contract['routes']}==set(contract['layout'])
    assert all(r['transform']=='reshape_f32' for r in contract['routes'])
    lock=json.loads((root/'third_party/ltx098-vae-source-lock.json').read_text(encoding='utf-8'))
    assert contract['checkpoint']==lock['checkpoint'] and contract['vae_config']==lock['vae_config']
    assert len(lock['layout'])==132 and sum(math.prod(s) for s in lock['layout'].values())==552814641
    assert {k.removeprefix('vae.decoder.'):v for k,v in contract['layout'].items() if k.startswith('vae.decoder.')}==lock['layout']
    assert contract['layout']['vae.per_channel_statistics.mean-of-means']==contract['layout']['vae.per_channel_statistics.std-of-means']==[128]
    assert sum(g['data_bytes'] for g in contract['graphs'])==audit['parameter_bytes_verified']==2211259604
    # Independently inspect every committed protobuf: no learned initializer
    # bytes, subgraphs or opaque functions; all float attributes are structural.
    sys.path.insert(0,str(root/'build/soulx-python'))
    import onnx
    import torch
    import numpy as np
    from onnx import numpy_helper
    assert torch.__version__==lock['torch_runtime_version']
    frequency=torch.exp((-math.log(10000)*torch.arange(128,dtype=torch.float32))/128).reshape(1,128).numpy()
    totals={1:0,7:0};frequencies=0;initializers=0
    for graph in contract['graphs']:
        path=root/'research/ltx098_vae_prepare/graphs'/graph['file'];raw=path.read_bytes()
        assert len(raw)==graph['bytes'] and digest(raw)==graph['sha256']
        model=onnx.load(str(path),load_external_data=False)
        assert not model.functions and not model.training_info and not model.graph.sparse_initializer
        initializers+=len(model.graph.initializer)
        for tensor in model.graph.initializer:
            assert tensor.data_location==onnx.TensorProto.EXTERNAL and tensor.data_type==1
            assert not any([tensor.raw_data,tensor.float_data,tensor.double_data,tensor.int32_data,tensor.int64_data,tensor.uint64_data,tensor.string_data])
            ext={p.key:p.value for p in tensor.external_data}
            assert len(ext)==len(tensor.external_data)==3 and ext['location']==graph['data_file']
            route=next(r for r in contract['routes'] if r['stage']==contract['graphs'].index(graph) and r['initializer']==tensor.name)
            assert list(tensor.dims)==route['shape'] and int(ext['offset'])==route['offset'] and int(ext['length'])==route['bytes']
        for node in model.graph.node:
            assert node.domain in ('','ai.onnx')
            for attr in node.attribute:
                assert attr.type in [onnx.AttributeProto.TENSOR,onnx.AttributeProto.INT,onnx.AttributeProto.INTS,onnx.AttributeProto.FLOAT]
                if attr.type==onnx.AttributeProto.FLOAT:assert attr.f==1.0
                if attr.type!=onnx.AttributeProto.TENSOR:continue
                value=numpy_helper.to_array(attr.t);assert attr.t.data_type in totals;totals[attr.t.data_type]+=1
                if attr.t.data_type==1:
                    if list(value.shape)==[1,128]:
                        assert node.name.endswith('/time_proj/Constant_1') and value.tobytes()==frequency.tobytes();frequencies+=1
                    else:assert value.size<=8 and np.all(np.isin(value,np.array([1e-8,1.,2.],dtype=np.float32)))
                else:assert value.size<=8
    assert totals=={7:1073,1:129} and frequencies==5 and initializers==138
    assert result['schema']=='lma.ltx098-native-vae-prepare-tests/1' and result['passed'] and result['checks']>=240
    assert result['actual_trained_conversions']==1 and result['actual_trained_decode_jobs']==4
    assert result['actual_native_children']==result['preparation_children']+4==len(result['jobs'])+len(result['decode_jobs'])
    assert len(result['guards'])==25 and len(set(result['guards']))==25
    assert result['guards']==[j['name'] for j in result['jobs'] if not j['success']]
    assert all(not j['native']['ok'] and j['native']['error'] for j in result['jobs'] if not j['success'])
    native=result['trained_conversion']
    assert native['source_sha256_verified'] and native['source_sha256']==native['expected_source_sha256']==lock['checkpoint']['sha256']
    assert native['source_streamed_bytes']==native['source_bytes']==6340744492 and native['source_tensor_count']==944
    assert native['source_header_sha256']==audit['source_header_sha256']
    assert native['contract_sha256']==digest(contract_path.read_bytes())
    assert native['asset_written_bytes']==native['asset_bytes']==2211661835 and native['asset_files']==18 and native['graphs']==9
    assert native['parameter_written_bytes']==native['parameter_bytes']==2211259604
    assert native['decoder_tensors']==132 and native['decoder_parameters']==552814641 and native['learned_source_tensors']==134 and native['external_initializers']==138
    assert native['graph_sha256_verified'] and native['parameter_sha256_verified'] and native['source_retained']
    assert native['input_chunk_bytes']==4*1024**2 and native['output_chunk_capacity_bytes']==8*1024**2 and not native['complete_tensor_allocated']
    assert {a['file']:(a['bytes'],a['sha256']) for a in native['assets']}=={a['file']:(a['bytes'],a['sha256']) for a in contract['manifest']['assets']}
    memory=result['conversion_resources'];assert memory['observed'] and memory['samples']>0 and not memory['gpu_memory_measured']
    assert 0<memory['observed_peak_working_set_bytes']<128*1024**2
    assert result['template_audit']==audit and result['all_18_assets_byte_identical_to_python'] and result['host_model_inference_tested']
    assert result['gates']==lock['gates'] and len(result['metrics'])==40
    for metric in result['metrics']:
        assert metric['elements']>0 and math.isfinite(metric['max_absolute_error']) and math.isfinite(metric['relative_rmse']) and math.isfinite(metric['cosine'])
        assert 0<=metric['max_absolute_error']<=lock['gates']['max_absolute_error'] and 0<=metric['relative_rmse']<=lock['gates']['max_relative_rmse'] and metric['cosine']>=lock['gates']['min_cosine']
    assert result['original_reference_files']==44
    current(result['original_reference']['input_fingerprint']);current(result['decoder_build']['input_fingerprint'])
    for job in result['decode_jobs']:
        value=job['native'];assert value['ok'] and value['graph_runs']==value['session_loads']==value['session_unloads']==9 and value['max_live_sessions']==1
        assert job['resources']['observed'] and job['resources']['samples']>0
    for platform in ['host','arm64']:
        build=records[f'ltx098-vae-prepare-{platform}.json'];assert result['builds'][platform]==build
        assert re.fullmatch('[a-f0-9]{64}',build['executable_sha256']) and build['executable_bytes']>0
        assert not any(build[k] for k in ['model_inference','model_data_embedded','engine_registered','packaged_in_apk','physical_android','virtualization_used'])
    arm=records['ltx098-vae-prepare-arm64.json']
    assert arm['android_arm64_compiled'] and arm['elf']['machine']=='aarch64' and arm['elf']['16k_elf_aligned'] and arm['elf']['android_api_notes']==[28]
    assert arm['elf']['interpreter']=='/system/bin/linker64' and set(arm['elf']['needed'])<={'libc.so','libm.so','libdl.so'} and not arm['forbidden_network_process_imports']
    assert not any(result[k] for k in ['engine_registered','packaged_in_apk','physical_android','complete_video_pipeline','release_ready','virtualization_used','model_data_embedded'])
    assert not any(native[k] for k in ['model_inference','model_data_embedded','engine_registered','packaged_in_apk','physical_android','complete_video_pipeline'])
    assert status['ltx098_vae_asset_prepare_host_tested'] and status['ltx098_vae_asset_prepare_android_compiled'] and status['ltx098_prepared_vae_decode_host_tested']
    assert not status['ltx098_full_chain_numeric_accepted'] and not status['release_ready']
    media_dir=root/'docs/media/development';media=json.loads((media_dir/'ltx098-vae-prepared-decode.json').read_text(encoding='utf-8'))
    current(media['input_fingerprint']);assert media['schema']=='lma.ltx098-vae-prepared-media/1'
    assert media['evidence_sha256']==digest((root/'verification/development/ltx098-vae-prepare.json').read_bytes())
    assert media['host_preparation_peak_bytes']==memory['observed_peak_working_set_bytes'] and len(media['sources'])==4
    assert media['native_children_executed_this_tool']==0 and media['capture_reused'] and media['synthetic_latent_inputs']
    for source in media['sources']:
        metric=next(m for m in result['metrics'] if m['case']==source['case'] and m['stage']==9)
        assert source['metric']==metric and re.fullmatch('[a-f0-9]{64}',source['native_sha256']) and source['native_bytes']==metric['elements']*4
        assert source['original_sha256']==result['original_reference']['files'][source['original_file']]['sha256']
    assert not any(media[k] for k in ['ui_recording','physical_android','prompt_to_video_quality_accepted','release_ready'])
    png=media_dir/'ltx098-vae-prepared-decode.png'
    assert png.stat().st_size==media['png_bytes'] and digest(png.read_bytes())==media['png_sha256']
