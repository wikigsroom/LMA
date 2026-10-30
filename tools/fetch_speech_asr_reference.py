"""Explicit developer-only Whisper acquisition; default is offline verification."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'research/speech_asr_reference/assets.json'
CACHE = ROOT / 'build/speech-asr-reference/model'


def assets():
    value = json.loads(LOCK.read_text(encoding='utf-8'))
    if value['schema'] != 'lma.speech-asr-reference-assets/1' or not value['developer_only'] or value['packaged_in_apk']:
        raise ValueError('Different ASR diagnostic asset boundary')
    for item in value['components']:
        if Path(item['path']).name != item['path'] or item['path'] in {'.', '..'}:
            raise ValueError('ASR reference must have a plain local filename')
    return value


def verify():
    from fetch_sd15_trained import sha
    value = assets()
    for item in value['components']:
        path = CACHE / item['path']
        path.resolve().relative_to(CACHE.resolve())
        if not path.is_file() or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
            raise ValueError('Explicitly acquire pinned local ASR reference: ' + item['path'])
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--origin', choices=['https://huggingface.co', 'https://hf-mirror.com'], default='https://huggingface.co')
    args = parser.parse_args()
    value = assets()
    if args.download:
        import fetch_wan_trained as transfer
        CACHE.mkdir(parents=True, exist_ok=True)
        def acquire(item):
            path = CACHE / item['path']
            path.resolve().relative_to(CACHE.resolve())
            if path.is_file() and path.stat().st_size == item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']:
                return
            if item['path'] == 'model.safetensors':
                transfer.DIRECTORY = ROOT / 'build/speech-asr-reference/originals'
                transfer.download(item, args.origin)
                original = transfer.DIRECTORY / item['sha256'] / item['path']
                import os
                if path.exists():
                    raise ValueError('Preserve changed existing ASR model for review')
                os.link(original, path)
            else:
                url = args.origin + '/' + value['repository'] + '/resolve/' + value['revision'] + '/' + item['path']
                request = urllib.request.Request(url, headers={'User-Agent': 'LMA-local-speech-diagnostic'})
                with urllib.request.urlopen(request, timeout=45) as response:
                    data = response.read(item['bytes'] + 1)
                if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                    raise ValueError('ASR reference hash mismatch: ' + item['path'])
                path.write_bytes(data)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(acquire, value['components']))
    verify()
    print(json.dumps(dict(verified_files=len(value['components']), downloaded_explicitly=args.download,
                          model_bytes=sum(x['bytes'] for x in value['components']), apk_model_data=False)))


if __name__ == '__main__':
    main()
