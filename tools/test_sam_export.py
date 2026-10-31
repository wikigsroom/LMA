"""Run the real offline SAM export CLI with tiny random actual source networks.

Only test factories reduce learned dimensions. The public JSON profile cannot
select arbitrary code, a test mode, network access or pretrained constructors.
"""
import copy
import json
from pathlib import Path
import shutil
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import torch
    import onnx
    from safetensors.torch import save_file
    import sam_conditioner
    import depth_components
    from sam_portable import SamSource,checked_model
    from sam_components import structure,mesh_decoder
    from export_sam import prepare
    from sam_catalogue import graphs,roles
    torch.set_num_threads(2);torch.manual_seed(53741)
    inputs=fingerprint('tools/export_sam.py','tools/sam_catalogue.py','tools/sam_components.py','tools/sam_conditioner.py','tools/sam_portable.py','tools/depth_components.py','tools/local_definitions.py','tools/spatial_portable.py','tools/spatial_sparse_graphs.py','tools/test_sam_export.py','third_party/portable-sparse-source-lock.json')
    out=ROOT/'build/sam-export-tests';out.mkdir(exist_ok=True);checks=[]
    def check(case,value,**details):assert value,(case,details);checks.append(dict(case=case,**details))
    original_c=sam_conditioner.conditioner;original_m=depth_components.moge;original_d=depth_components.da3
    sam_conditioner.conditioner=lambda target,args:original_c(target,args,tiny_backbone=dict(img_size=56,embed_dim=48,depth=2,num_heads=4))
    depth_components.moge=lambda args:original_m(args,tiny_backbone=dict(img_size=56,embed_dim=48,depth=4,num_heads=4))
    tiny=dict(img_size=56,patch_size=14,embed_dim=48,depth=4,num_heads=4,alt_start=2,qknorm_start=1,rope_start=1,cat_token=True)
    depth_components.da3=lambda args:original_d(args,tiny_backbone=tiny)
    try:
        for target in ('D08','D09'):
            print('preparing '+target,flush=True);multi=target=='D09';directory=out/target;directory.mkdir(exist_ok=True);exported=directory/'export'
            if exported.exists():assert exported.parent.resolve()==directory.resolve();shutil.rmtree(exported)
            source=SamSource(target);models={}
            def asset(name,settings,model):
                for key,p in model.named_parameters():
                    parent=key.rsplit('.',2)[-2] if '.' in key else ''
                    if parent.startswith('norm') and p.ndim<=1:torch.nn.init.ones_(p)
                    else:torch.nn.init.normal_(p,std=.03)
                config=directory/(name+'.json');weights=directory/(name+'.safetensors');config.write_text(json.dumps(settings),'utf-8')
                save_file({k:v.contiguous().clone() for k,v in model.state_dict().items()},str(weights));models[name]=dict(config=config.name,weights=weights.name)
            for points,name in ((True,'ss_conditioner'),(False,'slat_conditioner')):
                settings=dict(imageSize=28,embedders=[dict(type='dino',args=dict(input_size=28,dino_model='dinov2_vits14_reg',prenorm_features=not points),inputs=[['image','crop'],['mask','crop'],['rgb_image','full'],['rgb_image_mask','full']])],
                    fuser=dict(use_pos_embedding='learned',projection_net_hidden_dim_multiplier=2.,projection_pre_norm=True),preprocessing=dict(boxFactor=1.,padding=.1,normalizer=dict(method='ssi')))
                if points:settings['embedders'].append(dict(type='pointmap',args=dict(input_size=16,patch_size=8,embed_dim=32,remap_output='exp'),inputs=[['pointmap','pointmap'],['rgb_pointmap','full_points']]))
                _,_,_,model=sam_conditioner.conditioner(target,settings);asset(name,settings,model);del model
            heads=[dict(name='shape',channels=8,position=dict(type='ShapePositionEmbedder',args=dict(model_channels=32,resolution=4,patch_size=2))),dict(name='scale',channels=3,position=dict(type='LearntPositionEmbedder',args=dict(model_channels=32,token_len=1)))]
            sc=dict(args=dict(in_channels=8,model_channels=32,cond_channels=48,out_channels=8,num_blocks=2,num_heads=4,qk_rms_norm=True,qk_rms_norm_cross=True,is_shortcut_model=False),heads=heads,guidance={n:dict(strength=0,interval=None) for n in ('shape','scale')},captureLayer=1)
            asset('structure_flow',sc,structure(source,sc['args'],heads))
            dc=dict(out_channels=1,latent_channels=8,num_res_blocks=1,channels=[16,8],num_res_blocks_middle=1,norm_type='layer')
            asset('structure_decoder',dc,checked_model(source,'models/sparse_structure_vae.py','SparseStructureDecoder',dc))
            fc=dict(args=dict(resolution=4,in_channels=8,model_channels=32,cond_channels=48,out_channels=8,num_blocks=2,num_heads=4,patch_size=2,num_io_res_blocks=1,io_block_channels=[16],qk_rms_norm=True,qk_rms_norm_cross=False,is_shortcut_model=False),captureLayer=1,strength=0,interval=None)
            asset('slat_flow',fc,checked_model(source,'models/structured_latent_flow.py','SLatFlowModel',fc['args']))
            mc=dict(resolution=4,model_channels=256,latent_channels=8,num_blocks=2,num_heads=4,mlp_ratio=2,attn_mode='swin',window_size=2,qk_rms_norm=True,representation_config=dict(use_color=True))
            asset('mesh_decoder',mc,mesh_decoder(source,mc))
            if multi:
                config=dict(backbone=dict(name='vits',out_layers=[0,1,2,3],alt_start=2,qknorm_start=1,rope_start=1,cat_token=True),head=dict(dim_in=96,output_dim=2,features=16,out_channels=[16,24,32,48],pos_embed=True),camera=dict(dim_in=96))
                _,model=depth_components.da3(config);asset('depth_anyview',config,model);del model
                metric=copy.deepcopy(config);metric.update(headType='dpt',headClass='DPT',camera=None);metric['head']['output_dim']=1
                _,model=depth_components.da3(metric);asset('depth_metric',metric,model);del model
            else:
                config=dict(encoder='dinov2_vits14',intermediate_layers=4,dim_proj=32,dim_upsample=[32,32,32],last_conv_channels=16)
                _,model=depth_components.moge(config);asset('depth_moge',config,model);del model
            schedule=dict(rescale=1.,timeScale=1000.,reversed=False,shortcut=False,noShortcut=False,solver='euler');fusion=dict(enabled=multi,warmupSteps=1,pooling=2,patchBegin=1,patchEnd=5,alpha=8.,temperature=1.,minimum=.001)
            runtime=dict(structureSchedule=schedule,slatSchedule=schedule,structureFusion=fusion,slatFusion=fusion,poseConvention='default',prune=0,slatNormalization=dict(mean=[0]*8,std=[1]*8),depth=dict(imageSize=56,referenceView='first',maskThreshold=.5))
            profile=directory/'profile.json';profile.write_text(json.dumps(dict(schema='lma.sam-local-inputs/1',target=target,models=models,runtime=runtime)),'utf-8')
            prepare(profile,exported)
            bundle=json.loads((exported/'lma-bundle.json').read_text('utf-8'));cfg=json.loads((exported/'sam-config.json').read_text('utf-8'))
            check('all_required_graphs_exported',set(graphs(multi))<=set(c['role'] for c in bundle['components']))
            check('strict_condition_tokens',cfg['structureCondition']['tokens']==28 and cfg['slatCondition']['tokens']==36)
            check('geometry_sizes_derive_from_actual_models',cfg['structureResolution']==2 and cfg['occupancyResolution']==4 and cfg['meshResolution']==16 and cfg['meshChannels']==101)
            for name in graphs(multi):
                graph=onnx.load(str(exported/(name+'.onnx')),load_external_data=False);check(name+'_opset',any(o.domain=='' and o.version==17 for o in graph.opset_import))
            receipt=json.loads((exported/'conversion-receipt.json').read_text('utf-8'));check('no_network_or_phone_claim',not receipt['networkUsed'] and receipt['completeModelsRun']==receipt['phoneTests']==0 and not receipt['weightsBundledWithApk'])
            try:prepare(profile,exported)
            except AssertionError:check('refuses_overwrite',True)
            else:raise AssertionError('Existing export was replaced')
        current(inputs);(out/'results.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,phoneTests=0,trainedWeights=False,sourceDefinitions=['D08','D09','MOGE','DA3','TIMM']),indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))
    finally:
        sam_conditioner.conditioner=original_c;depth_components.moge=original_m;depth_components.da3=original_d


if __name__=='__main__':main()
