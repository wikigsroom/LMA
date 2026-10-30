"""Explicit developer acquisition of the four pinned Z-Image-Turbo components.

Default: verify already present bytes only. Never invoked by the App, tests,
discovery or inference. No credentials, gated downloads or inference services.
"""
import argparse
import concurrent.futures
import json
import re
import urllib.request
from pathlib import Path, PurePosixPath

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'research/zimage_trained/assets.json'
DIRECTORY = ROOT / 'build/zimage-trained/originals'
CHUNK = 64 * 1024 * 1024
BUNDLE_ID = 'z_image_turbo_q4_0_catalogue_v1'


def inputs():
    return fingerprint('tools/fetch_zimage_trained.py', LOCK, 'tools/fetch_sd15_trained.py')


def assets():
    lock = json.loads((ROOT / LOCK).read_text(encoding='utf-8'))
    if lock['schema'] != 'lma.zimage-trained-assets/1' or lock['selection_id'] != '06':
        raise ValueError('Different frozen Z-Image-Turbo target')
    if [c['role'] for c in lock['components']] != ['diffusion', 'llm', 'vae', 'qwen_merges']:
        raise ValueError('Require all four matched components')
    for c in lock['components'] + ([lock['reference_tokenizer']] if 'reference_tokenizer' in lock else []):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', c['repository']):
            raise ValueError('Invalid repository')
        if not re.fullmatch('[a-f0-9]{40}', c['revision']) or not re.fullmatch('[a-f0-9]{64}', c['sha256']):
            raise ValueError('Unpinned component')
        path = PurePosixPath(c['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in c['path'] or c['bytes'] <= 0:
            raise ValueError('Invalid component path/size')
        if c['url'] != 'https://huggingface.co/' + c['repository'] + '/resolve/' + c['revision'] + '/' + c['path']:
            raise ValueError('Different immutable source')
    return lock


def verify_reference():
    c=assets()['reference_tokenizer']; path=asset_path(c)
    if not path.is_file() or path.stat().st_size!=c['bytes'] or sha(path)!=c['sha256']:
        raise RuntimeError('Explicitly acquire the independent developer tokenizer reference')
    return path


def asset_path(c):
    return DIRECTORY / c['sha256'] / PurePosixPath(c['path']).name


def verify():
    lock = assets()
    for c in lock['components']:
        path = asset_path(c)
        if not path.is_file() or path.stat().st_size != c['bytes'] or sha(path) != c['sha256']:
            raise RuntimeError('Explicitly acquire the complete developer component: ' + c['role'])
    return lock


def download(c, origin):
    path = asset_path(c); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != c['bytes'] or sha(path) != c['sha256']:
            raise RuntimeError('Preserve changed existing component: ' + c['role'])
        return
    # Explicit acquisition may reuse exact bytes already acquired in this project.
    # Verify the full source SHA before linking; discovery/verification never reaches this branch.
    shared=ROOT/'build/flux2-trained/originals'/c['sha256']/PurePosixPath(c['path']).name
    if shared.is_file() and shared.stat().st_size==c['bytes'] and sha(shared)==c['sha256']:
        path.hardlink_to(shared)
        return
    part = path.with_name(path.name + '.part'); receipt = part.with_name(part.name + '.json')
    identity = {k: c[k] for k in ('role', 'repository', 'revision', 'path', 'bytes', 'sha256')}
    if part.exists():
        if not receipt.is_file() or json.loads(receipt.read_text(encoding='utf-8')) != identity or part.stat().st_size > c['bytes']:
            raise RuntimeError('Unknown partial component; preserve for review')
    else:
        receipt.write_text(json.dumps(identity, indent=2) + '\n', encoding='utf-8'); part.touch(exist_ok=False)
    start = part.stat().st_size
    if start < c['bytes']:
        start = start // CHUNK * CHUNK
        with part.open('r+b') as stream: stream.truncate(start)
    while start < c['bytes']:
        end = min(start + CHUNK, c['bytes']) - 1
        url = origin + '/' + c['repository'] + '/resolve/' + c['revision'] + '/' + c['path'] + '?download=true&lma_range=' + str(start)
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={'Range': 'bytes=%d-%d' % (start, end), 'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=45) as response:
                    ranged = response.status == 206 and response.headers.get('Content-Range') == 'bytes %d-%d/%d' % (start, end, c['bytes'])
                    whole = response.status == 200 and start == 0 and end == c['bytes'] - 1
                    if not (ranged or whole): raise ValueError('Unexpected component byte range')
                    with part.open('r+b') as stream:
                        stream.seek(start); stream.truncate(start); position = start
                        while position <= end:
                            block = response.read(min(1024 * 1024, end + 1 - position))
                            if not block: raise ValueError('Truncated component range')
                            stream.write(block); position += len(block)
                        if response.read(1): raise ValueError('Component range exceeds bound')
                break
            except Exception as error:
                print('Transfer retry', c['role'], attempt + 1, type(error).__name__, flush=True)
                if attempt == 2: raise RuntimeError('Transfer failed; partial retained') from None
        start = end + 1
        print('Transferred', c['role'], start, '/', c['bytes'], flush=True)
    if part.stat().st_size != c['bytes'] or sha(part) != c['sha256']:
        raise RuntimeError('Full SHA256 differs; partial retained')
    part.rename(path); receipt.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    parser.add_argument('--jobs', type=int, choices=[1, 2], default=1)
    parser.add_argument('--reference-tokenizer', action='store_true', help='Also acquire/verify the optional developer-only HF numerical reference')
    args = parser.parse_args(); before = inputs(); lock = assets()
    if args.download:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(download, c, args.origin) for c in lock['components'] + ([lock['reference_tokenizer']] if args.reference_tokenizer else [])]
            for future in futures: future.result()
    verify()
    if args.reference_tokenizer: verify_reference()
    current(before)
    report = dict(schema='lma.zimage-trained-acquisition/1', components=lock['components'],
                  explicit_download=args.download, download_origin=args.origin if args.download else None,
                  developer_assets_only=True, bundled_model_data=False, model_executed=False,
                  reference_tokenizer_verified=args.reference_tokenizer,
                  input_fingerprint=before)
    (DIRECTORY.parent / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(verified_assets=4, bytes=sum(c['bytes'] for c in lock['components']), model_executed=False)))


if __name__ == '__main__': main()
