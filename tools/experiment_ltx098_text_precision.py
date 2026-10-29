"""Test an isolated T5 precision candidate against the frozen real-prompt oracle.

The accepted encoder and all full-chain gates stay unchanged. Model acquisition
is never implicit. This developer experiment does not register an App engine.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from diagnose_ltx098_text import inputs as diagnosis_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import DIRECTORY, assets, sha, sources
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**diagnosis_inputs(), **fingerprint('research/ltx098_text_precision',
                                              'tools/experiment_ltx098_text_precision.py')}


def build(output, linear):
    baseline = json.loads((ROOT / 'build/ltx098-text-host/receipt.json').read_text(encoding='utf-8'))
    current(baseline['input_fingerprint'])
    if sha(ROOT / 'build/ltx098-text-host/bin/lma_ltx098_text_cli.exe') != baseline['executable_sha256']:
        raise ValueError('Changed baseline T5 executable')
    source = output / 'src'; source.mkdir()
    for item in (ROOT / 'research/ltx098_text').iterdir():
        if item.is_file() and item.name != 'CMakeLists.txt': shutil.copyfile(item, source / item.name)
    graph = source / 'graph.cpp'; text = graph.read_text(encoding='utf-8')
    def replace(old, new):
        nonlocal text
        if text.count(old) != 1: raise ValueError('Changed precision anchor: ' + old[:70])
        text = text.replace(old, new)
    extra = (ROOT / 'research/ltx098_text_precision/attention.hpp').read_text(encoding='utf-8')
    if linear: extra += '\n' + (ROOT / 'research/ltx098_text_precision/linear.hpp').read_text(encoding='utf-8')
    replace('int bucket(int key,int query) {', extra + '\nint bucket(int key,int query) {')
    start = text.index('auto* scores=ggml_mul_mat(c,k,q);')
    end = text.index('mixed=ggml_cont(c,ggml_permute', start)
    text = text[:start] + 'auto* mixed=ggml_map_custom3(c,q,k,v,precise_attention,GGML_N_TASKS_MAX,s.tensor("enc.blk.0.attn_rel_b.weight",l.heads,32)->data);\n        ' + text[end:]
    replace('ggml_backend_tensor_set(bias,relative.data(),0,relative.size()*sizeof(float));s.stop();', 's.stop();')
    if linear:
        anchor = 'auto* x=ggml_get_rows(c,s.tensor("token_embd.weight",l.width,l.vocabulary),tokens);'
        replace(anchor, 'auto precise=[&](ggml_tensor* w,ggml_tensor* in){auto* shape=ggml_new_tensor_2d(c,GGML_TYPE_F32,w->ne[1],in->ne[1]);return ggml_map_custom3(c,shape,w,in,precise_linear,GGML_N_TASKS_MAX,nullptr);};\n' + anchor)
        if text.count('ggml_mul_mat(c,matrix(') != 5: raise ValueError('Unexpected linear projection coverage')
        text = text.replace('ggml_mul_mat(c,matrix(', 'precise(matrix(')
    graph.write_text(text, encoding='utf-8')
    implementation = 'independent_ggml_f32_with_f64_attention' + ('_and_linear' if linear else '')
    driver = source / 'driver.cpp'; text = driver.read_text(encoding='utf-8')
    if text.count('independent_ggml_f32_compute') != 1: raise ValueError('Changed implementation identity')
    driver.write_text(text.replace('independent_ggml_f32_compute', implementation), encoding='utf-8')
    archives = ['src/llama.lib', 'ggml/src/ggml.lib', 'ggml/src/ggml-cpu.lib', 'ggml/src/ggml-base.lib']
    linked = {name: sha(ROOT / 'build/ltx098-text-host/llama-source' / name) for name in archives}
    cmake_text = '''cmake_minimum_required(VERSION 3.22)
project(lma_t5_precision LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
add_executable(lma_t5_precision driver.cpp encoder.cpp graph.cpp)
target_include_directories(lma_t5_precision PRIVATE "${ROOT}/build/native-src/llama-soulx/include" "${ROOT}/build/native-src/llama-soulx/ggml/include" "${ROOT}/build/native-src/sd-cpp/thirdparty")
target_link_libraries(lma_t5_precision PRIVATE ARCHIVES)
'''.replace('ARCHIVES', ' '.join('"${ROOT}/build/ltx098-text-host/llama-source/' + name + '"' for name in archives))
    (source / 'CMakeLists.txt').write_text(cmake_text, encoding='utf-8')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        alias = drive + '/'; relative = output.relative_to(ROOT).as_posix()
        cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'; directory = alias + relative + '/bin'
        commands = [[cmake, '-S', alias + relative + '/src', '-B', directory, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
                     '-DROOT=' + alias, '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe'],
                    [cmake, '--build', directory, '-j', '4']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for index, command in enumerate(commands):
            script = output / ('build-' + str(index) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (output / ('build-' + str(index) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Inspect isolated precision build log')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    return output / 'bin/lma_t5_precision.exe', implementation, linked


def run(reference, linear):
    if os.name != 'nt': raise RuntimeError('Use native Windows tools; no virtualization')
    before = inputs(); reference = reference.resolve()
    if not reference.is_relative_to(ROOT / 'build'): raise ValueError('Reference must stay below build/')
    baseline = json.loads((ROOT / 'verification/development/ltx098-pipeline.json').read_text(encoding='utf-8'))
    current(baseline['input_fingerprint'])
    oracle = json.loads((reference / 'references.json').read_text(encoding='utf-8')); current(oracle['input_fingerprint'])
    if oracle != baseline['original_oracle']: raise ValueError('Different independent original pipeline oracle')
    for case in oracle['cases']:
        directory = reference / case['name']
        for name, expected in case['files'].items():
            path = directory / name
            if path.parent != directory or path.stat().st_size != expected['bytes'] or sha(path) != expected['sha256']:
                raise ValueError('Changed original reference: ' + name)
    lock = sources(); assets(oracle=True)
    output = ROOT / 'build/ltx098-text-precision-experiments' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    executable, implementation, linked = build(output, linear)
    print('Execute trained T5 A/B/A:', implementation, output.relative_to(ROOT), flush=True)
    import numpy as np
    jobs = []; identities = []
    for index, case_index in enumerate([0, 1, 0]):
        directory = output / ('case-' + str(index)); directory.mkdir()
        source = ROOT / baseline['captured_native_pipelines'][case_index]
        if sha(source / 'pipeline.json') != baseline['captured_native_record_sha256'][case_index]:
            raise ValueError('Changed captured baseline pipeline')
        job = baseline['jobs'][case_index]; original = oracle['cases'][case_index]
        if original['native_record_sha256'] != sha(source / 'pipeline.json'): raise ValueError('Wrong oracle case')
        request = directory / 'request.json'
        request.write_text(json.dumps(dict(operation='encode', inputs=[dict(prompt=job['request']['prompt'])], max_tokens=256)), encoding='utf-8')
        target = directory / 'caption.f32'
        result, seconds, resources = execute([str(executable), str(DIRECTORY / 'originals' / lock['model']['file']),
                                             str(DIRECTORY / 'oracle/tokenizer_config.json'), str(request), str(target), '4'],
                                            timeout=7200, observe=True)
        (directory / 'native.log').write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError('Inspect candidate native.log')
        native = json.loads(result.stdout.decode('utf-8'))
        if native['encoder_implementation'] != implementation or native['layers'] != 24 or native['width'] != 4096 or not native['model_inference']:
            raise ValueError('Incomplete or misidentified trained candidate')
        if native['model_loads'] != 1 or native['model_unloads'] != 1 or native['encode_calls'] != 1 or native['fixture']:
            raise ValueError('Incorrect trained candidate lifecycle')
        left = np.fromfile(target, dtype='<f4').astype(np.float64)
        right = np.fromfile(reference / original['name'] / 'caption.f32', dtype='<f4').astype(np.float64)
        if left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError('Invalid candidate caption')
        delta = left - right; identity = sha(target); identities.append(identity)
        metric = dict(max_abs=float(abs(delta).max()), relative_rmse=float(np.linalg.norm(delta) / np.linalg.norm(right)))
        jobs.append(dict(case=case_index, prompt=job['request']['prompt'], tokens=original['tokens'], native=native,
                         metric=metric, seconds=seconds, resources=resources, caption_bytes=target.stat().st_size,
                         caption_sha256=identity, reference_sha256=original['files']['caption.f32']['sha256']))
        print(json.dumps(dict(case=case_index, metric=metric, seconds=seconds)), flush=True)
    if identities[0] != identities[2]: raise ValueError('Candidate A/B/A differs bitwise')
    current(before)
    report = dict(schema='lma.ltx098-text-precision/1', implementation=implementation, linear_f64=linear,
                  jobs=jobs, actual_trained_jobs=3, native_children=3, distinct_prompts=2, aba_bitwise_identical=True,
                  binary_sha256=sha(executable), linked_archives=linked,
                  original_oracle_sha256=sha(reference / 'references.json'),
                  output_directory=output.relative_to(ROOT).as_posix(),
                  trained_t5_tensors=219, trained_t5_parameters=4762310656,
                  production_source_changed=False, acceptance_gates_changed=False,
                  complete_pipeline_numeric_accepted=False, physical_android=False,
                  packaged_in_apk=False, engine_registered=False, input_fingerprint=before)
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (output.parent / ('linear-results.json' if linear else 'attention-results.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=output.relative_to(ROOT).as_posix(), aba_bitwise_identical=True)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--linear-f64', action='store_true', help='Also accumulate dense projections in F64')
    args = parser.parse_args(); run(args.reference, args.linear_f64)
