"""Pinned original SoulX normalization, RAS loop and history-window oracles."""
import ast,copy,json,re,time,types
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def original_normalize():
    path=ROOT/'build/native-src/soulx-podcast/soulxpodcast/utils/text.py';module=ast.parse(path.read_text(encoding='utf-8'))
    function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='normalize_text');env={'re':re}
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),env);return env['normalize_text']

def ras_case(case):
    import torch
    from transformers import LogitsProcessorList,RepetitionPenaltyLogitsProcessor,MinNewTokensLengthLogitsProcessor,TemperatureLogitsWarper,TopKLogitsWarper,TopPLogitsWarper
    path=ROOT/'build/native-src/soulx-podcast/soulxpodcast/models/modules/sampler.py';module=ast.parse(path.read_text(encoding='utf-8'))
    function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='_ras_sample_hf_engine');loop=next(n for n in function.body if isinstance(n,ast.While))
    # Extract the actual logits copy, processor, RAS and final sample blocks;
    # omit neural forward/cache/reporting, not sampling math.
    selected=[n for n in loop.body if n.lineno in [136,140,143,171]]
    assert len(selected)==4,'Pinned RAS source layout changed'
    p=case['sampling'];raw=torch.tensor(case['logits'],dtype=torch.float32)[None,None,:];generated=case['generated'];ids=torch.tensor([case['input']],dtype=torch.int64)
    ignore=ids.shape[1]-len(generated)
    processors=LogitsProcessorList([RepetitionPenaltyLogitsProcessor(float(p.get('repetition_penalty',1.25)),prompt_ignore_length=ignore),MinNewTokensLengthLogitsProcessor(ignore,p.get('min_tokens',8),5)])
    temperature=float(p.get('temperature',.6))
    if temperature>0:
        processors.append(TemperatureLogitsWarper(temperature))
        if p.get('top_k',100)>0:processors.append(TopKLogitsWarper(p.get('top_k',100)))
        if p.get('top_p',.9)<1:processors.append(TopPLogitsWarper(float(p.get('top_p',.9))))
    processed=processors(ids,raw[:,-1,:].clone());probabilities=torch.softmax(processed,dim=-1)[0].numpy().astype('f8')
    uniforms=iter([case['candidate_uniform'],case['final_uniform']] if p.get('use_ras',True) else [case['final_uniform']]);calls=[]
    def multinomial(probs,num_samples):
        assert num_samples==1;u=next(uniforms);array=probs[0].detach().numpy().astype('f8');cdf=np.cumsum(array/array.sum());token=min(int(np.searchsorted(cdf,u,side='right')),len(array)-1);calls.append(token);return torch.tensor([[token]],dtype=torch.int64)
    proxy=types.SimpleNamespace(multinomial=multinomial,argmax=torch.argmax,float32=torch.float32)
    env=dict(torch=proxy,nn=torch.nn,outputs=types.SimpleNamespace(logits=raw),input_ids=ids,logits_processor=processors,use_ras=p.get('use_ras',True),win_size=p.get('ras_window',25),tau_r=p.get('ras_tau',.2),do_sample=temperature>0)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),env)
    reset=False
    if p.get('use_ras',True) and temperature>0:
        candidate=calls[0];reset=int((ids[:,-p.get('ras_window',25):]==candidate).sum())+1>=p.get('ras_window',25)*p.get('ras_tau',.2)
    return dict(probabilities=probabilities,token=int(env['next_tokens'].item()),ras_reset=reset,actual_upstream_blocks=4)

def original_history(request):
    import torch
    from itertools import chain
    path=ROOT/'build/native-src/soulx-podcast/soulxpodcast/models/soulxpodcast.py';module=ast.parse(path.read_text(encoding='utf-8'))
    klass=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='SoulXPodcast');function=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='forward_longform')
    selected=[copy.deepcopy(n) for n in function.body if 93<=n.lineno<=117]
    loop=next(n for n in selected if isinstance(n,ast.For) and n.lineno==117);loop.body=[n for n in loop.body if n.lineno<=139]
    generated=[t['generated'] for t in request['turns']];inputs=[]
    def generate(ids,sampling_params,past_key_values):
        inputs.append(list(ids));return {'token_ids':generated[len(inputs)-1]}
    config=request['window'];refs=request['references'];layout=request['layout'];normal=original_normalize()
    def formatted(text,speaker,first):return ('<|task_podcast|>' if first else '')+f'<|SPEAKER_{speaker}|><|text_start|>'+normal(text)+'<|text_end|><|semantic_token_start|>'
    prompt_ids=[request['tokenized'][formatted(r['text'],i,i==0)] for i,r in enumerate(refs)]
    target_ids=[request['tokenized'][formatted(t['text'],t['speaker'],False)] for t in request['turns']]
    hf=types.SimpleNamespace(speech_token_offset=layout['offset'],eos_token_id=layout['eos'])
    obj=types.SimpleNamespace(config=types.SimpleNamespace(hf_config=hf,max_turn_size=config['max_turns'],turn_tokens_threshold=config['threshold'],prompt_context=len(refs),history_context=config['history'],history_text_context=config['text_history']),llm=types.SimpleNamespace(config=types.SimpleNamespace(hf_config=hf),generate=generate))
    env=dict(torch=torch,chain=chain,self=obj,prompt_size=len(refs),turn_size=len(target_ids),prompt_speech_tokens=[torch.tensor(r['codes']) for r in refs],prompt_text_tokens_for_llm=prompt_ids,text_tokens_for_llm=target_ids,use_dialect_prompt=False,sampling_params=None,time=time,
        AutoPretrainedConfig=lambda:types.SimpleNamespace(from_dataclass=lambda x:None),DynamicCache=lambda **kwargs:None)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(path),'exec'),env);return inputs
