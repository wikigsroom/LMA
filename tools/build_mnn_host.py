"""Compile the production Sana worker and identical generated pipeline on native Windows."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil

from build_mnn import generate_sources
from evidence import current, fingerprint
from fetch_mnn import validate_sources
from fetch_mnn_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/mnn', 'tools/build_mnn.py', 'tools/build_mnn_host.py',
                       'tools/fetch_mnn.py', 'tools/fetch_mnn_trained.py',
                       'research/sd_host/platform.hpp', 'third_party/mnn-source-lock.json')


def build():
    if os.name != 'nt': raise RuntimeError('Native Windows MSVC only')
    before = inputs()
    lock = json.loads((ROOT / 'third_party/mnn-source-lock.json').read_text(encoding='utf-8'))
    source = validate_sources(lock)
    if sha(ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp') != lock['json_header_sha256']:
        raise ValueError('Pinned JSON header differs')
    key = hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest()[:16]
    directory = ROOT / 'build/mnn-worker-host' / key
    executable = directory / 'lma_mnn_host.exe'; receipt = directory / 'receipt.json'
    if receipt.is_file():
        record = json.loads(receipt.read_text(encoding='utf-8')); current(record['input_fingerprint'])
        if record['input_fingerprint'] != before or record['sha256'] != sha(executable):
            raise ValueError('Changed immutable host build')
        return executable, record
    directory.mkdir(parents=True, exist_ok=True)
    generated = directory / 'generated'; generate_sources(source, generated)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free native build alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + '/'; relative = directory.relative_to(ROOT).as_posix()
        # Reuse upstream object files; each fingerprint gets a separately frozen executable.
        compile_relative = 'build/mnn-host-compile/' + lock['revision']
        cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        options = dict(CMAKE_BUILD_TYPE='Release', MNN_BUILD_SHARED_LIBS='OFF', MNN_SEP_BUILD='OFF',
                       MNN_WIN_RUNTIME_MT='ON', MNN_BUILD_LLM='ON', MNN_BUILD_LLM_OMNI='OFF',
                       MNN_BUILD_DIFFUSION='ON', MNN_IMGCODECS='ON', MNN_ARM82='OFF', MNN_OPENMP='OFF',
                       MNN_OPENCL='OFF', MNN_VULKAN='OFF', MNN_CUDA='OFF', MNN_BUILD_AUDIO='OFF',
                       MNN_BUILD_TRAIN='OFF', MNN_BUILD_TEST='OFF', MNN_BUILD_CONVERTER='OFF',
                       MNN_BUILD_BENCHMARK='OFF', MNN_LLM_BUILD_DEMO='OFF', LLM_SUPPORT_HTTP_RESOURCE='OFF',
                       MNN_USE_LOGCAT='OFF')
        commands = [[cmake, '-S', alias + 'build/native-src/mnn', '-B', alias + compile_relative, '-G', 'Ninja',
                     '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe',
                     '-DCMAKE_PROJECT_INCLUDE=' + alias + 'native/mnn/bootstrap.cmake',
                     '-DLMA_MNN_SOURCE=' + alias + 'build/native-src/mnn',
                     '-DLMA_MNN_INTEGRATION=' + alias + 'native/mnn',
                     '-DLMA_MNN_GENERATED=' + alias + relative + '/generated',
                     '-DLMA_MNN_HOST_COMPAT=' + alias + 'research/sd_host',
                     '-DLMA_JSON_SOURCE=' + alias + 'build/native-src/sd-cpp/thirdparty',
                     '-DLMA_MNN_REVISION=' + lock['revision']] + ['-D' + k + '=' + v for k, v in options.items()],
                    [cmake, '--build', alias + compile_relative, '--target', 'lma_mnn_worker', '-j', '4']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = directory / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            print('Compile production Sana Windows worker', index, flush=True)
            result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=1800)
            (directory / ('build-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Inspect build/mnn-worker-host/' + key + '/build-' + str(index) + '.log')
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    current(before); validate_sources(lock)
    shutil.copy2(ROOT / compile_relative / 'lma_mnn_host.exe', executable)
    record = dict(schema='lma.mnn-host-build/1', executable=executable.relative_to(ROOT).as_posix(),
                  bytes=executable.stat().st_size, sha256=sha(executable), source_revision=lock['revision'],
                  production_worker=True, identical_generated_pipeline=True, backend='cpu',
                  bundled_model_data=False, model_executed=False, android_compiled=False,
                  physical_android=False, input_fingerprint=before,
                  generated_sources=fingerprint(generated.relative_to(ROOT).as_posix()))
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return executable, record


if __name__ == '__main__':
    executable, report = build()
    print(json.dumps({k: report[k] for k in ('executable', 'bytes', 'sha256', 'backend')}))
