"""Explicit local DIS safetensors -> on-phone automatic foreground bundle."""
import argparse,hashlib,json,os,shutil,tempfile
from pathlib import Path


def export(weights,output,size=1024):
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    import torch
    from safetensors.torch import load_file
    from vision_components import construct,Foreground
    from shape_graphs import export_graph
    from fetch_vision_sources import verify
    from vision_catalogue import definition
    assert weights.is_file() and not weights.is_symlink() and weights.suffix=='.safetensors','Select explicit DIS safetensors'
    out=output.resolve();assert not out.exists() and size in [256,512,1024],'Use a new output and selected fixed image size'
    source=verify();model=construct().float().eval();state=load_file(str(weights),device='cpu')
    expected=model.state_dict();assert set(state)==set(expected),'DIS checkpoint keys must match the original ISNetDIS'
    for key,value in state.items():assert value.shape==expected[key].shape and torch.isfinite(value).all(),key
    model.load_state_dict(state,strict=True);del state
    out.parent.mkdir(parents=True,exist_ok=True);temporary=Path(tempfile.mkdtemp(prefix='.lma-foreground-',dir=out.parent))
    try:
        torch.set_num_threads(2)
        export_graph(Foreground(model),(torch.zeros(1,3,size,size),),temporary/'foreground.onnx',['pixels'],'mask',{})
        cfg=dict(schema='lma.foreground-export/1',pipeline='isnet_dis',dtype='float32',opset=17,imageSize=size,
                 source={k:source[k] for k in ['repository','revision']},preprocess='publisher_bilinear_uint8_mean_half',postprocess='publisher_bilinear_minmax_uint8')
        (temporary/'vision-config.json').write_text(json.dumps(cfg,indent=2)+'\n','utf-8')
        components=[]
        for file in sorted(temporary.iterdir()):
            role='config' if file.name=='vision-config.json' else 'foreground_data' if file.name.endswith('.data') else 'foreground'
            with file.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            components.append(dict(role=role,path=file.name,format='json' if role=='config' else 'onnx_data' if role.endswith('_data') else 'onnx',bytes=file.stat().st_size,sha256=digest,url=''))
        with weights.open('rb') as stream:identity=hashlib.file_digest(stream,'sha256').hexdigest()
        bundle=dict(schema='lma.model-bundle/2',id='isnet_dis_'+identity[:12]+'_'+str(size),modelId='isnet_dis_'+identity[:12]+'_'+str(size),name='DIS · 自动前景',description='手机 CPU 自动抠图；用户自行选择模型资产。',
                    recipeId='isnet_dis_onnx_cpu_v1',catalogue=False,components=components,**definition('isnet_dis'),resources=dict(source='unmeasured',estimatedPeakRamBytes=0),
                    content=dict(classification='unclassified',basis='none'),license=dict(name='Apache-2.0 / selected weights terms',url='https://github.com/'+source['repository'],status='component_terms_apply'),
                    evidence=dict(status='user_export_not_device_tested',acquisition='import_only',modelInferenceTested=False,physicalDeviceTests=0))
        (temporary/'lma-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n','utf-8')
        (temporary/'export-receipt.json').write_text(json.dumps(dict(schema='lma.foreground-receipt/1',source=cfg['source'],components=components,network=False,phoneTests=0),indent=2)+'\n','utf-8')
        temporary.rename(out)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return bundle


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--weights',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--size',type=int,default=1024,choices=[256,512,1024]);a=p.parse_args();print(json.dumps(dict(id=export(a.weights,a.output,a.size)['id'],network=False)))
