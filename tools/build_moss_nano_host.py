"""Build the production Nano worker with Windows-only CRT compatibility."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from evidence import current, fingerprint
from fetch_moss_nano import validate_sources
from fetch_moss_nano_host_runtime import verify as runtime
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/moss_nano', 'research/moss_nano_host', 'research/sd_host/platform.hpp',
                       'tools/build_moss_nano_host.py', 'tools/fetch_moss_nano_host_runtime.py',
                       'tools/fetch_moss_nano.py', 'third_party/moss-nano-source-lock.json')


def build():
    if os.name != 'nt': raise RuntimeError('Native Windows MSVC required')
    before = inputs(); lock = json.loads((ROOT / 'third_party/moss-nano-source-lock.json').read_text(encoding='utf-8'))
    sources = validate_sources(lock); directory, library = runtime()
    if sha(ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp') != lock['json_header_sha256']: raise ValueError('Changed pinned JSON header')
    key = hashlib.sha256(json.dumps(before, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    output = ROOT / 'build/moss-nano-worker-host' / key; receipt = output / 'receipt.json'; binary = output / 'bin/lma_moss_nano_host.exe'
    if receipt.exists():
        record = json.loads(receipt.read_text(encoding='utf-8')); current(record['input_fingerprint'])
        if record['input_fingerprint'] != before or record['sha256'] != sha(binary): raise ValueError('Changed immutable host build')
        for name, expected in library['files'].items():
            if sha(binary.parent / name) != expected['sha256']: raise ValueError('Changed copied runtime')
        return binary, record
    (output / 'bin').mkdir(parents=True, exist_ok=True)
    for name in library['files']: shutil.copyfile(directory / name, binary.parent / name)
    (output / 'ort.def').write_text('LIBRARY onnxruntime.dll\nEXPORTS\nOrtGetApiBase\n', encoding='ascii')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        alias = drive + '/'; relative = output.relative_to(ROOT).as_posix(); cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        commands = [[cmake, '-S', alias + 'research/moss_nano_host', '-B', alias + relative + '/bin', '-G', 'Ninja',
                     '-DCMAKE_BUILD_TYPE=Release', '-DROOT=' + alias, '-DRUNTIME=' + alias + directory.relative_to(ROOT).as_posix(),
                     '-DLMA_MOSS_REVISION=' + sources['moss-nano'], '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe'],
                    [cmake, '--build', alias + relative + '/bin', '--target', 'lma_moss_nano_host', '-j', '2']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = output / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
                + 'lib /nologo /def:"' + alias + relative + '/ort.def" /machine:x64 /out:"' + alias + relative + '/bin/onnxruntime.lib"\n'
                + 'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            print('Compile Nano production source on native Windows', index, flush=True)
            result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=1800)
            (output / ('build-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Inspect Nano host build log: ' + str(output.relative_to(ROOT)))
    finally: subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    record = dict(schema='lma.moss-nano-host-build/1', executable=binary.relative_to(ROOT).as_posix(), bytes=binary.stat().st_size,
                  sha256=sha(binary), sources=sources, runtime=library, backend='cpu',
                  production_worker_source_unmodified=True, windows_crt_compatibility=True,
                  external_tokenizer_and_voice_data=True, bundled_model_data=False, physical_android=False,
                  android_compiled=False, packaged_in_apk=False, model_executed=False, input_fingerprint=before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8'); return binary, record


if __name__ == '__main__':
    path, record = build(); print(json.dumps({key: record[key] for key in ['executable', 'bytes', 'sha256', 'backend']}))
