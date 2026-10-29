"""Explicitly acquire exactly the three frozen selection-10 developer bundles."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import urllib.request

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/tts-trained/originals'
CHUNK = 32 * 1024 * 1024


def inputs(): return fingerprint('tools/fetch_tts_trained.py', 'research/tts_trained/assets.json')


def selected():
    value = json.loads((ROOT / 'research/tts_trained/assets.json').read_text(encoding='utf-8'))
    assert value['schema'] == 'lma.tts-trained-assets-lock/1' and value['developer_assets_only']
    assert [b['pipeline'] for b in value['bundles']] == ['kokoro', 'piper_vits', 'matcha']
    for bundle in value['bundles']:
        assert bundle['language'] == 'en-US' and len(bundle['components']) in [3, 4]
        for item in bundle['components']:
            p = PurePosixPath(item['path'])
            assert len(p.parts) == 1 and not p.is_absolute() and '..' not in p.parts and '\\' not in item['path']
            assert item['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', item['sha256'])
            if item['url'].startswith('https://huggingface.co/'):
                assert re.fullmatch('[a-f0-9]{40}', item['revision'])
                assert item['url'] == 'https://huggingface.co/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']
            else:
                assert item['repository'] == 'k2-fsa/sherpa-onnx' and re.fullmatch('github_asset_[0-9]+', item['revision'])
                assert item['url'].startswith('https://github.com/k2-fsa/sherpa-onnx/releases/download/')
    return value


def distinct():
    by_sha = {}
    for bundle in selected()['bundles']:
        for item in bundle['components']:
            if item['sha256'] in by_sha and by_sha[item['sha256']] != item: raise ValueError('Conflicting shared content metadata')
            by_sha[item['sha256']] = item
    assert len(by_sha) == 9
    return list(by_sha.values())


def path_for(item): return DIRECTORY / item['sha256'] / item['path']


def verify():
    for item in distinct():
        path = path_for(item)
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly acquire selected developer asset: ' + item['path'])
    return selected()


def download(item, hf_origin):
    path = path_for(item); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != item['bytes'] or sha(path) != item['sha256']: raise ValueError('Preserve changed existing model asset')
        return
    partial = path.with_name(path.name + '.part'); receipt = partial.with_name(partial.name + '.json')
    if partial.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8')) != item or partial.stat().st_size > item['bytes']: raise ValueError('Preserve unidentified/different partial')
    else:
        if receipt.exists(): raise ValueError('Preserve orphan partial receipt')
        receipt.write_text(json.dumps(item, indent=2)+'\n', encoding='utf-8'); partial.touch(exist_ok=False)
    start = partial.stat().st_size
    if start < item['bytes']:
        start = start // CHUNK * CHUNK
        with partial.open('r+b') as stream: stream.truncate(start)
    while start < item['bytes']:
        end = min(start + CHUNK, item['bytes']) - 1
        url = item['url']
        if url.startswith('https://huggingface.co/'): url = hf_origin + url[len('https://huggingface.co'):]
        whole_request = start == 0 and end + 1 == item['bytes']
        url += '?download=true&lma_selection10_transfer=' + ('whole' if whole_request else str(start))
        headers = {'User-Agent':'LMA-explicit-selection10-assets/1', 'Accept-Encoding':'identity'}
        if not whole_request: headers['Range'] = f'bytes={start}-{end}'
        request = urllib.request.Request(url, headers=headers)
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    ranged = response.status == 206 and response.headers.get('Content-Range') == f'bytes {start}-{end}/{item["bytes"]}'
                    whole = response.status == 200 and start == 0 and end + 1 == item['bytes']
                    if not (ranged or whole): raise ValueError('Different transfer range')
                    with partial.open('r+b') as stream:
                        stream.seek(start); stream.truncate(start); position = start
                        while position <= end:
                            block = response.read(min(1024*1024, end+1-position))
                            if not block: raise ValueError('Truncated transfer range')
                            stream.write(block); position += len(block)
                        if response.read(1): raise ValueError('Range exceeds pinned file')
                break
            except Exception as error:
                print('Transfer retry', item['path'], attempt+1, type(error).__name__, flush=True)
                if attempt == 2: raise RuntimeError('Pinned download failed; partial preserved') from None
        start = end + 1; print('Transferred', item['path'], start, '/', item['bytes'], flush=True)
    if partial.stat().st_size != item['bytes'] or sha(partial) != item['sha256']: raise ValueError('Different full-file SHA; preserve partial')
    partial.rename(path); receipt.unlink(); print('Verified', item['path'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--download', action='store_true')
    parser.add_argument('--hf-origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co'); args = parser.parse_args()
    before = inputs()
    if args.download:
        for item in distinct(): download(item, args.hf_origin)
    verify(); current(before)
    if args.download:
        report = dict(schema='lma.tts-trained-assets/1', explicit_download=True, hf_download_origin=args.hf_origin,
            developer_assets_only=True, app_assets_modified=False, model_executed=False, bundles=selected()['bundles'],
            components=[dict(c, local_path=path_for(c).relative_to(ROOT).as_posix()) for c in distinct()], input_fingerprint=before)
        path = DIRECTORY.parent / 'receipt.json'
        if path.exists():
            old = json.loads(path.read_text(encoding='utf-8')); current(old['input_fingerprint'])
            if old['components'] != report['components']: raise ValueError('Preserve different acquisition receipt')
        else: path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('Verified 3 frozen TTS bundles / 9 distinct files; no App model installed', flush=True)


if __name__ == '__main__': main()
