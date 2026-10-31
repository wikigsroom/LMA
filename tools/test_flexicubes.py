"""Bounded literal publisher FlexiCubes vs signed CPU extraction, no models."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import types
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import numpy as np
    import torch
    from spatial_portable import Source
    from flexicubes_tables import tables,render
    torch.set_num_threads(2);torch.manual_seed(19321)
    source=Source('D08');prefix='sam3d_objects/model/backbone/tdfy_dit/representations/mesh/'
    table_values,digest=tables()
    class Dict(dict):__getattr__=dict.__getitem__
    namespace=dict(torch=torch,edict=Dict,SparseTensor=object,check_tensor=lambda t,s,throw=False:len(t.shape)==len(s) and all(b is None or a==b for a,b in zip(t.shape,s)))
    namespace.update(table_values)
    for rel in ('utils_cube.py','flexicubes/flexicubes.py','cube2mesh.py'):
        path,text=source.read(prefix+rel);tree=ast.parse(text)
        body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) or (rel=='utils_cube.py' and isinstance(n,ast.Assign))]
        exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),namespace)
    inputs=fingerprint('native/spatial/flexicubes.hpp','native/spatial/flexicubes_tables.hpp','native/spatial/sparse.hpp',
        'tests/expansion-native/sparse_graph.cpp','tools/flexicubes_tables.py','tools/test_flexicubes.py','third_party/portable-sparse-source-lock.json')
    out=ROOT/'build/flexicubes-tests';out.mkdir(exist_ok=True);checks=[]
    def check(name,ok,**details):assert ok,(name,details);checks.append(dict(case=name,**details))
    check('reproducible_signed_tables',(ROOT/'native/spatial/flexicubes_tables.hpp').read_bytes()==render().encode())
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(case,ok=True):
        (out/'request.json').write_text(json.dumps(case),'utf-8')
        run=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/build/flexicubes-tests/request.json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_accept' if ok else 'native_reject',(run.returncode==0)==ok,reason=run.stderr[-300:])
        return json.loads(run.stdout) if ok else None
    def compare(name,a,b):
        a=np.asarray(a);b=b.detach().numpy()
        check(name,a.shape==b.shape and np.allclose(a,b,rtol=1e-5,atol=3e-7),shape=list(a.shape),maxError=float(np.max(np.abs(a-b))) if a.size and a.shape==b.shape else None)
    try:
        for grid in (4,7,11):
            allcoords=torch.tensor([[x,y,z] for x in range(grid) for y in range(grid) for z in range(grid)],dtype=torch.int32)
            for channels in (53,101):
                for mode in ('sphere','random','missing','ambiguous','gamma_tie'):
                    coords=allcoords
                    if mode=='missing':coords=coords[torch.rand(len(coords))>.48]
                    features=torch.randn(len(coords),channels)*.18
                    if mode in ('sphere','missing','gamma_tie'):
                        cp=coords[:,None,:]+namespace['cube_corners'][None,:,:]
                        sdf=torch.linalg.norm(cp.float()/grid-.5,dim=-1)-.32
                        features[:,:8]=sdf+1/grid
                    else:features[:,:8]=torch.randn(len(coords),8)*.7+1/grid
                    if mode=='ambiguous':
                        # All checkerboard cases exercise adjacent ambiguous-face inversion.
                        cp=coords[:,None,:]+namespace['cube_corners'][None,:,:]
                        features[:,:8]=((cp.sum(-1)%2).float()*2-1)*.3+1/grid
                    if mode=='gamma_tie':features[:,52]=0
                    reference=namespace['SparseFeatures2Mesh'](device='cpu',res=grid,use_color=channels==101)
                    value=types.SimpleNamespace(coords=torch.nn.functional.pad(coords,(1,0)),feats=features.clone())
                    expected=reference(value,training=False)
                    case=dict(operation='flexicubes',grid=grid,channels=channels,coords=value.coords.tolist(),fields=features.flatten().tolist(),maxTriangles=1000000)
                    actual=native(case);label=str((grid,channels,mode))
                    compare('source_vertices_'+label,actual['vertices'],expected.vertices)
                    check('source_faces_'+label,actual['faces']==expected.faces.flatten().tolist())
                    if channels==101:compare('source_six_attributes_'+label,actual['colors'],expected.vertex_attrs)
                    else:check('source_no_invented_color_'+label,actual['colors']==[])
        for name,change in (
            ('duplicate',lambda p:p['coords'].__setitem__(1,p['coords'][0])),
            ('multibatch',lambda p:p['coords'][0].__setitem__(0,1)),
            ('outside_grid',lambda p:p['coords'][0].__setitem__(1,p['grid'])),
            ('negative_coordinate',lambda p:p['coords'][0].__setitem__(1,-1)),
            ('nonfinite',lambda p:p['fields'].__setitem__(0,float('nan'))),
            ('bad_width',lambda p:p.__setitem__('channels',54)),
            ('budget',lambda p:p.__setitem__('maxTriangles',1)),
            ('empty',lambda p:(p.__setitem__('coords',[]),p.__setitem__('fields',[]))),
            ('no_surface',lambda p:p.__setitem__('fields',[1]*len(p['fields']))),
        ):
            bad=copy.deepcopy(case);change(bad);native(bad,False);check(name,True)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,literalPublisherSource=True,sourceRevision=source.record['revision'],tablesSha256=digest,
        denseStorageReplacedByExactSparseCandidates=True,completeModelsRun=0,physicalDeviceTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
