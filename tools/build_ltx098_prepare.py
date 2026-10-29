"""Build model-free streaming old-LTX asset preparation with native MSVC/NDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from evidence import fingerprint, current
from verify_package import elf_info, SYSTEM_LIBS

ROOT = Path(__file__).resolve().parents[1]


def inputs(vae=False):
    names=['research/ltx098_vae_prepare' if vae else 'research/ltx098_prepare', 'research/local_prepare',
           'tools/build_ltx098_prepare.py', 'third_party/ltx098-source-lock.json', 'third_party/ltx098-text-source-lock.json']
    if vae:names+=['tools/build_ltx098_vae_prepare.py','tools/prepare_ltx098_vae_templates.py','third_party/ltx098-vae-source-lock.json']
    return fingerprint(*names)


def build(android=False,vae=False):
    if os.name != 'nt': raise RuntimeError('Use native Windows MSVC/NDK tools')
    before = inputs(vae)
    if vae:
        proof=ROOT/'build/ltx098-vae-template-tests/results.json'
        if not proof.exists():proof=ROOT/'verification/development/ltx098-vae-templates.json'
        audit=json.loads(proof.read_text(encoding='utf-8'))
        current(audit['input_fingerprint']);current(audit['output_fingerprint'])
        if not (audit['passed'] and audit['all_graph_constants_classified'] and not audit['inline_learned_data']):raise RuntimeError('Architecture graphs need a current audit')
    lock = json.loads((ROOT / 'third_party/ltx098-text-source-lock.json').read_text(encoding='utf-8'))
    if hashlib.sha256((ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest() != lock['json_header_sha256']:
        raise RuntimeError('Changed pinned JSON header')
    stem='ltx098-vae-prepare' if vae else 'ltx098-prepare'
    source='ltx098_vae_prepare' if vae else 'ltx098_prepare';target='lma_'+source
    name=stem+('-arm64' if android else '-host')
    out = ROOT / 'build' / name; out.mkdir(exist_ok=True); (out / 'receipt.json').unlink(missing_ok=True)
    drive = next((c + ':' for c in 'RSTUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + '/'; tool = alias + 'build/toolchain/'; directory = alias + 'build/' + name
        options = dict(CMAKE_MAKE_PROGRAM=tool + 'cmake-3.31.6/bin/ninja.exe', CMAKE_BUILD_TYPE='Release',
                       LMA_JSON_SOURCE=alias + 'build/native-src/sd-cpp/thirdparty')
        if android:
            options.update(CMAKE_TOOLCHAIN_FILE=tool + 'android-ndk-r30/build/cmake/android.toolchain.cmake',
                           ANDROID_ABI='arm64-v8a', ANDROID_PLATFORM='android-28', ANDROID_STL='c++_static')
        cmake = tool + 'cmake-3.31.6/bin/cmake.exe'
        commands = [[cmake, '-S', alias + 'research/'+source, '-B', directory, '-G', 'Ninja'] +
                    ['-D' + k + '=' + v for k, v in options.items()],
                    [cmake, '--build', directory, '--target', target, '-j', '4']]
        if android:
            commands.append([tool + 'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe',
                             '--strip-unneeded', directory + '/bin/liblma-'+stem+'.so'])
        for i, command in enumerate(commands):
            if android: result = subprocess.run(command, capture_output=True, timeout=300)
            else:
                setup = Path(os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
                script = out / f'build-{i}.cmd'
                script.write_text('@echo off\ncall "' + str(setup) + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' +
                                  subprocess.list2cmdline(command) + '\n', encoding='utf-8')
                result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (out / f'build-{i}.log').write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError(f'Inspect build/{name}/build-{i}.log')
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    binary = out / 'bin' / ('liblma-'+stem+'.so' if android else target+'.exe')
    data = binary.read_bytes()
    record = dict(kind='android_compile' if android else 'host_compile', executable_bytes=len(data),
                  executable_sha256=hashlib.sha256(data).hexdigest(), model_data_embedded=False,
                  model_inference=False, engine_registered=False, packaged_in_apk=False,
                  physical_android=False, virtualization_used=False, input_fingerprint=before)
    if android:
        elf = elf_info(data)
        if not elf['16k_elf_aligned'] or elf['android_api_notes'] != [28] or elf['interpreter'] != '/system/bin/linker64' or not elf['entry_point']:
            raise RuntimeError('Preparation CLI ELF contract failed')
        if set(elf['needed']) - SYSTEM_LIBS: raise RuntimeError('Unexpected preparation dependency')
        llvm = ROOT / 'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-nm.exe'
        output = subprocess.check_output([str(llvm), '-D', '--undefined-only', str(binary)], text=True, encoding='utf-8')
        imported = {line.split()[-1].split('@')[0] for line in output.splitlines()}
        forbidden = imported & {'connect', 'socket', 'getaddrinfo', 'system', 'popen', 'execve', 'execvp', 'posix_spawn'}
        if forbidden: raise RuntimeError('Unexpected network/process import')
        record.update(android_arm64_compiled=True, android_platform=28, elf=elf, ndk='30.0.16248370',
                      forbidden_network_process_imports=sorted(forbidden))
    current(before)
    (out / 'receipt.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k not in ('input_fingerprint', 'elf')}), flush=True)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--android', action='store_true')
    build(parser.parse_args().android)
