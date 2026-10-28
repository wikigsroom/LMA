"""Independent SoulX protocol/RAS/window, actual trained GGUF and cancellation checks.

Uses explicitly prepared complete language weights and current native trained
reference outputs. No App/phone/voice-quality claim; no implicit downloads.
"""
import copy,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
from evidence import fingerprint,current
from fetch_soulx_language import verify,sha,ASSETS
from soulx_language_oracle import original_normalize,ras_case,original_history
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/soulx-language-tests'

def main():
    lock=verify();verify(True);OUT.mkdir(exist_ok=True);(OUT/'results.json').unlink(missing_ok=True)
    inputs=fingerprint('research/soulx_language','tools/build_soulx_language.py','tools/fetch_soulx_language.py','tools/export_soulx_language.py','tools/test_soulx_language.py','tools/soulx_language_oracle.py','tools/soulx_language_logits.py','third_party/soulx-language-source-lock.json')
    compiled=json.loads((ROOT/'build/soulx-language-host/receipt.json').read_text(encoding='utf-8'));current(compiled['input_fingerprint'])
    host=ROOT/'build/soulx-language-host/bin';exe=host/'lma_soulx_language_cli.exe';policy=host/'lma_soulx_policy.exe'
    assert sha(exe)==compiled['executable_sha256'] and sha(policy)==compiled['policy_sha256']
    pack=ROOT/'build/soulx-language-official';manifest=json.loads((pack/'soulx-language.json').read_text(encoding='utf-8'));asset=manifest['assets'][0];model=pack/asset['file'];assert model.stat().st_size==asset['bytes'] and sha(model)==asset['sha256']
    assert manifest['official_source_hashes_verified'] and manifest['full_tensors']==311 and manifest['full_layers']==28
    children=0;passed=5;runs=[];metrics=[]
    def run(name,request,success=True,selected=model,policy_only=False,timeout=600):
        nonlocal children,passed
        input=OUT/(name+'.json');output=OUT/(name+'-output.json');output.unlink(missing_ok=True);input.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
        command=[str(policy),str(input)] if policy_only else [str(exe),str(selected),str(input),str(output)]
        p=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=timeout);children+=1;(OUT/(name+'.log')).write_bytes(p.stderr)
        if not p.stdout.strip():raise RuntimeError('Missing native result: '+name)
        result=json.loads(p.stdout.decode('utf-8').strip().splitlines()[-1]);assert result['ok']==success and (p.returncode==0)==success,(name,result);passed+=2
        if not policy_only:
            assert result['model_loads']==result['model_unloads'];passed+=1
            if not success:assert not output.exists();passed+=1
            runs.append(dict(name=name,**{k:v for k,v in result.items() if k not in ['texts','formatted','turns','logits']}))
        return result
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(str(ASSETS/'tokenizer.json'));encode=lambda text:tokenizer.encode(text,add_special_tokens=False).ids;normalize=original_normalize()
    texts=['','hello','你好','你 好 世 界','English 中文 text','你\u3000好\u00a0世 界','中 文 Hello 世 界','hello  world','hello\nworld','42','😀 Hello','[laughter] Hello!','<|semantic_token_end|>','<|0|>','<|6560|>']
    rng=np.random.default_rng(418);alphabet=['你','好','A','b',' ','\t','\u2003','。','1','😀']
    texts.extend(''.join(rng.choice(alphabet,size=int(rng.integers(1,40)))) for _ in range(100))
    turns=[dict(text='你 好 English',speaker=i,first_reference=i==0) for i in range(4)]
    normalized=run('text-policy',dict(mode='text',texts=texts,turns=turns),policy_only=True)
    assert normalized['texts']==[normalize(x) for x in texts];passed+=len(texts)
    formatted=[('<|task_podcast|>' if i==0 else '')+f'<|SPEAKER_{i}|><|text_start|>'+normalize(t['text'])+'<|text_end|><|semantic_token_start|>' for i,t in enumerate(turns)]
    assert normalized['formatted']==formatted;passed+=4
    inspect=run('official-tokenizer',dict(format='lma.soulx-language-input/1',mode='inspect',texts=texts,turns=turns))
    layout=inspect['layout'];assert layout==manifest['layout'];passed+=4
    assert [t['ids'] for t in inspect['texts']]==[encode(x) for x in texts] and [t['normalized'] for t in inspect['texts']]==[normalize(x) for x in texts];passed+=len(texts)*2
    assert [t['ids'] for t in inspect['formatted']]==[encode(x) for x in formatted];passed+=4
    community=ASSETS/lock['community_gguf']['file'];older=run('older-layout',dict(format='lma.soulx-language-input/1',mode='inspect',texts=['<|0|>','<|6560|>'],turns=[]),selected=community)
    assert older['layout']==dict(vocabulary=159488,speech_offset=152927,speech_eos=151675,audio_start=151674) and older['layout']!=layout;passed+=5
    # Independent original upstream sampler blocks with actual HF processors.
    cases=[];oracles=[]
    for i in range(12):
        logits=rng.normal(0,1,6600).astype('f4');logits[100]=8 if i in [0,1,2] else logits[100]
        generated=[100]*(6 if i==0 else 1) if i<3 else [40,44,48,40];prompt=[100]*25 if i==2 else [7,11,100]
        sampling=dict(temperature=[.6,1,0][i%3],repetition_penalty=[1.25,.8,1][i%3],top_k=[100,0,7][i%3],top_p=[.9,1,.2][i%3],min_tokens=8,max_tokens=100,use_ras=i%4!=3 and i%3!=2,ras_window=25,ras_tau=.2)
        case=dict(logits=logits.tolist(),generated=generated,input=prompt+generated,sampling=sampling,candidate_uniform=float(rng.random()),final_uniform=float(rng.random()));cases.append(case);oracles.append(ras_case(case))
    sampled=run('ras-policy',dict(mode='sample',layout=dict(vocabulary=6600,offset=39,eos=5,audio_start=7),cases=cases),policy_only=True)
    for i,(got,want) in enumerate(zip(sampled['cases'],oracles)):
        assert got['ok'] and got['token']==want['token'] and got['ras_reset']==want['ras_reset'],(i,got['token'],want['token'])
        error=float(np.max(np.abs(np.array(got['probabilities'])-want['probabilities'])));assert error<=2e-6,(i,error);passed+=4;metrics.append(dict(kind='processed_probabilities',case=i,maximum_absolute_error=error,maximum_allowed=2e-6))
    # Run the original publisher's prompt/history blocks, not a rewritten Python oracle.
    for speaker_count in [1,2,4]:
        references=[dict(text='Reference '+str(i),codes=[i,12,6560]) for i in range(speaker_count)];target=[dict(text='Target '+str(i),speaker=i%speaker_count,generated=[layout['speech_offset']+i,layout['speech_eos']]) for i in range(12)]
        tokenized={}
        for i,ref in enumerate(references):tokenized[('<|task_podcast|>' if i==0 else '')+f'<|SPEAKER_{i}|><|text_start|>'+normalize(ref['text'])+'<|text_end|><|semantic_token_start|>']=encode(('<|task_podcast|>' if i==0 else '')+f'<|SPEAKER_{i}|><|text_start|>'+normalize(ref['text'])+'<|text_end|><|semantic_token_start|>')
        for t in target:
            f=f'<|SPEAKER_{t["speaker"]}|><|text_start|>'+normalize(t['text'])+'<|text_end|><|semantic_token_start|>';tokenized[f]=encode(f)
        request=dict(mode='history',layout=dict(vocabulary=layout['vocabulary'],offset=layout['speech_offset'],eos=layout['speech_eos'],audio_start=layout['audio_start']),references=references,turns=target,window=dict(max_turns=speaker_count+2,threshold=6192,history=2,text_history=2),context=2048,reserve=100,tokenized=tokenized)
        expected=original_history(request);got=run('history-'+str(speaker_count),request,policy_only=True);assert got['inputs']==expected and got['resets']>0;passed+=len(expected)+1
        broken=copy.deepcopy(request);broken['references'][0]['codes']=[6561];run('invalid-code-'+str(speaker_count),broken,False,policy_only=True);passed+=1
    reference=json.loads((ROOT/'build/soulx-reference-tests/results.json').read_text(encoding='utf-8'));current(reference['input_fingerprint'])
    prepared=[]
    for i in [0,1,0,1]:prepared.append(np.fromfile(ROOT/'build/soulx-reference-tests/native-results'/('reference-'+str(i))/'tokens.i64',dtype='<i8').astype('i4').tolist())
    tokens=encode('<|task_podcast|><|SPEAKER_0|><|text_start|>'+normalize('This is a synthetic reference.')+'<|text_end|><|semantic_token_start|>')+[x+layout['speech_offset'] for x in prepared[0]]+[layout['speech_eos']]+encode('<|SPEAKER_0|><|text_start|>Hello.<|text_end|><|semantic_token_start|>')
    eval_request=dict(format='lma.soulx-language-input/1',mode='evaluate',context=2048,threads=4,batch=128,tokens=tokens)
    evaluated=run('trained-logits',eval_request);assert evaluated['decode_calls']>0;passed+=1
    oracle=OUT/'publisher-logits.f32';command=[sys.executable,'tools/soulx_language_logits.py','--input',str(OUT/'trained-logits.json'),'--output',str(oracle)]
    with (OUT/'publisher-logits.log').open('wb') as log:process=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    if process.returncode:raise RuntimeError('Inspect publisher-logits.log')
    hf_reference=json.loads(oracle.with_suffix('.json').read_text(encoding='utf-8'))
    assert hf_reference['original_publisher_hf_forward'] and hf_reference['full_layers']==28 and hf_reference['output_logits']==160156;passed+=3
    assert hf_reference['complete_tensor_index_derived'] and hf_reference['publisher_embedding_head_equal'] and hf_reference['reference_dtype']=='bfloat16';passed+=3
    actual=np.asarray(evaluated['logits'],dtype='f8');expected=np.fromfile(oracle,dtype='<f4').astype('f8');assert actual.shape==expected.shape==(160156,) and np.isfinite(actual).all();passed+=2
    cosine=float(np.dot(actual,expected)/(np.linalg.norm(actual)*np.linalg.norm(expected)));rmse=float(np.sqrt(np.mean((actual-expected)**2)));overlap=len(set(np.argsort(actual)[-20:])&set(np.argsort(expected)[-20:]))/20
    assert cosine>=.99 and rmse<=.5 and overlap>=.4,('Q4 vs original BF16 logits',cosine,rmse,overlap);passed+=3
    logit_metrics=dict(kind='native_q4_vs_original_hf_bf16',values=160156,cosine=cosine,minimum_cosine=.99,rmse=rmse,maximum_rmse=.5,top20_overlap=overlap,minimum_top20_overlap=.4)
    request=dict(format='lma.soulx-language-input/1',mode='generate',context=2048,threads=4,batch=128,seed=42,
        references=[dict(text='This is a synthetic reference.',codes=codes) for codes in prepared],turns=[dict(text='Hello.',speaker=0),dict(text='Good day.',speaker=3)],
        window=dict(max_turns=6,threshold=6192,history=2,text_history=2),sampling=dict(temperature=0,repetition_penalty=1.25,top_k=100,top_p=.9,min_tokens=8,max_tokens=96,use_ras=False))
    print('Run complete trained Qwen3 with native trained S3 reference codes',flush=True)
    generated=run('trained-generation',request,timeout=900)
    assert generated['decode_calls']>0 and generated['generated_tokens']>=2 and len(generated['turns'])==2;passed+=3
    for t in generated['turns']:
        assert t['codes'] and all(0<=x<6561 for x in t['codes']) and t['language_ids']==[x+layout['speech_offset'] for x in t['codes']]+([layout['speech_eos']] if t['eos'] else [])
        assert t['history_delimiter_inserted']==(not t['eos']);passed+=3
    # Same actual model lifetime/generation again, proving deterministic greedy codes.
    repeat=run('trained-repeat',request,timeout=900);assert repeat['turns']==generated['turns'];passed+=1
    for mode in ['cancel_before','cancel_decode','cancel_token']:
        req={**request,'mode':mode};cancelled=run(mode,req,False,timeout=900);assert 'cancelled' in cancelled['error'];passed+=1
        if mode=='cancel_decode':assert cancelled['aborted_decodes']==1;passed+=1
    for key,value in [('threads',0),('context',9000),('batch',0)]:
        req={**request,key:value};run('invalid-'+key,req,False);passed+=1
    bad={**request,'turns':[dict(text='<|semantic_token_end|>',speaker=0)]};run('invalid-protocol-text',bad,False);passed+=1
    current(inputs);current(reference['input_fingerprint'])
    record=dict(passed=passed,actual_host_children=children,actual_trained_language_generations=2,actual_neural_decode_calls=sum(r['decode_calls'] for r in runs),actual_aborted_decodes=sum(r['aborted_decodes'] for r in runs),
        full_language_layers=28,full_language_tensors=311,official_layout=layout,older_community_layout=older['layout'],official_source_hashes_verified=True,trained_reference_components_used=2,
        original_upstream_ras_blocks_executed=True,original_upstream_history_blocks_executed=True,original_normalization_executed=True,exact_publisher_tokenizer_ids=True,original_full_hf_forward_executed=True,logit_metrics=logit_metrics,
        reference_evidence_fingerprint=reference['input_fingerprint'],host_compile_fingerprint=compiled['input_fingerprint'],
        native_binary_sha256=sha(exe),policy_binary_sha256=sha(policy),actual_original_hf_oracle_children=1,original_hf_reference=hf_reference,
        converted_language_assets=manifest['assets'],metrics=metrics,runs=runs,
        successful_turns=[{k:t[k] for k in ['speaker','eos','input_tokens','history_delimiter_inserted']}|dict(semantic_codes=len(t['codes'])) for t in generated['turns']],
        full_soulx_text_to_speech=False,speech_quality_tested=False,real_person_audio_used=False,physical_android=False,apk_runtime_used=False,engine_registered=False,input_fingerprint=inputs)
    (OUT/'results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k not in ['input_fingerprint','reference_evidence_fingerprint','metrics','runs']}),flush=True)

if __name__=='__main__':main()
