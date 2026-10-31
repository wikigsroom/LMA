"""Offline, explicit local safetensors -> matched on-phone point-VAE bundle.

No model download, executable plugins, pickle or output replacement. The
posterior can use its mean or a seeded sample; this is reconstruction, not
image-conditioned rectified-flow generation.
"""
import argparse, gc, hashlib, json, os
from pathlib import Path
from export_shape import reference


def export(snapshot, output, pipeline):
    import torch
    from shape_graphs import Cache, Query, portable_attention, export_graph
    from pointcloud_graphs import PointEncoder
    from pointcloud_catalogue import definition
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    source, out = snapshot.resolve(), output.resolve()
    assert source.is_dir() and not out.exists(), 'Existing local snapshot and new output directory required'
    directory = source/'vae' if (source/'vae').is_dir() else source
    assert list(directory.glob('*.safetensors')), 'Local VAE safetensors required'
    settings = json.loads((directory/'config.json').read_text('utf-8'))
    assert settings.get('in_channels', 3) == 3 and settings.get('embedding_type', 'frequency') == 'frequency'
    entry, _, VAE = reference(pipeline)
    model = VAE.from_pretrained(directory, local_files_only=True, use_safetensors=True).float().eval()
    portable_attention(model)
    c, w = model.config.latent_channels, model.config.width_decoder
    assert 1 <= c <= 512 and 8 <= w <= 4096
    # Work in a private sibling; failures leave no importable half bundle.
    import tempfile, shutil
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.lma-points-', dir=out.parent))
    try:
        torch.set_num_threads(2)
        export_graph(PointEncoder(model), (torch.randn(1,31,6), torch.randn(1,8,6)), temporary/'encoder.onnx',
                     ['points','sampled_points'], 'moments', {'points':{1:'points'},'sampled_points':{1:'tokens'},'moments':{1:'tokens'}})
        export_graph(Cache(model), (torch.randn(1,8,c),), temporary/'cache.onnx', ['latents'], 'cache', {'latents':{1:'tokens'},'cache':{1:'tokens'}})
        export_graph(Query(model), (torch.randn(1,8,w),torch.randn(1,11,3)), temporary/'query.onnx', ['cache','points'], 'sdf', {'cache':{1:'tokens'},'points':{1:'queries'},'sdf':{1:'queries'}})
        del model; gc.collect()
        identity = hashlib.sha256(json.dumps(settings,sort_keys=True).encode())
        for file in sorted(directory.glob('*.safetensors')):
            with file.open('rb') as stream: identity.update(hashlib.file_digest(stream,'sha256').digest())
        cfg = dict(schema='lma.rf-pointcloud-export/1',pipeline=pipeline+'_points',dtype='float32',opset=17,
                   source={k:entry[k] for k in ['repository','revision']},latentChannels=c,decoderWidth=w,
                   maxTokens=4096,maxPoints=16384,features='xyz_normals',coordinates='publisher_normalized',
                   sampling='seeded_mt19937_four_times_then_cpu_fps_first_argmax',posterior='mean_or_sample')
        (temporary/'shape-config.json').write_text(json.dumps(cfg,indent=2)+'\n','utf-8')
        components=[]
        for file in sorted(temporary.iterdir()):
            role='config' if file.name=='shape-config.json' else file.name.split('.')[0]+('_data' if file.name.endswith('.data') else '')
            with file.open('rb') as stream: digest=hashlib.file_digest(stream,'sha256').hexdigest()
            components.append(dict(role=role,path=file.name,format='json' if role=='config' else 'onnx_data' if role.endswith('_data') else 'onnx',bytes=file.stat().st_size,sha256=digest,url=''))
        bundle=dict(schema='lma.model-bundle/2',id=pipeline+'_points_'+identity.hexdigest()[:12],modelId=pipeline+'_points_'+identity.hexdigest()[:12],
                    name=pipeline+' · point-cloud VAE',description='本地点云 VAE 重建；非图像扩散生成。',recipeId=pipeline+'_points_onnx_cpu_v1',catalogue=False,
                    components=components,**definition(pipeline+'_points'),resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
                    content=dict(classification='unclassified',basis='none'),license=dict(name='Original component terms apply',url='https://github.com/'+entry['repository'],status='component_terms_apply'),
                    evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0))
        (temporary/'lma-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n','utf-8')
        (temporary/'export-receipt.json').write_text(json.dumps(dict(schema='lma.pointcloud-export-receipt/1',source=cfg['source'],components=components,network=False,trainedModelValidation=False,phoneTests=0),indent=2)+'\n','utf-8')
        temporary.rename(out)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return bundle


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pipeline',choices=['triposg','partcrafter'],required=True)
    p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(dict(id=export(a.snapshot,a.output,a.pipeline)['id'],network=False,phoneTests=0)))
