"""Independent official PyTorch oracle and UNTRAINED GGUF fixtures for old LTX.

Developer test files only. No downloads, real checkpoint or complete video output.
"""
import hashlib,json,os,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def environment():
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    sys.path[:0]=[str(ROOT/'build/soulx-python'),str(ROOT/'build/native-src/ltx-video')]
    import huggingface_hub
    if not hasattr(huggingface_hub,'cached_download'):
        def offline(*a,**kw):raise RuntimeError('Deprecated model downloads are disabled in the oracle')
        huggingface_hub.cached_download=offline
    from build_ltx098 import validate_sources
    lock=validate_sources()
    import hashlib,importlib.metadata
    for name,digest in lock['python_sources'].items():
        if hashlib.sha256((ROOT/'build/soulx-python'/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Pinned oracle dependency changed: '+name)
    for name,version in lock['python_versions'].items():
        if importlib.metadata.version(name)!=version:raise RuntimeError('Wrong oracle dependency version: '+name)
    import torch
    if torch.__version__!=lock['torch_runtime_version']:raise RuntimeError('Wrong oracle torch runtime')

def gguf(path,config,state,half=False):
    """Small test-only GGUF v3 writer; standard reversed tensor dimensions."""
    def string(s):
        b=s.encode('utf-8');return struct.pack('<Q',len(b))+b
    entries=[('general.architecture','lma-ltx-video-098'),('ltx098.config',json.dumps(config,separators=(',',':')))]
    header=b'GGUF'+struct.pack('<IQQ',3,len(state),len(entries))
    for key,value in entries:header+=string(key)+struct.pack('<I',8)+string(value)
    payload=[];offset=0
    for name,value in state.items():
        array=np.asarray(value,dtype='<f2' if half and value.ndim==2 and name.endswith('.weight') else '<f4',order='C')
        shape=list(array.shape)
        header+=string(name)+struct.pack('<I',len(shape))+b''.join(struct.pack('<Q',n) for n in reversed(shape))+struct.pack('<IQ',1 if array.dtype.itemsize==2 else 0,offset)
        raw=array.tobytes(); padding=(-len(raw))%32;payload.append(raw+b'\0'*padding);offset+=len(raw)+padding
    with path.open('wb') as stream:
        stream.write(header+b'\0'*((-len(header))%32))
        for data in payload:stream.write(data)

def main():
    environment()
    import torch
    from ltx_video.models.transformers.transformer3d import Transformer3DModel
    torch.set_num_threads(4); torch.manual_seed(3107)
    output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=True)
    lock=json.loads((ROOT/'third_party/ltx098-source-lock.json').read_text(encoding='utf-8'))
    base={k:v for k,v in lock['checkpoint_transformer_config'].items() if not k.startswith('_')}
    with torch.device('meta'):complete=Transformer3DModel(**base)
    layout={k:list(v.shape) for k,v in complete.state_dict().items()}
    digest=hashlib.sha256(json.dumps(layout,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if len(layout)!=715 or sum(p.numel() for p in complete.parameters())!=1923385472 or digest!=lock['checkpoint_transformer_layout_sha256']:raise RuntimeError('Full official architecture differs from exact pinned checkpoint header')
    del complete
    records=[]
    for layers,width,head in [(2,24,12),(3,32,16),(28,24,12)]:
        config=dict(base,num_attention_heads=2,attention_head_dim=head,cross_attention_dim=width,caption_channels=32,in_channels=8,out_channels=8,num_layers=layers)
        model=Transformer3DModel(**config).eval();state={k:v.detach().cpu().numpy() for k,v in model.state_dict().items()}
        stem='layers'+str(layers);gguf(output/(stem+'.gguf'),config,state);gguf(output/(stem+'-f16.gguf'),config,state,half=True)
        original={k:v.detach().clone() for k,v in model.state_dict().items()}
        half={k:torch.from_numpy(v.astype(np.float16).astype(np.float32)) if v.ndim==2 and k.endswith('.weight') else torch.from_numpy(v) for k,v in state.items()}
        for variant in ['global','per-token','masked','masked-padding']:
            if variant=='masked-padding':
                context=context.clone();context[:,3:]+=1000.
            else:
                n=12 if variant!='per-token' else 7;text=5
                latents=torch.randn(1,n,8);context=torch.randn(1,text,32)
                coords=torch.stack([torch.linspace(0,16,n),torch.arange(n)*32.,torch.arange(n)*64.]).unsqueeze(0)
                times=torch.tensor([.725]) if variant!='per-token' else torch.linspace(.05,.99,n).reshape(1,n)
                mask=torch.tensor([[1,1,1,0,0]]) if variant=='masked' else torch.ones(1,text,dtype=torch.int64)
            model.load_state_dict(original)
            with torch.inference_mode():result=model(latents,coords,context,times,encoder_attention_mask=mask).sample
            name=stem+'-'+variant
            case=dict(tokens=n,text_tokens=text,latents=latents.flatten().tolist(),context=context.flatten().tolist(),coordinates=coords.flatten().tolist(),timesteps=times.flatten().tolist(),text_mask=mask.flatten().tolist())
            (output/(name+'.json')).write_text(json.dumps(case)+'\n',encoding='utf-8');result.numpy().astype('<f4').tofile(output/(name+'-expected.f32'))
            model.load_state_dict(half)
            with torch.inference_mode():half_result=model(latents,coords,context,times,encoder_attention_mask=mask).sample
            half_result.numpy().astype('<f4').tofile(output/(name+'-f16-expected.f32'))
            records.append(dict(name=name,model=stem,parameters=sum(v.numel() for v in model.parameters()),layers=layers,values=result.numel()))
        if layers==2:
            gguf(output/'missing.gguf',config,{k:v for k,v in state.items() if k!='proj_out.bias'})
            gguf(output/'extra.gguf',config,dict(state,unexpected=np.zeros(1,dtype=np.float32)))
            broken=dict(config,positional_embedding_theta=9999.);gguf(output/'wrong-config.gguf',broken,state)
        del model
    (output/'cases.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    (output/'oracle.json').write_text(json.dumps(dict(source_revision=lock['sources'][0]['revision'],checkpoint_layout_sha256=digest,full_tensors=len(layout),full_parameters=1923385472,full_weights_loaded=False,synthetic_parameters=True,torch_version=torch.__version__,python_versions=lock['python_versions'],reference='Unmodified publisher Transformer3DModel.forward; F16 dense weights rounded then dequantized to float32'),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(records),full_layer_depth=28,trained=False,complete_video_pipeline=False)))

if __name__=='__main__':main()
