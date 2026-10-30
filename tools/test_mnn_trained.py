"""Execute all thirteen real Sana components with the production CPU worker, offline.

Host execution/parameter/recovery evidence only. No phone, reference-numerics or
image-quality acceptance is inferred from these checks. Never downloads assets.
"""
import json
import os
from pathlib import Path
import subprocess
import time

from PIL import Image, ImageChops, ImageStat

from build_mnn_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_mnn_trained import verify, asset_path, inputs as asset_inputs, sha
from test_sd15_trained import execute

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ['A red ceramic teapot on a wooden table, studio photograph, soft light',
           'A small sailboat on a blue lake, snow covered mountain, landscape photograph']


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/test_mnn_trained.py', 'tools/test_sd15_trained.py')}


def image_stats(path):
    with Image.open(path) as source:
        if source.format != 'PNG': raise ValueError('Different actual image format')
        image = source.convert('RGB'); stats = ImageStat.Stat(image)
        return dict(bytes=path.stat().st_size, sha256=sha(path), width=image.width, height=image.height,
                    mean=stats.mean, stddev=stats.stddev, extrema=image.getextrema())


def difference(left, right):
    with Image.open(left) as a, Image.open(right) as b:
        delta = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
        stats = ImageStat.Stat(delta)
        return dict(maximum=max(hi for lo, hi in delta.getextrema()), mean=sum(stats.mean) / 3)


def workspace(folder, lock, alias):
    root = folder / 'workspace'
    llm_roles = {'llm', 'llm_data', 'llm_config', 'tokenizer', 'meta_queries'}
    for item in lock['components']:
        if item['role'] == 'llm_config': continue
        destination = root / ('llm' if item['role'] in llm_roles else 'models') / Path(item['path']).name
        destination.parent.mkdir(parents=True, exist_ok=True); os.link(asset_path(item), destination)
    metadata = json.loads(next(asset_path(i) for i in lock['components'] if i['role'] == 'llm_config').read_text(encoding='utf-8'))
    # Same explicit allowlist as MnnSpec; Java integration independently exercises production sanitization.
    (root / 'llm/llm_config.json').write_text(json.dumps({k: metadata[k] for k in
        ('model_type', 'hidden_size', 'attention_mask', 'attention_type', 'tie_embeddings')}), encoding='utf-8')
    config = dict(llm_model='llm.mnn', llm_weight='llm.mnn.weight', backend_type='cpu', thread_num=4,
                  precision='low', memory='low', max_all_tokens=768, max_new_tokens=0, use_mmap=False,
                  use_cached_mmap=False, kvcache_mmap=False, prompt_cache=False, reuse_kv=False,
                  tmp_path=alias(root) + '/')
    (root / 'llm/config.json').write_text(json.dumps(config), encoding='utf-8')
    return root


def main():
    before = inputs(); lock = verify(); binary, compilation = build()
    folder = ROOT / 'build/mnn-trained-tests' / ('run-' + str(time.time_ns())); folder.mkdir(parents=True)
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    checks = []; runs = []; outputs = {}; comparisons = {}
    def check(value, description):
        checks.append(dict(passed=bool(value), description=description))
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        root = workspace(folder, lock, alias)
        info, logs = execute([alias(binary), '--info'], dict(os.environ), timeout=30)
        check(info['returncode'] == 0 and len(info['events']) == 1 and info['events'][0].get('engine') == 'mnn_diffusion', 'Actual native engine identity')
        check(not info['protocol_errors'] and not logs[1], 'Identity diagnostics remain isolated')

        def invoke(name, prompt=PROMPTS[0], parameters=None, negative='', broken=None, output_invalid=False, pipeline='sana_mnn_v1'):
            p = dict(width=512, height=512, steps=10, threads=4, maxInputTokens=512, useCfg=False, cfg=4, seed=42)
            if parameters: p.update(parameters)
            output = folder / (name + '.png')
            command = dict(schema='lma.engine-request/1', type='image.generate', pipeline=pipeline,
                           input=dict(prompt=prompt, negativePrompt=negative), parameters=p,
                           workspace=alias(root), output=alias(output if not output_invalid else folder / 'missing-parent' / 'invalid.png'))
            request = folder / (name + '.json'); request.write_text(json.dumps(command, indent=2) + '\n', encoding='utf-8')
            removed = None
            if broken:
                removed = root / broken; os.unlink(removed)
            print('Execute actual Sana components:', name, flush=True)
            try: result, logs = execute([alias(binary), alias(request)], dict(os.environ), timeout=600)
            finally:
                if removed is not None:
                    source = next(asset_path(i) for i in lock['components'] if Path(i['path']).name == removed.name)
                    os.link(source, removed)
            (folder / (name + '.stdout')).write_bytes(logs[0]); (folder / (name + '.stderr')).write_bytes(logs[1])
            success = not (broken or output_invalid or pipeline != 'sana_mnn_v1' or p['maxInputTokens'] == 1 or negative and not p['useCfg'])
            complete = [e for e in result['events'] if e.get('event') == 'complete']
            check(not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated']) and not logs[1], name + ': bounded structured protocol, no leaked diagnostics')
            item = dict(name=name, request=command, process=result,
                        stdout_sha256=sha(folder / (name + '.stdout')), stderr_sha256=sha(folder / (name + '.stderr')))
            if success:
                check(result['returncode'] == 0 and len(complete) == 1 and output.is_file(), name + ': actual complete image')
                if output.is_file():
                    image = image_stats(output); outputs[name] = output; item['image'] = image
                    check(image['width'] == p['width'] and image['height'] == p['height'] and max(image['stddev']) > 1, name + ': requested dimensions and nonuniform RGB pixels; not a quality gate')
                    check(complete[0]['output'] == alias(output) and complete[0]['format'] == 'png', name + ': output provenance')
                progress = [e['fraction'] for e in result['events'] if e.get('event') == 'progress']
                check(progress == [(i + 1) / p['steps'] for i in range(p['steps'])], name + ': every completed real sampling step reported')
                stages = [e['stage'] for e in result['events'] if e.get('event') == 'stage']
                check(stages == ['encoding_text', 'loading_diffusion'], name + ': real pipeline stage transitions')
                check(result['resources']['observed'], name + ': host process memory observed')
            else:
                check(result['returncode'] != 0 and not complete and not output.exists(), name + ': local failure does not publish an artifact')
            runs.append(item)

        invoke('a')
        invoke('b', prompt=PROMPTS[1])
        invoke('cfg-a', parameters={'useCfg': True}, negative='blurry, distorted, low quality')
        invoke('cfg-b', parameters={'useCfg': True}, negative='red, ceramic, teapot')
        invoke('rectangle', parameters={'width': 320, 'height': 256, 'steps': 2})
        invoke('single-step', parameters={'width': 256, 'height': 256, 'steps': 1})
        invoke('token-budget', parameters={'maxInputTokens': 1})
        invoke('negative-needs-cfg', negative='blurry')
        invoke('missing-connector', broken='models/connector.mnn')
        invoke('invalid-output', parameters={'width': 256, 'height': 256, 'steps': 1}, output_invalid=True)
        invoke('wrong-pipeline', pipeline='sana_original')
        invoke('recovery-a')
        for name, a, b in [('prompt-effect', 'a', 'b'), ('cfg-effect', 'a', 'cfg-a'), ('negative-effect', 'cfg-a', 'cfg-b'), ('recovery', 'a', 'recovery-a')]:
            if a in outputs and b in outputs:
                comparisons[name] = difference(outputs[a], outputs[b])
                check((comparisons[name]['maximum'] == 0) if name == 'recovery' else (comparisons[name]['maximum'] > 0), name + ': observed same-host pixel relationship')
            else: check(False, name + ': missing output')
    finally:
        subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    verify(); current(before)
    report = dict(schema='lma.mnn-trained-host/1', passed=all(i['passed'] for i in checks), checks=checks,
                  compilation=compilation, assets=lock['components'], runs=runs, comparisons=comparisons,
                  capture_directory=folder.relative_to(ROOT).as_posix(), real_trained_host_execution=True,
                  model_data_bundled=False, network_inference=False, physical_android=False,
                  independent_reference_numerics_accepted=False, image_quality_accepted=False,
                  complete_target04_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    for path in [folder / 'results.json', folder.parent / 'results.json']:
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), outputs=len(outputs), failed=[c['description'] for c in checks if not c['passed']])), flush=True)
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
