"""Build immutable offline sampler candidates with explicit F32 matmul inputs."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from build_ltx098 import validate_sources
from evidence import current, fingerprint
from fetch_ltx098_text import sha
from ltx098_pipeline import SAMPLER, inputs as pipeline_inputs

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**pipeline_inputs(), **fingerprint('research/ltx098_compute_precision', 'tools/build_ltx098_compute_precision.py')}


def build(staged_rms=False):
    if os.name != 'nt': raise RuntimeError('Use native Windows MSVC; no virtualization')
    before = inputs(); validate_sources()
    base = ROOT / 'build/ltx098-host-vulkan'
    original = json.loads((base / 'receipt.json').read_text(encoding='utf-8')); current(original['input_fingerprint'])
    if sha(SAMPLER) != original['sampler_binary_sha256']: raise ValueError('Changed baseline executable')
    mode = 'f32-rms' if staged_rms else 'f32'
    key = hashlib.sha256(json.dumps(before, sort_keys=True).encode('utf-8')).hexdigest()[:16]
    output = ROOT / 'build/ltx098-compute-precision' / (mode + '-' + key)
    receipt = output / 'receipt.json'; executable = output / 'bin/lma_ltx098_sample.exe'
    libraries = ['ggml/src/ggml.lib', 'ggml/src/ggml-cpu.lib', 'ggml/src/ggml-vulkan/ggml-vulkan.lib', 'ggml/src/ggml-base.lib', 'vulkan-1.lib']
    linked = {name: sha(base / name) for name in libraries}
    if receipt.exists():
        record = json.loads(receipt.read_text(encoding='utf-8')); current(record['input_fingerprint'])
        if (record['input_fingerprint'] != before or record['linked_archives'] != linked or
            record['executable_sha256'] != sha(executable)): raise ValueError('Changed immutable candidate build')
        for name, identity in record['generated_sources'].items():
            if sha(output / 'src' / name) != identity: raise ValueError('Changed generated candidate source')
        return executable, record
    source = output / 'src'; source.mkdir(parents=True, exist_ok=False)
    for item in (ROOT / 'research/ltx098').iterdir():
        if item.is_file() and item.suffix in ['.cpp', '.hpp']: shutil.copyfile(item, source / item.name)
    path = source / 'transformer.cpp'; text = path.read_text(encoding='utf-8')
    anchor = 'auto result=ggml_mul_mat(ctx,a,b);'
    if text.count(anchor) != 1: raise ValueError('Changed matrix precision anchor')
    text = text.replace(anchor, 'if(a->type!=GGML_TYPE_F32)a=ggml_cast(ctx,a,GGML_TYPE_F32);\n        if(b->type!=GGML_TYPE_F32)b=ggml_cast(ctx,b,GGML_TYPE_F32);\n        ' + anchor)
    if staged_rms:
        anchor = 'namespace lma::ltx098 {'
        text = text.replace(anchor, (ROOT / 'research/ltx098_compute_precision/rms.hpp').read_text(encoding='utf-8') + '\n' + anchor, 1)
        if text.count('ggml_rms_norm(ctx,x,1e-5f)') != 1 or text.count('ggml_rms_norm(c,x,m.epsilon)') != 2:
            raise ValueError('Changed RMS coverage')
        text = text.replace('ggml_rms_norm(ctx,x,1e-5f)', 'ggml_map_custom1(ctx,x,diagnostic_f32_rms,GGML_N_TASKS_MAX,&diagnostic_qk_epsilon)')
        text = text.replace('ggml_rms_norm(c,x,m.epsilon)', 'ggml_map_custom1(c,x,diagnostic_f32_rms,GGML_N_TASKS_MAX,&m.epsilon)')
    path.write_text(text, encoding='utf-8')
    path = source / 'sampling_driver.cpp'; text = path.read_text(encoding='utf-8')
    anchor = 'record["precision_policy"]=backend=="vulkan"?"baseline_f32_compute_optional_f16_weight_storage":"native_cpu";'
    if text.count(anchor) != 1: raise ValueError('Changed precision identity anchor')
    text = text.replace(anchor, 'record["precision_policy"]="explicit_f32_matmul_' + mode + '";record["explicit_f32_matmul_operands"]=true;')
    path.write_text(text, encoding='utf-8')
    cmake_text = '''cmake_minimum_required(VERSION 3.22)
project(lma_ltx098_compute_precision LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
add_executable(lma_ltx098_sample transformer.cpp sampling.cpp sampling_driver.cpp)
target_compile_definitions(lma_ltx098_sample PRIVATE GGML_USE_CPU GGML_USE_VULKAN LMA_LTX_VULKAN=1)
target_include_directories(lma_ltx098_sample PRIVATE "${ROOT}/build/native-src/sd-cpp/ggml/include" "${ROOT}/build/native-src/sd-cpp/thirdparty")
target_link_libraries(lma_ltx098_sample PRIVATE ARCHIVES)
'''.replace('ARCHIVES', ' '.join('"${ROOT}/build/ltx098-host-vulkan/' + name + '"' for name in libraries))
    (source / 'CMakeLists.txt').write_text(cmake_text, encoding='utf-8')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    try:
        alias = drive + '/'; relative = output.relative_to(ROOT).as_posix()
        cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        commands = [[cmake, '-S', alias + relative + '/src', '-B', alias + relative + '/bin', '-G', 'Ninja',
                     '-DCMAKE_BUILD_TYPE=Release', '-DROOT=' + alias, '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe'],
                    [cmake, '--build', alias + relative + '/bin', '-j', '4']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = output / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            process = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (output / ('build-' + str(index) + '.log')).write_bytes(process.stdout + process.stderr)
            if process.returncode: raise RuntimeError('Inspect isolated compute precision build log')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    record = dict(schema='lma.ltx098-compute-precision-build/1', mode=mode,
                  executable=executable.relative_to(ROOT).as_posix(), executable_sha256=sha(executable), linked_archives=linked,
                  generated_sources={path.name: sha(path) for path in source.iterdir() if path.is_file()},
                  android_compiled=False, packaged_in_apk=False, engine_registered=False, input_fingerprint=before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return executable, record
