"""Explicit code-only SoulX DSP dependencies and optional host reference wheels.

No trained checkpoints or Android execution payloads. Code checkouts can include
upstream test fixtures; none are App assets or public source attachments.
"""
import argparse, hashlib, json, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'third_party/soulx-dsp-source-lock.json'


def validate_sources(lock):
    for source in lock['sources']:
        path = ROOT / 'build/native-src' / source['name']
        if not path.exists():
            subprocess.run(['git', 'clone', '--no-checkout', source['url'], str(path)], check=True)
            subprocess.run(['git', '-C', str(path), 'checkout', '--detach', source['revision']], check=True)
        if subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip() != source['revision']:
            raise RuntimeError('Wrong SoulX dependency revision: ' + source['name'])
        if subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain'], text=True).strip():
            raise RuntimeError('Modified SoulX reference checkout: ' + source['name'])
        for name, digest in source['reviewed_files'].items():
            if hashlib.sha256((path / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError('Modified SoulX reviewed file: ' + name)


def test_references(lock):
    cache = ROOT / 'build/soulx-reference'; cache.mkdir(parents=True, exist_ok=True)
    # Archive extraction is allowlisted and bounded. Do not import torchaudio's
    # native extension: its binary ABI need not match the host's PyTorch version.
    for wheel in lock['test_wheels']:
        path = cache / wheel['filename']
        if not path.exists():
            subprocess.run([sys.executable, '-m', 'pip', 'download', '--no-deps', '--dest', str(cache),
                            '--cache-dir', str(ROOT / 'build/pip-cache'), wheel['package']+'=='+wheel['version'],
                            '--platform', 'win_amd64' if wheel['package']=='torchaudio' else 'any',
                            '--python-version', '313', '--implementation', 'cp', '--abi', 'cp313'], check=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != wheel['sha256']:
            raise RuntimeError('Pinned SoulX test reference archive differs: ' + path.name)
        with zipfile.ZipFile(path) as archive:
            for name, digest in wheel['reviewed_files'].items():
                info = archive.getinfo(name)
                if info.file_size > 1024*1024: raise RuntimeError('Reference source too large')
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != digest: raise RuntimeError('Test reference source changed')
                target = cache / wheel['package'] / name
                if not target.resolve().is_relative_to(cache.resolve()): raise RuntimeError('Unsafe reference path')
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    return cache


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--test-references', action='store_true'); args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding='utf-8')); validate_sources(lock)
    if args.test_references: test_references(lock)
    print('Pinned SoulX DSP code verified; no trained checkpoints fetched')
