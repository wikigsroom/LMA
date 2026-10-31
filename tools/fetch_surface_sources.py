"""Code-only pinned source acquisition for original adaptive surface routes."""
import argparse,base64,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/surface-source-lock.json'
SOURCES=[dict(id='DISO',repository='SarahWeiii/diso',revision='9792ad928ccb09bdec938779651ee03e395758a6',directory='build/surface-source-review/DISO',
              paths=['LICENSE','src/cudualmc.cu','src/cudualmc.h','src/cumc.cu','src/cumc.h','diso/__init__.py']),
         dict(id='LEWINER',repository='scikit-image/scikit-image',revision='51b3367761a52ab9111bdbd9537272d7dd2eccde',directory='build/surface-source-review/LEWINER',
              paths=['LICENSE.txt','tools/precompute/mc_meta/MarchingCubes.cpp','tools/precompute/mc_meta/LookUpTable.h','tools/precompute/mc_meta/README.md']),
         dict(id='LEWINER_CPP',repository='neurolabusc/LewinerMarchingCubes',revision='23642e6716c77ac15a2c2349b5125d605ac76234',directory='build/surface-source-review/LEWINER_CPP',
              paths=['LICENSE','cpp/lookuptable.h','cpp/marchingcubes.cpp','cpp/marchingcubes.h']),
         dict(id='RF_TRIPO',repository='VAST-AI-Research/TripoSG',revision='fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c',directory='build/surface-source-review/RF_TRIPO',paths=['triposg/inference_utils.py']),
         dict(id='RF_PART',repository='wgsxm/PartCrafter',revision='3d773bf02fad51c7ab31a5615573fec93b287b30',directory='build/surface-source-review/RF_PART',paths=['src/utils/inference_utils.py'])]


def verify(fetch=False):
    lock=json.loads(LOCK.read_text('utf-8')) if LOCK.exists() else dict(schema='lma.surface-sources/1',sources=[])
    for spec in SOURCES:
        old=next((s for s in lock['sources'] if s['id']==spec['id']),None);files={}
        if old is not None:
            assert all(old[k]==v for k,v in spec.items() if k!='paths'),'Surface source identity changed'
            assert set(old['files'])==set(spec['paths']),'Surface source file set changed'
        else:assert fetch,'Explicit source preparation required'
        for name in spec['paths']:
            assert not name.endswith('.header.json')
            file=ROOT/spec['directory']/name
            if not file.exists() and fetch:
                value=json.loads(subprocess.check_output([str(ROOT/'build/github-cli/gh.exe'),'api','repos/'+spec['repository']+'/contents/'+name+'?ref='+spec['revision']],timeout=40))
                assert value['type']=='file' and value['size']<500000
                data=base64.b64decode(value['content']);assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==value['sha']
                file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
            assert file.is_file(),name
            digest=hashlib.sha256(file.read_bytes()).hexdigest()
            if old is not None:assert old['files'][name]==digest,('Changed surface source',name)
            files[name]=digest
        if old is None:lock['sources'].append({k:v for k,v in spec.items() if k!='paths'}|dict(files=files))
    if fetch:LOCK.write_text(json.dumps(lock,indent=2)+'\n','utf-8')
    return lock


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fetch',action='store_true');a=p.parse_args();print(json.dumps(dict(repositories=len(verify(a.fetch)['sources']),modelDownloads=0)))
