"""Build the unregistered T5 CPU encoder on native Windows or for Android ARM64."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_ltx098_text import sources
from verify_package import elf_info,SYSTEM_LIBS

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('research/ltx098_text','tools/build_ltx098_text.py','tools/fetch_ltx098_text.py','third_party/ltx098-text-source-lock.json')


def build(android=False):
    if os.name!='nt':raise RuntimeError('Use native Windows compilers; no virtualization')
    lock=sources();record=inputs();name='ltx098-text-arm64' if android else 'ltx098-text-host'
    out=ROOT/'build'/name;out.mkdir(exist_ok=True);(out/'receipt.json').unlink(missing_ok=True)
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias=drive+'/';tool=alias+'build/toolchain/';cmake=tool+'cmake-3.31.6/bin/cmake.exe';build_dir=alias+'build/'+name
        options=dict(CMAKE_MAKE_PROGRAM=tool+'cmake-3.31.6/bin/ninja.exe',CMAKE_BUILD_TYPE='Release',LMA_LLAMA_SOURCE=alias+'build/native-src/llama-soulx',LMA_JSON_SOURCE=alias+'build/native-src/sd-cpp/thirdparty')
        if android:
            for item in lock['android_runtime_files']:
                data=(ROOT/'app/src/main/jniLibs/arm64-v8a'/item['name']).read_bytes()
                if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise RuntimeError('Changed packaged CPU runtime')
            options.update(CMAKE_TOOLCHAIN_FILE=tool+'android-ndk-r30/build/cmake/android.toolchain.cmake',ANDROID_ABI='arm64-v8a',ANDROID_PLATFORM='android-28',ANDROID_STL='c++_static',LMA_LLAMA_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libllama.so',LMA_GGML_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libggml.so',LMA_GGML_BASE_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libggml-base.so')
        commands=[[cmake,'-S',alias+'research/ltx098_text','-B',build_dir,'-G','Ninja']+['-D'+k+'='+v for k,v in options.items()],
            [cmake,'--build',build_dir,'--target','lma_ltx098_text_cli','-j','4']]
        if android:commands.append([tool+'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',build_dir+'/liblma-ltx098-text.so'])
        for i,command in enumerate(commands):
            if android:result=subprocess.run(command,capture_output=True,timeout=900)
            else:
                setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
                script=out/f'build-{i}.cmd';script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
                result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True,timeout=900)
            (out/f'build-{i}.log').write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(f'Inspect build/{name}/build-{i}.log')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=out/('liblma-ltx098-text.so' if android else 'bin/lma_ltx098_text_cli.exe');data=binary.read_bytes()
    receipt=dict(kind='android_compile' if android else 'host_compile',executable_bytes=len(data),executable_sha256=hashlib.sha256(data).hexdigest(),
        llama_revision=lock['source']['revision'],backend='cpu',engine_registered=False,packaged_in_apk=False,model_inference=False,
        physical_android=False,virtualization_used=False,input_fingerprint=record)
    if android:
        elf=elf_info(data);assert elf['16k_elf_aligned'] and elf['android_api_notes']==[28] and elf['entry_point'] and elf['interpreter']=='/system/bin/linker64'
        assert not(set(elf['needed'])-SYSTEM_LIBS-{'libllama.so','libggml.so','libggml-base.so'})
        llvm=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
        symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D','--undefined-only',str(binary)],text=True,encoding='utf-8')
        imports={line.split()[-1].split('@')[0] for line in symbols.splitlines()}
        assert not imports & {'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn'}
        for item in lock['android_runtime_files']:assert elf_info((ROOT/'app/src/main/jniLibs/arm64-v8a'/item['name']).read_bytes())['16k_elf_aligned']
        receipt.update(android_arm64_compiled=True,android_platform=28,elf=elf,runtime_files=lock['android_runtime_files'],ndk='30.0.16248370',network_process_imports=False)
    current(record);(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['input_fingerprint','elf','runtime_files']}),flush=True);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--android',action='store_true');build(parser.parse_args().android)
