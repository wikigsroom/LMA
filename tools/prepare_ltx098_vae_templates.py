"""Audit model-free old-VAE graphs and map every external parameter to user weights.

Developer-only structural compilation. No downloads or neural inference. The
Android preparer will use these graphs and mappings without Python/ONNX/Torch.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sys
import time
import numpy as np
from evidence import fingerprint, current
from ltx098_assets import Checkpoint, sha

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'build/ltx098-vae-assets'
DEST = ROOT / 'research/ltx098_vae_prepare'


def inputs():
    return fingerprint('tools/prepare_ltx098_vae_templates.py', 'tools/ltx098_vae.py',
                       'tools/ltx098_assets.py', 'third_party/ltx098-source-lock.json',
                       'third_party/ltx098-vae-source-lock.json')


def source_name(stage, tensor, graph):
    name = tensor.name
    if name == 'multiplier': return 'vae.decoder.timestep_scale_multiplier'
    if stage == 0:
        if name in ['mean','std']: return 'vae.per_channel_statistics.' + ('mean-of-means' if name=='mean' else 'std-of-means')
        if name.startswith('conv.'): return 'vae.decoder.conv_in.' + name[len('conv.'):]
    if 1 <= stage <= 7:
        if name.startswith('block.'): return f'vae.decoder.up_blocks.{stage-1}.' + name[len('block.'):]
        if name.startswith('onnx::Add_'):
            consumers = [n for n in graph.node if name in n.input]
            assert len(consumers)==1 and consumers[0].op_type=='Add'
            match = re.fullmatch(r'/block/res_blocks\.(\d+)/Add',consumers[0].name)
            assert match
            return f'vae.decoder.up_blocks.{stage-1}.res_blocks.{match[1]}.scale_shift_table'
    if stage == 8:
        if name.startswith('embed.'): return 'vae.decoder.last_time_embedder.' + name[len('embed.'):]
        if name.startswith('conv.'): return 'vae.decoder.conv_out.' + name[len('conv.'):]
        if name.startswith('onnx::Add_'):
            consumers = [n for n in graph.node if name in n.input]
            assert len(consumers)==1 and consumers[0].name=='/Add' and consumers[0].op_type=='Add'
            return 'vae.decoder.last_scale_shift_table'
    raise ValueError('Unmapped initializer: ' + name)


def run():
    before=inputs()
    sys.path.insert(0,str(ROOT/'build/soulx-python'))
    import onnx
    from onnx import numpy_helper
    import torch
    lock=json.loads((ROOT/'third_party/ltx098-vae-source-lock.json').read_text(encoding='utf-8'))
    for name,version in lock['python_versions'].items():
        if name in ['onnx','numpy']:
            import importlib.metadata
            assert importlib.metadata.version(name)==version
    assert torch.__version__==lock['torch_runtime_version']
    original=json.loads((ASSETS/'ltx098-vae.json').read_text(encoding='utf-8'))
    current(original['input_fingerprint'])
    source=Checkpoint(ROOT/'build/ltx098-trained/originals'/lock['checkpoint']['file'])
    assert source.length==lock['checkpoint']['bytes'] and source.config['vae']==lock['vae_config']
    old_lock=json.loads((ROOT/'third_party/ltx098-source-lock.json').read_text(encoding='utf-8'))
    assert source.header_sha256==old_lock['checkpoint_header_sha256']
    layout={'vae.decoder.'+k:v for k,v in lock['layout'].items()}
    layout.update({'vae.per_channel_statistics.mean-of-means':[128], 'vae.per_channel_statistics.std-of-means':[128]})
    assert len(layout)==134 and all(source.tensors[k]['shape']==shape for k,shape in layout.items())
    # Original diffusers Timesteps(256, flip_sin_to_cos=True,
    # downscale_freq_shift=0): this vector is architecture-derived, not learned.
    frequency=torch.exp((-math.log(10000)*torch.arange(128,dtype=torch.float32))/128).reshape(1,128).numpy()
    assert frequency.dtype==np.float32
    expected={a['file']:a for a in original['assets']}
    routes=[];graphs=[];observed=set();constant_types=collections.Counter();frequency_nodes=0;folded=0;operators=collections.Counter()
    DEST.mkdir(exist_ok=True);(DEST/'graphs').mkdir(exist_ok=True)
    start=time.perf_counter()
    for stage in range(9):
        name=f'stage-{stage:02d}.onnx';path=ASSETS/name;raw=path.read_bytes()
        assert len(raw)==expected[name]['bytes'] and hashlib.sha256(raw).hexdigest()==expected[name]['sha256']
        model=onnx.load(str(path),load_external_data=False);graph=model.graph
        assert not model.functions and not model.training_info and not model.doc_string and not graph.doc_string
        assert not graph.sparse_initializer and all(not v.doc_string for v in list(graph.input)+list(graph.output)+list(graph.value_info))
        assert all(o.domain in ('','ai.onnx') and o.version==17 for o in model.opset_import)
        assert len({t.name for t in graph.initializer})==len(graph.initializer)
        offset=0;data_hash=hashlib.sha256()
        with (ASSETS/(name+'.data')).open('rb') as data:
            for tensor in graph.initializer:
                assert tensor.data_type==onnx.TensorProto.FLOAT and tensor.data_location==onnx.TensorProto.EXTERNAL
                assert not any([tensor.raw_data,tensor.float_data,tensor.double_data,tensor.int32_data,tensor.int64_data,tensor.uint64_data,tensor.string_data])
                ext={p.key:p.value for p in tensor.external_data}
                assert len(ext)==len(tensor.external_data)==3 and ext['location']==name+'.data'
                size=math.prod(tensor.dims)*4
                assert int(ext['offset'])==offset and int(ext['length'])==size
                key=source_name(stage,tensor,graph);assert key in layout
                assert math.prod(layout[key])*4==size
                array=source.array(key);blob=data.read(size)
                assert len(blob)==size and blob==array.astype('<f4',copy=False).tobytes(order='C'), 'Folded initializer is not a source reshape: '+tensor.name
                data_hash.update(blob);observed.add(key)
                routes.append(dict(source=key,stage=stage,initializer=tensor.name,shape=list(tensor.dims),offset=offset,bytes=size,transform='reshape_f32'))
                if tensor.name.startswith('onnx::'):folded+=1
                offset+=size;del array,blob
            assert not data.read(1)
        assert offset==expected[name+'.data']['bytes'] and data_hash.hexdigest()==expected[name+'.data']['sha256']
        for node in graph.node:
            assert node.domain in ('','ai.onnx') and not node.doc_string
            operators[node.op_type]+=1
            for attr in node.attribute:
                assert attr.type not in [onnx.AttributeProto.GRAPH,onnx.AttributeProto.GRAPHS,onnx.AttributeProto.TENSORS,
                                         onnx.AttributeProto.SPARSE_TENSOR,onnx.AttributeProto.SPARSE_TENSORS]
                if attr.type==onnx.AttributeProto.TENSOR:
                    tensor=attr.t;constant_types[tensor.data_type]+=1
                    assert tensor.data_location==onnx.TensorProto.DEFAULT and not tensor.external_data
                    value=numpy_helper.to_array(tensor)
                    if tensor.data_type==onnx.TensorProto.INT64:
                        assert value.size<=8 and np.all(np.abs(value.astype(object))<=9223372036854775807)
                    elif tensor.data_type==onnx.TensorProto.FLOAT:
                        if list(value.shape)==[1,128]:
                            assert node.name.endswith('/time_proj/Constant_1') and value.tobytes()==frequency.tobytes();frequency_nodes+=1
                        else:
                            assert value.size<=8 and np.all(np.isin(value,np.array([1e-8,1.,2.],dtype=np.float32)))
                    else:raise ValueError('Unexpected constant tensor type')
        graph_record=dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                          data_file=name+'.data',data_bytes=offset,data_sha256=data_hash.hexdigest(),
                          nodes=len(graph.node),initializers=len(graph.initializer))
        graphs.append(graph_record);(DEST/'graphs'/name).write_bytes(raw)
        print(json.dumps(dict(stage=stage,initializers=len(graph.initializer),external_parameter_bytes=offset)),flush=True)
    assert observed==set(layout) and len(routes)==138 and folded==21 and frequency_nodes==5
    # Remove developer evidence paths, keeping only architecture and source/asset identities.
    manifest={k:v for k,v in original.items() if k!='input_fingerprint'}
    contract=dict(schema='lma.ltx098-vae-prepare-contract/1',checkpoint=lock['checkpoint'],vae_config=lock['vae_config'],
                  layout=layout,graphs=graphs,routes=routes,manifest=manifest,
                  learned_tensors=134,decoder_tensors=132,decoder_parameters=552814641,
                  transformations=['reshape_f32'],model_data_embedded=False)
    contract_path=DEST/'contract.json';contract_path.write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    current(before)
    record=dict(schema='lma.ltx098-vae-templates/1',passed=True,graphs=graphs,external_initializers=len(routes),
                source_parameters_observed=len(observed),folded_reshape_tables=folded,
                architecture_frequency_vectors=frequency_nodes,constant_tensor_types=dict(constant_types),
                operator_counts=dict(operators),parameter_bytes_verified=sum(g['data_bytes'] for g in graphs),
                source_header_sha256=source.header_sha256,source_full_sha_verified_by_this_tool=False,
                all_external_parameters_match_original_source=True,all_graph_constants_classified=True,
                inline_learned_data=False,model_inference=False,packaged_in_apk=False,physical_android=False,
                seconds=time.perf_counter()-start,input_fingerprint=before,
                output_fingerprint=fingerprint('research/ltx098_vae_prepare/graphs','research/ltx098_vae_prepare/contract.json'))
    out=ROOT/'build/ltx098-vae-template-tests';out.mkdir(exist_ok=True)
    (out/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['input_fingerprint','output_fingerprint','graphs','operator_counts']}),flush=True)
    return record


if __name__=='__main__':run()
