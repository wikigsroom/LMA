"""Bind current Android compilation to the actually executed Sana host pipeline."""
import json
from pathlib import Path

from evidence import current, fingerprint
from fetch_mnn_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    native = json.loads((ROOT / 'build/mnn-build-info.json').read_text(encoding='utf-8'))
    host = json.loads((ROOT / 'build/mnn-trained-tests/results.json').read_text(encoding='utf-8'))
    bridge = json.loads((ROOT / 'build/mnn-app-host-tests/results.json').read_text(encoding='utf-8'))
    current(native['source_inputs']); current(native['generated_sources'])
    current(host['input_fingerprint']); current(bridge['input_fingerprint'])
    if not host['passed'] or not bridge['passed'] or host['compilation']['sha256'] != bridge['compilation']['sha256']:
        raise ValueError('Complete matching real host execution first')
    android_generated = {Path(k).name: v for k, v in native['generated_sources'].items()}
    host_generated = {Path(k).name: v for k, v in host['compilation']['generated_sources'].items()}
    if android_generated != host_generated or len(android_generated) != 2:
        raise ValueError('Android and host generated pipelines differ')
    binary = ROOT / 'app/src/main/jniLibs/arm64-v8a/liblma-mnn.so'
    if sha(binary) != native['sha256'] or binary.stat().st_size != native['bytes']:
        raise ValueError('Packaged native worker differs')
    inputs = {**native['source_inputs'], **native['generated_sources'],
              **fingerprint('tools/export_mnn_evidence.py', 'build/mnn-build-info.json',
                            'build/mnn-trained-tests/results.json', 'build/mnn-app-host-tests/results.json')}
    report = dict(schema='lma.mnn-arm64-evidence/1', native=native,
                  identical_host_android_generated_pipeline=True, generated_pipeline=android_generated,
                  host_worker_sha256=host['compilation']['sha256'], model_data_bundled=False,
                  host_execution_only=True, physical_android=False, complete_release_accepted=False,
                  input_fingerprint=inputs)
    (ROOT / 'build/mnn-arm64-evidence.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(android_compiled=True, identical_generated_pipeline=True, physical_android=False)))


if __name__ == '__main__': main()
