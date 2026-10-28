"""Explicit preparation of pinned LTX098/Vulkan SOURCE CODE; never downloads weights."""
import argparse,hashlib,io,json,os,shutil,subprocess,sys,tarfile,tempfile,urllib.request,zipfile
from pathlib import Path
from build_ltx098 import ROOT,LOCK,validate_sources

ARCHIVES={
    'Lightricks/LTX-Video':'Lightricks/LTX-Video',
    'Vulkan-Headers':'KhronosGroup/Vulkan-Headers',
    'SPIRV-Headers':'KhronosGroup/SPIRV-Headers',
}

def prepare_shaderc(pin):
    target=ROOT/pin['directory']
    if target.exists():
        for name,digest in pin['files'].items():
            if not (target/name).is_file() or hashlib.sha256((target/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Pinned shaderc binary differs: '+name)
        return
    cache=ROOT/'build/toolchain/downloads/shaderc-20261026-windows.zip';cache.parent.mkdir(parents=True,exist_ok=True)
    if not cache.is_file() or cache.stat().st_size!=pin['archive_bytes'] or hashlib.sha256(cache.read_bytes()).hexdigest()!=pin['archive_sha256']:
        partial=cache.with_suffix('.partial')
        try:
            with urllib.request.urlopen(pin['archive_url'],timeout=45) as response,partial.open('wb') as stream:
                count=0;digest=hashlib.sha256()
                while chunk:=response.read(1024*1024):
                    count+=len(chunk)
                    if count>pin['archive_bytes']:raise RuntimeError('Oversized shaderc archive')
                    stream.write(chunk);digest.update(chunk)
            if count!=pin['archive_bytes'] or digest.hexdigest()!=pin['archive_sha256']:raise RuntimeError('Shaderc archive identity differs')
            partial.replace(cache)
        finally:partial.unlink(missing_ok=True)
    target.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.shaderc-',dir=target.parent))
    try:
        with zipfile.ZipFile(cache) as archive:
            for name,digest in pin['files'].items():
                destination=stage/name
                if not destination.resolve().is_relative_to(stage.resolve()):raise RuntimeError('Unsafe compiler path')
                entry=archive.getinfo('install/'+name)
                if entry.file_size>64*1024*1024:raise RuntimeError('Oversized compiler file')
                blob=archive.read(entry)
                if hashlib.sha256(blob).hexdigest()!=digest:raise RuntimeError('Compiler file identity differs')
                destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(blob)
        stage.rename(target)
    finally:
        if stage.exists():
            if stage.resolve().parent!=target.resolve().parent:raise RuntimeError('Unsafe compiler cleanup')
            shutil.rmtree(stage)

def prepare(source):
    target=ROOT/source['directory']
    if target.exists():return
    repo=ARCHIVES[source['name']]
    request=urllib.request.Request('https://api.github.com/repos/'+repo+'/tarball/'+source['revision'],headers={'User-Agent':'LMA-pinned-code-preparation/1'})
    with urllib.request.urlopen(request,timeout=45) as response:blob=response.read(64*1024*1024+1)
    if len(blob)>64*1024*1024 or hashlib.sha256(blob).hexdigest()!=source['archive_sha256']:raise RuntimeError('Source archive identity differs: '+source['name'])
    target.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.ltx-source-',dir=target.parent))
    try:
        with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as archive:
            entries=archive.getmembers()
            if len(entries)>5000 or sum(e.size for e in entries)>100*1024*1024:raise RuntimeError('Oversized source archive')
            for entry in entries:
                path=stage/Path(*Path(entry.name).parts[1:])
                if not path.resolve().is_relative_to(stage.resolve()) or entry.issym() or entry.islnk():raise RuntimeError('Unsafe source entry')
                if entry.isdir():path.mkdir(parents=True,exist_ok=True)
                elif entry.isfile():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(archive.extractfile(entry).read())
                else:raise RuntimeError('Unsupported source entry')
        for name,digest in source['files'].items():
            if not (stage/name).is_file() or hashlib.sha256((stage/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Source file identity differs: '+name)
        stage.rename(target)
    finally:
        if stage.exists():
            if stage.resolve().parent!=target.resolve().parent:raise RuntimeError('Unsafe temporary source cleanup')
            shutil.rmtree(stage)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--python-dependencies',action='store_true');args=parser.parse_args()
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    for source in lock['sources']:
        if source['name'] in ARCHIVES:prepare(source)
        elif not (ROOT/source['directory']).is_dir():raise RuntimeError('Prepare the pinned stable-diffusion.cpp/ggml code first with tools/fetch_native.py')
    validate_sources()
    prepare_shaderc(lock['shaderc_windows'])
    if args.python_dependencies:
        temp=ROOT/'build/ltx098-python-temp';temp.mkdir(exist_ok=True)
        env=dict(os.environ,TEMP=str(temp),TMP=str(temp),TMPDIR=str(temp))
        subprocess.run([sys.executable,'-m','pip','install','--no-deps','--target',str(ROOT/'build/soulx-python'),'--cache-dir',str(ROOT/'build/pip-cache'),'diffusers==0.29.2','einops==0.8.2'],check=True,env=env)
    print('Pinned LTX098/Vulkan code prepared; model weights/tokenizers were not downloaded. Host oracle dependencies stay under build/.')

if __name__=='__main__':main()
