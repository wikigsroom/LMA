"""Fetch/read one immutable source file, never weights or installation code."""
import argparse
import hashlib
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
REVISION='75fbf0183001ed9876c8dbb35de6b68552ee08bd'
GIT_BLOB='7cf1397e58e42b9d66b2230f5b3d55fee708514d'
SHA256='112bd474d580f279ac196129f7989df6fdafa7ed7e08c350f2b386553e73e17d'
FILE='o-voxel/o_voxel/convert/flexible_dual_grid.py'
PATH=ROOT/'build/spatial-source-review/blobs'/GIT_BLOB


def source(fetch=False):
    if not PATH.is_file():
        assert fetch,'Fetch the explicit pinned FDG source with tools/fdg_reference.py --fetch'
        url=f'https://raw.githubusercontent.com/microsoft/TRELLIS.2/{REVISION}/{FILE}'
        with urllib.request.urlopen(url,timeout=35) as response:data=response.read(1024*1024+1)
        assert len(data)<=1024*1024 and hashlib.sha256(data).hexdigest()==SHA256
        PATH.parent.mkdir(parents=True,exist_ok=True);PATH.write_bytes(data)
    data=PATH.read_bytes()
    assert hashlib.sha256(data).hexdigest()==SHA256
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==GIT_BLOB
    return data.decode('utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');a=p.parse_args()
    source(a.fetch);print('Pinned inference FDG source verified; no model assets acquired')
