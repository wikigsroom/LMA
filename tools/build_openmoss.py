"""Build a real ARM64 CPU openmoss worker using Windows NDK/CMake, without model data."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint
from fetch_openmoss import validate_sources
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != 'nt': raise RuntimeError('Use native Windows NDK tools')
    lock = json.loads((ROOT/'third_party/openmoss-source-lock.json').read_text(encoding='utf-8'))
    source=validate_sources(lock)
    if hashlib.sha256((ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest() != lock['json_header_sha256']: raise RuntimeError('Pinned JSON header changed')
    inputs = fingerprint('native/openmoss','tools/build_openmoss.py','tools/fetch_openmoss.py','third_party/openmoss-source-lock.json')
    drive = next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No unused build path alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    log = ROOT/'build/openmoss-build.log'; log.write_bytes(b'')
    try:
        alias=drive+'/'; ndk=alias+'build/toolchain/android-ndk-r30'; cmake=alias+'build/toolchain/cmake-3.31.6/bin/cmake.exe'; output=alias+'build/openmoss-arm64-cpu-r30'
        options={'ANDROID_ABI':'arm64-v8a','ANDROID_PLATFORM':'android-28','ANDROID_STL':'c++_static','CMAKE_BUILD_TYPE':'Release','BUILD_SHARED_LIBS':'OFF','GGML_NATIVE':'OFF','GGML_CPU_ARM_ARCH':'armv8-a','GGML_CPU_ALL_VARIANTS':'OFF','GGML_BACKEND_DL':'OFF','GGML_OPENMP':'OFF','GGML_CPU_KLEIDIAI':'OFF','GGML_BLAS':'OFF','GGML_CUDA':'OFF','GGML_VULKAN':'OFF','GGML_OPENCL':'OFF','GGML_METAL':'OFF','GGML_BUILD_TESTS':'OFF','GGML_BUILD_EXAMPLES':'OFF','GGML_CCACHE':'OFF','LLAMA_BUILD_COMMON':'OFF','LLAMA_BUILD_TESTS':'OFF','LLAMA_BUILD_TOOLS':'OFF','LLAMA_BUILD_EXAMPLES':'OFF','LLAMA_BUILD_SERVER':'OFF','LLAMA_CURL':'OFF','LLAMA_OPENSSL':'OFF','LLAMA_BUILD_NUMBER':'1','LLAMA_BUILD_COMMIT':lock['llama_revision']}
        commands=[[cmake,'-S',alias+'native/openmoss','-B',output,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+alias+'build/toolchain/cmake-3.31.6/bin/ninja.exe','-DCMAKE_TOOLCHAIN_FILE='+ndk+'/build/cmake/android.toolchain.cmake',
            '-DLMA_OPENMOSS_SOURCE='+alias+'build/native-src/openmoss','-DLMA_JSON_SOURCE='+alias+'build/native-src/sd-cpp/thirdparty','-DLMA_OPENMOSS_REVISION='+lock['revision']]+['-D'+k+'='+v for k,v in options.items()],
            [cmake,'--build',output,'--target','lma_openmoss_worker','-j','4'],[ndk+'/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',output+'/liblma-openmoss.so']]
        for command in commands:
            result=subprocess.run(command,cwd=alias,capture_output=True)
            with log.open('ab') as stream: stream.write(result.stdout+result.stderr)
            print('\n'.join((result.stdout+result.stderr).decode('utf-8',errors='replace').splitlines()[-5:]),flush=True)
            if result.returncode: raise RuntimeError('openmoss build failed; inspect build/openmoss-build.log')
    finally: subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=ROOT/'build/openmoss-arm64-cpu-r30/liblma-openmoss.so';data=binary.read_bytes();info=elf_info(data)
    if not info['16k_elf_aligned'] or info['android_api_notes'] != [28] or info['interpreter'] != '/system/bin/linker64': raise RuntimeError('MOSS ELF/API contract failed')
    ndk_bin=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
    imports=subprocess.check_output([str(ndk_bin/'llvm-nm.exe'),'-D','--undefined-only',str(binary)],text=True)
    forbidden={'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn','__android_log_print','__android_log_vprint','__android_log_write'}
    if {line.split()[-1].split('@')[0] for line in imports.splitlines()} & forbidden: raise RuntimeError('Review unexpected network/logcat imports')
    validate_sources(lock);shutil.copy2(binary,ROOT/'app/src/main/jniLibs/arm64-v8a/liblma-openmoss.so')
    receipt=dict(schema='lma.native-build/1',engine='openmoss_native',file=binary.name,source_revision=lock['revision'],llama_revision=lock['llama_revision'],abi='arm64-v8a',backend='cpu',ndk='30.0.16248370',min_sdk=28,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),elf_load_alignment=info['load_segment_alignment'],android_api_notes=[28],source_inputs=inputs,vocabularies='external_user_selected_components',model_inference_tested=False,physical_device_tests=0,virtualization_used=False)
    (ROOT/'build/openmoss-build-info.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('engine','bytes','sha256','source_revision')}))


if __name__ == '__main__': main()
