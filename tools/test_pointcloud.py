"""Actual publisher random VAE, source-FPS oracle and production child checks."""
import copy,hashlib,json,os,shutil,struct,subprocess,sys
from pathlib import Path
from evidence import ROOT,current,fingerprint

OUT=ROOT/'build/pointcloud-tests'


def main():
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONIOENCODING='utf-8')
    sys.path.insert(0,str(ROOT/'build/shape-reference-python'))
    import numpy as np,torch,onnxruntime as ort
    from export_shape import reference
    from shape_graphs import portable_attention,export_graph
    from pointcloud_graphs import PointEncoder
    torch.set_num_threads(2);torch.manual_seed(739)
    inputs=fingerprint('tools/test_pointcloud.py','tools/export_pointcloud.py','tools/pointcloud_graphs.py','tools/pointcloud_catalogue.py','tools/shape_graphs.py','tools/export_shape.py','native/rf_shape','tests/expansion-native/pointcloud.cpp','third_party/rf-shape-source-lock.json')
    receipt=json.loads((ROOT/'build/shape-worker-host/receipt.json').read_text('utf-8'));current(receipt['source_inputs'])
    OUT.mkdir(exist_ok=True);checks=[]
    drive=next(c+':' for c in 'RTUVWXYZ' if not Path(c+':/').exists())
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    def path(p):return drive+'/'+p.resolve().relative_to(ROOT).as_posix()
    def run(exe,request):
        file=OUT/'request.json';file.write_text(json.dumps(request),'utf-8')
        return subprocess.run([path(exe),path(file)],capture_output=True,text=True,encoding='utf-8',timeout=90)
    try:
        # Literal source CPU FPS recurrence (torch argmax chooses first tie).
        for shape in ['random','ties','duplicate']:
            points=torch.randn(32,6);points[:,3:]=torch.nn.functional.normalize(points[:,3:],dim=-1)
            if shape=='ties':points[:,:3]=torch.tensor([1.,0.,0.]);points[0,:3]=torch.tensor([-1.,0.,0.])
            if shape=='duplicate':points[10:]=points[0]
            ids=np.random.default_rng(774).choice(len(points),32,replace=False).tolist();selected=points[ids,:3];index=0;distance=((selected-selected[index])**2).sum(1);indices=[index]
            for i in range(1,8):index=int(distance.argmax());indices.append(index);distance=torch.minimum(distance,((selected-selected[index])**2).sum(1))
            result=run(ROOT/'build/shape-worker-host/bin/lma_point_contract.exe',dict(points=points.flatten().tolist(),candidates=ids,tokens=8))
            assert result.returncode==0,result.stderr
            np.testing.assert_allclose(json.loads(result.stdout)['queries'],points[[ids[i] for i in indices]].flatten().numpy(),rtol=0,atol=0)
            checks.append('native_fps_source_'+shape)
        for pipeline in ['triposg','partcrafter']:
            _,_,VAE=reference(pipeline)
            model=VAE(latent_channels=4,num_attention_heads=2,width_encoder=16,width_decoder=16,num_layers_encoder=1,num_layers_decoder=2,embed_frequency=2).eval()
            original=copy.deepcopy(model);portable_attention(model);wrapper=PointEncoder(model)
            target=OUT/(pipeline+'-encoder.onnx')
            export_graph(wrapper,(torch.randn(1,31,6),torch.randn(1,8,6)),target,['points','sampled_points'],'moments',{'points':{1:'points'},'sampled_points':{1:'tokens'},'moments':{1:'tokens'}})
            options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
            session=ort.InferenceSession(str(target),sess_options=options,providers=['CPUExecutionProvider'])
            for n,tokens in [(31,8),(127,13),(16,32)]:
                points=torch.randn(1,n,6);queries=torch.randn(1,tokens,6)
                with torch.inference_mode():
                    # Original actual source _encode, replacing only its FPS
                    # selection with the already separately verified queries.
                    original._sample_features=lambda *args,**kwargs:queries
                    expected=original._encode(points,num_tokens=tokens,seed=1234).numpy()
                actual=session.run(None,dict(points=points.numpy(),sampled_points=queries.numpy()))[0]
                np.testing.assert_allclose(expected,actual,rtol=1e-4,atol=2e-5);checks.append(pipeline+'_actual_source_encoder_'+str((n,tokens)))
            snapshot=OUT/(pipeline+'-snapshot');snapshot.mkdir(exist_ok=True);model.save_pretrained(snapshot/'vae',safe_serialization=True)
            bundle_dir=OUT/(pipeline+'-bundle')
            if bundle_dir.exists():assert bundle_dir.parent==OUT;shutil.rmtree(bundle_dir)
            command=[sys.executable,str(ROOT/'tools/export_pointcloud.py'),'--pipeline',pipeline,'--snapshot',str(snapshot),'--output',str(bundle_dir)]
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=100,env={**os.environ,'PYTHONPATH':str(ROOT/'build/shape-reference-python')})
            assert result.returncode==0,(result.stdout,result.stderr)
            bundle=json.loads((bundle_dir/'lma-bundle.json').read_text('utf-8'))
            assert bundle['pipeline']==pipeline+'_points' and bundle['capabilities']==['pointcloud_to_3d','vae_reconstruction','sdf_geometry']
            for item in bundle['components']:
                assert item['url']=='' and hashlib.sha256((bundle_dir/item['path']).read_bytes()).hexdigest()==item['sha256']
            checks.append(pipeline+'_real_cli_random_safetensors')
            assert subprocess.run(command,capture_output=True,timeout=30).returncode!=0;checks.append(pipeline+'_no_overwrite')
            # Keep actual encoder + cache, replace only the SDF query with a
            # disclosed sphere IO fixture so random weights need not form a mesh.
            from test_shape import fixture
            query_dir=OUT/'query-fixture';fixture(query_dir,'triposg')
            shutil.copy2(query_dir/'query.onnx',bundle_dir/'query.onnx')
            (bundle_dir/'query.onnx.data').unlink(missing_ok=True)
            rows=np.random.default_rng(228).normal(size=(64,6)).astype('float32');rows[:,:3]=np.clip(rows[:,:3]*.2,-.9,.9);rows[:,3:]/=np.linalg.norm(rows[:,3:],axis=-1,keepdims=True)
            point_file=OUT/'cloud.txt';cloud=dict(schema='lma.pointcloud/1',coordinates='publisher_normalized',points=rows.tolist());point_file.write_text(json.dumps(cloud),'utf-8')
            cfg=(bundle_dir/'shape-config.json').read_bytes()
            worker=ROOT/'build/shape-worker-host/bin/lma_rf_shape.exe'
            for case in ['mean','sample','publisher_octree','publisher_flash','bad_normals','bad_coordinate','missing_normals','missing_encoder','bad_source','memory_budget','remote_parameter']:
                points=copy.deepcopy(cloud);parameters=dict(threads=2,tokens=512,grid=32,queryChunk=512,posterior='sample' if case=='sample' else 'mean')
                if case.startswith('publisher_'):parameters.update(extraction=case,octreeDepth=5,denseDepth=3)
                components={c['role']:path(bundle_dir/c['path']) for c in bundle['components'] if not c['path'].startswith('query.onnx.data')}
                config=json.loads(cfg)
                if case=='bad_normals':points['points'][0][3:]=[0,0,0]
                if case=='bad_coordinate':points['points'][0][0]=2
                if case=='missing_normals':points['points'][0]=[0,0,0]
                if case=='missing_encoder':components.pop('encoder')
                if case=='bad_source':config['source']['revision']='0'*40
                if case=='memory_budget':points['points']=points['points']*256;parameters['tokens']=4096
                if case=='remote_parameter':parameters['remote_url']='https://example.invalid'
                point_file.write_text(json.dumps(points),'utf-8');(bundle_dir/'shape-config.json').write_text(json.dumps(config),'utf-8')
                output=OUT/'output.glb';output.unlink(missing_ok=True)
                result=run(worker,dict(schema='lma.engine-request/1',type='mesh.generate',pipeline=pipeline+'_points',workspace=path(bundle_dir),components=components,parameters=parameters,pointCloud=path(point_file),output=path(output)))
                ok=case in ['mean','sample','publisher_octree','publisher_flash'];assert (result.returncode==0)==ok,(case,result.stdout,result.stderr)
                assert output.is_file()==ok
                if ok:
                    data=output.read_bytes();assert data[:4]==b'glTF';size=struct.unpack_from('<I',data,12)[0];root=json.loads(data[20:20+size]);assert len(root['meshes'])==1
                    assert any(json.loads(line).get('stage')=='encoding_pointcloud' for line in result.stdout.splitlines() if line.startswith('{'))
                    shutil.copy2(output,OUT/(pipeline+'-'+case+'.glb'))
                checks.append(pipeline+'_production_'+case)
            (bundle_dir/'shape-config.json').write_bytes(cfg)
        current(inputs);current(receipt['source_inputs'])
        report=dict(passed=len(checks),checks=checks,completeModelDownloads=0,completeModelRuns=0,phoneTests=0,randomActualSourceNetworks=True,surfaceQueryFixture=True,input_fingerprint=inputs)
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModelRuns=0,phoneTests=0)))
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
