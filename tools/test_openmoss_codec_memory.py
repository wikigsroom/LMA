"""Check real CPU graph allocation release/reuse and independent stream lifetime."""
import json
from pathlib import Path
import subprocess
import time
from build_openmoss_host import build, inputs
from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    before = inputs()
    before.update(fingerprint('tools/test_openmoss_codec_memory.py'))
    worker, compilation = build()
    binary = worker.parent / 'lma_openmoss_codec_memory_test.exe'
    folder = ROOT / 'build/openmoss-codec-memory-tests' / ('run-' + str(time.time_ns()))
    folder.mkdir(parents=True)
    result = subprocess.run([str(binary)], cwd=ROOT, capture_output=True, timeout=30)
    (folder / 'stdout.txt').write_bytes(result.stdout)
    (folder / 'stderr.txt').write_bytes(result.stderr)
    if result.returncode: raise RuntimeError('Inspect real allocator test: ' + str(folder))
    details = json.loads(result.stdout)
    assert details['passed'] >= 20 and details['actual_cpu_graphs'] == 7 and details['release_count'] == 3
    assert details['persistent_parameters_unchanged'] and details['streaming_allocator_preserved']
    assert not details['model_inference']
    current(before)
    report = dict(schema='lma.openmoss-codec-memory-contract/1', passed=True, details=details,
        compilation=compilation, executable_sha256=sha(binary), input_fingerprint=before,
        capture_directory=folder.relative_to(ROOT).as_posix(), physical_android=False,
        model_inference=False, network_requests=0)
    for path in [folder / 'results.json', folder.parent / 'results.json']:
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, details=details)), flush=True)


if __name__ == '__main__': main()
