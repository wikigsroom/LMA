"""Literal pinned FDG inference with a CPU hash versus production C++ topology.

Only bounded constructed fields are used. No learned model or device is run.
"""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import types
from evidence import ROOT, fingerprint, current
from fdg_reference import source, SHA256, REVISION


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import numpy as np
    import torch
    inputs=fingerprint('native/spatial/fdg.hpp','native/spatial/sparse.hpp','tests/expansion-native/sparse_graph.cpp',
                       'tools/fdg_reference.py','tools/test_fdg.py')
    out=ROOT/'build/fdg-tests';out.mkdir(exist_ok=True)
    # Execute the exact upstream function body. Replace only the CUDA hash,
    # not the quad construction, source FP32 arithmetic or diagonal decision.
    class Hash:
        @staticmethod
        def hashmap_insert_3d_idx_as_val_cuda(table,coords,*grid):
            table.update({tuple(c):i for i,c in enumerate(coords.tolist())})
        @staticmethod
        def hashmap_lookup_3d_cuda(table,coords,*grid):
            return torch.tensor([table.get(tuple(c),-1) for c in coords.tolist()],dtype=torch.int64)
    namespace=dict(torch=torch,np=np,Union=__import__('typing').Union,_C=Hash,
                   _init_hashmap=lambda *a,**kw:({},))
    tree=ast.parse(source());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='flexible_dual_grid_to_mesh')
    exec(compile(ast.Module(body=[node],type_ignores=[]),'literal-pinned-fdg','exec'),namespace)
    literal=namespace[node.name]
    checks=[]
    def check(name,ok,**details):
        assert ok,(name,details);checks.append(dict(case=name,**details))
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(case,ok=True):
        path=out/'request.json';path.write_text(json.dumps(case),'utf-8')
        r=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/build/fdg-tests/request.json'],
                         capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_accept' if ok else 'native_reject',(r.returncode==0)==ok,reason=r.stderr[-200:])
        return json.loads(r.stdout) if ok else None
    torch.manual_seed(8821)
    try:
        for grid in (2,16,1024):
            coords=torch.tensor([[x,y,z] for x in range(2) for y in range(2) for z in range(2)],dtype=torch.int32)
            for mode in ('ties','02','13','mixed','near_tie','missing_neighbors'):
                c=coords[:-1] if mode=='missing_neighbors' else coords
                v=torch.rand(len(c),3);flags=torch.ones(len(c),3,dtype=torch.bool)
                weights=torch.ones(len(c),1)
                if mode=='02':weights[0]=4
                elif mode=='13':weights[1]=4
                elif mode=='mixed':weights=torch.rand(len(c),1)+.1
                elif mode=='near_tie':
                    weights[0]=float(np.float32(1.0000001192092896));weights[3]=float(np.float32(.9999998807907104))
                expected_v,expected_f=literal(c,v,flags,weights,[[-.5]*3,[.5]*3],grid_size=grid,train=False)
                case=dict(operation='dual_grid',coords=[[0]+row for row in c.tolist()],vertices=v.flatten().tolist(),
                          flags=flags.int().flatten().tolist(),weights=weights.flatten().tolist(),grid=grid,maxTriangles=1000)
                actual=native(case)
                check('source_vertices_'+str((grid,mode)),np.allclose(actual['vertices'],expected_v.numpy(),rtol=1e-6,atol=1e-7))
                check('source_faces_'+str((grid,mode)),actual['faces']==expected_f.flatten().tolist())
        # Closed model ABI: bounds, uniqueness, one batch, finite values,
        # positive diagonal confidence, connected output and triangle budget.
        for name,change in (
            ('duplicate',lambda p:p['coords'].__setitem__(1,p['coords'][0])),
            ('batch',lambda p:p['coords'][0].__setitem__(0,1)),
            ('outside_grid',lambda p:p['coords'][0].__setitem__(1,p['grid'])),
            ('negative_coord',lambda p:p['coords'][0].__setitem__(1,-1)),
            ('nonfinite',lambda p:p['vertices'].__setitem__(0,float('nan'))),
            ('nonpositive',lambda p:p['weights'].__setitem__(0,0)),
            ('bad_flag',lambda p:p['flags'].__setitem__(0,2)),
            ('disconnected',lambda p:p.__setitem__('flags',[0]*len(p['flags']))),
            ('triangle_budget',lambda p:p.__setitem__('maxTriangles',1)),
        ):
            bad=copy.deepcopy(case);change(bad);native(bad,False);check(name,True)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,referenceRevision=REVISION,referenceSha256=SHA256,
                literalSourceFunction=True,cudaHashReplacedOnly=True,completeModelsRun=0,physicalDeviceTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')
    print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))


if __name__=='__main__':main()
