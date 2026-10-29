"""Build unchanged production Qwen Base CPU worker natively on Windows."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from evidence import current, fingerprint
from fetch_qwen_tts import validate_sources
from fetch_sd15_trained import sha

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/qwen_tts','research/qwen_tts_host','research/moss_nano_host/compat',
        'research/sd_host/platform.hpp','third_party/qwen-tts-source-lock.json','tools/build_qwen_tts_host.py','tools/fetch_qwen_tts.py')


def build():
    if os.name!='nt':raise RuntimeError('Native Windows MSVC required')
    before=inputs();lock=json.loads((ROOT/'third_party/qwen-tts-source-lock.json').read_text(encoding='utf-8'))
    if not (ROOT/'build/native-src/qwen3-tts/ggml/include/ggml.h').is_file():raise RuntimeError('Explicitly fetch reviewed Qwen source first')
    source=validate_sources(lock)
    if sha(ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp')!=lock['json_header_sha256']:raise ValueError('Different pinned JSON header')
    key=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()[:16]
    folder=ROOT/'build/qwen-tts-worker-host'/key;binary=folder/'bin/lma_qwen_tts_host.exe';receipt=folder/'receipt.json'
    if receipt.exists():
        value=json.loads(receipt.read_text(encoding='utf-8'));current(value['input_fingerprint'])
        if value['input_fingerprint']!=before or sha(binary)!=value['sha256']:raise ValueError('Changed immutable Qwen host build')
        return binary,value
    folder.mkdir(parents=True,exist_ok=True)
    drive=next((c+':' for c in 'TUVWXYZ' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No unused owned build alias')
    subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
    try:
        def alias(path):return drive+'/'+path.relative_to(ROOT).as_posix()
        cmake=alias(ROOT/'build/toolchain/cmake-3.31.6/bin/cmake.exe')
        options={name:'OFF' for name in ['BUILD_SHARED_LIBS','GGML_NATIVE','GGML_CPU_ALL_VARIANTS','GGML_BACKEND_DL','GGML_OPENMP',
            'GGML_BLAS','GGML_CUDA','GGML_VULKAN','GGML_OPENCL','GGML_METAL','GGML_BUILD_TESTS','GGML_BUILD_EXAMPLES','GGML_CCACHE']}
        commands=[[cmake,'-S',alias(ROOT/'research/qwen_tts_host'),'-B',alias(binary.parent),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_MAKE_PROGRAM='+alias(ROOT/'build/toolchain/cmake-3.31.6/bin/ninja.exe'),'-DROOT='+drive+'/',
            '-DQWEN_SOURCE='+alias(source),'-DLMA_QWEN_REVISION='+lock['revision']]+['-D'+key+'='+value for key,value in options.items()],
            [cmake,'--build',alias(binary.parent),'--target','lma_qwen_tts_host','-j','2']]
        setup=os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index,command in enumerate(commands):
            script=folder/('build-'+str(index)+'.cmd')
            script.write_text('@echo off\ncall "'+setup+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
            print('Qwen host build stage',index+1,'/ 2',flush=True)
            result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True,timeout=900)
            (folder/('build-'+str(index)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect Qwen native host build log: '+str(folder.relative_to(ROOT)))
    finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before);validate_sources(lock)
    value=dict(schema='lma.qwen-tts-host-build/1',executable=binary.relative_to(ROOT).as_posix(),bytes=binary.stat().st_size,sha256=sha(binary),
        source_revision=lock['revision'],ggml_revision=lock['ggml_revision'],compiled_library_sources=len(lock['compiled_sources']),
        backend='cpu',production_worker_source_unmodified=True,upstream_sources_unmodified=True,windows_crt_parent_environment_compatibility=True,
        bundled_model_data=False,physical_android=False,android_compiled=False,packaged_in_apk=False,model_executed=False,input_fingerprint=before)
    receipt.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');return binary,value


if __name__=='__main__':
    binary,value=build();print(json.dumps({key:value[key] for key in ['executable','bytes','sha256']}),flush=True)
