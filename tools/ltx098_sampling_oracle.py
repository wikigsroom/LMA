"""Offline publisher oracle for old-LTX geometry, RF sampling and trained DiT.

Synthetic text embeddings deliberately bypass T5; no complete video is claimed.
The trained oracle pages one publisher module's parameters into CPU memory at a
time, without replacing or reimplementing the publisher's forward equations.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from evidence import current,fingerprint
from ltx098_assets import Checkpoint,PREFIX,sha,validate_transformer
from ltx098_fixture import ROOT,environment,gguf


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def tensor_file(path,value):
    value.detach().cpu().numpy().astype('<f4').tofile(path)


def publisher_geometry(torch,width,height,frames,fps,channels):
    from ltx_video.models.transformers.symmetric_patchifier import SymmetricPatchifier
    from ltx_video.models.autoencoders.vae_encode import latent_to_pixel_coords_from_factors
    shape=(1,channels,(frames-1)//8+1,height//32,width//32)
    source=torch.arange(np.prod(shape),dtype=torch.float32).reshape(shape)/31
    patchifier=SymmetricPatchifier(1)
    tokens,coords=patchifier.patchify(source)
    pixel=latent_to_pixel_coords_from_factors(coords,(8,32,32),causal_fix=False).float()
    pixel[:,0]*=1/float(np.float32(fps))
    restored=patchifier.unpatchify(tokens,height//32,width//32,channels)
    assert torch.equal(source,restored)
    return tokens,pixel,restored


def scheduler():
    from ltx_video.schedulers.rf import RectifiedFlowScheduler
    result=RectifiedFlowScheduler(num_train_timesteps=1000,shifting=None,base_resolution=None,sampler='LinearQuadratic')
    result.set_timesteps(8)
    return result


def bf16_fixture(torch,path,config,state):
    payload=[];header={'__metadata__':{'config':json.dumps({'transformer':config})}};offset=0
    for name,value in state.items():
        blob=value.to(torch.bfloat16).view(torch.uint16).numpy().astype('<u2').tobytes()
        header[PREFIX+name]=dict(dtype='BF16',shape=list(value.shape),data_offsets=[offset,offset+len(blob)])
        payload.append(blob);offset+=len(blob)
    raw=json.dumps(header,separators=(',',':')).encode();raw+=b' '*((-len(raw))%8)
    import struct
    with path.open('wb') as stream:
        stream.write(struct.pack('<Q',len(raw)));stream.write(raw)
        for blob in payload:stream.write(blob)


def request(torch,shape,channels,caption):
    tokens,coords,_=publisher_geometry(torch,**shape,channels=channels)
    latents=torch.randn_like(tokens);context=torch.randn(1,5,caption)
    mask=torch.tensor([[1,1,1,0,0]],dtype=torch.int64)
    data=dict(operation='sample',**shape,text_tokens=5,latents=latents.flatten().tolist(),context=context.flatten().tolist(),text_mask=mask.flatten().tolist())
    return data,latents,context,coords,mask


def trajectory(torch,model,latents,context,coords,mask,output,prefix):
    rf=scheduler();sample=latents.clone();metrics=[];first=None
    for i,sigma in enumerate(rf.timesteps):
        start=time.monotonic()
        with torch.inference_mode():
            velocity=model(sample,coords,context,sigma.reshape(1),encoder_attention_mask=mask).sample
            sample=rf.step(velocity,sigma,sample).prev_sample
        if first is None:first=velocity.detach().clone()
        tensor_file(output/(prefix+'-step-'+str(i)+'.f32'),sample)
        metrics.append(dict(step=i,sigma=float(sigma),seconds=time.monotonic()-start,finite=bool(torch.isfinite(sample).all())))
        print(json.dumps(dict(event='oracle_step',name=prefix,**metrics[-1])),flush=True)
    tensor_file(output/(prefix+'-velocity.f32'),first)
    return metrics


def fixtures(torch,output,lock):
    from ltx_video.models.transformers.transformer3d import Transformer3DModel
    cases=[];rf=scheduler()
    for i,(width,height,frames,fps) in enumerate([(32,32,1,24),(64,96,17,29.97),(96,64,33,60),(32,32,257,240),(2048,2048,1,1)]):
        shape=dict(width=width,height=height,frames=frames,fps=fps)
        tokens,coords,restored=publisher_geometry(torch,**shape,channels=8)
        name='geometry-'+str(i);write(output/(name+'.json'),dict(operation='geometry',**shape));tensor_file(output/(name+'.f32'),coords)
        cases.append(dict(name=name,operation='geometry',tokens=tokens.shape[1],shape=list(restored.shape),sigmas=rf.timesteps.tolist()))
        if i<3:
            name='unpatchify-'+str(i);write(output/(name+'.json'),dict(operation='unpatchify',**shape,channels=8,latents=tokens.flatten().tolist()));tensor_file(output/(name+'.f32'),restored)
            cases.append(dict(name=name,operation='unpatchify'))
    for i,sigma in enumerate(rf.timesteps.tolist()+[.999998,.900001,.4218755,.0000001]):
        if sigma<=1e-6:continue
        sample=torch.randn(1,7,8);velocity=torch.randn_like(sample);t=torch.tensor(sigma)
        expected=rf.step(velocity,t,sample).prev_sample
        name='rf-global-'+str(i);write(output/(name+'.json'),dict(operation='rf_step',sample=sample.flatten().tolist(),velocity=velocity.flatten().tolist(),times=[float(t)],channels=8,per_token=False));tensor_file(output/(name+'.f32'),expected)
        cases.append(dict(name=name,operation='rf_step'))
    for i,times in enumerate([rf.timesteps.tolist()+[0.,1e-7,.999998,.4218755],[0.],[.725]]):
        sample=torch.randn(1,len(times),8);velocity=torch.randn_like(sample);t=torch.tensor([times])
        expected=rf.step(velocity,t,sample).prev_sample;name='rf-per-token-'+str(i)
        write(output/(name+'.json'),dict(operation='rf_step',sample=sample.flatten().tolist(),velocity=velocity.flatten().tolist(),times=t.flatten().tolist(),channels=8,per_token=True));tensor_file(output/(name+'.f32'),expected)
        cases.append(dict(name=name,operation='rf_step'))
    base={k:v for k,v in lock['checkpoint_transformer_config'].items() if not k.startswith('_')}
    neural=[]
    for layers in [2,28]:
        config=dict(base,num_attention_heads=2,attention_head_dim=12,cross_attention_dim=24,caption_channels=32,in_channels=8,out_channels=8,num_layers=layers)
        model=Transformer3DModel(**config).eval();original={k:v.detach().clone() for k,v in model.state_dict().items()}
        shape=dict(width=64,height=64,frames=17,fps=24);data,latent,context,coords,mask=request(torch,shape,8,32)
        name='layers'+str(layers);write(output/(name+'.json'),data)
        for precision in ['f32','f16']:
            state={k:v.half().float() if precision=='f16' and v.ndim==2 and k.endswith('.weight') else v for k,v in original.items()}
            model.load_state_dict(state);gguf(output/(name+'-'+precision+'.gguf'),config,{k:v.numpy() for k,v in state.items()},half=precision=='f16')
            metrics=trajectory(torch,model,latent,context,coords,mask,output,name+'-'+precision)
            neural.append(dict(name=name,precision=precision,steps=metrics,layers=layers))
        if layers==2:
            bf16_fixture(torch,output/'fixture.safetensors',config,original)
            state={k:v.to(torch.bfloat16).float() for k,v in original.items()};model.load_state_dict(state)
            metrics=trajectory(torch,model,latent,context,coords,mask,output,'converted')
            neural.append(dict(name=name,precision='converted',steps=metrics,layers=layers))
        del model
    return dict(math_cases=cases,neural_cases=neural,trained_weights_loaded=False,synthetic_parameters=True)


def trained(torch,output,checkpoint_path,lock):
    from ltx_video.models.transformers.transformer3d import Transformer3DModel
    assets=json.loads((ROOT/'third_party/ltx098-trained-assets.json').read_text(encoding='utf-8'))['models'][0]
    checkpoint=Checkpoint(checkpoint_path);config,items=validate_transformer(checkpoint)
    source_sha=sha(checkpoint_path)
    if checkpoint.length!=assets['bytes'] or source_sha!=assets['sha256']:raise ValueError('Unpinned trained checkpoint')
    with torch.device('meta'):model=Transformer3DModel(**{k:v for k,v in config.items() if not k.startswith('_')})
    model.eval();used=set();stats=dict(loads=0,max_scheduled_parameter_bytes=0)
    def load(prefix,module):
        state={name:torch.from_numpy(checkpoint.array(PREFIX+prefix+name)) for name in module.state_dict()}
        used.update(prefix+name for name in state)
        stats['loads']+=1;stats['max_scheduled_parameter_bytes']=max(stats['max_scheduled_parameter_bytes'],sum(v.numel()*4 for v in state.values()))
        module.load_state_dict(state,strict=True,assign=True)
    def pre(prefix):
        def hook(module,args):load(prefix,module)
        return hook
    def post(module,args,result):module.to_empty(device='meta')
    for name in ['patchify_proj','adaln_single','caption_projection','proj_out']+['transformer_blocks.'+str(i) for i in range(28)]:
        module=model.get_submodule(name)
        module.register_forward_pre_hook(pre(name+'.'));module.register_forward_hook(post,always_call=True)
    model.scale_shift_table=torch.nn.Parameter(torch.from_numpy(checkpoint.array(PREFIX+'scale_shift_table')),requires_grad=False);used.add('scale_shift_table')
    shape=dict(width=64,height=64,frames=17,fps=24);data,latent,context,coords,mask=request(torch,shape,128,4096)
    write(output/'trained.json',data)
    forward=dict(tokens=latent.shape[1],text_tokens=5,latents=data['latents'],context=data['context'],coordinates=coords.flatten().tolist(),timesteps=[1.],text_mask=data['text_mask'])
    write(output/'trained-forward.json',forward)
    metrics=trajectory(torch,model,latent,context,coords,mask,output,'trained')
    if used!=set(items):raise ValueError('Not every trained parameter was exercised: '+str(len(used)))
    return dict(trained_weights_loaded=True,synthetic_parameters=False,synthetic_text_embeddings=True,t5_executed=False,source_bytes=checkpoint.length,source_sha256=source_sha,parameters=sum(np.prod(v['shape']).item() for v in items.values()),tensors=len(used),layers=28,shape=shape,tokens=latent.shape[1],text_tokens=5,steps=metrics,parameter_paging=stats)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--checkpoint',type=Path);args=parser.parse_args()
    if args.output.exists():raise ValueError('Oracle output must be fresh')
    inputs=fingerprint('research/ltx098','tools/build_ltx098.py','tools/ltx098_sampling_oracle.py','tools/ltx098_fixture.py','tools/ltx098_assets.py','third_party/ltx098-source-lock.json','third_party/ltx098-trained-assets.json')
    environment();import torch
    torch.set_num_threads(4);torch.manual_seed(91317)
    args.output.mkdir(parents=True)
    lock=json.loads((ROOT/'third_party/ltx098-source-lock.json').read_text(encoding='utf-8'))
    record=trained(torch,args.output,args.checkpoint,lock) if args.checkpoint else fixtures(torch,args.output,lock)
    current(inputs)
    artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(args.output.iterdir()) if p.is_file()}
    record.update(source_revision=lock['sources'][0]['revision'],actual_publisher_forward=True,complete_video_pipeline=False,video_outputs=False,vae_executed=False,engine_registered=False,physical_android=False,artifacts=artifacts,input_fingerprint=inputs)
    write(args.output/'oracle.json',record)
    print(json.dumps({k:v for k,v in record.items() if k not in ['input_fingerprint','math_cases','neural_cases','steps']}))


if __name__=='__main__':main()
