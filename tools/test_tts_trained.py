"""Execute all three frozen trained speech recipes with the production worker."""
import ctypes
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid

from build_tts_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_tts_trained import verify, path_for, inputs as asset_inputs
from fetch_sd15_trained import sha
from test_moss_nano_trained import audio_stats

ROOT = Path(__file__).resolve().parents[1]
PROMPT_A = 'Hello world. The sun is shining.'
PROMPT_B = 'This is a new voice. Let us take a walk in the park.'


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_tts_trained.py', 'tools/test_moss_nano_trained.py')}


def execute(command, cancel=False):
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [(key, ctypes.c_size_t) for key in
            ['PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
             'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage']]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True); psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]; kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]; psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    start = time.perf_counter(); child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    handle = kernel.OpenProcess(0x410, False, child.pid); messages = queue.Queue(); captured = [bytearray(), bytearray()]
    errors = []; truncated = [False, False]; events = []; trigger = None; cancelled_at = None; timed_out = False
    resources = dict(observed=False, samples=0, interval_ms=20, observed_peak_working_set_bytes=0,
        sampled_peak_private_bytes=0, gpu_memory_measured=False, physical_device_memory_measured=False)
    def read(stream, index):
        try:
            for line in iter(stream.readline, b''):
                if len(captured[index])+len(line) <= 2*1024*1024: captured[index].extend(line)
                else: truncated[index] = True
                if index == 0:
                    try:
                        value = json.loads(line)
                        if not isinstance(value, dict): raise ValueError('Non-object')
                        messages.put(value)
                    except (ValueError, UnicodeError): errors.append('Non-protocol stdout')
        finally: stream.close()
    readers = [threading.Thread(target=read,args=(stream,index),daemon=True) for index,stream in enumerate([child.stdout,child.stderr])]
    for reader in readers: reader.start()
    try:
        while True:
            while not messages.empty():
                value = messages.get_nowait(); events.append(value)
                if (cancel and trigger is None and value.get('event') == 'progress' and value.get('stage') == 'synthesizing'
                    and 0 < value.get('fraction', 0) < 1 and child.poll() is None):
                    trigger = value; cancelled_at = time.perf_counter(); child.kill()
            if handle:
                counter = Counters(); counter.cb = ctypes.sizeof(counter)
                if psapi.GetProcessMemoryInfo(handle,ctypes.byref(counter),counter.cb):
                    resources['observed'] = True; resources['samples'] += 1
                    resources['observed_peak_working_set_bytes'] = max(resources['observed_peak_working_set_bytes'],counter.PeakWorkingSetSize)
                    resources['sampled_peak_private_bytes'] = max(resources['sampled_peak_private_bytes'],counter.PrivateUsage)
            if child.poll() is not None: break
            if time.perf_counter()-start > 600: timed_out = True; child.kill(); child.wait(timeout=10); break
            time.sleep(.02)
        child.wait(timeout=10)
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=10)
        for reader in readers: reader.join(timeout=10)
        if handle: kernel.CloseHandle(handle)
    while not messages.empty(): events.append(messages.get_nowait())
    if any(reader.is_alive() for reader in readers): raise RuntimeError('Owned log reader did not exit')
    return dict(returncode=child.returncode,seconds=time.perf_counter()-start,events=events,protocol_errors=errors,
        logs_truncated=truncated,timed_out=timed_out,forced_host_termination=trigger is not None,cancel_trigger=trigger,
        cancel_to_exit_seconds=None if cancelled_at is None else time.perf_counter()-cancelled_at,resources=resources),[bytes(x) for x in captured]


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows host only')
    before = inputs(); assets = verify(); binary, compilation = build()
    acquisition_path = ROOT / 'build/tts-trained/receipt.json'; acquisition = json.loads(acquisition_path.read_text(encoding='utf-8')); current(acquisition['input_fingerprint'])
    folder = ROOT / 'build/tts-trained-tests' / ('run-'+str(time.time_ns())+'-'+uuid.uuid4().hex[:8]); folder.mkdir(parents=True)
    drive = next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive: raise RuntimeError('No unused owned test alias')
    subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
    jobs=[]; controls=[]; failures=[]; info=None
    try:
        def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
        info, logs = execute([alias(binary),'--info'])
        for suffix,data in zip(['stdout','stderr'],logs):(folder/('info.'+suffix)).write_bytes(data)
        expected = dict(schema='lma.engine/1',engine='sherpa_tts',revision=compilation['source_revision'],sherpa='2.0.1',onnxruntime='1.28.2',backend='cpu',bundled_model_data=False,generation_tested=False)
        if info['returncode'] or info['events'] != [expected] or info['protocol_errors']: raise ValueError('Different actual C API/ORT identity')
        def request(bundle,name,prompt=PROMPT_A,changes=None):
            parameters=dict(threads=4,speaker=0,speed=1,silenceScale=1,maxAudioSeconds=180)
            if bundle['pipeline'] in ['piper_vits','matcha']:parameters['noiseScale']=.667
            if bundle['pipeline']=='piper_vits':parameters['noiseScaleW']=.8
            if changes:parameters.update(changes)
            return dict(schema='lma.engine-request/1',type='speech.synthesize',pipeline=bundle['pipeline'],input=dict(prompt=prompt),
                parameters=parameters,components={c['role']:alias(path_for(c)) for c in bundle['components']},output=alias(folder/(name+'.wav')))
        def invoke(bundle,name,value,cancel=False,error=None):
            path=folder/(name+'.json');path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            result,logs=execute([alias(binary),alias(path)],cancel=cancel)
            for suffix,data in zip(['stdout','stderr'],logs):(folder/(name+'.'+suffix)).write_bytes(data)
            result.update(name=name,bundle_id=bundle['id'],pipeline=bundle['pipeline'],parameters=value['parameters'],prompt=value['input']['prompt'],request_sha256=sha(path))
            output=folder/(name+'.wav');result['output_exists']=output.is_file()
            complete=[e for e in result['events'] if e.get('event')=='complete']; errors=[e for e in result['events'] if e.get('event')=='error']
            execution={}
            for event in result['events']:
                if event.get('event')=='execution':execution.update(event['details'])
            result['execution']=execution
            common=not result['protocol_errors'] and not any(result['logs_truncated']) and not result['timed_out']
            if cancel:
                result['passed']=common and result['forced_host_termination'] and result['returncode']!=0 and not complete and not result['output_exists']
                controls.append(result)
            elif error:
                result['expected_error']=error
                result['passed']=common and result['returncode']==1 and not complete and not result['output_exists'] and len(errors)==1 and errors[0]['message']==error
                controls.append(result)
            else:
                result['passed']=common and result['returncode']==0 and not errors and len(complete)==1 and complete[0]['output']==value['output'] and output.is_file()
                if output.is_file():
                    audio=audio_stats(output);result['audio']=audio
                    effective=dict(value['parameters'],speaker=min(value['parameters']['speaker'],bundle['declared_speakers']-1))
                    result['passed']=result['passed'] and audio['format']=='WAV' and audio['channels']==1 and audio['sample_width']==2 and 0<audio['seconds']<=value['parameters']['maxAudioSeconds'] and audio['rms']>1e-5 and audio['nonzero_samples']>10
                    result['passed']=result['passed'] and execution.get('speakerCount')==bundle['declared_speakers'] and execution.get('effectiveParameters')==effective and execution.get('sampleRate')==audio['sample_rate']
                    result['passed']=result['passed'] and execution.get('audio',{}).get('samples')==audio['samples'] and execution.get('audio',{}).get('sampleRate')==audio['sample_rate']
                jobs.append(result)
            (folder/(name+'-capture.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({k:result.get(k) for k in ['name','passed','returncode','seconds','audio','execution']},ensure_ascii=False),flush=True)
            if not result['passed']:failures.append(name);raise RuntimeError('Retain failed actual trained case: '+name)
            return result
        base=assets['bundles'][0]
        for name,mutate,error in [
            ('bad-schema',lambda r:r.update(schema='unknown'),'Unsupported TTS task'),
            ('empty-prompt',lambda r:r['input'].update(prompt=''),'Invalid speech text or output'),
            ('bad-threads',lambda r:r['parameters'].update(threads=17),'TTS parameter exceeds application bounds'),
            ('bad-speed',lambda r:r['parameters'].update(speed=4),'TTS parameter exceeds application bounds'),
            ('bad-speaker',lambda r:r['parameters'].update(speaker=65536),'TTS parameter exceeds application bounds'),
            ('missing-lexicon',lambda r:r['components'].pop('lexicon'),'A required TTS component is missing'),
            ('bad-pipeline',lambda r:r.update(pipeline='unknown'),'Unsupported TTS pipeline')]:
            value=request(base,name);mutate(value);invoke(base,name,value,error=error)
        for bundle in assets['bundles']:
            pipeline=bundle['pipeline'];first=invoke(bundle,pipeline+'-a',request(bundle,pipeline+'-a'))
            invoke(bundle,pipeline+'-b',request(bundle,pipeline+'-b',PROMPT_B))
            faster=invoke(bundle,pipeline+'-speed',request(bundle,pipeline+'-speed',changes=dict(speed=1.5)))
            if not faster['audio']['seconds']<first['audio']['seconds']:failures.append(pipeline+' speed did not shorten actual audio');raise RuntimeError(failures[-1])
            invoke(bundle,pipeline+'-speaker-clamp',request(bundle,pipeline+'-speaker-clamp',changes=dict(speaker=65535)))
            invoke(bundle,pipeline+'-duration-limit',request(bundle,pipeline+'-duration-limit',changes=dict(maxAudioSeconds=1)),error='Audio exceeded the selected duration limit; no partial output was accepted')
            invoke(bundle,pipeline+'-cancel',request(bundle,pipeline+'-cancel',(PROMPT_A+' ')*12),cancel=True)
            invoke(bundle,pipeline+'-recovery-a',request(bundle,pipeline+'-recovery-a'))
            if pipeline=='kokoro':
                for speaker in range(1,bundle['declared_speakers']):
                    name=f'kokoro-voice-{speaker:02d}';invoke(bundle,name,request(bundle,name,changes=dict(speaker=speaker)))
    except Exception as error:
        if not failures:failures.append(type(error).__name__+': '+str(error))
    finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before)
    by_name={j['name']:j for j in jobs}
    coverage={b['pipeline']:sorted({j['execution']['effectiveParameters']['speaker'] for j in jobs if j['pipeline']==b['pipeline'] and j['passed']}) for b in assets['bundles']}
    repeated={p:by_name[p+'-a']['audio']['sha256']==by_name[p+'-recovery-a']['audio']['sha256'] for p in ['kokoro','piper_vits','matcha'] if p+'-recovery-a' in by_name}
    files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
    report=dict(schema='lma.tts-trained-host/1',compilation=compilation,acquisition=acquisition,acquisition_receipt_sha256=sha(acquisition_path),
        info=info,jobs=jobs,controls=controls,voice_coverage=coverage,repeat_a_bitwise_identical=repeated,seed_control_available=False,
        files=files,capture_directory=folder.relative_to(ROOT).as_posix(),failures=failures,host_execution_checks_passed=not failures,
        trained_production_worker_executed=bool(jobs),production_worker_source_unmodified=True,backend='cpu',fixture=False,asset_download_attempted=False,
        physical_android=False,app_executed=False,android_log_interposition_tested=False,host_oov_guard_accepted=False,speech_quality_accepted=False,
        device_resource_fit_accepted=False,android_background_accepted=False,complete_target10_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    for path in [folder/'results.json',folder.parent/'results.json']:path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(jobs=len(jobs),controls=len(controls),voice_coverage=coverage,failures=failures),ensure_ascii=False),flush=True)
    if failures:raise SystemExit(1)


if __name__=='__main__':main()
