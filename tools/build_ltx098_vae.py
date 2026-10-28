"""Compile the unregistered old-LTX VAE CPU worker; no downloads or APK edits."""
import argparse, hashlib, importlib.metadata, json, os, shutil, subprocess
from pathlib import Path
from evidence import fingerprint, current
from verify_package import elf_info, SYSTEM_LIBS

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('research/ltx098_vae', 'research/soulx_ort', 'research/soulx/dsp.hpp',
                       'native/moss_nano/onnx_external.hpp', 'tools/build_ltx098_vae.py',
                       'third_party/ltx098-vae-source-lock.json', 'third_party/soulx-acoustic-source-lock.json')


def build(android=False):
    if os.name != 'nt': raise RuntimeError('Native Windows MSVC/NDK build required')
    record = inputs()
    lock = json.loads((ROOT / 'third_party/ltx098-vae-source-lock.json').read_text(encoding='utf-8'))
    runtime_lock = json.loads((ROOT / 'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    headers = next(s for s in runtime_lock['sources'] if s['name'] == 'onnxruntime-headers')
    for name, digest in headers['reviewed_files'].items():
        if hashlib.sha256((ROOT / 'build/native-src/onnxruntime-headers' / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Changed pinned ORT header: ' + name)
    if hashlib.sha256((ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest() != lock['json_header_sha256']:
        raise RuntimeError('Changed pinned JSON header')
    name = 'ltx098-vae-arm64' if android else 'ltx098-vae-host'
    out = ROOT / 'build' / name; out.mkdir(exist_ok=True)
    (out / 'receipt.json').unlink(missing_ok=True)
    if android:
        runtime = ROOT / 'app/src/main/jniLibs/arm64-v8a' / lock['android_runtime']['file']
        runtime_data = runtime.read_bytes()
        if len(runtime_data) != lock['android_runtime']['bytes'] or hashlib.sha256(runtime_data).hexdigest() != lock['android_runtime']['sha256']:
            raise RuntimeError('Changed Android ORT runtime')
    else:
        distribution = importlib.metadata.distribution('onnxruntime')
        runtime = Path(distribution.locate_file('onnxruntime/capi/onnxruntime.dll'))
        if distribution.version != lock['host_runtime']['version'] or hashlib.sha256(runtime.read_bytes()).hexdigest() != lock['host_runtime']['sha256']:
            raise RuntimeError('Changed host ORT runtime')
        (out / 'bin').mkdir(exist_ok=True); shutil.copyfile(runtime, out / 'bin/onnxruntime.dll')
        (out / 'ort.def').write_text('LIBRARY onnxruntime.dll\nEXPORTS\nOrtGetApiBase\n', encoding='ascii')
    drive = next((c + ':' for c in 'RSTUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + '/'; tool = alias + 'build/toolchain/'; directory = alias + 'build/' + name
        cmake = tool + 'cmake-3.31.6/bin/cmake.exe'
        options = dict(CMAKE_MAKE_PROGRAM=tool + 'cmake-3.31.6/bin/ninja.exe', CMAKE_BUILD_TYPE='Release',
                       LMA_ORT_HEADERS=alias + 'build/native-src/onnxruntime-headers/include/onnxruntime/core/session',
                       LMA_JSON_SOURCE=alias + 'build/native-src/sd-cpp/thirdparty')
        if android:
            options.update(CMAKE_TOOLCHAIN_FILE=tool + 'android-ndk-r30/build/cmake/android.toolchain.cmake',
                           ANDROID_ABI='arm64-v8a', ANDROID_PLATFORM='android-28', ANDROID_STL='c++_static',
                           LMA_ORT_LIBRARY=alias + 'app/src/main/jniLibs/arm64-v8a/libonnxruntime.so')
        else:
            options.update(LMA_ORT_LIBRARY=directory + '/bin/onnxruntime.dll', LMA_ORT_IMPORT_LIBRARY=directory + '/onnxruntime.lib')
        commands = [[cmake, '-S', alias + 'research/ltx098_vae', '-B', directory, '-G', 'Ninja'] +
                    ['-D' + k + '=' + v for k, v in options.items()],
                    [cmake, '--build', directory, '--target', 'lma_ltx098_vae_cli', '-j', '4']]
        if android:
            commands.append([tool + 'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe',
                             '--strip-unneeded', directory + '/bin/liblma-ltx098-vae.so'])
        for i, command in enumerate(commands):
            if android:
                result = subprocess.run(command, capture_output=True, timeout=300)
            else:
                setup = Path(os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
                script = out / f'build-{i}.cmd'
                script.write_text('@echo off\ncall "' + str(setup) + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
                                  'lib /nologo /def:"' + directory + '/ort.def" /machine:x64 /out:"' + directory + '/onnxruntime.lib"\n'
                                  'if errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
                result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (out / f'build-{i}.log').write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError(f'Inspect build/{name}/build-{i}.log')
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    binary = out / 'bin' / ('liblma-ltx098-vae.so' if android else 'lma_ltx098_vae_cli.exe')
    data = binary.read_bytes()
    receipt = dict(kind='android_compile' if android else 'host_compile', executable_bytes=len(data),
                   executable_sha256=hashlib.sha256(data).hexdigest(), backend='cpu',
                   runtime=lock['android_runtime' if android else 'host_runtime'], c_api_minimum=17,
                   engine_registered=False, packaged_in_apk=False, model_inference=False,
                   physical_android=False, virtualization_used=False, input_fingerprint=record)
    if android:
        elf = elf_info(data); dependency = elf_info(runtime_data)
        if not elf['16k_elf_aligned'] or elf['android_api_notes'] != [28] or elf['interpreter'] != '/system/bin/linker64' or not elf['entry_point']:
            raise RuntimeError('Android worker ELF contract failed')
        if not dependency['16k_elf_aligned'] or dependency['android_api_notes'] != lock['android_runtime']['android_api_notes']:
            raise RuntimeError('Android ORT ELF contract failed')
        if 'libonnxruntime.so' not in elf['needed'] or set(elf['needed']) - SYSTEM_LIBS - {'libonnxruntime.so'}:
            raise RuntimeError('Unresolved Android VAE dependencies')
        llvm = ROOT / 'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-nm.exe'
        symbols = subprocess.check_output([str(llvm), '-D', '--undefined-only', str(binary)], text=True, encoding='utf-8')
        imports = {line.split()[-1].split('@')[0] for line in symbols.splitlines()}
        if imports & {'connect', 'socket', 'getaddrinfo', 'system', 'popen', 'execve', 'execvp', 'posix_spawn', '__android_log_print', '__android_log_write', '__android_log_vprint'}:
            raise RuntimeError('Unexpected network/process/log imports')
        receipt.update(android_arm64_compiled=True, android_platform=28, elf=elf, ndk='30.0.16248370')
    current(record)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('input_fingerprint', 'elf', 'runtime')}), flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--android', action='store_true')
    build(parser.parse_args().android)
