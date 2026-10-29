"""Verify or explicitly download the pinned Windows-only ORT test runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/toolchain/moss-nano-ort-1.28.0'


def selected():
    record = json.loads((ROOT / 'research/moss_nano_host/runtime.json').read_text(encoding='utf-8'))
    if record['version'] != '1.28.0' or record['api'] != 28 or not record['host_only']:
        raise ValueError('Different reviewed Windows test runtime')
    if not record['archive']['url'].startswith('https://files.pythonhosted.org/packages/'):
        raise ValueError('Different official runtime origin')
    return record


def verify():
    record = selected()
    for name, expected in record['files'].items():
        if Path(name).name != name or not name.endswith('.dll'): raise ValueError('Invalid runtime filename')
        path = DIRECTORY / name
        if not path.is_file() or path.stat().st_size != expected['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']:
            raise RuntimeError('Explicitly acquire the pinned Windows test runtime')
    return DIRECTORY, record


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--download', action='store_true'); args = parser.parse_args()
    record = selected(); archive = record['archive']; DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = DIRECTORY / archive['file']
    if args.download:
        if not path.exists():
            partial = path.with_name(path.name + '.part')
            if partial.exists(): raise RuntimeError('Preserve an earlier partial runtime download')
            with partial.open('xb') as stream:
                for start in range(0, archive['bytes'], 1024 * 1024):
                    end = min(start + 1024 * 1024, archive['bytes']) - 1
                    request = urllib.request.Request(archive['url'], headers={'Range': f'bytes={start}-{end}',
                        'User-Agent': 'LMA-explicit-Nano-host-runtime/1'})
                    with urllib.request.urlopen(request, timeout=20) as response:
                        if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{archive["bytes"]}':
                            raise RuntimeError('Unexpected runtime archive range')
                        data = response.read(end - start + 2)
                        if len(data) != end - start + 1: raise RuntimeError('Truncated runtime archive range')
                        stream.write(data)
            if partial.stat().st_size != archive['bytes'] or hashlib.sha256(partial.read_bytes()).hexdigest() != archive['sha256']:
                raise RuntimeError('Different official runtime archive; preserve partial')
            partial.rename(path)
        if path.stat().st_size != archive['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != archive['sha256']:
            raise RuntimeError('Changed existing runtime archive')
        with zipfile.ZipFile(path) as contents:
            for name, expected in record['files'].items():
                data = contents.read('onnxruntime/capi/' + name)
                if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']: raise ValueError('Changed runtime member')
                target = DIRECTORY / name
                if target.exists():
                    if target.read_bytes() != data: raise ValueError('Preserve changed runtime DLL')
                else: target.write_bytes(data)
    verify(); print('Pinned Windows ORT 1.28.0/API28 verified; Android ORT 1.28.2 and system Python unchanged')


if __name__ == '__main__': main()
