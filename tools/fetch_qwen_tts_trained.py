"""Explicit developer acquisition of the exact frozen Qwen 0.6B Base GGUF recipe."""
import argparse
import json
from pathlib import Path
import re
import urllib.request

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/qwen-tts-trained/originals'
BUNDLE = 'qwen3_tts_06b_base_q4_rb7ee2e8'
CHUNK = 32*1024*1024


def inputs(): return fingerprint('tools/fetch_qwen_tts_trained.py','catalogue/model-bundles.json')


def selected():
    value=json.loads((ROOT/'catalogue/model-bundles.json').read_text(encoding='utf-8'))
    bundle=next(b for b in value['bundles'] if b['id']==BUNDLE)
    assert (bundle['engine'],bundle['pipeline'],bundle['backend'])==('qwen_tts_native','qwen3_tts_06b_base','cpu')
    assert [c['role'] for c in bundle['components']]==['talker','audio_codec'] and sum(c['bytes'] for c in bundle['components'])==920055680
    for c in bundle['components']:
        assert c['repository']=='Serveurperso/Qwen3-TTS-GGUF' and c['revision']=='b7ee2e8c7459c3bea99da23e3d178125a7d1713c'
        assert Path(c['path']).name==c['path'] and '\\' not in c['path'] and re.fullmatch('[A-Za-z0-9_.-]+[.]gguf',c['path'])
        assert re.fullmatch('[a-f0-9]{64}',c['sha256']) and c['bytes']>0
        assert c['url']=='https://huggingface.co/'+c['repository']+'/resolve/'+c['revision']+'/'+c['path']
    return bundle


def path_for(component): return DIRECTORY/component['path']


def verify():
    bundle=selected()
    for c in bundle['components']:
        p=path_for(c)
        if not p.is_file() or p.stat().st_size!=c['bytes'] or sha(p)!=c['sha256']:raise RuntimeError('Explicitly acquire pinned Qwen developer asset: '+c['role'])
    return bundle


def download(component,origin):
    path=path_for(component);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.stat().st_size!=component['bytes'] or sha(path)!=component['sha256']:raise ValueError('Preserve different existing Qwen asset')
        return
    partial=path.with_name(path.name+'.part');receipt=partial.with_name(partial.name+'.json')
    if partial.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8'))!=component or partial.stat().st_size>component['bytes']:raise ValueError('Preserve unknown/different partial')
    else:
        if receipt.exists():raise ValueError('Preserve orphan receipt')
        receipt.write_text(json.dumps(component,indent=2)+'\n',encoding='utf-8');partial.touch(exist_ok=False)
    start=partial.stat().st_size
    if start<component['bytes']:
        start=start//CHUNK*CHUNK
        with partial.open('r+b') as stream:stream.truncate(start)
    while start<component['bytes']:
        end=min(start+CHUNK,component['bytes'])-1
        url=origin+component['url'][len('https://huggingface.co'):]+'?download=true&lma_qwen_trained_range='+str(start)
        request=urllib.request.Request(url,headers={'User-Agent':'LMA-explicit-Qwen-trained-assets/1','Accept-Encoding':'identity','Range':f'bytes={start}-{end}'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request,timeout=45) as response:
                    if response.status!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{component["bytes"]}':raise ValueError('Different pinned transfer range')
                    with partial.open('r+b') as stream:
                        stream.seek(start);stream.truncate(start);position=start
                        while position<=end:
                            block=response.read(min(1024*1024,end+1-position))
                            if not block:raise ValueError('Truncated transfer')
                            stream.write(block);position+=len(block)
                        if response.read(1):raise ValueError('Transfer exceeds pinned size')
                break
            except Exception as error:
                print('Transfer retry',component['role'],attempt+1,type(error).__name__,flush=True)
                if attempt==2:raise RuntimeError('Pinned transfer failed; partial retained') from None
        start=end+1;print('Transferred',component['role'],start,'/',component['bytes'],flush=True)
    if partial.stat().st_size!=component['bytes'] or sha(partial)!=component['sha256']:raise ValueError('Different full-file SHA; preserve partial')
    partial.rename(path);receipt.unlink();print('Verified',component['role'],flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true')
    parser.add_argument('--hf-origin',choices=['https://huggingface.co','https://hf-mirror.com'],default='https://huggingface.co');args=parser.parse_args();before=inputs()
    if args.download:
        for component in selected()['components']:download(component,args.hf_origin)
    bundle=verify();current(before)
    if args.download:
        value=dict(schema='lma.qwen-tts-trained-assets/1',bundle_id=BUNDLE,explicit_download=True,download_origin=args.hf_origin,
            components=[dict(c,local_path=path_for(c).relative_to(ROOT).as_posix()) for c in bundle['components']],
            developer_assets_only=True,app_assets_modified=False,model_executed=False,input_fingerprint=before)
        path=DIRECTORY.parent/'receipt.json'
        if path.exists():
            old=json.loads(path.read_text(encoding='utf-8'));current(old['input_fingerprint'])
            if old['components']!=value['components']:raise ValueError('Preserve different acquisition receipt')
        else:path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print('Verified exact frozen Qwen 0.6B Base/12Hz codec; no App model installed',flush=True)


if __name__=='__main__':main()
