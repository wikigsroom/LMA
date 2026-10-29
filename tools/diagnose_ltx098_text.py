"""Capture trained T5 intermediate values in an isolated, offline host build.

This never changes the accepted encoder, reference equations, APK or numerical
gates. Native diagnostic outputs keep graph tensors alive until computation
finishes, so their timing/memory are not production measurements.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from evidence import current, fingerprint
from fetch_ltx098_text import DIRECTORY, assets, sha, sources
from ltx098_text_oracle import dependencies, paged_reference
from test_ltx098_text import execute

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return fingerprint('tools/diagnose_ltx098_text.py', 'research/ltx098_text',
                       'tools/ltx098_text_oracle.py', 'tools/test_ltx098_text.py',
                       'tools/build_ltx098_text.py', 'tools/fetch_ltx098_text.py',
                       'third_party/ltx098-text-source-lock.json')


def instrument(source):
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Pinned diagnostic anchor changed: ' + old[:80])
        source = source.replace(old, new)
    replace('#include <cstring>', '#include <cstring>\n#include <fstream>\n#include <cstdlib>')
    replace('auto* x=ggml_get_rows(c,s.tensor("token_embd.weight",l.width,l.vocabulary),tokens);', '''
    const char* folder=std::getenv("LMA_T5_DIAGNOSTIC_DIR");
    require(folder && *folder,"Missing isolated diagnostic directory");
    std::vector<std::pair<std::string,ggml_tensor*>> traces;
    auto trace=[&](const std::string& name,ggml_tensor* value){ggml_set_output(value);traces.emplace_back(name,value);};
    auto* x=ggml_get_rows(c,s.tensor("token_embd.weight",l.width,l.vocabulary),tokens);trace("embedding",x);''')
    replace('auto prefix="enc.blk."+std::to_string(i)+".";auto* normalized=normalize(x,prefix+"attn_norm.weight");',
            'auto prefix="enc.blk."+std::to_string(i)+".";auto label="block-"+std::to_string(i)+"-";auto* normalized=normalize(x,prefix+"attn_norm.weight");trace(label+"attn-norm",normalized);')
    replace('normalized);return ggml_cont(c,ggml_permute', 'normalized);trace(label+name,p);return ggml_cont(c,ggml_permute')
    replace('mixed=ggml_reshape_2d(c,mixed,l.width,n);', 'mixed=ggml_reshape_2d(c,mixed,l.width,n);trace(label+"mixed",mixed);')
    replace('x=ggml_add(c,x,ggml_mul_mat(c,matrix(prefix+"attn_o.weight",l.width,l.width),mixed));',
            'auto* projected=ggml_mul_mat(c,matrix(prefix+"attn_o.weight",l.width,l.width),mixed);trace(label+"attn-o",projected);x=ggml_add(c,x,projected);trace(label+"attn-residual",x);')
    replace('normalized=normalize(x,prefix+"ffn_norm.weight");', 'normalized=normalize(x,prefix+"ffn_norm.weight");trace(label+"ffn-norm",normalized);')
    replace('auto* activated=ggml_map_custom2(c,gate,up,f32_geglu,GGML_N_TASKS_MAX,nullptr);',
            'trace(label+"gate",gate);trace(label+"up",up);auto* activated=ggml_map_custom2(c,gate,up,f32_geglu,GGML_N_TASKS_MAX,nullptr);trace(label+"geglu",activated);')
    replace('x=ggml_add(c,x,ggml_mul_mat(c,matrix(prefix+"ffn_down.weight",l.feed_forward,l.width),activated));',
            'auto* down=ggml_mul_mat(c,matrix(prefix+"ffn_down.weight",l.feed_forward,l.width),activated);trace(label+"down",down);x=ggml_add(c,x,down);trace(label+"residual",x);')
    replace('auto* output=normalize(x,"enc.output_norm.weight");ggml_set_output(output);',
            'auto* output=normalize(x,"enc.output_norm.weight");ggml_set_output(output);trace("final",output);')
    replace('std::vector<float> data(static_cast<size_t>(n)*l.width);ggml_backend_tensor_get', '''
    for(const auto& item:traces) {
        require(item.second->type==GGML_TYPE_F32,"Diagnostic tensor is not F32");
        std::vector<float> values(static_cast<size_t>(ggml_nelements(item.second)));
        ggml_backend_tensor_get(item.second,values.data(),0,values.size()*sizeof(float));
        auto path=std::filesystem::path(folder)/(item.first+".f32");
        require(!std::filesystem::exists(path),"Existing diagnostic output");
        std::ofstream stream(path,std::ios::binary);stream.write(reinterpret_cast<const char*>(values.data()),static_cast<std::streamsize>(values.size()*sizeof(float)));
        require(stream.good(),"Cannot save diagnostic tensor");
    }
    std::vector<float> data(static_cast<size_t>(n)*l.width);ggml_backend_tensor_get''')
    return source


def build(output):
    if os.name != 'nt':
        raise RuntimeError('Use native Windows MSVC; no virtualized build')
    base = json.loads((ROOT / 'build/ltx098-text-host/receipt.json').read_text(encoding='utf-8'))
    current(base['input_fingerprint'])
    original = ROOT / 'build/ltx098-text-host/bin/lma_ltx098_text_cli.exe'
    if sha(original) != base['executable_sha256']:
        raise ValueError('Changed baseline executable')
    source = output / 'src'; source.mkdir()
    for item in (ROOT / 'research/ltx098_text').iterdir():
        if item.is_file() and item.name != 'CMakeLists.txt':
            shutil.copyfile(item, source / item.name)
    graph = source / 'graph.cpp'
    graph.write_text(instrument(graph.read_text(encoding='utf-8')), encoding='utf-8')
    archives = ['src/llama.lib', 'ggml/src/ggml.lib', 'ggml/src/ggml-cpu.lib', 'ggml/src/ggml-base.lib']
    linked = {name: sha(ROOT / 'build/ltx098-text-host/llama-source' / name) for name in archives}
    cmake_source = '''cmake_minimum_required(VERSION 3.22)
project(lma_t5_diagnosis LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
add_executable(lma_t5_diagnosis driver.cpp encoder.cpp graph.cpp)
target_include_directories(lma_t5_diagnosis PRIVATE "${ROOT}/build/native-src/llama-soulx/include" "${ROOT}/build/native-src/llama-soulx/ggml/include" "${ROOT}/build/native-src/sd-cpp/thirdparty")
target_link_libraries(lma_t5_diagnosis PRIVATE ARCHIVES)
'''.replace('ARCHIVES', ' '.join('"${ROOT}/build/ltx098-text-host/llama-source/' + p + '"' for p in archives))
    (source / 'CMakeLists.txt').write_text(cmake_source, encoding='utf-8')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free ASCII build alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        alias = drive + '/'; relative = output.relative_to(ROOT).as_posix()
        cmake = alias + 'build/toolchain/cmake-3.31.6/bin/cmake.exe'
        directory = alias + relative + '/bin'
        commands = [[cmake, '-S', alias + relative + '/src', '-B', directory, '-G', 'Ninja',
                     '-DCMAKE_BUILD_TYPE=Release', '-DROOT=' + alias,
                     '-DCMAKE_MAKE_PROGRAM=' + alias + 'build/toolchain/cmake-3.31.6/bin/ninja.exe'],
                    [cmake, '--build', directory, '-j', '4']]
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        for i, command in enumerate(commands):
            script = output / ('build-' + str(i) + '.cmd')
            script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
            result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=300)
            (output / ('build-' + str(i) + '.log')).write_bytes(result.stdout + result.stderr)
            if result.returncode: raise RuntimeError('Inspect isolated diagnostic build log')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    return output / 'bin/lma_t5_diagnosis.exe', dict(baseline=base['executable_sha256'], linked_archives=linked)


def run(pipeline):
    before = inputs(); pipeline = pipeline.resolve()
    if not pipeline.is_relative_to(ROOT / 'build'):
        raise ValueError('Use an existing developer pipeline below build/')
    record = json.loads((pipeline / 'pipeline.json').read_text(encoding='utf-8'))
    current(record['input_fingerprint'])
    if not record['actual_prompt_conditioning'] or record['physical_android']:
        raise ValueError('Require a real trained host prompt')
    lock = sources(); assets(oracle=True)
    output = ROOT / 'build/ltx098-text-diagnosis' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
    output.mkdir(parents=True, exist_ok=False)
    native = output / 'native'; reference = output / 'reference'; native.mkdir(); reference.mkdir()
    print('Build isolated traced encoder:', output.relative_to(ROOT), flush=True)
    executable, compilation = build(output)
    request = output / 'request.json'
    request.write_text(json.dumps(dict(operation='encode', inputs=[dict(prompt=record['request']['prompt'])], max_tokens=256)), encoding='utf-8')
    previous = os.environ.get('LMA_T5_DIAGNOSTIC_DIR')
    # The native child uses the project root cwd; an ASCII relative path avoids
    # Windows narrow-environment path conversion without leaving the workspace.
    os.environ['LMA_T5_DIAGNOSTIC_DIR'] = native.relative_to(ROOT).as_posix()
    try:
        print('Execute complete trained traced encoder', flush=True)
        result, seconds, resources = execute([str(executable), str(DIRECTORY / 'originals' / lock['model']['file']),
                                             str(DIRECTORY / 'oracle/tokenizer_config.json'), str(request),
                                             str(output / 'caption.f32'), '4'], timeout=1800, observe=True)
        (output / 'native.log').write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError('Inspect traced encoder native.log')
        native_record = json.loads(result.stdout.decode('utf-8'))
        if sha(native / 'final.f32') != sha(pipeline / 'caption.f32'):
            raise ValueError('Instrumentation changed baseline native caption')
    finally:
        if previous is None: os.environ.pop('LMA_T5_DIAGNOSTIC_DIR', None)
        else: os.environ['LMA_T5_DIAGNOSTIC_DIR'] = previous
    print('Execute original Transformers encoder with non-mutating forward hooks', flush=True)
    np, torch, gguf, transformers, versions = dependencies(lock)
    tokenizer = transformers.T5Tokenizer.from_pretrained(str(DIRECTORY / 'oracle'), local_files_only=True, legacy=True)
    encoded = tokenizer(record['request']['prompt'].strip(), return_tensors='pt', truncation=True, max_length=256)
    config = transformers.T5Config.from_pretrained(str(DIRECTORY / 'oracle'), local_files_only=True)
    reader = gguf.GGUFReader(DIRECTORY / 'originals' / lock['model']['file'])
    model, used, tensors, hooks = paged_reference(np, torch, gguf, transformers, reader, config)
    shapes = {}
    def save(name, value):
        value = value.detach().cpu().numpy().astype('<f4')
        shapes[name] = list(value.shape); value.tofile(reference / (name + '.f32'))
    def after(module, name):
        hooks.append(module.register_forward_hook(lambda target, args, value: save(name, value[0] if isinstance(value, tuple) else value)))
    def prior(module, name):
        hooks.append(module.register_forward_pre_hook(lambda target, args: save(name, args[0])))
    after(model.encoder.embed_tokens, 'embedding')
    for i, block in enumerate(model.encoder.block):
        prefix = 'block-' + str(i) + '-'; attention = block.layer[0]; ffn = block.layer[1]
        after(attention.layer_norm, prefix + 'attn-norm')
        for key in ('q', 'k', 'v', 'o'): after(getattr(attention.SelfAttention, key), prefix + ('attn-o' if key == 'o' else key))
        prior(attention.SelfAttention.o, prefix + 'mixed'); after(attention, prefix + 'attn-residual')
        after(ffn.layer_norm, prefix + 'ffn-norm')
        after(ffn.DenseReluDense.wi_0, prefix + 'gate'); after(ffn.DenseReluDense.wi_1, prefix + 'up')
        prior(ffn.DenseReluDense.wo, prefix + 'geglu'); after(ffn.DenseReluDense.wo, prefix + 'down')
        after(ffn, prefix + 'residual')
    after(model.encoder.final_layer_norm, 'final')
    start = time.perf_counter()
    with torch.inference_mode(): original = model(**encoded).last_hidden_state
    original_seconds = time.perf_counter() - start
    if used != set(tensors): raise ValueError('Incomplete trained T5 original parameter coverage')
    for hook in hooks: hook.remove()
    metrics = []
    for name, shape in shapes.items():
        left = np.fromfile(native / (name + '.f32'), dtype='<f4').astype(np.float64)
        right = np.fromfile(reference / (name + '.f32'), dtype='<f4').astype(np.float64)
        if left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError('Invalid intermediate: ' + name)
        delta = left - right
        metrics.append(dict(name=name, shape=shape, max_abs=float(abs(delta).max()),
                            relative_rmse=float(np.linalg.norm(delta) / max(np.linalg.norm(right), 1e-12)),
                            native_sha256=sha(native / (name + '.f32')), reference_sha256=sha(reference / (name + '.f32'))))
    current(before)
    report = dict(schema='lma.ltx098-text-diagnosis/1', metrics=metrics, tensors=len(tensors),
                  tokens=encoded['input_ids'].flatten().tolist(), native=native_record,
                  original_attention_implementation=config._attn_implementation,
                  versions=versions, native_seconds=seconds, original_seconds=original_seconds,
                  diagnostic_resources=resources, compilation=compilation, diagnostic_binary_sha256=sha(executable),
                  baseline_pipeline=pipeline.relative_to(ROOT).as_posix(), baseline_record_sha256=sha(pipeline / 'pipeline.json'),
                  retained_intermediates_change_memory=True, production_performance_measured=False,
                  baseline_native_caption_bitwise_identical=True,
                  original_forward_modified=False, acceptance_gates_changed=False,
                  physical_android=False, apk_changed=False, input_fingerprint=before)
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=output.relative_to(ROOT).as_posix(), metrics=len(metrics),
                          final=metrics[-1], original_attention_implementation=config._attn_implementation)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline', type=Path, help='Existing real trained pipeline output directory')
    run(parser.parse_args().pipeline)
