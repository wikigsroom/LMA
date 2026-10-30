"""Collect the exact MNN/header notices and register only the actually compiled worker."""
import hashlib
import json
from pathlib import Path
from evidence import current
from fetch_mnn import validate_sources
from native_payload import engine_files
from sana_sprint_profile import sources as sprint_sources

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = json.loads((ROOT / 'third_party/mnn-source-lock.json').read_text(encoding='utf-8'))
    receipt = json.loads((ROOT / 'build/mnn-build-info.json').read_text(encoding='utf-8'))
    current(receipt['source_inputs']); source = validate_sources(lock)
    output = ROOT / 'third_party/notices'; records = []
    for item in lock['notices']:
        data = (source / item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256'] or Path(item['output']).name != item['output']: raise RuntimeError('MNN source notice changed')
        if item.get('embedded_stb_notice'):
            text = data.decode('utf-8'); marker = text.rfind('ALTERNATIVE A - MIT License')
            if marker < 0: raise RuntimeError('Embedded stb notice is missing')
            data = (text[marker:].strip() + '\n').encode('utf-8')
        (output / item['output']).write_bytes(data)
        records.append(dict(file=item['output'], sha256=hashlib.sha256(data).hexdigest(), source=lock['repository'].removesuffix('.git') + '/blob/' + lock['revision'] + '/' + item['path']))
    notices = {r['file']: r['sha256'] for r in records}
    piece = sprint_sources()
    for item in piece['notices']:
        file = output/item['output']
        if hashlib.sha256(file.read_bytes()).hexdigest() != item['sha256']: raise RuntimeError('Existing SentencePiece notice differs')
        notices[item['output']] = item['sha256']
    for name in ('sd-nlohmann-json-LICENSE.txt', 'sd-NDK-LLVM-NOTICE.txt'): notices[name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    engine = {k: receipt[k] for k in ('engine', 'file', 'source_revision', 'abi', 'backend', 'ndk', 'sha256', 'bytes', 'android_api_notes')}; engine['notices'] = notices
    path = ROOT / 'third_party/engine-lock.json'; engines = json.loads(path.read_text(encoding='utf-8'))
    engines['engines'] = [e for e in engines['engines'] if e['engine'] != engine['engine']] + [engine]; engine_files(engines['engines'])
    newline = '\r\n' if b'\r\n' in path.read_bytes() else '\n'
    path.write_bytes((json.dumps(engines, indent=2) + '\n').replace('\n', newline).encode('utf-8'))
    (output / 'mnn-sources.json').write_bytes((json.dumps(dict(revision=lock['revision'], files=records, model_assets=False), indent=2) + '\n').encode('utf-8'))
    print(json.dumps(dict(notices=len(records), engine=engine['engine'], bundled_model_data=False)))


if __name__ == '__main__': main()
