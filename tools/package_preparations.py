"""Package signed foundation converters and model-free graphs; never fetch model data."""
import hashlib
import json
from pathlib import Path
import shutil
from evidence import current
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    lock = json.loads((ROOT / 'third_party/engine-lock.json').read_text(encoding='utf-8'))
    modules = lock.get('preparations', [])
    catalogue = json.loads((ROOT / 'catalogue/asset-preparations.json').read_text(encoding='utf-8'))
    assert catalogue['schema'] == 'lma.asset-preparation-catalogue/1'
    target = ROOT / 'app/src/main/jniLibs/arm64-v8a'; target.mkdir(parents=True, exist_ok=True)
    result = []
    for module in modules:
        record = json.loads((ROOT / module['receipt']).read_text(encoding='utf-8')); current(record['input_fingerprint'])
        assert record['android_arm64_compiled'] and not record.get('model_data_embedded', record.get('learned_data_embedded', True))
        source = ROOT / module['binary']; data = source.read_bytes(); info = elf_info(data)
        assert len(data) == module['bytes'] == record['executable_bytes']
        assert hashlib.sha256(data).hexdigest() == module['sha256'] == record['executable_sha256']
        assert info['16k_elf_aligned'] and info['android_api_notes'] == [28] and info['interpreter'] == '/system/bin/linker64'
        assert set(info['needed']) <= {'libc.so', 'libm.so', 'libdl.so'}
        assert Path(module['file']).name == module['file'] and module['file'].endswith('.so')
        for notice, expected in module['notices'].items():
            assert hashlib.sha256((ROOT / 'third_party/notices' / notice).read_bytes()).hexdigest() == expected
        shutil.copyfile(source, target / module['file'])
        result.append({k: v for k, v in module.items() if k not in ['receipt', 'binary']} | dict(deviceValidated=False, status='compiled_not_device_tested', model_data_embedded=False))
    known = {module['engine'] for module in modules}
    for plan in catalogue['plans']:
        assert plan['schema'] == 'lma.asset-preparation/1'
        for stage in plan['stages']:
            assert stage['module'] in known
            folder = ROOT / 'app/src/main/assets/preparations' / stage['module']; folder.mkdir(parents=True, exist_ok=True)
            for graph in stage.get('graphs', []):
                assert Path(graph['file']).name == graph['file']
                source = ROOT / 'research/ltx098_vae_prepare/graphs' / graph['file']; data = source.read_bytes()
                assert len(data) == graph['bytes'] and hashlib.sha256(data).hexdigest() == graph['sha256']
                shutil.copyfile(source, folder / graph['file'])
    audit_path = ROOT / 'build/ltx098-vae-template-tests/results.json'
    if not audit_path.exists(): audit_path = ROOT / 'verification/development/ltx098-vae-templates.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8')); current(audit['input_fingerprint']); current(audit['output_fingerprint'])
    assert audit['passed'] and not audit['inline_learned_data'] and audit['all_graph_constants_classified']
    (ROOT / 'app/src/main/assets/asset-preparations.json').write_bytes((ROOT / 'catalogue/asset-preparations.json').read_bytes())
    return result


if __name__ == '__main__':
    print(json.dumps({'preparations': prepare(), 'model_assets_downloaded': False}))
