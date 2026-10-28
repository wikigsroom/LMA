"""Execute old-LTX publisher/native sampling and local asset conversion checks.

Full trained evidence requires --trained and already downloaded pinned assets.
This tool never downloads, registers an App engine or produces video.
"""
import argparse,copy,json,os,struct,subprocess,time
from pathlib import Path
import numpy as np
from build_ltx098 import ROOT,validate_sources
from evidence import current,fingerprint
from export_ltx098 import convert
from ltx098_assets import Checkpoint,sha
from test_ltx098 import binary

OUT=ROOT/'build/ltx098-sampling-tests'


def write(path,value):path.write_text(json.dumps(value)+'\n',encoding='utf-8')


def verified_oracle(directory):
    record=json.loads((directory/'oracle.json').read_text(encoding='utf-8'));current(record['input_fingerprint'])
    artifacts=record['artifacts']
    if not artifacts or set(artifacts)!={p.name for p in directory.iterdir() if p.is_file() and p.name!='oracle.json'}:raise ValueError('Missing/unreviewed publisher reference artifacts')
    for name,item in artifacts.items():
        path=directory/name
        if path.resolve().parent!=directory.resolve() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('Publisher reference artifact changed: '+name)
    return record


def execute(command,timeout,observe):
    """Capture owned-child output; optionally sample Windows process memory.

    Working-set/private counters cover host process memory, never GPU VRAM.
    Sampling may miss the final interval, so it is not a phone/total-memory claim.
    """
    import threading
    stop=threading.Event();resources=dict(observed=False,samples=0,observed_peak_working_set_bytes=0,sampled_peak_private_bytes=0,interval_ms=20,gpu_memory_measured=False)
    child=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def monitor():
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD];psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        handle=kernel.OpenProcess(0x410,False,child.pid)
        if not handle:return
        try:
            while not stop.is_set():
                counter=Counters();counter.cb=ctypes.sizeof(counter)
                if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(counter),counter.cb):break
                resources['observed']=True;resources['samples']+=1
                resources['observed_peak_working_set_bytes']=max(resources['observed_peak_working_set_bytes'],counter.PeakWorkingSetSize)
                resources['sampled_peak_private_bytes']=max(resources['sampled_peak_private_bytes'],counter.PrivateUsage)
                stop.wait(.02)
        finally:kernel.CloseHandle(handle)
    thread=threading.Thread(target=monitor,daemon=True) if observe and os.name=='nt' else None
    if thread:thread.start()
    try:
        stdout,stderr=child.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command,child.returncode,stdout,stderr),resources
    finally:
        if child.poll() is None:child.kill();child.communicate(timeout=10)
        stop.set()
        if thread:thread.join(timeout=2)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trained',action='store_true');parser.add_argument('--skip-build',action='store_true');args=parser.parse_args()
    validate_sources();OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    os.environ['TEMP']=os.environ['TMP']=str(ROOT/'build/tmp')
    inputs=fingerprint('research/ltx098','tools/build_ltx098.py','tools/fetch_ltx098.py','tools/fetch_ltx098_trained.py','tools/export_ltx098.py','tools/ltx098_assets.py','tools/ltx098_fixture.py','tools/ltx098_sampling_oracle.py','tools/test_ltx098.py','tools/test_ltx098_sampling.py','third_party/ltx098-source-lock.json','third_party/ltx098-trained-assets.json')
    oracle_dir=ROOT/'build/ltx098-sampling-oracle';oracle=verified_oracle(oracle_dir)
    executables={};probes={};builds={}
    for backend in ['cpu','vulkan']:
        probes[backend],builds[backend]=binary(backend,args.skip_build)
        executables[backend]=probes[backend].with_name('lma_ltx098_sample.exe')
        if sha(executables[backend])!=builds[backend]['sampler_binary_sha256']:raise ValueError('Sampler binary differs from build receipt')
    # Fresh run folders preserve prior evidence and avoid overwriting trace/artifact paths.
    run_dir=OUT/('run-'+str(time.time_ns()));run_dir.mkdir()
    checks=0;children=0;guards=0;records=[];metrics=[];devices=set()
    def check(value,message):
        nonlocal checks
        if not value:raise AssertionError(message)
        checks+=1
    def process(backend,model,data,name,ok=True,fixture=True,preserve=False,probe=False):
        nonlocal children,guards
        request=run_dir/(name+'.json');write(request,data);output=run_dir/(name+'.f32')
        command=[str(probes[backend] if probe else executables[backend]),str(model),str(request),str(output),backend,'4']+(['--fixture'] if fixture else [])
        start=time.monotonic();result,resources=execute(command,900,observe=not fixture);children+=1
        (run_dir/(name+'.log')).write_bytes(result.stdout+result.stderr)
        record=json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1])
        check(result.returncode==(0 if ok else 2),'Unexpected native exit: '+name)
        check(record['ok']==ok,'Unexpected native success: '+name)
        check(record['complete_video_pipeline'] is False,'False complete-video claim')
        if not probe:check(record['engine_registered'] is False,'False App registration claim')
        if not ok:
            check(bool(record['error']),'Missing local failure explanation');guards+=1
            if not preserve:check(not output.exists(),'Failure produced a final artifact')
            return None,record
        check(output.is_file(),'Missing native output')
        array=np.fromfile(output,dtype='<f4');check(np.isfinite(array).all(),'Non-finite native output')
        identity=[line.strip() for line in result.stderr.decode('utf-8',errors='replace').splitlines() if 'ggml_vulkan: 0 =' in line]
        if backend=='vulkan':
            check(len(identity)==1 and 'fp16: 0' in identity[0] and 'matrix cores: none' in identity[0],'GPU baseline precision/device identity missing')
            devices.update(identity)
        if not fixture:check(resources['observed'] and resources['samples']>0 and resources['observed_peak_working_set_bytes']>0,'Missing trained host process memory samples')
        records.append(dict(name=name,backend=backend,seconds=time.monotonic()-start,output_bytes=output.stat().st_size,output_sha256=sha(output),host_process_memory=resources,record=record))
        return array,record
    def parity(actual,path,name,max_gate,rmse_gate):
        expected=np.fromfile(path,dtype='<f4');check(actual.shape==expected.shape,'Reference shape mismatch: '+name)
        difference=actual.astype(np.float64)-expected;maximum=float(np.max(np.abs(difference)));rmse=float(np.sqrt(np.mean(difference*difference)))
        metrics.append(dict(name=name,max_abs=maximum,rmse=rmse,max_gate=max_gate,rmse_gate=rmse_gate))
        check(maximum<=max_gate and rmse<=rmse_gate,'Numerical parity outside frozen gates: '+str(metrics[-1]))
    for case in oracle['math_cases']:
        data=json.loads((oracle_dir/(case['name']+'.json')).read_text(encoding='utf-8'));actual,record=process('cpu','-',data,case['name'])
        parity(actual,oracle_dir/(case['name']+'.f32'),case['name'],2e-6,5e-7)
        check(record['model_executed'] is False,'Math operation claimed neural inference')
        if case['operation']=='geometry':
            check(record['tokens']==case['tokens'],'Geometry token count differs')
            check(np.array_equal(np.array(record['sigmas'],dtype=np.float32),np.array(case['sigmas'],dtype=np.float32)),'Distilled schedule differs from publisher')
    source=oracle_dir/'fixture.safetensors';source_hash=sha(source);converted_dir=run_dir/'converted';converted=convert(source,converted_dir,fixture=True)
    current(converted['input_fingerprint']);check(converted['source_sha256']==source_hash,'Converted source hash mismatch')
    check(converted['synthetic_parameters'] is True and not converted['packaged_in_apk'],'Fixture conversion evidence mislabeled')
    for case in oracle['neural_cases']:
        name=case['name']+'-'+case['precision'];model=converted_dir/'ltx098-dit.gguf' if case['precision']=='converted' else oracle_dir/(name+'.gguf')
        for backend in ['cpu','vulkan']:
            label=backend+'-'+name;data=json.loads((oracle_dir/(case['name']+'.json')).read_text(encoding='utf-8'));trace=run_dir/(label+'-trace');data['trace_dir']=str(trace)
            actual,record=process(backend,model,data,label)
            check(record['model_executed'] is True and record['steps']==8,'Sampler did not execute eight neural steps')
            check(record['layers']==case['layers'],'Sampler changed layer depth')
            check(record['backend']==backend,'Sampler backend changed silently')
            check(len(record['compute_bytes'])==8 and all(x>0 for x in record['compute_bytes']),'Missing per-step graph allocations')
            gates=(2e-3,5e-4) if backend=='cpu' and case['precision']!='f32' else (2e-5,4e-6)
            prefix='converted' if case['precision']=='converted' else name
            for step in range(8):parity(np.fromfile(trace/('step-'+str(step)+'.f32'),dtype='<f4'),oracle_dir/(prefix+'-step-'+str(step)+'.f32'),label+'-step-'+str(step),*gates)
            check(np.array_equal(actual,np.fromfile(trace/'step-7.f32',dtype='<f4')),'Final latent differs from last step')
    # Exercise malformed geometry and explicit unsupported settings through real children.
    good=json.loads((oracle_dir/'geometry-1.json').read_text(encoding='utf-8'))
    for key,value in [('width',63),('height',0),('frames',16),('frames',265),('fps',0),('fps',241),('width',True),('fps','24')]:
        data=dict(good);data[key]=value;process('cpu','-',data,'guard-'+key+'-'+str(value),False)
    data=dict(good,width=2048,height=2048,frames=257);process('cpu','-',data,'guard-token-budget',False)
    for key,value in [('steps',16),('guidance',4),('sampler','euler'),('remote_url','http://unused.invalid')]:
        data=dict(good);data[key]=value;process('cpu','-',data,'guard-unhandled-'+key,False)
    rf=json.loads((oracle_dir/'rf-global-0.json').read_text(encoding='utf-8'))
    for key,value in [('times',[0]),('times',[1.01]),('times',[-1]),('times',[.7,.5]),('velocity',[]),('channels',0),('per_token',1)]:
        data=copy.deepcopy(rf);data[key]=value;process('cpu','-',data,'guard-rf-'+key+'-'+str(value).replace('/','_'),False)
    output,_=process('cpu','-',good,'preserved');previous=(run_dir/'preserved.f32').read_bytes();process('cpu','-',good,'preserved',False,preserve=True)
    check((run_dir/'preserved.f32').read_bytes()==previous,'Existing output overwritten')
    sample=json.loads((oracle_dir/'layers2.json').read_text(encoding='utf-8'));model=oracle_dir/'layers2-f32.gguf'
    cancel=run_dir/'cancel-before';cancel.touch();data=dict(sample,cancel_file=str(cancel));process('cpu',run_dir/'absent.gguf',data,'guard-cancel-before',False)
    # Cancel after an actual step starts. Only this owned child is terminated on timeout.
    cancel=run_dir/'cancel-live';request=run_dir/'cancel-live.json';output=run_dir/'cancel-live.f32';write(request,dict(sample,cancel_file=str(cancel)))
    command=[str(executables['cpu']),str(model),str(request),str(output),'cpu','4','--fixture']
    child=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE);children+=1;stderr=[];started=False
    import queue,threading
    lines=queue.Queue()
    def read_errors():
        for line in child.stderr:lines.put(line)
        lines.put(None)
    reader=threading.Thread(target=read_errors,daemon=True);reader.start();deadline=time.monotonic()+30
    try:
        while time.monotonic()<deadline:
            try:line=lines.get(timeout=.2)
            except queue.Empty:
                if child.poll() is not None:break
                continue
            if line is None:break
            stderr.append(line)
            if b'"event":"step_start"' in line:
                cancel.touch();started=True;break
        stdout=child.stdout.read() if child.poll() is not None else b''
        child.wait(timeout=30)
        if not stdout:stdout=child.stdout.read()
        reader.join(timeout=2)
        while not lines.empty():
            line=lines.get_nowait()
            if line:stderr.append(line)
        (run_dir/'cancel-live.log').write_bytes(stdout+b''.join(stderr));record=json.loads(stdout.decode('utf-8').strip().splitlines()[-1])
        check(started,'Cancellation never reached an actual neural step')
        check(child.returncode==2 and not record['ok'] and 'cancel' in record['error'].lower(),'Actual step cancellation failed')
        check(not output.exists(),'Cancelled sampler published a final artifact');guards+=1
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=10)
        child.stdout.close();child.stderr.close()
    # Safetensors rejection must not damage caller input or publish partial packs.
    raw=source.read_bytes();size=struct.unpack('<Q',raw[:8])[0];header=json.loads(raw[8:8+size]);payload=raw[8+size:]
    def malformed(name,value,body=payload):
        blob=value if isinstance(value,bytes) else json.dumps(value,separators=(',',':')).encode()
        path=run_dir/(name+'.safetensors');path.write_bytes(struct.pack('<Q',len(blob))+blob+body);return path
    first=next(k for k in header if k!='__metadata__')
    bads=[malformed('truncated',header,payload[:-1]),malformed('trailing',header,payload+b'x'),malformed('duplicate',b'{"x":1,"x":2}')]
    for key,value in [('dtype','I8'),('shape',[1]),('data_offsets',[1,2])]:
        data=copy.deepcopy(header);data[first][key]=value;bads.append(malformed('bad-'+key,data))
    data=copy.deepcopy(header);config=json.loads(data['__metadata__']['config']);config['transformer']['positional_embedding_theta']=9999.;data['__metadata__']['config']=json.dumps(config);bads.append(malformed('newer-config',data))
    # A finite BF16 value can still overflow the target F16 dense storage.
    dense=next(k for k,v in header.items() if k!='__metadata__' and len(v['shape'])==2 and k.endswith('.weight'))
    changed=bytearray(payload);offset=header[dense]['data_offsets'][0];changed[offset:offset+2]=struct.pack('<H',0x7f00);bads.append(malformed('half-overflow',header,changed))
    changed[offset:offset+2]=struct.pack('<H',0x7fc0);bads.append(malformed('nonfinite',header,changed))
    for path in bads:
        before=sha(path);target=run_dir/(path.stem+'-conversion')
        try:convert(path,target,fixture=True)
        except (ValueError,KeyError,TypeError):guards+=1
        else:raise AssertionError('Malformed checkpoint accepted: '+path.name)
        check(sha(path)==before,'Conversion changed input assets')
        check(not target.exists(),'Failed conversion left a published pack')
        check(not list(run_dir.glob('.ltx098-convert-*')),'Failed conversion left staging data')
    try:convert(source,converted_dir,fixture=True)
    except ValueError:guards+=1
    else:raise AssertionError('Converter overwrote an existing pack')
    check(sha(source)==source_hash and sha(converted_dir/'ltx098-dit.gguf')==converted['sha256'],'Existing assets changed')
    trained_record=None
    if args.trained:
        trained_dir=ROOT/'build/ltx098-trained';reference=trained_dir/'oracle';trained_oracle=verified_oracle(reference)
        conversion=json.loads((trained_dir/'converted/conversion.json').read_text(encoding='utf-8'));current(conversion['input_fingerprint']);model=trained_dir/'converted/ltx098-dit.gguf'
        check(sha(model)==conversion['sha256'],'Trained GGUF changed after conversion')
        check(trained_oracle['source_sha256']==conversion['source_sha256'],'Trained oracle and native weights differ')
        check(trained_oracle['trained_weights_loaded'] and not trained_oracle['synthetic_parameters'],'Trained reference is a fixture')
        data=json.loads((reference/'trained-forward.json').read_text(encoding='utf-8'));actual,forward=process('vulkan',model,data,'trained-forward',fixture=False,probe=True)
        parity(actual,reference/'trained-velocity.f32','trained-forward',2e-3,5e-4)
        data=json.loads((reference/'trained.json').read_text(encoding='utf-8'));trace=run_dir/'trained-trace';data['trace_dir']=str(trace)
        actual,sampling=process('vulkan',model,data,'trained-sample',fixture=False)
        for step in range(8):parity(np.fromfile(trace/('step-'+str(step)+'.f32'),dtype='<f4'),reference/('trained-step-'+str(step)+'.f32'),'trained-step-'+str(step),1e-2,2e-3)
        check(sampling['parameters']==1923385472 and sampling['layers']==28 and sampling['steps']==8,'Incomplete trained DiT sampling')
        check(np.array_equal(actual,np.fromfile(trace/'step-7.f32',dtype='<f4')),'Trained final latent differs')
        trained_record=dict(oracle=trained_oracle,conversion=conversion,forward=forward,sampling=sampling,trained_weights_loaded=True,synthetic_text_embeddings=True,t5_executed=False,vae_executed=False,video_outputs=False,backend='vulkan')
    current(inputs)
    record=dict(passed=checks,guard_assertions=guards,actual_host_children=children,actual_publisher_forward=True,oracle=oracle,math_cases=len(oracle['math_cases']),neural_trajectories=len(oracle['neural_cases'])*2,neural_steps=len(oracle['neural_cases'])*16,precision_metrics=metrics,native_runs=records,builds=builds,vulkan_device_identity=sorted(devices),conversion_fixture=converted,trained=trained_record,trained_weights_loaded=trained_record is not None,model_inference=False,complete_video_pipeline=False,video_outputs=False,t5_executed=False,vae_executed=False,engine_registered=False,packaged_in_apk=False,physical_android=False,input_fingerprint=inputs)
    write(OUT/'results.json',record)
    print(json.dumps(dict(passed=checks,guard_assertions=guards,actual_host_children=children,math_cases=len(oracle['math_cases']),neural_trajectories=len(oracle['neural_cases'])*2,trained_weights_loaded=trained_record is not None,complete_video_pipeline=False)))


if __name__=='__main__':main()
