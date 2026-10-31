"""Pinned UniForge literal view router against the production CPU algorithm."""
import json
from pathlib import Path
import subprocess
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch
    from spatial_portable import Source
    torch.set_num_threads(2)
    out=ROOT/'build/view-router-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial/view_router.hpp','native/spatial/sparse.hpp','tests/expansion-native/sparse_graph.cpp',
                       'tools/spatial_portable.py','tools/test_view_router.py','third_party/portable-sparse-source-lock.json')
    reference=Source('D05').namespace('uniforge3d/models/view_router.py').GPUVoxelViewRouter
    checks=[]
    def check(name,ok,**details):
        assert ok,(name,details);checks.append(dict(case=name,**details))
    def sample(view,pixel,cell,confidence=1,mask=True):
        return dict(row=view*448*448+pixel,cell=cell,confidence=confidence,mask=mask)
    cases=[
        ('empty',[],[(5,5,5)],1),
        ('real_view', [sample(2,0,(5,5,5))],[(5,5,5)],3),
        ('support_before_anchor',[sample(0,0,(5,5,5),20),sample(1,0,(5,5,5),1),sample(1,1,(5,5,5),1)],[(5,5,5)],2),
        ('anchor_before_confidence',[sample(0,0,(5,5,5),1),sample(1,0,(5,5,5),9)],[(5,5,5)],2),
        ('mean_nonanchor',[sample(1,0,(5,5,5),1),sample(2,0,(5,5,5),9)],[(5,5,5)],3),
        ('lowest_real_view',[sample(1,0,(5,5,5),3),sample(2,0,(5,5,5),3)],[(5,5,5)],3),
        ('single_hop',[sample(1,0,(5,5,5))],[(6,6,6),(7,7,7),(5,5,5)],2),
        ('one_hop_anchor_priority',[sample(1,0,(5,5,5),10),sample(0,0,(7,7,7),1)],[(6,6,6)],2),
        ('disconnected_patch_support',[sample(1,0,(5,5,5)),sample(1,40,(5,5,5)),sample(0,0,(5,5,5))],[(5,5,5)],2),
        ('eight_connected_patches',[sample(1,0,(5,5,5)),sample(1,14*448+14,(5,5,5)),sample(0,0,(5,5,5))],[(5,5,5)],2),
        ('mask_reject',[sample(1,0,(5,5,5),9,False),sample(0,0,(5,5,5))],[(5,5,5)],2),
        ('stable_top95',[sample(1,i,(5,5,5),2) for i in range(19)]+[sample(1,19,(20,20,20),1)],[(20,20,20),(5,5,5)],2),
    ]
    alias=next((c+':' for c in 'UVWXYZRT' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    try:
        for grid in (32,64):
            for name,samples,targets,views in cases:
                points=torch.zeros(1,views,448,448,3);confidence=torch.zeros(1,views,448,448);mask=torch.zeros_like(confidence,dtype=torch.bool)
                payload=[]
                for s in samples:
                    p=[(c+.5)/grid-.5 for c in s['cell']];row=s['row']
                    points.reshape(-1,3)[row]=torch.tensor(p);confidence.reshape(-1)[row]=s['confidence'];mask.reshape(-1)[row]=s['mask']
                    payload.append(dict(row=row,point=p,confidence=s['confidence'],mask=s['mask']))
                coords=torch.tensor([[0,*c] for c in targets]);router=reference(grid_resolution=grid,patch_grid_size=grid)
                value=router(points,confidence,mask,coords)['selected_view'];expected=value[coords[:,0],coords[:,1],coords[:,2],coords[:,3]].tolist()
                request=dict(operation='view_router',views=views,grid=grid,samples=payload,targets=coords.tolist())
                file=out/'request.json';file.write_text(json.dumps(request),'utf-8')
                native=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/build/view-router-tests/request.json'],capture_output=True,text=True,timeout=30)
                check('native_'+str((grid,name)),native.returncode==0,stderr=native.stderr[-200:])
                check('literal_source_'+str((grid,name)),json.loads(native.stdout)==expected,expected=expected)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,literalSource=True,completeModelsRun=0,phoneTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
