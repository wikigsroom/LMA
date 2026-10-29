"""Verify or explicitly acquire the official pinned Windows sherpa C API."""
import argparse
import json
from pathlib import Path
import tarfile
import urllib.request

from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/toolchain/sherpa-tts-host-2.0.1'


def selected():
    value = json.loads((ROOT / 'research/tts_host/runtime.json').read_text(encoding='utf-8'))
    if value['version'] != '2.0.1' or not value['host_only']: raise ValueError('Different reviewed host runtime')
    return value


def verify():
    value = selected()
    for name, item in value['files'].items():
        if Path(name).name != name or Path(name).suffix not in ['.dll', '.lib']: raise ValueError('Invalid runtime member')
        path = DIRECTORY / name
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly acquire reviewed host runtime: ' + name)
    return DIRECTORY, value


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--download', action='store_true'); args = parser.parse_args()
    value = selected(); item = value['archive']; path = DIRECTORY / item['file']; DIRECTORY.mkdir(parents=True, exist_ok=True)
    if args.download:
        if not path.exists():
            partial = path.with_name(path.name + '.part')
            if partial.exists(): raise RuntimeError('Preserve existing runtime partial')
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'LMA-explicit-sherpa-host/1'})
            with urllib.request.urlopen(request, timeout=45) as response, partial.open('xb') as stream:
                while block := response.read(1024*1024): stream.write(block)
            if partial.stat().st_size != item['bytes'] or sha(partial) != item['sha256']: raise ValueError('Different official runtime archive')
            partial.rename(path)
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']: raise ValueError('Preserve changed runtime archive')
        with tarfile.open(path) as archive:
            for name, expected in value['files'].items():
                member = archive.getmember(expected['member'])
                if not member.isfile() or member.size != expected['bytes']: raise ValueError('Different pinned archive member')
                data = archive.extractfile(member).read(); target = DIRECTORY / name
                import hashlib
                if hashlib.sha256(data).hexdigest() != expected['sha256']: raise ValueError('Different runtime member digest')
                if target.exists():
                    if target.read_bytes() != data: raise ValueError('Preserve changed runtime member')
                else: target.write_bytes(data)
    verify(); print('Official Windows sherpa 2.0.1 C API verified; no model/App/global runtime modified')


if __name__ == '__main__': main()
