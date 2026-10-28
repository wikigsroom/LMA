"""Fetch pinned native Qwen/ggml source only. Never download or convert model data."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate_sources(lock):
    source = ROOT / 'build/native-src/qwen3-tts'
    if not source.exists():
        subprocess.run(['git', 'clone', '--filter=blob:none', '--no-checkout', lock['repository'], str(source)], check=True)
        subprocess.run(['git', '-C', str(source), 'sparse-checkout', 'set', 'src', 'shared', 'ggml'], check=True)
        subprocess.run(['git', '-C', str(source), 'checkout', '--detach', lock['revision']], check=True)
    if not (source / 'ggml/include/ggml.h').is_file():
        subprocess.run(['git', '-C', str(source), 'submodule', 'update', '--init', '--depth', '1', 'ggml'], check=True)
    for directory, revision in [(source, lock['revision']), (source/'ggml', lock['ggml_revision'])]:
        head = subprocess.check_output(['git', '-C', str(directory), 'rev-parse', 'HEAD'], text=True).strip()
        dirty = subprocess.check_output(['git', '-C', str(directory), 'status', '--porcelain'], text=True).strip()
        if head != revision or dirty: raise RuntimeError('Pinned Qwen/ggml checkout differs or has local files')
    actual = sorted(p.relative_to(source).as_posix() for p in (source/'src').rglob('*.cpp') if p.name not in ('main.cpp','qwen3_tts_jni.cpp','qwen3_tts_quantize.cpp','qwen3_tts_c.cpp'))
    if actual != lock['compiled_sources']: raise RuntimeError('Reviewed Qwen compilation source list changed')
    return source


if __name__ == '__main__':
    print(validate_sources(json.loads((ROOT/'third_party/qwen-tts-source-lock.json').read_text(encoding='utf-8'))))
