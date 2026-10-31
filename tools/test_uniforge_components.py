"""Random source-defined UniForge components, exported and run by native ORT.

This checks learned component math, dynamic views/rows and paired decoder
topology. It does not claim a complete UniForge adapter or model inference.
"""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/'build/ultratex-python'),str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    import numpy as np
    import onnx
    import torch
    from torch import nn
    from spatial_portable import Source
    from uniforge_components import dino,StageAdapter,ShapeDecode,MaterialDecode
    torch.set_num_threads(2);torch.manual_seed(71823)
    out=ROOT/'build/uniforge-component-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('tools/test_uniforge_components.py','tools/uniforge_components.py','tools/spatial_portable.py',
        'tools/spatial_sparse_graphs.py','third_party/portable-sparse-source-lock.json','native/spatial','tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(name,value,**extra):
        assert value,(name,extra);checks.append(dict(case=name,**extra))
    def compare(name,a,b):
        a=a.detach().numpy() if hasattr(a,'detach') else np.asarray(a)
        b=b.detach().numpy() if hasattr(b,'detach') else np.asarray(b)
        check(name,a.shape==b.shape and np.allclose(a,b,rtol=5e-4,atol=2e-5),shape=list(a.shape))
    def randomize(model):
        for p in model.parameters():nn.init.normal_(p,std=.08)
        return model.float().eval().requires_grad_(False)
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(path):return alias+'/'+path.relative_to(ROOT).as_posix()
    def export(model,args,names,outputs,label,dynamic):
        file=out/(label+'.onnx')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            torch.onnx.export(model,args,file,input_names=names,output_names=outputs,dynamic_axes=dynamic,
                opset_version=17,dynamo=False,custom_opsets={'lma.spatial':1},external_data=False)
        return file
    def run(graph,args,names):
        consumed={i.name for i in onnx.load(str(graph),load_external_data=False).graph.input}
        file=out/'request.json';file.write_text(json.dumps(dict(graph=native(graph),inputs=[dict(name=n,shape=list(t.shape),
            dtype='float32' if t.is_floating_point() else 'int64',values=t.flatten().tolist()) for n,t in zip(names,args) if n in consumed])),'utf-8')
        p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_sparse_graph.exe'),native(file)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        check(graph.stem+'_native',p.returncode==0,error=p.stderr[-300:])
        return [np.array(t['values']).reshape(t['shape']) for t in json.loads(p.stdout)]
    try:
        s=Source('D05');base=s.namespace('uniforge3d/models/vggt_adapter.py')
        module=s.namespace('uniforge3d/models/joint_dit_vggt_stage1.py')
        # Actual block-specific VGGT->DINO delta retains special tokens.
        delta=randomize(module.BlockDinoCondDeltaMLP(dim=32,hidden_dim=32))
        names=['dino','aligned'];args=(torch.randn(1,2,9,32),torch.randn(2,64,2,2))
        graph=export(delta,args,names,['fused'],'vggt_to_dino',dict(dino={1:'views'},aligned={0:'views'},fused={1:'views'}))
        for views in (2,1,3):
            values=(torch.randn(1,views,9,32),torch.randn(views,64,2,2));expected=delta(*values)
            compare('delta_dynamic_views_'+str(views),expected,run(graph,values,names)[0])
            compare('five_special_tokens_'+str(views),expected[:,:,:5],values[0][:,:,:5])
            check('real_vggt_delta_'+str(views),not torch.allclose(expected[:,:,5:],values[0][:,:,5:]))
        # Actual DiT->VGGT return feedback and timestep-gated residual.
        feedback=randomize(module.DiTToVGGTResidual(32,24,24,heads=4,gate_cap=1))
        names=['vggt','dit','time'];args=(torch.randn(1,18,32),torch.randn(1,8,24),torch.randn(1,24))
        graph=export(feedback,args,names,['feedback'],'dit_to_vggt',dict(vggt={1:'queries'},dit={1:'shape_tokens'},feedback={1:'queries'}))
        for nq,nk in ((18,8),(9,5)):
            values=(torch.randn(1,nq,32),torch.randn(1,nk,24),args[2]);expected=feedback(*values)
            compare('feedback_dynamic_'+str((nq,nk)),expected,run(graph,values,names)[0])
            changed=list(values);changed[1]=changed[1].clone();changed[1][...,0]+=3
            check('actual_feedback_sensitivity_'+str(nq),not torch.allclose(feedback(*changed),expected))
        # Real 4-layer residual adapters, separate 512 and 1024 nearest+learned paths.
        for scale in (1,2):
            adapter=randomize(base.VGGT4LayerDINOAdapter(feature_dim=64,per_layer_dim=16,hidden_dim=64,output_dim=32,input_patch_grid_size=2,upsample_scale=scale))
            wrapper=StageAdapter(adapter).eval();names=['layer4','layer11','layer17','layer23'];args=tuple(torch.randn(1,2,9,64) for _ in names)
            graph=export(wrapper,args,names,['delta'],'four_layers_'+str(scale),{n:{1:'views'} for n in names+['delta']})
            for views in (2,1,3):
                values=tuple(torch.randn(1,views,9,64) for _ in names)
                compare('four_layers_scale_'+str((scale,views)),wrapper(*values),run(graph,values,names)[0])
        # Packed shape-token cross-attention cannot capture a particular N from
        # Python int(offset). Compare to the unmodified source method for each N.
        _,literal=s.read('uniforge3d/models/vggt_adapter.py');cls=next(n for n in ast.parse(literal).body if isinstance(n,ast.ClassDef) and n.name=='PackedCrossAttention')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward');namespace=dict(vars(base))
        node=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),method],type_ignores=[])
        exec(compile(ast.fix_missing_locations(node),'literal-packed-shape','exec'),namespace)
        packed=randomize(base.PackedCrossAttention(32,24,32,4))
        class Packed(nn.Module):
            def __init__(self):super().__init__();self.net=packed
            def forward(self,query,shape):return self.net(query,shape,torch.cat((torch.zeros(1,dtype=torch.int64),torch._shape_as_tensor(shape)[0:1])))
        wrapper=Packed();names=['query','shape'];args=(torch.randn(1,11,32),torch.randn(7,24))
        graph=export(wrapper,args,names,['result'],'packed_shape',dict(query={1:'queries'},shape={0:'shape_tokens'},result={1:'queries'}))
        for nq,nk in ((11,7),(5,3),(1,13)):
            values=(torch.randn(1,nq,32),torch.randn(nk,24));expected=namespace['forward'](packed,*values,torch.tensor([0,nk]))
            compare('literal_packed_shape_'+str((nq,nk)),expected,run(graph,values,names)[0])
        # Source DINOv3 path, including parameter-free final norm and all five
        # special tokens; only a tiny random architecture is instantiated.
        d=dino(s,dict(hidden_size=32,intermediate_size=64,num_hidden_layers=2,num_attention_heads=4,patch_size=16,
                      image_size=32,num_register_tokens=4,rope_theta=100.,layerscale_value=1.))
        names=['images'];args=(torch.rand(1,2,3,32,32),)
        graph=export(d,args,names,['features'],'dinov3',dict(images={1:'views'},features={1:'views'}))
        for views in (2,1,3):
            values=(torch.rand(1,views,3,32,32),);expected=d(*values)
            check('dinov3_special_tokens_'+str(views),tuple(expected.shape)==(1,views,9,32))
            compare('dinov3_native_'+str(views),expected,run(graph,values,names)[0])
        # Actual two-stage learned shape subdivisions are passed intact into
        # the separate material decoder, keeping the exact coordinate order.
        vae=s.namespace('uniforge3d/models/vaes/sparse_unet.py');api=s.sparse_api()
        common=dict(model_channels=[16,8,4],latent_channels=4,num_blocks=[1,1,1],block_type=['SparseConvNeXtBlock3d']*3,
                    up_block_type=['SparseResBlockC2S3d']*2,block_args=[{},{},{}])
        shape=randomize(vae.SparseUnetVaeDecoder(out_channels=7,pred_subdiv=True,**common))
        texture=randomize(vae.SparseUnetVaeDecoder(out_channels=6,pred_subdiv=False,**common))
        for name,p in shape.named_parameters():
            if name.endswith('to_subdiv.bias'):p.fill_(.3)
        sw=ShapeDecode(s,shape);tw=MaterialDecode(s,texture);names=['features','coords']
        coords=torch.tensor([[0,0,0,i] for i in range(3)]);args=(torch.randn(3,4),coords)
        outputs=['fields','decoded_coords','guide0','guide_coords0','guide1','guide_coords1']
        graph=export(sw,args,names,outputs,'shape_guides',{n:{0:n+'_rows'} for n in names+outputs})
        guides=sw(*args)[2:];tnames=['features','coords','guide0','guide_coords0','guide1','guide_coords1']
        tgraph=export(tw,(*args,*guides),tnames,['materials','material_coords'],'guided_material',{n:{0:n+'_rows'} for n in tnames+['materials','material_coords']})
        for count in (3,1,2):
            values=tuple(v[:count] for v in args);expected=sw(*values);actual=run(graph,values,names)
            for i in range(6):compare('shape_decoded_'+str((count,i)),expected[i],actual[i])
            texture_values=(*values,*expected[2:]);expected_mat=tw(*texture_values);actual_mat=run(tgraph,texture_values,tnames)
            for i in range(2):compare('texture_guided_'+str((count,i)),expected_mat[i],actual_mat[i])
            compare('shape_texture_coordinate_identity_'+str(count),expected[1],actual_mat[1])
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    result=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,sourceClasses=True,actualNativeOrt=True,
                sharedComponentsOnly=True,completeAdapters=[],completeModelsRun=0,phoneTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
