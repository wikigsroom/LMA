"""Program-only Paint checks: actual source networks with small random tensors.

Tests UniPC state against pinned Diffusers, exported attention/VAEs/RealESRGAN
against PyTorch, and the actual native worker from PNG+GLB to material GLB.
No trained model, phone, virtual machine or external inference is used.
"""
import copy,hashlib,json,os,shutil,struct,subprocess,sys
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/paint-tests'


def main():
    sys.path[:0]=[str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_DATASETS_OFFLINE='1')
    import torch,numpy as np,onnxruntime as ort
    from PIL import Image
    from diffusers import AutoencoderKL,UniPCMultistepScheduler
    from transformers import Dinov2Config,Dinov2Model
    from paint_graphs import construct,PaintFlow,arguments,static_positions,NAMES,VaeStatistics,VaeDecode
    from paint_reference import rrdb,verify as verify_sr
    from paint_sampler import profiles,prepare
    from shape_graphs import export_graph,ImageEncoder
    from export_paint import manifest
    from test_spatial import write_mesh
    torch.set_num_threads(2);torch.manual_seed(6043);rng=np.random.default_rng(6043)
    OUT.mkdir(exist_ok=True);verify_sr()
    inputs=fingerprint('native/spatial','native/rf_shape','tests/expansion-native/material.cpp','tools/test_paint.py','tools/paint_graphs.py','tools/paint_reference.py','tools/paint_sampler.py','tools/paint_catalogue.py','tools/export_paint.py','tools/export_spatial.py','tools/spatial_reference.py','third_party/paint-source-lock.json','third_party/spatial-shape-source-lock.json')
    checks=[]
    def check(name,value,**detail):
        assert value,(name,detail)
        checks.append(dict(case=name,**detail))
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    def exported(module,args,name,names,output):
        with torch.inference_mode():expected=module(*args).numpy()
        export_graph(module,args,OUT/(name+'.onnx'),names,output,{})
        session=ort.InferenceSession(str(OUT/(name+'.onnx')),options,providers=['CPUExecutionProvider'])
        got=session.run(None,{k:a.numpy() for k,a in zip(names,args)})[0]
        error=float(np.max(np.abs(got-expected)));check(name+'_torch_onnx',np.allclose(got,expected,atol=3e-5,rtol=3e-4),maximumError=error)
        return got
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(path):return alias+'/'+path.resolve().relative_to(ROOT).as_posix()
    def contract(p,success=True):
        f=OUT/'contract.json';f.write_text(json.dumps(p),'utf-8')
        r=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_material_contract.exe'),native(f)],capture_output=True,text=True,encoding='utf-8',timeout=45)
        assert (r.returncode==0)==success,r.stderr
        return json.loads(r.stdout) if success else None
    try:
        cfg=dict(num_train_timesteps=1000,beta_start=.00085,beta_end=.012,beta_schedule='scaled_linear',solver_order=2,prediction_type='epsilon',thresholding=False,predict_x0=True,solver_type='bh2',lower_order_final=True,timestep_spacing='trailing')
        sampler=profiles(cfg);sp=OUT/'sampler.json';sp.write_text(json.dumps(sampler,separators=(',',':'))+'\n','utf-8')
        for steps in range(1,101):
            sample=torch.tensor(rng.normal(size=(1,7)).astype(np.float32));noise=rng.normal(size=(steps,7)).astype(np.float32)
            scheduler,corrected=prepare(cfg,steps)
            check('unipc_requested_steps_'+str(steps),len(scheduler.timesteps)==steps and bool((scheduler.timesteps>=0).all()))
            state=sample.clone();expected=[]
            for t,n in zip(scheduler.timesteps,noise):state=scheduler.step(torch.tensor(n)[None],t,state,return_dict=False)[0];expected.append(state.flatten().numpy().copy())
            got=contract(dict(type='sampler',sampler=native(sp),sample=sample.flatten().tolist(),noise=noise.tolist()))
            error=float(np.max(np.abs(np.array(got['states'])-np.array(expected))))
            check('native_unipc_'+str(steps),np.allclose(got['states'],expected,atol=.00015,rtol=.00005) and np.allclose(got['times'],scheduler.timesteps.numpy()),maximumError=error)
        # Same primitive architecture as the publisher, reduced depth/width and
        # fixed random parameters. Includes material-specific/ref/3D-RoPE paths.
        model,module=construct(dict(sample_size=8,in_channels=4,out_channels=4,layers_per_block=1,block_out_channels=[64,64],down_block_types=['CrossAttnDownBlock2D','DownBlock2D'],up_block_types=['UpBlock2D','CrossAttnUpBlock2D'],cross_attention_dim=1024,attention_head_dim=1,norm_num_groups=32))
        args=arguments();flow=PaintFlow(model)
        with torch.inference_mode():original=flow(*args).numpy()
        static_positions(module,6,8)
        got=exported(flow,args,'flow',NAMES,'noise')
        check('position_port_matches_source',np.allclose(got,original,atol=3e-5,rtol=3e-4),maximumError=float(np.abs(got-original).max()))
        # A changed geometry map must change its discrete position/RoPE values.
        p=args[6].clone();p[:,:,0,:16]=1
        q=module.calc_multires_voxel_idxs(p.repeat(3,1,1,1,1))
        check('position_mask_and_resolutions',sorted(q)==[6,24,96,384] and all(v['voxel_indices'].shape[-1]==3 for v in q.values()))
        image=Dinov2Model(Dinov2Config(hidden_size=1536,num_hidden_layers=1,num_attention_heads=24,mlp_ratio=1/24,image_size=28,patch_size=14)).eval()
        exported(ImageEncoder(image),(torch.randn(1,3,28,28),),'image_encoder',['pixel_values'],'image_embeddings')
        del image
        vae=AutoencoderKL(in_channels=3,out_channels=3,down_block_types=['DownEncoderBlock2D']*4,up_block_types=['UpDecoderBlock2D']*4,block_out_channels=[32]*4,layers_per_block=1,latent_channels=4,norm_num_groups=32,sample_size=64).eval()
        exported(VaeStatistics(vae),(torch.randn(1,3,64,64),),'vae_encoder',['image'],'statistics')
        exported(VaeDecode(vae),(torch.randn(1,4,8,8),),'vae_decoder',['latents'],'image')
        del vae
        exported(rrdb()(3,3,num_feat=8,num_block=1,num_grow_ch=4).eval(),(torch.rand(1,3,64,64),),'upscale',['image'],'upscaled')
        cfg=dict(schema='lma.material-export/1',pipeline='hunyuan3d_21_paint',dtype='float32',opset=17,source=dict(repository='Tencent-Hunyuan/Hunyuan3D-2.1',revision='82920d643c0dc2f7bfd7255f45f62d386edfe60c'),views=6,imageSize=64,dinoSize=28,dinoResize=32,dinoWidth=1536,dinoTokens=5,vaeScaling=.18215,upscaleFactor=4,scheduler='UniPCMultistepScheduler',timestepSpacing='trailing')
        manifest(OUT,cfg,'random-program-fixture-not-trained')
        bundle=json.loads((OUT/'lma-bundle.json').read_text('utf-8'));components={}
        for c in bundle['components']:
            f=OUT/c['path'];check('manifest_'+c['role'],f.stat().st_size==c['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==c['sha256'] and not c['url']);components[c['role']]=native(f)
        picture=OUT/'reference.png';Image.new('RGBA',(73,59),(187,143,97,255)).save(picture)
        mesh=OUT/'input.glb';write_mesh(mesh,vertices=[[-1,-1,-1],[1,-1,-1],[0,1,-1],[0,0,1]],faces=[[0,2,1],[0,1,3],[1,2,3],[2,0,3]])
        command=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline='hunyuan3d_21_paint',workspace=native(OUT),components=components,referenceImage=native(picture),sourceMesh=native(mesh),parameters=dict(threads=2,steps=2,seed=7,guidance=3,atlas=256,upscale=False))
        def worker(value,success):
            path=OUT/'request.json';path.write_text(json.dumps(value),'utf-8')
            r=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),native(path)],capture_output=True,text=True,encoding='utf-8',timeout=120)
            records=[json.loads(x) for x in r.stdout.splitlines() if x.startswith('{')]
            (OUT/'worker.log').write_text(r.stdout+r.stderr,'utf-8')
            assert (r.returncode==0)==success,(r.returncode,r.stdout[-200:],r.stderr[-1000:],records[-2:])
            return records
        for enhanced in (False,True):
            output=OUT/('enhanced.glb' if enhanced else 'plain.glb');output.unlink(missing_ok=True)
            request=copy.deepcopy(command);request['output']=native(output);request['parameters']['upscale']=enhanced
            events=worker(request,True)
            data=output.read_bytes();length=struct.unpack_from('<I',data,12)[0];root=json.loads(data[20:20+length])
            check('worker_pbr_'+str(enhanced),len(root['images'])==2 and 'TEXCOORD_0' in root['meshes'][0]['primitives'][0]['attributes'] and events[-1]['event']=='complete')
            stages=[x['stage'] for x in events if x['event']=='stage'];check('worker_stages_'+str(enhanced),all(s in stages for s in ['rendering_conditions','encoding_image','sampling_material','decoding_material','baking_material']) and ('enhancing_material' in stages)==enhanced)
        (OUT/'invalid.glb').unlink(missing_ok=True)
        for name,change in [('missing_component',lambda p:p['components'].pop('sampler')),('missing_mesh',lambda p:p.pop('sourceMesh')),('invalid_steps_type',lambda p:p['parameters'].update(steps='many')),('invalid_field',lambda p:p['parameters'].update(remote=True))]:
            request=copy.deepcopy(command);request['output']=native(OUT/'invalid.glb');change(request);worker(request,False);check(name,not (OUT/'invalid.glb').exists())
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModelsDownloaded=0,completeModelsRun=0,randomNeuralGraphs=True,physicalDeviceTests=0,virtualizationUsed=False)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelsRun=0)))


if __name__=='__main__':main()
