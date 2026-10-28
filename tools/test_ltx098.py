"""Execute independent publisher-PyTorch/native CPU/Vulkan DiT parity checks.

UNTRAINED reduced-width fixtures include all 28 layers. This never proves trained
video generation, an Android execution, an App engine, or an inference API.
"""
import argparse,copy,hashlib,json,os,subprocess,sys,time
from pathlib import Path
import numpy as np
from evidence import current,fingerprint
from build_ltx098 import ROOT,validate_sources

OUT=ROOT/'build/ltx098-tests'
FIXTURES=OUT/'fixtures'

def run(command,log,timeout=600):
    result=subprocess.run([str(x) for x in command],cwd=ROOT,capture_output=True,timeout=timeout)
    log.write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Command failed; inspect '+str(log.relative_to(ROOT)))
    return result.stdout.decode('utf-8',errors='replace')

def fixtures(force):
    keys=fingerprint('tools/ltx098_fixture.py','tools/build_ltx098.py','third_party/ltx098-source-lock.json')
    receipt=OUT/'fixture-receipt.json';valid=False
    if receipt.exists() and not force:
        saved=json.loads(receipt.read_text(encoding='utf-8'))
        valid=saved['input_fingerprint']==keys and all((FIXTURES/name).is_file() and hashlib.sha256((FIXTURES/name).read_bytes()).hexdigest()==digest for name,digest in saved['files'].items())
    if not valid:
        FIXTURES.mkdir(exist_ok=True)
        run([sys.executable,'tools/ltx098_fixture.py',FIXTURES],OUT/'oracle.log')
        saved=dict(input_fingerprint=keys,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FIXTURES.iterdir() if p.is_file()})
        receipt.write_text(json.dumps(saved,indent=2)+'\n',encoding='utf-8')
    return json.loads((FIXTURES/'cases.json').read_text(encoding='utf-8')),json.loads((FIXTURES/'oracle.json').read_text(encoding='utf-8'))

def binary(backend,skip):
    directory=ROOT/('build/ltx098-host-'+backend);path=directory/'lma_ltx098_probe.exe';record=directory/'receipt.json'
    keys=fingerprint('research/ltx098','tools/build_ltx098.py','third_party/ltx098-source-lock.json')
    valid=False
    if path.is_file() and record.is_file():
        saved=json.loads(record.read_text(encoding='utf-8'))
        valid=saved['input_fingerprint']==keys and saved['binary_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    if not valid:
        if skip:raise RuntimeError('Stale native build: '+backend)
        command=[sys.executable,'tools/build_ltx098.py']+(['--vulkan'] if backend=='vulkan' else [])
        run(command,OUT/('build-'+backend+'.log'),1200)
    return path,json.loads(record.read_text(encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rebuild-fixtures',action='store_true');parser.add_argument('--skip-build',action='store_true');parser.add_argument('--cpu-only',action='store_true');args=parser.parse_args()
    validate_sources();OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('research/ltx098','tools/build_ltx098.py','tools/fetch_ltx098.py','tools/ltx098_fixture.py','tools/test_ltx098.py','third_party/ltx098-source-lock.json')
    os.environ['TEMP']=os.environ['TMP']=str(ROOT/'build/tmp')
    cases,oracle=fixtures(args.rebuild_fixtures)
    backends=['cpu'] if args.cpu_only else ['cpu','vulkan'];executables={};builds={}
    for backend in backends:executables[backend],builds[backend]=binary(backend,args.skip_build)
    checks=0;children=0;guards=0;metrics=[];outputs={};native_records=[];devices=set()
    result_dir=OUT/'outputs';result_dir.mkdir(exist_ok=True)
    def check(condition,message):
        nonlocal checks
        if not condition:raise AssertionError(message)
        checks+=1
    def native(backend,model,request,name,ok=True,threads='4',fixture=True,selected=None,preserve=False):
        nonlocal children,guards
        output=result_dir/(name+'.f32')
        if not preserve:output.unlink(missing_ok=True)
        command=[str(executables[backend]),str(model),str(request),str(output),selected or backend,threads]+(['--fixture'] if fixture else [])
        start=time.monotonic();result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=120)
        children+=1;(result_dir/(name+'.log')).write_bytes(result.stdout+result.stderr)
        record=json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1])
        check(result.returncode==(0 if ok else 2),'Unexpected child exit: '+name)
        check(record['ok']==ok,'Unexpected protocol success: '+name)
        check(not record['complete_video_pipeline'],'Incorrect complete-video claim')
        if not ok:
            guards+=1
            if not preserve:check(not output.exists(),'Rejected request produced output: '+name)
            return record
        check(record['backend']==backend,'Backend silently changed: '+name)
        check(record['fixture'] and not record['physical_android'],'Fixture/device evidence mislabeled')
        if backend=='vulkan':
            check(record['precision_policy']=='baseline_f32_compute_optional_f16_weight_storage','Wrong Vulkan precision policy')
            identity=[line.strip() for line in result.stderr.decode('utf-8',errors='replace').splitlines() if 'ggml_vulkan: 0 =' in line]
            check(len(identity)==1 and 'fp16: 0' in identity[0] and 'matrix cores: none' in identity[0],'GPU baseline precision was not applied')
            devices.add(identity[0])
        native_records.append(dict(name=name,backend=backend,layers=record['layers'],parameters=record['parameters'],weight_bytes=record['weight_bytes'],compute_bytes=record['compute_bytes'],elapsed_seconds=round(time.monotonic()-start,6)))
        return np.fromfile(output,dtype='<f4'),record
    check(oracle['full_tensors']==715 and oracle['full_parameters']==1923385472,'Wrong exact checkpoint architecture')
    check(not oracle['full_weights_loaded'] and oracle['synthetic_parameters'],'Oracle claims trained checkpoint')
    check(len(cases)==12 and max(c['layers'] for c in cases)==28,'Wrong fixture coverage')
    for backend in backends:
        for precision in ['f32','f16']:
            # Fixed before running: reduced-width F32 parity; F16 CPU matmul also
            # rounds activations, so its distinct gate covers that precision path.
            max_gate,rmse_gate=(1e-4,3e-5) if precision=='f32' else (.005,.001)
            for case in cases:
                name=backend+'-'+precision+'-'+case['name'];suffix='-f16' if precision=='f16' else ''
                expected=np.fromfile(FIXTURES/(case['name']+suffix+'-expected.f32'),dtype='<f4')
                actual,record=native(backend,FIXTURES/(case['model']+suffix+'.gguf'),FIXTURES/(case['name']+'.json'),name)
                check(actual.shape==expected.shape==(case['values'],),'Output shape mismatch: '+name)
                check(record['parameters']==case['parameters'] and record['layers']==case['layers'],'Architecture skipped layers: '+name)
                check(np.isfinite(actual).all(),'Non-finite output: '+name)
                delta=actual.astype(np.float64)-expected.astype(np.float64);peak=float(np.max(np.abs(delta)));rmse=float(np.sqrt(np.mean(delta*delta)))
                check(peak<=max_gate,'Peak parity failure: '+name+' '+str(peak))
                check(rmse<=rmse_gate,'RMSE parity failure: '+name+' '+str(rmse))
                metrics.append(dict(case=case['name'],backend=backend,precision=precision,max_abs=peak,rmse=rmse,max_abs_gate=max_gate,rmse_gate=rmse_gate))
                outputs[backend,precision,case['name']]=actual
            for layers in [2,3,28]:
                a=outputs[backend,precision,'layers'+str(layers)+'-masked'];b=outputs[backend,precision,'layers'+str(layers)+'-masked-padding']
                check(np.max(np.abs(a-b))<=1e-6,'Masked padding influenced output')
    base=json.loads((FIXTURES/'layers2-global.json').read_text(encoding='utf-8'));model=FIXTURES/'layers2.gguf';request=FIXTURES/'layers2-global.json'
    negatives=[('zero-tokens','tokens',0),('too-many-tokens','tokens',4097),('fractional-tokens','tokens',12.5),('zero-text','text_tokens',0),('too-much-text','text_tokens',257),('fractional-text','text_tokens',5.5),('latent-shape','latents',[0.]),('context-shape','context',[0.]),('coordinate-shape','coordinates',[0.]),('sigma-shape','timesteps',[.2,.3]),('negative-sigma','timesteps',[-.1]),('large-sigma','timesteps',[1.1]),('nonfinite-input','latents',[1e100]*len(base['latents'])),('no-text','text_mask',[0.]*5),('nonbinary-mask','text_mask',[1.,.5,1.,1.,1.]),('mask-shape','text_mask',[1.])]
    for name,key,value in negatives:
        bad=copy.deepcopy(base);bad[key]=value;path=OUT/(name+'.json');path.write_text(json.dumps(bad)+'\n',encoding='utf-8')
        native('cpu',model,path,'guard-'+name,False)
    for name,key,value in [('overflow-tokens','tokens',2**32+12),('overflow-text','text_tokens',2**32+5)]:
        bad=copy.deepcopy(base);bad[key]=value;path=OUT/(name+'.json');path.write_text(json.dumps(bad)+'\n',encoding='utf-8')
        native('cpu',model,path,'guard-'+name,False)
    for name in ['missing','extra','wrong-config']:native('cpu',FIXTURES/(name+'.gguf'),request,'guard-'+name,False)
    truncated=OUT/'truncated.gguf';truncated.write_bytes(model.read_bytes()[:-64]);native('cpu',truncated,request,'guard-truncated',False)
    native('cpu',model,request,'guard-no-fixture-opt-in',False,fixture=False)
    for count in ['0','33','-1','2junk','2.5']:native('cpu',model,request,'guard-threads'+count,False,threads=count)
    native('cpu',model,request,'guard-no-silent-fallback',False,selected='vulkan')
    native('cpu',model,request,'guard-unknown-backend',False,selected='cuda')
    original=outputs['cpu','f32','layers2-global']
    repeated,_=native('cpu',model,request,'repeat-load');check(np.array_equal(repeated,original),'Reload changed deterministic CPU output')
    previous=(result_dir/'repeat-load.f32').read_bytes();native('cpu',model,request,'repeat-load',False,preserve=True);check((result_dir/'repeat-load.f32').read_bytes()==previous,'Existing output overwritten')
    for name in ['research/ltx098/transformer.cpp','research/ltx098/driver.cpp']:
        text=(ROOT/name).read_text(encoding='utf-8')
        check(not any(token in text for token in ['http://','https://','curl_','socket(','system(']),'Research worker contains network/shell execution')
    current(inputs)
    record=dict(passed=checks,guard_assertions=guards,actual_host_children=children,actual_publisher_forward=True,oracle=oracle,backends=backends,vulkan_device_identity=sorted(devices),cases=len(cases),precision_metrics=metrics,native_runs=native_records,builds=builds,full_layer_depth=28,trained_weights_loaded=False,model_inference=False,complete_video_pipeline=False,video_outputs=False,engine_registered=False,packaged_in_apk=False,physical_android=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=checks,actual_host_children=children,guards=guards,backends=backends,parity_runs=len(metrics),trained_weights_loaded=False,complete_video_pipeline=False)))

if __name__=='__main__':main()
