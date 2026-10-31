"""Random tiny actual SAM / MV-SAM learned definitions -> native CPU ORT.

No trained model assets, CUDA, emulators or phone runs. Tests vary sparse support
after export so traced coordinates cannot masquerade as a dynamic adapter.
"""
import json
from pathlib import Path
import subprocess
import sys
import warnings
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import numpy as np
    import torch
    from torch import nn
    from sam_portable import SamSource,checked_model
    from sam_components import structure,Structure,Slat,mesh_decoder,MeshFields,Occupancy
    torch.set_num_threads(2);torch.manual_seed(308099)
    out=ROOT/'build/sam-component-tests';out.mkdir(exist_ok=True)
    inputs=fingerprint('tools/test_sam_components.py','tools/sam_components.py','tools/sam_portable.py',
        'tools/spatial_portable.py','tools/spatial_sparse_graphs.py','third_party/portable-sparse-source-lock.json',
        'native/spatial','tests/expansion-native/sparse_graph.cpp')
    checks=[]
    def check(name,value,**extra):assert value,(name,extra);checks.append(dict(case=name,**extra))
    def compare(name,a,b):
        a=a.detach().numpy() if hasattr(a,'detach') else np.asarray(a);b=np.asarray(b)
        check(name,a.shape==b.shape and np.allclose(a,b,rtol=8e-4,atol=4e-5),shape=list(a.shape),error=float(np.max(np.abs(a-b))) if a.size else 0)
    def randomize(model):
        for name,p in model.named_parameters():
            parent=name.rsplit('.',2)[-2] if '.' in name else ''
            if (parent.startswith('norm') or name.endswith('.gamma')) and p.ndim<=2 and p.numel()<1000:nn.init.ones_(p)
            else:nn.init.normal_(p,std=.045)
        return model.float().eval().requires_grad_(False)
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(path):return alias+'/'+path.relative_to(ROOT).as_posix()
    def export(label,model,args,names,outputs,dynamic=None):
        print('export '+label,flush=True)
        with torch.no_grad():
            expected=model(*args)
            for value in (expected if isinstance(expected,tuple) else (expected,)):
                if value.is_floating_point():check(label+'_finite_reference',bool(torch.isfinite(value).all()))
        file=out/(label+'.onnx')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');torch.onnx.export(model,args,file,input_names=names,output_names=outputs,
                opset_version=17,dynamo=False,custom_opsets={'lma.spatial':1},external_data=False,dynamic_axes=dynamic)
        return file
    def run(file,args,names):
        print('native '+file.stem,flush=True)
        request=out/'request.json';request.write_text(json.dumps(dict(graph=native(file),inputs=[dict(name=name,dtype='float32' if a.is_floating_point() else 'int64',shape=list(a.shape),values=a.flatten().tolist()) for name,a in zip(names,args)])),'utf-8')
        p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_sparse_graph.exe'),native(request)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        check(file.stem+'_native',p.returncode==0,error=p.stderr[-600:]);return [np.array(v['values']).reshape(v['shape']) for v in json.loads(p.stdout)]
    try:
        for target in ('D08','D09'):
            source=SamSource(target)
            heads=[dict(name='shape',channels=8,position=dict(type='ShapePositionEmbedder',args=dict(model_channels=32,resolution=4,patch_size=2))),
                   dict(name='scale',channels=3,position=dict(type='LearntPositionEmbedder',args=dict(model_channels=32,token_len=1))),
                   dict(name='6drotation_normalized',channels=6,position=dict(type='LearntPositionEmbedder',args=dict(model_channels=32,token_len=1)))]
            model=randomize(structure(source,dict(in_channels=8,model_channels=32,cond_channels=24,out_channels=8,num_blocks=2,num_heads=4,
                qk_rms_norm=True,qk_rms_norm_cross=True,is_shortcut_model=True),heads))
            wrapper=Structure(model,1).eval();names=['features','time','condition','shortcut']
            args=(torch.randn(1,73),torch.rand(1),torch.randn(1,9,24),torch.rand(1));file=export(target+'_mot',wrapper,args,names,['velocity','attention_q','attention_k'])
            for variant in range(2):
                args=(torch.randn(1,73),torch.rand(1),torch.randn(1,9,24),torch.rand(1));expected=wrapper(*args)
                check(target+'_finite_mot',all(bool(torch.isfinite(value).all()) for value in expected));actual=run(file,args,names)
                for i,value in enumerate(expected):compare(target+'_mot_'+str(variant)+'_'+str(i),value,actual[i])
            # The protected shape stream must not attend layout / pose values.
            a=list(args);b=list(args);b[0]=a[0].clone();b[0][:,64:]+=4
            compare(target+'_shape_protection',wrapper(*a)[0][:,:64],wrapper(*b)[0][:,:64].detach().numpy())
            model=randomize(checked_model(source,'models/structured_latent_flow.py','SLatFlowModel',dict(resolution=8,in_channels=8,
                model_channels=32,cond_channels=24,out_channels=8,num_blocks=2,num_heads=4,patch_size=2,num_io_res_blocks=1,
                io_block_channels=[16],qk_rms_norm=True,qk_rms_norm_cross=False,is_shortcut_model=True)))
            wrapper=Slat(source,model,1).eval();names=['features','coords','time','condition','shortcut'];file=None
            for variant,rows in enumerate(([[0,x,y,z] for x in range(3) for y in range(2) for z in range(2)],[[0,0,0,0],[0,1,0,0],[0,4,2,1],[0,5,3,0]])):
                args=(torch.randn(len(rows),8),torch.tensor(rows,dtype=torch.int64),torch.rand(1),torch.randn(1,9,24),torch.rand(1))
                if file is None:file=export(target+'_slat',wrapper,args,names,['velocity','attention_q','attention_k','attention_coords'],{k:{0:k+'_rows'} for k in ('features','coords','velocity','attention_q','attention_coords')})
                expected=wrapper(*args);actual=run(file,args,names)
                for i,value in enumerate(expected):compare(target+'_slat_'+str(variant)+'_'+str(i),value,actual[i])
            model=randomize(mesh_decoder(source,dict(resolution=4,model_channels=256,latent_channels=8,num_blocks=2,num_heads=4,
                mlp_ratio=2,attn_mode='swin',window_size=2,qk_rms_norm=True,representation_config=dict(use_color=True))))
            wrapper=MeshFields(source,model).eval();names=['features','coords'];file=None
            for variant,rows in enumerate(([[0,0,0,0],[0,1,0,0]],[[0,0,0,0],[0,3,0,0],[0,2,2,1]])):
                args=(torch.randn(len(rows),8),torch.tensor(rows,dtype=torch.int64))
                if file is None:file=export(target+'_mesh_fields',wrapper,args,names,['fields','field_coords'],{k:{0:k+'_rows'} for k in names+['fields','field_coords']})
                expected=wrapper(*args);actual=run(file,args,names)
                compare(target+'_mesh_projection_'+str(variant),expected[0],actual[0]);check(target+'_mesh_subdivision_'+str(variant),actual[0].shape==(len(rows)*64,101) and np.array_equal(expected[1].numpy(),actual[1]))
            model=randomize(checked_model(source,'models/sparse_structure_vae.py','SparseStructureDecoder',dict(out_channels=1,
                latent_channels=8,num_res_blocks=1,channels=[16,8],num_res_blocks_middle=1,norm_type='layer')))
            wrapper=Occupancy(model,2).eval();args=(torch.randn(1,8,8),);file=export(target+'_occupancy',wrapper,args,['features'],['occupancy'])
            compare(target+'_actual_occupancy_decoder',wrapper(*args),run(file,args,['features'])[0])
        current(inputs);report=dict(schema='lma.program-checks/1',suite='sam_learned_components',passed=len(checks),checks=checks,input_fingerprint=inputs,
            completeModelsRun=0,phoneTests=0,trainedWeights=False,sourceDefinitions=['D08','D09'],dynamicSparseSupport=True)
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
