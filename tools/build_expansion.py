"""Build actual CPU workers with native Windows CMake/MSVC or Android NDK."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint, current
from fetch_expansion_sources import verify, sha
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    'speech_extra': ('audio_cpp', 'lma-speech-extra', 'audio'),
    'mesh': ('trellis_native', 'lma-mesh', 'trellis'),
}


def inputs(engine):
    return fingerprint('native/' + engine, 'native/worker_common.hpp', 'tools/build_expansion.py', 'tools/fetch_expansion_sources.py',
                       'third_party/expansion-source-lock.json')


def build(engine, host=False):
    assert os.name == 'nt', 'Native Windows build only'
    lock = verify(); entry = next(x for x in lock['sources'] if x['id'] == CONFIG[engine][2])
    before = inputs(engine)
    drive = None
    for letter in ('UVWXYZT' if engine == 'speech_extra' else 'TUVWXYZ'):
        candidate = letter + ':'
        if Path(candidate + '/').exists():
            continue
        if subprocess.run(['subst', candidate, str(ROOT)], capture_output=True).returncode == 0:
            drive = candidate
            break
    assert drive, 'No unused owned build alias'
    output = ROOT / ('build/' + engine + ('-host' if host else '-arm64'))
    output.mkdir(parents=True, exist_ok=True)
    try:
        a = drive + '/'; cmake = a + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        ndk = a + 'build/toolchain/android-ndk-r30'
        destination = a + output.relative_to(ROOT).as_posix()
        command = [cmake, '-S', a + 'native/' + engine, '-B', destination, '-G', 'Ninja',
                   '-DCMAKE_MAKE_PROGRAM=' + a + 'build/toolchain/cmake-3.31.6/bin/ninja.exe',
                   '-DCMAKE_BUILD_TYPE=Release',
                   '-DLMA_AUDIO_SOURCE=' + a + 'build/native-src/audio-cpp-ssh',
                   '-DLMA_TRELLIS_SOURCE=' + a + 'build/native-src/trellis-cpp',
                   '-DLMA_JSON_SOURCE=' + a + 'build/native-src/sd-cpp/thirdparty']
        if not host:
            command += ['-DCMAKE_TOOLCHAIN_FILE=' + ndk + '/build/cmake/android.toolchain.cmake',
                        '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-28', '-DANDROID_STL=c++_static']
        for index, cmd in enumerate((command, [cmake, '--build', destination, '--target', CONFIG[engine][1], '-j', '4'])):
            if host:
                setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
                script = output / ('step-' + str(index) + '.cmd')
                script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' +
                                  subprocess.list2cmdline(cmd) + '\n', encoding='utf-8')
                result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True)
            else:
                result = subprocess.run(cmd, capture_output=True)
            (output / ('step-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            print((result.stdout + result.stderr).decode('utf-8', errors='replace')[-1000:], flush=True)
            if result.returncode:
                raise RuntimeError('Inspect ' + str(output.relative_to(ROOT)) + '/step-' + str(index) + '.log')
        if not host:
            binary = output / ('lib' + CONFIG[engine][1] + '.so')
            subprocess.run([ndk + '/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe',
                            '--strip-unneeded', destination + '/' + binary.name], check=True, capture_output=True)
        else:
            binary = output / (CONFIG[engine][1] + '.exe')
            if not binary.exists():
                binary = output / 'bin' / binary.name
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    current(before)
    receipt = dict(schema='lma.native-build/1', engine=CONFIG[engine][0], file=binary.name,
                   source_revision=entry['revision'], abi='windows-x64' if host else 'arm64-v8a', backend='cpu',
                   ndk=None if host else '30.0.16248370', min_sdk=None if host else 28,
                   bytes=binary.stat().st_size, sha256=sha(binary), dependencies=[],
                   source_inputs=before, vocabularies='external_user_selected_components',
                   physical_device_tests=0, model_inference_tested=False, virtualization_used=False)
    if not host:
        info = elf_info(binary.read_bytes())
        assert info['16k_elf_aligned'] and info['android_api_notes'] == [28]
        receipt.update(elf_load_alignment=info['load_segment_alignment'], android_api_notes=[28])
        shutil.copy2(binary, ROOT / 'app/src/main/jniLibs/arm64-v8a' / binary.name)
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if not host:
        (ROOT / 'build' / (engine + '-build-info.json')).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'source_inputs'}))
    return binary, receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('engine', choices=CONFIG)
    parser.add_argument('--host', action='store_true')
    args = parser.parse_args()
    build(args.engine, args.host)
