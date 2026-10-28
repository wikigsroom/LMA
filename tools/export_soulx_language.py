"""Offline full official SoulX language export and explicit Q4_K_M quantization.

Reads only previously selected, hash-verified publisher assets. Full upstream
conversion and quantization run locally; no model/code/dependency download.
The new user/developer output directory is committed only after success.
"""
import argparse,hashlib,importlib.metadata,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
from evidence import current
from fetch_soulx_language import verify,sha,ASSETS
ROOT=Path(__file__).resolve().parents[1]

def convert(output):
    lock=verify();output=output.resolve()
    if output.exists():raise RuntimeError('Output must be a new directory; existing models are preserved')
    host=ROOT/'build/soulx-language-host';compiled=json.loads((host/'receipt.json').read_text(encoding='utf-8'));current(compiled['input_fingerprint'])
    quantizer=host/'bin/lma_soulx_quantize.exe'
    if sha(quantizer)!=compiled['quantizer_sha256']:raise RuntimeError('Changed native quantizer')
    versions={name:importlib.metadata.version(name) for name in ['torch','transformers','tokenizers','numpy','safetensors']}
    python=ROOT/'build/soulx-language-python'
    if not (python/'sentencepiece').is_dir():raise RuntimeError('Explicitly prepare sentencepiece==0.2.1 in build/soulx-language-python first')
    output.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.soulx-language-',dir=output.parent))
    try:
        source=stage/'source';source.mkdir()
        for item in lock['publisher_assets']:os.link(ASSETS/item['file'],source/item['file'])
        from safetensors import safe_open
        weight_map={}
        for item in lock['publisher_assets']:
            if item['file'].endswith('.safetensors'):
                with safe_open(source/item['file'],framework='pt',device='cpu') as model:
                    for key in model.keys():
                        if key in weight_map:raise RuntimeError('Duplicated publisher language tensor')
                        weight_map[key]=item['file']
        if len(weight_map)!=311:raise RuntimeError('Incomplete full SoulX language tensor set')
        (source/'model.safetensors.index.json').write_text(json.dumps(dict(weight_map=weight_map),indent=2)+'\n',encoding='utf-8')
        f16=stage/'full-f16.gguf';gguf=stage/'soulx-language-q4_k_m.gguf'
        env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(ROOT/'build/hf-cache'),PYTHONIOENCODING='utf-8',PYTHONPATH=str(python),TOKENIZERS_PARALLELISM='false')
        command=[sys.executable,str(ROOT/'build/native-src/llama-soulx/convert_hf_to_gguf.py'),str(source),'--outfile',str(f16),'--outtype','f16']
        # The pinned upstream quantizer writes with a narrow std::ofstream on
        # Windows. Keep its filenames ASCII and use Python's Unicode-safe cwd;
        # the repository and staging directory may contain non-ASCII text.
        for i,cmd in enumerate([command,[str(quantizer),f16.name,gguf.name]]):
            with (stage/('conversion-'+str(i)+'.log')).open('wb') as log:result=subprocess.run(cmd,cwd=stage if i else ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
            if result.returncode:raise RuntimeError('Conversion failed; '+str(stage/('conversion-'+str(i)+'.log')))
        sys.path.insert(0,str(ROOT/'build/native-src/llama-soulx/gguf-py'));from gguf import GGUFReader
        reader=GGUFReader(str(gguf));tokens=reader.fields['tokenizer.ggml.tokens'].contents();marker=lambda name:tokens.index(name)
        layout=dict(vocabulary=len(tokens),speech_offset=marker('<|0|>'),speech_eos=marker('<|semantic_token_end|>'),audio_start=marker('<|semantic_token_start|>'))
        if layout!={'vocabulary':160156,'speech_offset':153595,'speech_eos':153478,'audio_start':153477} or len(reader.tensors)!=311:raise RuntimeError('Official model/tokenizer layout mismatch after conversion')
        if any(marker('<|'+str(i)+'|>')!=layout['speech_offset']+i for i in range(6561)):raise RuntimeError('Noncontiguous semantic vocabulary')
        del reader
        record=dict(format='lma.soulx-language-gguf/1',architecture='qwen3_soulx_podcast',layout=layout,full_layers=28,full_tensors=311,
            source_assets=lock['publisher_assets'],llama_revision=lock['sources'][0]['revision'],developer_versions={**versions,'sentencepiece':'0.2.1'},
            assets=[dict(file=gguf.name,bytes=gguf.stat().st_size,sha256=sha(gguf),role='language')],official_source_hashes_verified=True,
            tokenizer_embedded_in_user_gguf=True,model_assets_packaged_in_apk=False,full_soulx_pipeline=False)
        (stage/'soulx-language.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        # Own staging paths were verified at creation; remove only conversion
        # intermediates and hardlinks, never original publisher/user assets.
        if source.resolve().parent!=stage or f16.resolve().parent!=stage:raise RuntimeError('Unsafe conversion staging cleanup')
        shutil.rmtree(source);f16.unlink();stage.rename(output);return record
    except Exception:
        # Preserve diagnostic logs and intermediate files on a failed conversion.
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args();record=convert(args.output_dir)
    print(json.dumps({k:v for k,v in record.items() if k!='source_assets'}),flush=True)
