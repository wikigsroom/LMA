"""Compile the model-free fixed-guidance preparer with native MSVC or Android NDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from evidence import current, fingerprint
from verify_package import SYSTEM_LIBS, elf_info

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('research/lcm_prepare', 'research/local_prepare', 'tools/build_lcm_prepare.py',
                       'tools/generate_lcm_condition_contract.py', 'third_party/ltx098-text-source-lock.json')


def build(android=False):
    if os.name != 'nt':
        raise RuntimeError('Use native Windows MSVC / NDK; no virtualized runtime')
    before = inputs()
    lock = json.loads((ROOT / 'third_party/ltx098-text-source-lock.json').read_text(encoding='utf-8'))
    header = ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp'
    if hashlib.sha256(header.read_bytes()).hexdigest() != lock['json_header_sha256']:
        raise RuntimeError('Changed pinned JSON header')
    name = 'lcm-prepare-' + ('arm64' if android else 'host')
    directory = ROOT / 'build' / name
    directory.mkdir(exist_ok=True)
    receipt = directory / 'receipt.json'
    binary = directory / 'bin' / ('liblma-lcm-prepare.so' if android else 'lma_lcm_prepare.exe')
    if receipt.exists():
        record = json.loads(receipt.read_text(encoding='utf-8'))
        if record['input_fingerprint'] == before and binary.exists():
            if hashlib.sha256(binary.read_bytes()).hexdigest() != record['executable_sha256']:
                raise RuntimeError('Changed compiled preparation program')
            current(before)
            return binary, record
    receipt.unlink(missing_ok=True)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if drive is None:
        raise RuntimeError('No free task-owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        alias = drive + '/'
        tool = alias + 'build/toolchain/'
        options = dict(CMAKE_BUILD_TYPE='Release', CMAKE_MAKE_PROGRAM=tool + 'cmake-3.31.6/bin/ninja.exe',
                       LMA_JSON_SOURCE=alias + 'build/native-src/sd-cpp/thirdparty')
        if android:
            options.update(CMAKE_TOOLCHAIN_FILE=tool + 'android-ndk-r30/build/cmake/android.toolchain.cmake',
                           ANDROID_ABI='arm64-v8a', ANDROID_PLATFORM='android-28', ANDROID_STL='c++_static')
        cmake = tool + 'cmake-3.31.6/bin/cmake.exe'
        commands = [[cmake, '-S', alias + 'research/lcm_prepare', '-B', alias + 'build/' + name, '-G', 'Ninja'] +
                    ['-D' + k + '=' + v for k, v in options.items()],
                    [cmake, '--build', alias + 'build/' + name, '--target', 'lma_lcm_prepare', '-j', '2']]
        if android:
            commands.append([tool + 'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe',
                             '--strip-unneeded', alias + 'build/' + name + '/bin/liblma-lcm-prepare.so'])
        for index, command in enumerate(commands):
            if android:
                result = subprocess.run(command, capture_output=True, timeout=300)
            else:
                setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
                script = directory / ('build-' + str(index) + '.cmd')
                script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' +
                                  subprocess.list2cmdline(command) + '\n', encoding='utf-8')
                result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (directory / ('build-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError('Inspect build/' + name + '/build-' + str(index) + '.log')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    data = binary.read_bytes()
    record = dict(schema='lma.lcm-preparer-build/1', android_arm64_compiled=android,
                  executable=binary.relative_to(ROOT).as_posix(), executable_bytes=len(data),
                  executable_sha256=hashlib.sha256(data).hexdigest(), input_fingerprint=before,
                  learned_data_embedded=False, mathematical_guidance_constants=256,
                  packaged_in_apk=False, production_app_integrated=False, physical_android=False,
                  model_inference=False, virtualization_used=False)
    if android:
        elf = elf_info(data)
        if (elf['machine'] != 'aarch64' or not elf['16k_elf_aligned'] or elf['android_api_notes'] != [28]
                or elf['interpreter'] != '/system/bin/linker64' or not elf['entry_point']
                or set(elf['needed']) - SYSTEM_LIBS):
            raise RuntimeError('Preparation CLI ELF contract failed')
        llvm = ROOT / 'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-nm.exe'
        imported = subprocess.check_output([str(llvm), '-D', '--undefined-only', str(binary)], text=True, encoding='utf-8')
        symbols = {line.split()[-1].split('@')[0] for line in imported.splitlines()}
        forbidden = symbols & {'connect', 'socket', 'getaddrinfo', 'system', 'popen', 'execve', 'execvp', 'posix_spawn'}
        if forbidden:
            raise RuntimeError('Unexpected network / child-process imports')
        record.update(elf=elf, android_platform=28, ndk='30.0.16248370', forbidden_network_process_imports=[])
    current(before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return binary, record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--android', action='store_true')
    path, record = build(parser.parse_args().android)
    print(json.dumps({k: v for k, v in record.items() if k not in ('input_fingerprint', 'elf')}))
