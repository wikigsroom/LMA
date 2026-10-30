"""Explicit acquisition of a complete public, precision-preserving MOSS 1.5 pair.

Default verifies existing developer assets. Never called by the App or tests.
The immutable range transfer is shared with the reviewed Wan acquisition tool.
No credentials, model gates, inference services or bundled model data.
"""
import argparse
import concurrent.futures
import json
import re
from pathlib import Path, PurePosixPath

from evidence import current, fingerprint
from fetch_sd15_trained import sha
import fetch_wan_trained as transfer

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'research/openmoss_trained/assets.json'
DIRECTORY = ROOT / 'build/openmoss-trained/originals'


def inputs():
    return fingerprint('tools/fetch_openmoss_trained.py', LOCK,
                       'tools/fetch_wan_trained.py', 'tools/fetch_sd15_trained.py')


def assets():
    lock = json.loads((ROOT / LOCK).read_text(encoding='utf-8'))
    if lock['schema'] != 'lma.openmoss-trained-assets/1' or lock['target'] != 'MOSS-TTS-v1.5':
        raise ValueError('Different frozen MOSS target')
    if [c['role'] for c in lock['components']] != ['model', 'extras']:
        raise ValueError('Require a complete matched model/extras pair')
    for c in lock['components']:
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', c['repository']):
            raise ValueError('Invalid public repository')
        if not re.fullmatch('[a-f0-9]{40}', c['revision']) or not re.fullmatch('[a-f0-9]{64}', c['sha256']):
            raise ValueError('Unpinned component')
        p = PurePosixPath(c['path'])
        if p.is_absolute() or '..' in p.parts or '\\' in c['path'] or c['bytes'] <= 0:
            raise ValueError('Invalid component path/size')
        if c['repository'] != lock['repository'] or c['revision'] != lock['revision']:
            raise ValueError('Mixed component revisions')
        if c['url'] != 'https://huggingface.co/' + c['repository'] + '/resolve/' + c['revision'] + '/' + c['path']:
            raise ValueError('Different immutable source')
    return lock


def asset_path(c):
    return DIRECTORY / c['sha256'] / PurePosixPath(c['path']).name


def verify():
    lock = assets()
    for c in lock['components']:
        p = asset_path(c)
        if not p.is_file() or p.stat().st_size != c['bytes'] or sha(p) != c['sha256']:
            raise RuntimeError('Explicitly acquire complete developer component: ' + c['role'])
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    parser.add_argument('--jobs', type=int, choices=[1, 2], default=1)
    args = parser.parse_args(); before = inputs(); lock = assets()
    if args.download:
        # This standalone acquisition process owns the imported helper's destination.
        # It does not call Wan main/verify or modify any Wan files or receipts.
        transfer.DIRECTORY = DIRECTORY
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(transfer.download, c, args.origin) for c in lock['components']]
            for future in futures:
                future.result()
    verify(); current(before)
    report = dict(schema='lma.openmoss-trained-acquisition/1', components=lock['components'],
                  explicit_download=args.download, download_origin=args.origin if args.download else None,
                  developer_assets_only=True, bundled_model_data=False, model_executed=False,
                  input_fingerprint=before)
    (DIRECTORY.parent / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(verified_assets=2, bytes=sum(c['bytes'] for c in lock['components']), model_executed=False)))


if __name__ == '__main__':
    main()
