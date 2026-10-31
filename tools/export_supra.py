"""Prepare explicit local SUPRA-Tex assets for the fixed Android CPU adapter.

Only source-matched safetensors, standard local Qwen processor files and source
configs are accepted. PBR weights must include the trained LoRA and modality
embeddings. There is no Hub access, executable checkpoint or remote inference.
"""
import argparse
import ast
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
STAGES=('text','vae','pbr','shape_encoder','material_encoder','shape_decoder','material_decoder','completion')
GRAPHS=('qwen_text','qwen_encode','qwen_decode','qwen_material','shape_encoder','material_encoder','shape_decoder','material_decoder','completion')


def config(path):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=131072
    value=json.loads(path.read_text('utf-8'));assert isinstance(value,dict);return value


def local_layout(source,processor_dir,resolution):
    from PIL import Image
    from transformers import AutoProcessor
    _,text=source.read('deployment/runtime/qwen/examples/qwen_image_21/pbr/inference_utils.py')
    node=next(n for n in ast.parse(text).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROMPT' for t in n.targets))
    prompt=ast.literal_eval(node.value)
    processor=AutoProcessor.from_pretrained(str(processor_dir),local_files_only=True,trust_remote_code=False)
    processor.image_processor.size={'shortest_edge':resolution**2,'longest_edge':resolution**2}
    system='Comprehend and analyze the provided prompt.'
    message=[dict(role='system',content=[dict(type='text',text=system)])]
    drop=processor.apply_chat_template(message,tokenize=True,return_dict=False)
    drop=len(drop) if not drop or isinstance(drop[0],int) else len(drop[0])
    template=f'<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n<image1><|vision_start|><|image_pad|><|vision_end|>{prompt}<|im_end|>\n<|im_start|>assistant\n'
    values=processor(text=[template],images=[Image.new('RGB',(resolution,resolution),'white')],padding=True,return_tensors='pt')
    ids=values.input_ids[0].tolist();grid=values.image_grid_thw[0].tolist()
    assert grid==[1,resolution//16,resolution//16] and len(ids)<=2048 and int(values.attention_mask.min())==1
    image_id=processor.tokenizer.encode('<|image_pad|>',add_special_tokens=False)
    assert len(image_id)==1 and ids.count(image_id[0])==(resolution//32)**2
    relative=processor_dir/'tokenizer.json';assert relative.is_file() and not relative.is_symlink()
    return dict(prompt=prompt,template=template,tokenIds=ids,drop=drop,imageToken=image_id[0],grid=grid,
        mean=list(processor.image_processor.image_mean),std=list(processor.image_processor.image_std),
        patch=16,merge=2,temporal=2,vocabulary=151936),relative


def manifest(output,cfg,selected):
    from supra_catalogue import recipe,roles
    template=recipe();components=[]
    for role,name in roles().items():
        file=output/name;assert file.is_file();fmt='json' if name.endswith('.json') else 'onnx'
        components.append(dict(role=role,path=name,url='',repository='local/export',revision=cfg['source']['revision'],format=fmt,
            bytes=file.stat().st_size,sha256=hashlib.file_digest(file.open('rb'),'sha256').hexdigest()))
        side=output/(name+'.data')
        if fmt=='onnx' and side.exists():components.append(dict(role=role+'_data',path=side.name,url='',repository='local/export',revision=cfg['source']['revision'],format='onnx_data',bytes=side.stat().st_size,sha256=hashlib.file_digest(side.open('rb'),'sha256').hexdigest()))
    identity=hashlib.sha256(json.dumps(components,sort_keys=True).encode()).hexdigest();model='supratex_'+identity[:16]
    value=dict(schema='lma.model-bundle/2',id=model,modelId=model,recipeId=template['id'],catalogue=False,name=template['name'],
        **template['definition'],components=components,tags=['local','3d','pbr_material','user_selected_assets','cpu','onnx'],
        source=cfg['source'],description='Local SUPRA-Tex export; complete model and phone not tested',resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
        content=dict(classification='unclassified',basis='none'),evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0),
        license=dict(name='SUPRA-Tex, Qwen and SCVAE component terms apply',url='https://github.com/Supra-3D/SUPRA-Tex',status='component_terms_apply'))
    (output/'lma-bundle.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
    (output/'conversion-receipt.json').write_text(json.dumps(dict(schema='lma.offline-conversion/1',source=cfg['source'],
        networkUsed=False,completeModelsRun=0,phoneTests=0,weightsBundledWithApk=False,
        inputPolicy=cfg['inputPolicy'],precision='float32',inputs={str(p):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in selected}),indent=2)+'\n','utf-8')


def prepare(profile_path,output):
    import torch
    from transformers import Qwen3VLConfig,Qwen3VLForConditionalGeneration
    from spatial_portable import Source,strict_weights
    from supra_components import qwen_dit,qwen_pbr,FixedPBR,qwen_vae,VaeEncode,VaeDecode,VLFeatures,Completion,ShapeEncode,MaterialEncode,CachedDecode,scvae,definitions,QWEN
    from export_uniforge import export
    source=Source('D10');profile=config(profile_path);assert profile['schema']=='lma.supra-local-inputs/1'
    stages=profile['stages'];assert set(stages)==set(STAGES)
    root=profile_path.resolve().parent;selected=[profile_path]
    def asset(stage,key):
        unresolved=root/stages[stage][key];assert not unresolved.is_symlink();path=unresolved.resolve();assert path.is_file();selected.append(path);return path
    def spec(stage):return config(asset(stage,'config'))
    def load(stage,model):return strict_weights(model,asset(stage,'weights'))
    output=output.resolve();assert not output.exists(),'Choose a new model asset folder'
    output.parent.mkdir(parents=True,exist_ok=True);working=Path(tempfile.mkdtemp(prefix='.lma-supra-',dir=output.parent))
    try:
        resolution=profile.get('resolution',1024);assert type(resolution) is int and resolution==1024,'Released PBR material profile is 1024'
        processor=(root/profile['processor']).resolve();assert processor.is_dir()
        layout,tokenizer=local_layout(source,processor,resolution);selected.append(tokenizer);shutil.copyfile(tokenizer,working/'qwen-tokenizer.json')
        ids=torch.tensor([layout['tokenIds']],dtype=torch.int64);h=resolution//16;nimage=(resolution//32)**2
        flags=[i==layout['imageToken'] for i in layout['tokenIds'][layout['drop']:]]
        length=len(flags);width=4096
        def save(name,model,args,names,outputs,dynamic=None):
            assert name in GRAPHS;export(model,args,working/(name+'.onnx'),names,outputs,dynamic)
        # Validate the full source Qwen3-VL architecture, not a text-only stand-in.
        text_config=spec('text');formal=definitions(source,QWEN+'models/qwen_image_21_text_encoder.py').QwenImage21TextEncoder.QWEN_IMAGE_21_TEXT_ENCODER_CONFIG
        for section in ('text_config','vision_config'):
            assert all(text_config[section].get(k)==v for k,v in formal[section].items()),'Unmatched Qwen3-VL '+section
        cfg=Qwen3VLConfig(**text_config);cfg._attn_implementation='eager';cfg.text_config._attn_implementation='eager';cfg.vision_config._attn_implementation='eager'
        model=load('text',Qwen3VLForConditionalGeneration(cfg));wrapper=VLFeatures(model,layout['tokenIds'],layout['grid'],layout['drop'])
        save('qwen_text',wrapper,(ids,torch.zeros(h*h,1536)),['ids','pixels'],['features'])
        del model,wrapper;gc.collect()
        args=spec('vae');assert args.get('z_dim',64)==64 and args.get('in_channels',4)==4 and args.get('out_channels',4)==4
        assert args.get('dim_mult',[1,2,4,8,8])==[1,2,4,8,8]
        model=load('vae',qwen_vae(source,args));save('qwen_encode',VaeEncode(model),(torch.zeros(1,4,resolution,resolution),),['rgba'],['latent'])
        save('qwen_decode',VaeDecode(model),(torch.zeros(1,64,h,h),),['latent'],['rgba']);del model;gc.collect()
        args=spec('pbr');assert args==dict(patch_size=1,in_channels=64,out_channels=64,num_layers=32,attention_head_dim=128,num_attention_heads=32,context_in_dim=4096,mlp_ratio=3,axes_dims_rope=[16,56,56],eps=1e-6,causal_condition=True)
        model=load('pbr',qwen_pbr(source,qwen_dit(source,args)));wrapper=FixedPBR(model,flags,h,h)
        save('qwen_material',wrapper,(torch.zeros(1,2,64,h,h),torch.zeros(1,length,width),torch.zeros(1,64,h,h)),['noise','prompt','rgb'],['velocity']);del model,wrapper;gc.collect()
        # Trace exact surface topology once. All row counts are dynamic. These
        # are coordinate fixtures, never fabricated learned subdivision masks.
        surface=torch.tensor([[0,x,y,z] for x in range(2) for y in range(2) for z in range(2)],dtype=torch.int64)
        latent_coords=torch.tensor([[0,0,0,0]],dtype=torch.int64);vertices=torch.rand(8,3);edges=torch.ones(8,3)
        scvae_configs={}
        for stage in ('shape_encoder','material_encoder','shape_decoder','material_decoder'):
            item=spec(stage);args=dict(item['args']);args['use_fp16']=False
            assert args['latent_channels']==32 and len(args['model_channels'])==5
            if stage=='shape_encoder':assert item['name']=='FlexiDualGridVaeEncoder'
            if stage=='material_encoder':assert item['name']=='SparseUnetVaeEncoder' and args['in_channels']==6
            if stage=='shape_decoder':
                resolution=args.pop('resolution')
                assert item['name']=='FlexiDualGridVaeDecoder' and type(resolution) is int and 8<=resolution<=1024 and args.pop('voxel_margin',.5)==.5
                args['out_channels']=7
            if stage=='material_decoder':assert item['name']=='SparseUnetVaeDecoder' and args['out_channels']==6 and args['pred_subdiv'] is False
            model=load(stage,scvae(source,stage,args));scvae_configs[stage]=args
            if stage=='shape_encoder':wrapper=ShapeEncode(source,model);values=(vertices,edges,surface);names=['vertices','intersected','coords'];outs=['latent','latent_coords']
            elif stage=='material_encoder':wrapper=MaterialEncode(source,model);values=(torch.zeros(8,6),surface);names=['features','coords'];outs=['latent','latent_coords']
            else:wrapper=CachedDecode(source,model,4);values=(torch.zeros(1,32),latent_coords,surface);names=['features','coords','surface_coords'];outs=['fields','decoded_coords']
            dynamic={k:{0:k+'_rows'} for k in names+outs};save(stage,wrapper,values,names,outs,dynamic);del model,wrapper;gc.collect()
        _,raw=source.read('configs/inference_model.json');up=json.loads(raw);formal=up['models']['denoiser']['args'];args=spec('completion')
        assert args==formal,'The complete released Interleaved architecture and normalization are required'
        model=load('completion',source.namespace('supratex/models/interleaved_flow_transformer.py').InterleavedFlowTransformer(**args))
        wrapper=Completion(source,model);names=['features','coords','time','shape','observed','observed_coords']
        values=(torch.zeros(1,32),latent_coords,torch.ones(1),torch.zeros(1,32),torch.zeros(1,34),latent_coords)
        save('completion',wrapper,values,names,['velocity'],{k:{0:'observed_rows' if k.startswith('observed') else 'latent_rows'} for k in names+['velocity'] if k!='time'});del model,wrapper;gc.collect()
        dataset=up['dataset']['args'];_,partial=source.read('configs/partial_normalization.json');partial=json.loads(partial)
        cfg=dict(schema='lma.supratex-export/1',pipeline='supratex',source={k:source.record[k] for k in ('repository','revision')},dtype='float32',opset=17,
            resolution=1024,latentChannels=32,decoderLevels=4,inputPolicy='mesh_camera_rgba',surfacePolicy='original_mesh_exact_encoder_topology',
            qwen=layout,shapeNormalization=dataset['shape_slat_normalization'],pbrNormalization=dataset['pbr_slat_normalization'],partialNormalization=partial,
            sampler=dict(steps=25,shift=3,sigmaMin=1e-5,policy='euler_static_observation_no_cfg'))
        (working/'supra-config.json').write_text(json.dumps(cfg,indent=2)+'\n','utf-8');manifest(working,cfg,selected);working.rename(output)
    except BaseException:shutil.rmtree(working);raise
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    prepare(a.profile,a.output);print('Local SUPRA-Tex assets prepared; no trained-model inference or phone test is implied.')


if __name__=='__main__':main()
