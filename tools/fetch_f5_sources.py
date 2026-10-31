"""Fetch pinned text-program sources/data only; no model, installer or inference."""
import hashlib
import base64
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'build/frontend-reference'
LOCK = ROOT/'third_party/f5-frontend-source-lock.json'


def download(url, maximum):
    assert url.startswith('https://')
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'LMA-source-review'}), timeout=90) as response:
        data = response.read(maximum+1)
    assert 0 < len(data) <= maximum
    return data


def verify():
    lock = json.loads(LOCK.read_text('utf-8'))
    for item in lock['files']:
        path = ROOT/item['cachePath']
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], item['cachePath']
    return lock


def main():
    lock = json.loads(LOCK.read_text('utf-8'))
    CACHE.mkdir(parents=True, exist_ok=True)
    for item in lock['archives']:
        archive = CACHE/(item['name']+'-source.tar.gz')
        data = archive.read_bytes() if archive.exists() else download(item['url'], 8*1024*1024)
        assert hashlib.sha256(data).hexdigest() == item['sha256'], 'Changed pinned source archive'
        archive.write_bytes(data)
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
            total = 0
            for member in tar.getmembers():
                path = PurePosixPath(member.name)
                assert not path.is_absolute() and '..' not in path.parts and not member.issym() and not member.islnk()
                if not member.isfile():
                    assert member.isdir()
                    continue
                assert 0 <= member.size <= 8*1024*1024
                total += member.size
                assert total <= 32*1024*1024
                relative = PurePosixPath(*path.parts[1:]).as_posix()
                # Fixed source/text-data allowlist. No executable/build scripts.
                destination = None
                if item['name'] == 'rjieba' and relative in ('src/lib.rs','rjieba/__init__.py','LICENSE'):
                    destination = CACHE/relative
                elif item['name'] == 'jieba-rs':
                    if relative in ('src/lib.rs','src/hmm.rs','src/trie.rs','LICENSE'):
                        destination = CACHE/'jieba-rs'/relative
                    elif relative == 'src/data/dict.txt':
                        destination = CACHE/'jieba-data/dict.txt'
                elif item['name'] == 'jieba-macros' and relative in ('src/lib.rs','src/hmm.model','LICENSE'):
                    destination = CACHE/'jieba-macros'/relative
                elif item['name'] == 'pypinyin' and (relative.startswith('pypinyin/') and relative.endswith('.py') or relative == 'LICENSE.txt'):
                    destination = CACHE/'pypinyin-source'/relative
                if destination:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(tar.extractfile(member).read())
    target = CACHE/'f5_utils.py'
    expected = next(f for f in lock['files'] if f['cachePath'].endswith('/f5_utils.py'))
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != expected['sha256']:
        source = lock['f5Source']
        target.write_bytes(download('https://raw.githubusercontent.com/'+source['repository']+'/'+source['revision']+'/src/f5_tts/model/utils.py', 1024*1024))
    for item in lock['files']:
        if 'url' not in item:continue
        path=ROOT/item['cachePath'];assert path.resolve().is_relative_to(CACHE.resolve())
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:continue
        data=base64.b64decode(json.loads(download(item['url'],1024*1024))['content'])
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    verify()
    print(json.dumps(dict(sourceFilesVerified=len(lock['files']), network='source_only', neuralWeightsDownloaded=False, installersExecuted=False)))


if __name__ == '__main__':
    main()
