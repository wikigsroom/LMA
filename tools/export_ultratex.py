"""Explicit offline local UltraTex -> fixed Android CPU/PBR bundle.

No hub/network lookup, CUDA, checkpoint pickle execution or model download.
Use publisher-compatible local configs, safetensors and tokenizer assets. The
APK contains only this adapter, never the user's selected assets.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def config(path):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=65536
    value=json.loads(path.read_text('utf-8'));assert isinstance(value,dict);return value


def local_weights(path):
    assert path.is_file() and not path.is_symlink() and path.suffix=='.safetensors'
    from safetensors.torch import load_file
    import torch
    state=load_file(str(path),device='cpu')
    assert state and all((t.is_floating_point() and torch.isfinite(t).all()) or (name.endswith('num_batches_tracked') and t.dtype==torch.int64 and t.numel()==1 and int(t)>=0) for name,t in state.items())
    return state


def rename_graph(source,target):
    import onnx
    model=onnx.load(str(source),load_external_data=True)
    onnx.save_model(model,str(target),save_as_external_data=True,all_tensors_to_one_file=True,
                    location=target.name+'.data',size_threshold=0)
    onnx.checker.check_model(str(target))
    source.unlink();(source.parent/(source.name+'.data')).unlink(missing_ok=True)


def manifest(output,cfg,inputs):
    from ultratex_catalogue import recipe
    template=recipe(cfg['pipeline']);requirements={v['role']:v for v in template['requirements']}
    components=[]
    for role,rule in requirements.items():
        file=output/rule['matchFiles'][0]
        if not file.exists():assert not rule['required'];continue
        assert file.is_file() and not file.is_symlink()
        with file.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        components.append(dict(role=role,path=file.name,url='',repository='local/export',revision=cfg['source']['revision'],bytes=file.stat().st_size,sha256=digest,format=rule['formats'][0]))
    identity=hashlib.sha256(json.dumps(components,sort_keys=True).encode()).hexdigest()
    definition=template['definition']
    model_id=cfg['pipeline']+'_'+identity[:16]
    bundle=dict(id=model_id,modelId=model_id,recipeId=template['id'],catalogue=False,name=template['name'],**definition,components=components,
                tags=['local','3d','pbr_material','user_selected_assets','cpu','onnx'],
                source=dict(repository=cfg['source']['repository'],revision=cfg['source']['revision']))
    # The import format matches the existing full local model-bundle contract.
    bundle.update(schema='lma.model-bundle/2',description='Local selected CPU UltraTex export; phone and complete model not tested',
        resources=dict(source='unmeasured',estimatedPeakRamBytes=0),content=dict(classification='unclassified',basis='none'),
        evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0),
        license=dict(name='UltraTex / FLUX / text and tokenizer component terms apply',url='https://github.com/yiboz2001/UltraTex',status='component_terms_apply'))
    (output/'lma-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n','utf-8')
    receipts=[]
    for role,path in inputs:
        with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
        receipts.append(dict(role=role,bytes=path.stat().st_size,sha256=sha))
    (output/'export-receipt.json').write_text(json.dumps(dict(schema='lma.ultratex-export-receipt/1',source=cfg['source'],inputs=receipts,
        components=components,network=False,trainedModelsDownloaded=0,fullModelInferenceTested=False,physicalDeviceTests=0,
        differences=['portable six-view orthographic rig, not unpublished TexVerse camera metadata',
                     'float32 CPU sampling and platform RNG instead of CUDA/BF16 random stream',
                     'bounded CPU raster, xatlas UV and nearest observed texel fill']),indent=2)+'\n','utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family',choices=['flux1','flux2'],required=True)
    for name in ('flow-config','flow-weights','vae-config','vae-weights','albedo-lora','mr-lora','mr-decoder','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--clip',type=Path);p.add_argument('--t5',type=Path);p.add_argument('--qwen',type=Path)
    p.add_argument('--image-size',type=int,default=256)
    p.add_argument('--lora-scale',type=float,default=1.)
    p.add_argument('--float-attention',action='store_true')
    a=p.parse_args();out=a.output.resolve();assert not out.exists(),'Choose a new output directory'
    assert 32<=a.image_size<=512 and a.image_size%16==0
    assert (a.clip and a.t5 and not a.qwen) if a.family=='flux1' else (a.qwen and not a.clip and not a.t5)
    fc,vc=config(a.flow_config),config(a.vae_config)
    assert len(vc['ch_mult'])==4 and fc['in_channels']==vc['z_channels']*4
    if a.family=='flux1':assert vc['z_channels']==16 and fc['in_channels']==64
    else:assert vc.get('z_channels',32)==32 and fc['in_channels']==128
    selected=[('flow_config',a.flow_config),('flow',a.flow_weights),('vae_config',a.vae_config),('vae',a.vae_weights),
              ('albedo_lora',a.albedo_lora),('mr_lora',a.mr_lora),('mr_decoder',a.mr_decoder)]
    for _,path in selected:assert path.is_file() and not path.is_symlink()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    import torch
    from ultratex_codecs import autoencoder,export_codec,Decode,export_text
    from ultratex_flows import architecture,export,merge_lora
    from shape_graphs import export_graph
    torch.set_num_threads(4);out.mkdir(parents=True)
    text=export_text(a.family,dict(clip=a.clip,t5=a.t5,qwen=a.qwen),out)
    assert text['textWidth']==fc['context_in_dim']
    if a.family=='flux1':assert text['clipWidth']==fc['vec_in_dim']
    asset=[('tokenizer',a.t5/'spiece.model','t5.model'),('clip_tokenizer',a.clip/'tokenizer.json','clip-tokenizer.json')] if a.family=='flux1' else [('tokenizer',a.qwen/'tokenizer.json','qwen-tokenizer.json')]
    for role,path,name in asset:
        assert path.is_file() and not path.is_symlink() and path.stat().st_size<=32*1024*1024
        shutil.copyfile(path,out/name);selected.append((role,path))
    # Record every source config and shard, not just one filename in a folder.
    for name,path in [('clip',a.clip),('t5',a.t5),('qwen',a.qwen)]:
        if path:
            selected.append((name+'_config',path/'config.json'))
            if (path/'tokenizer_config.json').is_file():selected.append((name+'_tokenizer_config',path/'tokenizer_config.json'))
            shards=sorted(path.glob('*.safetensors'));assert shards
            selected.extend((name+'_shard',f) for f in shards)
    vae=autoencoder(a.family,vc);vae.load_state_dict(local_weights(a.vae_weights),strict=True)
    export_codec(vae,a.family,a.image_size,out)
    # Fine-tuned decoder must be complete and matched; never silently reuse
    # an RGB decoder for the separate metallic/roughness material pass.
    mr=local_weights(a.mr_decoder)
    if all(k.startswith('decoder.') for k in mr):mr={k[len('decoder.'):]:v for k,v in mr.items()}
    vae.decoder.load_state_dict(mr,strict=True);del mr
    export_graph(Decode(vae,a.family),(torch.zeros(1,fc['in_channels'],a.image_size//16,a.image_size//16),),
                 out/'mr_decoder.onnx',['latents'],'image',{})
    del vae;gc.collect()
    for pass_name,lora in [('albedo',a.albedo_lora),('mr',a.mr_lora)]:
        model,_=architecture(a.family,fc,bfloat16=not a.float_attention)
        model.load_state_dict(local_weights(a.flow_weights),strict=True)
        merge_lora(model,a.family,local_weights(lora),a.lora_scale)
        export(model,a.family,fc,out/'flow.onnx');rename_graph(out/'flow.onnx',out/(pass_name+'_flow.onnx'))
        del model;gc.collect()
    lock=config(ROOT/'third_party/ultratex-flow-source-lock.json')
    cfg=dict(schema='lma.ultratex-export/1',pipeline='ultratex_'+a.family,dtype='float32',opset=17,
             source={k:lock[k] for k in ('repository','revision')},imageSize=a.image_size,latentChannels=fc['in_channels'],
             cameraRig='lma_orthographic_y_up_six_v1',guidanceEmbedding=fc.get('guidance_embed',fc.get('use_guidance_embed',True)),**text)
    (out/'ultratex-config.json').write_text(json.dumps(cfg,indent=2)+'\n','utf-8')
    manifest(out,cfg,selected)
    print('UltraTex local CPU assets prepared. No full-model or phone execution is implied.')


if __name__=='__main__':main()
