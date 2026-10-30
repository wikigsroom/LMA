"""Read bounded publisher metadata/safetensors headers, never complete trained weights."""
import hashlib
import json
import struct
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/ltx098-official-metadata'
LIMIT = 2 * 1024 * 1024


def get(route, *, offset=0, count=LIMIT, ranged=False):
    for domain in ('hf-mirror.com', 'huggingface.co'):
        try:
            headers = {'User-Agent': 'LMA-program-metadata/1'}
            if ranged:
                headers['Range'] = f'bytes={offset}-{offset + count - 1}'
            with urllib.request.urlopen(urllib.request.Request('https://' + domain + route, headers=headers), timeout=25) as stream:
                if ranged and offset:
                    if stream.status != 206 or not stream.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                        raise ValueError('Server ignored bounded byte range')
                data = stream.read(count if ranged else count + 1)
            if len(data) > count or (ranged and len(data) != count):
                raise ValueError('Bounded metadata size mismatch')
            return data
        except Exception:
            if domain == 'huggingface.co':
                raise


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, repo in [('pixart', 'PixArt-alpha/PixArt-XL-2-1024-MS'), ('ltx', 'Lightricks/LTX-Video')]:
        info_path = OUT / f'{slug}-api.json'
        if not info_path.exists():
            info_path.write_bytes(get('/api/models/' + repo + '?blobs=true'))
        info = json.loads(info_path.read_bytes())
        revision = info['sha']
        entries = {f['rfilename']: f for f in info['siblings']}
        files = (['text_encoder/config.json', 'text_encoder/model.safetensors.index.json',
                  'tokenizer/tokenizer_config.json', 'tokenizer/special_tokens_map.json', 'tokenizer/spiece.model',
                  'text_encoder/model-00001-of-00002.safetensors', 'text_encoder/model-00002-of-00002.safetensors']
                 if slug == 'pixart' else ['ltxv-spatial-upscaler-0.9.8.safetensors'])
        summary = {'repository': repo, 'revision': revision, 'files': []}
        for name in files:
            item = entries[name]
            record = {'file': name, 'bytes': item['size'], 'sha256': item.get('lfs', {}).get('sha256')}
            route = '/' + repo + '/resolve/' + revision + '/' + name
            path = OUT / (slug + '-' + Path(name).name)
            if name.endswith('.safetensors'):
                path = path.with_suffix('.header.json')
                if not path.exists():
                    size = struct.unpack('<Q', get(route, count=8, ranged=True))[0]
                    if not 2 <= size <= LIMIT:
                        raise ValueError('Publisher header exceeds metadata limit')
                    data = get(route, offset=8, count=size, ranged=True)
                    json.loads(data)
                    path.write_bytes(data)
                data = path.read_bytes()
                record.update(header_bytes=len(data), header_sha256=hashlib.sha256(data).hexdigest())
            else:
                if item['size'] > LIMIT:
                    raise ValueError('Non-weight input exceeds metadata limit')
                if not path.exists():
                    path.write_bytes(get(route, count=item['size']))
                data = path.read_bytes()
                if len(data) != item['size']:
                    raise ValueError('Small input size mismatch')
                record['sha256'] = hashlib.sha256(data).hexdigest()
            record['metadata_file'] = path.name
            summary['files'].append(record)
            print(f"Bounded metadata: {slug}/{name}; {len(data)} bytes", flush=True)
        (OUT / f'{slug}-identity.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print('No complete model downloaded; no model inference executed.')


if __name__ == '__main__':
    main()
