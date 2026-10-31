"""Explicit offline source-matched SAM / MV-SAM3D + depth -> signed CPU recipe.

The profile names local JSON constructor settings and safetensors, never Python
plugins, pickle, Hub identifiers or installers. Conversion stays on the host;
every exported inference stage subsequently executes on the Android phone.
"""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from export_uniforge import read_config,export
from sam_catalogue import graphs,roles,recipe


def manifest(output,cfg,selected):
    multi=cfg['pipeline']=='mv_sam3d_da3';template=recipe(multi);components=[]
    def digest(p):
        with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    for role,name in roles(multi).items():
        path=output/name;assert path.is_file()
        components.append(dict(role=role,path=name,url='',repository='local/export',revision=cfg['source']['revision'],format='json' if role=='config' else 'onnx',bytes=path.stat().st_size,sha256=digest(path)))
        side=output/(name+'.data')
        if role!='config' and side.exists():components.append(dict(role=role+'_data',path=side.name,url='',repository='local/export',revision=cfg['source']['revision'],format='onnx_data',bytes=side.stat().st_size,sha256=digest(side)))
    identity=hashlib.sha256(json.dumps(components,sort_keys=True).encode()).hexdigest();model_id=cfg['pipeline']+'_'+identity[:16]
    bundle=dict(schema='lma.model-bundle/2',id=model_id,modelId=model_id,recipeId=template['id'],catalogue=False,name=template['name'],
        **template['definition'],components=components,tags=['local','3d','vertex_color','user_selected_assets','cpu','onnx'],source=cfg['source'],
        description='Source-matched local SAM export; complete model and phone not tested',resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
        content=dict(classification='unclassified',basis='none'),evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0),
        license=dict(name='SAM 3D, depth, DINO and component terms apply',url='https://github.com/'+cfg['source']['repository'],status='component_terms_apply'))
    (output/'lma-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n','utf-8')
    (output/'conversion-receipt.json').write_text(json.dumps(dict(schema='lma.offline-conversion/1',source=cfg['source'],auxiliarySources=cfg['auxiliarySources'],
        inputs={str(p):digest(p) for p in selected},networkUsed=False,completeModelsRun=0,phoneTests=0,weightsBundledWithApk=False,precision='float32',inputPolicy=cfg['inputPolicy'],surfacePolicy=cfg['surfacePolicy']),indent=2)+'\n','utf-8')


def prepare(profile_path,output):
    import torch
    from spatial_portable import strict_weights
    from sam_portable import SamSource,checked_model
    from sam_components import structure,Structure,Slat,mesh_decoder,MeshFields,Occupancy
    from sam_conditioner import conditioner,Conditioner
    from depth_components import moge,MoGe,da3,DA3,Metric
    profile_path=Path(profile_path);profile=read_config(profile_path);assert profile['schema']=='lma.sam-local-inputs/1' and profile['target'] in ('D08','D09')
    multi=profile['target']=='D09';source=SamSource(profile['target']);models=profile['models'];runtime=profile['runtime'];selected=[profile_path]
    assert set(models)==set(graphs(multi));root=profile_path.resolve().parent
    def local(stage,key):
        candidate=root/models[stage][key];assert candidate.is_file() and not candidate.is_symlink()
        path=candidate.resolve();assert path.suffix in ('.json','.safetensors');selected.append(path);return path
    def settings(stage):return read_config(local(stage,'config'))
    def loaded(stage,model):return strict_weights(model,local(stage,'weights'))
    output=Path(output).resolve();assert not output.exists(),'Refusing to replace an existing export';output.parent.mkdir(parents=True,exist_ok=True)
    working=Path(tempfile.mkdtemp(prefix='.lma-sam-',dir=output.parent))
    try:
        def save(name,model,args,names,outputs,dynamic=None):
            export(model,args,working/(name+'.onnx'),names,outputs,dynamic)
        cfg=dict(schema='lma.sam-export/1',pipeline='mv_sam3d_da3' if multi else 'sam3d_objects',dtype='float32',opset=17,
            source={k:source.record[k] for k in ('repository','revision')},views=4 if multi else 1,inputPolicy='explicit_rgba_fixed_square',surfacePolicy='source_flexicubes_vertex_attributes')
        lock=json.loads((Path(__file__).resolve().parents[1]/'third_party/portable-sparse-source-lock.json').read_text('utf-8'))
        records={s['id']:s for s in lock['sources']}
        cfg['auxiliarySources']={k:{n:records[k][n] for n in ('repository','revision')} for k in ('MOGE','TIMM','DA3') if k!='DA3' or multi}
        for key in ('structureSchedule','slatSchedule','structureFusion','slatFusion','poseConvention','prune','slatNormalization'):cfg[key]=runtime[key]
        for name,key in (('ss_conditioner','structureCondition'),('slat_conditioner','slatCondition')):
            settings_=settings(name);_,_,_,model=conditioner(profile['target'],settings_);model=loaded(name,model)
            image_size=int(settings_['imageSize']);assert 14<=image_size<=1024;keys=[];spans=[];tokens=0
            for module,entry in zip(model.module_list,settings_['embedders']):
                if entry['type']=='dino':
                    registers=module.backbone.num_register_tokens if module.prenorm_features else 0
                    length=(module.input_size//module.backbone.patch_size)**2+1+registers
                else:length=(module.input_size//module.patch_size)**2
                for key_,_ in entry['inputs']:
                    assert key_ not in keys and key_ in ('image','mask','rgb_image','rgb_image_mask','pointmap','rgb_pointmap');keys.append(key_)
                    if entry['type']=='pointmap':spans.append((tokens,tokens+length))
                    tokens+=length
            points='pointmap' in keys;assert set(keys)==set(['image','mask','rgb_image','rgb_image_mask']+(['pointmap','rgb_pointmap'] if points else []))
            values=[];names=[]
            for key_ in keys:
                channels=1 if key_ in ('mask','rgb_image_mask') else 3;values.append(torch.zeros(1,channels,image_size,image_size));names.append(key_)
                if key_ in ('pointmap','rgb_pointmap'):values.append(torch.ones(1,1,image_size,image_size));names.append(key_+'_valid')
            save(name,Conditioner(model,keys,spans),tuple(values),names,['condition','unconditional','without_pointmap'])
            cfg[key]=dict(imageSize=image_size,tokens=tokens,width=model.embed_dims,pointmap=points,keys=names,preprocessing=settings_['preprocessing'])
            del model;gc.collect()
        sc=settings('structure_flow');model=loaded('structure_flow',structure(source,sc['args'],sc['heads']));capture=multi;layer=int(sc.get('captureLayer',6)) if capture else None
        wrapper=Structure(model,layer);cfg['heads']=[]
        for name,rows,channels in wrapper.heads:
            guidance=sc['guidance'][name];cfg['heads'].append(dict(name=name,rows=rows,channels=channels,strength=guidance['strength'],pointStrength=guidance.get('pointStrength',0),interval=guidance['interval']))
        shape=next(x for x in cfg['heads'] if x['name']=='shape');resolution=round(shape['rows']**(1/3));assert resolution**3==shape['rows'] and shape['channels']==8
        cfg['structureResolution']=resolution;total=sum(h['rows']*h['channels'] for h in cfg['heads']);condition=cfg['structureCondition'];shortcut=model.is_shortcut_model
        assert cfg['structureSchedule']['shortcut']==shortcut
        args=(torch.zeros(1,total),torch.ones(1),torch.zeros(1,condition['tokens'],condition['width']));names=['features','time','condition']
        # Wrapper signature always accepts shortcut; unused argument is omitted
        # from the final graph for ordinary FlowMatching networks.
        args+=(torch.ones(1),);outs=['velocity']+(['attention_q','attention_k'] if capture else [])
        if shortcut:save('structure_flow',wrapper,args,names+['shortcut'],outs)
        else:save('structure_flow',_NoShortcut(wrapper),args[:3],names,outs)
        heads_=model.num_heads;cfg['structureFlow']=dict(capture=capture,attentionHeads=heads_,attentionWidth=sc['args']['model_channels']//heads_,pointmapCfg=sc.get('pointmapCfg',False));del model,wrapper;gc.collect()
        dc=settings('structure_decoder');assert dc['latent_channels']==8 and dc['out_channels']==1;dc['reshape_input_to_cube']=False
        model=loaded('structure_decoder',checked_model(source,'models/sparse_structure_vae.py','SparseStructureDecoder',dc));cfg['occupancyResolution']=resolution*2**(len(dc['channels'])-1)
        save('structure_decoder',Occupancy(model,resolution),(torch.zeros(1,resolution**3,8),),['features'],['occupancy']);del model;gc.collect()
        coords=torch.tensor([[0,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],dtype=torch.int64)
        fc=settings('slat_flow');model=loaded('slat_flow',checked_model(source,'models/structured_latent_flow.py','SLatFlowModel',fc['args']));assert fc['args']['resolution']==cfg['occupancyResolution'] and fc['args']['in_channels']==fc['args']['out_channels']==8
        cfg['slatHeads']=[dict(name='shape',rows=1,channels=8,strength=fc['strength'],pointStrength=fc.get('pointStrength',0),interval=fc['interval'])]
        condition=cfg['slatCondition'];shortcut=model.is_shortcut_model;assert cfg['slatSchedule']['shortcut']==shortcut;wrapper=Slat(source,model,int(fc.get('captureLayer',6)) if capture else None)
        args=(torch.zeros(4,8),coords,torch.ones(1),torch.zeros(1,condition['tokens'],condition['width']));names=['features','coords','time','condition'];outs=['velocity']+(['attention_q','attention_k','attention_coords'] if capture else []);dynamic={k:{0:k+'_rows'} for k in ('features','coords','velocity')+ (('attention_q','attention_coords') if capture else ())}
        if shortcut:save('slat_flow',wrapper,(*args,torch.ones(1)),names+['shortcut'],outs,dynamic)
        else:save('slat_flow',_NoShortcut(wrapper),args,names,outs,dynamic)
        ah=model.num_heads;cfg['slatFlow']=dict(capture=capture,attentionHeads=ah,attentionWidth=fc['args']['model_channels']//ah,pointmapCfg=fc.get('pointmapCfg',False));del model,wrapper;gc.collect()
        mc=settings('mesh_decoder');assert mc['latent_channels']==8 and mc['resolution']==cfg['occupancyResolution'];model=loaded('mesh_decoder',mesh_decoder(source,mc));cfg.update(meshResolution=mc['resolution']*4,meshColor=bool(mc.get('representation_config',{}).get('use_color',False)));cfg['meshChannels']=101 if cfg['meshColor'] else 53
        save('mesh_decoder',MeshFields(source,model),(torch.zeros(4,8),coords),['features','coords'],['fields','decoded_coords'],{k:{0:k+'_rows'} for k in ('features','coords','fields','decoded_coords')});del model;gc.collect()
        cfg['depth']=runtime['depth'];size=cfg['depth']['imageSize'];assert 28<=size<=1024 and size%14==0
        if multi:
            for name,wrapper_type,outputs in (('depth_anyview',DA3,['depth','confidence','sky','camera']),('depth_metric',Metric,['depth','sky'])):
                _,model=da3(settings(name));model=loaded(name,model);save(name,wrapper_type(model),(torch.zeros(1,4,3,size,size),),['images'],outputs);del model;gc.collect()
        else:
            _,model=moge(settings('depth_moge'));model=loaded('depth_moge',model);assert cfg['depth']['maskThreshold']==model.mask_threshold
            save('depth_moge',MoGe(model,size),(torch.zeros(1,3,size,size),),['images'],['points','mask']);del model;gc.collect()
        (working/'sam-config.json').write_text(json.dumps(cfg,indent=2)+'\n','utf-8');manifest(working,cfg,selected);working.rename(output)
    except BaseException:
        shutil.rmtree(working);raise
    return output


def _NoShortcut(wrapper):
    import torch
    class Boundary(torch.nn.Module):
        def __init__(self):super().__init__();self.module=wrapper
        def forward(self,*args):return self.module(*args,args[0].new_zeros(1))
    return Boundary()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--profile',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1');prepare(a.profile,a.output);print('Prepared explicit local SAM assets; complete model and phone validation are not implied.')


if __name__=='__main__':main()
