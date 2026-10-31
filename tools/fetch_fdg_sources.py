"""Acquire immutable CPU source dependencies; never acquire model assets.

Default mode verifies the existing cache. --fetch explicitly obtains missing
Git blobs and the fixed Eigen checkout. No publisher installer is executed.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
EIGEN='3147391d946bb4b6c68edd901f2add6ac1f31f8c'
TRELLIS='75fbf0183001ed9876c8dbb35de6b68552ee08bd'
BLOBS={
 'fdg_python':('microsoft/TRELLIS.2','7cf1397e58e42b9d66b2230f5b3d55fee708514d'),
 'fdg_cpu':('microsoft/TRELLIS.2','ad89edc01d1efb9d2644f251560c60de243cb1dd'),
 'fdg_license':('microsoft/TRELLIS.2','79656060de00aa4659ad2c276d5be8830664d544'),
 'volume_cuda':('JeffreyXiang/FlexGEMM','165c09863c4db66137fc460c62008a08ff95c501'),
 'volume_reference':('JeffreyXiang/FlexGEMM','225ca3e22980c53091f2e4b5878c7d1a910ff1fb'),
 'volume_wrapper':('JeffreyXiang/FlexGEMM','41db3eeb103f3d8ba212ec958e041d297ccfb08b'),
 'volume_license':('JeffreyXiang/FlexGEMM','d0f96cd8065cf767fabfd0b813933aa75f26cded'),
}


def verify(fetch=False):
    directory=ROOT/'build/spatial-source-review/blobs';records={}
    for label,(repository,blob) in BLOBS.items():
        path=directory/blob
        if not path.exists():
            assert fetch,'Missing source '+label+'; run tools/fetch_fdg_sources.py --fetch'
            url=f'https://api.github.com/repos/{repository}/git/blobs/{blob}'
            request=urllib.request.Request(url,headers={'User-Agent':'LMA-source-preparation','Accept':'application/vnd.github+json'})
            with urllib.request.urlopen(request,timeout=40) as response:value=json.loads(response.read(4*1024*1024))
            assert value['sha']==blob and value['encoding']=='base64'
            data=base64.b64decode(value['content']);assert len(data)==value['size']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
            directory.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        data=path.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==blob
        records[label]=dict(repository=repository,git_blob=blob,path=path.relative_to(ROOT).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    eigen=ROOT/'build/native-src/eigen-fdg'
    if not eigen.exists():
        assert fetch,'Missing fixed Eigen source; run tools/fetch_fdg_sources.py --fetch'
        eigen.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['git','clone','--no-checkout','https://github.com/eigen-mirror/eigen.git',str(eigen)],check=True)
        subprocess.run(['git','-C',str(eigen),'checkout','--detach',EIGEN],check=True)
    assert subprocess.check_output(['git','-C',str(eigen),'rev-parse','HEAD'],text=True).strip()==EIGEN
    assert not subprocess.check_output(['git','-C',str(eigen),'status','--porcelain','--untracked-files=no'],text=True).strip()
    record=dict(schema='lma.fdg-source-lock/1',trellis_revision=TRELLIS,eigen_revision=EIGEN,
        eigen_repository='eigen-mirror/eigen',eigen_policy=['EIGEN_MPL2_ONLY','EIGEN_DONT_PARALLELIZE'],sources=records,
        assets='source_code_only',trained_models=False)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fetch',action='store_true');args=parser.parse_args()
    record=verify(args.fetch);(ROOT/'third_party/fdg-source-lock.json').write_text(json.dumps(record,indent=2)+'\n','utf-8')
    print(json.dumps(dict(sources=len(record['sources']),eigen=EIGEN,model_assets=False)))


if __name__=='__main__':main()
