"""Bounded native cascade/source-math contracts, no complete trained models."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/'build/ultratex-python'),str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    import numpy as np
    import torch
    from PIL import Image
    from spatial_portable import Source,strict_weights
    from uniforge_components import FrozenConditioner,joint,flow
    from export_uniforge import manifest
    from uniforge_catalogue import roles
    from safetensors.torch import save_file
    torch.set_num_threads(2);out=ROOT/'build/cascade-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial','tests/expansion-native/cascade.cpp','tools/test_cascade.py',
        'tools/export_uniforge.py','tools/uniforge_components.py','tools/uniforge_catalogue.py','tools/spatial_portable.py','third_party/portable-sparse-source-lock.json')
    checks=[]
    def check(name,value,**extra):assert value,(name,extra);checks.append(dict(case=name,**extra))
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(p,success=True):
        file=out/'request.json';file.write_text(json.dumps(p),'utf-8')
        r=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_cascade_contract.exe',alias+'/build/cascade-tests/request.json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_'+p['operation'],(r.returncode==0)==success,error=r.stderr[-200:]);return json.loads(r.stdout) if success else None
    try:
        s=Source('D05');_,raw=s.read('uniforge3d/configs/pipeline.json');config=json.loads(raw)
        # Meta tensors validate actual full source constructors/state paths with
        # zero weight allocation and no forward pass, inference or model I/O.
        for name,construct in [('conditioner',lambda:FrozenConditioner(s)),('joint',lambda:joint(s,config['sparse_structure']['model']['args'])),('shape512',lambda:flow(s,config['structured_latent_512']['model']['args']))]:
            with torch.device('meta'):model=construct()
            check('formal_source_constructor_'+name,all(p.is_meta for p in model.parameters()),parameters=sum(p.numel() for p in model.parameters()))
            del model
        rng=np.random.default_rng(1762)
        for side,target in ((1,16),(7,32),(17,9),(33,16),(32,32),(64,19)):
            pixels=rng.integers(0,256,(side,side,3),dtype=np.uint8)
            expected=np.asarray(Image.fromarray(pixels).resize((target,target),Image.Resampling.LANCZOS))
            actual=np.asarray(native(dict(operation='resize',pixels=pixels.reshape(-1).tolist(),input=side,output=target))).reshape(target,target,3)
            check('pillow_lanczos_'+str((side,target)),np.array_equal(actual,expected),maxError=int(np.abs(actual-expected).max()))
        # Exact unchanged source triangle/AABB functions, FP32 mesh as on phone.
        _,text=s.read('uniforge3d/utils/mesh.py');tree=ast.parse(text);names={'surface_voxelize','_triangles_intersect_axis_aligned_boxes'}
        body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        env=dict(np=np);exec(compile(ast.fix_missing_locations(ast.Module(body=body,type_ignores=[])),'source-surface-SAT','exec'),env)
        for grid in (8,16,32,64):
            for case in range(3):
                v=rng.uniform(-.45,.45,(3,3)).astype(np.float32);f=np.array([[0,1,2]])
                expected=env['surface_voxelize'](v,f,grid)
                actual=np.asarray(native(dict(operation='handoff',vertices=v.tolist(),indices=f.reshape(-1).tolist(),grid=grid)))[:,1:]
                check('source_exact_SAT_'+str((grid,case)),np.array_equal(actual,expected))
        # Reference source Euler CFG formula, dense unbiased vs sparse population.
        for dense in (True,False):
            for strength in (0.,1.,3.,7.5):
                for rescale in (0.,.3,.7):
                    x,a,b=[torch.tensor(rng.normal(size=24),dtype=torch.float32) for _ in range(3)]
                    t=.713;v=b+strength*(a-b) if dense else strength*a+(1-strength)*b
                    if rescale>0 and strength not in (0,1):
                        den=1e-5+(1-1e-5)*t;xa=(1-1e-5)*x-den*a;xb=(1-1e-5)*x-den*v
                        std=lambda value:value.std(correction=1 if dense else 0)
                        scale=std(xa)/std(xb).clamp_min(1e-6);rescaled=rescale*xb*scale+(1-rescale)*xb;v=((1-1e-5)*x-rescaled)/den
                    actual=native(dict(operation='guidance',sample=x.tolist(),positive=a.tolist(),negative=b.tolist(),time=t,strength=strength,rescale=rescale,dense=dense))
                    check('source_guidance_'+str((dense,strength,rescale)),np.allclose(actual,v.numpy(),atol=2e-5,rtol=2e-5))
        coords=np.array([[0,x,y,z] for x in range(4) for y in range(4) for z in range(4)],np.int64);features=rng.uniform(0,1,(len(coords),6)).astype(np.float32)
        for drop in (False,True):
            active=coords[::2] if drop else coords;feats=features[::2] if drop else features;lookup={tuple(c):i for i,c in enumerate(active)}
            points=rng.uniform(-.55,.55,(24,3)).astype(np.float32);expected=[]
            for point in points:
                q=(point+.5)*8;base=np.floor(q-.5).astype(int);row=np.zeros(6,np.float32);total=np.float32(0)
                for k in range(8):
                    c=base+np.array([k&1,(k>>1)&1,(k>>2)&1]);index=lookup.get((0,*c))
                    if np.any(c<0) or np.any(c>=8) or index is None:continue
                    weight=np.prod(1-np.abs(q-c.astype(np.float32)-.5),dtype=np.float32);row+=weight*feats[index];total+=weight
                expected.append(row/max(total,1e-12))
            actual=native(dict(operation='volume',coords=active.tolist(),features=feats.reshape(-1).tolist(),grid=8,channels=6,points=points.tolist()))
            check('fixed_cuda_trilinear_map_'+str(drop),np.allclose(actual,expected,atol=2e-6,rtol=2e-6))
        # Immutable normalization buffers must match the selected configuration.
        class Stats(torch.nn.Module):
            def __init__(self):super().__init__();self.register_buffer('pbr_mean',torch.tensor([.3,.7]));self.weight=torch.nn.Parameter(torch.ones(2))
        model=Stats();path=out/'stats.safetensors';save_file(model.state_dict(),str(path));strict_weights(model,path);check('strict_stats_match',True)
        state=model.state_dict();state['pbr_mean']=state['pbr_mean']+.1;save_file(state,str(path))
        try:strict_weights(model,path)
        except AssertionError:check('wrong_normalization_rejected',True)
        else:raise AssertionError('Changed checkpoint stats accepted')
        # Bundle creation has all closed roles, explicit imports and no URLs.
        fixture=out/'bundle';fixture.mkdir(exist_ok=True)
        for role,name in roles().items():(fixture/name).write_bytes(b'{}' if role=='config' else b'fixture graph, not trained weights')
        manifest(fixture,dict(source={k:s.record[k] for k in ('repository','revision')},inputPolicy='explicit_rgba_foreground',surfacePolicy='raw_fdg_sat_handoff'),[])
        bundle=json.loads((fixture/'lma-bundle.json').read_text('utf-8'))
        check('bundle_all_roles',set(c['role'] for c in bundle['components'])==set(roles()))
        check('bundle_no_automatic_download',all(c['url']=='' for c in bundle['components']))
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,actualNativeCpu=True,completeModelsRun=0,phoneTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
