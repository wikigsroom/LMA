"""Explicit developer preparation of pinned SoulX language code/model assets.

Default verifies code only. --download requests the nine official model assets;
--community-gguf independently requests the older quantizer's GGUF. Nothing
is an App prerequisite, APK input or implicit download during testing/export.
"""
import argparse,hashlib,json,subprocess,urllib.request
from pathlib import Path
from fetch_soulx_reference import sha
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/soulx-language-source-lock.json'
ASSETS=ROOT/'build/soulx-language-assets/originals'

def sources():
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['sources']:
        source=ROOT/'build/native-src'/item['name']
        if not source.is_dir():raise RuntimeError('Explicitly prepare pinned code first: '+item['url']+' @ '+item['revision'])
        revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        if revision!=item['revision'] or subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():raise RuntimeError('Modified SoulX language source: '+item['name'])
        for name,digest in item['reviewed_files'].items():
            if sha(source/name)!=digest:raise RuntimeError('SoulX reviewed source changed: '+name)
    return lock

def verify(community=False):
    lock=sources();items=[lock['community_gguf']] if community else lock['publisher_assets']
    for item in items:
        p=ASSETS/item['file']
        if not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise RuntimeError('Missing/different explicitly selected SoulX language asset: '+item['file'])
    return lock

def download(item,origin):
    ASSETS.mkdir(parents=True,exist_ok=True);path=ASSETS/item['file'];partial=ASSETS/(item['file']+'.part')
    if path.exists():
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise RuntimeError('Existing language asset differs; preserve it for review')
        return
    if partial.exists():raise RuntimeError('Existing partial preserved; inspect this tool\'s partial before an explicit retry')
    # HF raw serves actual small JSON; large LFS files need resolve.
    kind='resolve' if item['file'].endswith(('.safetensors','.gguf')) or item['file']=='tokenizer.json' else 'raw'
    url=origin+'/'+item['repo']+'/'+kind+'/'+item['revision']+'/'+item['file']
    digest=hashlib.sha256();size=0
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LMA-explicit-developer-language/1'}),timeout=45) as response,partial.open('xb') as target:
        while block:=response.read(1024*1024):
            size+=len(block)
            if size>item['bytes']:raise RuntimeError('Language asset exceeds pinned size')
            digest.update(block);target.write(block)
    if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise RuntimeError('Language publisher identity mismatch; partial retained')
    partial.rename(path)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true');parser.add_argument('--community-gguf',action='store_true')
    parser.add_argument('--origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co');args=parser.parse_args();lock=sources()
    if args.download:
        for item in lock['publisher_assets']:download(item,args.origin)
        verify()
    if args.community_gguf:download(lock['community_gguf'],args.origin);verify(True)
    print('Pinned language sources verified; official assets requested='+str(args.download)+'; older community GGUF requested='+str(args.community_gguf)+'; no APK/model/phone acceptance')
