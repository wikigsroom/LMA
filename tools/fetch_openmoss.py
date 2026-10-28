"""Validate/fetch reviewed native code only; never fetch or convert model assets."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def validate_sources(lock):
    source=ROOT/'build/native-src/openmoss'
    if not source.exists():
        subprocess.run(['git','clone','--filter=blob:none','--no-checkout',lock['repository'],str(source)],check=True)
        subprocess.run(['git','-C',str(source),'sparse-checkout','set','--cone','include','src','third_party','docs','scripts','tests'],check=True)
        subprocess.run(['git','-C',str(source),'checkout','--detach',lock['revision']],check=True)
        subprocess.run(['git','-C',str(source),'submodule','update','--init','--depth','1','third_party/llama.cpp'],check=True)
    for folder,revision in [(source,lock['revision']),(source/'third_party/llama.cpp',lock['llama_revision'])]:
        head=subprocess.check_output(['git','-C',str(folder),'rev-parse','HEAD'],text=True).strip()
        dirty=subprocess.check_output(['git','-C',str(folder),'status','--porcelain'],text=True).strip()
        if head!=revision or dirty:raise RuntimeError('Pinned openmoss/llama source differs or has local changes')
    for name,digest in lock['reviewed_files'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Reviewed openmoss file changed: '+name)
    return source


def sound_primitives(source):
    """Reviewed CPU-only formatting, noise and solver schedule; no graph/model APIs."""
    text=(source/'src/soundeffect.cpp').read_text(encoding='utf-8')
    result=text[text.index('std::string whitespace_clean('):text.index('// Run the Qwen3 text encoder')]
    if any(s in result for s in ('llama_', 'ggml_', 'Model &', 'int main(')):
        raise RuntimeError('SoundEffect primitive extraction crossed a graph boundary')
    return result


if __name__=='__main__':
    print(validate_sources(json.loads((ROOT/'third_party/openmoss-source-lock.json').read_text(encoding='utf-8'))))
