"""Original full publisher HF Qwen3 CPU forward for native-logit comparisons.

Offline developer oracle. No remote code, downloads, speech-quality claim
or use as an Android runtime. All original model assets are hash-verified.
"""
import argparse,gc,json,os,tempfile
from pathlib import Path
from fetch_soulx_language import verify,ASSETS,ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();lock=verify()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HOME=str(ROOT/'build/hf-cache'),TOKENIZERS_PARALLELISM='false')
    import numpy as np,torch
    from transformers import AutoModelForCausalLM
    torch.set_num_threads(4)
    request=json.loads(args.input.read_text(encoding='utf-8'));tokens=request['tokens'];assert tokens and len(tokens)<=2048 and all(isinstance(t,int) and 0<=t<160156 for t in tokens)
    # Derive a fresh complete shard index from the verified publisher tensors.
    # Do not depend on an unverified/manual index beside the original assets.
    from safetensors import safe_open
    with tempfile.TemporaryDirectory(prefix='soulx-language-hf-',dir=ROOT/'build') as temporary:
        source=Path(temporary);weight_map={}
        for file in ['config.json','generation_config.json']:os.link(ASSETS/file,source/file)
        for item in lock['publisher_assets']:
            if not item['file'].endswith('.safetensors'):continue
            file=ASSETS/item['file']
            os.link(file,source/file.name)
            with safe_open(file,framework='pt',device='cpu') as shard:
                for key in shard.keys():
                    assert key not in weight_map;weight_map[key]=file.name
        assert len(weight_map)==311 and len(set(weight_map.values()))==3
        (source/'model.safetensors.index.json').write_text(json.dumps(dict(metadata={},weight_map=weight_map)),encoding='utf-8')
        # Validate every embedding/head value before retaining the publisher's
        # tied configuration, rather than silently discarding a distinct head.
        with safe_open(source/weight_map['model.embed_tokens.weight'],framework='pt',device='cpu') as embed,safe_open(source/weight_map['lm_head.weight'],framework='pt',device='cpu') as head:
            e=embed.get_tensor('model.embed_tokens.weight');h=head.get_tensor('lm_head.weight');assert torch.equal(e,h);del e,h
        model=AutoModelForCausalLM.from_pretrained(source,local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,attn_implementation='eager')
        assert len(model.model.layers)==28 and model.config.hidden_size==2048 and model.config.vocab_size==160156
        model.eval()
        with torch.inference_mode():logits=model(input_ids=torch.tensor([tokens],dtype=torch.int64),use_cache=False,logits_to_keep=1).logits[0,-1].float().cpu().numpy()
        del model;gc.collect()
    assert logits.shape==(160156,) and np.isfinite(logits).all();args.output.parent.mkdir(parents=True,exist_ok=True);logits.astype('<f4').tofile(args.output)
    args.output.with_suffix('.json').write_text(json.dumps(dict(original_publisher_hf_forward=True,full_layers=28,complete_tensor_index_derived=True,publisher_embedding_head_equal=True,reference_dtype='bfloat16',output_dtype='float32',torch_version=torch.__version__,input_tokens=len(tokens),output_logits=160156,model_inference_on_phone=False)),encoding='utf-8')
    print('Original full trained HF Qwen3 forward completed, BF16 CPU; no phone/TTS-quality evidence',flush=True)

if __name__=='__main__':main()
