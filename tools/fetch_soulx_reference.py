"""Explicit developer source preparation and OPTIONAL trained reference assets.

Default: validate/fetch pinned CODE only. --publisher-models is a separate,
explicit request for two trained reference components, never a user/App
prerequisite, APK payload or implicit download by export/testing.
"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
from fetch_soulx_dsp import validate_sources
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/soulx-reference-source-lock.json'


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def verify_models(lock,directory):
    for item in lock['publisher_models']:
        p=directory/item['file']
        if not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise RuntimeError('Missing/different trained reference asset; explicitly prepare with fetch_soulx_reference.py --publisher-models: '+item['file'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--publisher-models',action='store_true')
    parser.add_argument('--origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co')
    args=parser.parse_args();lock=json.loads(LOCK.read_text(encoding='utf-8'));validate_sources(lock)
    if not args.publisher_models:print('Pinned reference CODE verified; no trained assets requested');return
    directory=ROOT/'build/soulx-reference-models/originals';directory.mkdir(parents=True,exist_ok=True)
    for item in lock['publisher_models']:
        p=directory/item['file']
        if p.exists():
            if p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise RuntimeError('Existing reference asset differs; preserve it for review')
            continue
        partial=p.with_suffix('.part');url=args.origin+'/'+item['repo']+'/resolve/'+item['revision']+'/'+item['file']
        if partial.exists():raise RuntimeError('Inspect/remove this tool\'s incomplete partial before retry: '+str(partial.relative_to(ROOT)))
        digest=hashlib.sha256();size=0
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LMA-explicit-developer-reference-assets/1'}),timeout=60) as response,partial.open('xb') as target:
            while block:=response.read(1024*1024):
                size+=len(block)
                if size>item['bytes']:raise RuntimeError('Reference download exceeds pinned length')
                target.write(block);digest.update(block)
        if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise RuntimeError('Publisher reference identity mismatch; partial retained')
        partial.rename(p)
    verify_models(lock,directory);print('Two explicitly requested trained REFERENCE components verified; no complete SoulX/phone acceptance and nothing added to APK')

if __name__=='__main__':main()
