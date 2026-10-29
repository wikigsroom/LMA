"""Ignored learned-subgraph investigation, not a runtime conversion or full model test."""
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Optional
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
import numpy as np
import torch
torch.set_num_threads(1)
directory=Path(__file__).resolve().parent
sys.path.insert(0,str(directory.parents[1]/'tools'))
from fetch_sd15_trained import sha
lock=json.loads((directory/'diffusers-reference.json').read_text())
assert lock['revision']=='df60b35e4747c6fba196922de42a383ec0e82c06'
source={}
for item in lock['files']:
    raw=(directory/item['local_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    source[Path(item['path']).name]=raw.decode('utf-8')
scope=dict(torch=torch,math=math,nn=torch.nn,Optional=Optional,USE_PEFT_BACKEND=True,
           get_activation=lambda name:torch.nn.SiLU() if name=='silu' else (_ for _ in ()).throw(ValueError(name)))
definitions=[]
for filename,names in [('embeddings.py',{'TimestepEmbedding','get_timestep_embedding'}),
                       ('pipeline_latent_consistency_text2img.py',{'get_guidance_scale_embedding'})]:
    tree=ast.parse(source[filename]);found={}
    for node in ast.walk(tree):
        if isinstance(node,(ast.ClassDef,ast.FunctionDef)) and node.name in names:found[node.name]=node
    assert set(found)==names
    definitions.extend(found.values())
exec(compile(ast.fix_missing_locations(ast.Module(body=definitions,type_ignores=[])),'pinned-official-lcm-subgraph','exec'),scope)
receipt=json.loads((directory/'original-unet-acquisition-receipt.json').read_text())
item=receipt['asset'];asset=directory/'originals'/item['sha256']/Path(item['path']).name
assert asset.stat().st_size==item['bytes'] and sha(asset)==item['sha256']
tensors={t['name']:t for t in receipt['header']['tensors']}
def load(name):
    t=tensors['time_embedding.'+name];assert t['dtype']=='F32'
    start,end=t['data_offsets']
    with asset.open('rb') as stream:
        stream.seek(8+receipt['header']['header_bytes']+start);raw=stream.read(end-start)
    assert len(raw)==end-start
    return torch.from_numpy(np.frombuffer(raw,dtype='<f4').copy().reshape(t['shape']))
state={name:load(name) for name in ['linear_1.weight','linear_1.bias','linear_2.weight','linear_2.bias','cond_proj.weight']}
reference=scope['TimestepEmbedding'](320,1280,cond_proj_dim=256).eval();reference.load_state_dict(state,strict=True)
plain=scope['TimestepEmbedding'](320,1280).eval();plain.load_state_dict({k:v for k,v in state.items() if k!='cond_proj.weight'},strict=True)
sample=scope['get_timestep_embedding'](torch.tensor([0,1,249,499,749,999]),320,flip_sin_to_cos=True,downscale_freq_shift=0)
metrics=[]
def compare(a,b):
    d=(a-b).double()
    return dict(max_abs=float(d.abs().max()),rmse=float(torch.sqrt(torch.mean(d*d))))
with torch.no_grad():
    for guidance in [1.,8.5,12.]:
        condition=scope['get_guidance_scale_embedding'](None,torch.tensor([guidance-1.]),embedding_dim=256)
        offset=torch.nn.functional.linear(condition,state['cond_proj.weight'])
        delta=torch.nn.functional.linear(offset,state['linear_1.weight'])
        folded=scope['TimestepEmbedding'](320,1280).eval()
        folded.load_state_dict({k:v for k,v in state.items() if k!='cond_proj.weight'},strict=True)
        folded.linear_1.bias.copy_(state['linear_1.bias']+delta[0])
        expected=reference(sample,condition)
        measured=folded(sample)
        metrics.append(dict(distilled_guidance=guidance,folded_vs_reference=compare(measured,expected),
                            omitted_branch_vs_reference=compare(plain(sample),expected),
                            folded_bias_delta_max_abs=float(delta.abs().max())))
record=dict(schema='lma.private-lcm-trained-subgraph-fold-probe/1',official_source=lock,source_asset=item,
            actual_trained_subgraph=True,original_fp32_weights=True,full_model_forward=False,
            converted_gguf_executed=False,preparation_implemented=False,physical_android=False,
            image_quality_accepted=False,complete_release_accepted=False,timesteps=[0,1,249,499,749,999],metrics=metrics)
(directory/'lcm-condition-fold-probe.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(metrics),flush=True)
