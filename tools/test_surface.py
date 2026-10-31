"""Original-source adaptive grids, actual Lewiner and DISO forward parity."""
import sys
import ast,contextlib,hashlib,io,json,os,re,subprocess,typing
from pathlib import Path
from evidence import ROOT,current,fingerprint
from fetch_surface_sources import verify
OUT=ROOT/'build/surface-tests'


def definitions():
    import torch,numpy as np,scipy
    from skimage import measure
    path=ROOT/'build/surface-source-review/RF_TRIPO/triposg/inference_utils.py'
    tree=ast.parse(path.read_text('utf-8'))
    names=['generate_dense_grid_points_gpu','find_candidates_band','expand_edge_region_fast','parallel_zoom','hierarchical_extract_geometry','extract_near_surface_volume_fn','generate_dense_grid_points_2','flash_extract_geometry']
    selected=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
    assert len(selected)==len(names)
    # The only device edit replaces the allocator's hardcoded CUDA device;
    # no learned math, mask, index or interpolation statement is changed.
    class CPU(ast.NodeTransformer):
        def visit_Constant(self,node):return ast.copy_location(ast.Constant('cpu'),node) if node.value=='cuda' else node
    tree=ast.fix_missing_locations(CPU().visit(ast.Module(selected,type_ignores=[])))
    from einops import repeat
    scope=dict(repeat=repeat,torch=torch,np=np,nn=torch.nn,F=torch.nn.functional,scipy=scipy,measure=measure,**vars(typing))
    exec(compile(tree,str(path),'exec'),scope)
    return scope


def main():
    sys.path[:0]=[str(ROOT/"build/shape-reference-python"),str(ROOT/"build/spatial-reference-python")]
    import numpy as np,torch
    from skimage import measure
    torch.set_num_threads(2);verify()
    inputs=fingerprint('native/rf_shape','tests/expansion-native/surface.cpp','tools/test_surface.py','tools/prepare_surface_cpu.py','tools/fetch_surface_sources.py','third_party/surface-source-lock.json')
    receipt=json.loads((ROOT/'build/shape-worker-host/receipt.json').read_text('utf-8'));current(receipt['source_inputs'])
    OUT.mkdir(exist_ok=True);checks=[];drive=next(c+':' for c in 'RTUVWXYZ' if not Path(c+':/').exists());subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    def path(p):return drive+'/'+p.relative_to(ROOT).as_posix()
    def run(request,ok=True):
        file=OUT/'request.json';file.write_text(json.dumps(request,allow_nan=True),'utf-8')
        p=subprocess.run([path(ROOT/'build/shape-worker-host/bin/lma_surface_contract.exe'),path(file)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        assert (p.returncode==0)==ok,(p.stdout[:1000],p.stderr[:1000]);return json.loads(p.stdout) if ok else None
    try:
        # Actual skimage oracle, not another rewritten cube-case routine.
        for n in [7,11]:
            x,y,z=np.meshgrid(*([np.linspace(-1,1,n,dtype='float32')]*3),indexing='ij')
            for name,field in [('sphere',.41-x*x-y*y-z*z),('plane',x+.3*y-.2*z+.017),('saddle',x*x-y*y+.33*z+.019)]:
                v,f,_,_=measure.marching_cubes(field,0,method='lewiner')
                got=run(dict(operation='mc',field=field.flatten().tolist(),n=n,divisor=n-1))
                nv=np.asarray(got['vertices'])*(n-1)/2+(n-1)/2;nf=np.asarray(got['indices']).reshape(-1,3)
                # Original C++ and Cython enumerate vertices in different
                # orders. Match their geometric triangle multisets.
                from scipy.spatial import cKDTree
                distance,mapping=cKDTree(v).query(nv)
                assert float(distance.max())<=2e-5 and len(set(mapping))==len(v)==len(nv),(n,name,float(distance.max()))
                assert {tuple(sorted(map(int,t))) for t in f}=={tuple(sorted(map(int,mapping[t]))) for t in nf},(n,name,len(v),len(nv),len(f),len(nf))
                expected=np.sum(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])*(v[f].mean(1)),axis=1).sum()
                actual=np.sum(np.cross(nv[nf[:,1]]-nv[nf[:,0]],nv[nf[:,2]]-nv[nf[:,0]])*(nv[nf].mean(1)),axis=1).sum()
                assert np.sign(expected)==np.sign(actual),(name,expected,actual)
                checks.append('lewiner_actual_skimage_'+name+'_'+str(n))
        scope=definitions()
        for box in [1.,1.005]:
            for name in ['sphere','plane']:
                request=dict(operation='volume',mode='publisher_octree',depth=5,dense=3,chunk=137,box=box,function=name)
                got=run(request);observed=[]
                def geometry(points):
                    x,y,z=points.unbind(-1);v=.5-x*x-y*y-z*z if name=='sphere' else x+.375*y-.2*z+.03125
                    observed.append((points.detach().clone(),v.detach().clone()));return v.unsqueeze(-1)
                with contextlib.redirect_stdout(io.StringIO()):scope['hierarchical_extract_geometry'](geometry,torch.device('cpu'),bounds=box,dense_octree_depth=3,hierarchical_octree_depth=5)
                # Obtain the original function's final field by replacing
                # only its external mesher, not its adaptive query stages.
                class Capture:
                    @staticmethod
                    def marching_cubes(field,*args,**kwargs):Capture.field=field.copy();raise ValueError('captured field')
                original=scope['measure'];scope['measure']=Capture
                with contextlib.redirect_stdout(io.StringIO()):scope['hierarchical_extract_geometry'](geometry,torch.device('cpu'),bounds=box,dense_octree_depth=3,hierarchical_octree_depth=5)
                scope['measure']=original
                actual=np.array(got['values'],dtype='float32').reshape(got['size'],got['size'],got['size'])
                expected=Capture.field
                # FP32 query ABI is intentional; source queries/field use
                # FP16. Compare with a disclosed tolerance, never alter it
                # automatically to accept an index or schedule mismatch.
                error=float(np.max(np.abs(actual-expected)))
                assert error<=.016,(box,name,error)
                checks.append(dict(case='original_octree_'+name+'_'+str(box),maxAbsoluteError=error,limit=.016,sourceQueryDtype='float16',onnxQueryDtype='float32'))
        # Execute the original Flash query/refinement function on CPU and
        # capture only its external DMC call, retaining masks and query order.
        import types
        for depth in [6,7]:
            for name in ['sphere','plane']:
                class DMC:
                    def __init__(self,**kwargs):pass
                    def to(self,*a):return self
                    def __call__(self,sdf,**kwargs):DMC.field=-sdf.numpy()*32;raise ValueError('captured source DMC input')
                class Decoder:
                    def set_topk(self,value):assert value is False
                class VAE:
                    decoder=Decoder()
                    def decode(self,latents,points):
                        x,y,z=points.unbind(-1);v=.5-x*x-y*y-z*z if name=='sphere' else x+.375*y-.2*z+.03125
                        return types.SimpleNamespace(sample=v.unsqueeze(-1))
                scope['DiffDMC']=DMC
                with contextlib.redirect_stdout(io.StringIO()):scope['flash_extract_geometry'](torch.zeros(1,2,2),VAE(),bounds=1.,num_chunks=389,octree_depth=depth)
                got=run(dict(operation='volume',mode='publisher_flash',depth=depth,dense=5,chunk=389,box=1.,function=name));actual=np.asarray(got['values'],dtype='float32').reshape([got['size']]*3);expected=DMC.field
                actual=actual*(-(1<<depth));np.testing.assert_array_equal(np.isnan(actual),np.isnan(expected));np.testing.assert_allclose(actual,expected,atol=3e-6,rtol=3e-6,equal_nan=True)
                checks.append('original_flash_'+name+'_'+str(depth))
        # DISO source-table forward oracle. No CUDA code or GPU is invoked.
        source=(ROOT/'build/surface-source-review/DISO/src/cudualmc.cu').read_text('utf-8')
        def table(name):
            m=re.search(r'__constant__\s+[^;=]*\b'+name+r'\s*(?:\[[^]]*\])+\s*=\s*(\{.*?\});',source,re.S);assert m,name
            text=re.sub(r'//[^\n]*','',m[1]);return ast.literal_eval(text.replace('{','[').replace('}',']'))
        corners,locations,patches,edges,edge_ids,problem,offset,quad=[table(k) for k in ['mcCorners','mcEdgeLocations','mcFirstPatchIndex','mcFirstEdgeIndex','mcEdgeIndex','problematicConfigs','dmcEdgeOffset','dmcQuad']]
        def diso(field):
            data=np.pad(field,1,constant_values=1);shape=data.shape;cells={};vertices=[]
            def code(x,y,z):return sum((int(data[x+a,y+b,z+c]>=0)<<i) for i,(a,b,c) in enumerate(corners))
            for x in range(shape[0]-1):
                for y in range(shape[1]-1):
                    for z in range(shape[2]-1):
                        c=code(x,y,z)
                        if c in [0,255]:continue
                        direction=problem[c];neighbor=[x,y,z]
                        if direction!=255:
                            axis=direction>>1;neighbor[axis]+=1 if direction&1 else -1
                            if 0<=neighbor[axis]<shape[axis]-1 and problem[code(*neighbor)]!=255:c^=255
                        cells[x,y,z]=(c,len(vertices))
                        for patch in range(patches[c],patches[c+1]):
                            points=[]
                            for e in edge_ids[edges[patch]:edges[patch+1]]:
                                a,b,cc,dim=locations[e];p=np.array([x+a,y+b,z+cc],dtype='float32');end=p.copy();end[dim]+=1;d0=data[tuple(p.astype(int))];d1=data[tuple(end.astype(int))];t=np.float32(np.clip(-d0/(d1-d0),0,1)) if d0!=d1 else np.float32(.5);points.append(p+(end-p)*t)
                            vertices.append(np.sum(points,axis=0,dtype='float32')/np.float32(len(points))-1)
            quads=[]
            for (x,y,z),(c,first) in cells.items():
                d0=data[x,y,z]
                for dim in range(3):
                    other=[x,y,z];other[dim]+=1;d=data[tuple(other)];enter=d0<0<=d;leave=d<0<=d0
                    if enter or leave:
                        face=[]
                        for dx,dy,dz,e in quad[(3 if leave else 0)+dim]:
                            cell=cells[x+dx,y+dy,z+dz];face.append(cell[1]+offset[cell[0]][e])
                        quads.append(face)
            vertices=np.array(vertices,dtype='float32');quads=torch.tensor(quads);v=torch.from_numpy(vertices)
            a1,a2=[],[]
            for configs,dest in [([[0,1,3],[1,2,3]],a1),([[0,1,2],[0,2,3]],a2)]:
                for face in configs:
                    p,q,r=torch.unbind(v[quads[:,face]],dim=-2);dest.append(torch.stack([(torch.nn.functional.normalize(q-p,dim=-1)*torch.nn.functional.normalize(r-p,dim=-1)).sum(-1),(torch.nn.functional.normalize(r-q,dim=-1)*torch.nn.functional.normalize(p-q,dim=-1)).sum(-1),(torch.nn.functional.normalize(p-r,dim=-1)*torch.nn.functional.normalize(q-r,dim=-1)).sum(-1)],-1).max(-1).values)
            a1,a2=torch.stack(a1,-1).max(-1).values,torch.stack(a2,-1).max(-1).values
            f=torch.cat((quads[a1<a2][:,[0,1,3,1,2,3]].reshape(-1,3),quads[a1>=a2][:,[0,1,2,0,2,3]].reshape(-1,3)),0)
            return vertices,f.numpy()[:,::-1]
        for case in ['sphere','random','ambiguous']:
            n=5;x,y,z=np.meshgrid(*([np.linspace(-1,1,n,dtype='float32')]*3),indexing='ij')
            field=x*x+y*y+z*z-.51 if case=='sphere' else np.random.default_rng(468 if case=='random' else 99).normal(size=(n,n,n)).astype('float32')
            expected_v,expected_f=diso(field);got=run(dict(operation='dmc',field=field.flatten().tolist(),n=n,divisor=n-1));v=np.asarray(got['vertices'])*(n-1)/2+(n-1)/2;f=np.array(got['indices']).reshape(-1,3)
            np.testing.assert_allclose(v,expected_v,rtol=1e-6,atol=2e-6)
            # CPU angle FP32 can choose a different equal-angle diagonal.
            # Keep exact source triangles wherever the decision is unequal;
            # verify manifold edges, total area and orientation separately.
            assert len(f)==len(expected_f)
            edges_count={}
            for face in f:
                for a,b in [(face[0],face[1]),(face[1],face[2]),(face[2],face[0])]:k=tuple(sorted((int(a),int(b))));edges_count[k]=edges_count.get(k,0)+1
            assert set(edges_count.values())=={2},case
            def geometric_measures(verts,faces):
                a,b,c=verts[faces].transpose(1,0,2);normal=np.cross(b-a,c-a)
                return np.linalg.norm(normal,axis=1).sum()/2,(a*np.cross(b,c)).sum()/6
            np.testing.assert_allclose(geometric_measures(v,f),geometric_measures(expected_v,expected_f),rtol=2e-5,atol=2e-5)

            checks.append('actual_diso_forward_'+case)
        for mode in ['publisher_octree','publisher_flash']:
            data=run(dict(operation='volume',mode=mode,depth=6,dense=5,chunk=389,box=1.,function='sphere'))
            field=[-10000 if v is None else v for v in data['values']]
            if mode=='publisher_flash':
                # NaN unknown cells are source sentinels; with a compact sphere
                # all sign-changing edges have actual finite queried endpoints.
                field=[1. if v==-10000 else v for v in field]
            mesh=run(dict(operation='dmc' if mode=='publisher_flash' else 'mc',field=field,n=data['size'],divisor=data['divisor']))
            assert mesh['indices'];checks.append(mode+'_surface_program')
        for operation in ['mc','dmc']:
            run(dict(operation=operation,field=[1.]*27,n=3,divisor=2),False);checks.append(operation+'_empty_field_rejects')
        current(inputs);current(receipt['source_inputs'])
        report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModels=0,phoneTests=0,virtualization=False)
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModels=0)))
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
