"""Build the reviewed chat-parser fix with native Windows Android NDK tools.

Only libllama-common.so is replaced. The pinned publisher archive and every other
runtime library retain their original identity. No weights or virtualization.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'b29c606e28a01b1bc8c1351026a0fa6e616bf6c4'
SOURCE = ROOT / 'build/native-src/llama-chat-runtime'
PATCH = ROOT / 'third_party/patches/0002-bare-json-parallel-tools.patch'
LOCK = ROOT / 'third_party/runtime-lock.json'
LIBS = ROOT / 'app/src/main/jniLibs/arm64-v8a'
LIBRARY = 'libllama-common.so'
BASE_SHA = '9d6870185327144cc8a34d8479e17a6e8ff51f28df8ccb56a0daadb3e5aec345'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], stderr=subprocess.PIPE)


def prepare_source():
    if not SOURCE.exists():
        SOURCE.mkdir(parents=True)
        subprocess.run(['git', 'init', str(SOURCE)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(SOURCE), 'config', 'core.autocrlf', 'false'], check=True)
        subprocess.run(['git', '-C', str(SOURCE), 'fetch', '--depth', '1', 'https://github.com/ggml-org/llama.cpp.git', REVISION], check=True)
        subprocess.run(['git', '-C', str(SOURCE), 'checkout', '--detach', REVISION], check=True)
    assert git('rev-parse', 'HEAD').decode().strip() == REVISION, 'Wrong native revision'
    expected = PATCH.read_bytes()
    paths = ['common/chat-peg-parser.cpp', 'common/chat-peg-parser.h', 'common/chat.cpp']
    diff = git('diff', '--', *paths)
    if not diff:
        subprocess.run(['git', '-C', str(SOURCE), 'apply', '--check', str(PATCH)], check=True)
        subprocess.run(['git', '-C', str(SOURCE), 'apply', str(PATCH)], check=True)
        diff = git('diff', '--', *paths)
    assert diff == expected, 'Native parser differs from the reviewed patch'
    changes = git('status', '--porcelain', '--untracked-files=no').decode().splitlines()
    assert changes == [' M ' + path for path in paths], 'Unexpected native source modifications'


def verify_patch_record():
    lock = json.loads(LOCK.read_text('utf8'))
    record = lock.get('local_chat_parser_build', {})
    assert record.get('source_revision') == REVISION, 'Build reviewed chat runtime before packaging'
    assert record.get('patch_sha256') == sha(PATCH), 'Chat parser patch provenance is stale'
    assert record.get('library_sha256') == sha(LIBS / LIBRARY), 'Patched chat runtime differs'
    assert record.get('base_library_sha256') == BASE_SHA
    assert record.get('unmodified_runtime_libraries_preserved') is True
    assert record.get('abi_required_symbols_preserved') is True
    assert record.get('linked_against_retained_runtime') is True
    assert record.get('cpp_imports_resolved_against_retained_runtime') is True
    assert record.get('android_load_alignment_at_least') == 16384
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    if args.verify:
        print(json.dumps(verify_patch_record(), ensure_ascii=True)); return
    assert os.name == 'nt', 'Use native Windows NDK tools'
    assert 1 <= args.jobs <= 16
    prepare_source()
    lock = json.loads(LOCK.read_text('utf8'))
    assert lock['asset_sha256'] == '551e5be8494bd2ae9955992faaaca1a4f5cf29e3a97f90d2e04205eb460fcde6'
    before = {r['name']: sha(LIBS / r['name']) for r in lock['files']}
    assert all(r['sha256'] == before[r['name']] for r in lock['files']), 'Pinned runtime file mismatch'
    cache = ROOT / 'build/llama-chat-android-packaged/CMakeCache.txt'
    previous = re.search(r'CMAKE_HOME_DIRECTORY:INTERNAL=([A-Z]):/', cache.read_text('utf8')) if cache.exists() else None
    drive = previous[1] + ':' if previous else next(c + ':' for c in 'RSTUVWXYZ' if not Path(c + ':/').exists())
    assert not Path(drive + '/').exists(), 'Temporary build alias is occupied'
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    out = ROOT / 'build/llama-chat-android-packaged'; out.mkdir(exist_ok=True)
    log = out / 'build.log'; log.write_bytes(b'')
    ndk = ROOT / 'build/toolchain/android-ndk-r30'
    llvm = ndk / 'toolchains/llvm/prebuilt/windows-x86_64/bin'
    def logged(command):
        with log.open('ab') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        assert result.returncode == 0, 'Inspect build/llama-chat-android-packaged/build.log'
    try:
        cmake = drive + '/build/toolchain/cmake-3.31.6/bin/cmake.exe'
        build = drive + '/build/llama-chat-android-packaged'
        command = [cmake, '-S', drive + '/native/chat-runtime', '-B', build, '-G', 'Ninja',
                   '-DLMA_LLAMA_SOURCE=' + drive + '/build/native-src/llama-chat-runtime',
                   '-DLMA_BASE_RUNTIME=' + drive + '/app/src/main/jniLibs/arm64-v8a',
                   '-DCMAKE_MAKE_PROGRAM=' + drive + '/build/toolchain/cmake-3.31.6/bin/ninja.exe',
                   '-DCMAKE_TOOLCHAIN_FILE=' + drive + '/build/toolchain/android-ndk-r30/build/cmake/android.toolchain.cmake',
                   '-DANDROID_ABI=arm64-v8a', '-DANDROID_PLATFORM=android-28', '-DANDROID_STL=c++_static',
                   '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON', '-DLLAMA_BUILD_COMMON=ON',
                   '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_TOOLS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF',
                   '-DLLAMA_BUILD_SERVER=OFF', '-DLLAMA_BUILD_APP=OFF', '-DLLAMA_BUILD_MTMD=OFF', '-DLLAMA_OPENSSL=OFF',
                   '-DLLAMA_CURL=OFF', '-DLLAMA_SUBPROCESS=OFF', '-DGGML_NATIVE=OFF', '-DGGML_CPU=OFF',
                   '-DGGML_OPENMP=OFF', '-DGGML_VULKAN=OFF', '-DGGML_CUDA=OFF',
                   '-DCMAKE_SHARED_LINKER_FLAGS=-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384']
        print('Configure pinned Android chat runtime', flush=True); logged(command)
        print('Build reviewed libllama-common.so', flush=True)
        logged([cmake, '--build', build, '--target', 'llama-common', '-j', str(args.jobs)])
        candidates = list(out.rglob(LIBRARY))
        assert len(candidates) == 1, 'Ambiguous common library output'
        built = candidates[0]
        subprocess.run([str(llvm / 'llvm-strip.exe'), '--strip-unneeded', str(built)], check=True)
        def symbols(path):
            result = subprocess.check_output([str(llvm / 'llvm-readelf.exe'), '--dyn-syms', '--wide', str(path)], text=True)
            defined, undefined = set(), set()
            for line in result.splitlines():
                cols = line.split()
                if len(cols) >= 8 and cols[0].rstrip(':').isdigit() and cols[4] in ('GLOBAL', 'WEAK'):
                    (undefined if cols[6] == 'UND' else defined).add(cols[7].split('@')[0])
            return defined, undefined
        old_symbols, _ = symbols(LIBS / LIBRARY)
        new_symbols, new_undefined = symbols(built)
        used = set()
        for record in lock['files']:
            if record['name'] != LIBRARY:
                used.update(symbols(LIBS / record['name'])[1] & old_symbols)
        missing = used - new_symbols
        assert not missing, 'Required native ABI symbols missing: ' + ', '.join(sorted(missing))
        # Verify all llama/ggml imports against the retained publisher libraries.
        available = set()
        for record in lock['files']:
            if record['name'] != LIBRARY:
                available.update(symbols(LIBS / record['name'])[0])
        required = {s for s in new_undefined if s.startswith(('llama_', 'ggml_', '_Z'))}
        assert required <= available, 'Native imports differ from the retained runtime'
        dynamic = subprocess.check_output([str(llvm / 'llvm-readelf.exe'), '-d', str(built)], text=True)
        needed = re.findall(r'\(NEEDED\).*\[(.*?)\]', dynamic)
        assert set(needed) <= {'libllama.so', 'libggml.so', 'libggml-base.so', 'libm.so', 'libdl.so', 'libc.so', 'liblog.so'}
        segments = subprocess.check_output([str(llvm / 'llvm-readelf.exe'), '-l', '--wide', str(built)], text=True)
        alignments = [int(line.split()[-1], 16) for line in segments.splitlines() if line.strip().startswith('LOAD ')]
        assert alignments and min(alignments) >= 16384
        shutil.copyfile(built, LIBS / LIBRARY)
        assert all(sha(LIBS / name) == digest for name, digest in before.items() if name != LIBRARY)
        entry = next(r for r in lock['files'] if r['name'] == LIBRARY)
        entry.update(size=built.stat().st_size, sha256=sha(built))
        record = dict(source_repository='https://github.com/ggml-org/llama.cpp', source_revision=REVISION,
                      patch=PATCH.relative_to(ROOT).as_posix(), patch_sha256=sha(PATCH),
                      library=LIBRARY, library_sha256=entry['sha256'], base_library_sha256=BASE_SHA,
                      toolchain='Android NDK r30 / Windows x86_64 / CMake 3.31.6 / Ninja',
                      android_api=28, abi='arm64-v8a', stl='c++_static',
                      unmodified_runtime_libraries_preserved=True, abi_required_symbols_preserved=True,
                      required_symbol_count=len(used), android_load_alignment_at_least=min(alignments),
                      linked_against_retained_runtime=True, cpp_imports_resolved_against_retained_runtime=True,
                      shared_dependencies=needed, modified_library_is_publisher_original=False,
                      bare_final_envelope_only_recovery=True, argument_json_repair=False,
                      incomplete_final_native_records_rejected=True,
                      model_weights_downloaded=False, model_inference_tested=False, virtualization_used=False)
        lock['publisher_digest_scope'] = 'Original downloaded archive; the locally patched library has separate provenance below'
        lock['local_chat_parser_build'] = record
        LOCK.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + '\n', 'utf8')
        print(json.dumps(record), flush=True)
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)


if __name__ == '__main__':
    main()
