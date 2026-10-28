"""Native Windows NDK ARM64 Stable Audio LiteRT CPU build; code only."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from evidence import fingerprint
from fetch_stable_audio import validate_sources,runtime
from verify_package import elf_info
ROOT=Path(__file__).resolve().parents[1]

def main():
    if os.name!='nt':raise RuntimeError('Use native Windows toolchain')
    lock=json.loads((ROOT/'third_party/stable-audio-source-lock.json').read_text(encoding='utf-8'));sources=validate_sources(lock);cache=runtime(lock)
    if hashlib.sha256((ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest()!=lock['json_header_sha256']:raise RuntimeError('JSON header changed')
    inputs=fingerprint('native/stable_audio','tools/build_stable_audio.py','tools/fetch_stable_audio.py','third_party/stable-audio-source-lock.json')
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True);log=ROOT/'build/stable-audio-build.log';log.write_bytes(b'')
    try:
        alias=drive+'/';ndk=alias+'build/toolchain/android-ndk-r30';cmake=alias+'build/toolchain/cmake-3.31.6/bin/cmake.exe';output=alias+'build/stable-audio-arm64-cpu-r30'
        options=dict(ANDROID_ABI='arm64-v8a',ANDROID_PLATFORM='android-28',ANDROID_STL='c++_static',CMAKE_BUILD_TYPE='Release',LMA_SENTENCEPIECE_SOURCE=alias+'build/native-src/sentencepiece',LMA_LITERT_SDK=alias+'build/litert-probe/litert_cc_sdk',LMA_LITERT_RUNTIME=alias+'build/litert-probe/libLiteRt.so',LMA_JSON_SOURCE=alias+'build/native-src/sd-cpp/thirdparty',LMA_SAO_REVISION=sources['arm-audiogen'])
        commands=[[cmake,'-S',alias+'native/stable_audio','-B',output,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+alias+'build/toolchain/cmake-3.31.6/bin/ninja.exe','-DCMAKE_TOOLCHAIN_FILE='+ndk+'/build/cmake/android.toolchain.cmake']+['-D'+k+'='+v for k,v in options.items()],[cmake,'--build',output,'--target','lma_stable_audio_worker','-j','4'],[ndk+'/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',output+'/liblma-stable-audio.so']]
        for command in commands:
            r=subprocess.run(command,cwd=alias,capture_output=True)
            with log.open('ab') as f:f.write(r.stdout+r.stderr)
            print('\n'.join((r.stdout+r.stderr).decode('utf-8',errors='replace').splitlines()[-6:]),flush=True)
            if r.returncode:raise RuntimeError('Inspect build/stable-audio-build.log')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=ROOT/'build/stable-audio-arm64-cpu-r30/liblma-stable-audio.so';data=binary.read_bytes();info=elf_info(data);cpu=elf_info((cache/'libLiteRt.so').read_bytes())
    if not info['16k_elf_aligned'] or info['android_api_notes']!=[28] or info['interpreter']!='/system/bin/linker64' or not cpu['16k_elf_aligned'] or cpu['android_api_notes']!=[23]:raise RuntimeError('LiteRT ELF/API contract failed')
    ndk_bin=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
    imports=subprocess.check_output([str(ndk_bin/'llvm-nm.exe'),'-D','--undefined-only',str(binary)],text=True)
    if {line.split()[-1].split('@')[0] for line in imports.splitlines()} & {'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn','__android_log_print','__android_log_vprint','__android_log_write'}:raise RuntimeError('Unexpected worker network/process/log imports')
    runtime_imports=subprocess.check_output([str(ndk_bin/'llvm-nm.exe'),'-D','--undefined-only',str(cache/'libLiteRt.so')],text=True)
    if {line.split()[-1].split('@')[0] for line in runtime_imports.splitlines()} & {'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn'}:raise RuntimeError('Unexpected runtime network or process imports')
    exports=subprocess.check_output([str(ndk_bin/'llvm-nm.exe'),'-D','--defined-only',str(binary)],text=True)
    if not {'__android_log_print','__android_log_vprint','__android_log_write'}.issubset({line.split()[-1] for line in exports.splitlines()}):raise RuntimeError('Runtime log isolation symbols are missing')
    for p in [binary,cache/'libLiteRt.so']:shutil.copy2(p,ROOT/'app/src/main/jniLibs/arm64-v8a'/p.name)
    dependency={k:lock['runtime'][k] for k in ('file','bytes','sha256','android_api_notes')}
    receipt=dict(schema='lma.native-build/1',engine='stable_audio_litert',file=binary.name,source_revision=sources['arm-audiogen'],sources=sources,runtime_version='2.2.0',abi='arm64-v8a',backend='cpu',ndk='30.0.16248370',min_sdk=28,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),elf_load_alignment=info['load_segment_alignment'],android_api_notes=[28],dependencies=[dependency],source_inputs=inputs,vocabularies='external_user_selected_components',model_inference_tested=False,physical_device_tests=0,virtualization_used=False)
    (ROOT/'build/stable-audio-build-info.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:receipt[k] for k in ('engine','bytes','sha256')}))

if __name__=='__main__':main()
