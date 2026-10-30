"""Compare the real native prompt grid with pinned official processor methods.

Uses only an existing GGUF vocabulary, pinned local tokenizer metadata and
synthetic integer code matrices. No model download, codec or model inference.
"""
import ast
import __future__
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Union

from build_openmoss_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_openmoss import validate_sources
from fetch_openmoss_trained import asset_path, assets
from fetch_openmoss_reference import CACHE as OFFICIAL, verify as verify_official
from fetch_sd15_trained import sha
from openmoss_pipeline import guarded_pipeline

ROOT = Path(__file__).resolve().parents[1]


def official_methods():
    import torch
    from transformers import Qwen2TokenizerFast

    verify_official()
    source = OFFICIAL / 'processing_moss_tts.py'
    assert sha(source) == 'e591ff156e8fadcae34db5613a2221fab7ec5d814bfc0ec001e8ec4ef2782425'
    tokenizer_config = json.loads((OFFICIAL / 'tokenizer_config.json').read_text(encoding='utf-8'))
    assert tokenizer_config['tokenizer_class'] in {'Qwen2Tokenizer', 'Qwen2TokenizerFast'}
    tokenizer = Qwen2TokenizerFast.from_pretrained(str(OFFICIAL), local_files_only=True)
    tokenizer.chat_template = (OFFICIAL / 'chat_template.jinja').read_text(encoding='utf-8')
    config = json.loads((OFFICIAL / 'config.json').read_text(encoding='utf-8'))
    config.update(im_start_token_id=151644, im_end_token_id=151645, pad_token_id=151643)
    tree = ast.parse(source.read_text(encoding='utf-8'))
    names = {'Message', 'UserMessage', 'MossTTSDelayProcessor'}
    nodes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name in names]
    processor = next(n for n in nodes if n.name == 'MossTTSDelayProcessor')
    # Only formatting methods are executed; their official bodies are unchanged.
    methods = {'_replace_audio_placeholders', '_merge_consecutive_audio_placeholders',
               'apply_delay_pattern', '_get_unified_codes'}
    processor.bases = []
    processor.body = [n for n in processor.body if isinstance(n, ast.FunctionDef) and n.name in methods]
    namespace = dict(__name__=__name__, torch=torch, re=re, dataclass=dataclass, AUDIO_PLACEHOLDER='<|audio|>',
                     Any=Any, Dict=Dict, List=List, Optional=Optional, Union=Union)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec',
                 flags=__future__.annotations.compiler_flag), namespace)
    instance = namespace['MossTTSDelayProcessor']()
    instance.tokenizer = tokenizer
    instance.model_config = SimpleNamespace(**config)
    for attr in ['audio_user_slot_token', 'audio_assistant_gen_slot_token',
                 'audio_assistant_delay_slot_token', 'audio_start_token', 'audio_end_token']:
        setattr(instance, attr, tokenizer.convert_ids_to_tokens(config[attr + '_id']))
    return torch, tokenizer, config, namespace['UserMessage'], instance


def main():
    before = {**build_inputs(), **fingerprint('research/openmoss_reference',
        'tools/test_openmoss_prompt.py', 'tools/fetch_openmoss_reference.py',
        'research/openmoss_trained/assets.json')}
    binary, compilation = build()
    cache = ROOT / compilation['compile_cache']
    folder = ROOT / 'build/openmoss-prompt-tests' / ('run-' + str(time.time_ns()))
    folder.mkdir(parents=True)
    lock = json.loads((ROOT / 'third_party/openmoss-source-lock.json').read_text(encoding='utf-8'))
    source = validate_sources(lock)
    (folder / 'pipeline.cpp').write_text(guarded_pipeline(source), encoding='utf-8')
    torch, tokenizer, config, UserMessage, processor = official_methods()
    cases = []
    for name, text, length in [('english', 'Hello world.', 0),
            ('chinese', '你好，世界。', 0), ('reference-original-shape', 'Hello world.', 38),
            ('reference-one-frame', 'Hello world.', 1),
            ('reference-minimum', '你好，世界。', 12),
            ('reference-maximum', 'Hello world.', 126),
            ('mixed-script', '你好，LMA! Test 123：本地语音。', 38)]:
        refs = [] if not length else [dict(frames=length,
            codes=[(channel * 31 + frame * 13) % 1024
                   for channel in range(32) for frame in range(length)])]
        cases.append(dict(name=name, text=text, language='English' if name != 'chinese' else 'Chinese', references=refs))
    model = asset_path(assets()['components'][0])
    if not model.is_file():
        raise RuntimeError('Use explicitly acquired existing GGUF; no automatic download')
    drive = next((c + ':' for c in 'UVWXYT' if not Path(c + ':/').exists()), None)
    if not drive:
        raise RuntimeError('No unused owned test alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        def alias(path):
            return drive + '/' + path.relative_to(ROOT).as_posix()
        request = dict(model=alias(model), config=config, cases=cases)
        (folder / 'request.json').write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
        libraries = [cache / 'lma_openmoss_core.lib', cache / 'llama/src/llama.lib']
        libraries += [cache / ('llama/ggml/src/' + name + '.lib') for name in ['ggml', 'ggml-cpu', 'ggml-base']]
        compile_command = ['cl', '/nologo', '/std:c++17', '/EHsc', '/utf-8', '/O2', '/MT',
            '/DNOMINMAX', '/D_CRT_SECURE_NO_WARNINGS',
            '/I' + alias(folder), '/I' + alias(ROOT / 'native/openmoss'),
            '/I' + alias(ROOT / 'build/native-src/sd-cpp/thirdparty'),
            '/I' + alias(source / 'include'), '/I' + alias(source / 'third_party/llama.cpp/include'),
            '/I' + alias(source / 'third_party/llama.cpp/ggml/include'),
            alias(ROOT / 'research/openmoss_reference/prompt_probe.cpp'),
            '/Fe:' + alias(folder / 'prompt-probe.exe'), '/Fo:' + alias(folder / 'prompt-probe.obj'),
            '/link', *[alias(p) for p in libraries], 'advapi32.lib']
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        script = folder / 'compile.cmd'
        script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n'
                          + subprocess.list2cmdline(compile_command) + '\n', encoding='utf-8')
        result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=120)
        (folder / 'compile.log').write_bytes(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError('Inspect ' + str((folder / 'compile.log').relative_to(ROOT)))
        result = subprocess.run([alias(folder / 'prompt-probe.exe'), alias(folder / 'request.json')],
                                capture_output=True, timeout=90)
        (folder / 'native.stdout.json').write_bytes(result.stdout)
        (folder / 'native.stderr.txt').write_bytes(result.stderr)
        if result.returncode:
            raise RuntimeError('Actual native prompt probe failed')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    actual = json.loads(result.stdout)
    comparisons = []
    for case, native in zip(cases, actual, strict=True):
        refs = [torch.tensor(r['codes'], dtype=torch.long).reshape(32, r['frames']).T for r in case['references']]
        message = UserMessage(text=case['text'], language=case['language'], reference=refs or None).to_dict()
        content = tokenizer.apply_chat_template([dict(role='user', content=message['content'])],
                                                add_generation_prompt=True, tokenize=False)
        expected = processor._get_unified_codes('user', content, refs, False)
        observed = torch.tensor(native['grid']).reshape(native['positions'], native['columns'])
        same_shape = list(expected.shape) == list(observed.shape)
        equal = same_shape and torch.equal(expected, observed)
        extra_start_only = (observed.shape[0] == expected.shape[0] + 1
            and torch.equal(expected, observed[:-1])
            and int(observed[-1, 0]) == config['audio_start_token_id']
            and bool((observed[-1, 1:] == config['audio_pad_code']).all()))
        entry = dict(name=case['name'], exact_grid_equal=equal,
            official_shape=list(expected.shape), native_shape=list(observed.shape),
            difference_is_only_extra_assistant_audio_start=extra_start_only)
        comparisons.append(entry)
        (folder / (case['name'] + '-official.json')).write_text(json.dumps(expected.tolist()), encoding='utf-8')
    current(before)
    report = dict(schema='lma.openmoss-prompt-parity/1', cases=comparisons,
        passed=sum(x['exact_grid_equal'] for x in comparisons), expected_cases=len(cases),
        all_exact=all(x['exact_grid_equal'] for x in comparisons), compilation=compilation,
        official_sources=verify_official(),
        processor_sha256=sha(OFFICIAL / 'processing_moss_tts.py'),
        library_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in libraries},
        executable_sha256=sha(folder / 'prompt-probe.exe'),
        capture_directory=folder.relative_to(ROOT).as_posix(), input_fingerprint=before,
        model_inference=False, codec_executed=False, physical_android=False,
        speech_quality_accepted=False, release_accepted=False)
    for target in [folder / 'results.json', folder.parent / 'results.json']:
        target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], expected_cases=len(cases), cases=comparisons)), flush=True)
    if not report['all_exact']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
