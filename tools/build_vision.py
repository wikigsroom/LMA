"""Compile the local vision CPU worker using native Windows host/NDK tools.

Code-only, offline, pinned inputs. --android copies only the worker to the
App native directory. Never prepares, converts or downloads model assets.
"""
import argparse,hashlib,importlib.metadata,json,os,shutil,subprocess
from pathlib import Path
from evidence import fingerprint,current
from fetch_soulx_language import sources
from fetch_vision_sources import verify
from verify_package import elf_info,SYSTEM_LIBS
ROOT=Path(__file__).resolve().parents[1]

def source_inputs():
    return fingerprint('native/vision','tests/expansion-native/vision.cpp','native/rf_shape/ort.hpp','native/rf_shape/image.hpp','native/worker_common.hpp','native/runtime_metrics.hpp','native/moss_nano/onnx_external.hpp','research/soulx_ort/android_log.cpp','tools/build_vision.py','tools/fetch_vision_sources.py','third_party/vision-source-lock.json','third_party/soulx-language-source-lock.json','third_party/soulx-acoustic-source-lock.json','build/native-src/onnxruntime-headers/include/onnxruntime/core/session','build/native-src/pixal3d-mv-cpp/thirdparty/stb/stb_image.h','build/native-src/pixal3d-mv-cpp/thirdparty/stb/stb_image_write.h')


def build(android=False):
    if os.name!='nt':raise RuntimeError('Native Windows toolchains required')
    language=sources()
    acoustic=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'));verify()
    if hashlib.sha256((ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest()!=acoustic['json_header_sha256']:raise RuntimeError('Changed JSON header')
    headers=next(s for s in acoustic['sources'] if s['name']=='onnxruntime-headers')
    for relative,digest in headers['reviewed_files'].items():
        if hashlib.sha256((ROOT/'build/native-src/onnxruntime-headers'/relative).read_bytes()).hexdigest()!=digest:raise RuntimeError('Changed pinned ORT source: '+relative)
    inputs=source_inputs();name='vision-worker-arm64' if android else 'vision-worker-host';out=ROOT/'build'/name;out.mkdir(exist_ok=True);(out/'receipt.json').unlink(missing_ok=True)
    if android:(ROOT/'build/vision-build-info.json').unlink(missing_ok=True)
    ort=ROOT/'app/src/main/jniLibs/arm64-v8a/libonnxruntime.so';runtime=acoustic['android_runtime'];deps=[]
    if android:
        for item in [dict(name=runtime['file'],size=runtime['bytes'],sha256=runtime['sha256'])]:
            p=ort.parent/item['name'];data=p.read_bytes();info=elf_info(data)
            if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256'] or not info['16k_elf_aligned']:raise RuntimeError('Changed shared Android runtime: '+p.name)
            deps.append(dict(file=p.name,bytes=len(data),sha256=item['sha256'],android_api_notes=info['android_api_notes']))
    else:
        distribution=importlib.metadata.distribution('onnxruntime');dll=Path(distribution.locate_file('onnxruntime/capi/onnxruntime.dll'))
        if distribution.version!=acoustic['host_runtime']['version'] or hashlib.sha256(dll.read_bytes()).hexdigest()!=acoustic['host_runtime']['sha256']:raise RuntimeError('Changed host ORT runtime')
        (out/'bin').mkdir(exist_ok=True);shutil.copyfile(dll,out/'bin/onnxruntime.dll');(out/'ort.def').write_text('LIBRARY onnxruntime.dll\nEXPORTS\nOrtGetApiBase\n',encoding='ascii')
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias=drive+'/';tool=alias+'build/toolchain/';cmake=tool+'cmake-3.31.6/bin/cmake.exe';directory=alias+'build/'+name
        options=dict(LMA_LLAMA_SOURCE=alias+'build/native-src/llama-soulx',CMAKE_MAKE_PROGRAM=tool+'cmake-3.31.6/bin/ninja.exe',CMAKE_BUILD_TYPE='Release',LMA_JSON_SOURCE=alias+'build/native-src/sd-cpp/thirdparty',LMA_STB_SOURCE=alias+'build/native-src/pixal3d-mv-cpp/thirdparty/stb',LMA_ORT_HEADERS=alias+'build/native-src/onnxruntime-headers/include/onnxruntime/core/session')
        if android:options.update(CMAKE_TOOLCHAIN_FILE=tool+'android-ndk-r30/build/cmake/android.toolchain.cmake',ANDROID_ABI='arm64-v8a',ANDROID_PLATFORM='android-28',ANDROID_STL='c++_static',LMA_ORT_LIBRARY=alias+'app/src/main/jniLibs/arm64-v8a/libonnxruntime.so')
        else:options.update(LMA_ORT_LIBRARY=directory+'/bin/onnxruntime.dll',LMA_ORT_IMPORT_LIBRARY=directory+'/onnxruntime.lib')
        commands=[[cmake,'-S',alias+'native/vision','-B',directory,'-G','Ninja']+['-D'+k+'='+v for k,v in options.items()],
                  [cmake,'--build',directory,'--target','lma_vision_worker']+([] if android else ['lma_vision_contract'])+['-j','4']]
        if android:commands.append([tool+'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',directory+'/liblma-vision.so'])
        for i,command in enumerate(commands):
            if android:result=subprocess.run(command,capture_output=True,timeout=900)
            else:
                setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
                script=out/('build-'+str(i)+'.cmd');script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\nlib /nologo /def:"'+directory+'/ort.def" /machine:x64 /out:"'+directory+'/onnxruntime.lib"\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
                result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True,timeout=900)
            (out/('build-'+str(i)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect build/'+name+'/build-'+str(i)+'.log')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=out/('liblma-vision.so' if android else 'bin/lma_vision_worker.exe');data=binary.read_bytes()
    receipt=dict(schema='lma.native-build/1',engine='vision_cpu',file='liblma-vision.so',source_revision='b6764e20381f6f42a70f83fa3324181529ed1403',llama_revision=language['sources'][0]['revision'],backend='cpu',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),source_inputs=inputs,model_inference_tested=False,physical_device_tests=0,virtualization_used=False)
    if android:
        info=elf_info(data)
        if not info['16k_elf_aligned'] or info['android_api_notes']!=[28] or info['interpreter']!='/system/bin/linker64' or not info['entry_point'] or set(info['needed'])-SYSTEM_LIBS-{d['file'] for d in deps}:raise RuntimeError('Vision ELF/dependency/API contract failed')
        llvm=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
        forbidden={'connect','socket','getaddrinfo','system','popen','execve','execvp','posix_spawn'};logs={'__android_log_print','__android_log_vprint','__android_log_write'}
        def symbols(path,kind):
            value=subprocess.check_output([str(llvm/'llvm-nm.exe'),'-D',kind,str(path)],text=True,encoding='utf-8');return {line.split()[-1].split('@')[0] for line in value.splitlines()}
        if symbols(binary,'--undefined-only') & (forbidden|logs) or not logs.issubset(symbols(binary,'--defined-only')):raise RuntimeError('Vision network/process/log isolation failed')
        for dep in deps:
            if symbols(ort.parent/dep['file'],'--undefined-only') & forbidden:raise RuntimeError('Shared runtime has network/process imports')
        receipt.update(abi='arm64-v8a',ndk='30.0.16248370',min_sdk=28,android_api_notes=[28],elf_load_alignment=info['load_segment_alignment'],dependencies=deps,vocabularies='external_user_selected_components',runtime_version='ORT 1.28.2 API17 + static llama.cpp mtmd',required_model_components='per_pipeline')
        shutil.copy2(binary,ort.parent/binary.name);(ROOT/'build/vision-build-info.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    current(inputs);(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:receipt[k] for k in ['engine','bytes','sha256','model_inference_tested','physical_device_tests']}),flush=True);return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--android',action='store_true');args=parser.parse_args();build(args.android)
