"""Explicit developer-only review of pinned GGUF headers; never reads tensor weights or runs models."""
import argparse,hashlib,json,struct,urllib.request
from pathlib import Path
from evidence import fingerprint,current
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co')
    args=parser.parse_args();root=ROOT
    inputs=fingerprint('tools/audit_qwen_headers.py','catalogue/model-bundles.json','native/qwen_tts/model_contract.hpp','third_party/qwen-tts-source-lock.json')
    bundle=next(b for b in json.loads((root/'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['pipeline']=='qwen3_tts_06b_base')
    component=bundle['components'][0]
    url=args.origin+'/api/models/'+component['repository']+'/revision/'+component['revision']+'?blobs=true'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LMA-development-header-review/1'}),timeout=40) as response:repo=json.load(response)
    if repo['sha']!=component['revision']:raise RuntimeError('HF pinned revision differs')
    for selected in bundle['components']:
        actual=next(x for x in repo['siblings'] if x['rfilename']==selected['path'])
        if actual['size']!=selected['bytes'] or actual['lfs']['sha256']!=selected['sha256']:raise RuntimeError('HF component identity differs from the user-selectable recipe')
    results=[]
    for name in ['qwen-talker-0.6b-base-Q4_K_M.gguf','qwen-tokenizer-12hz-Q8_0.gguf']:
        url=args.origin+'/Serveurperso/Qwen3-TTS-GGUF/resolve/'+repo['sha']+'/'+name
        request=urllib.request.Request(url,headers={'Range':'bytes=0-16777215','User-Agent':'LMA-development-header-review/1','Accept-Encoding':'identity'})
        with urllib.request.urlopen(request,timeout=40) as response:
            if response.status!=206:raise RuntimeError('Header review requires a bounded range response')
            consumed=bytearray()
            def read(n):
                if n<0 or len(consumed)+n>16777216:raise RuntimeError('Header too large')
                b=response.read(n)
                if len(b)!=n:raise RuntimeError('Truncated header')
                consumed.extend(b);return b
            def num(fmt):return struct.unpack('<'+fmt,read(struct.calcsize('<'+fmt)))[0]
            def string(keep=True):
                n=num('Q')
                if n>4*1024*1024:raise RuntimeError('Oversized metadata string')
                b=read(n);return b.decode('utf-8') if keep else None
            def value(t,keep=True):
                if t==8:return string(keep)
                if t==9:
                    element=num('I');count=num('Q')
                    if count>2000000 or element==9:raise RuntimeError('Invalid metadata array')
                    for _ in range(count):value(element,False)
                    return {'element_type':element,'count':count} if keep else None
                f={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t]
                return num(f)
            if read(4)!=b'GGUF' or num('I')!=3:raise RuntimeError('Not GGUF v3')
            tensors_count=num('Q');metadata_count=num('Q');metadata={}
            if tensors_count>100000 or metadata_count>100000:raise RuntimeError('Oversized header tables')
            for _ in range(metadata_count):
                key=string();metadata[key]=value(num('I'))
            tensors={}
            for _ in range(tensors_count):
                key=string();ndim=num('I')
                if ndim<1 or ndim>4:raise RuntimeError('Invalid tensor rank')
                dims=[num('Q') for _ in range(ndim)];kind=num('I');offset=num('Q');tensors[key]=dims
            selected={k:v for k,v in metadata.items() if k.startswith(('general.','qwen3-tts.','qwen3-tts-tokenizer.')) and not isinstance(v,dict)}
            item=next(x for x in repo['siblings'] if x['rfilename']==name)
            if name.startswith('qwen-talker-'):
                expected={'general.architecture':'qwen3-tts','qwen3-tts.model_type':'base','qwen3-tts.talker.embedding_length':1024,'qwen3-tts.talker.block_count':28,'qwen3-tts.talker.text_hidden_size':2048,'qwen3-tts.talker.text_vocab_size':151936,'qwen3-tts.num_code_groups':16,'qwen3-tts.code_pred.block_count':5,'qwen3-tts.code_pred.embedding_length':1024}
                expected_tensors={'talker.text_embd.weight':[2048,151936],'talker.codec_embd.weight':[1024,3072],'talker.codec_head.weight':[1024,3072],'talker.output_norm.weight':[1024],'code_pred.output_norm.weight':[1024]}
                expected_tensors.update({'talker.blk.'+str(i)+'.attn_norm.weight':[1024] for i in range(28)})
                expected_tensors.update({'code_pred.blk.'+str(i)+'.attn_norm.weight':[1024] for i in range(5)})
                expected_tensors.update({'code_pred.lm_head.'+str(i)+'.weight':[1024,2048] for i in range(15)})
                expected_tensors['spk_enc.fc.weight']=[1,3072,1024]
                if not 151646<=metadata['tokenizer.ggml.tokens']['count']<=151936 or metadata['tokenizer.ggml.merges']['count']<1:raise RuntimeError('Embedded Qwen vocabulary/speaker data are missing')
            else:
                expected={'general.architecture':'qwen3-tts-tokenizer','qwen3-tts-tokenizer.output_sample_rate':24000,'qwen3-tts-tokenizer.decoder.num_quantizers':16,'qwen3-tts-tokenizer.decode_upsample_rate':1920};expected_tensors={}
                if not any(k.startswith('tok_dec.') for k in tensors):raise RuntimeError('Audio decoder tensors are missing')
            if any(metadata.get(k)!=v for k,v in expected.items()) or any(tensors.get(k)!=v for k,v in expected_tensors.items()):raise RuntimeError('Pinned GGUF header differs from this runtime conversion layout')
            record=dict(file=name,repository=repo['id'],revision=repo['sha'],bytes=item['size'],sha256=item['lfs']['sha256'],headerBytes=len(consumed),headerSHA256=hashlib.sha256(consumed).hexdigest(),metadata=selected,tensors=tensors,metadataArraySizes={k:v for k,v in metadata.items() if isinstance(v,dict)},complete_model_downloaded=False,model_inference=False)
            results.append(record)
            print(json.dumps(dict(file=name,headerBytes=len(consumed),identity=selected.get('general.architecture'),modelType=selected.get('qwen3-tts.model_type'),dimensions={k:v for k,v in selected.items() if any(s in k for s in ('embedding_length','block_count','sample_rate','num_code','num_quantizers','upsample_rate'))}),ensure_ascii=False),flush=True)
    current(inputs)
    report=dict(schema='lma.qwen-header-review/1',passed=True,revision=repo['sha'],records=results,gguf_header_metadata_read=True,tensor_weights_read=False,complete_model_weights_downloaded=False,model_inference=False,physical_android=False,input_fingerprint=inputs)
    (root/'build/qwen-headers.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,files=len(results),tensor_weights_read=False,model_inference=False)))

if __name__=='__main__':main()
