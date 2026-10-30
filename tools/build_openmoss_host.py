"""Build unchanged production openmoss CPU worker natively on Windows."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from evidence import current, fingerprint
from fetch_openmoss import validate_sources
from openmoss_pipeline import guarded_pipeline, guarded_model
from fetch_sd15_trained import sha

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('native/openmoss','research/openmoss_host','research/moss_nano_host/compat','research/qwen_tts_host/compat',
        'tests/native/openmoss_mapping_test.cpp','research/sd_host/platform.hpp','third_party/openmoss-source-lock.json','tools/build_openmoss_host.py','tools/fetch_openmoss.py','tools/openmoss_pipeline.py')


def build():
    if os.name!='nt':raise RuntimeError('Native Windows MSVC required')
    before=inputs();lock=json.loads((ROOT/'third_party/openmoss-source-lock.json').read_text(encoding='utf-8'))
    if not (ROOT/'build/native-src/openmoss/third_party/llama.cpp/ggml/include/ggml.h').is_file():raise RuntimeError('Explicitly fetch reviewed openmoss source first')
    source=validate_sources(lock)
    generated=ROOT/'build/openmoss-generated';generated.mkdir(parents=True,exist_ok=True)
    for name,content in [('pipeline.cpp',guarded_pipeline(source)),('model.cpp',guarded_model(source))]:
        path=generated/name
        if not path.exists() or path.read_text(encoding='utf-8')!=content:path.write_text(content,encoding='utf-8')
    if sha(ROOT/'build/native-src/sd-cpp/thirdparty/json.hpp')!=lock['json_header_sha256']:raise ValueError('Different pinned JSON header')
    key=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()[:16]
    folder=ROOT/'build/openmoss-worker-host'/key;binary=folder/'bin/lma_openmoss_host.exe';receipt=folder/'receipt.json'
    if receipt.exists():
        value=json.loads(receipt.read_text(encoding='utf-8'));current(value['input_fingerprint'])
        if value['input_fingerprint']!=before or sha(binary)!=value['sha256']:raise ValueError('Changed immutable openmoss host build')
        return binary,value
    folder.mkdir(parents=True,exist_ok=True)
    drive=next((c+':' for c in 'UVWXYZT' if not Path(c+':/').exists()),None)
    if not drive:raise RuntimeError('No unused owned build alias')
    subprocess.run(['subst',drive,str(ROOT)],capture_output=True,check=True)
    try:
        def alias(path):return drive+'/'+path.relative_to(ROOT).as_posix()
        # Reuse compiled objects; keep every fingerprint's executable snapshot immutable.
        cache=ROOT/'build/openmoss-host-cache'/('cpu-'+lock['llama_revision'][:12]+'-'+drive[0])/'bin'
        cache.mkdir(parents=True,exist_ok=True)
        cmake=alias(ROOT/'build/toolchain/cmake-3.31.6/bin/cmake.exe')
        options={name:'OFF' for name in ['LLAMA_BUILD_COMMON','LLAMA_BUILD_TESTS','LLAMA_BUILD_TOOLS','LLAMA_BUILD_EXAMPLES','LLAMA_BUILD_SERVER','LLAMA_CURL','LLAMA_OPENSSL','BUILD_SHARED_LIBS','GGML_NATIVE','GGML_CPU_ALL_VARIANTS','GGML_BACKEND_DL','GGML_OPENMP',
            'GGML_BLAS','GGML_CUDA','GGML_VULKAN','GGML_OPENCL','GGML_METAL','GGML_BUILD_TESTS','GGML_BUILD_EXAMPLES','GGML_CCACHE']}
        commands=[[cmake,'-S',alias(ROOT/'research/openmoss_host'),'-B',alias(cache),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
            '-DCMAKE_MAKE_PROGRAM='+alias(ROOT/'build/toolchain/cmake-3.31.6/bin/ninja.exe'),'-DROOT='+drive+'/',
            '-DLMA_MAPPED_MODEL='+alias(generated/'model.cpp'),'-DLMA_GUARDED_PIPELINE='+alias(generated/'pipeline.cpp'),'-DOPENMOSS_SOURCE='+alias(source),'-DLMA_OPENMOSS_REVISION='+lock['revision']]+['-D'+key+'='+value for key,value in options.items()],
            [cmake,'--build',alias(cache),'--target','lma_openmoss_host','lma_openmoss_mapping_test','-j','4']]
        setup=os.environ.get('LMA_VCVARS',r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index,command in enumerate(commands):
            script=folder/('build-'+str(index)+'.cmd')
            script.write_text('@echo off\ncall "'+setup+'" >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(command)+'\n',encoding='utf-8')
            print('openmoss host build stage',index+1,'/ 2',flush=True)
            result=subprocess.run(['cmd','/d','/c',str(script)],capture_output=True,timeout=900)
            (folder/('build-'+str(index)+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError('Inspect openmoss native host build log: '+str(folder.relative_to(ROOT)))
    finally:subprocess.run(['subst',drive,'/D'],capture_output=True,check=True)
    current(before);validate_sources(lock)
    import shutil
    binary.parent.mkdir(parents=True,exist_ok=True)
    for name in ['lma_openmoss_host.exe','lma_openmoss_mapping_test.exe']:
        shutil.copy2(cache/name,binary.parent/name)
    value=dict(schema='lma.openmoss-host-build/1',executable=binary.relative_to(ROOT).as_posix(),bytes=binary.stat().st_size,sha256=sha(binary),
        source_revision=lock['revision'],llama_revision=lock['llama_revision'],compiled_library_sources=10,compile_cache=cache.relative_to(ROOT).as_posix(),
        backend='cpu',private_weight_mapping=True,production_worker_source_unmodified=True,upstream_sources_unmodified=True,windows_crt_parent_environment_compatibility=True,
        bundled_model_data=False,physical_android=False,android_compiled=False,packaged_in_apk=False,model_executed=False,input_fingerprint=before)
    receipt.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');return binary,value


if __name__=='__main__':
    binary,value=build();print(json.dumps({key:value[key] for key in ['executable','bytes','sha256']}),flush=True)
