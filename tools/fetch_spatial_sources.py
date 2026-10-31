"""Read hash-pinned source only. No install scripts, checkpoints or inference."""
import concurrent.futures
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'build/spatial-source-review'


def entries():
    return json.loads((ROOT / 'research/portability/audit-v0.3.4.json').read_text('utf-8'))['unported_configurations']


def fetch(entry):
    tree_file = DIRECTORY / (entry['id'] + '-tree.json')
    if not tree_file.exists():
        tree_file.write_bytes(subprocess.check_output([
            str(ROOT / 'build/github-cli/gh.exe'), 'api',
            'repos/' + entry['repository'] + '/git/trees/' + entry['revision'] + '?recursive=1']))
    tree = json.loads(tree_file.read_bytes())
    assert not tree.get('truncated')
    selected = []
    for item in tree['tree']:
        name = PurePosixPath(item['path'])
        if item['type'] != 'blob' or item.get('mode') not in ('100644', '100755'):
            continue
        if name.suffix not in ('.py', '.cpp', '.cc', '.c', '.cu', '.cuh', '.h', '.hpp', '.json', '.yaml', '.yml', '.md', '.txt', '.toml') and not name.name.upper().startswith(('LICENSE', 'NOTICE', 'COPYING')):
            continue
        assert not name.is_absolute() and '..' not in name.parts
        assert item.get('size', 0) <= 2 * 1024 * 1024
        selected.append(item)

    def one(item):
        destination = DIRECTORY / 'repos' / entry['id'] / item['path']
        def valid(data):
            return len(data) == item['size'] and hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['sha']
        if destination.is_file() and valid(destination.read_bytes()):
            data = destination.read_bytes()
        else:
            for attempt in range(3):
                try:
                    cache = DIRECTORY / 'blobs' / item['sha']
                    if cache.is_file():
                        data = cache.read_bytes()
                    else:
                        raw = subprocess.check_output([str(ROOT / 'build/github-cli/gh.exe'), 'api',
                            'repos/' + entry['repository'] + '/git/blobs/' + item['sha']], timeout=40)
                        value = json.loads(raw)
                        assert value['encoding'] == 'base64' and value['size'] <= 2 * 1024 * 1024
                        data = base64.b64decode(value['content'], validate=False)
                        assert valid(data)
                        cache.parent.mkdir(exist_ok=True)
                        cache.write_bytes(data)
                    assert valid(data), 'Source identity mismatch: ' + item['path']
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        return dict(path=item['path'], bytes=len(data), git_blob=item['sha'], sha256=hashlib.sha256(data).hexdigest())

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(one, selected))
    record = dict(id=entry['id'], repository=entry['repository'], revision=entry['revision'], files=files,
                  source_only=True, upstream_code_executed=False, trained_models_downloaded=0)
    (DIRECTORY / (entry['id'] + '-sources.json')).write_text(json.dumps(record, indent=2) + '\n', 'utf-8')
    print(json.dumps(dict(id=entry['id'], verified_source_files=len(files))), flush=True)
    return record


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for entry in entries():
        fetch(entry)


if __name__ == '__main__':
    main()
