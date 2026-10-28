"""Compile the real Sana MNN CPU worker using native Windows NDK/CMake tools."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from evidence import fingerprint
from fetch_mnn import validate_sources
from verify_package import elf_info

ROOT = Path(__file__).resolve().parents[1]

def once(text, old, new):
    if text.count(old) != 1: raise RuntimeError('Reviewed upstream patch no longer matches')
    return text.replace(old, new)

def main():
    if os.name != 'nt': raise RuntimeError('Use native Windows NDK tools')
    lock = json.loads((ROOT / 'third_party/mnn-source-lock.json').read_text(encoding='utf-8'))
    source = validate_sources(lock)
    if hashlib.sha256((ROOT / 'build/native-src/sd-cpp/thirdparty/json.hpp').read_bytes()).hexdigest() != lock['json_header_sha256']: raise RuntimeError('Pinned JSON header changed')
    generated = ROOT / 'build/mnn-generated'; generated.mkdir(parents=True, exist_ok=True)
    host = (source / 'transformers/diffusion/engine/include/diffusion/sana_llm.hpp').read_text(encoding='utf-8')
    host = once(host, '#include <vector>', '#include <stdexcept>\n#include <vector>')
    host = once(host, 'SanaLlm(const std::string& config_path) {', 'SanaLlm(const std::string& config_path, int maximum_tokens) : mMaximumTokens(maximum_tokens) {')
    host = once(host, 'mLlm->set_config(', 'if (!mLlm) throw std::runtime_error("Cannot create the matched Qwen3 encoder");\n        mLlm->set_config(')
    host = once(host, 'mLlm->load();', 'if (!mLlm->load()) throw std::runtime_error("Cannot load the complete Qwen3 encoder");')
    host = once(host, 'auto ids = mLlm->tokenizer_encode(p);', 'auto ids = mLlm->tokenizer_encode(p);\n            if (ids.empty() || ids.size() > static_cast<size_t>(mMaximumTokens)) throw std::runtime_error("Sana formatted input exceeds its selected token budget");')
    host = once(host, 'std::unique_ptr<Llm> mLlm;', 'int mMaximumTokens;\n    std::unique_ptr<Llm> mLlm;')
    (generated / 'lma_sana_llm.hpp').write_text(host, encoding='utf-8')
    diffusion = (source / 'transformers/diffusion/engine/src/sana_diffusion.cpp').read_text(encoding='utf-8')
    diffusion = once(diffusion, '#include "tokenizer.hpp"', '#include "tokenizer.hpp"\n#include <cstdlib>')
    diffusion = once(diffusion, 'config.numThread = 4;', 'const char* bounded_threads = std::getenv("LMA_MNN_THREADS");\n                config.numThread = bounded_threads ? std::atoi(bounded_threads) : 4;\n                if (config.numThread < 1 || config.numThread > 32) return false;')
    diffusion = once(diffusion, 'mModules[4] = nullptr;\n\n            return true;', 'mModules[4] = nullptr;\n            for (int i = 0; i < 4; ++i) if (!mModules[i]) return false;\n            return true;')
    (generated / 'sana_diffusion.cpp').write_text(diffusion, encoding='utf-8')
    inputs = fingerprint('native/mnn', 'tools/build_mnn.py', 'tools/fetch_mnn.py', 'third_party/mnn-source-lock.json')
    drive = next((c+':' for c in 'RSTUVWXYZ' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No unused build path alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    log = ROOT / 'build/mnn-build.log'; log.write_bytes(b'')
    try:
        alias = drive+'/'; ndk=alias+'build/toolchain/android-ndk-r30'; cmake=alias+'build/toolchain/cmake-3.31.6/bin/cmake.exe'; output=alias+'build/mnn-arm64-cpu-r30'
        options = {'ANDROID_ABI':'arm64-v8a','ANDROID_PLATFORM':'android-28','ANDROID_STL':'c++_static','CMAKE_BUILD_TYPE':'Release','MNN_BUILD_SHARED_LIBS':'OFF','MNN_SEP_BUILD':'OFF','MNN_BUILD_LLM':'ON','MNN_BUILD_LLM_OMNI':'OFF','MNN_BUILD_DIFFUSION':'ON','MNN_IMGCODECS':'ON','MNN_ARM82':'OFF','MNN_OPENMP':'OFF','MNN_OPENCL':'OFF','MNN_VULKAN':'OFF','MNN_BUILD_AUDIO':'OFF','MNN_BUILD_TRAIN':'OFF','MNN_BUILD_TEST':'OFF','MNN_BUILD_CONVERTER':'OFF','MNN_BUILD_BENCHMARK':'OFF','MNN_LLM_BUILD_DEMO':'OFF','LLM_SUPPORT_HTTP_RESOURCE':'OFF','MNN_USE_LOGCAT':'OFF','MNN_BUILD_FOR_ANDROID_COMMAND':'ON'}
        commands = [[cmake,'-S',alias+'build/native-src/mnn','-B',output,'-G','Ninja','-DCMAKE_MAKE_PROGRAM='+alias+'build/toolchain/cmake-3.31.6/bin/ninja.exe','-DCMAKE_TOOLCHAIN_FILE='+ndk+'/build/cmake/android.toolchain.cmake',
            '-DCMAKE_PROJECT_INCLUDE='+alias+'native/mnn/bootstrap.cmake','-DLMA_MNN_SOURCE='+alias+'build/native-src/mnn','-DLMA_MNN_INTEGRATION='+alias+'native/mnn','-DLMA_MNN_GENERATED='+alias+'build/mnn-generated','-DLMA_JSON_SOURCE='+alias+'build/native-src/sd-cpp/thirdparty','-DLMA_MNN_REVISION='+lock['revision']] + ['-D'+k+'='+v for k,v in options.items()],
            [cmake,'--build',output,'--target','lma_mnn_worker','-j','4'],[ndk+'/toolchains/llvm/prebuilt/windows-x86_64/bin/llvm-strip.exe','--strip-unneeded',output+'/liblma-mnn.so']]
        for command in commands:
            result = subprocess.run(command, cwd=alias, capture_output=True)
            with log.open('ab') as stream: stream.write(result.stdout+result.stderr)
            print('\n'.join((result.stdout+result.stderr).decode('utf-8',errors='replace').splitlines()[-5:]),flush=True)
            if result.returncode: raise RuntimeError('MNN compilation failed; inspect build/mnn-build.log')
    finally: subprocess.run(['subst',drive,'/D'],check=True,capture_output=True)
    binary=ROOT/'build/mnn-arm64-cpu-r30/liblma-mnn.so';data=binary.read_bytes();info=elf_info(data)
    if not info['16k_elf_aligned'] or info['android_api_notes'] != [28] or info['interpreter'] != '/system/bin/linker64': raise RuntimeError('MNN ELF contract failed')
    ndk_bin=ROOT/'build/toolchain/android-ndk-r30/toolchains/llvm/prebuilt/windows-x86_64/bin'
    imports=subprocess.check_output([str(ndk_bin/'llvm-nm.exe'),'-D','--undefined-only',str(binary)],text=True)
    forbidden={'connect','socket','getaddrinfo','__android_log_print','__android_log_vprint','__android_log_write'}
    if {line.split()[-1].split('@')[0] for line in imports.splitlines()} & forbidden: raise RuntimeError('Review unexpected network/logcat imports')
    validate_sources(lock)
    shutil.copy2(binary,ROOT/'app/src/main/jniLibs/arm64-v8a/liblma-mnn.so')
    receipt=dict(schema='lma.native-build/1',engine='mnn_diffusion',file=binary.name,source_revision=lock['revision'],abi='arm64-v8a',backend='cpu',ndk='30.0.16248370',min_sdk=28,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),elf_load_alignment=info['load_segment_alignment'],android_api_notes=[28],source_inputs=inputs,
        generated_sources=fingerprint('build/mnn-generated'),vocabularies='external_user_selected_components',model_inference_tested=False,physical_device_tests=0,virtualization_used=False,http_resources_compiled=False,logcat_compiled=False)
    (ROOT/'build/mnn-build-info.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('engine','bytes','sha256','source_revision')}))

if __name__ == '__main__': main()
