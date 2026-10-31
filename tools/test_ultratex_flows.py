"""Random publisher networks -> exported ONNX -> actual native ORT/SLA.

No trained checkpoints, Android emulation, browser or network inference.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings
from evidence import ROOT, current, fingerprint

OUT = ROOT/'build/ultratex-flow-tests'


def main():
    sys.path.insert(0, str(ROOT/'build/shape-reference-python'))
    import torch
    import numpy as np
    import onnx
    from safetensors.torch import save_file
    from ultratex_flows import architecture, wrapper, example, export, merge_lora, definitions, source, IntegerRotary
    from ultratex_attention import Attention
    torch.set_num_threads(2); torch.manual_seed(714)
    OUT.mkdir(exist_ok=True)
    inputs = fingerprint('tools/test_ultratex_flows.py','tools/ultratex_flows.py','tools/export_ultratex_flow.py',
        'tools/ultratex_attention.py','third_party/ultratex-flow-source-lock.json','native/spatial',
        'tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(name, ok, **details):
        assert ok, (name,details)
        checks.append(dict(case=name,**details))
    lock=json.loads((ROOT/'third_party/ultratex-flow-source-lock.json').read_text('utf-8'))
    for item in lock['files']:
        source(item['path']); check('pinned_'+item['path'],True)
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def local(p):return alias+'/'+p.relative_to(ROOT).as_posix()
    def native(file,names,args,success=True):
        values=[dict(name=n,dtype='float32' if t.dtype==torch.float32 else 'int64',shape=list(t.shape),values=t.flatten().tolist()) for n,t in zip(names,args)]
        path=OUT/'request.json';path.write_text(json.dumps(dict(graph=local(file),inputs=values)),'utf-8')
        r=subprocess.run([local(ROOT/'build/spatial-worker-host/bin/lma_sparse_graph.exe'),local(path)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        check('native_accept' if success else 'native_reject',(r.returncode==0)==success,error=r.stderr[-500:])
        if success:return [np.array(x['values']).reshape(x['shape']) for x in json.loads(r.stdout)]
    def cfg(family,guidance=True):
        c=dict(in_channels=8,context_in_dim=12,hidden_size=64,num_heads=4,depth=1,depth_single_blocks=1,
            axes_dim=[4,6,6] if family=='flux1' else [4,4,4,4],theta=10000,mlp_ratio=2.)
        c.update(vec_in_dim=8,qkv_bias=True,guidance_embed=guidance) if family=='flux1' else c.update(use_guidance_embed=guidance)
        return c
    def expect_bad(name,call,model=None):
        before={n:p.detach().clone() for n,p in model.named_parameters()} if model is not None else {}
        try:call()
        except (AssertionError,ValueError,KeyError,StopIteration,TypeError,RuntimeError):pass
        else:raise AssertionError(name+' accepted')
        check(name,True)
        if model is not None:check(name+'_atomic',all(torch.equal(before[n],p) for n,p in model.named_parameters()))
    try:
        # Independently execute the unmodified publisher rotary function. This
        # detects a float32 trig approximation hidden behind the lookup export.
        from einops import rearrange
        path,text=source('ultratex/backbones/flux1/math.py')
        node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='rope')
        namespace=dict(torch=torch,Tensor=torch.Tensor,rearrange=rearrange)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
        model,_=architecture('flux1',cfg('flux1'),query_block=8,key_block=4,ratio=.5,bfloat16=False)
        lookup=IntegerRotary(model.pe_embedder)
        for dtype in (torch.float32,torch.int64):
            ids=torch.randint(0,8192,(2,113,3)).to(dtype)
            expected=torch.cat([namespace['rope'](ids[...,i],d,10000) for i,d in enumerate(cfg('flux1')['axes_dim'])],dim=-3).unsqueeze(1)
            check('exact_publisher_rotary_'+str(dtype),torch.equal(lookup(ids.long()),expected))
        expect_bad('unsupported_flux1_schnell',lambda:architecture('flux1',cfg('flux1',False)))
        for family,guide in [('flux1',True),('flux2',True),('flux2',False)]:
            c=cfg(family,guide);model,module=architecture(family,c,query_block=8,key_block=4,ratio=.5,bfloat16=False)
            graph=wrapper(family,model);file=OUT/(family+str(guide)+'.onnx')
            file.unlink(missing_ok=True)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore');export(model,family,c,file)
            parsed=onnx.load(str(file));onnx.checker.check_model(parsed)
            check('source_network_with_bsa_'+family+str(guide),sum(n.domain=='lma.spatial' and n.op_type=='BlockSparseAttention' for n in parsed.graph.node)==2)
            check('names_preserved_'+family+str(guide),[x.name for x in parsed.graph.input]==graph.names)
            check('no_constant_foreground_'+family+str(guide),sum(n.op_type=='NonZero' for n in parsed.graph.node)>=2)
            for target,normal,ref,text,batch in [(29,31,7,11,1),(37,19,9,17,2),(1,1,3,9,1),(11,13,5,7,1)]:
                args=list(example(family,c,target,normal,ref,text,batch))
                tm=graph.names.index('target_mask');nm=graph.names.index('normal_mask')
                if target==1:
                    args[tm]=torch.ones_like(args[tm]);args[nm]=torch.ones_like(args[nm])
                if target==11:args[tm]=torch.ones_like(args[tm]);args[nm]=torch.zeros_like(args[nm])
                with torch.no_grad():expected=graph(*args)
                got=native(file,graph.names,args)
                error=float(np.max(np.abs(got[0]-expected[0].numpy())))
                check('dynamic_publisher_network_'+str((family,guide,target,batch)),np.allclose(got[0],expected[0].numpy(),atol=7e-6,rtol=4e-4),maximumError=error)
                check('original_target_indices_'+str((family,guide,target)),np.array_equal(got[1],np.flatnonzero(args[tm].numpy())))
            args=list(example(family,c,23,27,5,15))
            tm=graph.names.index('target_mask');nm=graph.names.index('normal_mask')
            with torch.no_grad():baseline=graph(*args)[0]
            changed=[x.clone() for x in args];changed[0][:,changed[tm]==0]=12345;changed[2][:,changed[nm]==0]=-4567
            with torch.no_grad():masked=graph(*changed)[0]
            check('removed_background_never_attends_'+family+str(guide),torch.equal(baseline,masked))
            changed=[x.clone() for x in args];changed[1][...,1]+=137
            with torch.no_grad():moved=graph(*changed)[0]
            check('original_position_ids_matter_'+family+str(guide),not torch.allclose(baseline,moved,atol=1e-5,rtol=1e-5))
            changed=[x.clone() for x in args];changed[4].mul_(0)
            with torch.no_grad():unreferenced=graph(*changed)[0]
            check('single_reference_not_discarded_'+family+str(guide),not torch.allclose(baseline,unreferenced,atol=1e-5,rtol=1e-5))
        for family in ('flux1','flux2'):
            c=cfg(family);model,_=architecture(family,c,query_block=8,key_block=4,ratio=.5,bfloat16=True)
            graph=wrapper(family,model);file=OUT/(family+'-bf16-attention.onnx');file.unlink(missing_ok=True)
            with warnings.catch_warnings():warnings.simplefilter('ignore');export(model,family,c,file)
            args=example(family,c,37,39,7,19)
            with torch.no_grad():expected=graph(*args)[0]
            got=native(file,graph.names,args)[0]
            check('source_network_bfloat16_attention_'+family,np.allclose(got,expected.numpy(),atol=.002,rtol=.02),maximumError=float(np.max(np.abs(got-expected.numpy()))))
        # Flux1 merge against the actual unmerged publisher processors, with
        # random factors. Small projection dimensions only replace the source
        # constructor's hard-coded production 15360; forward stays unmodified.
        c=cfg('flux1');base,module=architecture('flux1',c,query_block=8,key_block=4,ratio=.5,bfloat16=False)
        unmerged=copy.deepcopy(base);state={};scale=.63
        layers=definitions('ultratex/backbones/flux1/modules/layers.py',
            {n:getattr(definitions('ultratex/backbones/flux1/math.py',{'sparse_attn':Attention(8,4,.5,False)}),n) for n in ('attention','attention_masked','rope')})
        double=layers.DoubleStreamBlockLoraProcessor(64,rank=3,lora_weight=scale)
        single=layers.SingleStreamBlockLoraProcessor(64,rank=3,lora_weight=scale)
        single.proj_lora=layers.LoRALinearLayer(64+128,64,rank=3)
        for name,processor in [('double_blocks.0',double),('single_blocks.0',single)]:
            for n,p in processor.named_parameters():
                with torch.no_grad():p.normal_(0,.04)
                state[name+'.processor.'+n]=p.detach().clone()
        unmerged.double_blocks[0].set_processor(double);unmerged.single_blocks[0].set_processor(single)
        merged=copy.deepcopy(base);count=merge_lora(merged,'flux1',state,scale)
        args=example('flux1',c)
        with torch.no_grad():before=wrapper('flux1',unmerged)(*args)[0];after=wrapper('flux1',merged)(*args)[0]
        check('flux1_lora_publisher_processors',count==6 and torch.allclose(before,after,atol=3e-6,rtol=3e-5),maximumError=float((before-after).abs().max()))
        for side in ('down','up'):
            bad=dict(state);bad.pop(next(k for k in bad if '.'+side+'.' in k));expect_bad('missing_flux1_'+side,lambda:merge_lora(merged,'flux1',bad),merged)
        bad=dict(state);bad['unknown.weight']=torch.zeros(1,1);expect_bad('unknown_flux1_key',lambda:merge_lora(merged,'flux1',bad),merged)
        bad=dict(state);name=next(iter(bad));bad[name]=bad[name].clone();bad[name][0,0]=float('nan');expect_bad('nonfinite_lora',lambda:merge_lora(merged,'flux1',bad),merged)
        bad=dict(state);bad[next(iter(bad))]=torch.zeros(3,5);expect_bad('mismatched_lora_dimension',lambda:merge_lora(merged,'flux1',bad),merged)
        expect_bad('invalid_lora_scale',lambda:merge_lora(merged,'flux1',state,float('nan')),merged)
        # Flux2 PEFT factors against separate unmerged Linear modules in the
        # actual publisher model, independent of the B@A merge calculation.
        c2=cfg('flux2',False);base2,_=architecture('flux2',c2,query_block=8,key_block=4,ratio=.5,bfloat16=False)
        class SeparateLora(torch.nn.Module):
            def __init__(self,linear,a,b):
                super().__init__();self.base=linear;self.a=a;self.b=b
            def forward(self,x):
                return self.base(x)+torch.nn.functional.linear(torch.nn.functional.linear(x,self.a),self.b)*.75
        original=copy.deepcopy(base2);state2={}
        for name in ['double_blocks.0.img_attn.qkv','double_blocks.0.txt_attn.proj','single_blocks.0.linear1','single_blocks.0.linear2']:
            layer=original.get_submodule(name);a=torch.randn(3,layer.in_features)*.04;b=torch.randn(layer.out_features,3)*.04
            state2['base_model.model.'+name+'.lora_A.default.weight']=a
            state2['base_model.model.'+name+'.lora_B.default.weight']=b
            parent,leaf=name.rsplit('.',1);setattr(original.get_submodule(parent),leaf,SeparateLora(layer,a,b))
        merged2=copy.deepcopy(base2);count=merge_lora(merged2,'flux2',state2,.75)
        args=example('flux2',c2)
        with torch.no_grad():expected=wrapper('flux2',original)(*args)[0];got=wrapper('flux2',merged2)(*args)[0]
        check('flux2_lora_unmerged_layers',count==4 and torch.allclose(expected,got,atol=3e-6,rtol=3e-5),maximumError=float((expected-got).abs().max()))
        bad=dict(state2);bad['base_model.model.time_in.lora_A.default.weight']=torch.zeros(2,2);expect_bad('unsupported_flux2_target',lambda:merge_lora(merged2,'flux2',bad),merged2)
        # Real CLI, both families, with random architecture weights only.
        env=dict(os.environ,PYTHONIOENCODING='utf-8')
        env['PYTHONPATH']=os.pathsep.join([str(ROOT/'build/shape-reference-python'),str(ROOT/'tools')])
        for family,c,model,lora in [('flux1',cfg('flux1'),base,state),('flux2',c2,base2,state2)]:
            cp=OUT/(family+'-config.json');wp=OUT/(family+'-random.safetensors');lp=OUT/(family+'-lora.safetensors')
            cp.write_text(json.dumps(c),'utf-8');save_file(model.state_dict(),str(wp));save_file(lora,str(lp))
            # New output each run; never delete or overwrite a prior export.
            import tempfile
            parent=Path(tempfile.mkdtemp(prefix=family+'-',dir=OUT));dest=parent/'output'
            cmd=[sys.executable,str(ROOT/'tools/export_ultratex_flow.py'),'--family',family,'--config',str(cp),'--weights',str(wp),'--lora',str(lp),'--output',str(dest),'--float-attention']
            r=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
            check('actual_cli_'+family,r.returncode==0,error=r.stderr[-1400:])
            receipt=json.loads((dest/'export-receipt.json').read_text('utf-8'))
            check('component_not_complete_adapter_'+family,not receipt['complete_adapter'] and not receipt['app_recipe_registered'] and not receipt['network'] and len(receipt['missing_stages'])==6)
            for component in receipt['components']:
                data=(dest/component['file']).read_bytes();check('export_hash_'+family,len(data)==component['bytes'] and hashlib.sha256(data).hexdigest()==component['sha256'])
            # Execute the actual CLI artifact with a new foreground pattern
            # and enough blocks for the publisher's default topk=.2 policy.
            oracle,_=architecture(family,c,bfloat16=False)
            oracle.load_state_dict(model.state_dict(),strict=True);merge_lora(oracle,family,lora)
            wrapped=wrapper(family,oracle);args=example(family,c,41,43,11,333)
            with torch.no_grad():expected,indices=wrapped(*args)
            got=native(dest/'flow.onnx',wrapped.names,args)
            check('actual_cli_native_equivalence_'+family,np.allclose(got[0],expected.numpy(),atol=1e-5,rtol=5e-4),maximumError=float(np.max(np.abs(got[0]-expected.numpy()))))
            check('actual_cli_native_target_indices_'+family,np.array_equal(got[1],indices.numpy()))
            before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.iterdir()}
            # Removing torch from PYTHONPATH still must reject an existing
            # destination before heavy dependencies or model reads.
            r=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
            check('cli_existing_output_refused_'+family,r.returncode!=0 and 'Choose a new output directory' in r.stderr)
            check('prior_export_unchanged_'+family,before=={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.iterdir()})
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    current(inputs)
    report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,actual_native_ort=True,publisher_random_networks=True,
        complete_adapter=False,app_recipe_registered=False,complete_models_downloaded=0,complete_models_run=0,
        physical_device_tests=0,virtualization_used=False)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','input_fingerprint')}))


if __name__=='__main__':main()
