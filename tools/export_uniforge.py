"""Explicit offline UniForge assets -> closed same-phone CPU cascade.

Requires complete source-matched safetensors. Stage flow weights must already
include their trained LoRA deltas; no pickle, Hub, upstream installer or network
code executes. Each original learned architecture is constructed separately.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def read_config(path):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=65536
    value=json.loads(path.read_text('utf-8'));assert isinstance(value,dict);return value


def export(module,args,path,inputs,outputs,dynamic=None):
    import torch
    import onnx
    with torch.inference_mode():
        torch.onnx.export(module.eval(),args,str(path),input_names=inputs,output_names=outputs,
            dynamic_axes=dynamic or {},opset_version=17,dynamo=False,external_data=True,
            custom_opsets={'lma.spatial':1},do_constant_folding=True)
    graph=onnx.load(str(path),load_external_data=True)
    assert [i.name for i in graph.graph.input]==inputs,'Required graph input was pruned; select a trained matched architecture'
    assert [i.name for i in graph.graph.output]==outputs
    onnx.save_model(graph,str(path),save_as_external_data=True,all_tensors_to_one_file=True,
        location=path.name+'.data',size_threshold=0)
    onnx.checker.check_model(str(path))
    del graph;gc.collect()


def manifest(output,cfg,selected):
    from uniforge_catalogue import recipe,roles
    template=recipe();components=[]
    for role,name in roles().items():
        file=output/name;assert file.is_file()
        components.append(dict(role=role,path=name,url='',repository='local/export',revision=cfg['source']['revision'],format='json' if role=='config' else 'onnx',bytes=file.stat().st_size,sha256=hashlib.file_digest(file.open('rb'),'sha256').hexdigest()))
        if role!='config':
            side=output/(name+'.data')
            if side.exists():components.append(dict(role=role+'_data',path=side.name,url='',repository='local/export',revision=cfg['source']['revision'],format='onnx_data',bytes=side.stat().st_size,sha256=hashlib.file_digest(side.open('rb'),'sha256').hexdigest()))
    identity=hashlib.sha256(json.dumps(components,sort_keys=True).encode()).hexdigest();model_id='uniforge3d_'+identity[:16]
    bundle=dict(schema='lma.model-bundle/2',id=model_id,modelId=model_id,recipeId=template['id'],catalogue=False,name=template['name'],
        **template['definition'],components=components,tags=['local','3d','pbr_material','user_selected_assets','cpu','onnx'],
        source=cfg['source'],description='Local UniForge export; phone and complete model not tested',resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
        content=dict(classification='unclassified',basis='none'),evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0),
        license=dict(name='UniForge, TRELLIS, VGGT and DINO component terms apply',url='https://github.com/xibushu/UniForge3D',status='component_terms_apply'))
    (output/'lma-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n','utf-8')
    receipt=dict(schema='lma.offline-conversion/1',source=cfg['source'],completeModelsRun=0,phoneTests=0,
        networkUsed=False,weightsBundledWithApk=False,inputs={str(p):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in selected},
        inputPolicy=cfg['inputPolicy'],surfacePolicy=cfg['surfacePolicy'],precision='float32')
    (output/'conversion-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n','utf-8')


def prepare(profile_path,output):
    import torch
    from spatial_portable import Source,strict_weights
    from uniforge_components import dino,joint,JointPredictions,FrozenConditioner,StageAdapter,RoutedFlow,flow,structure_decoder,sparse_decoder,ShapeDecode,MaterialDecode
    from uniforge_catalogue import GRAPHS
    profile=read_config(profile_path);assert profile['schema']=='lma.uniforge-local-inputs/1'
    source=Source('D05');_,raw=source.read('uniforge3d/configs/pipeline.json');upstream=json.loads(raw)
    root=profile_path.resolve().parent;selected=[profile_path];stages=profile['stages']
    required={'dino','joint','conditioner','shape512','shape1024','texture','structure_decoder','shape_decoder','texture_decoder'}
    assert set(stages)==required
    def asset(stage,key):
        path=root/stages[stage][key];assert path.is_file() and not path.is_symlink();path=path.resolve();selected.append(path);return path
    def configuration(stage):return read_config(asset(stage,'config'))
    def load(stage,model):return strict_weights(model,asset(stage,'weights'))
    def free(*models):
        # Called only after the graph export returns and local references end.
        gc.collect()
    output=Path(output).resolve();assert not output.exists(),'Refusing to replace existing model assets'
    output.parent.mkdir(parents=True,exist_ok=True)
    working=Path(tempfile.mkdtemp(prefix='.lma-uniforge-',dir=output.parent))
    try:
        def save(name,model,args,names,outputs,dynamic=None):
            assert name in GRAPHS;export(model,args,working/(name+'.onnx'),names,outputs,dynamic)
        config=configuration('dino');assert config['hidden_size']==1024 and config.get('patch_size',16)==16 and config.get('num_register_tokens',4)==4
        model=load('dino',dino(source,config))
        for size in (512,1024):save('dino'+str(size),model,(torch.zeros(1,4,3,size,size),),['images'],['features'])
        del model;free()
        args=upstream['sparse_structure']['model']['args'];lora=None
        if stages['joint'].get('withStage1Lora',False):
            w=upstream['sparse_structure']['weights'];lora=dict(dit=w['dit_lora'],vggt=w['vggt_lora'])
        model=load('joint',joint(source,args,lora))
        save('structure_flow',JointPredictions(model),(torch.zeros(1,8,16,16,16),torch.ones(1),torch.zeros(1,4,3,448,448),torch.zeros(1,4,1029,1024)),['noisy','time','images','dino'],['positive','negative'])
        del model;free()
        sc=configuration('structure_decoder');assert sc['name']=='SparseStructureDecoder' and sc['args']['latent_channels']==8 and sc['args']['out_channels']==1
        dc=dict(sc['args']);dc['use_fp16']=False;model=load('structure_decoder',structure_decoder(source,dc))
        occupancy=16*2**(len(dc['channels'])-1)
        assert occupancy>=64 and occupancy<=256 and occupancy%64==0
        save('structure_decoder',model,(torch.zeros(1,8,16,16,16),),['latents'],['occupancy'])
        del model;free()
        coords=torch.tensor([[0,16,16,16],[0,16,16,17],[0,16,17,16],[0,17,16,16]],dtype=torch.int64)
        model=load('conditioner',FrozenConditioner(source).float().eval())
        outs=['layer4','layer11','layer17','layer23','points','confidence']
        save('conditioner',model,(torch.zeros(1,4,3,448,448),coords),['images','coords'],outs,{'coords':{0:'condition_rows'}})
        del model;free()
        for key,config_key in (('shape512','structured_latent_512'),('shape1024','structured_latent_1024'),('texture','texture')):
            model=load(key,flow(source,upstream[config_key]['model']['args']))
            layers=tuple(torch.zeros(1,4,1029,2048) for _ in range(4))
            save(key+'_adapter',StageAdapter(model.adapter),layers,['layer4','layer11','layer17','layer23'],['delta'])
            n=4;tokens=1029 if key=='shape512' else 4101;names=['features','coords','time','full','selected'];values=(torch.zeros(n,32),coords,torch.ones(1),torch.zeros(1,4,tokens,1024),torch.zeros(n,dtype=torch.int64))
            if key=='texture':names+=['shape'];values+= (torch.zeros(n,32),)
            dynamic={k:{0:'latent_rows'} for k in names if k in ('features','coords','selected','shape')};dynamic['velocity']={0:'latent_rows'}
            save(key+'_flow',RoutedFlow(source,model,key=='texture'),values,names,['velocity'],dynamic)
            del model;free()
        shape=configuration('shape_decoder');assert shape['name']=='FlexiDualGridVaeDecoder';dc=dict(shape['args']);dc.pop('resolution');margin=dc.pop('voxel_margin',.5);assert margin==.5;dc.update(out_channels=7,use_fp16=False,pred_subdiv=True)
        assert dc['latent_channels']==32 and len(dc['model_channels'])==5
        shape_model=load('shape_decoder',sparse_decoder(source,dc));wrapper=ShapeDecode(source,shape_model)
        args=(torch.zeros(4,32),coords);names=['features','coords'];outs=['fields','decoded_coords']+[v for i in range(4) for v in ('guide'+str(i),'guide_coords'+str(i))]
        dynamic={k:{0:k+'_rows'} for k in names+outs}
        # Both resolutions use exactly the same VAE learned weights. The native
        # stage supplies the explicit 512/1024 geometric grid to FDG decoding.
        for key in ('shape512_decoder','shape1024_decoder'):save(key,wrapper,args,names,outs,dynamic)
        # Obtain tracing guides from the actual source decoder; no weights are
        # initialized or fabricated to force a particular subdivision pattern.
        with torch.inference_mode():guides=wrapper(*args)[2:]
        tc=configuration('texture_decoder');assert tc['name']=='SparseUnetVaeDecoder';td=dict(tc['args']);td['use_fp16']=False
        assert td['out_channels']==6 and td['latent_channels']==32 and not td['pred_subdiv'] and len(td['model_channels'])==5
        texture_model=load('texture_decoder',sparse_decoder(source,td));tnames=names+outs[2:]
        save('texture_decoder',MaterialDecode(source,texture_model),(*args,*guides),tnames,['materials','material_coords'],{k:{0:k+'_rows'} for k in tnames+['materials','material_coords']})
        del shape_model,texture_model,wrapper;free()
        cfg=dict(schema='lma.uniforge-export/1',pipeline='uniforge3d',source={k:source.record[k] for k in ('repository','revision')},dtype='float32',opset=17,
            views=4,imageSizes=[512,1024,448],structureChannels=8,structureResolution=16,latentChannels=32,featureWidth=1024,conditionWidth=2048,decoderLevels=4,
            occupancyResolution=occupancy,inputPolicy='explicit_rgba_foreground',surfacePolicy='raw_fdg_sat_handoff',
            shapeNormalization=upstream['texture']['shape_slat_normalization'],textureNormalization=upstream['texture']['texture_slat_normalization'])
        (working/'uniforge-config.json').write_text(json.dumps(cfg,indent=2)+'\n','utf-8');manifest(working,cfg,selected);working.rename(output)
    except BaseException:
        # Only the private temporary directory created above is removed.
        shutil.rmtree(working);raise
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    prepare(a.profile,a.output);print('UniForge assets prepared locally; no phone or complete trained-model inference is implied.')


if __name__=='__main__':main()
