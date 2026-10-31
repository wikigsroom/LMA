"""Prepare selected local Hunyuan Paint/DINO/VAE/RealESRGAN assets for Android.

No fetches, upstream pipeline scripts, arbitrary targets or pickle constructors.
The converter traces dummy forwards, not end-to-end trained model generation.
"""
import argparse,gc,hashlib,json,os
from pathlib import Path
from spatial_reference import ROOT,verify
from export_spatial import Weights
from paint_catalogue import PIPELINE,ROLES,definition


def config(path):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=65536
    result=json.loads(path.read_text('utf-8'));assert isinstance(result,dict)
    return result


def local_weights(folder):
    matches=[folder/n for n in ('diffusion_pytorch_model.safetensors','diffusion_pytorch_model.bin','model.safetensors','pytorch_model.bin') if (folder/n).is_file()]
    assert len(matches)==1,'Select a single unsharded matched weight file in each architecture directory'
    return matches[0]


def manifest(out,cfg,identity):
    (out/ROLES['config']).write_text(json.dumps(cfg,indent=2)+'\n','utf-8');components=[]
    roles=dict(ROLES)
    for role,path in list(roles.items()):
        if path.endswith('.onnx') and (out/(path+'.data')).is_file():roles[role+'_data']=path+'.data'
    for role,path in roles.items():
        file=out/path
        with file.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
        components.append(dict(role=role,path=path,format='json' if role in ('config','sampler') else 'onnx_data' if role.endswith('_data') else 'onnx',bytes=file.stat().st_size,sha256=sha,url='',repository='local/export',revision=identity))
    b=dict(schema='lma.model-bundle/2',id=PIPELINE+'_'+identity[:12],modelId=PIPELINE+'_'+identity[:12],name='Hunyuan3D Paint · local CPU export',recipeId=PIPELINE+'_onnx_cpu_v1',catalogue=False,
        **definition(),components=components,description='用户主动转换的六视图 PBR 资产；手机性能、完整模型与质量未测。',resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
        content=dict(classification='unclassified',basis='none'),evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0),
        license=dict(name='Tencent Hunyuan non-commercial; DINO/VAE/BasicSR/RealESRGAN component terms apply',url='https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1',status='component_terms_apply'))
    (out/'lma-bundle.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n','utf-8')
    (out/'export-receipt.json').write_text(json.dumps(dict(schema='lma.material-export-receipt/1',source=cfg['source'],components=components,network=False,exportTracingExecutesDummyForwards=True,completeModelInferenceTested=False,physicalDeviceTests=0),indent=2)+'\n','utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('unet','vae','dino','scheduler','upscaler','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--image-size',type=int,default=320,help='Fixed export resolution, 64..512, multiple of 64')
    a=p.parse_args();assert 64<=a.image_size<=512 and a.image_size%64==0
    out=a.output.resolve();assert not out.exists(),'Choose a new export directory'
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    lock=verify();entry=next(s for s in lock['sources'] if s['id']=='D07')
    import torch
    from diffusers import AutoencoderKL
    from transformers import Dinov2Config,Dinov2Model
    from paint_graphs import construct,static_positions,PaintFlow,VaeStatistics,VaeDecode,arguments,NAMES
    from paint_sampler import profiles
    from paint_reference import rrdb
    from shape_graphs import export_graph,ImageEncoder
    torch.set_num_threads(4)
    uc,vc,dc,sc=[config(f) for f in (a.unet/'config.json',a.vae/'config.json',a.dino/'config.json',a.scheduler)]
    assert vc.get('latent_channels',4)==4 and len(vc.get('block_out_channels',[]))==4
    assert dc.get('model_type')=='dinov2' and dc['hidden_size']==1536 and dc.get('patch_size',14)==14
    size=a.image_size;latent=size//8;dino_size=int(dc.get('image_size',224));assert 28<=dino_size<=518 and dino_size%14==0
    scaling=float(vc.get('scaling_factor',.18215));assert 0<scaling<=10
    files=[a.unet/'config.json',a.vae/'config.json',a.dino/'config.json',a.scheduler,local_weights(a.unet),local_weights(a.vae),a.upscaler]
    files+=sorted(a.dino.glob('*.safetensors'));assert files[-1].is_file()
    identity=hashlib.sha256(json.dumps(dict(size=size,source=entry['revision']),sort_keys=True).encode())
    for f in files:
        with f.open('rb') as stream:identity.update(hashlib.file_digest(stream,'sha256').digest())
    out.mkdir(parents=True)
    # Stage residency is sequential in preparation as well as Android execution.
    image=Dinov2Model.from_pretrained(a.dino,local_files_only=True,use_safetensors=True,attn_implementation='eager').float().eval()
    export_graph(ImageEncoder(image),(torch.zeros(1,3,dino_size,dino_size),),out/ROLES['image_encoder'],['pixel_values'],'image_embeddings',{})
    del image;gc.collect()
    vae=AutoencoderKL.from_config(vc).float().eval();weights=Weights(local_weights(a.vae));weights.load(vae,'',exact=True);del weights
    export_graph(VaeStatistics(vae),(torch.zeros(1,3,size,size),),out/ROLES['vae_encoder'],['image'],'statistics',{})
    export_graph(VaeDecode(vae),(torch.zeros(1,4,latent,latent),),out/ROLES['vae_decoder'],['latents'],'image',{})
    del vae;gc.collect()
    model,module=construct(uc);weights=Weights(local_weights(a.unet));weights.load(model,'',exact=True);del weights
    static_positions(module,6,latent)
    export_graph(PaintFlow(model),arguments(size,6,(dino_size//14)**2+1),out/ROLES['flow'],NAMES,'noise',{})
    del model;gc.collect()
    upscale=rrdb()(3,3,scale=4,num_feat=64,num_block=23,num_grow_ch=32).float().eval();weights=Weights(a.upscaler)
    prefix='params_ema.' if any(k.startswith('params_ema.') for k in weights.keys) else 'params.' if any(k.startswith('params.') for k in weights.keys) else ''
    weights.load(upscale,prefix,exact=True);del weights
    export_graph(upscale,(torch.zeros(1,3,size,size),),out/ROLES['upscale'],['image'],'upscaled',{})
    del upscale;gc.collect()
    sampler=profiles(sc);(out/ROLES['sampler']).write_text(json.dumps(sampler,separators=(',',':'),allow_nan=False)+'\n','utf-8')
    cfg=dict(schema='lma.material-export/1',pipeline=PIPELINE,dtype='float32',opset=17,source={k:entry[k] for k in ('repository','revision')},views=6,imageSize=size,
        dinoSize=dino_size,dinoResize=dino_size*256//224,dinoWidth=1536,dinoTokens=(dino_size//14)**2+1,vaeScaling=scaling,upscaleFactor=4,scheduler='UniPCMultistepScheduler',timestepSpacing='trailing')
    manifest(out,cfg,identity.hexdigest());print('Local material export prepared. No phone, quality or full-model acceptance is implied.')


if __name__=='__main__':main()
