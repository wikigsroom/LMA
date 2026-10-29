"""Private parameter comparison only, never a model forward or native acceptance."""
import json
import os
from pathlib import Path
import sys

os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from fetch_sd15_trained import sha

directory=ROOT/'build/sd-distilled-asset-probe'
original=json.loads((directory/'original-unet-acquisition-receipt.json').read_text(encoding='utf-8'))
candidate=next(a for a in json.loads((directory/'asset-plan.json').read_text(encoding='utf-8'))['assets'] if a['id']=='lcm_dreamshaper_v7_f16')
converted=json.loads((directory/'lcm-checkpoint-header.json').read_text(encoding='utf-8'))
assert original['full_sha256_verified'] and not original['model_executed']
for item in [original['asset'],candidate]:
    file=directory/'originals'/item['sha256']/Path(item['path']).name
    assert file.stat().st_size==item['bytes'] and sha(file)==item['sha256']
def sf(name):
    item=original['asset'];file=directory/'originals'/item['sha256']/Path(item['path']).name
    t=next(t for t in original['header']['tensors'] if t['name']==name);assert t['dtype']=='F32'
    start,end=t['data_offsets']
    with file.open('rb') as stream:stream.seek(8+original['header']['header_bytes']+start);raw=stream.read(end-start)
    assert len(raw)==end-start
    return np.frombuffer(raw,dtype='<f4').reshape(t['shape'])
def gguf(name):
    file=directory/'originals'/candidate['sha256']/candidate['path']
    t=next(t for t in converted['tensors'] if t['name']==name);assert t['ggml_type'] in [0,1]
    with file.open('rb') as stream:stream.seek(converted['data_offset']+t['offset']);raw=stream.read(t['bytes'])
    assert len(raw)==t['bytes']
    return np.frombuffer(raw,dtype='<f4' if t['ggml_type']==0 else '<f2').reshape(list(reversed(t['shape'])))
comparisons=[]
for native,reference in [('model.diffusion_model.time_embed.0.weight','time_embedding.linear_1.weight'),
                         ('model.diffusion_model.time_embed.0.bias','time_embedding.linear_1.bias')]:
    actual=gguf(native);expected=sf(reference)
    assert actual.shape==expected.shape and np.isfinite(actual).all() and np.isfinite(expected).all()
    cast=expected.astype(actual.dtype)
    comparisons.append(dict(candidate_tensor=native,original_tensor=reference,shape=list(actual.shape),candidate_dtype=str(actual.dtype),
                            equals_original_cast=bool(np.array_equal(actual,cast)),
                            maximum_abs_difference_from_original_cast=float(np.max(np.abs(actual.astype(np.float32)-cast.astype(np.float32))))))
projection=sf('time_embedding.cond_proj.weight')
assert projection.shape==(320,256) and np.isfinite(projection).all()
result=dict(schema='lma.private-lcm-parameter-comparison/1',assets=[original['asset'],candidate],full_asset_sha256s_verified=True,
            comparisons=comparisons,original_condition_projection_shape=list(projection.shape),
            original_projection_nonzero_elements=int(np.count_nonzero(projection)),
            candidate_has_named_projection=any('cond_proj' in t['name'] for t in converted['tensors']),
            fixed_guidance_folding_or_equivalence_proven=False,parameter_comparison_only=True,
            full_model_forward_executed=False,native_loading_attempted=False,quality_accepted=False,physical_android=False,complete_release_accepted=False)
(directory/'lcm-bias-comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ['comparisons','original_projection_nonzero_elements','candidate_has_named_projection','full_model_forward_executed']}))
