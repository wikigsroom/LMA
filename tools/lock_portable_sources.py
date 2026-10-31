"""Pin verified source definitions used by the offline portable sparse exporter.

This reads the existing Git-blob-verified source cache. It downloads nothing and
does not execute upstream code or inspect checkpoint/header files.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = {'D05': ('uniforge3d/modules/', 'uniforge3d/models/','uniforge3d/configs/','uniforge3d/pipelines/','uniforge3d/utils/'),
            'D10': ('supratex/modules/', 'supratex/models/','supratex/inference/','supratex/pipelines/','configs/',
                    'deployment/runtime/qwen/diffsynth/models/qwen_image_21',
                    'deployment/runtime/qwen/diffsynth/pipelines/qwen_image_21',
                    'deployment/runtime/qwen/examples/qwen_image_21/pbr/'),
            'D08': ('sam3d_objects/',), 'D09': ('sam3d_objects/','scripts/run_da3.py'),
            'MOGE': ('moge/',), 'DA3': ('src/depth_anything_3/',), 'TIMM': ('timm/',)}


def main():
    sources = []
    for target, prefixes in PREFIXES.items():
        receipt = json.loads((ROOT/f'build/spatial-source-review/{target}-sources.json').read_text('utf-8'))
        directory = f'build/spatial-source-review/repos/{target}'
        files = []
        for item in receipt['files']:
            name = item['path']
            if not name.startswith(prefixes) or not name.endswith(('.py','.json','.yaml')) or name.endswith('.header.json'):
                continue
            data = (ROOT/directory/name).read_bytes()
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() == item['git_blob']
            files.append(item)
        sources.append(dict(id=target, repository=receipt['repository'], revision=receipt['revision'],
                            directory=directory, files=files))
    path = ROOT/'third_party/portable-sparse-source-lock.json'
    path.write_text(json.dumps(dict(schema='lma.source-definitions/1', sources=sources), indent=2)+'\n', 'utf-8')
    print(json.dumps({s['id']: len(s['files']) for s in sources}))


if __name__ == '__main__':
    main()
