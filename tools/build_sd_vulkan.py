"""Build the explicit local Wan Vulkan worker with native Windows tools only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from build_native import SD_REVISION, GGML_REVISION, git
from build_ltx098 import validate_sources
from evidence import current, fingerprint
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/sd_worker.cpp', 'native/sd_backend.hpp', 'native/sd_policy.hpp',
                       'native/lcm_condition.hpp', 'native/qwen_prompt.hpp', 'native/vocab_external.cpp',
                       'native/tokenizer_data.hpp', 'native/CMakeLists.txt', 'research/sd_vulkan_host',
                       'research/sd_host/compat', 'tools/build_sd_vulkan.py', 'tools/build_ltx098.py',
                       'third_party/ltx098-source-lock.json', 'third_party/notices/sd-sources.json')


def build(android=False, jobs=2):
    if os.name != 'nt' or not 1 <= jobs <= 4:
        raise RuntimeError('Use native Windows and one to four build jobs')
    if git('rev-parse', 'HEAD') != SD_REVISION or git('-C', 'ggml', 'rev-parse', 'HEAD') != GGML_REVISION:
        raise ValueError('Different pinned diffusion sources')
    if git('status', '--porcelain', '--untracked-files=no') or git('-C', 'ggml', 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Modified pinned diffusion sources')
    lock = validate_sources(); before = inputs()
    shaderc = lock['shaderc_windows']
    for name, expected in shaderc['files'].items():
        path = ROOT / shaderc['directory'] / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Pinned native shader compiler differs: ' + name)
    directory = ROOT / 'build' / ('sd-vulkan-arm64' if android else 'sd-vulkan-host')
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / 'receipt.json'
    filename = 'liblma-wan-vulkan.so' if android else 'lma_sd_vulkan_host.exe'
    binary = directory / (filename if android else 'bin/' + filename)
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        if saved['source_inputs'] == before and binary.is_file() and hashlib.sha256(binary.read_bytes()).hexdigest() == saved['sha256']:
            current(before)
            if android:
                shutil.copy2(binary, ROOT / 'app/src/main/jniLibs/arm64-v8a' / filename)
                (ROOT / 'build/wan-vulkan-build-info.json').write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
            return binary, saved
    cache = directory / 'CMakeCache.txt'
    drive = None
    if cache.exists():
        pattern = r'CMAKE_HOME_DIRECTORY:INTERNAL=([T-Z]):[/\\]'
        match = re.search(pattern, cache.read_text(encoding='utf-8'))
        if not match: raise ValueError('Preserve unexpected Vulkan CMake cache')
        drive = match[1] + ':'
        if Path(drive + '/').exists(): raise RuntimeError('The Vulkan build alias is currently owned')
    if drive is None: drive = next((x + ':' for x in 'TUVWXYZ' if not Path(x + '/').exists()), None)
    if drive is None: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    log = directory / 'build.log'
    log.write_bytes(b'')
    try:
        alias = drive + '/'; tc = alias + 'build/toolchain/'; out = alias + directory.relative_to(ROOT).as_posix()
        cmake = tc + 'cmake-3.31.6/bin/cmake.exe'
        ninja = tc + 'cmake-3.31.6/bin/ninja.exe'
        setup = Path(os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
        if not setup.is_file(): raise RuntimeError('Native MSVC tools are required for shader generation')
        def run(args, timeout=3600):
            script = directory / 'command.cmd'
            script.write_text('@echo off\ncall "' + str(setup) + '" >nul\nif errorlevel 1 exit /b %errorlevel%\nset "PATH=' + tc + 'cmake-3.31.6/bin;%PATH%"\n' + subprocess.list2cmdline([str(a) for a in args]) + '\n', encoding='utf-8')
            with log.open('ab') as stream:
                result = subprocess.run(['cmd', '/d', '/c', 'command.cmd'], cwd=directory, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            if result.returncode: raise RuntimeError('Vulkan build failed; inspect ' + str(log))
        prefix = alias + 'build/ltx098-spirv-install'
        if not (ROOT / 'build/ltx098-spirv-install/share/cmake/SPIRV-Headers/SPIRV-HeadersConfig.cmake').is_file():
            run([cmake, '-S', alias + 'build/native-src/spirv-headers', '-B', alias + 'build/ltx098-spirv-headers', '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DSPIRV_HEADERS_ENABLE_TESTS=OFF', '-DCMAKE_INSTALL_PREFIX=' + prefix])
            run([cmake, '--install', alias + 'build/ltx098-spirv-headers'])
        command = [cmake, '-S', alias + ('native' if android else 'research/sd_vulkan_host'), '-B', out, '-G', 'Ninja', '-DCMAKE_MAKE_PROGRAM=' + ninja, '-DCMAKE_BUILD_TYPE=Release', '-DLMA_SD_REVISION=' + SD_REVISION,
                   '-DVulkan_INCLUDE_DIR=' + alias + 'build/native-src/vulkan-headers/include', '-DVulkan_GLSLC_EXECUTABLE=' + alias + shaderc['directory'] + '/bin/glslc.exe', '-DSPIRV-Headers_DIR=' + prefix + '/share/cmake/SPIRV-Headers']
        if android:
            ndk = tc + 'android-ndk-r30'
            command += ['-DCMAKE_TOOLCHAIN_FILE=' + ndk + '/build/cmake/android.toolchain.cmake', '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-28', '-DANDROID_STL=c++_static', '-DLMA_SD_SOURCE=' + alias + 'build/native-src/sd-cpp', '-DLMA_SD_VULKAN=ON']
        else:
            loader = Path(os.environ['SystemRoot']) / 'System32/vulkan-1.dll'
            if not loader.is_file(): raise RuntimeError('No native Windows Vulkan loader')
            script = directory / 'exports.cmd'
            script.write_text('@echo off\ncall "' + str(setup) + '" >nul\nif errorlevel 1 exit /b %errorlevel%\ndumpbin /exports "' + str(loader) + '"\n', encoding='utf-8')
            result = subprocess.run(['cmd', '/d', '/c', 'exports.cmd'], cwd=directory, capture_output=True, timeout=30)
            if result.returncode: raise RuntimeError('Cannot inspect native Vulkan loader')
            names = re.findall(r'^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(vk\w+)\s*$', result.stdout.decode('utf-8', errors='replace'), re.MULTILINE)
            if len(names) < 100 or 'vkGetInstanceProcAddr' not in names: raise ValueError('Incomplete Vulkan loader exports')
            (directory / 'vulkan-1.def').write_text('LIBRARY vulkan-1.dll\nEXPORTS\n' + '\n'.join(names) + '\n', encoding='ascii')
            run(['lib', '/nologo', '/machine:x64', '/def:vulkan-1.def', '/out:vulkan-1.lib'])
            command += ['-DVulkan_LIBRARY=' + out + '/vulkan-1.lib']
        run(command)
        print('Compile pinned Vulkan worker: ' + ('Android ARM64' if android else 'native Windows'), flush=True)
        run([cmake, '--build', out, '--target', 'lma_sd_worker' if android else 'lma_sd_vulkan_host', '-j', str(jobs)])
        if android: run([tc + 'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe', '--strip-unneeded', out + '/' + filename])
        data = binary.read_bytes(); current(before)
        saved = dict(schema='lma.native-build/1', engine='wan_sd_cpp', source_revision=SD_REVISION, ggml_revision=GGML_REVISION, backend='vulkan', file=filename, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     vocabularies='external_user_selected_components', physical_device_tests=0, model_inference_tested=False, virtualization_used=False, source_inputs=before,
                     module_backends=dict(text='cpu', vae='cpu', diffusion='vulkan0'), gpu_execution_requires_completed_operation=True, remote_inference=False)
        if android:
            elf = elf_info(data)
            if elf['machine'] != 'aarch64' or not elf['16k_elf_aligned'] or any(api > 28 for api in elf['android_api_notes']): raise ValueError('Vulkan ELF/API contract differs')
            saved.update(abi='arm64-v8a', min_sdk=28, ndk='30.0.16248370', elf_load_alignment=elf['load_segment_alignment'])
            shutil.copy2(binary, ROOT / 'app/src/main/jniLibs/arm64-v8a' / filename)
            (ROOT / 'build/wan-vulkan-build-info.json').write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
        else: saved.update(abi='windows-x86_64', compiler='native MSVC')
        receipt.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
        return binary, saved
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--android', action='store_true'); parser.add_argument('--jobs', type=int, default=2)
    args = parser.parse_args(); binary, receipt = build(args.android, args.jobs)
    print(json.dumps(dict(file=binary.relative_to(ROOT).as_posix(), sha256=receipt['sha256'], backend='vulkan', android=args.android)), flush=True)


if __name__ == '__main__': main()
