"""Pinned random tiny graph parity and actual native program paths; no checkpoints."""
import copy,hashlib,json,os,struct,subprocess,sys
from pathlib import Path
from evidence import current,fingerprint
from fetch_shape_sources import ROOT,verify
OUT=ROOT/'build/shape-tests'
ALIAS=None
def native_path(p):return ALIAS+'/'+p.resolve().relative_to(ROOT.resolve()).as_posix()

def setup():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    verify();OUT.mkdir(exist_ok=True)

def parity():
    import numpy as np,torch,onnxruntime as ort
    from transformers import Dinov2Config,Dinov2Model
    from PIL import Image
    from export_shape import reference
    from shape_graphs import Cache,Query,Flow,export_all,portable_attention
    torch.set_num_threads(2);torch.manual_seed(8462);checks=[]
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    for pipeline in ['triposg','partcrafter']:
        _,FlowModel,VaeModel=reference(pipeline);parts=pipeline!='triposg'
        model=FlowModel(num_attention_heads=2,width=16,in_channels=4,num_layers=3,cross_attention_dim=8,
            **(dict(max_num_parts=16,global_attn_block_ids=[0,2]) if parts else {})).eval()
        vae=VaeModel(latent_channels=4,num_attention_heads=2,width_encoder=16,width_decoder=16,num_layers_encoder=1,num_layers_decoder=2,embed_frequency=2).eval()
        # The real DINO checkpoint's training size differs from the crop. Test
        # the actual positional-interpolation export path with bounded sizes.
        image=Dinov2Model(Dinov2Config(image_size=56,patch_size=14,hidden_size=8,num_hidden_layers=2,num_attention_heads=2,intermediate_size=32,layerscale_value=1.)).eval()
        image.set_attn_implementation('eager')
        original=copy.deepcopy(model);original_vae=copy.deepcopy(vae);directory=OUT/pipeline
        export_all(image,model,vae,directory,4,16,5,8,28,parts)
        sessions={name:ort.InferenceSession(str(directory/(name+'.onnx')),sess_options=options,providers=['CPUExecutionProvider']) for name in ['image_encoder','flow','cache','query']}
        def compare(label,expected,actual):
            expected=expected.detach().numpy();error=float(np.max(np.abs(expected-actual)));assert np.allclose(expected,actual,rtol=1e-4,atol=2e-5),(label,error)
            checks.append(dict(case=pipeline+'_'+label,maxAbsoluteError=error))
        with torch.inference_mode():
            pixels=torch.randn(1,3,28,28);compare('image_encoder',image(pixels).last_hidden_state,sessions['image_encoder'].run(None,{'pixel_values':pixels.numpy()})[0])
            for count in ([1,2,3,16] if parts else [1]):
                for tokens in [5,9,17]:
                    x=torch.randn(count,tokens,4);t=torch.full((count,),450.);e=torch.randn(1,5,8).repeat(count,1,1)
                    args=dict(attention_kwargs={'num_parts':count}) if parts else {}
                    expected=original(x,t,encoder_hidden_states=e,return_dict=False,**args)[0]
                    compare('flow_p'+str(count)+'_t'+str(tokens),expected,sessions['flow'].run(None,dict(latents=x.numpy(),timestep=t.numpy(),image_embeddings=e.numpy()))[0])
                    # Conditional/unconditional use the same part embedding IDs.
                    e.zero_();expected=original(x,t,encoder_hidden_states=e,return_dict=False,**args)[0]
                    compare('uncond_p'+str(count)+'_t'+str(tokens),expected,sessions['flow'].run(None,dict(latents=x.numpy(),timestep=t.numpy(),image_embeddings=e.numpy()))[0])
            for tokens in [5,13]:
                z=torch.randn(1,tokens,4);cache=sessions['cache'].run(None,{'latents':z.numpy()})[0]
                for count in [1,7,137]:
                    points=torch.randn(1,count,3);expected=original_vae.decode(z,sampled_points=points,num_chunks=3).sample
                    compare('sdf_t'+str(tokens)+'_q'+str(count),expected,sessions['query'].run(None,dict(cache=cache,points=points.numpy()))[0])
        # Scheduler source oracle, not a rewritten copy of the native formula.
        import importlib
        scheduler=importlib.import_module(('src' if parts else 'triposg')+'.schedulers.scheduling_rectified_flow').RectifiedFlowScheduler
        for shift in [1.,2.5,7.]:
            s=scheduler(shift=shift);s.set_timesteps(7);state=torch.tensor([.2,-.1,1.]);native=state.numpy().copy()
            for i,time in enumerate(s.timesteps):
                velocity=torch.tensor([.1,-.7,.4]);state=s.step(velocity,time,state,return_dict=False)[0]
                before=1-i/7;after=1-(i+1)/7;dt=shift*before/(1+(shift-1)*before)-shift*after/(1+(shift-1)*after);native+=np.float32(dt)*velocity.numpy()
            compare('scheduler_shift_'+str(shift),state,native)
            data=np.arange(43*37*3,dtype=np.uint8).reshape(37,43,3);photo=Image.fromarray(data);image_file=OUT/'preprocess.png';photo.save(image_file)
            request=OUT/'arithmetic.json';request.write_text(json.dumps(dict(state=[.2,-.1,1.],velocity=[.1,-.7,.4],steps=7,shift=shift,image=native_path(image_file))),encoding='utf-8')
            got=json.loads(subprocess.check_output([native_path(ROOT/'build/shape-worker-host/bin/lma_shape_contract.exe'),native_path(request)]))
            compare('native_scheduler_shift_'+str(shift),state,np.array(got['state']))
            compare('native_timesteps_shift_'+str(shift),s.timesteps,np.array(got['timesteps']))
            from transformers import BitImageProcessor
            processor=BitImageProcessor(size={'shortest_edge':32},crop_size={'height':28,'width':28},resample=3,image_mean=[.485,.456,.406],image_std=[.229,.224,.225])
            expected=processor(photo,return_tensors='np').pixel_values.flatten();err=float(np.max(np.abs(expected-np.array(got['pixels']))))
            assert err<=1/255/.224+1e-5,err
            checks.append(dict(case=pipeline+'_native_resize_'+str(shift),maxAbsoluteError=err,limit='one_8bit_level_after_normalization'))
        # Exercise the documented CLI with tiny random safetensors, including
        # from_pretrained, offline guards and real generated manifest hashes.
        snapshot=OUT/(pipeline+'-snapshot');snapshot.mkdir(exist_ok=True)
        original.save_pretrained(snapshot/'transformer',safe_serialization=True)
        original_vae.save_pretrained(snapshot/'vae',safe_serialization=True)
        image.save_pretrained(snapshot/'image_encoder_dinov2',safe_serialization=True)
        processor.save_pretrained(snapshot/'feature_extractor_dinov2')
        scheduler(shift=1.).save_pretrained(snapshot/'scheduler')
        import shutil
        exported=OUT/(pipeline+'-cli-export')
        if exported.exists():assert exported.resolve().parent==OUT.resolve();shutil.rmtree(exported)
        result=subprocess.run([sys.executable,str(ROOT/'tools/export_shape.py'),'--pipeline',pipeline,'--snapshot',str(snapshot),'--output',str(exported)],
            capture_output=True,text=True,encoding='utf-8',timeout=100,env={**os.environ,'PYTHONPATH':str(ROOT/'build/shape-reference-python')})
        assert result.returncode==0,(pipeline,result.stdout,result.stderr)
        manifest=json.loads((exported/'lma-bundle.json').read_text(encoding='utf-8'))
        assert manifest['pipeline']==pipeline and manifest['recipeId']==pipeline+'_onnx_cpu_v1' and manifest['evidence']['acquisition']=='import_only'
        for component in manifest['components']:
            file=exported/component['path'];assert component['url']=='' and file.stat().st_size==component['bytes']
            with file.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==component['sha256']
        assert {c['role'] for c in manifest['components']}=={'config','image_encoder','flow','cache','query','image_encoder_data','flow_data','cache_data','query_data'}
        checks.append(dict(case=pipeline+'_documented_cli_random_safetensors',components=len(manifest['components']),network=False,trainedWeights=False))
    return checks

def fixture(directory,pipeline='triposg',bad_sdf=False):
    import onnx
    from onnx import helper as H,TensorProto as T
    directory.mkdir(parents=True,exist_ok=True)
    f=lambda n,s:H.make_tensor_value_info(n,T.FLOAT,s)
    def save(name,nodes,inputs,output,constants):
        g=H.make_graph(nodes,name,inputs,[output],constants);m=H.make_model(g,opset_imports=[H.make_opsetid('',17)],ir_version=10);onnx.save(m,str(directory/(name+'.onnx')))
    const=lambda n,d,s:H.make_tensor(n,T.FLOAT,s,d)
    save('image_encoder',[H.make_node('ReduceMean',['pixel_values'],['mean'],keepdims=0),H.make_node('Add',['mean','base'],['image_embeddings'])],
        [f('pixel_values',[1,3,28,28])],f('image_embeddings',[1,5,8]),[const('base',[0.]*40,[1,5,8])])
    save('flow',[H.make_node('ReduceMean',['timestep'],['time'],keepdims=0),H.make_node('ReduceMean',['image_embeddings'],['image'],keepdims=0),H.make_node('Add',['time','image'],['sum']),H.make_node('Mul',['sum','zero'],['bias']),H.make_node('Mul',['latents','scale'],['state']),H.make_node('Add',['state','bias'],['velocity'])],
        [f('latents',['parts','tokens',4]),f('timestep',['parts']),f('image_embeddings',['parts',5,8])],f('velocity',['parts','tokens',4]),[const('scale',[.1],[]),const('zero',[0.],[])])
    save('cache',[H.make_node('Concat',['latents']*4,['cache'],axis=2)], [f('latents',[1,'tokens',4])],f('cache',[1,'tokens',16]),[])
    nodes=[H.make_node('Mul',['points','points'],['square']),H.make_node('ReduceSum',['square','axes'],['radius'],keepdims=1),H.make_node('ReduceMean',['cache'],['mean'],keepdims=0),H.make_node('Mul',['mean','zero'],['bias']),H.make_node('Sub',['level','radius'],['sphere']),H.make_node('Add',['sphere','bias'],['sdf'])]
    save('query',nodes,[f('cache',[1,'tokens',16]),f('points',[1,'queries',3])],f('sdf',[1,'queries',1]),[const('level',[-5. if bad_sdf else .5],[]),const('zero',[0.],[]),H.make_tensor('axes',T.INT64,[1],[2])])
    from export_shape import reference
    e,_,_=reference(pipeline)
    config=dict(schema='lma.rf-shape-export/1',pipeline=pipeline,dtype='float32',opset=17,source={k:e[k] for k in ['repository','revision']},latentChannels=4,decoderWidth=16,imageSize=28,resizeShortest=32,encoderTokens=5,encoderWidth=8,maxTokens=4096,maxParts=16 if pipeline!='triposg' else 1,imageMean=[.485,.456,.406],imageStd=[.229,.224,.225],scheduleShift=1,trainingTimesteps=1000)
    (directory/'shape-config.json').write_text(json.dumps(config),encoding='utf-8');return config

def workers():
    from PIL import Image
    records=[];root=OUT/'native';root.mkdir(exist_ok=True);image=root/'image.png';Image.new('RGB',(40,32),(230,220,210)).save(image)
    worker=ROOT/'build/shape-worker-host/bin/lma_rf_shape.exe'
    assert json.loads(subprocess.check_output([str(worker),'--info']))['engine']=='rf_shape_ort'
    for pipeline in ['triposg','partcrafter','partcrafter_scene']:
        directory=root/pipeline;cfg=fixture(directory,pipeline)
        names={'config':'shape-config.json',**{n:n+'.onnx' for n in ['image_encoder','flow','cache','query']}}
        original=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline=pipeline,workspace=native_path(directory),referenceImage=native_path(image),output=native_path(root/'result.glb'),
            components={k:native_path(directory/v) for k,v in names.items()},parameters=dict(steps=2,tokens=512,parts=1 if pipeline=='triposg' else 2,grid=32,queryChunk=512,guidance=7))
        for case in ['success','source_revision','wrong_pipeline','missing_role','external_path','bad_dimensions','misaligned_grid','missing_image','empty_surface','triangle_budget']:
            value=copy.deepcopy(original);selected=copy.deepcopy(cfg);output=Path(value['output']);output.unlink(missing_ok=True)
            if case=='source_revision':selected['source']['revision']='0'*40
            if case=='wrong_pipeline':value['pipeline']='hunyuan3d'
            if case=='missing_role':value['components'].pop('cache')
            if case=='external_path':value['components']['flow']=native_path(image)
            if case=='bad_dimensions':selected['latentChannels']=800000
            if case=='misaligned_grid':value['parameters']['grid']=33
            if case=='missing_image':value['referenceImage']=native_path(root/'absent.png')
            if case=='empty_surface':fixture(directory,pipeline,True)
            if case=='triangle_budget':value['parameters']['maxTriangles']=1000
            if case!='empty_surface':(directory/'shape-config.json').write_text(json.dumps(selected),encoding='utf-8')
            file=root/'request.json';file.write_text(json.dumps(value),encoding='utf-8')
            result=subprocess.run([native_path(worker),native_path(file)],capture_output=True,text=True,encoding='utf-8',timeout=40)
            events=[json.loads(s) for s in result.stdout.splitlines() if s.startswith('{')];done=any(e['event']=='complete' for e in events)
            assert done==(case=='success') and (result.returncode==0)==done,(pipeline,case,result.stdout,result.stderr)
            detail={}
            if done:
                data=output.read_bytes();length=struct.unpack_from('<I',data,12)[0];g=json.loads(data[20:20+length]);assert len(g['meshes'])==value['parameters']['parts'] and len(g['nodes'])==len(g['meshes'])
                assert all('uri' not in b for b in g['buffers']);detail=dict(meshes=len(g['meshes']),bytes=len(data))
            assert any(e['event']=='execution' and 'runtimeMeasurements' in e['details'] for e in events)
            records.append(dict(pipeline=pipeline,case=case,expectedSuccess=done,**detail))
            if case=='empty_surface':fixture(directory,pipeline)
    return records

def main():
    global ALIAS
    setup();inputs=fingerprint('native/rf_shape','tests/expansion-native/shape.cpp','tools/test_shape.py','tools/shape_graphs.py','tools/export_shape.py','tools/shape_catalogue.py','tools/fetch_shape_sources.py','third_party/rf-shape-source-lock.json','native/moss_nano/onnx_external.hpp','native/worker_common.hpp','native/runtime_metrics.hpp')
    ALIAS=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert ALIAS
    subprocess.run(['subst',ALIAS,str(ROOT)],check=True,capture_output=True)
    try:graphs=parity();native=workers();current(inputs)
    finally:subprocess.run(['subst',ALIAS,'/D'],check=True,capture_output=True)
    report=dict(passed=len(graphs)+len(native)*3+1,graphParity=graphs,nativeProcesses=native,trainedModelDownloads=0,trainedModelRuns=0,physicalAndroidTests=0,virtualizationUsed=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=report['passed'],graphChecks=len(graphs),nativeProcesses=len(native),completeModels=0)))

if __name__=='__main__':main()
