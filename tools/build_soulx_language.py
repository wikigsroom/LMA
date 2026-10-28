"""Native Windows host or unregistered Android SoulX language compilation."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_soulx_language import sources
from verify_package import elf_info,SYSTEM_LIBS
ROOT=Path(__file__).resolve().parents[1]

def build(android=False):
    if os.name!='nt':raise RuntimeError('Use native Windows compilers')
    lock=sources();json_header=ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp'
    if hashlib.sha256(json_header.read_bytes()).hexdigest()!=lock['json_header_sha256']:raise RuntimeError('Changed JSON dependency')
    inputs=fingerprint('research/soulx_language','tools/build_soulx_language.py','tools/fetch_soulx_language.py','third_party/soulx-language-source-lock.json')
    name='soulx-language-arm64' if android else 'soulx-language-host';out=ROOT/'build'/name;out.mkdir(exist_ok=True);(out/'receipt.json').unlink(missing_ok=True)
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias=drive+'/';tool=alias+'build/toolchain/';cmake=tool+'cmake-3.31.6/bin/cmake.exe';build_dir=alias+'build/'+name
        options=dict(CMAKE_MAKE_PROGRAM=tool+'cmake-3.31.6/bin/ninja.exe',CMAKE_BUILD_TYPE='Release',LMA_LLAMA_SOURCE=alias+'build/native-src/llama-soulx',LMA_JSON_SOURCE=alias+'build/native-src/sd-cpp/thirdparty')
        if android:
            for item in lock['android_runtime_files']:
                p=ROOT/'app/src/main/jniLibs/arm64-v8a'/item['name']
                if p.stat().st_size!=item['size'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:raise RuntimeError('Changed packaged language runtime')
            options.update(CMAKE_TOOLCHAIN_FILE=tool+'android-ndk-r30/build/cmake/android.toolchain.cmake',ANDROID_ABI='arm64-v8a',ANDROID_PLATFORM='android-28',ANDROID_STL='c++_static',LMA_LLAMA_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libllama.so',LMA_GGML_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libggml.so')
        commands=[[cmake,'-S',alias+'research/soulx_language','-B',build_dir,'-G','Ninja']+['-D'+k+'='+v for k,v in options.items()],
            [cmake,'--build',build_dir,'--target','lma_soulx_language_cli']+([] if android else ['lma_soulx_quantize','lma_soulx_policy'])+['-j','4']]
        if android:commands.append([tool+'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',build_dir+'/liblma-soulx-language.so'])
        for i,command in enumerate(commands):
            if android:result=subprocess.run(command,capture_output=True,timeout=900)
            else:
                import subprocess as sp
                setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
                script=out/('build-'+str(i)+'.cmd');script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+sp.list2cmdline(command)+'\n',encoding='utf-8')
                result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True,timeout=900)
            (out/('build-'+str(i)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect '+name+'/build-'+str(i)+'.log')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=out/('liblma-soulx-language.so' if android else 'bin/lma_soulx_language_cli.exe');data=binary.read_bytes();receipt=dict(kind='android_compile' if android else 'host_compile',executable_bytes=len(data),executable_sha256=hashlib.sha256(data).hexdigest(),llama_revision=lock['sources'][0]['revision'],backend='cpu',engine_registered=False,packaged_in_apk=False,model_inference=False,physical_android=False,virtualization_used=False,input_fingerprint=inputs)
    if android:
        elf=elf_info(data);assert elf['16k_elf_aligned'] and elf['android_api_notes']==[28] and elf['entry_point'] and elf['interpreter']=='/system/bin/linker64'
        assert not(set(elf['needed'])-SYSTEM_LIBS-{'libllama.so','libggml.so','libggml-base.so'})
        llvm=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
        symbols=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D','--undefined-only',str(binary)],text=True,encoding='utf-8')
        imports={line.split()[-1].split('@')[0] for line in symbols.splitlines()}
        assert not imports & {'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn'}
        for item in lock['android_runtime_files']:
            dependency=elf_info((ROOT/'app/src/main/jniLibs/arm64-v8a'/item['name']).read_bytes());assert dependency['16k_elf_aligned']
        receipt.update(android_arm64_compiled=True,android_platform=28,elf=elf,runtime_files=lock['android_runtime_files'],ndk='30.0.16248370',network_process_imports=False)
    else:
        quantizer=out/'bin/lma_soulx_quantize.exe';receipt['quantizer_sha256']=hashlib.sha256(quantizer.read_bytes()).hexdigest()
        receipt['policy_sha256']=hashlib.sha256((out/'bin/lma_soulx_policy.exe').read_bytes()).hexdigest()
    current(inputs);(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in receipt.items() if k not in ['input_fingerprint','elf','runtime_files']}),flush=True);return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--android',action='store_true');args=parser.parse_args();build(args.android)
