"""Analytic source-kernel FDG voxelization/QR fixtures; no trained model."""
import copy
import json
from pathlib import Path
import subprocess
from evidence import ROOT,fingerprint,current


def main():
    out=ROOT/'build/fdg-mesh-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial/fdg_mesh.hpp','native/spatial/fdg.hpp','native/spatial/sparse.hpp',
        'tools/test_fdg_mesh.py','tools/prepare_fdg_cpu.py','tests/expansion-native/sparse_graph.cpp','build/fdg-cpu-source')
    checks=[]
    def check(name,ok,**extra):
        assert ok,(name,extra);checks.append(dict(case=name,**extra))
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(request,ok=True):
        file=out/'request.json';file.write_text(json.dumps(request),'utf-8')
        p=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/build/fdg-mesh-tests/request.json'],
                          capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_'+request['operation'],(p.returncode==0)==ok,error=p.stderr[-200:])
        return json.loads(p.stdout) if ok else None
    try:
        for grid in (8,16,32):
            for axis in (0,1,2):
                verts=[]
                for a,b in ((-.31,-.29),(.33,-.29),(.33,.32),(-.31,.32)):
                    v=[0.,0.,0.];v[axis]=.07;v[(axis+1)%3]=a;v[(axis+2)%3]=b;verts.append(v)
                request=dict(operation='mesh_to_dual_grid',vertices=verts,indices=[0,1,2,0,2,3],grid=grid)
                result=native(request);coords=result['coords'];offsets=result['vertices'];flags=result['flags']
                check('unique_surface_'+str((grid,axis)),len({tuple(c) for c in coords})==len(coords) and len(coords)>4)
                positions=[[(c[j+1]+offsets[i*3+j])/grid-.5 for j in range(3)] for i,c in enumerate(coords)]
                check('analytic_plane_'+str((grid,axis)),all(abs(p[axis]-.07)<2e-5 for p in positions))
                check('constrained_voxel_offsets_'+str((grid,axis)),all(0<=v<=1 for v in offsets))
                check('source_edge_axis_'+str((grid,axis)),any(flags[i*3+axis] for i in range(len(coords))) and all(not flags[i*3+j] for i in range(len(coords)) for j in range(3) if j!=axis))
                reconstructed=native(dict(operation='dual_grid',coords=coords,vertices=offsets,flags=flags,weights=[1]*len(coords),grid=grid,maxTriangles=100000))
                check('connected_planar_mesh_'+str((grid,axis)),len(reconstructed['faces'])>=6 and all(abs(p[axis]-.07)<2e-5 for p in reconstructed['vertices']))
        vertices=[[x,y,z] for x in (-.3,.3) for y in (-.3,.3) for z in (-.3,.3)]
        indices=[0,1,3,0,3,2,4,6,7,4,7,5,0,4,5,0,5,1,2,3,7,2,7,6,0,2,6,0,6,4,1,5,7,1,7,3]
        request=dict(operation='mesh_to_dual_grid',vertices=vertices,indices=indices,grid=16);result=native(request)
        actual=[[(c[j+1]+result['vertices'][i*3+j])/16-.5 for j in range(3)] for i,c in enumerate(result['coords'])]
        for axis in range(3):
            check('cube_min_'+str(axis),abs(min(p[axis] for p in actual)+.3)<2e-5)
            check('cube_max_'+str(axis),abs(max(p[axis] for p in actual)-.3)<2e-5)
        for name,change in (
            ('outside_cube',lambda p:p['vertices'][0].__setitem__(0,.5)),
            ('bad_index',lambda p:p['indices'].__setitem__(0,100)),
            ('bad_grid',lambda p:p.__setitem__('grid',2048)),
            ('degenerate',lambda p:p.__setitem__('indices',[0,0,0])),
            ('bad_triangle_count',lambda p:p.__setitem__('indices',[0,1])),
        ):
            bad=copy.deepcopy(request);change(bad);native(bad,False);check(name,True)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    record=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,publisherCpuKernel=True,eigenMplOnly=True,
                completeModelsRun=0,phoneTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(record,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
