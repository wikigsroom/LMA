"""Fresh-text complete trained SoulX host pipeline with synthetic references.

Actual native reference -> Qwen3 -> Flow/HiFT children, all offline. This is
not App integration, phone acceptance, real-person cloning or speech-quality
validation. Models must already be explicitly selected/prepared.
"""
import hashlib,json,subprocess,sys,wave
from pathlib import Path
import numpy as np
from evidence import fingerprint,current
from fetch_soulx_reference import sha
from soulx_native_checks import compile_host
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/soulx-pipeline-tests'

def main():
    OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    evidence={name:json.loads((ROOT/'build'/name/'results.json').read_text(encoding='utf-8')) for name in ['soulx-reference-tests','soulx-trained-tests','soulx-language-tests']}
    for record in evidence.values():current(record['input_fingerprint'])
    inputs=fingerprint('research/soulx','research/soulx_ort','research/soulx_reference','research/soulx_acoustic','research/soulx_language','tools/test_soulx_pipeline.py','tools/soulx_native_checks.py','third_party/soulx-reference-source-lock.json','third_party/soulx-acoustic-source-lock.json','third_party/soulx-trained-assets.json','third_party/soulx-language-source-lock.json')
    model=ROOT/'build/soulx-language-official';manifest=json.loads((model/'soulx-language.json').read_text(encoding='utf-8'));language=model/manifest['assets'][0]['file'];assert sha(language)==manifest['assets'][0]['sha256']
    passed=1;children=0;runs=[];artifacts=[]
    # Compile the actual current reference/acoustic source for this check;
    # never trust a previously cached developer executable by filename.
    binaries={}
    for role,source,lock_name,test_name in [('reference','soulx_reference','soulx-reference-source-lock.json','soulx-reference-tests'),('acoustic','soulx_acoustic','soulx-acoustic-source-lock.json','soulx-trained-tests')]:
        lock=json.loads((ROOT/'third_party'/lock_name).read_text(encoding='utf-8'));directory=ROOT/'build'/('soulx-pipeline-'+role);directory.mkdir(exist_ok=True)
        binaries[role]=compile_host(lock,directory,source)
        for asset in evidence[test_name]['assets']:
            file=ROOT/'build'/test_name/'pack'/asset['file'];assert file.stat().st_size==asset['bytes'] and sha(file)==asset['sha256'];passed+=1
    binaries['language']=ROOT/'build/soulx-language-host/bin/lma_soulx_language_cli.exe'
    assert sha(binaries['language'])==evidence['soulx-language-tests']['native_binary_sha256'];passed+=1
    def execute(kind,command,timeout=900):
        nonlocal passed,children
        result=subprocess.run([str(x) for x in command],cwd=ROOT,capture_output=True,timeout=timeout);children+=1
        (OUT/(kind+'.log')).write_bytes(result.stderr)
        if not result.stdout.strip():raise RuntimeError('Missing pipeline child receipt: '+kind)
        record=json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1]);assert result.returncode==0 and record['ok'],(kind,record);passed+=2
        runs.append(dict(stage=kind,**{k:v for k,v in record.items() if k not in ['turns','logits','trace_shapes']}));return record
    references=[]
    for i,count in enumerate([27611,36139]):
        directory=OUT/('reference-input-'+str(i));directory.mkdir(exist_ok=True);rng=np.random.default_rng(70431+i);t=np.arange(count)/24000
        pcm=(.03*rng.standard_normal(count)+.05*np.sin(2*np.pi*(132*t+31*t*t))).astype('<f4');pcm.tofile(directory/'pcm.f32');(directory/'input.json').write_text(json.dumps(dict(format='lma.soulx-reference-input/1',threads=2)),encoding='utf-8')
        output=OUT/('reference-output-'+str(i))
        if output.exists():
            import shutil
            if output.resolve().parent!=OUT.resolve():raise RuntimeError('Unsafe own pipeline output cleanup')
            shutil.rmtree(output)
        record=execute('reference-'+str(i),[binaries['reference'],ROOT/'build/soulx-reference-tests/pack',directory,output]);assert record['graph_runs']==2 and record['session_loads']==record['session_unloads']==2 and record['max_live_sessions']==1;passed+=3
        codes=np.fromfile(output/'tokens.i64',dtype='<i8');assert len(codes)==record['tokens'] and np.all((codes>=0)&(codes<6561));passed+=2
        references.append(dict(directory=output,codes=codes.astype('i4').tolist()))
    request=dict(format='lma.soulx-language-input/1',mode='generate',context=2048,threads=4,batch=128,seed=9183,
        references=[dict(text='A synthetic reference for an offline check.',codes=r['codes']) for r in references],
        turns=[dict(text='Testing local speech.',speaker=0),dict(text='你好，这是本地测试。',speaker=1)],
        sampling=dict(temperature=.6,repetition_penalty=1.25,top_k=100,top_p=.9,min_tokens=8,max_tokens=160,use_ras=True))
    input=OUT/'language-input.json';input.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8');output=OUT/'language-output.json';output.unlink(missing_ok=True)
    generated=execute('language',[binaries['language'],language,input,output]);assert generated['model_loads']==generated['model_unloads']==1 and generated['decode_calls']>0 and len(generated['turns'])==2;passed+=3
    waves=[]
    for i,turn in enumerate(generated['turns']):
        reference=references[turn['speaker']];directory=OUT/('acoustic-input-'+str(i));directory.mkdir(exist_ok=True)
        tokens=np.array(reference['codes']+turn['codes'],dtype='<i8');tokens.tofile(directory/'tokens.i64')
        import shutil
        for name in ['speaker.f32','prompt-mel.f32']:shutil.copyfile(reference['directory']/name,directory/name)
        (directory/'input.json').write_text(json.dumps(dict(format='lma.soulx-acoustic-input/1',prompt_tokens=len(reference['codes']),steps=15,threads=2,seed=1031+i,cfg=.7,trace=False,inject_noise=False)),encoding='utf-8')
        output=OUT/('turn-'+str(i)+'.f32');output.unlink(missing_ok=True)
        receipt=execute('acoustic-'+str(i),[binaries['acoustic'],ROOT/'build/soulx-trained-tests/pack',directory,output]);assert receipt['graph_runs']==18 and receipt['session_loads']==receipt['session_unloads']==4 and receipt['max_live_sessions']==1;passed+=3
        pcm=np.fromfile(output,dtype='<f4');assert len(pcm)==len(turn['codes'])*960 and len(pcm)>0 and np.isfinite(pcm).all() and np.std(pcm)>1e-5 and np.max(np.abs(pcm))<=.990001;passed+=5
        path=OUT/('turn-'+str(i)+'.wav')
        with wave.open(str(path),'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(np.rint(np.clip(pcm,-1,1)*32767).astype('<i2').tobytes())
        with wave.open(str(path),'rb') as wav:assert wav.getnchannels()==1 and wav.getframerate()==24000 and wav.getnframes()==len(pcm);passed+=3
        waves.append(pcm);artifacts.append(dict(file=path.name,bytes=path.stat().st_size,sha256=sha(path),samples=len(pcm),seconds=len(pcm)/24000,speaker=turn['speaker'],semantic_codes=len(turn['codes']),eos=turn['eos'],history_delimiter_inserted=turn['history_delimiter_inserted'],peak=float(np.max(np.abs(pcm))),rms=float(np.sqrt(np.mean(pcm.astype('f8')**2)))))
    current(inputs)
    for record in evidence.values():current(record['input_fingerprint'])
    report=dict(passed=passed,actual_host_children=children,actual_reference_graph_runs=4,actual_acoustic_graph_runs=36,actual_neural_decode_calls=generated['decode_calls'],
        trained_reference_models=2,trained_language_backbones=1,trained_acoustic_checkpoints=2,full_trained_host_pipeline_executed=True,fresh_texts=[t['text'] for t in request['turns']],
        synthetic_reference_pcm=True,real_person_audio_used=False,same_host_sequential_children=True,no_network_inference=True,
        source_evidence_fingerprints={k:v['input_fingerprint'] for k,v in evidence.items()},native_binary_sha256={k:sha(v) for k,v in binaries.items()},converted_language_assets=manifest['assets'],artifacts=artifacts,runs=runs,
        speech_quality_tested=False,complete_target_13_accepted=False,physical_android=False,apk_runtime_used=False,engine_registered=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k not in ['source_evidence_fingerprints','input_fingerprint','runs']}),flush=True)

if __name__=='__main__':main()
