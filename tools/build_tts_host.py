"""Build unchanged production speech worker against pinned Windows C API."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from evidence import current, fingerprint
from fetch_tts_host_runtime import verify
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/tts', 'research/tts_host', 'research/sd_host/platform.hpp',
        'research/moss_nano_host/compat', 'third_party/tts-source-lock.json',
        'tools/build_tts_host.py', 'tools/fetch_tts_host_runtime.py')


def build():
    if os.name != 'nt': raise RuntimeError('Native Windows MSVC required')
    before = inputs(); runtime_path, runtime = verify()
    lock = json.loads((ROOT / 'third_party/tts-source-lock.json').read_text(encoding='utf-8')); source = ROOT / 'build/native-src/sherpa-onnx'
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    if revision != lock['source_revision'] or subprocess.check_output(['git', 'status', '--porcelain'], cwd=source, text=True).strip(): raise ValueError('Different source revision or dirty C API source')
    if sha(source / 'sherpa-onnx/c-api/c-api.h') != lock['header_sha256'] or sha(ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp') != lock['json_header_sha256']: raise ValueError('Different reviewed headers')
    key = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()[:16]
    output = ROOT / 'build/tts-worker-host' / key; binary = output / 'bin/lma_tts_host.exe'; receipt = output / 'receipt.json'
    if receipt.exists():
        value = json.loads(receipt.read_text(encoding='utf-8')); current(value['input_fingerprint'])
        if value['input_fingerprint'] != before or sha(binary) != value['sha256']: raise ValueError('Changed immutable worker')
        for name, item in runtime['files'].items():
            if name.endswith('.dll') and sha(binary.parent / name) != item['sha256']: raise ValueError('Changed copied runtime')
        return binary, value
    binary.parent.mkdir(parents=True, exist_ok=True)
    for name in runtime['files']:
        if name.endswith('.dll'): shutil.copyfile(runtime_path / name, binary.parent / name)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No unused owned build alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        cmake = alias(ROOT / 'build/toolchain/cmake-3.31.6/bin/cmake.exe')
        commands = [[cmake, '-S', alias(ROOT / 'research/tts_host'), '-B', alias(binary.parent), '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=Release', '-DROOT=' + drive + '/', '-DRUNTIME=' + alias(runtime_path),
            '-DLMA_SHERPA_REVISION=' + revision, '-DCMAKE_MAKE_PROGRAM=' + alias(ROOT / 'build/toolchain/cmake-3.31.6/bin/ninja.exe')],
            [cmake, '--build', alias(binary.parent), '--target', 'lma_tts_host', '-j', '2']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = output / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=600)
            (output / ('build-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Inspect native Windows TTS build log: ' + str(output.relative_to(ROOT)))
    finally: subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    value = dict(schema='lma.tts-host-build/1', executable=binary.relative_to(ROOT).as_posix(), bytes=binary.stat().st_size, sha256=sha(binary),
        source_revision=revision, runtime=runtime, backend='cpu', production_worker_source_unmodified=True,
        windows_crt_parent_compatibility=True, external_model_data=True, android_log_interposition_tested=False,
        physical_android=False, android_compiled=False, packaged_in_apk=False, model_executed=False, input_fingerprint=before)
    receipt.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8'); return binary, value


if __name__ == '__main__':
    binary, value = build(); print(json.dumps({k:value[k] for k in ['executable', 'bytes', 'sha256']}))
