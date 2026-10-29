"""Build signed-App old-LTX stages on native Windows. No model downloads or execution."""
import argparse, hashlib, importlib.metadata, json, os, re, shutil, subprocess
from pathlib import Path
from evidence import fingerprint, current
from build_ltx098 import validate_sources
from fetch_ltx098_text import sources as text_sources
from verify_package import elf_info, SYSTEM_LIBS

ROOT=Path(__file__).resolve().parents[1]
STAGES={'tensors':'lma_ltx098_tensors','text':'lma_ltx098_text_cli','sample':'lma_ltx098_app_sample','vae':'lma_ltx098_vae_cli'}

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while block:=stream.read(4*1024*1024):digest.update(block)
    return digest.hexdigest()

def inputs():
    return fingerprint('native/ltx098','research/ltx098','research/ltx098_text','research/ltx098_pipeline','research/ltx098_vae',
        'research/soulx_ort','research/soulx/dsp.hpp','native/moss_nano/onnx_external.hpp','tools/build_ltx098_app.py',
        'tools/build_ltx098.py','tools/fetch_ltx098_text.py','third_party/ltx098-source-lock.json','third_party/ltx098-text-source-lock.json',
        'third_party/ltx098-vae-source-lock.json','third_party/ltx098-pipeline-source-lock.json','third_party/soulx-acoustic-source-lock.json')

def build(android=False):
    if os.name!='nt':raise RuntimeError('Use native Windows tools; no virtualization')
    lock=validate_sources(); text=text_sources(); before=inputs()
    vae=json.loads((ROOT/'third_party/ltx098-vae-source-lock.json').read_text(encoding='utf-8'))
    runtime=json.loads((ROOT/'third_party/soulx-acoustic-source-lock.json').read_text(encoding='utf-8'))
    header=next(s for s in runtime['sources'] if s['name']=='onnxruntime-headers')
    for name,digest in header['reviewed_files'].items():
        if sha(ROOT/'build/native-src/onnxruntime-headers'/name)!=digest:raise RuntimeError('Changed ORT header')
    name='ltx098-app-'+('arm64' if android else 'host');out=ROOT/'build'/name;out.mkdir(exist_ok=True)
    (out/'receipt.json').unlink(missing_ok=True)
    drive=next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free private ASCII alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    compiled=[]
    try:
        alias=drive+'/';tool=alias+'build/toolchain/';cmake=tool+'cmake-3.31.6/bin/cmake.exe'
        setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
        def execute(command,directory,label,prelude=''):
            script=directory/(label+'.cmd')
            script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\nset "PATH='+tool+'cmake-3.31.6/bin;%PATH%"\n'+prelude+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
            result=subprocess.run(['cmd','/d','/c',str(script)],cwd=directory,capture_output=True,timeout=1800)
            (directory/(label+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect '+str((directory/(label+'.log')).relative_to(ROOT)))
            return result
        prefix=alias+'build/ltx098-spirv-install'
        if not (ROOT/'build/ltx098-spirv-install/share/cmake/SPIRV-Headers/SPIRV-HeadersConfig.cmake').exists():
            execute([cmake,'-S',alias+'build/native-src/spirv-headers','-B',alias+'build/ltx098-spirv-headers','-G','Ninja',
                '-DCMAKE_MAKE_PROGRAM='+tool+'cmake-3.31.6/bin/ninja.exe','-DSPIRV_HEADERS_ENABLE_TESTS=OFF','-DCMAKE_INSTALL_PREFIX='+prefix],out,'spirv-configure')
            execute([cmake,'--install',alias+'build/ltx098-spirv-headers'],out,'spirv-install')
        loader=None
        if not android:
            system_loader=Path(os.environ['SystemRoot'])/'System32/vulkan-1.dll'
            dumped=execute(['dumpbin','/exports',str(system_loader)],out,'loader-exports')
            names=re.findall(r'^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(vk\w+)\s*$',dumped.stdout.decode('utf-8',errors='replace'),re.MULTILINE)
            if len(names)<100 or 'vkGetInstanceProcAddr' not in names:raise RuntimeError('Incomplete system Vulkan exports')
            (out/'vulkan-1.def').write_text('LIBRARY vulkan-1.dll\nEXPORTS\n'+'\n'.join(names)+'\n',encoding='ascii')
            execute(['lib','/nologo','/machine:x64','/def:vulkan-1.def','/out:vulkan-1.lib'],out,'loader-import')
            loader=alias+'build/'+name+'/vulkan-1.lib'
        for stage,target in STAGES.items():
            directory=out/stage;directory.mkdir(exist_ok=True);build_path=alias+'build/'+name+'/'+stage
            options=dict(CMAKE_MAKE_PROGRAM=tool+'cmake-3.31.6/bin/ninja.exe',CMAKE_BUILD_TYPE='Release',LMA_STAGE=stage,
                LMA_JSON_SOURCE=alias+'build/native-src/sd-cpp/thirdparty',LMA_JSON_INCLUDE=alias+'build/native-src/sd-cpp/thirdparty',
                LMA_LLAMA_SOURCE=alias+'build/native-src/llama-soulx',LMA_GGML_SOURCE=alias+'build/native-src/sd-cpp/ggml',
                LMA_ORT_HEADERS=alias+'build/native-src/onnxruntime-headers/include/onnxruntime/core/session')
            if android:
                options.update(CMAKE_TOOLCHAIN_FILE=tool+'android-ndk-r30/build/cmake/android.toolchain.cmake',ANDROID_ABI='arm64-v8a',ANDROID_PLATFORM='android-28',ANDROID_STL='c++_static')
                for item in text['android_runtime_files']:
                    path=ROOT/'app/src/main/jniLibs/arm64-v8a'/item['name']
                    if path.stat().st_size!=item['size'] or sha(path)!=item['sha256']:raise RuntimeError('Changed T5 CPU dependency')
                for key,file in [('LMA_LLAMA_LIBRARY','libllama.so'),('LMA_GGML_LIBRARY','libggml.so'),('LMA_GGML_BASE_LIBRARY','libggml-base.so'),('LMA_ORT_LIBRARY','libonnxruntime.so')]:options[key]=alias+'app/src/main/jniLibs/arm64-v8a/'+file
                ort=vae['android_runtime'];file=ROOT/'app/src/main/jniLibs/arm64-v8a'/ort['file']
                if file.stat().st_size!=ort['bytes'] or sha(file)!=ort['sha256']:raise RuntimeError('Changed ORT CPU dependency')
            elif stage=='vae':
                distribution=importlib.metadata.distribution('onnxruntime');dll=Path(distribution.locate_file('onnxruntime/capi/onnxruntime.dll'))
                if distribution.version!=vae['host_runtime']['version'] or sha(dll)!=vae['host_runtime']['sha256']:raise RuntimeError('Changed host ORT runtime')
                (directory/'bin').mkdir(exist_ok=True);shutil.copyfile(dll,directory/'bin/onnxruntime.dll')
                (directory/'ort.def').write_text('LIBRARY onnxruntime.dll\nEXPORTS\nOrtGetApiBase\n',encoding='ascii')
                execute(['lib','/nologo','/machine:x64','/def:ort.def','/out:onnxruntime.lib'],directory,'ort-import')
                options.update(LMA_ORT_LIBRARY=build_path+'/bin/onnxruntime.dll',LMA_ORT_IMPORT_LIBRARY=build_path+'/onnxruntime.lib')
            if stage=='sample':
                shader=lock['shaderc_windows']
                for file,digest in shader['files'].items():
                    if sha(ROOT/shader['directory']/file)!=digest:raise RuntimeError('Changed pinned shader compiler')
                options.update(LMA_LTX_VULKAN='ON',Vulkan_INCLUDE_DIR=alias+'build/native-src/vulkan-headers/include',
                    Vulkan_GLSLC_EXECUTABLE=alias+shader['directory']+'/bin/glslc.exe',**{'SPIRV-Headers_DIR':prefix+'/share/cmake/SPIRV-Headers'})
                if not android:options['Vulkan_LIBRARY']=loader
            execute([cmake,'-S',alias+'native/ltx098','-B',build_path,'-G','Ninja']+['-D'+k+'='+v for k,v in options.items()],directory,'configure')
            print('Building local LTX App stage: '+stage,flush=True)
            execute([cmake,'--build',build_path,'--target',target,'-j','4'],directory,'compile')
            file='liblma-ltx098-app-'+stage+'.so' if android else 'lma-ltx098-app-'+stage+'.exe';binary=directory/'bin'/file
            item=dict(stage=stage,file=file,bytes=binary.stat().st_size,sha256=sha(binary),path=str(binary.relative_to(ROOT)).replace('\\','/'))
            if android:
                execute([tool+'android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',build_path+'/bin/'+file],directory,'strip')
                item.update(bytes=binary.stat().st_size,sha256=sha(binary));elf=elf_info(binary.read_bytes())
                if elf['machine']!='aarch64' or not elf['16k_elf_aligned'] or elf['android_api_notes']!=[28] or elf['interpreter']!='/system/bin/linker64':raise RuntimeError('Invalid Android stage ELF')
                allowed=SYSTEM_LIBS|{'libllama.so','libggml.so','libggml-base.so','libonnxruntime.so','libvulkan.so'}
                if set(elf['needed'])-allowed:raise RuntimeError('Unreviewed native dependencies')
                item['elf']=elf
            compiled.append(item)
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    current(before)
    record=dict(schema='lma.ltx098-app-build/1',android_arm64_compiled=android,min_sdk=28 if android else None,stages=compiled,
        source_revision=lock['sources'][0]['revision'],ggml_revision=lock['sources'][1]['revision'],llama_revision=text['source']['revision'],
        ndk='30.0.16248370' if android else None,model_inference=False,physical_android=False,quality_accepted=False,numerical_accepted=False,
        no_automatic_model_download=True,virtualization_used=False,input_fingerprint=before)
    (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['input_fingerprint','stages']}),flush=True);return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--android',action='store_true');build(parser.parse_args().android)
