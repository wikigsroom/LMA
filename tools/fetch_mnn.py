"""Fetch only pinned MNN source code, never model data. Native Windows, no virtualization."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def validate_sources(lock):
    source = ROOT / 'build/native-src/mnn'
    def git(*args): return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
    if not source.exists():
        subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout', lock['repository'], str(source)], check=True)
        subprocess.run(['git', '-C', str(source), 'checkout', '--detach', lock['revision']], check=True)
    if git('rev-parse', 'HEAD') != lock['revision'] or git('status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Pinned MNN source revision differs or has tracked edits')
    return source

if __name__ == '__main__':
    lock = json.loads((ROOT / 'third_party/mnn-source-lock.json').read_text(encoding='utf-8'))
    print(validate_sources(lock))
