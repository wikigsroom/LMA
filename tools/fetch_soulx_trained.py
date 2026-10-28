"""Verify or explicitly download the two developer-only acoustic checkpoints.

Never called by the App, a test, export, startup, upgrade or model browsing.
"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
from fetch_soulx_reference import sha
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/soulx-trained-assets.json'
DIRECTORY=ROOT/'build/soulx-trained-acoustic/originals'


def verify():
    record=json.loads(LOCK.read_text(encoding='utf-8'))
    for item in record['models']:
        p=DIRECTORY/item['file']
        if not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise RuntimeError('Missing/different acoustic checkpoint; explicitly use fetch_soulx_trained.py --download: '+item['file'])
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true')
    parser.add_argument('--origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co');args=parser.parse_args()
    if args.download:
        DIRECTORY.mkdir(parents=True,exist_ok=True)
        for item in json.loads(LOCK.read_text(encoding='utf-8'))['models']:
            p=DIRECTORY/item['file']
            if p.exists():
                if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise RuntimeError('Existing checkpoint differs; preserve for review')
                continue
            partial=p.with_suffix('.part');url=args.origin+'/'+item['repo']+'/resolve/'+item['revision']+'/'+item['file']
            if partial.exists():raise RuntimeError('Inspect this tool\'s incomplete partial before retry')
            digest=hashlib.sha256();size=0
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LMA-explicit-developer-acoustic-assets/1'}),timeout=60) as response,partial.open('xb') as target:
                while block:=response.read(1024*1024):
                    size+=len(block)
                    if size>item['bytes']:raise RuntimeError('Acoustic asset exceeds pinned length')
                    target.write(block);digest.update(block)
            if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise RuntimeError('Acoustic asset hash mismatch; partial retained')
            partial.rename(p)
    verify();print('Two trained acoustic components verified; no complete text-to-speech/phone evidence, no APK model assets')

if __name__=='__main__':main()
