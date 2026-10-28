"""Verify pinned T5 research inputs; downloads require explicit command-line flags.

Never called by App installation, upgrades, browsing, builds, or tests. All model
and tokenizer bytes stay in the ignored project build directory.
"""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/ltx098-text-source-lock.json'
DIRECTORY=ROOT/'build/ltx098-text-assets'
CHUNK=64*1024*1024


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(4*1024*1024):digest.update(block)
    return digest.hexdigest()


def sources():
    lock=json.loads(LOCK.read_text(encoding='utf-8'));source=ROOT/'build/native-src'/lock['source']['name']
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if revision!=lock['source']['revision']:raise RuntimeError('Unexpected llama.cpp revision')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain','--untracked-files=no'],text=True).strip():raise RuntimeError('Modified native reference source')
    for name,expected in lock['source']['reviewed_files'].items():
        if sha(source/name)!=expected:raise RuntimeError('Changed reviewed source: '+name)
    if sha(ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp')!=lock['json_header_sha256']:raise RuntimeError('Changed JSON dependency')
    return lock


def assets(oracle=False):
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    selected=[(DIRECTORY/'originals',lock['model']),(DIRECTORY/'oracle',lock['runtime_tokenizer_config'])]
    if oracle:selected += [(DIRECTORY/'oracle',item) for item in lock['oracle_assets']]
    for directory,item in selected:
        file=directory/item['file']
        if not file.is_file() or file.stat().st_size!=item['bytes'] or sha(file)!=item['sha256']:
            raise RuntimeError('Explicitly prepare pinned external T5 assets: '+item['file'])
    return lock


def download(item,directory,origin):
    directory.mkdir(parents=True,exist_ok=True);path=directory/item['file']
    if path.exists():
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise RuntimeError('Existing asset differs; preserve for review')
        return
    partial=path.with_suffix('.part');receipt=path.with_suffix('.part.json')
    identity={k:item[k] for k in ['repo','revision','file','bytes','sha256']}
    if partial.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8'))!=identity or partial.stat().st_size>item['bytes']:
            raise RuntimeError('Unknown partial asset; preserve for review')
    else:receipt.write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8');partial.touch(exist_ok=False)
    start=partial.stat().st_size
    if start<item['bytes']:
        start=start//CHUNK*CHUNK
        with partial.open('r+b') as stream:stream.truncate(start)
    while start<item['bytes']:
        end=min(start+CHUNK,item['bytes'])-1
        request=urllib.request.Request(origin+'/'+item['repo']+'/resolve/'+item['revision']+'/'+item['file']+'?download=true&lma_range='+str(start),
            headers={'Range':f'bytes={start}-{end}','User-Agent':'LMA-explicit-T5-research/1'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request,timeout=45) as response:
                    ranged=response.status==206 and response.headers.get('Content-Range')==f'bytes {start}-{end}/{item["bytes"]}'
                    whole=response.status==200 and start==0 and end+1==item['bytes']
                    if not(ranged or whole):raise RuntimeError('Pinned range response differs')
                    position=start
                    with partial.open('r+b') as stream:
                        stream.seek(start);stream.truncate(start)
                        while position<=end:
                            block=response.read(min(1024*1024,end+1-position))
                            if not block:raise RuntimeError('Truncated asset range')
                            stream.write(block);position+=len(block)
                        if response.read(1):raise RuntimeError('Range exceeds pinned length')
                break
            except Exception:
                if attempt==2:raise
        start=end+1;print(f'T5 external asset {item["file"]}: {start}/{item["bytes"]} bytes; whole-file SHA256 pending',flush=True)
    if partial.stat().st_size!=item['bytes'] or sha(partial)!=item['sha256']:raise RuntimeError('Asset SHA256 differs; partial retained')
    partial.rename(path);receipt.unlink()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Explicitly download the pinned external quantized encoder')
    parser.add_argument('--oracle-assets',action='store_true',help='Also verify the four external Google reference assets')
    parser.add_argument('--download-oracle-assets',action='store_true',help='Explicitly download the four Google reference assets')
    parser.add_argument('--origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co');args=parser.parse_args()
    lock=sources()
    if args.download:
        download(lock['model'],DIRECTORY/'originals',args.origin)
        download(lock['runtime_tokenizer_config'],DIRECTORY/'oracle',args.origin)
    if args.download_oracle_assets:
        for item in lock['oracle_assets']:download(item,DIRECTORY/'oracle',args.origin)
    assets(args.oracle_assets or args.download_oracle_assets)
    print('Pinned external T5 research inputs verified; no download without explicit flags, no App registration')
