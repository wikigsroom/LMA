"""Prepare an explicitly selected, local safetensors snapshot for Android.

Offline asset preparation, NOT an Android/remote inference service. Does not
fetch a checkpoint, execute installation scripts, accept pickle or overwrite
an export. Normal program checks use only randomly initialized tiny graphs.
"""
import argparse,ast,gc,hashlib,importlib,importlib.util,json,os,sys
from pathlib import Path
from fetch_shape_sources import ROOT,verify

def reference(pipeline):
    lock=verify();entry=lock['sources'][0 if pipeline=='triposg' else 1]
    # PartCrafter's package is named src; use only the pinned code path.
    sys.path.insert(0,str(ROOT/entry['directory']))
    prefix=entry['package']
    flow=importlib.import_module(prefix+'.models.transformers.'+('triposg' if pipeline=='triposg' else 'partcrafter')+'_transformer')
    name=prefix+'.models.autoencoders.autoencoder_kl_triposg'
    if pipeline!='triposg' and name not in sys.modules:
        # The selected path only decodes RF latents. Upstream's point-cloud
        # *encoder* imports torch_cluster FPS, which is not used by this path.
        # Load the hash-verified module with exactly that import replaced by a
        # rejecting guard; never emulate FPS or change decoder instructions.
        path=ROOT/entry['directory']/prefix/'models/autoencoders/autoencoder_kl_triposg.py'
        tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path));removed=0
        for index,node in enumerate(tree.body):
            if isinstance(node,ast.ImportFrom) and node.module=='torch_cluster':
                assert [a.name for a in node.names]==['fps'];removed+=1
                tree.body[index]=ast.parse("def fps(*args, **kwargs):\n    raise RuntimeError('Point-cloud encoding is outside the image-to-shape decoder export')").body[0]
        assert removed==1
        parent=name.rsplit('.',1)[0];parent_spec=importlib.util.spec_from_file_location(parent,path.parent/'__init__.py',submodule_search_locations=[str(path.parent)])
        package=importlib.util.module_from_spec(parent_spec);sys.modules[parent]=package
        module=importlib.util.module_from_spec(importlib.util.spec_from_file_location(name,path));sys.modules[name]=module
        try:
            exec(compile(ast.fix_missing_locations(tree),str(path),'exec'),module.__dict__)
            parent_spec.loader.exec_module(package)
        except BaseException:sys.modules.pop(name,None);sys.modules.pop(parent,None);raise
    vae=importlib.import_module(name)
    return entry,getattr(flow,'TripoSGDiTModel' if pipeline=='triposg' else 'PartCrafterDiTModel'),vae.TripoSGVAEModel

def write_manifest(out,pipeline,config,identity):
    from shape_catalogue import definition
    (out/'shape-config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    roles={'config':'shape-config.json','image_encoder':'image_encoder.onnx','flow':'flow.onnx','cache':'cache.onnx','query':'query.onnx'}
    for role in list(roles):
        if (out/(roles[role]+'.data')).is_file():roles[role+'_data']=roles[role]+'.data'
    components=[]
    for role,name in roles.items():
        path=out/name;digest=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
        components.append(dict(role=role,path=name,format='json' if role=='config' else 'onnx_data' if role.endswith('_data') else 'onnx',
            bytes=path.stat().st_size,sha256=digest,url='',repository='local/export',revision=identity))
    b=dict(schema='lma.model-bundle/2',id=pipeline+'_onnx_'+identity[:12],modelId=pipeline+'_onnx_'+identity[:12],
        name=pipeline+' · local FP32 export',description='用户自行选择的离线转换资产；手机推理、质量和内存未测。',
        recipeId=pipeline+'_onnx_cpu_v1',catalogue=False,components=components,**definition(pipeline),
        resources=dict(source='unmeasured',estimatedPeakRamBytes=0),content=dict(classification='unclassified',basis='none'),
        evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0),
        license=dict(name='Original model and per-file terms apply',url='https://github.com/'+config['source']['repository'],status='component_terms_apply'))
    (out/'lma-bundle.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'export-receipt.json').write_text(json.dumps(dict(schema='lma.rf-shape-export-receipt/1',source=config['source'],
        snapshotIdentity=identity,network=False,exportTracingExecutesDummyForwards=True,phoneInferenceTested=False,physicalDeviceTests=0,components=components),indent=2)+'\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pipeline',choices=['triposg','partcrafter','partcrafter_scene'],required=True)
    p.add_argument('--snapshot',type=Path,required=True,help='Existing local HF snapshot, safetensors only');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    source=a.snapshot.resolve();out=a.output.resolve();assert source.is_dir() and not out.exists(),'Use an existing snapshot and new export directory'
    # Refuse all fallback pickle loading. Models may use safetensors shards.
    for name in ['transformer','vae','image_encoder_dinov2']:
        directory=source/name;assert directory.is_dir() and list(directory.glob('*.safetensors')),'Missing local safetensors: '+name
    entry,FlowModel,VaeModel=reference(a.pipeline)
    import torch
    from transformers import Dinov2Model
    from shape_graphs import ImageEncoder,Flow,Cache,Query,portable_attention,export_graph
    torch.set_num_threads(4);out.mkdir(parents=True)
    read=lambda n:json.loads((source/n).read_text(encoding='utf-8'))
    fc,vc,ic,pre,schedule=[read(n) for n in ['transformer/config.json','vae/config.json','image_encoder_dinov2/config.json','feature_extractor_dinov2/preprocessor_config.json','scheduler/scheduler_config.json']]
    assert pre.get('resample')==3 and all(pre.get(k) is True for k in ['do_resize','do_center_crop','do_normalize','do_rescale','do_convert_rgb'])
    assert pre['crop_size']['height']==pre['crop_size']['width'] and abs(pre['rescale_factor']-1/255)<1e-12
    assert not schedule.get('use_dynamic_shifting',False) and schedule.get('_class_name') in ['RectifiedFlowScheduler','FlowMatchEulerDiscreteScheduler']
    # LMA uses the publisher's RectifiedFlowScheduler's i/steps sequence; reject
    # upstream variants rather than silently applying another scheduler.
    assert schedule.get('_class_name')=='RectifiedFlowScheduler','Use the matched publisher RF scheduler'
    cfg=dict(schema='lma.rf-shape-export/1',pipeline=a.pipeline,dtype='float32',opset=17,source={k:entry[k] for k in ['repository','revision']},
        latentChannels=int(fc['in_channels']),decoderWidth=int(vc['width_decoder']),imageSize=int(pre['crop_size']['height']),resizeShortest=int(pre['size']['shortest_edge']),
        encoderTokens=(int(pre['crop_size']['height'])//int(ic['patch_size']))**2+1,encoderWidth=int(ic['hidden_size']),maxTokens=4096,
        maxParts=1 if a.pipeline=='triposg' else min(16,int(fc['max_num_parts'])),imageMean=pre['image_mean'],imageStd=pre['image_std'],
        scheduleShift=float(schedule.get('shift',1)),trainingTimesteps=int(schedule.get('num_train_timesteps',1000)))
    identity=hashlib.sha256(json.dumps(dict(configs=[fc,vc,ic,pre,schedule],pipeline=a.pipeline),sort_keys=True).encode())
    # Hash identity covers every local selected asset, without copying them.
    for file in sorted(source.rglob('*.safetensors')):
        identity.update(file.relative_to(source).as_posix().encode())
        with file.open('rb') as stream:identity.update(hashlib.file_digest(stream,'sha256').digest())
    c,w,e,ew=cfg['latentChannels'],cfg['decoderWidth'],cfg['encoderTokens'],cfg['encoderWidth'];part=a.pipeline!='triposg';b=2 if part else 1
    image=Dinov2Model.from_pretrained(source/'image_encoder_dinov2',local_files_only=True,use_safetensors=True,attn_implementation='eager').float().eval()
    export_graph(ImageEncoder(image),(torch.zeros(1,3,cfg['imageSize'],cfg['imageSize']),),out/'image_encoder.onnx',['pixel_values'],'image_embeddings',{})
    del image;gc.collect()
    flow=FlowModel.from_pretrained(source/'transformer',local_files_only=True,use_safetensors=True).float().eval();portable_attention(flow,flow.global_attn_block_ids if part else ())
    export_graph(Flow(flow,part),(torch.randn(b,8,c),torch.ones(b),torch.zeros(b,e,ew)),out/'flow.onnx',['latents','timestep','image_embeddings'],'velocity',{'latents':{0:'parts',1:'tokens'},'timestep':{0:'parts'},'image_embeddings':{0:'parts'},'velocity':{0:'parts',1:'tokens'}})
    del flow;gc.collect()
    vae=VaeModel.from_pretrained(source/'vae',local_files_only=True,use_safetensors=True).float().eval();portable_attention(vae)
    export_graph(Cache(vae),(torch.randn(1,8,c),),out/'cache.onnx',['latents'],'cache',{'latents':{1:'tokens'},'cache':{1:'tokens'}})
    export_graph(Query(vae),(torch.randn(1,8,w),torch.randn(1,11,3)),out/'query.onnx',['cache','points'],'sdf',{'cache':{1:'tokens'},'points':{1:'queries'},'sdf':{1:'queries'}})
    write_manifest(out,a.pipeline,cfg,identity.hexdigest());print('Offline export written; import lma-bundle.json and its selected components. No phone/model quality acceptance is implied.')

if __name__=='__main__':main()
