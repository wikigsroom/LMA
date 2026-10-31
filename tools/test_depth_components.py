"""Random tiny actual source MoGe / DA3 exports and native ORT parity."""
import json
from pathlib import Path
import subprocess
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch
    import numpy as np
    from depth_components import moge,MoGe,da3,DA3
    torch.set_num_threads(2);torch.manual_seed(49214)
    out=ROOT/'build/depth-component-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('tools/test_depth_components.py','tools/depth_components.py','tools/local_definitions.py','tools/spatial_portable.py',
        'native/spatial','tests/expansion-native/sparse_graph.cpp','third_party/portable-sparse-source-lock.json')
    checks=[]
    def check(name,ok,**details):assert ok,(name,details);checks.append(dict(case=name,**details))
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def path(p):return alias+'/'+p.relative_to(ROOT).as_posix()
    def run(label,model,image,names):
        print('export '+label,flush=True);model.eval().requires_grad_(False)
        with torch.no_grad():expected=model(image)
        for value in expected:check(label+'_source_finite',bool(torch.isfinite(value).all()),shape=list(value.shape))
        file=out/(label+'.onnx')
        torch.onnx.export(model,(image,),str(file),input_names=['images'],output_names=names,opset_version=17,dynamo=False)
        request=dict(graph=path(file),inputs=[dict(name='images',dtype='float32',shape=list(image.shape),values=image.flatten().tolist())])
        (out/'request.json').write_text(json.dumps(request),'utf-8')
        actual=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',path(out/'request.json')],capture_output=True,text=True,encoding='utf-8',timeout=45)
        check(label+'_native_accept',actual.returncode==0,reason=actual.stderr[-800:])
        for name,a,b in zip(names,expected,json.loads(actual.stdout)):
            b=np.asarray(b['values'],dtype=np.float32).reshape(b['shape']);a=a.detach().numpy()
            check(label+'_'+name,a.shape==b.shape and np.allclose(a,b,rtol=1e-3,atol=4e-5),maxError=float(np.max(np.abs(a-b))))
        return expected
    try:
        source,model=moge(dict(encoder='dinov2_vits14',intermediate_layers=4,dim_proj=32,dim_upsample=[32,32,32],last_conv_channels=16),
            tiny_backbone=dict(img_size=56,embed_dim=48,depth=4,num_heads=4))
        image=torch.rand(1,3,56,56)
        with torch.no_grad():original=model(image,16)
        wrapper=MoGe(model,56)
        actual=run('moge',wrapper,image,['points','mask'])
        check('moge_closed_profile_matches_literal_forward',all(torch.allclose(a,original[k],atol=2e-6,rtol=2e-5) for a,k in zip(actual,['points','mask'])))
        config=dict(backbone=dict(name='vits',out_layers=[0,1,2,3],alt_start=1,qknorm_start=1,rope_start=1,cat_token=True),
            head=dict(dim_in=96,output_dim=2,features=16,out_channels=[16,24,32,48],pos_embed=True),camera=dict(dim_in=96))
        source,model=da3(config,tiny_backbone=dict(img_size=56,patch_size=14,embed_dim=48,depth=4,num_heads=4,alt_start=1,qknorm_start=1,rope_start=1,cat_token=True))
        # Distinct views must share the actual cross-view transformer, and the
        # second view must affect the first view's predictions.
        images=torch.randn(1,2,3,56,56)*.5
        expected=run('da3_joint',DA3(model),images,['depth','confidence','sky','camera'])
        changed=images.clone();changed[:,1]=changed[:,1]*-.8+.2
        with torch.no_grad():changed_result=DA3(model)(changed)
        check('da3_joint_view_coupling',not torch.allclose(expected[0][:,0],changed_result[0][:,0],atol=1e-6,rtol=1e-6))
        run('da3_changed_views',DA3(model),changed,['depth','confidence','sky','camera'])
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    (out/'results.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,phoneTests=0),indent=2)+'\n','utf-8')
    print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
