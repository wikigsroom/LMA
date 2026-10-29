"""Explicit developer-only acquisition of the exact App SD1.5 bundle.

Without --download this only verifies existing files. Never called by App,
installation, browsing, tests or inference. Weights remain ignored in build/.
"""
import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/sd15-trained/originals'
BUNDLE_ID = 'sd15_ss_q4_0_r031b5f5'
CHUNK = 64 * 1024 * 1024


def inputs():
    return fingerprint('tools/fetch_sd15_trained.py', 'app/src/main/assets/model-bundles.json')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''): digest.update(block)
    return digest.hexdigest()


def bundle():
    record = json.loads((ROOT / 'app/src/main/assets/model-bundles.json').read_text(encoding='utf-8'))
    selected = next(item for item in record['bundles'] if item['id'] == BUNDLE_ID)
    if selected['pipeline'] != 'sd15' or selected['engine'] != 'sd_cpp' or selected['backend'] != 'cpu':
        raise ValueError('Changed selected bundle contract')
    if [item['role'] for item in selected['components']] != ['model', 'clip_merges']:
        raise ValueError('Different SD1.5 component set')
    for item in selected['components']:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', item['repository']): raise ValueError('Invalid repository')
        if not re.fullmatch('[a-f0-9]{40}', item['revision']) or not re.fullmatch('[a-f0-9]{64}', item['sha256']):
            raise ValueError('Unpinned component')
        path = PurePosixPath(item['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in item['path'] or item['bytes'] <= 0:
            raise ValueError('Invalid component path/size')
        expected = 'https://huggingface.co/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']
        if item['url'] != expected: raise ValueError('Different component URL')
    return selected


def asset_path(item):
    return DIRECTORY / PurePosixPath(item['path']).name


def verify():
    selected = bundle()
    for item in selected['components']:
        path = asset_path(item)
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly fetch/verify the pinned developer asset: ' + item['role'])
    return selected


def download(item, origin):
    DIRECTORY.mkdir(parents=True, exist_ok=True); path = asset_path(item)
    if path.exists():
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']: raise RuntimeError('Existing asset differs; preserve for review')
        return
    partial = path.with_name(path.name + '.part'); receipt = partial.with_name(partial.name + '.json')
    identity = {key: item[key] for key in ['role', 'repository', 'revision', 'path', 'bytes', 'sha256']}
    if partial.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8')) != identity:
            raise RuntimeError('Unknown partial asset; preserve for review')
        if partial.stat().st_size > item['bytes']: raise RuntimeError('Partial exceeds pinned size')
    else:
        receipt.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8'); partial.touch(exist_ok=False)
    start = partial.stat().st_size
    if start < item['bytes']:
        start = start // CHUNK * CHUNK
        with partial.open('r+b') as stream: stream.truncate(start)
    while start < item['bytes']:
        end = min(start + CHUNK, item['bytes']) - 1
        url = origin + '/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path'] + '?download=true&lma_range=' + str(start)
        request = urllib.request.Request(url, headers={'Range': 'bytes=' + str(start) + '-' + str(end), 'User-Agent': 'LMA-explicit-SD15-developer-assets/1'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    ranged = response.status == 206 and response.headers.get('Content-Range') == 'bytes ' + str(start) + '-' + str(end) + '/' + str(item['bytes'])
                    whole = response.status == 200 and start == 0 and end == item['bytes'] - 1
                    if not (ranged or whole): raise RuntimeError('Different pinned transfer range')
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
                if attempt == 2: raise RuntimeError('Pinned transfer failed; partial retained') from None
        start = end + 1
        print('Transferred', item['role'], start, '/', item['bytes'], 'bytes; final SHA256 pending', flush=True)
    if partial.stat().st_size != item['bytes'] or sha(partial) != item['sha256']:
        raise RuntimeError('Complete asset SHA256 differs; partial retained')
    partial.rename(path); receipt.unlink(); print('Verified pinned asset', item['role'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    args = parser.parse_args(); before = inputs(); selected = bundle()
    if args.download:
        for item in selected['components']: download(item, args.origin)
    verify(); current(before)
    report = dict(schema='lma.sd15-trained-assets/1', bundle_id=BUNDLE_ID,
                  components=[dict(item, local_path=asset_path(item).relative_to(ROOT).as_posix()) for item in selected['components']],
                  developer_assets_only=True, model_executed=False, app_assets_modified=False,
                  explicit_download=args.download, download_origin=args.origin if args.download else None,
                  input_fingerprint=before)
    (DIRECTORY.parent / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Pinned SD1.5 developer assets verified; no App model is installed or enabled', flush=True)


if __name__ == '__main__': main()
