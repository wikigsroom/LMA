"""Build the unregistered, offline LTX-Video 0.9.8 DiT research probe.

No model conversion/download, APK packaging or execution-support registration.
"""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from evidence import fingerprint,current

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/'third_party/ltx098-source-lock.json'

def validate_sources():
    lock=json.loads(LOCK.read_text(encoding='utf-8'))
    for source in lock['sources']:
        base=ROOT/source['directory']
        for name,digest in source['files'].items():
            if not (base/name).is_file() or hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest:
                raise RuntimeError('Pinned LTX source differs: '+source['name']+'/'+name)
        if source.get('verify_git'):
            actual=subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],text=True).strip()
            dirty=subprocess.check_output(['git','-C',str(base),'status','--porcelain','--untracked-files=no'],text=True).strip()
            if actual!=source['revision'] or dirty:raise RuntimeError('Pinned native source checkout changed: '+source['name'])
    return lock

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--android',action='store_true');parser.add_argument('--vulkan',action='store_true');args=parser.parse_args()
    lock=validate_sources(); inputs=fingerprint('research/ltx098','tools/build_ltx098.py','third_party/ltx098-source-lock.json')
    if os.name!='nt':raise RuntimeError('This reproducible path requires native Windows MSVC/NDK')
    name='ltx098-'+('arm64' if args.android else 'host')+('-vulkan' if args.vulkan else '-cpu')
    output=ROOT/'build'/name;output.mkdir(exist_ok=True);(output/'receipt.json').unlink(missing_ok=True)
    drive=next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst',drive,str(ROOT)],check=True,capture_output=True)
    try:
        alias=drive+'/'; tc=alias+'build/toolchain/'; cmake=tc+'cmake-3.31.6/bin/cmake.exe'; ndk=tc+'android-ndk-r30'; build=alias+'build/'+name
        command=[cmake,'-S',alias+'research/ltx098','-B',build,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+tc+'cmake-3.31.6/bin/ninja.exe',
            '-DCMAKE_BUILD_TYPE=Release','-DLMA_GGML_SOURCE='+alias+'build/native-src/sd-cpp/ggml','-DLMA_JSON_INCLUDE='+alias+'build/native-src/sd-cpp/thirdparty',
            '-DLMA_LTX_VULKAN='+('ON' if args.vulkan else 'OFF')]
        if args.android:command+=['-DCMAKE_TOOLCHAIN_FILE='+ndk+'/build/cmake/android.toolchain.cmake','-DANDROID_ABI=arm64-v8a','-DANDROID_PLATFORM=android-28','-DANDROID_STL=c++_static']
        if args.vulkan:
            includes=ROOT/'build/native-src/vulkan-headers/include'
            if not (includes/'vulkan/vulkan.hpp').is_file():raise RuntimeError('Explicit pinned Vulkan headers are required before Vulkan compilation')
            shaderc=lock['shaderc_windows']
            compiler=ROOT/shaderc['directory']/'bin/glslc.exe'
            for tool_name,digest in shaderc['files'].items():
                tool=ROOT/shaderc['directory']/tool_name
                if not tool.is_file() or hashlib.sha256(tool.read_bytes()).hexdigest()!=digest:
                    raise RuntimeError('Pinned native shaderc compiler is missing or changed; run tools/fetch_ltx098.py')
            command+=['-DVulkan_INCLUDE_DIR='+alias+'build/native-src/vulkan-headers/include','-DVulkan_GLSLC_EXECUTABLE='+alias+shaderc['directory']+'/bin/glslc.exe']
            if not args.android:
                # Link the system's existing Vulkan loader; do not copy/distribute it.
                loader=Path(os.environ['SystemRoot'])/'System32/vulkan-1.dll'
                if not loader.is_file():raise RuntimeError('Native host Vulkan loader is unavailable')
                setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
                script=output/'loader.cmd';script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\ndumpbin /exports "'+str(loader)+'"\n',encoding='utf-8')
                result=subprocess.run(['cmd','/d','/c','loader.cmd'],cwd=build,capture_output=True,timeout=30)
                if result.returncode:raise RuntimeError('Unable to inspect host Vulkan loader exports')
                import re
                names=re.findall(r'^\s+\d+\s+[0-9A-F]+\s+[0-9A-F]+\s+(vk\w+)\s*$',result.stdout.decode('utf-8',errors='replace'),re.MULTILINE)
                if len(names)<100 or 'vkGetInstanceProcAddr' not in names:raise RuntimeError('Incomplete Vulkan loader exports')
                (output/'vulkan-1.def').write_text('LIBRARY vulkan-1.dll\nEXPORTS\n'+'\n'.join(names)+'\n',encoding='ascii')
                script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\nlib /nologo /machine:x64 /def:vulkan-1.def /out:vulkan-1.lib\n',encoding='utf-8')
                result=subprocess.run(['cmd','/d','/c','loader.cmd'],cwd=build,capture_output=True,timeout=30)
                if result.returncode:raise RuntimeError('Unable to build local Vulkan import library')
                command+=['-DVulkan_LIBRARY='+build+'/vulkan-1.lib']
        commands=[]
        if args.vulkan:
            source=alias+'build/native-src/spirv-headers'; header_build=alias+'build/ltx098-spirv-headers'; prefix=alias+'build/ltx098-spirv-install'
            commands=[[cmake,'-S',source,'-B',header_build,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+tc+'cmake-3.31.6/bin/ninja.exe','-DSPIRV_HEADERS_ENABLE_TESTS=OFF','-DCMAKE_INSTALL_PREFIX='+prefix],
                      [cmake,'--install',header_build]]
            command+=['-DSPIRV-Headers_DIR='+prefix+'/share/cmake/SPIRV-Headers']
        commands += [command,[cmake,'--build',build,'--target','lma_ltx098_probe','-j','4']]
        setup=Path(os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat'))
        for i,cmd in enumerate(commands):
            # Android's Vulkan build also creates a native Windows shader generator.
            # Its child CMake must inherit both the host compiler and Ninja paths.
            script=output/('build-'+str(i)+'.cmd');script.write_text('@echo off\ncall "'+str(setup)+'" >nul\nif errorlevel 1 exit /b %errorlevel%\nset "PATH='+tc+'cmake-3.31.6/bin;%PATH%"\n'+subprocess.list2cmdline(cmd)+'\n',encoding='utf-8')
            result=subprocess.run(['cmd','/d','/c','build-'+str(i)+'.cmd'],cwd=build,capture_output=True,timeout=1200)
            (output/('build-'+str(i)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect build/'+name+'/build-'+str(i)+'.log')
        binary=output/('lma_ltx098_probe' if args.android else 'lma_ltx098_probe.exe')
        if args.android:
            llvm=ndk+'/toolchains/llvm/prebuilt/windows-x86_64/bin/'
            subprocess.run([llvm+'llvm-strip.exe','--strip-unneeded',build+'/lma_ltx098_probe'],check=True,capture_output=True)
            from verify_package import elf_info
            elf=elf_info(binary.read_bytes());assert elf['machine']=='aarch64' and elf['16k_elf_aligned'] and elf['android_api_notes']==[28]
            assert elf['interpreter']=='/system/bin/linker64'
            assert set(elf['needed']) <= {'libc.so','libm.so','libdl.so','libvulkan.so'}
            assert ('libvulkan.so' in elf['needed']) == args.vulkan
            (output/'elf.json').write_text(json.dumps(elf,indent=2)+'\n',encoding='utf-8')
    finally:subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    current(inputs)
    record=dict(source_revision=lock['sources'][0]['revision'],ggml_revision=lock['sources'][1]['revision'],
        backend='vulkan' if args.vulkan else 'cpu',android_arm64_compiled=args.android,min_sdk=28 if args.android else None,
        binary_bytes=binary.stat().st_size,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
        shaderc=lock['shaderc_windows'] if args.vulkan else None,
        elf=elf if args.android else None,
        packaged_in_apk=False,engine_registered=False,model_inference=False,physical_android=False,complete_video_pipeline=False,input_fingerprint=inputs)
    (output/'receipt.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='input_fingerprint'}))

if __name__=='__main__':main()
