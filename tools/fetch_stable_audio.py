"""Fetch pinned code and CPU runtime only; never model repositories or vocabularies."""
import hashlib,io,json,subprocess,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def validate_sources(lock):
    for s in lock['sources']:
        p=ROOT/'build/native-src'/s['name']
        if not p.exists():
            subprocess.run(['git','clone','--filter=blob:none','--no-checkout',s['url'],str(p)],check=True)
            if s['name']=='arm-audiogen':subprocess.run(['git','-C',str(p),'sparse-checkout','set','--cone','kleidiai-examples/audiogen'],check=True)
            subprocess.run(['git','-C',str(p),'checkout','--detach',s['revision']],check=True)
        if subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()!=s['revision'] or subprocess.check_output(['git','-C',str(p),'status','--porcelain'],text=True).strip():raise RuntimeError('Pinned source modified: '+s['name'])
        for name,digest in s['reviewed_files'].items():
            if hashlib.sha256((p/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Reviewed source changed: '+name)
    return {s['name']:s['revision'] for s in lock['sources']}

def runtime(lock):
    s=lock['runtime'];cache=ROOT/'build/litert-probe';cache.mkdir(parents=True,exist_ok=True)
    def fetch(name,url,digest):
        p=cache/name
        if not p.exists():
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LMA-code-runtime-build/1'}),timeout=60) as response:data=response.read(100*1024*1024+1)
            if len(data)>100*1024*1024:raise RuntimeError('Runtime download too large')
            if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Official runtime archive hash differs')
            p.write_bytes(data)
        data=p.read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest:raise RuntimeError('Pinned runtime archive modified: '+name)
        return data
    aar=fetch('litert-2.2.0.aar',s['aar_url'],s['aar_sha256']);sdk=fetch('litert_cc_sdk.zip',s['sdk_url'],s['sdk_sha256'])
    # Re-extract verified bytes rather than trusting a possibly modified header cache.
    with zipfile.ZipFile(io.BytesIO(sdk)) as z:
        for item in z.infolist():
            p=(cache/item.filename).resolve()
            if not p.is_relative_to(cache.resolve()):raise RuntimeError('Unsafe SDK path')
            if not item.is_dir():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(item))
    with zipfile.ZipFile(io.BytesIO(aar)) as z:
        data=z.read('jni/arm64-v8a/libLiteRt.so')
        if len(data)!=s['bytes'] or hashlib.sha256(data).hexdigest()!=s['sha256']:raise RuntimeError('CPU runtime hash differs')
        (cache/s['file']).write_bytes(data)
    return cache

if __name__=='__main__':
    lock=json.loads((ROOT/'third_party/stable-audio-source-lock.json').read_text(encoding='utf-8'));print(validate_sources(lock));print(runtime(lock))
