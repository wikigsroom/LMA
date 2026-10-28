"""Execute the complete production SoulX worker offline with explicitly prepared weights.

Fresh synthetic references/transcripts are contract probes, NOT speech quality
or a voice demo. Outputs remain ignored developer files. No downloads occur.
"""
import hashlib,json,os,queue,shutil,subprocess,threading,time,wave
from pathlib import Path
import numpy as np
from evidence import fingerprint,current
from build_soulx import source_inputs
from soulx_recipe import FILES,schema
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/soulx-worker-trained-tests'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('native/soulx','research/soulx','research/soulx_ort','research/soulx_reference','research/soulx_acoustic','research/soulx_language','native/moss_nano/onnx_external.hpp','tools/test_soulx_worker_trained.py','tools/build_soulx.py','tools/soulx_recipe.py','third_party/soulx-reference-source-lock.json','third_party/soulx-acoustic-source-lock.json','third_party/soulx-trained-assets.json','third_party/soulx-language-source-lock.json')
    host=ROOT/'build/soulx-worker-host';receipt=json.loads((host/'receipt.json').read_text(encoding='utf-8'));current(receipt['source_inputs'])
    if receipt['source_inputs']!=source_inputs():raise RuntimeError('Rebuild the current complete worker')
    binary=host/'bin/lma_soulx_worker.exe'
    if sha(binary)!=receipt['sha256']:raise RuntimeError('Changed worker executable')
    for name in ['soulx-reference-tests','soulx-trained-tests','soulx-language-tests']:
        proof=json.loads((ROOT/'build'/name/'results.json').read_text(encoding='utf-8'));current(proof['input_fingerprint'])
    assets={};passed=0;children=0;runs=[];outputs=[]
    for folder,manifest in [('build/soulx-reference-tests/pack','soulx-reference.json'),('build/soulx-trained-tests/pack','soulx-acoustic.json'),('build/soulx-language-official','soulx-language.json')]:
        directory=ROOT/folder;record=json.loads((directory/manifest).read_text(encoding='utf-8'))
        for item in record['assets']:
            path=directory/item['file'];identity=sha(path)
            if identity!=item['sha256'] or path.stat().st_size!=item['bytes']:raise RuntimeError('Changed selected model asset: '+item['file'])
            role='language' if item['file'].endswith('.gguf') else item['role']
            assets[role]=(path,dict(role=role,file=FILES[role],bytes=item['bytes'],sha256=identity));passed+=1
    assert set(assets)==set(FILES);passed+=1
    def workspace(name,count):
        root=OUT/name
        if root.exists():
            if root.resolve().parent!=OUT.resolve():raise RuntimeError('Unsafe own trained workspace cleanup')
            shutil.rmtree(root)
        (root/'models').mkdir(parents=True);(root/'inputs').mkdir()
        for role,(source,item) in assets.items():os.link(source,root/'models'/FILES[role])
        transcripts={};refs=[]
        for i in range(count):
            n=25237+i*5011;t=np.arange(n)/24000;rng=np.random.default_rng(82541+i)
            pcm=.025*rng.standard_normal(n)+.06*np.sin(2*np.pi*((118+17*i)*t+29*t*t));path=root/'inputs'/('reference_s'+str(i+1)+'.wav')
            with wave.open(str(path),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000);f.writeframes(np.rint(np.clip(pcm,-1,1)*32767).astype('<i2').tobytes())
            role='reference_s'+str(i+1);refs.append(dict(role=role,artifactId='synthetic_'+str(i+1)));transcripts[role]='Synthetic reference for a local contract check.'
        return root,dict(prompt='[S1] Testing the complete local worker.\n[S2] 你好，这是完整本地音频测试。' if count>1 else 'Testing complete local speech.',artifacts=refs,transcripts=transcripts)
    def run(name,count,changes=None,prompt=None,cancel_stage=None):
        nonlocal children,passed
        root,input=workspace(name,count);p={k:v['default'] for k,v in schema()['fields'].items()};p.update(context=2048,historyThreshold=2048,threads=2,maxNewTokens=160,seed=9183,steps=15,pauseMs=120,temperature=.6,useRas=True);p.update(changes or {})
        if prompt is not None:input['prompt']=prompt
        output=root/'output.wav';request=dict(schema='lma.engine-request/1',type='speech.synthesize',pipeline='soulx_podcast_cpu_v1',input=input,parameters=p,workspace=str(root),output=str(output));file=root/'request.json';file.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
        start=time.monotonic();process=subprocess.Popen([str(binary),str(file)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=host/'bin');children+=1;events=[];lines=queue.Queue();terminated=False
        def reader():
            try:
                for line in process.stdout:lines.put(line)
            finally:lines.put(None)
        thread=threading.Thread(target=reader,daemon=True);thread.start();deadline=start+1200
        try:
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise RuntimeError('Trained production worker timed out')
                try:line=lines.get(timeout=min(1,remaining))
                except queue.Empty:continue
                if line is None:break
                event=json.loads(line.decode('utf-8'));events.append(event)
                if cancel_stage and event.get('stage')==cancel_stage and not terminated:
                    process.terminate();terminated=True
            code=process.wait(timeout=15);stderr=process.stderr.read();thread.join(timeout=5)
            assert not thread.is_alive() and not stderr;passed+=2
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=15)
            process.stdout.close();process.stderr.close();thread.join(timeout=5)
        (root/'events.json').write_text(json.dumps(events,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if cancel_stage:
            assert terminated and code!=0 and not output.exists() and not any(e.get('event')=='complete' for e in events);passed+=4
            runs.append(dict(name=name,forced_host_termination=True,observed_stage=cancel_stage,android_cooperative_cancellation_tested=False,seconds=time.monotonic()-start));return
        assert code==0 and events[-1]==dict(event='complete',output=str(output));passed+=2
        details=next(e['details'] for e in reversed(events) if e.get('event')=='execution');assert details['backend']=='cpu' and details['stageLoading']=='sequential';passed+=2
        assert details['referenceGraphRuns']==2*count and details['languageModelLoads']==details['languageModelUnloads']==1 and details['languageDecodeCalls']>0;passed+=3
        assert details['ortModelLoads']==details['ortModelUnloads']==2*count+4*len(details['turns']) and details['maxConcurrentOrtModels']==1;passed+=2
        assert details['acousticGraphRuns']==(p['steps']+3)*len(details['turns']);passed+=1
        for turn in details['turns']:
            assert 1<=turn['semanticCodes']<=p['maxNewTokens'] and turn['samples']==turn['semanticCodes']*960 and turn['modelLoads']==turn['modelUnloads']==4;passed+=3
            assert 1<=turn['speaker']<=count and turn['historyDelimiterInserted']==(not turn['eos']);passed+=2
        with wave.open(str(output),'rb') as f:
            assert f.getnchannels()==1 and f.getsampwidth()==2 and f.getframerate()==24000 and f.getnframes()==details['outputSamples'];passed+=4;pcm=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2')
        assert np.std(pcm.astype('f8'))>1 and len(pcm)==960*details['generatedSemanticCodes']+24*p['pauseMs']*(len(details['turns'])-1);passed+=2
        assert not (root/'audio.part.wav').exists();passed+=1
        outputs.append(dict(name=name,bytes=output.stat().st_size,sha256=sha(output),samples=len(pcm),seconds=len(pcm)/24000,turns=details['turns'],peak_before_pcm=details['peakBeforePcm']))
        runs.append(dict(name=name,execution=details,wall_seconds=time.monotonic()-start));print(json.dumps(dict(completed=name,turns=len(details['turns']),samples=len(pcm))),flush=True)
    run('paired-fresh-text',2)
    run('four-speakers-explicit-cap',4,dict(maxNewTokens=8,minNewTokens=0,temperature=0,useRas=False,steps=3,pauseMs=0),prompt='[S1] One.\n[S2] Two.\n[S3] Three.\n[S4] Four.')
    run('terminate-language',1,cancel_stage='language_decode')
    run('terminate-acoustic',1,dict(maxNewTokens=8,minNewTokens=0,temperature=0,useRas=False),cancel_stage='flow_estimator')
    current(inputs);current(receipt['source_inputs'])
    report=dict(passed=passed,actual_host_children=children,full_trained_production_worker_executed=True,production_soulx_binding=True,reference_speakers_tested=[2,4],trained_model_components=14,assets=[value[1] for value in assets.values()],fresh_synthetic_reference_pcm=True,real_person_audio_used=False,speech_quality_tested=False,physical_android=False,complete_target13_accepted=False,remote_inference=False,model_assets_packaged_in_apk=False,native_binary_sha256=sha(binary),actual_forced_host_terminations=2,android_cooperative_cancellation_tested=False,runs=runs,outputs=outputs,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['input_fingerprint','assets','runs','outputs']}))

if __name__=='__main__':main()
