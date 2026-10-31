"""Fetch only fixed automatic foreground code, never weights or installers."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='xuebinqin/DIS'
REVISION='b6764e20381f6f42a70f83fa3324181529ed1403'
FILES=('IS-Net/models/isnet.py','IS-Net/Inference.py','LICENSE.md')
DIRECTORY=ROOT/'build/vision-source-review/DIS'
LOCK=ROOT/'third_party/vision-source-lock.json'


def verify(fetch=False):
    record=json.loads(LOCK.read_text('utf-8')) if LOCK.exists() else None
    if record:assert record['repository']==REPOSITORY and record['revision']==REVISION and set(record['files'])==set(FILES)
    entries={}
    for name in FILES:
        assert not name.endswith('.header.json')
        file=DIRECTORY/name
        if not file.exists():
            assert fetch,'Fetch the selected fixed source first'
            raw=subprocess.check_output([str(ROOT/'build/github-cli/gh.exe'),'api','repos/'+REPOSITORY+'/contents/'+name+'?ref='+REVISION],cwd=ROOT,timeout=45)
            value=json.loads(raw);assert value['type']=='file' and value['size']<=300000
            data=base64.b64decode(value['content']);blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();assert blob==value['sha']
            file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
        assert file.is_file() and not file.is_symlink();data=file.read_bytes();entry=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        if record:assert record['files'][name]==entry,'Changed pinned foreground source: '+name
        entries[name]=entry
    value=dict(schema='lma.vision-source/1',repository=REPOSITORY,revision=REVISION,directory=DIRECTORY.relative_to(ROOT).as_posix(),files=entries)
    if record is None:
        assert fetch;LOCK.write_text(json.dumps(value,indent=2)+'\n','utf-8')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');a=p.parse_args();r=verify(a.fetch);print(json.dumps(dict(repository=r['repository'],files=len(r['files']),trainedAssets=0)))
