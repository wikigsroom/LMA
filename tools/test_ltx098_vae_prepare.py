"""Native old-VAE preparation, byte identity and actual decoding of prepared assets."""
import copy
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time
import numpy as np
from evidence import fingerprint, current
from build_ltx098_vae_prepare import inputs as build_inputs
from ltx098_assets import Checkpoint, sha
from test_ltx098_text import execute

ROOT=Path(__file__).resolve().parents[1]
EXE=ROOT/'build/ltx098-vae-prepare-host/bin/lma_ltx098_vae_prepare.exe'
DECODER=ROOT/'build/ltx098-vae-host/bin/lma_ltx098_vae_cli.exe'
SOURCE=ROOT/'build/ltx098-trained/originals/ltxv-2b-0.9.8-distilled.safetensors'
GRAPHS=ROOT/'research/ltx098_vae_prepare/graphs'
OUT=ROOT/'build/ltx098-vae-prepare-tests'


def inputs():
    return {**build_inputs(),**fingerprint('tools/test_ltx098_vae_prepare.py','tools/test_ltx098_text.py',
            'tools/ltx098_assets.py','tools/ltx098_vae.py','tools/build_ltx098_vae.py',
            'research/ltx098_vae','research/soulx_ort','third_party/ltx098-vae-source-lock.json')}


def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False)+'\n',encoding='utf-8')


def sparse_checkpoint(path,header,header_bytes,length):
    """Metadata-only negative fixture; not a downloaded/trained model."""
    import msvcrt
    from ctypes import wintypes
    raw=json.dumps(header,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    if len(raw)>header_bytes:raise RuntimeError('Negative fixture header exceeds original envelope')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.DeviceIoControl.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,
                                    ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD),ctypes.c_void_p]
    kernel.DeviceIoControl.restype=wintypes.BOOL
    kernel.SetFilePointerEx.argtypes=[wintypes.HANDLE,ctypes.c_longlong,ctypes.c_void_p,wintypes.DWORD]
    kernel.SetFilePointerEx.restype=wintypes.BOOL
    kernel.SetEndOfFile.argtypes=[wintypes.HANDLE];kernel.SetEndOfFile.restype=wintypes.BOOL
    with path.open('w+b') as stream:
        returned=wintypes.DWORD()
        if not kernel.DeviceIoControl(msvcrt.get_osfhandle(stream.fileno()),0x000900C4,None,0,None,0,ctypes.byref(returned),None):
            raise RuntimeError('Workspace volume does not support sparse metadata test files')
        stream.write(struct.pack('<Q',header_bytes));stream.write(raw.ljust(header_bytes,b' '));stream.flush()
        # CRT _chsize_s fills an extension with zeros, even for sparse handles.
        # SetEndOfFile preserves an unwritten sparse extent on native Windows.
        handle=msvcrt.get_osfhandle(stream.fileno())
        if not kernel.SetFilePointerEx(handle,length,None,0) or not kernel.SetEndOfFile(handle):raise RuntimeError('Cannot extend sparse metadata fixture')
        os.fsync(stream.fileno())


def run():
    if os.name!='nt':raise RuntimeError('Use native Windows test tools')
    before=inputs();OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    directory=OUT/('run-'+str(time.time_ns()));directory.mkdir()
    lock=json.loads((ROOT/'third_party/ltx098-vae-source-lock.json').read_text(encoding='utf-8'))
    contract=json.loads((ROOT/'research/ltx098_vae_prepare/contract.json').read_text(encoding='utf-8'))
    audit=json.loads((ROOT/'build/ltx098-vae-template-tests/results.json').read_text(encoding='utf-8'))
    current(audit['input_fingerprint']);current(audit['output_fingerprint'])
    assert audit['passed'] and not audit['inline_learned_data']
    builds={}
    for platform in ['host','arm64']:
        build=json.loads((ROOT/f'build/ltx098-vae-prepare-{platform}/receipt.json').read_text(encoding='utf-8'))
        current(build['input_fingerprint']);assert build['input_fingerprint']==build_inputs()
        binary=EXE if platform=='host' else ROOT/'build/ltx098-vae-prepare-arm64/bin/liblma-ltx098-vae-prepare.so'
        assert sha(binary)==build['executable_sha256'];builds[platform]=build
    decoder_build=json.loads((ROOT/'build/ltx098-vae-host/receipt.json').read_text(encoding='utf-8'))
    current(decoder_build['input_fingerprint']);assert sha(DECODER)==decoder_build['executable_sha256']
    checkpoint=Checkpoint(SOURCE)
    base=dict(operation='convert_vae',checkpoint=str(SOURCE),expected_source_bytes=lock['checkpoint']['bytes'],
              expected_source_sha256=lock['checkpoint']['sha256'],graph_root=str(GRAPHS),storage_root=str(directory),output_name='prepared')
    checks=[];jobs=[];guards=[];decode_jobs=[];metrics=[]
    def check(ok,name):
        checks.append(dict(name=name,passed=bool(ok)))
        if not ok:raise RuntimeError('Failed: '+name)
    def clean_stage(name):check(not any(p.name.startswith('.ltx098-prepare-') for p in directory.iterdir()),name+': staging cleaned')
    def invoke(name,request,success=True,raw=None,observe=False):
        if not success and request.get('output_name')=='prepared':request=dict(request,output_name='guard-'+name)
        path=directory/(name+'.request.json')
        if raw is None:write(path,request)
        else:path.write_text(raw,encoding='utf-8')
        result,seconds,resources=execute([str(EXE),str(path)],timeout=1800,observe=observe)
        (directory/(name+'.stdout.json')).write_bytes(result.stdout);(directory/(name+'.progress.jsonl')).write_bytes(result.stderr)
        value=json.loads(result.stdout)
        check(value['ok'] is success and result.returncode==(0 if success else 1),name+': result and exit status')
        if not success:guards.append(name);clean_stage(name)
        jobs.append(dict(name=name,success=success,native=value,seconds=seconds,resources=resources))
        return value
    inspection={k:v for k,v in base.items() if k not in ['graph_root','storage_root','output_name']};inspection['operation']='inspect_vae'
    inspected=invoke('inspect',inspection)
    check(not inspected['source_sha256_verified'] and 'assets' not in inspected,'inspection makes no payload verification claim')
    check(inspected['learned_source_tensors']==134 and inspected['external_initializers']==138,'complete learned routing preflight')
    check(inspected['asset_bytes']==2211661835 and inspected['parameter_bytes']==2211259604,'exact asset and parameter storage plan')
    for name,change in [('unknown-operation',dict(operation='download')),('unknown-field',dict(remote=True)),
                        ('wrong-bytes',dict(expected_source_bytes=1)),('wrong-sha',dict(expected_source_sha256='0'*64)),
                        ('bad-sha',dict(expected_source_sha256='invalid')),('budget',dict(max_output_bytes=1)),
                        ('remote-checkpoint',dict(checkpoint='https://example.invalid/model')),
                        ('relative-checkpoint',dict(checkpoint='model.safetensors')),
                        ('missing-storage',dict(storage_root=str(directory/'absent'))),
                        ('missing-graphs',dict(graph_root=str(directory/'absent'))),
                        ('inspect-output',dict(operation='inspect_vae')),
                        ('unsafe-name',dict(output_name='../outside')),('reserved-name',dict(output_name='CON'))]:
        invoke(name,dict(base,**change),False)
    invoke('duplicate-key',base,False,raw=json.dumps(base)[:-1]+',"operation":"convert_vae"}')
    invoke('request-budget',base,False,raw=' '*32769)
    existing=directory/'existing';existing.mkdir();(existing/'user').write_bytes(b'user-owned')
    invoke('preserve-existing',dict(base,output_name='existing'),False)
    check((existing/'user').read_bytes()==b'user-owned','existing user directory untouched')
    flag=directory/'pre-cancel';flag.touch();invoke('pre-cancel',dict(base,cancel_file=str(flag)),False)
    with SOURCE.open('rb') as stream:
        header_bytes=struct.unpack('<Q',stream.read(8))[0];header=json.loads(stream.read(header_bytes))
    def changed_config(h):
        cfg=json.loads(h['__metadata__']['config']);cfg['vae']['causal_decoder']=True;h['__metadata__']['config']=json.dumps(cfg,separators=(',',':'),ensure_ascii=False)
    def changed_shape(h):
        key='vae.decoder.conv_in.conv.weight';shape=h[key]['shape'];shape[0]//=2;shape[1]*=2
    def renamed(h,key,new):h[new]=h.pop(key)
    for name,change in [('different-config',changed_config),('different-shape',changed_shape),
                        ('missing-multiplier',lambda h:renamed(h,'vae.decoder.timestep_scale_multiplier','vae.unused.multiplier')),
                        ('missing-statistics',lambda h:renamed(h,'vae.per_channel_statistics.std-of-means','vae.unused.statistics')),
                        ('statistics-shape',lambda h:h['vae.per_channel_statistics.mean-of-means'].update(shape=[2,64])),
                        ('unknown-decoder',lambda h:renamed(h,'vae.decoder.conv_out.conv.bias','vae.decoder.unreviewed'))]:
        modified=copy.deepcopy(header);change(modified);path=directory/(name+'.negative-sparse.safetensors')
        sparse_checkpoint(path,modified,header_bytes,checkpoint.length)
        try:invoke(name,dict(base,checkpoint=str(path)),False)
        finally:
            assert path.resolve().parent==directory.resolve();path.unlink()
    tampered=directory/'tampered-graphs';tampered.mkdir()
    for item in contract['graphs']:shutil.copyfile(GRAPHS/item['file'],tampered/item['file'])
    file=tampered/'stage-00.onnx'
    with file.open('r+b') as stream:stream.seek(-1,2);old=stream.read(1);stream.seek(-1,2);stream.write(bytes([old[0]^1]))
    invoke('graph-sha',dict(base,graph_root=str(tampered)),False)
    # Cancellation after all graph files and nine data handles have been created.
    flag=directory/'mid.cancel';request=dict(base,output_name='mid-cancel',cancel_file=str(flag));path=directory/'mid-cancel.request.json';write(path,request)
    child=subprocess.Popen([str(EXE),str(path)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE);start=time.perf_counter()
    try:
        first=child.stderr.readline();check(json.loads(first)['phase']=='convert','mid-cancel: actual conversion entered');flag.touch()
        stdout,stderr=child.communicate(timeout=60);value=json.loads(stdout)
        (directory/'mid-cancel.stdout.json').write_bytes(stdout);(directory/'mid-cancel.progress.jsonl').write_bytes(first+stderr)
        check(child.returncode==1 and not value['ok'] and value['error']=='Cancelled','mid-cancel: stopped by cancellation')
        check(not (directory/'mid-cancel').exists(),'mid-cancel: no final partial assets');clean_stage('mid-cancel');guards.append('mid-cancel')
        jobs.append(dict(name='mid-cancel',success=False,native=value,seconds=time.perf_counter()-start,resources=dict(observed=False)))
    finally:
        if child.poll() is None:child.kill();child.communicate(timeout=10)
    native=invoke('trained-convert',base,observe=True);converted=directory/'prepared'
    check(native['source_sha256_verified'] and native['source_sha256']==lock['checkpoint']['sha256'],'all source bytes match old checkpoint SHA')
    check(native['source_streamed_bytes']==checkpoint.length==6340744492,'complete source streamed')
    check(native['asset_written_bytes']==native['asset_bytes']==2211661835,'all 18 assets written')
    check(native['parameter_written_bytes']==native['parameter_bytes']==2211259604,'all external parameters written including shared multiplier')
    check(native['graph_sha256_verified'] and native['parameter_sha256_verified'] and native['source_retained'],'complete conversion verification and source retention')
    memory=jobs[-1]['resources'];check(memory['observed'] and memory['samples']>0 and memory['observed_peak_working_set_bytes']<128*1024*1024,'bounded observed converter working set')
    original=json.loads((ROOT/'build/ltx098-vae-assets/ltx098-vae.json').read_text(encoding='utf-8'));current(original['input_fingerprint'])
    files={a['file']:a for a in native['assets']}
    for item in original['assets']:
        target=converted/item['file'];reference=ROOT/'build/ltx098-vae-assets'/item['file']
        check(target.stat().st_size==item['bytes']==files[item['file']]['bytes'],item['file']+': exact byte count')
        check(sha(target)==sha(reference)==item['sha256']==files[item['file']]['sha256'],item['file']+': independently re-read whole-file SHA identity')
    manifest=json.loads((converted/'ltx098-vae.json').read_text(encoding='utf-8'))
    check(manifest==contract['manifest'],'production-compatible manifest contains only intended metadata')
    check(json.loads((converted/'preparation.json').read_text(encoding='utf-8'))==native,'persisted receipt matches native result')
    clean_stage('complete conversion')
    reference_dir=ROOT/'build/ltx098-vae-tests/references';oracle=json.loads((reference_dir/'references.json').read_text(encoding='utf-8'))
    current(oracle['input_fingerprint'])
    for name,item in oracle['files'].items():
        path=reference_dir/name;check(path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],'original reference identity: '+name)
    gates=lock['gates']
    for case in oracle['cases']:
        name=case['name'];trace=directory/(name+'-trace');target=directory/(name+'.f32');path=directory/(name+'.decode.json')
        request=dict(operation='decode',latent_shape=case['latent_shape'],latents=str(reference_dir/case['files']['latent']),
                     noise=str(reference_dir/case['files']['noise']),timestep=case['timestep'],noise_scale=case['noise_scale'],threads=4,trace_dir=str(trace))
        write(path,request);result,seconds,resource=execute([str(DECODER),str(converted),str(path),str(target)],timeout=900,observe=True)
        (directory/(name+'.decode.log')).write_bytes(result.stdout+result.stderr);response=json.loads(result.stdout.strip().splitlines()[-1])
        check(result.returncode==0 and response['ok'],name+': actual decoder completed')
        check(response['session_loads']==response['session_unloads']==response['graph_runs']==9 and response['max_live_sessions']==1,name+': sequential session lifecycle')
        check(response['output_shape']==case['output_shape'],name+': output geometry')
        check(resource['observed'] and resource['samples']>0,name+': actual decoder memory observed')
        decode_jobs.append(dict(name=name,seconds=seconds,native=response,resources=resource))
        for i in range(10):
            actual=trace/f'stage-{i:02d}.onnx.f32' if i<9 else target
            ref=reference_dir/case['files'][f'stage-{i:02d}' if i<8 else 'output']
            a=np.fromfile(actual,dtype='<f4').astype(np.float64);b=np.fromfile(ref,dtype='<f4').astype(np.float64)
            check(a.shape==b.shape and a.size>0 and np.isfinite(a).all() and np.isfinite(b).all(),name+f'-{i}: finite matching shape')
            delta=a-b;absolute=float(np.max(np.abs(delta)));rmse=float(np.sqrt(np.mean(delta*delta)));relative=rmse/max(float(np.sqrt(np.mean(b*b))),1e-12)
            denom=float(np.linalg.norm(a)*np.linalg.norm(b));cosine=float(np.dot(a,b)/denom) if denom else float(np.array_equal(a,b))
            check(absolute<=gates['max_absolute_error'] and relative<=gates['max_relative_rmse'] and cosine>=gates['min_cosine'],name+f'-{i}: original-forward gates')
            metrics.append(dict(case=name,stage=i,max_absolute_error=absolute,relative_rmse=relative,cosine=cosine,elements=a.size))
    current(before)
    record=dict(schema='lma.ltx098-native-vae-prepare-tests/1',passed=True,checks=len(checks),guards=guards,
                preparation_children=len(jobs),actual_trained_conversions=1,trained_conversion=native,conversion_resources=memory,
                actual_trained_decode_jobs=len(decode_jobs),actual_native_children=len(jobs)+len(decode_jobs),
                jobs=jobs,decode_jobs=decode_jobs,metrics=metrics,gates=gates,original_reference_files=len(oracle['files']),
                original_reference=oracle,builds=builds,decoder_build=decoder_build,template_audit=audit,
                all_18_assets_byte_identical_to_python=True,host_model_inference_tested=True,model_data_embedded=False,
                engine_registered=False,packaged_in_apk=False,physical_android=False,complete_video_pipeline=False,release_ready=False,
                virtualization_used=False,artifacts_directory=directory.relative_to(ROOT).as_posix(),input_fingerprint=before)
    write(directory/'checks.json',checks);write(directory/'results.json',record);write(OUT/'results.json',record)
    print(json.dumps({k:record[k] for k in ['passed','checks','preparation_children','actual_native_children','actual_trained_conversions','actual_trained_decode_jobs','artifacts_directory']}),flush=True)
    return record


if __name__=='__main__':run()
