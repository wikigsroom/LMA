"""Verify or explicitly download the exact old LTX developer checkpoint.

Never invoked by tests, conversion, App installation/upgrades or browsing.
Model data stays under the ignored project build directory.
"""
import argparse,hashlib,json,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/ltx098-trained-assets.json'
DIRECTORY=ROOT/'build/ltx098-trained/originals'
CHUNK=64*1024*1024

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(4*1024*1024):digest.update(block)
    return digest.hexdigest()

def verify():
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['models']:
        path=DIRECTORY/item['file']
        if not path.is_file() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:
            raise RuntimeError('Explicitly prepare/verify the pinned checkpoint with fetch_ltx098_trained.py --download: '+item['file'])
    return lock

def download(item,origin):
    DIRECTORY.mkdir(parents=True,exist_ok=True);path=DIRECTORY/item['file']
    if path.exists():
        if path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise RuntimeError('Existing checkpoint differs; preserve for review')
        return
    partial=path.with_suffix('.part');receipt=path.with_suffix('.part.json')
    identity={k:item[k] for k in ['repo','revision','file','bytes','sha256']}
    if partial.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8'))!=identity:raise RuntimeError('Unknown partial file; preserve for review')
        if partial.stat().st_size>item['bytes']:raise RuntimeError('Partial exceeds pinned asset length')
    else:
        receipt.write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8');partial.touch(exist_ok=False)
    start=partial.stat().st_size
    if start<item['bytes']:
        start=start//CHUNK*CHUNK
        with partial.open('r+b') as stream:stream.truncate(start)
    while start<item['bytes']:
        end=min(start+CHUNK,item['bytes'])-1
        url=origin+'/'+item['repo']+'/resolve/'+item['revision']+'/'+item['file']+'?download=true&lma_range='+str(start)
        request=urllib.request.Request(url,headers={'Range':'bytes='+str(start)+'-'+str(end),'User-Agent':'LMA-explicit-old-LTX-developer-checkpoint/1'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request,timeout=45) as response:
                    expected='bytes '+str(start)+'-'+str(end)+'/'+str(item['bytes'])
                    if response.status!=206 or response.headers.get('Content-Range')!=expected:raise RuntimeError('Pinned range response differs')
                    position=start
                    with partial.open('r+b') as stream:
                        stream.seek(start);stream.truncate(start)
                        while position<=end:
                            block=response.read(min(1024*1024,end+1-position))
                            if not block:raise RuntimeError('Truncated checkpoint range')
                            stream.write(block);position+=len(block)
                        if response.read(1):raise RuntimeError('Checkpoint range exceeds pinned length')
                break
            except Exception:
                if attempt==2:raise
        start=end+1;print('Verified transfer range '+str(start)+' / '+str(item['bytes'])+' bytes; final SHA256 pending',flush=True)
    if partial.stat().st_size!=item['bytes'] or sha(partial)!=item['sha256']:raise RuntimeError('Full checkpoint SHA256 mismatch; partial retained')
    partial.rename(path);receipt.unlink();print('Pinned complete checkpoint SHA256 verified',flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true');parser.add_argument('--origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co');args=parser.parse_args()
    if args.download:
        for item in json.loads(LOCK.read_text(encoding='utf-8'))['models']:download(item,args.origin)
    verify();print('Old 0.9.8 checkpoint verified; no App assets or model support registered')

if __name__=='__main__':main()
