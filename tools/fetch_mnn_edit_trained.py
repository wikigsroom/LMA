"""Explicitly acquire/verify all fifteen matched Sana Edit developer components."""
import argparse
import json
from pathlib import Path

from evidence import current, fingerprint
from fetch_mnn_trained import assets as base_assets, asset_path, download, sha

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'research/mnn_edit_trained/assets.json'


def inputs():
    return fingerprint('tools/fetch_mnn_edit_trained.py', 'tools/fetch_mnn_trained.py',
                       'research/mnn_trained/assets.json', LOCK)


def assets():
    base = base_assets()
    lock = json.loads((ROOT / LOCK).read_text(encoding='utf-8'))
    if lock['schema'] != 'lma.mnn-edit-trained-assets/1' or len(lock['components']) != 15:
        raise ValueError('Require the complete fifteen-component edit recipe')
    if lock['components'][:13] != base['components']:
        raise ValueError('Retain the original thirteen component identities')
    expected = {'vae_encoder': 'vae_encoder.mnn', 'vae_encoder_data': 'vae_encoder.mnn.weight'}
    for item in lock['components'][13:]:
        if expected.pop(item['role'], None) != item['path']:
            raise ValueError('Unexpected edit component path/role')
        if item['repository'] != base['repository'] or item['revision'] != base['revision']:
            raise ValueError('Mixed edit asset identity')
        if item['bytes'] < 1 or len(item['sha256']) != 64 or any(c not in '0123456789abcdef' for c in item['sha256']):
            raise ValueError('Unpinned edit component')
        if item['url'] != 'https://huggingface.co/' + item['repository'] + '/resolve/' + item['revision'] + '/' + item['path']:
            raise ValueError('Different asset source')
    if expected:
        raise ValueError('Missing image encoder component')
    return lock


def verify():
    lock = assets()
    for item in lock['components']:
        path = asset_path(item)
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise RuntimeError('Explicitly acquire the selected edit component: ' + item['role'])
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    args = parser.parse_args(); before = inputs(); lock = assets()
    if args.download:
        for item in lock['components']:
            download(item, args.origin, 'Mozilla/5.0' if args.origin == 'https://hf-mirror.com' else 'LMA-explicit-Sana-developer-assets/1')
    verify(); current(before)
    report = dict(schema='lma.mnn-edit-trained-acquisition/1', components=lock['components'],
                  developer_assets_only=True, explicit_download=args.download, origin=args.origin,
                  model_executed=False, model_data_bundled=False, physical_android=False,
                  input_fingerprint=before)
    target = ROOT / 'build/mnn-edit-trained'; target.mkdir(parents=True, exist_ok=True)
    (target / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(verified_components=15, bytes=sum(i['bytes'] for i in lock['components']), model_data_bundled=False)))


if __name__ == '__main__': main()
