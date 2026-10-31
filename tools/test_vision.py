"""Actual DIS blocks, source preprocessing, native workers and bounded VLM contracts.

Random tiny networks and interface fixtures only. No trained assets or devices.
"""
import ast,copy,json,os,shutil,subprocess,sys,types
from pathlib import Path
from evidence import ROOT,fingerprint,current


def main():
    sys.path[:0]=[str(ROOT/"build/shape-reference-python"),str(ROOT/"build/spatial-reference-python")]
    import numpy as np,torch,onnx,onnxruntime as ort
    from PIL import Image
    from onnx import helper as h,TensorProto as T
    from vision_components import definitions,Foreground
    from shape_graphs import export_graph
    from fetch_vision_sources import verify
    from safetensors.torch import save_file
    torch.set_num_threads(2);torch.manual_seed(8114);source=verify()
    inputs=fingerprint('native/vision','tools/test_vision.py','tools/vision_components.py','tools/export_foreground.py','tools/vision_catalogue.py','third_party/vision-source-lock.json','tests/expansion-native/vision.cpp')
    receipt=json.loads((ROOT/'build/vision-worker-host/receipt.json').read_text('utf-8'));current(receipt['source_inputs']);out=ROOT/'build/vision-tests';out.mkdir(exist_ok=True)
    checks=[];drive=next(c+':' for c in 'RTUVWXYZ' if not Path(c+':/').exists());subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    def path(p):return drive+'/'+p.relative_to(ROOT).as_posix()
    def run(request,success=True,worker=False):
        file=out/'request.json';file.write_text(json.dumps(request),'utf-8');binary='lma_vision_worker.exe' if worker else 'lma_vision_contract.exe'
        p=subprocess.run([path(ROOT/'build/vision-worker-host/bin'/binary),path(file)],capture_output=True,text=True,encoding='utf-8',timeout=45)
        assert (p.returncode==0)==success,(p.stdout[-1000:],p.stderr[-1000:]);return p.stdout if worker else json.loads(p.stdout) if success else None
    try:
        d=definitions()
        with torch.device('meta'):formal=d['ISNetDIS'](3,1)
        assert sum(p.numel() for p in formal.parameters())>10000000;checks.append('formal_publisher_ISNetDIS_meta_construction')
        for name in ['RSU7','RSU6','RSU5','RSU4','RSU4F']:
            model=d[name](3,2,4).eval();pixels=torch.randn(1,3,32,32);graph=out/(name+'.onnx');export_graph(model,(pixels,),graph,['pixels'],'mask',{})
            with torch.inference_mode():expected=model(pixels).numpy()
            actual=ort.InferenceSession(str(graph),providers=['CPUExecutionProvider']).run(None,{'pixels':pixels.numpy()})[0];np.testing.assert_allclose(actual,expected,atol=3e-5,rtol=3e-4);checks.append('actual_source_'+name+'_onnx_parity')
        # Torch calls and integer conversion are exactly those in pinned Inference.py.
        for w,hg,side in [(11,7,9),(8,13,16),(12,12,12),(7,11,5)]:
            pixels=np.random.default_rng(w).integers(0,256,size=(hg,w,4),dtype=np.uint8);request=dict(width=w,height=hg,side=side,rgba=pixels.flatten().tolist())
            src=torch.from_numpy(pixels[:,:,:3].copy()).permute(2,0,1)[None].float();resized=torch.nn.functional.interpolate(src,size=(side,side),mode='bilinear',align_corners=False).to(torch.uint8).float()/255-.5
            actual=np.asarray(run(dict(request,operation='pixels'))).reshape(1,3,side,side);error=float(abs(actual-resized.numpy()).max());assert error<=1.001/255,(w,hg,error);checks.append('publisher_preprocess_uint8_'+str(w)+'x'+str(hg))
            mask=torch.rand(1,1,side,side);alpha=torch.nn.functional.interpolate(mask,size=(hg,w),mode='bilinear',align_corners=False);alpha=((alpha-alpha.min())/(alpha.max()-alpha.min())*255).to(torch.uint8).numpy().reshape(hg,w)
            native=np.asarray(run(dict(request,operation='alpha',mask=mask.numpy().flatten().tolist())),dtype=np.uint8).reshape(hg,w,4);np.testing.assert_array_equal(native[:,:,:3],pixels[:,:,:3]);assert abs(native[:,:,3].astype(int)-alpha.astype(int)).max()<=1;checks.append('publisher_mask_postprocess_'+str(w)+'x'+str(hg))
        run(dict(width=2,height=2,side=2,rgba=[255]*16,operation='alpha',mask=[.5]*4),False);checks.append('constant_mask_rejected')
        for text in ['{"parts":[{"name":"leg"},{"name":"seat"}]}','{"parts":[{"name":"轮胎"}]}']:
            assert run(dict(operation='parts',text=text))==json.loads(text);checks.append('native_parts_json_valid')
        for value in [{},dict(parts=[]),dict(parts=[dict(name='a')]*2),dict(parts=[dict(name='x'+str(i)) for i in range(17)]),dict(parts=[dict(name='a')],url='https://example.invalid'),dict(parts=[dict(name='\n')])]:
            run(dict(operation='parts',text=json.dumps(value)),False);checks.append('native_invalid_parts_rejected')
        # Actual exporter transaction with a small source RSU test factory.
        # This does not export/run the formal full network or trained checkpoint.
        class Small(torch.nn.Module):
            def __init__(self):super().__init__();self.block=d['RSU4'](3,2,1)
            def forward(self,pixels):return [torch.sigmoid(self.block(pixels))],[]
        import vision_components,export_foreground
        old=vision_components.construct
        try:
            vision_components.construct=Small;weights=out/'random.safetensors';save_file(Small().state_dict(),str(weights));exported=out/'bundle'
            if exported.exists():assert exported.resolve().parent==out.resolve();shutil.rmtree(exported)
            bundle=export_foreground.export(weights,exported,256);checks.append('offline_actual_source_export_transaction')
            try:export_foreground.export(weights,exported,256);raise AssertionError('overwrite')
            except AssertionError as e:assert str(e)!='overwrite'
            checks.append('export_preserves_existing_output')
        finally:vision_components.construct=old
        image=out/'reference.png';Image.fromarray(np.random.default_rng(5).integers(0,256,(19,23,3),dtype=np.uint8)).save(image)
        # Production worker actual neural graph is the explicit tiny random RSU fixture.
        command=dict(schema='lma.engine-request/1',type='image.generate',pipeline='isnet_dis',parameters=dict(threads=2),workspace=path(exported),components={c['role']:path(exported/c['path']) for c in bundle['components']},referenceImage=path(image),output=path(out/'result.png'))
        (out/'result.png').unlink(missing_ok=True);events=run(command,worker=True);result=Image.open(out/'result.png');assert result.mode=='RGBA' and result.size==(23,19) and 'complete' in events;checks.append('production_foreground_worker_actual_tiny_network')
        for field,value in [('parameters',dict(threads=2,remote_url='https://example.invalid')),('pipeline','unsupported')]:
            bad=copy.deepcopy(command);bad[field]=value;bad['output']=path(out/'invalid.png');(out/'invalid.png').unlink(missing_ok=True);run(bad,False,True);assert not (out/'invalid.png').exists();checks.append('production_bad_'+field+'_no_fallback')
        for c in bundle['components']:
            from hashlib import sha256
            assert sha256((exported/c['path']).read_bytes()).hexdigest()==c['sha256']
        checks.append('exported_component_hashes')
        current(inputs);current(receipt['source_inputs']);report=dict(passed=len(checks),checks=checks,input_fingerprint=inputs,completeModels=0,phoneTests=0,trainedInference=False,virtualization=False)
        (out/'results.json').write_text(json.dumps(report,indent=2)+'\n','utf-8');print(json.dumps(dict(passed=len(checks),completeModels=0)))
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)


if __name__=='__main__':main()
