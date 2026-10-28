"""Create offline T5 fixtures with the independent installed Hugging Face model.

Full trained comparisons dequantize the pinned community GGUF, one original
Transformers module at a time. They do NOT compare to unquantized Google weights,
prove prompt/video quality, or run on a phone. No native encoder is called here.
"""
import argparse
import gc
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path
from evidence import fingerprint,current
from fetch_ltx098_text import assets,sources,sha,DIRECTORY

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/ltx098-text-oracle'


def inputs():
    return fingerprint('tools/ltx098_text_oracle.py','tools/fetch_ltx098_text.py','third_party/ltx098-text-source-lock.json')


def dependencies(lock):
    # All caches remain project-local. Imports do not install or download anything.
    sys.dont_write_bytecode=True
    sys.path[:0]=[str(ROOT/'build/soulx-language-python'),str(ROOT/'build/native-src/llama-soulx/gguf-py')]
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(ROOT/'build/hf-cache'),TOKENIZERS_PARALLELISM='false')
    import numpy as np
    import torch
    import gguf
    import transformers
    import sentencepiece
    versions=dict(transformers=transformers.__version__,torch=torch.__version__,numpy=np.__version__,sentencepiece=sentencepiece.__version__)
    expected=lock['oracle_dependencies']
    assert versions=={k:(v['version'] if isinstance(v,dict) else v) for k,v in expected.items()},'Different numerical reference dependency version'
    base=Path(transformers.__file__).parent
    for name,digest in expected['transformers']['files'].items():assert sha(base/name)==digest,'Modified Transformers reference source: '+name
    torch.set_num_threads(4)
    return np,torch,gguf,transformers,versions


def mapping(layers):
    result={'encoder.embed_tokens.weight':'token_embd.weight','encoder.final_layer_norm.weight':'enc.output_norm.weight'}
    for i in range(layers):
        a=f'encoder.block.{i}.layer.0.';f=f'encoder.block.{i}.layer.1.';g=f'enc.blk.{i}.'
        for hf,gg in [('q','q'),('k','k'),('v','v'),('o','o')]:result[a+'SelfAttention.'+hf+'.weight']=g+'attn_'+gg+'.weight'
        result[a+'layer_norm.weight']=g+'attn_norm.weight'
        if i==0:result[a+'SelfAttention.relative_attention_bias.weight']=g+'attn_rel_b.weight'
        for hf,gg in [('wi_0','gate'),('wi_1','up'),('wo','down')]:result[f+'DenseReluDense.'+hf+'.weight']=g+'ffn_'+gg+'.weight'
        result[f+'layer_norm.weight']=g+'ffn_norm.weight'
    return result


def fixture(np,torch,gguf,transformers,template,layers):
    torch.manual_seed(700+layers)
    config=transformers.T5Config(vocab_size=32128,d_model=32,d_kv=8,d_ff=64,num_layers=layers,num_heads=4,feed_forward_proj='gated-gelu',dropout_rate=0,layer_norm_epsilon=1e-6)
    model=transformers.T5EncoderModel(config).eval();path=OUT/f'untrained-{layers}.gguf'
    writer=gguf.GGUFWriter(path,'t5encoder')
    for k,field in template.fields.items():
        if k.startswith('tokenizer.'):
            writer.add_key_value(k,field.contents(),field.types[0],field.types[1] if len(field.types)>1 else None)
    for key,value in {'context_length':512,'embedding_length':32,'feed_forward_length':64,'block_count':layers,'attention.head_count':4,'attention.key_length':8,'attention.value_length':8,'attention.relative_buckets_count':32}.items():writer.add_uint32('t5encoder.'+key,value)
    writer.add_float32('t5encoder.attention.layer_norm_rms_epsilon',1e-6)
    writer.add_float32('t5encoder.attention.layer_norm_epsilon',1e-6)
    state=model.state_dict();names=mapping(layers)
    for hf,gg in names.items():writer.add_tensor(gg,state[hf].detach().numpy().copy())
    writer.write_header_to_file();writer.write_kv_data_to_file();writer.write_tensors_to_file(progress=False);writer.close()
    return model,path


def write_json(name,value):
    path=OUT/name;path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return path.name


def paged_reference(np,torch,gguf,transformers,reader,config):
    """Execute the original encoder forward, keeping at most one block resident."""
    with torch.device('meta'):model=transformers.T5EncoderModel(config).eval()
    tensors={t.name:t for t in reader.tensors};names=mapping(config.num_layers);used=set();hooks=[]
    assert set(tensors)==set(names.values()),'Unexpected/missing trained encoder tensor layout'
    def materialize(hf):
        name=names[hf];tensor=tensors[name];used.add(name)
        array=gguf.quants.dequantize(tensor.data,tensor.tensor_type).astype(np.float32,copy=False)
        return torch.from_numpy(array.copy())
    def bind(module,prefix,embedding=False):
        keys=list(module.state_dict())
        def before(target,args):
            target.load_state_dict({k:materialize('encoder.embed_tokens.weight' if embedding else prefix+k) for k in keys},strict=True,assign=True)
        def after(target,args,output):target.to_empty(device='meta')
        hooks.extend([module.register_forward_pre_hook(before),module.register_forward_hook(after)])
    # Transformers 5.17 constructs encoder.embed_tokens separately from shared.
    # Bind the module actually called by the unmodified encoder forward; do not
    # assume a shared-weight alias or materialize the unused meta embedding.
    bind(model.encoder.embed_tokens,'',True)
    for i,block in enumerate(model.encoder.block):bind(block,f'encoder.block.{i}.')
    bind(model.encoder.final_layer_norm,'encoder.final_layer_norm.')
    return model,used,tensors,hooks


def create(trained=False):
    lock=sources();print('Verifying external T5 assets',flush=True);assets(oracle=True);record=inputs()
    print('Importing pinned offline reference dependencies',flush=True);np,torch,gguf,transformers,versions=dependencies(lock)
    OUT.mkdir(exist_ok=True);(OUT/'manifest.json').unlink(missing_ok=True)
    reader=gguf.GGUFReader(DIRECTORY/'originals'/lock['model']['file'])
    tokenizer=transformers.T5Tokenizer.from_pretrained(str(DIRECTORY/'oracle'),local_files_only=True,legacy=True)
    import sentencepiece
    from sentencepiece import sentencepiece_model_pb2
    serialized=(DIRECTORY/'oracle/spiece.model').read_bytes()
    processor=sentencepiece.SentencePieceProcessor(model_proto=serialized)
    proto=sentencepiece_model_pb2.ModelProto();proto.ParseFromString(serialized)
    pieces=reader.fields['tokenizer.ggml.tokens'].contents();scores=reader.fields['tokenizer.ggml.scores'].contents()
    assert processor.get_piece_size()==32000 and len(pieces)==32128
    assert pieces[:32000]==[processor.id_to_piece(i) for i in range(32000)],'GGUF learned vocabulary differs from original SentencePiece'
    assert np.array_equal(np.asarray(scores[:32000],np.float32),np.asarray([processor.get_score(i) for i in range(32000)],np.float32)),'GGUF learned scores differ'
    charsmap=bytes(reader.fields['tokenizer.ggml.precompiled_charsmap'].contents())
    assert charsmap==proto.normalizer_spec.precompiled_charsmap,'GGUF normalization differs from original SentencePiece'
    assert reader.fields['tokenizer.ggml.add_space_prefix'].contents()==proto.normalizer_spec.add_dummy_prefix
    assert reader.fields['tokenizer.ggml.remove_extra_whitespaces'].contents()==proto.normalizer_spec.remove_extra_whitespaces
    vocab_identity=dict(learned_tokens_compared=32000,learned_scores_compared=32000,sentinel_definitions_from_external_config=100,
        normalized_charsmap_bytes=len(charsmap),normalized_charsmap_sha256=__import__('hashlib').sha256(charsmap).hexdigest(),gguf_sentinel_names_missing=True)
    prompts=[
        'A red balloon floats above a quiet lake.',
        '  Hello, world!\n\t', '', '\u3000\u2003\t\n',
        '中文测试，a small cat。', 'Café naïve Straße — Привет!',
        'one <extra_id_0> two <extra_id_99>', 'literal </s>', '<pad> a token',
        'a\x00b 😀', 'Line\n\n two\t  spaces', '\u001c\u0085\u00a0test\u202f\u3000',
        '  a photograph of mountains, rivers and trees. '*100,
        '<extra_id_0>two', 'one<extra_id_5>two', '<extra_id_99><extra_id_0>',
        'one<extra_id_100>two', 'one<extra_id_01>two', '<extra_id_7> 中文',
        '<extra_id_3>\n\t two</s>', '<extra_id_4>\u2581test',
    ]
    token_cases=[]
    for i,prompt in enumerate(prompts):
        for maximum in ([1,2,16,256] if i in [0,12] else [256]):
            full=tokenizer.encode(prompt.strip(),add_special_tokens=True)
            ids=tokenizer.encode(prompt.strip(),add_special_tokens=True,truncation=True,max_length=maximum)
            request=write_json(f'tokens-{i}-{maximum}.json',dict(operation='tokenize',max_tokens=maximum,inputs=[dict(prompt=prompt)]))
            token_cases.append(dict(request=request,tokens=ids,truncated=len(full)>maximum,max_tokens=maximum,prompt_case=i))
    untrained=[];padded_checks=[]
    for layers in [2,24]:
        print('Creating independent untrained T5 fixture: '+str(layers)+' layers',flush=True)
        model,model_file=fixture(np,torch,gguf,transformers,reader,layers)
        for index,ids in enumerate([[3,4,1],[32127,32099,2,1],[0,7,0,12,1],list(range(3,258))+[1]]):
            inputs_tensor=torch.tensor([ids],dtype=torch.long)
            with torch.inference_mode():expected=model(input_ids=inputs_tensor,attention_mask=torch.ones_like(inputs_tensor)).last_hidden_state.detach().numpy().copy()
            expected_path=OUT/f'untrained-{layers}-{index}.f32';expected.astype('<f4').tofile(expected_path)
            request=write_json(f'untrained-{layers}-{index}.json',dict(operation='encode',inputs=[dict(tokens=ids)]))
            untrained.append(dict(model=model_file.name,request=request,expected=expected_path.name,tokens=ids,shape=list(expected.shape),layers=layers))
        for prompt in [prompts[0],prompts[4],prompts[6]]:
            encoded=tokenizer(prompt.strip(),max_length=256,truncation=True,padding='max_length',return_tensors='pt')
            valid=int(encoded['attention_mask'].sum())
            with torch.inference_mode():
                padded=model(**encoded).last_hidden_state[:,:valid].numpy().copy()
                compact=model(input_ids=encoded['input_ids'][:,:valid],attention_mask=encoded['attention_mask'][:,:valid]).last_hidden_state.numpy().copy()
            error=float(np.max(np.abs(padded-compact)));assert error<1e-4,'Compacting valid T5 tokens changes reference attention'
            padded_checks.append(dict(layers=layers,valid_tokens=valid,padded_tokens=256,max_abs=error))
        del model;gc.collect()
    trained_case=None
    if trained:
        print('Evaluating full trained T5 via original module forwards',flush=True)
        config=transformers.T5Config.from_pretrained(str(DIRECTORY/'oracle'),local_files_only=True)
        assert (config.d_model,config.d_ff,config.d_kv,config.num_layers,config.num_heads,config.feed_forward_proj)==(4096,10240,64,24,64,'gated-gelu')
        model,used,tensors,hooks=paged_reference(np,torch,gguf,transformers,reader,config)
        texts=[prompts[0],'A blue boat moves slowly across a calm lake.','A <extra_id_0> boat on a lake.']
        enc=tokenizer([t.strip() for t in texts],return_tensors='pt',padding=True,truncation=True,max_length=256)
        start=time.perf_counter()
        with torch.inference_mode():values=model(**enc).last_hidden_state.detach().numpy().copy()
        seconds=time.perf_counter()-start
        assert used==set(tensors),'Not all trained T5 tensors were evaluated'
        examples=[]
        for i,text in enumerate(texts):
            count=int(enc['attention_mask'][i].sum());name=f'trained-{i}.f32';values[i,:count].astype('<f4').tofile(OUT/name)
            examples.append(dict(prompt=text,tokens=enc['input_ids'][i,:count].tolist(),expected=name,shape=[1,count,config.d_model]))
        request=write_json('trained.json',dict(operation='encode',inputs=[dict(prompt=texts[0]),dict(prompt=texts[1]),dict(prompt=texts[2]),dict(prompt=texts[0])]))
        trained_case=dict(request=request,examples=examples,native_item_order=[0,1,2,0],evaluated_tensors=len(used),tensor_parameters=sum(int(np.prod(t.shape)) for t in reader.tensors),
            reference_seconds=seconds,reference_input_shape=list(enc['input_ids'].shape),reference='Unmodified installed Transformers T5EncoderModel; pinned GGUF dequantized to F32, one original module resident at a time',
            original_unquantized_weights_compared=False,prompt_quality_tested=False,video_quality_tested=False)
        for h in hooks:h.remove()
        del model;gc.collect()
    names={case['request'] for case in token_cases}
    for case in untrained:names.update(case[k] for k in ['model','request','expected'])
    if trained_case:
        names.add(trained_case['request']);names.update(item['expected'] for item in trained_case['examples'])
    artifacts={name:dict(bytes=(OUT/name).stat().st_size,sha256=sha(OUT/name)) for name in sorted(names)}
    manifest=dict(schema='lma.ltx098-text-oracle/1',oracle_dependencies=versions,model_asset=lock['model'],vocabulary_identity=vocab_identity,untrained=untrained,tokenization=token_cases,padded_mask_checks=padded_checks,
        trained=trained_case,artifacts=artifacts,input_fingerprint=record,remote_inference=False,physical_android=False)
    current(record);(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(untrained_cases=len(untrained),tokenization_cases=len(token_cases),padding_comparisons=len(padded_checks),trained_tensors=trained_case['evaluated_tensors'] if trained_case else 0,artifact_files=len(artifacts))),flush=True)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--trained',action='store_true');create(parser.parse_args().trained)
