"""Execute unchanged production diffusion code with complete trained SDXL and both LoRA families.

Native Windows CPU only; all assets must already exist. No download or Android
execution occurs. All raw successful/failed requests, logs and outputs survive.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import time

from build_sd_host import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_sd15_trained import asset_path as sd15_path, inputs as sd15_inputs, sha, verify as verify_sd15
from fetch_sd_variants_trained import asset_path, inputs as asset_inputs, verify
from sd_variants_capture import execute
from sd_variants_inspect import gguf, safetensors
from sd_variants_manifests import inputs as manifest_inputs

ROOT = Path(__file__).resolve().parents[1]
PROMPT_A = 'A small red fox sitting beside a blue ceramic teapot on a wooden table, pixel art, PixArFK, clean composition'
PROMPT_B = 'A yellow sailboat on a quiet blue lake below snow covered mountains, pixel art, clean composition'


def inputs():
    return {**build_inputs(), **sd15_inputs(), **asset_inputs(), **manifest_inputs(), **fingerprint(
        'tools/test_sd_variants_trained.py', 'tools/sd_variants_capture.py', 'tools/sd_variants_inspect.py', 'research/sd_variants_trained')}


def cases():
    result = []
    for family in ['sd15', 'sdxl']:
        for name, profile, adapters, cancel in [
            ('base-a', 'standard', [], None),
            ('style-zero', 'standard', [(family + '_style_pixelart', 0.)], None),
            ('style-one', 'standard', [(family + '_style_pixelart', 1.)], None),
            ('lcm-a', 'lcm', [(family + '_lcm_lora', 1.)], None),
            ('lcm-style', 'lcm', [(family + '_lcm_lora', 1.), (family + '_style_pixelart', .9 if family == 'sd15' else 1.2)], None),
            ('lcm-cancel-step1', 'lcm', [(family + '_lcm_lora', 1.)], 1),
            ('lcm-recovery-a', 'lcm', [(family + '_lcm_lora', 1.)], None)]:
            result.append(dict(name=family + '-' + name, family=family, profile=profile, adapters=adapters,
                               cancel_step=cancel, prompt=PROMPT_A, width=512, height=512))
        if family == 'sdxl':
            result.append(dict(name='sdxl-base-b', family=family, profile='standard', adapters=[], cancel_step=None,
                               prompt=PROMPT_B, width=512, height=512))
            result.append(dict(name='sdxl-lcm-native-resolution', family=family, profile='lcm', adapters=[('sdxl_lcm_lora', 1.)],
                               cancel_step=None, prompt=PROMPT_A, width=1024, height=1024))
    return result


def image_stats(path):
    from PIL import Image, ImageStat
    with Image.open(path) as image:
        image.load(); rgb = image.convert('RGB'); stats = ImageStat.Stat(rgb)
        return dict(width=image.width, height=image.height, format=image.format, mode=image.mode,
                    bytes=path.stat().st_size, sha256=sha(path), channel_mean=stats.mean,
                    channel_stddev=stats.stddev, extrema=rgb.getextrema(), entropy=rgb.entropy())


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows host only')
    before = inputs(); old = verify_sd15(); lock = verify(); executable, compilation = build()
    acquisition_path = ROOT / 'build/sd-variants-trained/receipt.json'
    acquisition = json.loads(acquisition_path.read_text(encoding='utf-8')); current(acquisition['input_fingerprint'])
    if acquisition['lock'] != lock or not acquisition['explicit_download']: raise ValueError('Different explicit complete acquisition')
    folder = ROOT / 'build/sd-variants-trained-tests' / ('run-' + str(time.time_ns())); folder.mkdir(parents=True, exist_ok=False)
    headers = {}; assets = {item['id']: item for item in lock['assets']}
    for item in lock['assets']:
        headers[item['id']] = gguf(asset_path(item)) if item['format'] == 'gguf' else safetensors(asset_path(item))
    xl = {t['name']: t for t in headers['sdxl_base_q4_0']['tensors']}
    embedding_names = ['cond_stage_model.transformer.text_model.embeddings.token_embedding.weight',
                       'cond_stage_model.1.transformer.text_model.embeddings.token_embedding.weight']
    if [xl[name]['shape'] for name in embedding_names] != [[768, 49408], [1280, 49408]]:
        raise ValueError('SDXL file does not contain both complete CLIP embeddings')
    if sum(name.startswith('first_stage_model.decoder.') for name in xl) < 100 or sum(name.startswith('model.diffusion_model.') for name in xl) < 1000:
        raise ValueError('SDXL all-in-one checkpoint lacks the full diffusion/VAE components')
    for key in ['sd15_style_pixelart', 'sdxl_style_pixelart', 'sd15_lcm_lora', 'sdxl_lcm_lora']:
        if headers[key]['tensor_count'] < 50: raise ValueError('Incomplete trained adapter tensor set')
    (folder / 'headers.json').write_text(json.dumps(headers, indent=2) + '\n', encoding='utf-8')
    drive = next((c + ':' for c in 'TUVWXYZ' if not Path(c + ':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    jobs = []; controls = []; failures = []; comparisons = {}
    try:
        def alias(path): return drive + '/' + path.relative_to(ROOT).as_posix()
        environment = os.environ.copy()
        merges = next(item for item in old['components'] if item['role'] == 'clip_merges')
        environment['LMA_VOCAB_CLIP_MERGES'] = alias(sd15_path(merges))
        models = {'sd15': next(sd15_path(c) for c in old['components'] if c['role'] == 'model'),
                  'sdxl': asset_path(assets['sdxl_base_q4_0'])}
        info, logs = execute([alias(executable), '--info'], environment, timeout=30)
        (folder / 'info.stdout').write_bytes(logs[0]); (folder / 'info.stderr').write_bytes(logs[1])
        expected_info = dict(schema='lma.engine/1', engine='sd_cpp', revision=compilation['source_revision'],
                             backend='cpu', bundled_model_data=False, generation_tested=False)
        if info['returncode'] or info['events'] != [expected_info] or info['protocol_errors']: raise ValueError('Different production worker identity')

        def request(case, output):
            lcm = case['profile'] == 'lcm'
            parameters = dict(width=case['width'], height=case['height'], steps=4 if lcm else 8, cfg=1. if lcm else 7.,
                              sampler='lcm' if lcm else 'euler', scheduler='lcm' if lcm else 'discrete',
                              seed=42, threads=6, vaeTiling=True, flowShift=0)
            return dict(schema='lma.engine-request/1', pipeline=case['family'], architecture=case['family'],
                        samplingProfile=case['profile'], type='image.generate', output=alias(output),
                        input=dict(prompt=case['prompt'], negativePrompt='' if lcm else 'blurry, distorted, low quality'),
                        parameters=parameters, components=dict(model=alias(models[case['family']]), clip_merges=alias(sd15_path(merges))),
                        loras=[dict(path=alias(asset_path(assets[key])), scale=scale) for key, scale in case['adapters']])

        def invoke(name, value, cancel_step=None):
            path = folder / (name + '.json'); path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
            print('Actual trained production diffusion:', name, flush=True)
            result, logs = execute([alias(executable), alias(path)], environment, value['parameters']['steps'], cancel_step)
            for suffix, data in zip(['stdout', 'stderr'], logs): (folder / (name + '.' + suffix)).write_bytes(data)
            result.update(name=name, request_sha256=sha(path), parameters=value['parameters'], pipeline=value['pipeline'],
                          sampling_profile=value['samplingProfile'], adapters=value['loras'])
            print(json.dumps(dict(name=name, returncode=result['returncode'], seconds=result['seconds'],
                                  cancelled=result['forced_host_termination'], events=len(result['events']))), flush=True)
            return result

        for family in ['sd15', 'sdxl']:
            case = next(c for c in cases() if c['family'] == family)
            for suffix, expected in [('wrong-architecture', 'Loaded tensor architecture does not match the selected diffusion recipe'),
                                     ('bad-lcm-cfg', 'Distilled sampling parameters do not match the frozen plan'),
                                     ('bad-lora-scale', 'LoRA scale out of bounds')]:
                name = family + '-' + suffix; output = folder / (name + '.png'); value = request(case, output)
                if suffix == 'wrong-architecture': value.update(pipeline='sdxl' if family == 'sd15' else 'sd15', architecture='sdxl' if family == 'sd15' else 'sd15')
                elif suffix == 'bad-lcm-cfg':
                    value['samplingProfile'] = 'lcm'; value['parameters'].update(steps=4, cfg=7., sampler='lcm', scheduler='lcm'); value['input']['negativePrompt'] = ''
                    value['loras'] = [dict(path=alias(asset_path(assets[family + '_lcm_lora'])), scale=1.)]
                else: value['loras'] = [dict(path=alias(asset_path(assets[family + '_style_pixelart'])), scale=5.)]
                result = invoke(name, value)
                result.update(expected_error=expected, output_exists=output.exists(), passed=result['returncode'] == 1 and
                              result['events'][-1:] == [dict(event='error', message=expected)] and not output.exists()
                              and not result['protocol_errors'] and not result['timed_out'] and not any(result['logs_truncated']))
                controls.append(result)
                (folder / (name + '-capture.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                if not result['passed']: failures.append(name)

        for case in cases():
            name = case['name']; output = folder / (name + '.png'); value = request(case, output)
            result = invoke(name, value, case['cancel_step']); result.update(case=case, output_exists=output.exists())
            steps = value['parameters']['steps']; phase = None; consistent = True
            for event in result['events']:
                if event.get('event') == 'stage': phase = event['stage']
                elif event.get('event') == 'progress': consistent = consistent and phase in ['loading', 'generating'] and event['stage'] == phase
            result['progress_phase_consistent'] = consistent
            result['sampling_steps_observed'] = [e.get('step') for e in result['events'] if e.get('event') == 'progress' and e.get('stage') == 'generating' and e.get('steps') == steps]
            complete = [e for e in result['events'] if e.get('event') == 'complete']
            common = consistent and not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated'])
            if case['cancel_step'] is not None:
                trigger = result['cancel_trigger'] or {}
                result['passed'] = (common and result['forced_host_termination'] and result['returncode'] != 0 and not complete and not output.exists()
                                    and trigger.get('stage') == 'generating' and trigger.get('steps') == steps and 1 <= trigger.get('step', -1) < steps)
                controls.append(result)
            else:
                result['passed'] = (common and result['returncode'] == 0 and output.is_file() and len(complete) == 1
                                    and complete[0] == dict(event='complete', output=alias(output), format='png', width=case['width'], height=case['height'])
                                    and result['sampling_steps_observed'] == list(range(steps + 1)))
                if output.is_file():
                    stats = image_stats(output); result['image'] = stats
                    result['passed'] = (result['passed'] and stats['format'] == 'PNG' and stats['mode'] == 'RGB'
                                        and stats['width'] == case['width'] and stats['height'] == case['height']
                                        and all(math.isfinite(x) and 1 < x <= 128 for x in stats['channel_stddev']))
                jobs.append(result)
            (folder / (name + '-capture.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            if not result['passed']: failures.append(name)
            if result['timed_out']: break
        images = {j['name']: j.get('image', {}).get('sha256') for j in jobs}
        for family in ['sd15', 'sdxl']:
            for label, left, right, equal in [('zero_matches_base', 'base-a', 'style-zero', True),
                                               ('style_changes_output', 'base-a', 'style-one', False),
                                               ('combined_style_changes_output', 'lcm-a', 'lcm-style', False),
                                               ('recovery_matches_lcm', 'lcm-a', 'lcm-recovery-a', True)]:
                a, b = images.get(family + '-' + left), images.get(family + '-' + right)
                comparisons[family + '_' + label] = bool(a and b and ((a == b) == equal))
        a, b = images.get('sdxl-base-a'), images.get('sdxl-base-b')
        comparisons['sdxl_prompt_changes_output'] = bool(a and b and a != b)
        failures.extend(key for key, passed in comparisons.items() if not passed)
    finally: subprocess.run(['subst', drive, '/D'], check=True, capture_output=True)
    current(before)
    files = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
    report = dict(schema='lma.sd-variants-trained-host/1', compilation=compilation, acquisition=acquisition,
                  acquisition_receipt_sha256=sha(acquisition_path), existing_sd15_bundle=old, headers=headers,
                  info=info, jobs=jobs, controls=controls, comparisons=comparisons, files=files,
                  capture_directory=folder.relative_to(ROOT).as_posix(), failures=failures,
                  trained_model_executed=any(j.get('image') for j in jobs), host_execution_checks_passed=not failures,
                  production_worker_source_unmodified=True, production_vocabulary_source_unmodified=True, backend='cpu',
                  fixture=False, all_assets_already_present=True, asset_download_attempted=False,
                  android_compiled=False, physical_android=False, app_executed=False, semantic_quality_accepted=False,
                  device_resource_fit_accepted=False, android_background_accepted=False,
                  complete_target02_accepted=False, complete_target03_accepted=False, complete_target05_accepted=False,
                  complete_release_accepted=False, input_fingerprint=before)
    for path in [folder / 'results.json', folder.parent / 'results.json']: path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(failures=failures, comparisons=comparisons, capture_directory=report['capture_directory'])), flush=True)
    if failures: raise SystemExit(1)


if __name__ == '__main__': main()
