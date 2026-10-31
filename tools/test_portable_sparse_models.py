"""Actual pinned random sparse networks -> exported graph -> native CPU ORT.

Shared components only; no complete trained model, phone, or downloaded weights.
"""
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import warnings
from evidence import ROOT, fingerprint, current

OUT=ROOT/'build/portable-sparse-model-tests'


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import numpy as np
    import torch
    from torch import nn
    from spatial_portable import Source,RealRoPE
    from spatial_sparse_graphs import operation
    torch.manual_seed(28145);torch.set_num_threads(2)
    OUT.mkdir(exist_ok=True)
    inputs=fingerprint('tools/spatial_portable.py','tools/spatial_sparse_graphs.py','tools/test_portable_sparse_models.py',
        'third_party/portable-sparse-source-lock.json','native/spatial','tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(name,value,**details):
        assert value,(name,details);checks.append(dict(case=name,**details))
    def compare(name,a,b):
        a=a.detach().numpy() if hasattr(a,'detach') else np.array(a)
        b=b.detach().numpy() if hasattr(b,'detach') else np.array(b)
        check(name,a.shape==b.shape and np.allclose(a,b,atol=1e-5,rtol=2e-4),shape=list(a.shape))
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def path(p):return alias+'/'+p.relative_to(ROOT).as_posix()
    def export(model,args,names,outputs,name):
        file=OUT/(name+'.onnx')
        dynamic={n:{0:n+'_rows'} for n in names+outputs if n!='time'}
        if 'full' in names:dynamic['full']={1:'views'}
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            torch.onnx.export(model,args,file,input_names=names,output_names=outputs,dynamic_axes=dynamic,
                opset_version=17,custom_opsets={'lma.spatial':1},dynamo=False,external_data=False)
        return file
    def run(file,names,args,success=True):
        import onnx
        consumed={i.name for i in onnx.load(str(file),load_external_data=False).graph.input}
        assert set(names)-consumed <= {'coords'},'An unexpected learned input was pruned'
        request=dict(graph=path(file),inputs=[dict(name=n,shape=list(t.shape),dtype='float32' if t.is_floating_point() else 'int64',
            values=t.flatten().tolist()) for n,t in zip(names,args) if n in consumed])
        f=OUT/'request.json';f.write_text(json.dumps(request),'utf-8')
        r=subprocess.run([path(ROOT/'build/spatial-worker-host/bin/lma_sparse_graph.exe'),path(f)],
            capture_output=True,text=True,encoding='utf-8',timeout=60)
        check(file.stem+('_executes' if success else '_rejects'),(r.returncode==0)==success,error=r.stderr[-500:])
        return [np.array(v['values']).reshape(v['shape']) for v in json.loads(r.stdout)] if success else None
    def randomize(model):
        for p in model.parameters():nn.init.normal_(p,mean=0,std=.07)
        return model.float().eval().requires_grad_(False)
    try:
        source=Source('D10');sp=source.sparse_api()
        original=source.namespace('supratex/modules/attention/rope.py')
        # Independently execute the unmodified complex reference definitions.
        _,text=source.read('supratex/modules/attention/rope.py');scope={}
        exec(compile(text,'pinned-rope-reference','exec'),scope)
        for dim in (8,12,18):
            coords=torch.randint(0,1024,(13,3)).float();q=torch.randn(13,2,dim)
            literal=scope['RotaryPositionEmbedder'](dim);real=RealRoPE(dim)
            compare('complex_rope_'+str(dim),literal.apply_rotary_embedding(q,literal(coords)),real.apply_rotary_embedding(q,real(coords)))
        # Paired two-level caches must survive both inverses; even an explicit
        # all-false guide cannot override the cached original support.
        coords=torch.tensor([[0,x,y,z] for x in range(4) for y in range(3) for z in range(2)])
        f=torch.randn(len(coords),8);x=sp.SparseTensor(f,coords)
        for container in (sp.SparseTensor(f,coords),sp.VarLenTensor(f)):
            row=torch.randn(1,8)
            compare('per_batch_add_'+type(container).__name__,(container+row).feats,f+row)
            compare('per_batch_sub_'+type(container).__name__,(container-row).feats,f-row)
            compare('per_batch_multiply_'+type(container).__name__,(container*row).feats,f*row)
        down=sp.SparseDownsample(2);up=sp.SparseUpsample(2)
        a=down(x);b=down(a);wrong=sp.SparseTensor(torch.zeros(len(b.feats),8,dtype=torch.bool),b.coords)
        c=up(b,wrong);d=up(c)
        compare('two_level_cached_support',d.coords,coords)
        expected=f.clone()
        # The reference uses averaging: coordinate restoration, not identity.
        compare('two_level_cached_values',d.feats,b.feats[torch.zeros(len(coords),dtype=torch.int64)])
        c2s=sp.SparseChannel2Spatial();s2c=sp.SparseSpatial2Channel()
        y=s2c(s2c(x));y=c2s(y,sp.SparseTensor(torch.zeros(len(y.feats),8,dtype=torch.bool),y.coords));y=c2s(y)
        compare('two_level_channel_inverse',y.feats,f)
        compare('two_level_channel_coords',y.coords,coords)
        for norm in (False,True):
            attention=randomize(sp.SparseMultiHeadAttention(24,2,ctx_channels=8,type='cross',qk_rms_norm=norm))
            class Cross(nn.Module):
                def __init__(self):super().__init__();self.attention=attention
                def forward(self,features,coords,context):
                    return self.attention(sp.SparseTensor(features,coords),context).feats
            cross=Cross().eval();cf=torch.randn(len(coords),24);context=torch.randn(1,7,8)
            graph=export(cross,(cf,coords,context),['features','coords','context'],['result'],'dense_cross_'+str(norm))
            for count in (len(coords),7):
                values=(cf[:count],coords[:count],context)
                compare('actual_dense_conditioning_'+str((norm,count)),cross(*values),run(graph,['features','coords','context'],values)[0])
        # Exact released routed projections and RMS norms. Only the CUDA
        # packing/attention boundary differs. Retain the real 12x128 head ABI.
        d05=Source('D05');dapi=d05.sparse_api();rel='uniforge3d/modules/sparse/attention/routed_full_only_flash.py'
        routed=d05.namespace(rel);_,literal_text=d05.read(rel)
        cls=next(n for n in ast.parse(literal_text).body if isinstance(n,ast.ClassDef) and n.name=='RoutedFullOnlyFlashCrossAttention')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward')
        scope=dict(vars(routed));exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),method],type_ignores=[])),'literal-routed-forward','exec'),scope)
        original_forward=scope['forward']
        for norm in (False,True):
            attention=randomize(routed.RoutedFullOnlyFlashCrossAttention(1536,16,12,qk_rms_norm=norm));attention.full_tokens=7
            class Routed(nn.Module):
                def __init__(self):super().__init__();self.attention=attention
                def forward(self,features,full,selected):
                    c=torch.zeros((features.shape[0],4),dtype=torch.int64)
                    return self.attention(dapi.SparseTensor(features,c),dict(full_bank=full,selected_rows=selected)).feats
            wrapper=Routed().eval();names=['features','full','selected']
            values=(torch.randn(5,1536),torch.randn(1,3,7,16),torch.tensor([2,0,2,1,0]))
            graph=export(wrapper,values,names,['result'],'routed_view_'+str(norm))
            # Dynamic V and N are both checked; the full graph uses B=1.
            for views,selected in ((3,[2,0,2,1,0]),(2,[1,1,0]),(1,[0])):
                values=(torch.randn(len(selected),1536),torch.randn(1,views,7,16),torch.tensor(selected))
                expected=wrapper(*values);compare('routed_native_'+str((norm,views)),expected,run(graph,names,values)[0])
                order=torch.argsort(values[2],stable=True);inverse=torch.argsort(order);active=torch.unique(values[2],sorted=True)
                counts=torch.bincount(values[2],minlength=views)[active];cq=torch.cat((torch.zeros(1,dtype=torch.int64),counts.cumsum(0)))
                context=dict(full_bank=values[1],routed_query_order=order,routed_query_inverse=inverse,routed_active_groups=active,
                             routed_cu_seqlens_q=cq,routed_cu_seqlens_k=torch.arange(len(active)+1)*7,routed_max_seqlen_q=int(counts.max()))
                reference=original_forward(attention,dapi.SparseTensor(values[0],torch.zeros(len(selected),4,dtype=torch.int64)),context).feats
                compare('literal_routed_'+str((norm,views)),expected,reference)
            bad=list(values);bad[2]=torch.tensor([views]);run(graph,names,bad,False)
        module=source.namespace('supratex/models/interleaved_flow_transformer.py')
        stats=dict(partial_mean=[.2]*32,partial_std=[.7]*32,pbr_mean=[-.3]*32,pbr_std=[1.2]*32)
        model=randomize(module.InterleavedFlowTransformer(model_channels=24,num_heads=2,num_blocks=4,mlp_ratio=2,
            use_checkpoint=False,_test_tiny=True,allow_test_config=True,**stats))
        class Completion(nn.Module):
            def __init__(self,net):super().__init__();self.net=net
            def forward(self,features,coords,time,shape,observed,observed_coords):
                return self.net(sp.SparseTensor(features,coords),time,concat_cond=sp.SparseTensor(shape,coords),
                    partial_z_obs=sp.SparseTensor(observed,observed_coords)).feats
        wrapper=Completion(model).eval();names=['features','coords','time','shape','observed','observed_coords']
        def sample(n,selected):
            coords=torch.tensor([[0,0,i//4,i%4] for i in range(n)])
            return (torch.randn(n,32),coords,torch.tensor([650.]),torch.randn(n,32),torch.randn(len(selected),34),coords[selected])
        args=sample(9,[1,4,7]);file=export(wrapper,args,names,['velocity'],'supra_completion')
        for n,selected in ((9,[1,4,7]),(13,[0,3]),(4,[0,1,2,3])):
            args=sample(n,selected)
            with torch.no_grad():expected=wrapper(*args)
            result=run(file,names,args)[0];compare('actual_interleaved_'+str((n,selected)),expected,result)
            changed=list(args);changed[4]=changed[4]+.3
            compare('actual_observation_effect_'+str(n),wrapper(*changed),run(file,names,changed)[0])
        # Public source uses int32 coordinates. The graph ABI is explicit int64,
        # and the binding converts both sides without changing output row type.
        join=source.namespace('supratex/models/observation_attention.py')._join_exact_rows
        compare('source_int32_join',join(args[1].int(),args[5].int()),torch.arange(4))
        class Join(nn.Module):
            def forward(self,full,observed):return operation('join')(full,observed)
        j=export(Join(),(args[1],args[5]),['full','observed'],['rows'],'exact_join')
        compare('exact_join_order',run(j,['full','observed'],(args[1],args[5].flip(0)))[0],torch.arange(3,-1,-1))
        bad=args[5].clone();bad[0,1]=50;run(j,['full','observed'],(args[1],bad),False)
        bad=args[5].clone();bad[0]=bad[1];run(j,['full','observed'],(args[1],bad),False)
        vae=source.namespace('supratex/models/sc_vaes/sparse_unet_vae.py')
        encoder=randomize(vae.SparseUnetVaeEncoder(in_channels=6,model_channels=[8,16],latent_channels=4,
            num_blocks=[1,1],block_type=['SparseConvNeXtBlock3d']*2,down_block_type=['SparseResBlockS2C3d'],block_args=[{},{}]))
        class Encode(nn.Module):
            def forward(self,features,coords):
                out=encoder(sp.SparseTensor(features,coords));return out.feats,out.coords
        class EncoderGraph(nn.Module):
            def __init__(self):super().__init__();self.encoder=encoder
            def forward(self,features,coords):
                out=self.encoder(sp.SparseTensor(features,coords));return out.feats,out.coords
        e=EncoderGraph().eval();coords=torch.tensor([[0,x,y,z] for x in range(4) for y in range(3) for z in range(2)])
        args=(torch.randn(len(coords),6),coords);g=export(e,args,['features','coords'],['latent','latent_coords'],'sparse_vae_encoder')
        for count in (len(coords),17,8):
            values=(args[0][:count],args[1][:count]);expected=e(*values);actual=run(g,['features','coords'],values)
            for k in (0,1):compare('actual_scvae_encoder_'+str((count,k)),expected[k],actual[k])
        for target in ('D05','D10'):
            reference=Source(target);api=reference.sparse_api()
            rel='uniforge3d/models/vaes/sparse_unet.py' if target=='D05' else 'supratex/models/sc_vaes/sparse_unet_vae.py'
            dec=reference.namespace(rel)
            decoder=randomize(dec.SparseUnetVaeDecoder(out_channels=7,model_channels=[16,8],latent_channels=4,
                num_blocks=[1,1],block_type=['SparseConvNeXtBlock3d']*2,up_block_type=['SparseResBlockC2S3d'],block_args=[{},{}]))
            # Avoid empty topology in the random fixture while retaining every
            # learned subdivision head and its input-dependent decisions.
            for name,p in decoder.named_parameters():
                if name.endswith('to_subdiv.bias'):p.fill_(.25)
            class Decode(nn.Module):
                def __init__(self):super().__init__();self.decoder=decoder
                def forward(self,features,coords):
                    out,subs=self.decoder(api.SparseTensor(features,coords),return_subs=True)
                    return out.feats,out.coords,subs[0].feats,subs[0].coords
            d=Decode().eval();coords=torch.tensor([[0,0,0,i] for i in range(3)]);args=(torch.randn(3,4),coords)
            g=export(d,args,['features','coords'],['decoded','decoded_coords','subdivision','subdivision_coords'],target+'_sparse_vae_decoder')
            for count in (3,2,1):
                values=tuple(v[:count] for v in args);expected=d(*values);actual=run(g,['features','coords'],values)
                for k in range(4):compare('actual_'+target+'_decoder_'+str((count,k)),expected[k],actual[k])
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,sourceDefinitions=True,actualNativeOrt=True,
        sharedComponentsOnly=True,completeAdapters=[],completeModelsDownloaded=0,completeModelsRun=0,physicalDeviceTests=0,virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))


if __name__=='__main__':main()
