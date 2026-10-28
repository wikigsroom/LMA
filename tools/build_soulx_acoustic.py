"""Compile unregistered SoulX acoustic ORT/CPU CLI for Android ARM64/API28.

This does not copy a worker to jniLibs or register an App engine. No models
are downloaded, exported, packaged or executed by this compilation check.
"""
import hashlib,json,os,subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_soulx_dsp import validate_sources
from verify_package import elf_info,SYSTEM_LIBS
ROOT=Path(__file__).resolve().parents[1]


def main():
    if os.name!='nt':raise RuntimeError('Use native Windows NDK tools')
    lock=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    validate_sources(lock)
    if hashlib.sha256((ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest()!=lock['json_header_sha256']:raise RuntimeError('Pinned JSON header changed')
    runtime=ROOT/'app/src/main/jniLibs/arm64-v8a'/lock['android_runtime']['file'];runtime_data=runtime.read_bytes()
    if len(runtime_data)!=lock['android_runtime']['bytes'] or hashlib.sha256(runtime_data).hexdigest()!=lock['android_runtime']['sha256']:raise RuntimeError('Pinned Android ORT runtime changed')
    inputs=fingerprint('research/soulx_acoustic','research/soulx_ort','research/soulx','native/moss_nano/onnx_external.hpp','tools/build_soulx_acoustic.py','tools/fetch_soulx_dsp.py','third_party/soulx-acoustic-source-lock.json')
    out=ROOT/'build/soulx-acoustic-arm64';out.mkdir(exist_ok=True);(out/'receipt.json').unlink(missing_ok=True)
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias=drive+'/';tc=alias+'build/toolchain/';ndk=tc+'android-ndk-r30'
        cmake=tc+'cmake-3.31.6/bin/cmake.exe';output=alias+'build/soulx-acoustic-arm64'
        options=dict(ANDROID_ABI='arm64-v8a',ANDROID_PLATFORM='android-28',ANDROID_STL='c++_static',CMAKE_BUILD_TYPE='Release',
            LMA_KISSFFT_SOURCE=alias+'build/native-src/kissfft',
            LMA_ORT_HEADERS=alias+'build/native-src/onnxruntime-headers/include/onnxruntime/core/session',
            LMA_ORT_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libonnxruntime.so',
            LMA_JSON_SOURCE=alias+'build/native-src/sd-cpp/thirdparty')
        commands=[[cmake,'-S',alias+'research/soulx_acoustic','-B',output,'-G','Ninja',
            '-DCMAKE_MAKE_PROGRAM='+tc+'cmake-3.31.6/bin/ninja.exe',
            '-DCMAKE_TOOLCHAIN_FILE='+ndk+'/build/cmake/android.toolchain.cmake']+['-D'+k+'='+v for k,v in options.items()],
            [cmake,'--build',output,'--target','lma_soulx_acoustic_cli','-j','4'],
            [ndk+'/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',output+'/liblma-soulx-acoustic.so']]
        for index,command in enumerate(commands):
            result=subprocess.run(command,capture_output=True,timeout=240)
            (out/('build-'+str(index)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect build/soulx-acoustic-arm64/build-'+str(index)+'.log')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=out/'liblma-soulx-acoustic.so';data=binary.read_bytes();info=elf_info(data);dependency=elf_info(runtime_data)
    if not info['16k_elf_aligned'] or info['android_api_notes']!=[28] or info['interpreter']!='/system/bin/linker64' or info['entry_point']==0:raise RuntimeError('Worker ELF/API contract failed')
    if not dependency['16k_elf_aligned'] or dependency['android_api_notes']!=lock['android_runtime']['android_api_notes']:raise RuntimeError('ORT ELF/API contract failed')
    if 'libonnxruntime.so' not in info['needed'] or set(info['needed'])-SYSTEM_LIBS-{'libonnxruntime.so'}:raise RuntimeError('Unresolved acoustic dependencies')
    llvm=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
    def symbols(path,kind):
        output=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D',kind,str(path)],text=True,encoding='utf-8')
        (out/(path.stem+kind+'.txt')).write_text(output,encoding='utf-8')
        return {line.split()[-1].split('@')[0] for line in output.splitlines()}
    forbidden={'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn'}
    logs={'__android_log_print','__android_log_vprint','__android_log_write'}
    if symbols(binary,'--undefined-only') & (forbidden|logs) or symbols(runtime,'--undefined-only') & forbidden:raise RuntimeError('Unexpected network/process/log imports')
    if not logs.issubset(symbols(binary,'--defined-only')):raise RuntimeError('Missing isolated runtime log exports')
    current(inputs)
    receipt=dict(android_arm64_compiled=True,android_platform=28,abi='arm64-v8a',backend='cpu',ndk='30.0.16248370',
        executable_bytes=len(data),executable_sha256=hashlib.sha256(data).hexdigest(),elf=info,
        runtime_version='1.28.2',runtime=lock['android_runtime'],c_api_minimum=17,
        engine_registered=False,packaged_in_apk=False,model_inference=False,physical_android=False,virtualization_used=False,input_fingerprint=inputs)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['elf','input_fingerprint','runtime']}))

if __name__=='__main__':main()
