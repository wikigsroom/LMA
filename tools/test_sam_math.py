"""Pinned source SAM ODE/CFG and MV head-mean patch entropy contracts."""
import ast
import copy
import functools
import json
import math
from pathlib import Path
import subprocess
import sys
import types
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch
    import numpy as np
    from spatial_portable import Source
    torch.set_num_threads(2);torch.manual_seed(45091)
    inputs=fingerprint('native/spatial/sam_math.hpp','native/spatial/sparse.hpp','tests/expansion-native/sparse_graph.cpp',
        'tools/test_sam_math.py','third_party/portable-sparse-source-lock.json')
    source=Source('D09');base='sam3d_objects/'
    namespace=dict(torch=torch,np=np,math=math,partial=functools.partial,logger=types.SimpleNamespace(info=lambda *a:None,debug=lambda *a:None,warning=lambda *a:None))
    def literal(relative,names):
        path,text=source.read(base+relative);tree=ast.parse(text)
        body=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
        assert {n.name for n in body}==set(names)
        code=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+body,type_ignores=[])
        exec(compile(ast.fix_missing_locations(code),str(path),'exec'),namespace)
    literal('pipeline/multi_view_weighted.py',['compute_ss_entropy_weights'])
    literal('utils/latent_weighting.py',['compute_patch_entropy','weighted_fusion'])
    namespace.update(SLAT_CONDITION_LAYOUT={'image_cropped':(0,1374)},PATCH_START=5,PATCH_END=1374)
    literal('model/backbone/generator/flow_matching/solver.py',['linear_approximation_step','ODESolver','Euler','Midpoint','RungeKutta4'])
    namespace['tree_tensor_map']=lambda fn,*args:fn(*args)
    out=ROOT/'build/sam-math-tests';out.mkdir(exist_ok=True);checks=[]
    def check(name,ok,**details):assert ok,(name,details);checks.append(dict(case=name,**details))
    def compare(name,a,b,atol=3e-6):
        a=np.asarray(a);b=b.detach().numpy() if hasattr(b,'detach') else np.asarray(b)
        check(name,a.shape==b.shape and np.allclose(a,b,rtol=3e-5,atol=atol),error=float(np.max(np.abs(a-b))) if a.shape==b.shape else None)
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(case,ok=True):
        (out/'request.json').write_text(json.dumps(case),'utf-8');r=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/build/sam-math-tests/request.json'],capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_accept' if ok else 'native_reject',(r.returncode==0)==ok,reason=r.stderr[-500:]);return json.loads(r.stdout) if ok else None
    try:
        for begin,end,keys in ((1,1370,1500),(5,1374,5496),(3,13,19)):
            queries,heads,width=7,3,8;attention={};views=[]
            for v in range(3):
                q=torch.randn(queries,heads,width)*(v+1);k=torch.randn(keys,heads,width)
                scores=torch.einsum('qhd,khd->hqk',q,k)/math.sqrt(width)
                attention[v]=scores.softmax(-1).mean(0)[None]
                views.append(dict(q=q.flatten().tolist(),k=k.flatten().tolist()))
            expected=namespace['compute_ss_entropy_weights'](attention,alpha=60,min_weight=.001,patch_start=begin,patch_end=end)
            case=dict(operation='sam_entropy',views=views,queries=queries,keys=keys,heads=heads,width=width,begin=begin,end=end,alpha=60,temperature=1,minimum=.001)
            actual=native(case);compare('source_ss_fusion_weights',actual['weights'],expected)
            reference=[]
            for v in range(3):
                p=attention[v][0,:,begin:end];p=p/p.sum(-1,keepdim=True).clamp(min=1e-10)
                reference.append((-(p*torch.log(p+1e-10)).sum(-1)/math.log(end-begin)).tolist())
            compare('source_head_mean_entropy',actual['entropy'],reference)
            if begin==5:
                expected_entropy=[namespace['compute_patch_entropy'](attention[v]) for v in range(3)]
                compare('source_slat_entropy',actual['entropy'],torch.stack(expected_entropy))
            # Join the actual source pooling coordinates, including reordered
            # coarse rows; original row order must survive exact expansion.
            coarse=[[0,0,i,0] for i in range(queries)][::-1];original=[[0,1,2*i+1,0] for i in range(queries)]
            case.update(coarse=coarse,original=original,factor=2)
            actual=native(case);compare('source_pool_inverse_weight_expansion',actual['expanded'],expected.flip(1))
        for solver,cls in [('euler','Euler'),('midpoint','Midpoint'),('rk4','RungeKutta4')]:
            for reverse in (False,True):
                for shortcut in (False,True):
                    p=dict(steps=7,rescale=2.3,timeScale=1000,reversed=reverse,shortcut=shortcut,noShortcut=False,solver=solver)
                    x=torch.randn(11);times=np.linspace(0,1,8);times=times/(1+(p['rescale']-1)*(1-times));times=1-times if reverse else times
                    calls=[];d=1000/7 if shortcut else 0
                    def dynamics(value,t):
                        t=torch.tensor(float(t)*1000,dtype=torch.float32);calls.append([float(t),d]);return torch.sin(t*.001+.17)+value*.035+d*.0002
                    expected=namespace[cls]().solve(dynamics,x.clone(),times)
                    actual=native(dict(operation='sam_schedule',schedule=p,state=x.tolist()))
                    compare('source_ode_'+solver,actual['state'],expected)
                    compare('source_time_shortcut_'+solver,actual['calls'],np.asarray(calls),atol=1e-4)
        for pointmap in (False,True):
            a,b,c=(torch.randn(17) for _ in range(3));s,pm=3.4,1.2
            actual=native(dict(operation='sam_cfg',conditional=a.tolist(),unconditional=b.tolist(),withoutPoints=c.tolist(),strength=s,pointStrength=pm,pointmapCfg=pointmap))
            expected=a+pm*(a-c)+s*(c-b) if pointmap else (1+s)*a-s*b
            compare('source_cfg',actual,expected)
        bad=copy.deepcopy(case);bad['end']=bad['begin']+1;native(bad,False)
        bad=copy.deepcopy(case);bad['original'][0]=[0,999,999,999];native(bad,False)
        bad=copy.deepcopy(case);bad['temperature']=0;native(bad,False)
        bad=copy.deepcopy(case);bad['views'][0]['q'][0]=float('nan');native(bad,False)
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    (out/'results.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,physicalDeviceTests=0),indent=2)+'\n','utf-8')
    print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
