"""Actual random Qwen PBR / RGBA VAE / Qwen3-VL -> native CPU ONNX checks.

Tiny architecture fixtures exercise learned math and compare against independent
literal source forwards. They are not trained models or phone acceptance.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    import numpy as np
    import torch
    from torch import nn
    from spatial_portable import Source
    from supra_components import definitions,QWEN,qwen_dit,qwen_pbr,FixedPBR,qwen_vae,VaeEncode,VaeDecode,VLFeatures,patchify,unpatchify,ShapeEncode,MaterialEncode,CachedDecode,scvae
    from transformers import Qwen3VLConfig,Qwen3VLForConditionalGeneration
    torch.set_num_threads(2);torch.manual_seed(51021)
    out=ROOT/'build/supra-component-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('tools/test_supra_components.py','tools/supra_components.py','tools/spatial_portable.py',
        'tools/spatial_sparse_graphs.py','third_party/portable-sparse-source-lock.json','native/spatial','tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(case,value,**extra):assert value,(case,extra);checks.append(dict(case=case,**extra))
    def compare(case,a,b):
        a=a.detach().numpy() if hasattr(a,'detach') else np.asarray(a)
        b=b.detach().numpy() if hasattr(b,'detach') else np.asarray(b)
        check(case,a.shape==b.shape and np.allclose(a,b,rtol=8e-4,atol=4e-5),shape=list(a.shape),error=float(np.max(np.abs(a-b))) if a.size else 0)
    def randomize(model):
        for name,p in model.named_parameters():
            if 'norm' in name and p.ndim==1:nn.init.ones_(p)
            else:nn.init.normal_(p,std=.06)
        return model.float().eval().requires_grad_(False)
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(path):return alias+'/'+path.relative_to(ROOT).as_posix()
    def export(label,model,args,names,outputs,dynamic=None):
        file=out/(label+'.onnx')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            torch.onnx.export(model,args,file,input_names=names,output_names=outputs,opset_version=17,dynamo=False,
                custom_opsets={'lma.spatial':1},external_data=False,dynamic_axes=dynamic)
        return file
    def run(file,args,names):
        request=out/'request.json';request.write_text(json.dumps(dict(graph=native(file),inputs=[dict(name=name,dtype='float32' if a.is_floating_point() else 'int64',shape=list(a.shape),values=a.flatten().tolist()) for name,a in zip(names,args)])),'utf-8')
        p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_sparse_graph.exe'),native(request)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        check(file.stem+'_native',p.returncode==0,error=p.stderr[-400:]);return [np.array(v['values']).reshape(v['shape']) for v in json.loads(p.stdout)]
    try:
        source=Source('D10')
        def literal_attention_forward(q,k,v,attn_mask=None,**kw):
            return nn.functional.scaled_dot_product_attention(q.transpose(1,2),k.transpose(1,2),v.transpose(1,2),attn_mask=attn_mask).transpose(1,2)
        reference=definitions(source,QWEN+'models/qwen_image_21_dit.py',dict(attention_forward=literal_attention_forward))
        args=dict(in_channels=8,out_channels=8,num_layers=2,attention_head_dim=12,num_attention_heads=2,
            context_in_dim=16,mlp_ratio=2,axes_dims_rope=(4,4,4))
        model=randomize(qwen_pbr(source,qwen_dit(source,args)))
        original=qwen_pbr(source,reference.QwenImage21DiT(**args)).float().eval();original.load_state_dict(model.state_dict())
        # Nonempty text before AND after the reference; source group-causal
        # prefix and two jointly attending target blocks must both survive.
        layout=[False,False]+[True]*4+[False]*3
        fixed=FixedPBR(model,layout,4,4).eval();names=['noise','prompt','rgb']
        values=(torch.randn(1,2,8,4,4),torch.randn(1,len(layout),16),torch.randn(1,8,4,4))
        with torch.no_grad():expected=original(values[0],torch.tensor([1000.]),values[1],None,torch.tensor([layout]),[values[2]])
        compare('literal_complex_source_pbr',expected,fixed(*values))
        file=export('qwen_material_endpoint',fixed,values,names,['velocity'])
        for index in range(3):
            values=tuple(torch.randn_like(v) for v in values)
            with torch.no_grad():expected=original(values[0],torch.tensor([1000.]),values[1],None,torch.tensor([layout]),[values[2]])
            compare('endpoint_cpu_'+str(index),expected,run(file,values,names)[0])
            compare('endpoint_noise_minus_velocity_'+str(index),values[0]-expected,values[0]-run(file,values,names)[0])
        # Actual source RGBA VAE, including its latent normalization and channel
        # layout. The single-frame path is the source's own image-specialization.
        vae_args=dict(base_dim=4,decoder_base_dim=4,z_dim=4,dim_mult=[1,2,2,2,2],num_res_blocks=1,
            temperal_downsample=[False,True,True,True],latents_mean=[.1,.2,.3,.4],latents_std=[.8,.9,1.1,1.2])
        vae=randomize(qwen_vae(source,vae_args))
        original_vae=definitions(source,QWEN+'models/qwen_image_21_vae.py').QwenImage21VAE(**vae_args).float().eval()
        original_vae.load_state_dict(vae.state_dict())
        image=torch.rand(1,4,32,32)*2-1;encoder=VaeEncode(vae).eval();file=export('qwen_rgba_encode',encoder,(image,),['rgba'],['latent'])
        compare('actual_rgba_encoder',encoder(image),run(file,(image,),['rgba'])[0])
        compare('literal_rgba_encoder',original_vae.encode(image),encoder(image))
        latent=torch.randn(1,4,2,2);decoder=VaeDecode(vae).eval();file=export('qwen_rgba_decode',decoder,(latent,),['latent'],['rgba'])
        compare('actual_rgba_decoder',decoder(latent),run(file,(latent,),['latent'])[0])
        compare('literal_rgba_decoder',original_vae.decode(latent).add(1).mul(.5),decoder(latent))
        # Actual Transformers Qwen3-VL: image patch embedding, positional
        # interpolation, three deepstack injections and pre-final text norm.
        cfg=Qwen3VLConfig(text_config=dict(vocab_size=32,hidden_size=24,intermediate_size=48,num_hidden_layers=3,
                num_attention_heads=4,num_key_value_heads=2,head_dim=6,rope_scaling=dict(rope_type='default',mrope_section=[1,1,1],mrope_interleaved=True)),
            vision_config=dict(depth=3,hidden_size=32,intermediate_size=48,num_heads=4,patch_size=2,spatial_merge_size=2,
                temporal_patch_size=2,out_hidden_size=24,num_position_embeddings=16,deepstack_visual_indexes=[0,1,2]),
            image_token_id=9,video_token_id=12,vision_start_token_id=10,vision_end_token_id=11)
        cfg._attn_implementation='eager';cfg.text_config._attn_implementation='eager';cfg.vision_config._attn_implementation='eager'
        vl=randomize(Qwen3VLForConditionalGeneration(cfg));ids=torch.tensor([[1,10,9,9,9,9,11,2]])
        pixels=torch.randn(16,3*2*2*2);grid=torch.tensor([[1,4,4]])
        wrapper=VLFeatures(vl,ids[0].tolist(),grid,1).eval()
        captured=[];hook=vl.model.language_model.norm.register_forward_pre_hook(lambda module,args:captured.append(args[0].detach().clone()))
        try:
            with torch.no_grad():vl.model(input_ids=ids,pixel_values=pixels,image_grid_thw=grid,attention_mask=torch.ones_like(ids),use_cache=False)
        finally:hook.remove()
        compare('literal_qwen3vl_prenorm',captured[-1][:,1:],wrapper(ids,pixels))
        file=export('qwen3vl_condition',wrapper,(ids,pixels),['ids','pixels'],['features'])
        for index in range(2):
            pixels=torch.randn_like(pixels)
            compare('qwen3vl_native_'+str(index),wrapper(ids,pixels),run(file,(ids,pixels),['ids','pixels'])[0])
        # Actual learned SCVAE encoders and cached C2S decoders. Compare the
        # reconstructed integer topology against the caches carried directly
        # by the real source encoder, then vary the sparse surface support.
        sparse=source.sparse_api()
        common=dict(model_channels=[8,16,16],latent_channels=4,num_blocks=[1,1,1],
            block_type=['SparseConvNeXtBlock3d']*3,block_args=[{} for _ in range(3)])
        down=dict(down_block_type=['SparseResBlockS2C3d']*2)
        shape_encoder=randomize(scvae(source,'shape_encoder',dict(**common,**down)))
        material_encoder=randomize(scvae(source,'material_encoder',dict(in_channels=6,**common,**down)))
        dynamic=lambda names:{name:{0:name+'_rows'} for name in names}
        for kind,encoder,channels in [('shape',shape_encoder,7),('material',material_encoder,6)]:
            decargs=dict(**common);decargs['model_channels']=[16,16,8]
            decoder=randomize(scvae(source,kind+'_decoder',dict(out_channels=channels,
                up_block_type=['SparseResBlockC2S3d']*2,pred_subdiv=False,**decargs)))
            decode=CachedDecode(source,decoder,2).eval()
            exported_encoder=None;exported_decoder=None
            for variant,rows in enumerate(([(0,x,y,z) for x in range(3) for y in range(3) for z in range(2)],
                                            [(0,0,0,0),(0,1,0,0),(0,4,0,0),(0,5,1,0),(0,4,2,1)])):
                coords=torch.tensor(rows,dtype=torch.int64);features=torch.randn(len(rows),6)
                if kind=='shape':
                    vertices=features[:,:3];intersected=(features[:,3:]>0).float()
                    latent=encoder(sparse.SparseTensor(vertices,coords),sparse.SparseTensor(intersected,coords))
                    enc=ShapeEncode(source,encoder);args=(vertices,intersected,coords);names=['vertices','intersected','coords']
                else:
                    latent=encoder(sparse.SparseTensor(features,coords));enc=MaterialEncode(source,encoder)
                    args=(features,coords);names=['features','coords']
                if exported_encoder is None:exported_encoder=export(kind+'_encoder',enc,args,names,['latent','latent_coords'],dynamic(names+['latent','latent_coords']))
                actual=run(exported_encoder,args,names)
                compare(kind+'_encoder_features_'+str(variant),latent.feats,actual[0])
                check(kind+'_encoder_coordinates_'+str(variant),np.array_equal(latent.coords.numpy(),actual[1]))
                direct=decoder(latent);args=(latent.feats,latent.coords,coords);names=['features','coords','surface_coords']
                if exported_decoder is None:exported_decoder=export(kind+'_cached_decoder',decode,args,names,['fields','decoded_coords'],dynamic(names+['fields','decoded_coords']))
                expected=decode(*args);actual=run(exported_decoder,args,names)
                compare(kind+'_source_encoder_cache_'+str(variant),direct.feats,expected[0])
                compare(kind+'_cached_decoder_'+str(variant),direct.feats,actual[0])
                check(kind+'_restored_exact_support_'+str(variant),np.array_equal(coords.numpy(),actual[1]))
        current(inputs);result=dict(schema='lma.program-checks/1',suite='supra_learned_components',passed=len(checks),checks=checks,
            input_fingerprint=inputs,completeModelsRun=0,phoneTests=0,trainedWeights=False,source='Supra-3D/SUPRA-Tex@cee4435652d0f23737bd28d5704e0fae9830b411')
        (out/'results.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
