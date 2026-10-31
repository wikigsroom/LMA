"""SAM source preprocessing, multi-view state machine and production worker IO.

Neural worker graphs in this suite are declared synthetic interface fixtures.
Actual learned definitions have separate source / native parity suites. No
complete trained model, phone, browser or emulator is used.
"""
import ast
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import types
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    import numpy as np
    import torch
    import torch.nn.functional as F
    import onnx
    from onnx import helper as h,TensorProto as T,numpy_helper as nh
    from PIL import Image
    from spatial_portable import Source
    from sam_catalogue import roles
    from export_sam import manifest
    torch.set_num_threads(2);torch.manual_seed(51019)
    inputs=fingerprint('native/spatial','tests/expansion-native/cascade.cpp','tools/test_sam.py','tools/export_sam.py','tools/sam_catalogue.py','third_party/portable-sparse-source-lock.json')
    out=ROOT/'build/sam-tests';out.mkdir(exist_ok=True);checks=[]
    def check(case,value,**extra):assert value,(case,extra);checks.append(dict(case=case,**extra))
    def compare(case,a,b,atol=3e-6):
        a=np.asarray(a);b=b.detach().numpy() if hasattr(b,'detach') else np.asarray(b)
        check(case,a.shape==b.shape and np.allclose(a,b,rtol=4e-5,atol=atol),error=float(np.max(np.abs(a-b))) if a.shape==b.shape else None)
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def path(p):return alias+'/'+p.relative_to(ROOT).as_posix()
    def contract(value,success=True):
        file=out/'request.json';file.write_text(json.dumps(value),'utf-8');r=subprocess.run([path(ROOT/'build/spatial-worker-host/bin/lma_cascade_contract.exe'),path(file)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        check(value['operation']+'_accepted' if success else value['operation']+'_rejected',(r.returncode==0)==success,error=r.stderr[-700:]);return json.loads(r.stdout) if success else None
    def vi(name,shape,dtype=T.FLOAT):return h.make_tensor_value_info(name,dtype,shape)
    def graph(directory,name,fields,outputs,constants,nodes):
        initial=[nh.from_array(np.asarray(v),key) for key,v in constants.items()]
        model=h.make_model(h.make_graph(nodes,name,fields,outputs,initial),opset_imports=[h.make_opsetid('',17)]);model.ir_version=9;onnx.checker.check_model(model);onnx.save(model,str(directory/(name+'.onnx')))
    source=Source('D08');_,raw=source.read('sam3d_objects/data/dataset/tdfy/img_and_mask_transforms.py');tree=ast.parse(raw)
    def crop(image,top,left,height,width):
        pad=(max(-left,0),max(left+width-image.shape[-1],0),max(-top,0),max(top+height-image.shape[-2],0))
        padded=F.pad(image,pad);return padded[...,top+pad[2]:top+pad[2]+height,left+pad[0]:left+pad[0]+width]
    namespace=dict(torch=torch,np=np,BoundingBoxError=ValueError,torchvision=types.SimpleNamespace(transforms=types.SimpleNamespace(functional=types.SimpleNamespace(crop=crop))))
    selected={'crop_around_mask_with_padding','compute_mask_bbox','concat_rgba','split_rgba','check_bounding_box','rembg'}
    body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in selected]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)]+body,type_ignores=[])),'locked-sam-crop','exec'),namespace)
    try:
        # Exact float tensor AA resize, independent of the image codec path.
        for iw,ih,ow,oh in ((17,23,7,11),(7,9,28,28),(28,28,28,28),(32,32,13,13)):
            pixels=torch.rand(ih,iw,3);actual=contract(dict(operation='sam_resize',pixels=pixels.flatten().tolist(),iw=iw,ih=ih,ow=ow,oh=oh,channels=3))
            expected=F.interpolate(pixels.permute(2,0,1)[None],(oh,ow),mode='bicubic',align_corners=False,antialias=True)[0].permute(1,2,0)
            compare('float_bicubic_aa',np.asarray(actual).reshape(oh,ow,3),expected,atol=2e-6)
        for method in ('ssi','object_scene','object_quantile','object_norm_median'):
            height,width,size=13,17,28;rgb=torch.rand(3,height,width);mask=torch.zeros(height,width);mask[2:11,3:14]=1
            yy,xx=torch.meshgrid(torch.arange(height),torch.arange(width),indexing='ij');points=torch.stack((xx*.1,yy*.13,torch.sin(xx*.1)+yy*.07+3));valid=torch.ones(height,width);valid[:2,:2]=0
            nan=points.clone();nan[:,valid<.5]=float('nan')
            if method=='ssi':shift=torch.tensor([0,0,nan[2].nanmedian()]);scale=(nan-shift[:,None,None]).abs().nanmean()
            else:
                object_points=nan[:,mask>.5];shift=object_points.nanmedian(-1).values;centered=nan-shift[:,None,None]
                if method=='object_scene':scale=centered.abs().max(0).values.nanmedian()
                else:
                    norms=(object_points-shift[:,None]).norm(dim=0);scale=norms.nanmedian() if method=='object_norm_median' else (norms.nanquantile(.9)-norms.nanquantile(.1))*2
            normalized=(nan-shift[:,None,None])/scale
            cropped,cm,cp=namespace['crop_around_mask_with_padding'](rgb,mask,1.,.1,normalized)
            cropped,cm,cp=namespace['rembg'](cropped,cm,cp)
            preprocessing=dict(boxFactor=1.,padding=.1,normalizer=dict(method=method))
            actual=contract(dict(operation='sam_inputs',width=width,height=height,size=size,rgb=rgb.permute(1,2,0).flatten().tolist(),mask=mask.flatten().tolist(),points=points.permute(1,2,0).flatten().tolist(),valid=valid.flatten().tolist(),preprocessing=preprocessing))
            compare('normalizer_shift',actual['shift'],shift);compare('normalizer_scale',actual['scale'],scale)
            compare('source_crop_rgb',np.asarray(actual['inputs']['image']).reshape(3,size,size),F.interpolate(cropped[None],(size,size),mode='bicubic',align_corners=False,antialias=True)[0])
            compare('source_crop_mask',np.asarray(actual['inputs']['mask']).reshape(size,size),F.interpolate(cm[None,None],(size,size),mode='nearest')[0,0])
            expected=F.interpolate(cp[None],(size,size),mode='nearest')[0];expected_valid=expected.isfinite().all(0)
            compare('source_crop_point_valid',np.asarray(actual['inputs']['pointmap_valid']).reshape(size,size),expected_valid)
            compare('source_crop_points',np.asarray(actual['inputs']['pointmap']).reshape(3,size,size),expected.nan_to_num())
        # Shared state, source pose view 0, SS noise replay versus SLAT fresh draw.
        for structure in (True,False):
            heads=[dict(name='shape',rows=5,channels=2,strength=0,pointStrength=0,interval=None)]
            if structure:heads.append(dict(name='pose',rows=1,channels=3,strength=0,pointStrength=0,interval=None))
            fusion=dict(enabled=True,warmupSteps=1,pooling=1,patchBegin=1,patchEnd=5,alpha=8.,temperature=1.,minimum=.001)
            schedule=dict(rescale=1.,timeScale=1000.,reversed=False,shortcut=True,noShortcut=False,solver='euler')
            coords=[[0,x,0,0] for x in range(5)]
            actual=contract(dict(operation='sam_sampling',structure=structure,heads=heads,seed=42,fusion=fusion,schedule=schedule,steps=3,views=3,queries=5,coords=coords,coarse=coords))
            calls=actual['calls'];initial=np.asarray(calls[3]['state']);first=np.asarray(actual['firstNoise'])
            check('structure_replays_noise' if structure else 'slat_uses_fresh_noise',np.allclose(initial,first) if structure else not np.allclose(initial,first))
            for start in range(0,len(calls),3):
                compare('every_view_uses_same_latent_state',calls[start]['state'],calls[start+1]['state']);compare('every_view_uses_same_latent_state',calls[start]['state'],calls[start+2]['state'])
            weights=np.asarray(actual['weights']);compare('per_row_weights_sum',weights.sum(0),np.ones(5))
            state=initial.copy()
            for _ in range(3):
                velocity=state*.1
                velocity[:10]+=np.repeat((weights*np.arange(1,4)[:,None]).sum(0),2)
                if structure:velocity[10:]+=1
                state+=velocity/3
            compare('weighted_velocity_and_first_view_pose',actual['value'],state,atol=8e-6)
        # The synthetic worker bundle is intentionally small. All NN stage IO
        # is exercised; learned math has separate actual-source parity tests.
        for multi in (False,True):
            directory=out/('mv_bundle' if multi else 'single_bundle');directory.mkdir(exist_ok=True);nv=4 if multi else 1;size=28;tokens=8;width=8;shape_rows=8;total=67
            image_fields=[vi(k,[1,1 if k in ('mask','rgb_image_mask') else 3,size,size]) for k in ('image','mask','rgb_image','rgb_image_mask')]
            for name in ('ss_conditioner','slat_conditioner'):
                constants={'condition_shape':np.array([1,tokens,width],np.int64),'zero':np.array(0.,np.float32)}
                nodes=[h.make_node('ReduceMean',['image'],['average'],keepdims=0),h.make_node('Expand',['average','condition_shape'],['condition']),h.make_node('Expand',['zero','condition_shape'],['unconditional']),h.make_node('Identity',['condition'],['without_pointmap'])]
                graph(directory,name,image_fields,[vi(k,[1,tokens,width]) for k in ('condition','unconditional','without_pointmap')],constants,nodes)
            coords=np.array([[0,x,y,z] for x in range(4) for y in range(4) for z in range(4)],np.int64)
            for sparse,name in ((False,'structure_flow'),(True,'slat_flow')):
                fields=[vi('features',['rows',8] if sparse else [1,total])]+([vi('coords',['rows',4],T.INT64)] if sparse else [])+[vi('time',[1]),vi('condition',[1,tokens,width])]
                outputs=[vi('velocity',['rows',8] if sparse else [1,total])];constants={'factor':np.array(.05,np.float32)};nodes=[h.make_node('Mul',['features','factor'],['velocity'])]
                if multi:
                    constants.update(q=np.full((64 if sparse else shape_rows,2,2),.2,np.float32),k=np.arange(tokens*4,dtype=np.float32).reshape(tokens,2,2)*.05)
                    nodes+=[h.make_node('Identity',['q'],['attention_q']),h.make_node('Identity',['k'],['attention_k'])];outputs+=[vi('attention_q',[64 if sparse else shape_rows,2,2]),vi('attention_k',[tokens,2,2])]
                    if sparse:nodes.append(h.make_node('Identity',['coords'],['attention_coords']));outputs.append(vi('attention_coords',['rows',4],T.INT64))
                graph(directory,name,fields,outputs,constants,nodes)
            graph(directory,'structure_decoder',[vi('features',[1,8,8])],[vi('occupancy',[1,1,4,4,4])],{'logits':np.ones((1,1,4,4,4),np.float32)},[h.make_node('Identity',['logits'],['occupancy'])])
            decoded=np.array([[0,x,y,z] for x in range(16) for y in range(16) for z in range(16)],np.int64);fields=np.zeros((len(decoded),101),np.float32)
            for i in range(8):
                xyz=(decoded[:,1:]+np.array([(i>>a)&1 for a in range(3)]))/16-.5
                fields[:,i]=np.sqrt((xyz*xyz).sum(-1))-.28+1/16
            fields[:,53:]=np.tile(np.array([.4,-.2,.8,0.,.1,.2],np.float32),8)
            graph(directory,'mesh_decoder',[vi('features',['rows',8]),vi('coords',['rows',4],T.INT64)],[vi('fields',[4096,101]),vi('decoded_coords',[4096,4],T.INT64)],{'result':fields,'result_coords':decoded},[h.make_node('Identity',['result'],['fields']),h.make_node('Identity',['result_coords'],['decoded_coords'])])
            if multi:
                camera=np.zeros((1,nv,9),np.float32);camera[:,:,6]=1;camera[:,:,7:]=1
                graph(directory,'depth_anyview',[vi('images',[1,nv,3,size,size])],[vi('depth',[1,nv,size,size]),vi('confidence',[1,nv,size,size]),vi('sky',[1,nv,size,size]),vi('camera',[1,nv,9])],{'d':np.full((1,nv,size,size),2,np.float32),'c':np.ones((1,nv,size,size),np.float32),'s':np.zeros((1,nv,size,size),np.float32),'p':camera},[h.make_node('Identity',[k],[v]) for k,v in zip(('d','c','s','p'),('depth','confidence','sky','camera'))])
                graph(directory,'depth_metric',[vi('images',[1,nv,3,size,size])],[vi('depth',[1,nv,size,size]),vi('sky',[1,nv,size,size])],{'d':np.full((1,nv,size,size),10,np.float32),'s':np.zeros((1,nv,size,size),np.float32)},[h.make_node('Identity',['d'],['depth']),h.make_node('Identity',['s'],['sky'])])
            else:
                yy,xx=np.mgrid[:size,:size];z=2+.2*np.sin(xx/4)+.1*np.cos(yy/3);uv=np.stack((xx/size*2-((size-1)/size),yy/size*2-((size-1)/size)),-1)/np.sqrt(2);points=np.concatenate((uv*z[...,None]/1.4,(z-.3)[...,None]),-1).astype(np.float32)
                graph(directory,'depth_moge',[vi('images',[1,3,size,size])],[vi('points',[1,size,size,3]),vi('mask',[1,size,size])],{'p':points[None],'m':np.ones((1,size,size),np.float32)},[h.make_node('Identity',['p'],['points']),h.make_node('Identity',['m'],['mask'])])
            head=dict(name='shape',rows=8,channels=8,strength=0,pointStrength=0,interval=None);condition=dict(imageSize=size,tokens=tokens,width=width,pointmap=False,keys=['image','mask','rgb_image','rgb_image_mask'],preprocessing=dict(boxFactor=1.,padding=.1));flow=dict(capture=multi,attentionHeads=2,attentionWidth=2,pointmapCfg=False);schedule=dict(rescale=1.,timeScale=1000.,reversed=False,shortcut=False,noShortcut=False,solver='euler');fusion=dict(enabled=multi,warmupSteps=1,pooling=1,patchBegin=1,patchEnd=5,alpha=8.,temperature=1.,minimum=.001)
            cfg=dict(schema='lma.sam-export/1',pipeline='mv_sam3d_da3' if multi else 'sam3d_objects',source=dict(repository='devinli123/MV-SAM3D' if multi else 'facebookresearch/sam-3d-objects',revision='abb04b5e8af5bc33b0265bdf19937e76bbb6bcdd' if multi else 'f91db411c50efee93d8db7aeb323885650f6f722'),auxiliarySources={k:dict(repository=v[0],revision=v[1]) for k,v in dict(MOGE=('microsoft/MoGe','74fbce054ebed49800de42d0ad0e83495065719a'),TIMM=('huggingface/pytorch-image-models','78c3724f4545c0067d0b4d2f7df6337196be01ce'),**(dict(DA3=('ByteDance-Seed/Depth-Anything-3','3d835ec1a5802d64a8b8b15f817a1ab54809bfe4')) if multi else {})).items()},dtype='float32',opset=17,views=nv,inputPolicy='explicit_rgba_fixed_square',surfacePolicy='source_flexicubes_vertex_attributes',structureResolution=2,occupancyResolution=4,meshResolution=16,meshChannels=101,meshColor=True,prune=0,poseConvention='default',heads=[head,dict(head,name='scale',rows=1,channels=3)],slatHeads=[dict(head,rows=1)],structureCondition=condition,slatCondition=condition,structureFlow=flow,slatFlow=flow,structureSchedule=schedule,slatSchedule=schedule,structureFusion=fusion,slatFusion=fusion,slatNormalization=dict(mean=[0]*8,std=[1]*8),depth=dict(imageSize=size,referenceView='first',maskThreshold=.5))
            config=directory/'sam-config.json';config.write_text(json.dumps(cfg),'utf-8');manifest(directory,cfg,[config])
            views=out/'views';views.mkdir(exist_ok=True)
            for i,name in enumerate(('00_front.png','01_right.png','02_back.png','03_left.png')):
                pixels=np.zeros((40,32,4),np.uint8);pixels[:,:,:3]=[30+i*20,90,180];pixels[5:35,4:28,3]=255;Image.fromarray(pixels).save(views/name)
            command=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline=cfg['pipeline'],workspace=path(directory),output=path(out/('multi.glb' if multi else 'single.glb')),parameters=dict(threads=2,seed=42,structureSteps=2,slatSteps=2,maxRows=4096,maxTriangles=300000),components={role:path(directory/name) for role,name in roles(multi).items()})
            command['viewsDirectory' if multi else 'referenceImage']=path(views if multi else views/'00_front.png')
            target=out/('multi.glb' if multi else 'single.glb');target.unlink(missing_ok=True);request=out/'production-request.json';request.write_text(json.dumps(command),'utf-8')
            r=subprocess.run([path(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),path(request)],capture_output=True,text=True,encoding='utf-8',timeout=90)
            check('production_sam_workflow',r.returncode==0 and target.is_file(),pipeline=cfg['pipeline'],events=r.stdout[-1500:],stderr=r.stderr[-600:])
            data=target.read_bytes();length=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+length]);attrs=doc['meshes'][0]['primitives'][0]['attributes'];check('learned_attribute_channels_preserved',{'POSITION','NORMAL','COLOR_0','_SAM_AUX'}<=set(attrs));check('no_gaussian_bake_claim',doc['extras']['trainedGaussianBake'] is False)
            target.unlink();bad=copy.deepcopy(command);bad['components'].pop('mesh_decoder');request.write_text(json.dumps(bad),'utf-8');r=subprocess.run([path(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),path(request)],capture_output=True,text=True,encoding='utf-8',timeout=20);check('missing_stage_rejected_without_output',r.returncode!=0 and not target.exists())
            request.write_text(json.dumps(command),'utf-8');subprocess.run([path(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),path(request)],capture_output=True,check=True,timeout=90)
        current(inputs)
        (out/'results.json').write_text(json.dumps(dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsRun=0,phoneTests=0,neuralWorkflowFixtures='synthetic_stage_io_only',upstreamPreprocessing='literal_locked_source'),indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
