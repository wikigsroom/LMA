"""Fetch only hash-pinned Python reference code for offline shape export/checks."""
import argparse,base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/rf-shape-source-lock.json'

def verify(fetch=False):
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    for entry in lock['sources']:
        directory=ROOT/entry['directory']
        for name,digest in entry['files'].items():
            path=directory/name
            if not path.exists() and fetch:
                route='repos/'+entry['repository']+'/contents/'+name+'?ref='+entry['revision']
                gh=ROOT/'build/github-cli/gh.exe'
                if gh.exists():raw=subprocess.check_output([str(gh),'api',route],cwd=ROOT,timeout=40)
                else:
                    with urllib.request.urlopen('https://api.github.com/'+route,timeout=30) as response:raw=response.read(500000)
                value=json.loads(raw);assert value['type']=='file' and value['size']<300000
                data=base64.b64decode(value['content']);assert hashlib.sha256(data).hexdigest()==digest
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Changed reference source: '+name
    return lock

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');a=p.parse_args()
    value=verify(a.fetch);print(json.dumps(dict(repositories=len(value['sources']),trained_assets=0)))
