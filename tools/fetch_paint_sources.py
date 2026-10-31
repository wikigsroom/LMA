"""Restore three SHA-locked BasicSR source/license files, never model assets."""
import base64,hashlib,json,urllib.request
from spatial_reference import ROOT
from paint_reference import verify


def main():
    lock=json.loads((ROOT/'third_party/paint-source-lock.json').read_text('utf-8'))
    for item in lock['files']:
        p=ROOT/lock['directory']/item['path']
        if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']:continue
        assert item['url'].startswith('https://api.github.com/repos/XPixelGroup/BasicSR/contents/')
        with urllib.request.urlopen(urllib.request.Request(item['url'],headers={'User-Agent':'LMA-source-review'}),timeout=45) as r:raw=r.read(2*1024*1024+1)
        assert len(raw)<=2*1024*1024
        data=base64.b64decode(json.loads(raw)['content'])
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    verify();print('Verified three code/license files; no model downloads or installers.')


if __name__=='__main__':main()
