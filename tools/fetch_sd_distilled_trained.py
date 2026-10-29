"""Explicit developer-only acquisition of pinned SD-Turbo and independent LCM diagnostic weights.

Without --download, verify existing bytes only. Never called by the App,
installation, discovery, import, test, or inference. No HF credentials are read.
"""
import argparse
import email.utils
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'research/sd_distilled_trained/assets.json'
DIRECTORY = ROOT / 'build/sd-distilled-asset-probe/originals'
CHUNK = 64 * 1024 * 1024


def inputs():
    return fingerprint(LOCK, 'tools/fetch_sd_distilled_trained.py', 'tools/fetch_sd15_trained.py')


def selected():
    record = json.loads((ROOT / LOCK).read_text(encoding='utf-8'))
    if record['schema'] != 'lma.sd-distilled-trained-assets-lock/1': raise ValueError('Different asset lock schema')
    if record['selection_ids'] != ['03']: raise ValueError('Different scoped targets')
    expected = ['sd_turbo_q8_0', 'lcm_dreamshaper_v7_f16', 'lcm_original_unet_f32']
    if [item['id'] for item in record['assets']] != expected: raise ValueError('Different complete developer asset set')
    for item in record['assets']:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', item['repository']): raise ValueError('Invalid repository')
        if not re.fullmatch('[a-f0-9]{40}', item['revision']) or not re.fullmatch('[a-f0-9]{64}', item['sha256']):
            raise ValueError('Unpinned asset')
        path = PurePosixPath(item['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in item['path'] or item['bytes'] <= 0:
            raise ValueError('Invalid asset path/size')
        expected_url = 'https://huggingface.co/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']
        if item['url'] != expected_url: raise ValueError('Different immutable asset URL')
    return record


def asset_path(item):
    return DIRECTORY / item['sha256'] / PurePosixPath(item['path']).name


def verify():
    record = selected()
    for item in record['assets']:
        path = asset_path(item)
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly fetch and verify the pinned developer asset: ' + item['id'])
    return record


def download(item, origin):
    path = asset_path(item); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Existing bytes differ; preserve for review')
        print('Existing pinned asset verified:', item['id'], flush=True); return
    partial = path.with_name(path.name + '.part'); receipt = partial.with_name(partial.name + '.json')
    identity = {key: item[key] for key in ['id', 'repository', 'revision', 'path', 'bytes', 'sha256']}
    if partial.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8')) != identity:
            raise RuntimeError('Unknown partial; preserve for review')
        if partial.stat().st_size > item['bytes']: raise RuntimeError('Partial exceeds pinned size')
    else:
        receipt.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8'); partial.touch(exist_ok=False)
    start = partial.stat().st_size
    if start < item['bytes']:
        start = start // CHUNK * CHUNK
        with partial.open('r+b') as stream: stream.truncate(start)
    while start < item['bytes']:
        end = min(start + CHUNK, item['bytes']) - 1
        url = origin + '/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']
        url += '?download=true&lma_range=' + str(start)
        for attempt in range(5):
            request = urllib.request.Request(url + '&lma_attempt=' + str(time.time_ns()), headers={
                'Range': 'bytes=' + str(start) + '-' + str(end), 'User-Agent': 'LMA-explicit-diffusion-developer-assets/1'})
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    ranged = response.status == 206 and response.headers.get('Content-Range') == 'bytes ' + str(start) + '-' + str(end) + '/' + str(item['bytes'])
                    whole = response.status == 200 and start == 0 and end == item['bytes'] - 1
                    if not (ranged or whole): raise RuntimeError('Different pinned range')
                    with partial.open('r+b') as stream:
                        stream.seek(start); stream.truncate(start); position = start
                        while position <= end:
                            block = response.read(min(1024 * 1024, end + 1 - position))
                            if not block: raise RuntimeError('Truncated range')
                            stream.write(block); position += len(block)
                        if response.read(1): raise RuntimeError('Range exceeds pinned length')
                break
            except Exception as error:
                code = error.code if isinstance(error, urllib.error.HTTPError) else None
                print('Transfer retry:', item['id'], attempt + 1, type(error).__name__, code, flush=True)
                if attempt == 4: raise RuntimeError('Transfer failed; partial retained') from None
                delay = 3 * (attempt + 1)
                if code == 429:
                    retry = error.headers.get('Retry-After', '')
                    try: delay = max(60., float(retry))
                    except ValueError:
                        try: delay = max(60., email.utils.parsedate_to_datetime(retry).timestamp() - time.time())
                        except (ValueError, TypeError): delay = 60.
                    if delay > 600: raise RuntimeError('Server requests a later retry; partial retained') from None
                print('Respect transfer backoff seconds:', delay, flush=True)
                while delay > 0:
                    pause = min(delay, 30.); time.sleep(pause); delay -= pause
        start = end + 1
        print('Transferred:', item['id'], start, '/', item['bytes'], '; final SHA256 pending', flush=True)
    if partial.stat().st_size != item['bytes'] or sha(partial) != item['sha256']:
        raise RuntimeError('Full SHA256 differs; partial retained')
    partial.rename(path); receipt.unlink(); print('Verified pinned asset:', item['id'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    args = parser.parse_args(); before = inputs(); record = selected()
    if args.download:
        for item in record['assets']: download(item, args.origin)
    verify(); current(before)
    report = dict(schema='lma.sd-distilled-trained-assets/1', lock=record,
                  assets=[dict(item, local_path=asset_path(item).relative_to(ROOT).as_posix()) for item in record['assets']],
                  developer_assets_only=True, model_executed=False, app_assets_modified=False,
                  explicit_download=args.download, download_origin=args.origin if args.download else None,
                  input_fingerprint=before)
    (DIRECTORY.parent / 'public-asset-receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Three pinned developer assets verified. No App model installed or enabled.', flush=True)


if __name__ == '__main__': main()
