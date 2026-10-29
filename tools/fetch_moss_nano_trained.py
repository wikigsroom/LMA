"""Explicitly acquire pinned Nano developer assets; never called by App or tests."""
import argparse
import json
import re
from pathlib import Path, PurePosixPath
import urllib.request

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/moss-nano-trained/originals'
CHUNK = 32 * 1024 * 1024


def inputs():
    return fingerprint('tools/fetch_moss_nano_trained.py', 'research/moss_nano_trained/assets.json')


def selected():
    value = json.loads((ROOT / 'research/moss_nano_trained/assets.json').read_text(encoding='utf-8'))
    seen = set()
    for item in value['components']:
        path = PurePosixPath(item['path'])
        if (len(path.parts) != 1 or path.is_absolute() or '..' in path.parts or '\\' in item['path']
            or item['bytes'] <= 0 or item['role'] in seen
            or not re.fullmatch('[a-f0-9]{40}', item['revision'])
            or not re.fullmatch('[a-f0-9]{64}', item['sha256'])
            or not re.fullmatch(r'OpenMOSS-Team/[A-Za-z0-9_.-]+', item['repository'])):
            raise ValueError('Unpinned or unsafe Nano component')
        seen.add(item['role'])
        if item['url'] != 'https://huggingface.co/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']:
            raise ValueError('Different pinned URL')
    if len(seen) != 11: raise ValueError('Different complete Nano component set')
    return value


def path_for(item):
    return DIRECTORY / ('codec' if item['role'].startswith('codec_') else 'tts') / item['path']


def verify():
    lock = selected()
    for item in lock['components']:
        path = path_for(item)
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly acquire the pinned developer asset: ' + item['role'])
    return lock


def download(item, origin):
    path = path_for(item); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']: raise RuntimeError('Preserve changed existing asset')
        return
    partial = path.with_name(path.name + '.part'); record = partial.with_name(partial.name + '.json')
    identity = {key: item[key] for key in ['role', 'repository', 'revision', 'path', 'bytes', 'sha256']}
    if partial.exists():
        if not record.is_file() or json.loads(record.read_text(encoding='utf-8')) != identity or partial.stat().st_size > item['bytes']:
            raise RuntimeError('Preserve partial with a different identity')
    else:
        if record.exists(): raise RuntimeError('Preserve orphan partial receipt')
        record.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8'); partial.touch(exist_ok=False)
    start = partial.stat().st_size
    if start < item['bytes']:
        start = start // CHUNK * CHUNK
        with partial.open('r+b') as stream: stream.truncate(start)
    while start < item['bytes']:
        end = min(start + CHUNK, item['bytes']) - 1
        url = origin + '/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path'] + '?download=true&lma_range=' + str(start)
        request = urllib.request.Request(url, headers={'User-Agent': 'LMA-explicit-Nano-developer-assets/1', 'Range': f'bytes={start}-{end}'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    ranged = response.status == 206 and response.headers.get('Content-Range') == f'bytes {start}-{end}/{item["bytes"]}'
                    whole = response.status == 200 and start == 0 and end == item['bytes'] - 1
                    if not (ranged or whole): raise RuntimeError('Unexpected transfer range')
                    with partial.open('r+b') as stream:
                        stream.seek(start); stream.truncate(start); position = start
                        while position <= end:
                            block = response.read(min(1024 * 1024, end + 1 - position))
                            if not block: raise RuntimeError('Truncated range')
                            stream.write(block); position += len(block)
                        if response.read(1): raise RuntimeError('Range exceeds pinned length')
                break
            except Exception as error:
                print('Transfer retry', item['role'], attempt + 1, type(error).__name__, flush=True)
                if attempt == 2: raise RuntimeError('Pinned transfer failed; partial preserved') from None
        start = end + 1
        print('Transferred', item['role'], start, '/', item['bytes'], 'bytes; SHA256 pending', flush=True)
    if partial.stat().st_size != item['bytes'] or sha(partial) != item['sha256']: raise RuntimeError('Complete SHA256 differs; preserve partial')
    partial.rename(path); record.unlink(); print('Verified', item['role'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    args = parser.parse_args(); before = inputs(); lock = selected()
    if args.download:
        for item in lock['components']: download(item, args.origin)
    verify(); current(before)
    if args.download:
        report = dict(schema='lma.moss-nano-trained-assets/1', explicit_download=True, download_origin=args.origin,
                      components=[dict(item, local_path=path_for(item).relative_to(ROOT).as_posix()) for item in lock['components']],
                      developer_assets_only=True, model_executed=False, app_assets_modified=False, input_fingerprint=before)
        receipt = DIRECTORY.parent / 'receipt.json'
        if receipt.exists():
            existing = json.loads(receipt.read_text(encoding='utf-8')); current(existing['input_fingerprint'])
            if existing['components'] != report['components']: raise RuntimeError('Preserve different acquisition receipt')
        else: receipt.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('All 11 pinned Nano developer assets verified; no App model installed', flush=True)


if __name__ == '__main__': main()
