"""Fetch/revalidate pinned native code, without model or tokenizer downloads."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def validate_sources(lock):
    source=ROOT/'build/native-src/moss-tts-cpp'
    if not source.exists():
        subprocess.run(['git','clone','--filter=blob:none','--no-checkout',lock['repository'],str(source)],check=True)
        subprocess.run(['git','-C',str(source),'sparse-checkout','set','--cone','include','src','third_party','docs','tests','scripts'],check=True)
        subprocess.run(['git','-C',str(source),'checkout','--detach',lock['revision']],check=True)
        subprocess.run(['git','-C',str(source),'submodule','update','--init','--depth','1','third_party/ggml'],check=True)
    for folder,revision in [(source,lock['revision']),(source/'third_party/ggml',lock['ggml_revision'])]:
        head=subprocess.check_output(['git','-C',str(folder),'rev-parse','HEAD'],text=True).strip();dirty=subprocess.check_output(['git','-C',str(folder),'status','--porcelain'],text=True).strip()
        if head!=revision or dirty:raise RuntimeError('Pinned MOSS RQ/ggml source differs or is modified')
    for name,digest in lock['reviewed_files'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Reviewed RQ source changed: '+name)
    return source


if __name__=='__main__':print(validate_sources(json.loads((ROOT/'third_party/moss-rq-source-lock.json').read_text(encoding='utf-8'))))
