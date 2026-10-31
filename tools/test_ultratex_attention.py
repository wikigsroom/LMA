"""Actual native ORT block attention vs independent program/source oracles."""
import ast,hashlib,json,os,subprocess,sys,warnings
from pathlib import Path
from evidence import fingerprint,current
from spatial_reference import ROOT,read
OUT=ROOT/'build/ultratex-attention-tests'


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch,onnx,numpy as np
    from ultratex_attention import Attention,selected,BlockSparseAttention
    torch.set_num_threads(2);torch.manual_seed(9871);OUT.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial','tools/test_ultratex_attention.py','tools/ultratex_attention.py','tools/spatial_reference.py','third_party/spatial-shape-source-lock.json','tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(label,ok,**details):assert ok,(label,details);checks.append(dict(case=label,**details))
    # Only this named, pinned source function executes. Its Triton pool is
    # replaced by an independent tensor reduction; no upstream package import.
    path,source=read('D04','ultratex/sparse_attention/utils.py');tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='get_block_map')
    def pool(x,n):return torch.stack([x[...,i:i+n,:].sum(-2)/min(n,x.shape[-2]-i) for i in range(0,x.shape[-2],n)],-2)
    namespace=dict(torch=torch,mean_pool=pool)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(file,args,success=True):
        request=dict(graph=alias+'/'+file.relative_to(ROOT).as_posix(),inputs=[dict(name=n,dtype='float32' if t.dtype==torch.float32 else 'int64',shape=list(t.shape),values=t.flatten().tolist()) for n,t in zip(('q','k','v','policy'),args)])
        f=OUT/'request.json';f.write_text(json.dumps(request),'utf-8')
        r=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',alias+'/'+f.relative_to(ROOT).as_posix()],capture_output=True,text=True,encoding='utf-8',timeout=30)
        check('native_accept' if success else 'native_reject',(r.returncode==0)==success,error=r.stderr[-400:])
        if success:
            v=json.loads(r.stdout)[0];return np.array(v['values']).reshape(v['shape'])
    try:
        class Wrapper(torch.nn.Module):
            def forward(self,q,k,v,policy):return torch.ops.lma_ultratex_export.block_attention(q,k,v,policy)
        args=[torch.randn(1,2,33,8) for _ in range(3)]+[torch.tensor([7,5,500000,0])]
        graph=OUT/'block-attention.onnx'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');torch.onnx.export(Wrapper(),tuple(args),graph,input_names=['q','k','v','policy'],output_names=['out'],dynamic_axes={n:{0:'B',1:'H',2:'L',3:'D'} for n in ('q','k','v','out')},opset_version=17,custom_opsets={'lma.spatial':1},dynamo=False,external_data=False)
        model=onnx.load(str(graph));onnx.checker.check_model(model);check('signed_in_custom_domain',len(model.graph.node)==1 and model.graph.node[0].domain=='lma.spatial')
        for length,qb,kb,ratio in [(33,7,5,.5),(67,16,8,.2),(17,7,4,1),(128,128,16,.2),(19,3,8,.5)]:
            q,k,v=[torch.randn(2,3,length,8) for _ in range(3)]
            source_map,lut,count=namespace['get_block_map'](q,k,ratio,qb,kb)
            ours=selected(q,k,qb,kb,ratio);check('publisher_selected_blocks_'+str(length),torch.equal(lut.sort(-1).values,ours.sort(-1).values) and count==ours.shape[-1])
            for precision in (0,1):
                policy=torch.tensor([qb,kb,int(ratio*1000000),precision]);expected=BlockSparseAttention.apply(q,k,v,policy).numpy();got=native(graph,[q,k,v,policy])
                error=float(np.max(np.abs(expected-got)));check('online_softmax_'+str((length,precision)),np.allclose(got,expected,atol=.004 if precision else 4e-6,rtol=.01 if precision else 4e-5),maximumError=error)
                if ratio==1 and precision==0:
                    dense=torch.nn.functional.scaled_dot_product_attention(q,k,v).numpy();check('full_ratio_dense_attention',np.allclose(got,dense,atol=4e-6,rtol=4e-5))
            # Smooth-key selection is translation invariant, while execution
            # uses the original keys. Observe this independently via SDPA.
            got=native(graph,[q,k+7,v,torch.tensor([qb,kb,1000000,0])]);expected=torch.nn.functional.scaled_dot_product_attention(q,k+7,v).numpy();check('original_keys_not_pooled_keys_'+str(length),np.allclose(got,expected,atol=7e-6,rtol=8e-5))
        q,k,v=[torch.randn(1,1,9,4) for _ in range(3)]
        for p in ([0,4,1000000,0],[4,0,1000000,0],[4,4,0,0],[4,4,1000001,0],[4,4,1000000,2],[4,4,1,0],[4,4,1000000]):native(graph,[q,k,v,torch.tensor(p)],False)
        native(graph,[q,k[:,:,:-1],v,torch.tensor([4,4,1000000,0])],False)
        # Stable ties are portable and explicitly documented rather than
        # pretending Torch/CUDA provides a fixed tie order.
        z=torch.zeros_like(q);got=native(graph,[z,z,v,torch.tensor([4,4,500000,0])]);check('deterministic_ties',np.allclose(got,v[:,:,:4].mean(-2,keepdim=True).expand_as(v).numpy(),atol=1e-6))
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    current(inputs);report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsDownloaded=0,completeModelsRun=0,physicalDeviceTests=0,fullUltraTexAdapter=False,virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps({k:report[k] for k in ('passed','completeModelsRun','fullUltraTexAdapter')}))


if __name__=='__main__':main()
