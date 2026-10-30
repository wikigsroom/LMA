"""Explicit developer-only acquisition of pinned official prompt-reference files.

No model weights, inference provider or APK data. Without --download this only
verifies existing files and never accesses the network.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

from evidence import fingerprint

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'research/openmoss_reference/official-sources.json'
CACHE = ROOT / 'build/openmoss-reference-sources'


def verify():
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    for item in lock['files']:
        path = CACHE / item['path']
        path.resolve().relative_to(CACHE.resolve())
        if (not path.is_file() or path.stat().st_size != item['bytes']
                or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']):
            raise ValueError('Missing or changed official reference: ' + item['path'])
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Explicitly download the disclosed developer reference files')
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    if args.download:
        CACHE.mkdir(parents=True, exist_ok=True)
        def acquire(item):
            path = CACHE / item['path']
            path.resolve().relative_to(CACHE.resolve())
            if path.is_file() and path.stat().st_size == item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']:
                return
            failures = []
            for domain in ['huggingface.co', 'hf-mirror.com']:
                try:
                    url = ('https://' + domain + '/' + lock['repository'] + '/resolve/'
                           + lock['revision'] + '/' + item['path'])
                    request = urllib.request.Request(url, headers={'User-Agent': 'LMA-source-review'})
                    with urllib.request.urlopen(request, timeout=45) as response:
                        data = response.read(item['bytes'] + 1)
                    if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                        raise ValueError('Official reference hash mismatch')
                    path.write_bytes(data)
                    return
                except Exception as error:
                    failures.append(type(error).__name__)
            raise RuntimeError(item['path'] + ': ' + ', '.join(failures))
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(acquire, lock['files']))
    verify()
    print(json.dumps(dict(verified_files=len(lock['files']), revision=lock['revision'],
        downloaded_explicitly=args.download, model_weights=False, apk_data=False,
        input_fingerprint=fingerprint('research/openmoss_reference/official-sources.json',
                                      'tools/fetch_openmoss_reference.py'))))


if __name__ == '__main__':
    main()
