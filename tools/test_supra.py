"""Production SUPRA workflow and exact CPU observation contracts, no trained model."""
import ast
import copy
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import types
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    import numpy as np
    import onnx
    from onnx import helper as h,TensorProto as T,numpy_helper as nh
    from PIL import Image,ImageFilter
    from tokenizers import Tokenizer,models,pre_tokenizers,AddedToken
    from spatial_portable import Source
    from export_supra import manifest
    out=ROOT/'build/supra-tests';out.mkdir(exist_ok=True);assets=out/'bundle';assets.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial','tests/expansion-native/cascade.cpp','tools/test_supra.py','tools/export_supra.py','tools/supra_catalogue.py','third_party/portable-sparse-source-lock.json')
    checks=[]
    def check(case,value,**extra):assert value,(case,extra);checks.append(dict(case=case,**extra))
    alias=next(c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists());subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(path):return alias+'/'+path.resolve().relative_to(ROOT).as_posix()
    def contract(value,success=True):
        file=out/'contract.json';file.write_text(json.dumps(value),'utf-8');p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_cascade_contract.exe'),native(file)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        check(value['operation']+'_outcome',(p.returncode==0)==success,error=p.stderr[-400:]);return json.loads(p.stdout) if success else None
    def graph(name,fields,outputs,pool=False):
        nodes=[];initial=[];info=[h.make_tensor_value_info(k,t,s) for k,s,t in fields]
        if pool:
            # Four exact integer S2C coordinate reductions; features only serve
            # this explicitly synthetic IO fixture, not a learned replacement.
            initial+=[nh.from_array(np.array([1],np.int64),'one'),nh.from_array(np.array([2],np.int64),'factor')]
            nodes.append(h.make_node('ReduceMean',[fields[0][0]],['base_feature'],axes=[1],keepdims=1));lastf='base_feature';lastc='coords'
            for level in range(4):
                f,c,idx,child=[k+str(level) for k in ('f','c','i','ch')]
                nodes.append(h.make_node('SpatialToChannel3D',[lastf,lastc,'factor'],[f,c,idx,child],domain='lma.spatial'))
                nodes.append(h.make_node('ReduceMean',[f],[f+'mean'],axes=[1],keepdims=1));lastf=f+'mean';lastc=c
            nodes.append(h.make_node('Identity',[lastc],['latent_coords']));rowsfrom='latent_coords'
        else:rowsfrom='surface_coords' if name.endswith('decoder') else 'features'
        for key,shape,kind in outputs:
            if pool and key=='latent_coords':continue
            if kind==T.INT64:
                nodes.append(h.make_node('Identity',['surface_coords'],[key]));continue
            if isinstance(shape[0],str):
                nodes.append(h.make_node('Shape',[rowsfrom],['in_shape_'+key]));initial.append(nh.from_array(np.array([0],np.int64),'axis_'+key));nodes.append(h.make_node('Gather',['in_shape_'+key,'axis_'+key],['rows_'+key],axis=0));initial.append(nh.from_array(np.array(shape[1:],np.int64),'tail_'+key));nodes.append(h.make_node('Concat',['rows_'+key,'tail_'+key],['size_'+key],axis=0))
            else:initial.append(nh.from_array(np.array(shape,np.int64),'size_'+key))
            nodes.append(h.make_node('ConstantOfShape',['size_'+key],[key],value=nh.from_array(np.array([.1 if key=='fields' else 0.],np.float32))))
        model=h.make_model(h.make_graph(nodes,name,info,[h.make_tensor_value_info(k,t,s) for k,s,t in outputs],initial),opset_imports=[h.make_opsetid('',17),h.make_opsetid('lma.spatial',1)]);model.ir_version=9;onnx.checker.check_model(model);onnx.save(model,str(assets/(name+'.onnx')))
    def make_glb(file):
        v=[[-.001,-.001,-.001],[.001,-.001,-.001],[.001,.001,-.001],[-.001,.001,-.001],[-.001,-.001,.001],[.001,-.001,.001],[.001,.001,.001],[-.001,.001,.001]]
        faces=[0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7]
        binary=struct.pack('<24f',*(x for p in v for x in p))+struct.pack('<36I',*faces)
        doc=dict(asset=dict(version='2.0'),buffers=[dict(byteLength=len(binary))],bufferViews=[dict(buffer=0,byteOffset=0,byteLength=96),dict(buffer=0,byteOffset=96,byteLength=144)],
            accessors=[dict(bufferView=0,componentType=5126,count=8,type='VEC3',min=[-.001]*3,max=[.001]*3),dict(bufferView=1,componentType=5125,count=36,type='SCALAR')],meshes=[dict(primitives=[dict(attributes=dict(POSITION=0),indices=1,mode=4)])],nodes=[dict(mesh=0)],scenes=[dict(nodes=[0])],scene=0)
        text=json.dumps(doc,separators=(',',':')).encode();text+=b' '*((-len(text))%4);file.write_bytes(struct.pack('<III',0x46546c67,2,12+8+len(text)+8+len(binary))+struct.pack('<II',len(text),0x4e4f534a)+text+struct.pack('<II',len(binary),0x004e4942)+binary)
    try:
        source=Source('D10');_,raw=source.read('supratex/inference/native_observation.py');tree=ast.parse(raw)
        outer=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_dda_batch_kernel');kernel=next(n for n in outer.body if isinstance(n,ast.FunctionDef));kernel.decorator_list=[]
        env=dict(np=np,math=math,numba=types.SimpleNamespace(prange=range));exec(compile(ast.fix_missing_locations(ast.Module(body=[kernel],type_ignores=[])),'literal-source-dda','exec'),env)
        camera=dict(distance=2,camera_angle_x=1.0);size=32;grid=8;coords=np.array([[0,x,y,3] for x in range(8) for y in range(8)],np.int64)
        alpha=np.full((size,size),255,np.uint8);eye=np.array([0.,0.,2.]);f=.5/math.tan(.5)
        yy,xx=np.mgrid[0:size,0:size];directions=np.stack((((xx+.5)/size-.5)/f,-((yy+.5)/size-.5)/f,-np.ones_like(xx)),axis=-1).reshape(-1,3)
        bits=np.zeros((grid**3+7)//8,np.uint8);keys=(coords[:,1]*grid+coords[:,2])*grid+coords[:,3];np.bitwise_or.at(bits,keys>>3,(1<<(keys&7)).astype(np.uint8))
        owners,reasons,ties=env['kernel'](eye,directions,bits,-.5,.5,grid)
        reference=set(map(tuple,owners[reasons==0]));expected=[tuple(c[1:]) in reference for c in coords]
        got=contract(dict(operation='supra_visible',coords=coords.tolist(),alpha=alpha.flatten().tolist(),camera=camera,size=size,grid=grid));check('literal_first_hit_dda',got==[int(v) for v in expected])
        contract(dict(operation='supra_visible',coords=coords.tolist(),alpha=np.zeros_like(alpha).flatten().tolist(),camera=camera,size=size,grid=grid),False)
        full=[[0,0,0,0],[0,1,0,0],[0,2,0,0],[0,10,10,10]];surface=[[0,0,0,0],[0,1,0,0],[0,16,0,0],[0,32,0,0],[0,160,160,160]];visible=[1,0,1,0,1];observed=[full[i] for i in (0,1,3)]
        got=contract(dict(operation='supra_messages',raw=[.5]*96,observed=observed,surface=surface,visible=visible,shape=full,normalization=dict(mean=[.1]*32,std=[.8]*32)))
        got=np.array(got).reshape(3,34);check('coverage_and_disconnected_distance',np.allclose(got[:,32],[.5,1,1]) and list(got[:,33])==[2,1,-1] and np.allclose(got[:,:32],.5))
        ffield=lambda k,s:(k,s,T.FLOAT);ifield=lambda k,s:(k,s,T.INT64)
        vocab={'<unk>':0,**{v:i+1 for i,v in enumerate(sorted(pre_tokenizers.ByteLevel.alphabet()))}};tokenizer=Tokenizer(models.BPE(vocab=vocab,merges=[],unk_token='<unk>'));tokenizer.pre_tokenizer=pre_tokenizers.ByteLevel(add_prefix_space=False);tokenizer.add_special_tokens([AddedToken('<|image_pad|>',special=True,normalized=False)]);tokenizer.save(str(assets/'qwen-tokenizer.json'))
        template='a<|image_pad|>b';marker=tokenizer.token_to_id('<|image_pad|>');ids=tokenizer.encode(template).ids;expanded=[value for item in ids for value in ([item]*1024 if item==marker else [item])];length=len(expanded)-1
        graph('qwen_text',[ifield('ids',[1,len(expanded)]),ffield('pixels',[4096,1536])],[ffield('features',[1,length,4096])])
        graph('qwen_encode',[ffield('rgba',[1,4,1024,1024])],[ffield('latent',[1,64,64,64])]);graph('qwen_decode',[ffield('latent',[1,64,64,64])],[ffield('rgba',[1,4,1024,1024])])
        graph('qwen_material',[ffield('noise',[1,2,64,64,64]),ffield('prompt',[1,length,4096]),ffield('rgb',[1,64,64,64])],[ffield('velocity',[1,2,64,64,64])])
        graph('shape_encoder',[ffield('vertices',['surface',3]),ffield('intersected',['surface',3]),ifield('coords',['surface',4])],[ffield('latent',['rows',32]),ifield('latent_coords',['rows',4])],True)
        graph('material_encoder',[ffield('features',['surface',6]),ifield('coords',['surface',4])],[ffield('latent',['rows',32]),ifield('latent_coords',['rows',4])],True)
        for name,channels in [('shape_decoder',7),('material_decoder',6)]:graph(name,[ffield('features',['latent',32]),ifield('coords',['latent',4]),ifield('surface_coords',['surface',4])],[ffield('fields',['surface',channels]),ifield('decoded_coords',['surface',4])])
        graph('completion',[ffield('features',['rows',32]),ifield('coords',['rows',4]),ffield('time',[1]),ffield('shape',['rows',32]),ffield('observed',['observed',34]),ifield('observed_coords',['observed',4])],[ffield('velocity',['rows',32])])
        stats=dict(mean=[0.]*32,std=[1.]*32)
        cfg=dict(schema='lma.supratex-export/1',pipeline='supratex',source={k:source.record[k] for k in ('repository','revision')},dtype='float32',opset=17,resolution=1024,latentChannels=32,decoderLevels=4,inputPolicy='mesh_camera_rgba',surfacePolicy='original_mesh_exact_encoder_topology',
            qwen=dict(template=template,prompt='Explicit program fixture',tokenIds=expanded,imageToken=marker,drop=1,grid=[1,64,64],patch=16,merge=2,temporal=2,vocabulary=151936,mean=[.5]*3,std=[.5]*3),
            shapeNormalization=stats,pbrNormalization=stats,partialNormalization=stats,sampler=dict(steps=25,shift=3,sigmaMin=1e-5,policy='euler_static_observation_no_cfg'))
        configfile=assets/'supra-config.json';configfile.write_text(json.dumps(cfg),'utf-8');manifest(assets,cfg,[]);bundle=json.loads((assets/'lma-bundle.json').read_text('utf-8'))
        image=np.zeros((1024,1024,4),np.uint8);image[400:624,400:624]=[90,130,175,255];Image.fromarray(image).save(out/'reference.png');make_glb(out/'source.glb');(out/'camera.txt').write_text(json.dumps(dict(distance=.01,camera_angle_x=1.0)),'utf-8')
        command=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline='supratex',workspace=native(assets),output=native(out/'result.glb'),referenceImage=native(out/'reference.png'),sourceMesh=native(out/'source.glb'),camera=native(out/'camera.txt'),
            components={c['role']:native(assets/c['path']) for c in bundle['components']},parameters=dict(threads=2,seed=42,steps=2,atlas=256,maxRows=20000))
        def execute(c,success=True):
            (out/'result.glb').unlink(missing_ok=True)
            request=out/'contract-generate.json';request.write_text(json.dumps(dict(operation='generate',command=c)),'utf-8')
            p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_cascade_contract.exe'),native(request)],capture_output=True,text=True,encoding='utf-8',timeout=90)
            check('native_workflow_outcome',(p.returncode==0)==success,error=p.stderr[-600:],events=p.stdout[-600:]);return [json.loads(line) for line in p.stdout.splitlines() if line.startswith('{')]
        events=execute(command);check('local_pbr_glb_created',(out/'result.glb').is_file() and events[-1]['event']=='complete')
        glb=(out/'result.glb').read_bytes();doc=json.loads(glb[20:20+struct.unpack_from('<I',glb,12)[0]]);check('embedded_pbr_resources',len(doc['images'])==2 and 'metallicRoughnessTexture' in doc['materials'][0]['pbrMetallicRoughness'])
        (out/'completed-contract.glb').write_bytes(glb)
        (out/'result.glb').unlink()
        request=out/'worker-request.json';request.write_text(json.dumps(command),'utf-8')
        p=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),native(request)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        check('actual_production_worker',p.returncode==0 and (out/'result.glb').is_file(),error=p.stderr[-600:],events=p.stdout[-600:])
        stages=[e['stage'] for e in events if e['event']=='stage'];check('all_production_stages',all(v in stages for v in ('qwen_visual_conditioning','predicting_albedo_mra','encoding_geometry_observation','sampling_material_completion','baking_material')))
        for key,value in [('threads',False),('steps',.5),('atlas',257),('remote_url','https://invalid.example')]:bad=copy.deepcopy(command);bad['parameters'][key]=value;execute(bad,False)
        bad=copy.deepcopy(command);bad['components'].pop('completion');execute(bad,False)
        badcfg=copy.deepcopy(cfg);badcfg['source']['revision']='0'*40;configfile.write_text(json.dumps(badcfg),'utf-8');execute(command,False);configfile.write_text(json.dumps(cfg),'utf-8');manifest(assets,cfg,[])
        current(inputs);report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,contractFixtures=True,actualNativeWorkflow=True,learnedNetworkMathSuite='build/supra-component-tests/results.json',completeModelsRun=0,phoneTests=0)
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
