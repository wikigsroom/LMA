"""Private complete learned-parameter comparison, not a full neural forward."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
root=Path(__file__).resolve().parents[2];directory=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'tools'))
from fetch_sd15_trained import sha
deadline=time.monotonic()+7200
ready=root/'build/sd-variants-app-host-tests/run-1793296745112181400/java.stderr'
while not ready.exists() or b'Start actual production Java/native case: sd15-initial' not in ready.read_bytes():
    if time.monotonic()>deadline:raise RuntimeError('No CPU-stage window; full comparison not started')
    time.sleep(10)
original=json.loads((directory/'original-unet-acquisition-receipt.json').read_text())
candidate=next(a for a in json.loads((directory/'asset-plan.json').read_text())['assets'] if a['id']=='lcm_dreamshaper_v7_f16')
header=json.loads((directory/'lcm-checkpoint-header.json').read_text())
mapping=json.loads((directory/'lcm-tensor-mapping.json').read_text())
assert mapping['mapped_tensors']==686 and len(mapping['missing'])==1 and not mapping['unexpected_candidate']
files=[directory/'originals'/item['sha256']/Path(item['path']).name for item in [original['asset'],candidate]]
stamps=[]
for path,item in zip(files,[original['asset'],candidate]):
    stamps.append((path.stat().st_size,path.stat().st_mtime_ns))
    assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256']
print('Both complete original and converted objects rehashed; compare every mapped UNet parameter.',flush=True)
sources={t['name']:t for t in original['header']['tensors']};targets={t['name']:t for t in header['tensors']}
metrics=[];total=0
with files[0].open('rb') as reference,files[1].open('rb') as converted:
    for entry in sorted(mapping['mapping'],key=lambda e:sources[e['original']]['data_offsets'][0]):
        a=sources[entry['original']];b=targets[entry['candidate']]
        assert a['dtype']=='F32' and b['ggml_type'] in [0,1]
        dtype=np.dtype('<f4' if b['ggml_type']==0 else '<f2')
        elements=int(np.prod(a['shape'],dtype=np.int64));assert b['bytes']==elements*dtype.itemsize
        reference.seek(8+original['header']['header_bytes']+a['data_offsets'][0]);converted.seek(header['data_offset']+b['offset'])
        remaining=elements;mismatches=0;maximum_cast=0.;maximum_original=0.
        while remaining:
            size=min(262144,remaining);xraw=reference.read(size*4);yraw=converted.read(size*dtype.itemsize)
            assert len(xraw)==size*4 and len(yraw)==size*dtype.itemsize
            x=np.frombuffer(xraw,dtype='<f4');y=np.frombuffer(yraw,dtype=dtype)
            assert np.isfinite(x).all() and np.isfinite(y).all()
            cast=x.astype(dtype);assert np.isfinite(cast).all()
            mismatches+=int(np.count_nonzero(y!=cast))
            maximum_cast=max(maximum_cast,float(np.max(np.abs(y.astype(np.float32)-cast.astype(np.float32)))))
            maximum_original=max(maximum_original,float(np.max(np.abs(y.astype(np.float32)-x))))
            remaining-=size
        metrics.append(dict(original=entry['original'],candidate=entry['candidate'],parameters=elements,candidate_dtype=str(dtype),
                            mismatches_from_original_cast=mismatches,max_abs_from_original_cast=maximum_cast,max_abs_from_original_f32=maximum_original))
        total+=elements
        if len(metrics)%100==0:print('Compared mapped tensors: '+str(len(metrics))+' / 686',flush=True)
for path,stamp in zip(files,stamps):assert (path.stat().st_size,path.stat().st_mtime_ns)==stamp
result=dict(schema='lma.private-lcm-full-unet-parameter-comparison/1',assets=[original['asset'],candidate],full_object_sha256s_reverified=True,
            mapped_tensors=len(metrics),parameters_compared=total,all_mapped_values_equal_original_cast=all(m['mismatches_from_original_cast']==0 for m in metrics),
            mismatch_tensors=sum(m['mismatches_from_original_cast']>0 for m in metrics),metrics=metrics,
            omitted_original_projection=mapping['missing'],parameter_comparison_only=True,complete_unet_forward=False,
            condition_projection_repaired=False,checkpoint_prepared=False,physical_android=False,image_quality_accepted=False,complete_release_accepted=False)
(directory/'lcm-full-unet-comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['metrics','assets','omitted_original_projection']}),flush=True)
