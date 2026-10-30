"""Compare actual native delayed sampling with unchanged pinned official methods.

Fixed greedy logits isolate the real scheduling/extraction algorithm. No model
weights, generated speech, Android execution or network calls are involved.
"""
import __future__
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

from build_openmoss_host import build
from evidence import current, fingerprint
from fetch_openmoss import validate_sources
from fetch_openmoss_reference import CACHE, verify
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def official_methods():
    import torch
    import torch.nn.functional as F
    namespace = dict(torch=torch, F=F, tqdm=lambda sequence, **kwargs: sequence)
    trees = [ast.parse((CACHE / name).read_text(encoding='utf-8')) for name in
             ['inference_utils.py', 'modeling_moss_tts.py', 'processing_moss_tts.py']]
    nodes = [node for node in trees[0].body if isinstance(node, ast.FunctionDef)]
    model = next(n for n in trees[1].body if isinstance(n, ast.ClassDef) and n.name == 'MossTTSDelayModel')
    nodes += [next(n for n in model.body if isinstance(n, ast.FunctionDef) and n.name == 'generate')]
    processor = next(n for n in trees[2].body if isinstance(n, ast.ClassDef) and n.name == 'MossTTSDelayProcessor')
    method = next(n for n in processor.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_de_delay_pattern')
    method.decorator_list = []  # Static binding only; method body stays unchanged.
    nodes.append(method)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<pinned official methods>', 'exec',
                 flags=__future__.annotations.compiler_flag), namespace)
    return namespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-delay', type=Path, help='Explicit local candidate source; never production/Android acceptance')
    args = parser.parse_args()
    candidate = args.candidate_delay.resolve() if args.candidate_delay else None
    if candidate:
        candidate.relative_to(ROOT)
        if not candidate.is_file(): raise ValueError('Missing local delay candidate')
    lock = verify()
    before = fingerprint('research/openmoss_reference', 'tools/test_openmoss_delay.py',
                         'tools/fetch_openmoss_reference.py', 'tools/openmoss_pipeline.py',
                         'native/openmoss', 'third_party/openmoss-source-lock.json')
    if candidate: before.update(fingerprint(candidate.relative_to(ROOT).as_posix()))
    binary, compilation = build()
    source_lock = json.loads((ROOT / 'third_party/openmoss-source-lock.json').read_text(encoding='utf-8'))
    source = validate_sources(source_lock)
    config = json.loads((CACHE / 'config.json').read_text(encoding='utf-8'))
    config.update(pad_token_id=151643, im_start_token_id=151644, im_end_token_id=151645)
    pad = config['audio_pad_code']; start = config['audio_start_token_id']
    gen = config['audio_assistant_gen_slot_token_id']; delay = config['audio_assistant_delay_slot_token_id']
    def row(token): return [token] + [pad] * config['n_vq']
    plain = [row(config['im_start_token_id']), row(7), row(8)]
    reference = [row(config['im_start_token_id']), row(start)]
    reference += [[config['audio_user_slot_token_id']] + [c + 1 for c in range(config['n_vq'])] for _ in range(40)]
    reference += [row(config['audio_end_token_id'])] + plain
    schedule = [start] + [gen] * 9 + [delay] + [42] * 35 + [config['im_end_token_id']] * 10
    cases = [dict(name='plain-generation', prompt=plain, schedule=schedule),
             dict(name='assistant-started', prompt=plain + [row(start)], schedule=[gen] * 10 + schedule[10:]),
             dict(name='reference-generation', prompt=reference, schedule=schedule),
             dict(name='truncated', prompt=plain, schedule=[start] + [gen] * 40),
             dict(name='reference-without-generated-audio', prompt=reference, schedule=[42] * 40)]
    folder = ROOT / 'build/openmoss-delay-tests' / ('run-' + str(time.time_ns()))
    folder.mkdir(parents=True)
    request = folder / 'request.json'
    request.write_text(json.dumps(dict(config=config, cases=cases)), encoding='utf-8')
    cache = ROOT / compilation['compile_cache']
    libraries = [cache / 'lma_openmoss_core.lib', cache / 'llama/src/llama.lib']
    libraries += [cache / ('llama/ggml/src/' + name + '.lib') for name in ['ggml', 'ggml-cpu', 'ggml-base']]
    drive = next(c + ':' for c in 'VWXYTU' if not Path(c + ':/').exists())
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        command = ['cl', '/nologo', '/std:c++17', '/EHsc', '/utf-8', '/O2', '/MT', '/DNDEBUG', '/DNOMINMAX',
            '/I' + alias(ROOT / 'build/native-src/sd-cpp/thirdparty'), '/I' + alias(source / 'include'),
            '/I' + alias(source / 'third_party/llama.cpp/include'),
            '/I' + alias(source / 'third_party/llama.cpp/ggml/include'),
            alias(ROOT / 'research/openmoss_reference/delay_probe.cpp'),
            *([alias(candidate)] if candidate else []),
            '/I' + alias(source / 'src'),
            '/Fe:' + alias(folder / 'delay-probe.exe'), '/Fo:' + alias(folder) + '/',
            '/link', *[alias(p) for p in libraries], 'advapi32.lib']
        setup = os.environ.get('LMA_VCVARS', r'C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat')
        script = folder / 'compile.cmd'
        script.write_text('@echo off\ncall "' + setup + '" >nul\nif errorlevel 1 exit /b %errorlevel%\n' + subprocess.list2cmdline(command) + '\n', encoding='utf-8')
        result = subprocess.run(['cmd', '/d', '/c', str(script)], capture_output=True, timeout=120)
        (folder / 'compile.log').write_bytes(result.stdout + result.stderr)
        if result.returncode: raise RuntimeError('Inspect delay probe compile log: ' + str(folder))
        result = subprocess.run([alias(folder / 'delay-probe.exe'), alias(request)], capture_output=True, timeout=60)
        (folder / 'native.stdout.json').write_bytes(result.stdout)
        (folder / 'native.stderr.txt').write_bytes(result.stderr)
        if result.returncode: raise RuntimeError('Native delay probe failed: ' + str(folder))
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    observed = json.loads(result.stdout)
    import torch
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    methods = official_methods()
    class FixedLogits:
        def __init__(self, case): self.config = SimpleNamespace(**config); self.config.language_config = SimpleNamespace(**config['language_config']); self.case = case; self.step = 0
        def __call__(self, **kwargs):
            step = self.step; self.step += 1
            text = torch.full((1, 1, config['language_config']['vocab_size']), -1000000.)
            for token, value in [(42,-10),(start,-20),(gen,-30),(delay,-40),(config['im_end_token_id'],-50)]: text[0,0,token] = value
            text[0,0,self.case['schedule'][step]] = 100
            logits = [text]
            for cb in range(config['n_vq']):
                audio = torch.full((1, 1, config['audio_vocab_size'] + 1), -1000000.)
                audio[0,0,(step * 37 + cb * 11) % config['audio_vocab_size']] = 100
                logits.append(audio)
            return SimpleNamespace(logits=logits, past_key_values=None)
    comparisons = []
    for case, native in zip(cases, observed):
        prompt = torch.tensor([case['prompt']], dtype=torch.long)
        result = methods['generate'](FixedLogits(case), prompt, attention_mask=torch.ones(prompt.shape[:2], dtype=torch.long),
            max_new_tokens=len(case['schedule']), text_temperature=0, audio_temperature=0, audio_repetition_penalty=1)
        prefix, assistant = result[0]
        expected = assistant[prefix:]
        actual = torch.tensor(native['rows'], dtype=torch.long)
        first = next((i for i in range(min(len(expected), len(actual))) if not torch.equal(expected[i], actual[i])), None)
        extracted = methods['apply_de_delay_pattern'](assistant[:,1:])
        extracted = extracted[(extracted != pad).any(dim=1)]
        audio = extracted.T.contiguous().tolist()
        equal_codes = native['frames'] == extracted.shape[0] and native['codes'] == [v for head in audio for v in head]
        entry = dict(name=case['name'], exact_rows=expected.shape == actual.shape and torch.equal(expected, actual),
            first_different_step=first, official_rows=len(expected), native_rows=len(actual),
            exact_codes=equal_codes, official_frames=int(extracted.shape[0]), native_frames=native['frames'])
        comparisons.append(entry)
        (folder / (case['name'] + '-official.json')).write_text(json.dumps(dict(rows=expected.tolist(), codes=audio)), encoding='utf-8')
    current(before)
    report = dict(schema='lma.openmoss-delay-reference/1', cases=comparisons,
        passed=sum(c['exact_rows'] and c['exact_codes'] for c in comparisons), expected_cases=len(cases),
        all_exact=all(c['exact_rows'] and c['exact_codes'] for c in comparisons),
        candidate_only=bool(candidate), candidate_sha256=sha(candidate) if candidate else None,
        official_sources=lock, compilation=compilation,
        native_executable_sha256=sha(folder / 'delay-probe.exe'),
        library_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in libraries},
        input_fingerprint=before, capture_directory=folder.relative_to(ROOT).as_posix(),
        model_inference=False, logits_are_fixtures=True, codec_executed=False, network_calls=0,
        physical_android=False, speech_quality_accepted=False, release_accepted=False)
    for path in [folder / 'results.json', folder.parent / 'results.json']:
        path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], expected_cases=len(cases), cases=comparisons)), flush=True)
    if not report['all_exact']: raise SystemExit(1)


if __name__ == '__main__': main()
