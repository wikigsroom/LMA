"""Explicitly fetch three bounded tokenizer/config inputs for program tests, never neural weights.

No production app path calls this developer command. External .weight files,
complete Gemma/DiT/VAE models and image generation are intentionally absent.
"""
import hashlib
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
FILES=[
    ('sprint-gemma-meta.json','simota1987/Sana_Sprint/c7b846e1cec3ec9ec7ae456cf7d3ceb36742d656/gemma/gemma_meta.json',122,'443666ef0061ece40dedbaf17d81ff032a553191845077594dbfb3783c00938a'),
    ('tokenizer.model','Efficient-Large-Model/Sana_600M_1024px_diffusers/28f3af7689de15f3883d5863059a2fca0aa9b829/tokenizer/tokenizer.model',4241003,'61a7b147390c64585d6c3543dd6fc636906c9af3865a5548f27f31aee1d4c8e2'),
    ('tokenizer.json','Efficient-Large-Model/Sana_600M_1024px_diffusers/28f3af7689de15f3883d5863059a2fca0aa9b829/tokenizer/tokenizer.json',34362873,'5f7eee611703c5ce5d1eee32d9cdcfe465647b8aff0c1dfb3bed7ad7dbb05060'),
]


def main():
    output=ROOT/'build/sana-program-source';output.mkdir(parents=True,exist_ok=True)
    for name,source,size,digest in FILES:
        path=output/name
        if path.is_file() and path.stat().st_size==size and hashlib.sha256(path.read_bytes()).hexdigest()==digest:
            print('Verified cached program input: '+name);continue
        repo,owner,revision,*parts=source.split('/')
        for domain in ('huggingface.co','hf-mirror.com'):
            try:
                request=urllib.request.Request('https://'+domain+'/'+repo+'/'+owner+'/resolve/'+revision+'/'+'/'.join(parts),headers={'User-Agent':'LMA-program-metadata/1'})
                with urllib.request.urlopen(request,timeout=30) as stream:
                    data=stream.read(size+1)
                if len(data)!=size or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Program input identity differs: '+name)
                path.write_bytes(data);print('Fetched bounded program input: '+name);break
            except Exception:
                if domain=='hf-mirror.com':raise
    print('No complete model weights downloaded; no inference executed.')


if __name__=='__main__':main()
