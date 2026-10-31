"""Actual SAM DINO/timm point encoder/fuser and CFG conditioning branches."""
import json
from pathlib import Path
import subprocess
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch
    import numpy as np
    from sam_conditioner import conditioner,Conditioner
    torch.set_num_threads(2);torch.manual_seed(44091)
    out=ROOT/'build/sam-conditioner-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('tools/test_sam_conditioner.py','tools/sam_conditioner.py','tools/local_definitions.py','tools/spatial_portable.py',
        'third_party/portable-sparse-source-lock.json','native/spatial','tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(name,value,**details):assert value,(name,details);checks.append(dict(case=name,**details))
    def compare(name,a,b):
        a=a.detach().numpy() if hasattr(a,'detach') else np.asarray(a);b=np.asarray(b)
        check(name,a.shape==b.shape and np.allclose(a,b,atol=3e-5,rtol=1e-3),error=float(np.max(np.abs(a-b))) if a.shape==b.shape else None)
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def path(p):return alias+'/'+p.relative_to(ROOT).as_posix()
    try:
        for target in ('D08','D09'):
            for pointmap in (False,True):
                settings=dict(embedders=[dict(type='dino',args=dict(input_size=56,dino_model='dinov2_vits14_reg',prenorm_features=not pointmap),
                    inputs=[['image','crop'],['mask','crop'],['rgb_image','full'],['rgb_image_mask','full']])],
                    fuser=dict(use_pos_embedding='learned',projection_net_hidden_dim_multiplier=2.,projection_pre_norm=True))
                if pointmap:settings['embedders'].append(dict(type='pointmap',args=dict(input_size=16,patch_size=8,embed_dim=32,remap_output='exp'),inputs=[['pointmap','pointmap'],['rgb_pointmap','full_points']]))
                _,_,_,model=conditioner(target,settings,tiny_backbone=dict(img_size=56,embed_dim=48,depth=2,num_heads=4))
                model.eval().requires_grad_(False)
                keys=['image','mask','rgb_image','rgb_image_mask'];values=[torch.rand(1,3,56,56),torch.rand(1,1,56,56),torch.rand(1,3,56,56),torch.rand(1,1,56,56)]
                args=dict(zip(keys,values));spans=[]
                if pointmap:
                    start=4*17;spans=[(start,start+4),(start+4,start+8)]
                    for key in ('pointmap','rgb_pointmap'):
                        xyz=torch.rand(1,3,16,16);valid=torch.ones(1,1,16,16);valid[:,:,2:5,3:7]=0
                        keys.append(key);args[key]=torch.where(valid>0,xyz,torch.full_like(xyz,float('nan')));values.extend([xyz,valid])
                    point_encoder=model.module_list[1]
                    with torch.no_grad():
                        compare('literal_point_mask_scatter',point_encoder.embed_pointmap_windows(args['pointmap'])[0],point_encoder._lma_literal_windows(args['pointmap'])[0])
                wrapper=Conditioner(model,keys,spans)
                with torch.no_grad():
                    expected=wrapper(*values);literal=model(**args)
                    compare('source_conditional',expected[0],literal)
                    literal_u=model(**{k:torch.zeros_like(v) for k,v in args.items()});compare('source_unconditional_input_zero',expected[1],literal_u)
                    model.force_drop_modalities=['pointmap','rgb_pointmap'];literal_pm=model(**args);model.force_drop_modalities=None
                    compare('source_forced_pointmap_drop',expected[2],literal_pm)
                check('unconditional_retains_learned_bias_and_position',not torch.allclose(expected[1],torch.zeros_like(expected[1])))
                names=[]
                for key in keys:names.extend([key,key+'_valid'] if key in ('pointmap','rgb_pointmap') else [key])
                label=target+('_ss' if pointmap else '_slat');print('export '+label,flush=True);file=out/(label+'.onnx')
                torch.onnx.export(wrapper,tuple(values),str(file),opset_version=17,dynamo=False,input_names=names,output_names=['condition','unconditional','without_pointmap'])
                request=dict(graph=path(file),inputs=[dict(name=n,dtype='float32',shape=list(v.shape),values=v.flatten().tolist()) for n,v in zip(names,values)])
                (out/'request.json').write_text(json.dumps(request),'utf-8')
                run=subprocess.run([alias+'/build/spatial-worker-host/bin/lma_sparse_graph.exe',path(out/'request.json')],capture_output=True,text=True,encoding='utf-8',timeout=45)
                check(label+'_native_accept',run.returncode==0,reason=run.stderr[-700:])
                for index,(a,b) in enumerate(zip(expected,json.loads(run.stdout))):compare(label+'_branch_'+str(index),a,np.asarray(b['values']).reshape(b['shape']))
                changed=[v.clone() for v in values];changed[0]*=.1
                with torch.no_grad():new=wrapper(*changed)
                check('rgb_input_changes_conditional',not torch.allclose(new[0],expected[0]))
                compare('rgb_input_does_not_change_unconditional',new[1],expected[1])
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    (out/'results.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,physicalDeviceTests=0),indent=2)+'\n','utf-8')
    print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
