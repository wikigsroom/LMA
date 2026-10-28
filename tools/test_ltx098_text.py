"""Test actual native T5 children against separately created HF encoder outputs."""
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from evidence import fingerprint,current
from fetch_ltx098_text import assets,sources,sha,DIRECTORY
from build_ltx098_text import inputs as build_inputs

ROOT=Path(__file__).resolve().parents[1]
ORACLE=ROOT/'build/ltx098-text-oracle'
OUT=ROOT/'build/ltx098-text-tests'
EXE=ROOT/'build/ltx098-text-host/bin/lma_ltx098_text_cli.exe'
TOKENIZER=DIRECTORY/'oracle/tokenizer_config.json'


def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False)+'\n',encoding='utf-8')


def execute(command,timeout=900,observe=False):
    """Measure this owned Windows child only; counters exclude GPU/device memory."""
    stop=threading.Event();resources=dict(observed=False,samples=0,interval_ms=20,observed_peak_working_set_bytes=0,sampled_peak_private_bytes=0,gpu_memory_measured=False)
    child=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def monitor():
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
    start=time.perf_counter()
    try:
        stdout,stderr=child.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command,child.returncode,stdout,stderr),time.perf_counter()-start,resources
    finally:
        if child.poll() is None:child.kill();child.communicate(timeout=10)
        stop.set()
        if thread:thread.join(timeout=2)


def run(trained=False):
    import numpy as np
    lock=sources();assets(oracle=True)
    record=fingerprint('research/ltx098_text','tools/build_ltx098_text.py','tools/fetch_ltx098_text.py','tools/ltx098_text_oracle.py','tools/test_ltx098_text.py','third_party/ltx098-text-source-lock.json')
    build=json.loads((ROOT/'build/ltx098-text-host/receipt.json').read_text(encoding='utf-8'));current(build['input_fingerprint']);assert build['input_fingerprint']==build_inputs()
    assert sha(EXE)==build['executable_sha256']
    oracle=json.loads((ORACLE/'manifest.json').read_text(encoding='utf-8'));current(oracle['input_fingerprint']);assert oracle['model_asset']==lock['model']
    for name,item in oracle['artifacts'].items():
        path=ORACLE/name
        assert path.parent==ORACLE and path.is_file() and path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'Changed independent oracle artifact: '+name
    OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    checks=0;children=0;guards=0;metrics=[];events=[]
    def check(ok,message):
        nonlocal checks
        checks+=1
        if not ok:raise AssertionError(message)
    def invoke(name,model,request,fixture=True,success=True,threads='4',preserve=None,observe=False,tokenizer=TOKENIZER,raw_request=None):
        nonlocal children,guards
        path=OUT/(name+'.json');write(path,request);output=OUT/(name+'.bin')
        if raw_request is not None:path.write_bytes(raw_request)
        output.unlink(missing_ok=True)
        if preserve is not None:output.write_bytes(preserve)
        command=[str(EXE),str(model),str(tokenizer),str(path),str(output),threads]+(['--fixture'] if fixture else [])
        completed,seconds,resources=execute(command,observe=observe);children+=1
        (OUT/(name+'.stderr')).write_bytes(completed.stderr)
        if success:
            check(completed.returncode==0,name+': '+completed.stderr.decode('utf-8',errors='replace')[-1800:])
            response=json.loads(completed.stdout);check(output.is_file() and output.stat().st_size==response['bytes'],name+': output length')
            check(not response['engine_registered'] and not response['complete_video'] and not response['physical_android'],name+': evidence scope')
            check(response['vocabulary_loads']==response['vocabulary_unloads']==1,name+': balanced vocabulary lifecycle')
            stages=[]
            for line in completed.stderr.splitlines():
                try:
                    item=json.loads(line)
                    if 'stage' in item:stages.append(item['stage'])
                except (ValueError,TypeError):pass
            events.extend(stages)
            check(stages.count('t5_load')==2,name+': actual load progress')
            return response,output,seconds,resources
        guards+=1;check(completed.returncode!=0,name+': must reject')
        check(output.read_bytes()==preserve if preserve is not None else not output.exists(),name+': preserve existing/no partial output')
        return None
    def compare(name,actual,expected,is_trained=False):
        check(actual.shape==expected.shape,name+': shape');check(np.isfinite(actual).all(),name+': finite output')
        delta=actual.astype(np.float64)-expected;rmse=float(np.sqrt(np.mean(delta*delta)));maximum=float(np.max(np.abs(delta)))
        denominator=float(np.sqrt(np.mean(expected.astype(np.float64)**2)));relative=rmse/max(denominator,1e-12)
        rows=actual.reshape(-1,actual.shape[-1]).astype(np.float64);truth=expected.reshape(-1,expected.shape[-1]).astype(np.float64)
        cosine=np.sum(rows*truth,axis=1)/np.maximum(np.linalg.norm(rows,axis=1)*np.linalg.norm(truth,axis=1),1e-12)
        metric=dict(name=name,max_abs=maximum,rmse=rmse,relative_rmse=relative,min_token_cosine=float(cosine.min()),trained=is_trained)
        metrics.append(metric);g=lock['numerical_gates'];prefix='trained' if is_trained else 'untrained'
        check(maximum<=g[prefix+'_max_abs'],name+': absolute maximum '+str(metric));check(rmse<=g[prefix+'_rmse'],name+': RMSE '+str(metric))
        if is_trained:
            check(relative<=g['trained_relative_rmse'],name+': relative RMSE');check(float(cosine.min())>=g['trained_min_token_cosine'],name+': cosine')
    fixture=ORACLE/'untrained-2.gguf'
    identity=oracle['vocabulary_identity'];check(identity['learned_tokens_compared']==identity['learned_scores_compared']==32000 and identity['sentinel_definitions_from_external_config']==100,'Complete original learned vocabulary identity')
    for i,case in enumerate(oracle['tokenization']):
        response,path,_,_=invoke(f'tokens-{i}',fixture,json.loads((ORACLE/case['request']).read_text(encoding='utf-8')))
        item=response['items'][0]
        check(item['tokens']==case['tokens'],f'tokens-{i}: exact independent Google SentencePiece IDs: {item["tokens"]} vs {case["tokens"]}')
        check(item['truncated']==case['truncated'],f'tokens-{i}: truncation');check(item['mask']==[1]*len(case['tokens']),f'tokens-{i}: valid mask')
        check(np.fromfile(path,dtype='<i4').tolist()==case['tokens'],f'tokens-{i}: binary IDs')
        check(not response['model_inference'] and response['model_loads']==0 and response['encode_calls']==0,f'tokens-{i}: vocabulary-only scope')
    for i,case in enumerate(oracle['untrained']):
        response,path,_,_=invoke(f'untrained-{i}',ORACLE/case['model'],json.loads((ORACLE/case['request']).read_text(encoding='utf-8')))
        check(response['encode_calls']==1 and response['model_loads']==response['model_unloads']==1,f'untrained-{i}: balanced lifecycle')
        check(response['items'][0]['tokens']==case['tokens'],f'untrained-{i}: supplied token preservation')
        compare(f'untrained-{i}',np.fromfile(path,dtype='<f4').reshape(case['shape']),np.fromfile(ORACLE/case['expected'],dtype='<f4').reshape(case['shape']))
    ids_a=[3,4,1];ids_b=[7,8,9,10,1]
    response,path,_,_=invoke('reuse',fixture,dict(operation='encode',inputs=[dict(tokens=ids_a),dict(tokens=ids_b),dict(tokens=ids_a)]))
    binary=path.read_bytes();a,c=response['items'][0],response['items'][2]
    check(binary[a['offset_bytes']:a['offset_bytes']+a['bytes']]==binary[c['offset_bytes']:c['offset_bytes']+c['bytes']],'A/B/A exact context isolation')
    check(response['encode_calls']==3 and response['model_loads']==response['model_unloads']==1,'Resident encoder lifecycle')
    for i,item in enumerate(oracle['padded_mask_checks']):check(item['max_abs']<1e-4,f'Original masked padding equivalence {i}')
    base=dict(operation='encode',inputs=[dict(tokens=[3,4,1])])
    invalid=[('operation',dict(operation='decode',inputs=base['inputs'])),('unknown-key',dict(base,attention_mask=[1,1,1])),
        ('empty-inputs',dict(base,inputs=[])),('many-inputs',dict(base,inputs=base['inputs']*5)),('input-keys',dict(base,inputs=[dict(tokens=[1],prompt='x')])),
        ('empty-tokens',dict(base,inputs=[dict(tokens=[])])),('negative-id',dict(base,inputs=[dict(tokens=[-1])])),('high-id',dict(base,inputs=[dict(tokens=[32128])])),
        ('float-id',dict(base,inputs=[dict(tokens=[1.5])])),('boolean-id',dict(base,inputs=[dict(tokens=[True])])),
        ('long-tokens',dict(base,inputs=[dict(tokens=[3]*257)])),('tokens-over-selection',dict(base,max_tokens=2)),('zero-limit',dict(base,max_tokens=0)),
        ('high-limit',dict(base,max_tokens=257)),('float-limit',dict(base,max_tokens=3.5)),('long-prompt',dict(base,inputs=[dict(prompt='a'*65537)])),
        ('empty-cancel',dict(base,cancel_file='')),('object-cancel',dict(base,cancel_file={})),('unknown-input',dict(base,inputs=[dict(embedding=[1])]))]
    for name,request in invalid:invoke('guard-'+name,fixture,request,success=False)
    for value in ['0','33','4x','-1','2147483648']:invoke('guard-thread-'+value,fixture,base,success=False,threads=value)
    for name,raw in [('duplicate-root',b'{"operation":"encode","operation":"tokenize","inputs":[{"tokens":[1]}]}'),('duplicate-input',b'{"operation":"encode","inputs":[{"tokens":[1],"tokens":[2]}]}'),('invalid-utf8',b'{"operation":"tokenize","inputs":[{"prompt":"\xff"}]}'),('oversized-json',b' '*300001)]:
        invoke('guard-'+name,fixture,base,success=False,raw_request=raw)
    invoke('guard-missing-tokenizer',fixture,base,success=False,tokenizer=OUT/'absent-tokenizer.json')
    config=json.loads(TOKENIZER.read_text(encoding='utf-8'))
    for name,change in [('missing-sentinels',dict(additional_special_tokens=[])),('wrong-sentinel',dict(additional_special_tokens=['wrong']*100)),('float-extras',dict(extra_ids=100.5)),('wrong-eos',dict(eos_token='wrong'))]:
        path=OUT/('config-'+name+'.json');write(path,dict(config,**change));invoke('guard-'+name,fixture,base,success=False,tokenizer=path)
    invoke('guard-missing-model',OUT/'absent.gguf',base,success=False)
    invoke('guard-preserve-output',fixture,base,success=False,preserve=b'existing-user-output')
    invoke('guard-fixture-in-production',fixture,base,fixture=False,success=False)
    wrong=OUT/'wrong.gguf';wrong.write_bytes(b'not-a-model')
    invoke('guard-wrong-model',wrong,base,success=False)
    cancel=OUT/'pre-cancel';cancel.write_text('stop',encoding='utf-8')
    invoke('guard-pre-cancel',fixture,dict(base,cancel_file=str(cancel)),success=False)
    cancel.unlink()
    trained_results=None
    if trained:
        case=oracle['trained'];check(bool(case),'Missing full trained independent reference')
        model=DIRECTORY/'originals'/lock['model']['file'];request=json.loads((ORACLE/case['request']).read_text(encoding='utf-8'))
        response,path,seconds,resources=invoke('trained',model,request,fixture=False,observe=True)
        check(response['width']==4096 and response['layers']==24 and response['encode_calls']==4,'Complete trained T5 architecture')
        check(response['model_loads']==response['model_unloads']==1,'Complete trained T5 balanced lifecycle')
        check(response['weight_execution']=='streamed_f32_matrix_casts' and response['encoder_implementation']=='independent_ggml_f32_compute','No extra Q8 activation quantization')
        check(response['buffers']['mapped_file_bytes']==lock['model']['bytes'],'Mapped model identity size')
        check(0<response['buffers']['peak_compute_bytes']<1024*1024*1024,'Bounded temporary casts; no complete F32 checkpoint allocation')
        raw=path.read_bytes()
        for i,index in enumerate(case['native_item_order']):
            expected=case['examples'][index];item=response['items'][i]
            check(item['tokens']==expected['tokens'],f'trained-{i}: exact prompt token IDs')
            values=np.frombuffer(raw[item['offset_bytes']:item['offset_bytes']+item['bytes']],dtype='<f4').reshape(expected['shape'])
            compare(f'trained-{i}',values,np.fromfile(ORACLE/expected['expected'],dtype='<f4').reshape(expected['shape']),True)
        a,c=response['items'][0],response['items'][-1]
        check(raw[a['offset_bytes']:a['offset_bytes']+a['bytes']]==raw[c['offset_bytes']:c['offset_bytes']+c['bytes']],'Trained A/B/A exact isolation')
        # Cancel only this owned child after it enters the real encoder, rather
        # than replacing its neural graph with a fixture/simulated callback.
        signal=OUT/'inference.cancel';signal.unlink(missing_ok=True);output=OUT/'cancel-trained.bin';output.unlink(missing_ok=True)
        cancel_request=OUT/'cancel-trained.json';write(cancel_request,dict(operation='encode',inputs=[dict(tokens=list(range(3,258))+[1])],cancel_file=str(signal)))
        child=subprocess.Popen([str(EXE),str(model),str(TOKENIZER),str(cancel_request),str(output),'4'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        signalled=threading.Event();lines=[]
        def reader():
            for line in iter(child.stderr.readline,b''):
                lines.append(line)
                if b'"stage":"t5_compute"' in line:
                    time.sleep(.03);signal.write_text('stop',encoding='utf-8');signalled.set()
        observer=threading.Thread(target=reader,daemon=True);observer.start()
        try:
            child.wait(timeout=900);stdout=child.stdout.read();observer.join(timeout=3);children+=1;guards+=1
            stderr=b''.join(lines);(OUT/'cancel-trained.stderr').write_bytes(stderr)
            check(signalled.is_set(),'Cancellation reached actual neural entry');check(child.returncode!=0 and b'cancelled during neural evaluation' in stderr,'Real T5 encoder aborted in-flight')
            check(not output.exists() and not stdout.strip(),'Cancellation left no final artifact')
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=10)
            observer.join(timeout=2);signal.unlink(missing_ok=True)
        trained_results=dict(model=lock['model'],evaluated_tensors=case['evaluated_tensors'],tensor_parameters=case['tensor_parameters'],
            native_inputs=4,distinct_prompts=3,native_seconds_including_load=seconds,host_process_memory=resources,native_buffers=response['buffers'],actual_neural_cancellation=True,
            original_unquantized_weights_compared=False,prompt_quality_tested=False,video_quality_tested=False)
    result=dict(schema='lma.ltx098-text-tests/1',checks=checks,actual_native_children=children,negative_guards=guards,tokenization_cases=len(oracle['tokenization']),
        untrained_cases=len(oracle['untrained']),padding_comparisons=len(oracle['padded_mask_checks']),metrics=metrics,numerical_gates=lock['numerical_gates'],
        trained=trained_results,vocabulary_identity=identity,host_model_inference_tested=bool(trained_results),android_model_inference_tested=False,engine_registered=False,packaged_in_apk=False,
        complete_video_tested=False,physical_android=False,remote_inference=False,virtualization_used=False,observed_stage_counts={name:events.count(name) for name in sorted(set(events))},
        executable_sha256=sha(EXE),oracle_manifest_sha256=sha(ORACLE/'manifest.json'),oracle_artifact_files=len(oracle['artifacts']),oracle=oracle,input_fingerprint=record)
    current(record);write(OUT/'results.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['input_fingerprint','metrics','trained','numerical_gates']}),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trained',action='store_true');run(parser.parse_args().trained)
