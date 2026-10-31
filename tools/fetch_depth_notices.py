"""Explicit pinned code-license acquisition; no models or executable installers."""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/depth-notice-lock.json'
SOURCES=[('MoGe','microsoft/MoGe','74fbce054ebed49800de42d0ad0e83495065719a','LICENSE'),('DA3','ByteDance-Seed/Depth-Anything-3','3d835ec1a5802d64a8b8b15f817a1ab54809bfe4','LICENSE'),('timm','huggingface/pytorch-image-models','78c3724f4545c0067d0b4d2f7df6337196be01ce','LICENSE')]


def verify(fetch=False):
    old=json.loads(LOCK.read_text('utf-8')) if LOCK.exists() else None;items=[]
    for name,repo,revision,path in SOURCES:
        target=ROOT/'third_party/notices'/('expansion-spatial-'+name+'-LICENSE.txt')
        if not target.exists():
            assert fetch,'Explicitly fetch pinned code notices first'
            value=json.loads(subprocess.check_output([str(ROOT/'build/github-cli/gh.exe'),'api','repos/'+repo+'/contents/'+path+'?ref='+revision],timeout=40));data=base64.b64decode(value['content']);assert len(data)<=100000 and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==value['sha'];target.write_bytes(data)
        items.append(dict(repository=repo,revision=revision,path=path,file=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    record=dict(schema='lma.code-notices/1',sources=items)
    if old is None:assert fetch;LOCK.write_text(json.dumps(record,indent=2)+'\n','utf-8')
    else:assert old==record,'Changed pinned code notice'
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');a=p.parse_args();print(json.dumps(dict(notices=len(verify(a.fetch)['sources']),models=0)))
