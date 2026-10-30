"""Explicit acquisition/verification of the pinned thirteen Sana developer assets.

No download without --download. Never invoked by the App or by inference/tests.
All learned data stays ignored under build/; the public lock contains metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import urllib.request

from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/mnn-trained/originals'
LOCK = 'research/mnn_trained/assets.json'
CHUNK = 32 * 1024 * 1024


def inputs():
    return fingerprint('tools/fetch_mnn_trained.py', LOCK)


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def assets():
    lock = json.loads((ROOT / LOCK).read_text(encoding='utf-8'))
    if lock['schema'] != 'lma.mnn-trained-assets/1' or len(lock['components']) != 13:
        raise ValueError('Different Sana asset contract')
    seen = set()
    for item in lock['components']:
        name = PurePosixPath(item['path'])
        if name.is_absolute() or '..' in name.parts or '\\' in item['path'] or item['path'] in seen:
            raise ValueError('Invalid or duplicate asset path')
        seen.add(item['path'])
        if item['repository'] != lock['repository'] or item['revision'] != lock['revision']:
            raise ValueError('Mixed source identity')
        if not re.fullmatch(r'[a-f0-9]{40}', item['revision']) or not re.fullmatch(r'[a-f0-9]{64}', item['sha256']) or item['bytes'] < 1:
            raise ValueError('Unpinned asset')
        if item['url'] != 'https://huggingface.co/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']:
            raise ValueError('Different source URL')
    return lock


def asset_path(item):
    return DIRECTORY / item['path']


def verify():
    lock = assets()
    for item in lock['components']:
        path = asset_path(item)
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly acquire the pinned developer asset: ' + item['role'])
    return lock


def download(item, origin, user_agent='LMA-explicit-Sana-developer-assets/1'):
    path = asset_path(item); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Preserve changed existing developer asset: ' + item['role'])
        return
    part = path.with_name(path.name + '.part'); record = part.with_name(part.name + '.json')
    identity = {key: item[key] for key in ('role', 'repository', 'revision', 'path', 'bytes', 'sha256')}
    if part.exists():
        if not record.is_file() or json.loads(record.read_text(encoding='utf-8')) != identity or part.stat().st_size > item['bytes']:
            raise RuntimeError('Unknown partial asset; preserve for review')
    else:
        record.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8'); part.touch(exist_ok=False)
    start = part.stat().st_size
    if start < item['bytes']:
        start = start // CHUNK * CHUNK
        with part.open('r+b') as stream: stream.truncate(start)
    while start < item['bytes']:
        end = min(start + CHUNK, item['bytes']) - 1
        url = origin + '/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path'] + '?download=true&lma_range=' + str(start)
        request = urllib.request.Request(url, headers={'Range': 'bytes=%d-%d' % (start, end), 'User-Agent': user_agent})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    ranged = response.status == 206 and response.headers.get('Content-Range') == 'bytes %d-%d/%d' % (start, end, item['bytes'])
                    whole = response.status == 200 and start == 0 and end == item['bytes'] - 1
                    if not (ranged or whole): raise RuntimeError('Unexpected pinned transfer range')
                    with part.open('r+b') as stream:
                        stream.seek(start); stream.truncate(start); position = start
                        while position <= end:
                            block = response.read(min(1024 * 1024, end + 1 - position))
                            if not block: raise RuntimeError('Truncated asset range')
                            stream.write(block); position += len(block)
                        if response.read(1): raise RuntimeError('Asset range exceeds bound')
                break
            except Exception as error:
                print('Transfer retry', item['role'], attempt + 1, type(error).__name__, flush=True)
                if attempt == 2: raise RuntimeError('Transfer failed; partial retained') from None
        start = end + 1
        print('Transferred', item['role'], start, '/', item['bytes'], flush=True)
    if part.stat().st_size != item['bytes'] or sha(part) != item['sha256']:
        raise RuntimeError('Asset SHA256 differs; partial retained')
    part.rename(path); record.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    args = parser.parse_args(); before = inputs(); lock = assets()
    if args.download:
        for item in lock['components']: download(item, args.origin)
    verify(); current(before)
    report = dict(schema='lma.mnn-trained-acquisition/1', components=lock['components'],
                  developer_assets_only=True, bundled_model_data=False, model_executed=False,
                  explicit_download=args.download, download_origin=args.origin if args.download else None,
                  input_fingerprint=before)
    (DIRECTORY.parent / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'verified_assets': 13, 'bytes': sum(i['bytes'] for i in lock['components']), 'model_executed': False}))


if __name__ == '__main__': main()
