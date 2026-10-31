"""Production UniForge orchestration with bounded, explicit IO fixtures.

These ONNX graphs test the stage contract, not the learned network math (covered
by test_uniforge_components). No complete model or device inference is claimed.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/'build/ultratex-python'),str(ROOT/'build/shape-reference-python'),str(ROOT/'build/spatial-reference-python')]
    import numpy as np
    import onnx
    from onnx import helper as h,TensorProto as T,numpy_helper as nh
    from PIL import Image
    from export_uniforge import manifest
    from uniforge_catalogue import roles
    from spatial_portable import Source
    out=ROOT/'build/uniforge-tests';out.mkdir(exist_ok=True);assets=out/'bundle';assets.mkdir(exist_ok=True)
    inputs=fingerprint('native/spatial','tools/test_uniforge.py','tools/export_uniforge.py','tools/uniforge_catalogue.py','third_party/portable-sparse-source-lock.json')
    checks=[]
    def check(name,value,**extra):assert value,(name,extra);checks.append(dict(case=name,**extra))
    alias=next((c+':' for c in 'TUVWXYZR' if not Path(c+':/').exists()),None);assert alias
    subprocess.run(['subst',alias,str(ROOT)],check=True,capture_output=True)
    def native(path):return alias+'/'+path.resolve().relative_to(ROOT).as_posix()
    def graph(name,fields,outputs,constants=None):
        nodes=[];initializers=[];info=[]
        # Every graph retains its declared closed inputs. Float outputs respond
        # to the supplied inputs, so the coordinator cannot omit any feed.
        for index,(key,shape,kind) in enumerate(fields):
            info.append(h.make_tensor_value_info(key,kind,shape));value=key
            if kind==T.INT64:nodes.append(h.make_node('Cast',[key],['float_'+key],to=T.FLOAT));value='float_'+key
            nodes.append(h.make_node('ReduceMean',[value],['mean_'+key],keepdims=0))
            if index==0:nodes.append(h.make_node('Identity',['mean_'+key],['sum_0']))
            else:nodes.append(h.make_node('Add',['sum_'+str(index-1),'mean_'+key],['sum_'+str(index)]))
        initializers.append(nh.from_array(np.array(1e-9,np.float32),'gain'));nodes.append(h.make_node('Mul',['sum_'+str(len(fields)-1),'gain'],['scalar']))
        for key,shape,kind in outputs:
            if constants and key in constants:initializers.append(nh.from_array(np.asarray(constants[key],np.float32 if kind==T.FLOAT else np.int64),key));continue
            if key.startswith('guide_coords'):nodes.append(h.make_node('Identity',['coords'],[key]));continue
            dynamic=isinstance(shape[0],str)
            if dynamic:
                nodes.append(h.make_node('Shape',['coords'],['coords_shape_'+key]));initializers.append(nh.from_array(np.array([0],np.int64),'axis_'+key));nodes.append(h.make_node('Gather',['coords_shape_'+key,'axis_'+key],['rows_'+key],axis=0));initializers.append(nh.from_array(np.array(shape[1:],np.int64),'tail_'+key));nodes.append(h.make_node('Concat',['rows_'+key,'tail_'+key],['shape_'+key],axis=0))
            else:initializers.append(nh.from_array(np.array(shape,np.int64),'shape_'+key))
            nodes.append(h.make_node('Expand',['scalar','shape_'+key],[key]))
        model=h.make_model(h.make_graph(nodes,name,info,[h.make_tensor_value_info(k,t,s) for k,s,t in outputs],initializers),opset_imports=[h.make_opsetid('',17)]);model.ir_version=9;onnx.checker.check_model(model);onnx.save(model,str(assets/(name+'.onnx')))
    try:
        f=lambda name,shape:(name,shape,T.FLOAT)
        i=lambda name,shape:(name,shape,T.INT64)
        for size in (512,1024):graph('dino'+str(size),[f('images',[1,4,3,size,size])],[f('features',[1,4,(size//16)**2+5,1024])])
        graph('structure_flow',[f('noisy',[1,8,16,16,16]),f('time',[1]),f('images',[1,4,3,448,448]),f('dino',[1,4,1029,1024])],[f('positive',[1,8,16,16,16]),f('negative',[1,8,16,16,16])])
        occupancy=np.full((1,1,64,64,64),-1,np.float32);occupancy[:,:,32:34,32:34,32:34]=1
        graph('structure_decoder',[f('latents',[1,8,16,16,16])],[f('occupancy',[1,1,64,64,64])],{'occupancy':occupancy})
        graph('conditioner',[f('images',[1,4,3,448,448]),i('coords',['rows',4])],[*(f('layer'+str(v),[1,4,1029,2048]) for v in (4,11,17,23)),f('points',[1,4,448,448,3]),f('confidence',[1,4,448,448])])
        for stage,grid in (('shape512',32),('shape1024',64),('texture',64)):
            graph(stage+'_adapter',[f('layer'+str(v),[1,4,1029,2048]) for v in (4,11,17,23)],[f('delta',[1,4,grid*grid,1024])])
            fields=[f('features',['rows',32]),i('coords',['rows',4]),f('time',[1]),f('full',[1,4,grid*grid+5,1024]),i('selected',['rows'])]
            if stage=='texture':fields+=[f('shape',['rows',32])]
            graph(stage+'_flow',fields,[f('velocity',['rows',32])])
        surface={};names=[f('features',['rows',32]),i('coords',['rows',4])]
        for stage,grid in (('shape512',512),('shape1024',1024)):
            coord=np.array([[0,grid//2,grid//2+y,grid//2+z] for y,z in ((0,0),(0,1),(1,1),(1,0))],np.int64)
            fields=np.tile(np.array([0,0,0,1,-1,-1,0],np.float32),(4,1));guides=[v for level in range(4) for v in (f('guide'+str(level),['rows',8]),i('guide_coords'+str(level),['rows',4]))]
            graph(stage+'_decoder',names,[f('fields',[4,7]),i('decoded_coords',[4,4]),*guides],dict(fields=fields,decoded_coords=coord));surface[stage]=coord
        graph('texture_decoder',names+guides,[f('materials',[4,6]),i('material_coords',[4,4])],dict(materials=np.tile(np.array([.5,-.5,.25,-.8,.4,1],np.float32),(4,1)),material_coords=surface['shape1024']))
        source=Source('D05');_,raw=source.read('uniforge3d/configs/pipeline.json');policy=json.loads(raw)
        config=dict(schema='lma.uniforge-export/1',pipeline='uniforge3d',source={k:source.record[k] for k in ('repository','revision')},dtype='float32',opset=17,views=4,
            imageSizes=[512,1024,448],structureChannels=8,structureResolution=16,latentChannels=32,featureWidth=1024,conditionWidth=2048,decoderLevels=4,occupancyResolution=64,
            inputPolicy='explicit_rgba_foreground',surfacePolicy='raw_fdg_sat_handoff',shapeNormalization=policy['texture']['shape_slat_normalization'],textureNormalization=policy['texture']['texture_slat_normalization'])
        (assets/'uniforge-config.json').write_text(json.dumps(config),'utf-8');manifest(assets,config,[]);bundle=json.loads((assets/'lma-bundle.json').read_text('utf-8'))
        views=out/'views';views.mkdir(exist_ok=True)
        for name in ('00_front.png','01_right.png','02_back.png','03_left.png'):
            image=np.zeros((32,32,4),np.uint8);image[4:28,6:26]=[86,126,190,255];Image.fromarray(image).save(views/name)
        command=dict(schema='lma.engine-request/1',type='mesh.generate',pipeline='uniforge3d',workspace=native(assets),output=native(out/'result.glb'),
            viewsDirectory=native(views),components={c['role']:native(assets/c['path']) for c in bundle['components']},parameters=dict(threads=2,seed=42,structureSteps=2,shapeSteps=2,textureSteps=2,maxRows=16384,maxTriangles=300000,atlas=256))
        def run(c,success):
            path=out/'request.json';path.write_text(json.dumps(c),'utf-8');output=Path(c['output'].replace(alias+'/',str(ROOT)+'/'));output.unlink(missing_ok=True)
            r=subprocess.run([native(ROOT/'build/spatial-worker-host/bin/lma_spatial.exe'),native(path)],capture_output=True,text=True,encoding='utf-8',timeout=90)
            check('production_native_outcome',(r.returncode==0)==success,tail=r.stdout[-1000:]);events=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')];return events
        events=run(command,True);check('complete_local_GLb',events[-1]['event']=='complete' and (out/'result.glb').stat().st_size>100)
        stages=[e['stage'] for e in events if e['event']=='stage'];check('all_cascade_stages',all(v in stages for v in ('encoding_multiview','sampling_structure','shape512_conditioning','shape1024_conditioning','texture_conditioning','decoding_geometry_material','baking_material')))
        execution=next(e['details'] for e in events if e['event']=='execution');check('disclosed_cpu_surface_policy',execution['surfacePolicy']=='raw_fdg_sat_handoff' and not execution['cudaRemeshingParity'])
        for key,value in (('threads',.25),('shapeSteps',True),('maxRows','invalid'),('atlas',257),('remote_url','https://example.invalid')):
            bad=copy.deepcopy(command);bad['parameters'][key]=value;run(bad,False);check('invalid_parameter_'+key,True)
        bad=copy.deepcopy(command);bad['components'].pop('texture_flow');run(bad,False);check('missing_network_rejected',True)
        old=copy.deepcopy(config);config['source']['revision']='0'*40;(assets/'uniforge-config.json').write_text(json.dumps(config),'utf-8');run(command,False);check('unmatched_source_rejected',True)
        (assets/'uniforge-config.json').write_text(json.dumps(old),'utf-8');manifest(assets,old,[])
        current(inputs)
    finally:subprocess.run(['subst',alias,'/D'],check=True,capture_output=True)
    report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,actualNativeWorker=True,contractFixtures=True,learnedNetworkMathSuite='build/uniforge-component-tests/results.json',completeModelsRun=0,phoneTests=0,virtualizationUsed=False)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks))))


if __name__=='__main__':main()
