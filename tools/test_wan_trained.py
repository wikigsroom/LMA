"""Run complete selected Wan assets through the production Vulkan worker on Windows.

Development evidence only: Windows Vulkan/FFmpeg are not Android acceptance.
No assets are downloaded, and no numerical/quality threshold is relaxed.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

from build_sd_vulkan import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_wan_trained import BUNDLE_ID, asset_path, inputs as asset_inputs, sha, verify
from sd_variants_capture import execute

ROOT = Path(__file__).resolve().parents[1]
PROMPT_A = 'A small red toy robot waving its hand beside a blue ceramic teapot on a wooden table, gentle camera movement, soft daylight'
PROMPT_B = 'A yellow sailboat moving across a calm blue lake below snow covered mountains, bright daylight, detailed landscape'


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint(
        'tools/test_wan_trained.py', 'tools/sd_variants_capture.py', 'research/wan_trained',
        'app/src/main/assets/recipe-templates.json', 'catalogue/model-bundles.json')}


def frame_stats(path):
    """Inspect the real generated RGB stream without a synthetic video fixture."""
    from PIL import Image, ImageStat, ImageChops
    with path.open('rb') as stream:
        header = stream.read(28)
        if len(header) != 28 or header[:8] != b'LMAFRM1\0': raise ValueError('Invalid generated frame header')
        width, height, count, fps, channels = struct.unpack('<5I', header[8:])
        if not (64 <= width <= 2048 and 64 <= height <= 2048 and 2 <= count <= 129 and 1 <= fps <= 60 and channels == 3):
            raise ValueError('Invalid actual frame geometry')
        if path.stat().st_size != 28 + width * height * count * 3: raise ValueError('Incomplete actual generated frames')
        hashes = []; deviations = []; differences = []; first = None
        for _ in range(count):
            pixels = stream.read(width * height * 3); hashes.append(hashlib.sha256(pixels).hexdigest())
            image = Image.frombytes('RGB', (width, height), pixels)
            deviations.append(ImageStat.Stat(image).stddev)
            if first is None: first = image.copy()
            else: differences.append(max(v[1] for v in ImageChops.difference(first, image).getextrema()))
    return dict(bytes=path.stat().st_size, sha256=sha(path), width=width, height=height, frames=count, fps=fps,
                channels=channels, frame_sha256=hashes, channel_stddev=deviations,
                changed_from_first=sum(v > 0 for v in differences), maximum_motion_delta=max(differences, default=0),
                quality_accepted=False)


def main():
    if os.name != 'nt': raise RuntimeError('Native Windows Vulkan only')
    before = inputs(); lock = verify(); binary, compilation = build()
    bundle = next(b for b in json.loads((ROOT/'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['id'] == BUNDLE_ID)
    if bundle['components'] != lock['components']: raise ValueError('Catalogue differs from complete selected assets')
    folder = ROOT/'build/wan-trained-tests'/('run-'+str(time.time_ns())); folder.mkdir(parents=True, exist_ok=False)
    drive = next((c+':' for c in 'UVWXYZT' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No free owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    runs = []; checks = []; outputs = {}
    def check(value, description): checks.append(dict(passed=bool(value), description=description))
    try:
        def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
        env = dict(os.environ)
        env['LMA_VOCAB_UMT5_JSON'] = alias(asset_path(next(c for c in lock['components'] if c['role'] == 'umt5_tokenizer')))
        info, logs = execute([alias(binary), '--info'], env, timeout=30)
        (folder/'info.stdout').write_bytes(logs[0]); (folder/'info.stderr').write_bytes(logs[1])
        check(info['returncode'] == 0 and info['events'][0].get('engine') == 'wan_sd_cpp' and
              info['events'][0].get('backend') == 'vulkan', 'Actual signed-source Vulkan worker identity')
        for name, prompt, steps, cancel, error in [
            ('a', PROMPT_A, 4, None, None), ('b', PROMPT_B, 4, None, None),
            ('one-step', PROMPT_A, 1, None, None), ('cancel-step1', PROMPT_A, 4, 1, None),
            ('empty-prompt', '', 4, None, 'Invalid prompt or output'),
            ('wrong-task', PROMPT_A, 4, None, 'Unsupported diffusion task'),
            ('recovery-a', PROMPT_A, 4, None, None),
            ('legacy-a', PROMPT_A, 4, None, None),
            ('bad-tile', PROMPT_A, 4, None, 'VAE tile size must be 128-1024 pixels, aligned to 64')]:
            output = folder/(name+'.rgb')
            request = dict(schema='lma.engine-request/1', backend='vulkan',
                type='audio.generate' if name == 'wrong-task' else 'video.generate', pipeline='wan21_13b',
                architecture='wan21', samplingProfile='standard', input=dict(prompt=prompt, negativePrompt=''),
                parameters=dict(width=256, height=256, frames=5, fps=8, steps=steps, threads=6, seed=42,
                    cfg=6, sampler='euler', scheduler='discrete', flowShift=3, vaeTiling=True,
                    vaeTileSize=512, vaeTemporalTiling=True),
                components={c['role']: alias(asset_path(c)) for c in lock['components']}, loras=[], output=alias(output))
            if name == 'legacy-a':
                request['parameters'].pop('vaeTileSize'); request['parameters'].pop('vaeTemporalTiling')
            if name == 'bad-tile': request['parameters']['vaeTileSize'] = 129
            path = folder/(name+'.json'); path.write_text(json.dumps(request, indent=2)+'\n', encoding='utf-8')
            print('Execute complete trained Wan Vulkan:', name, flush=True)
            result, logs = execute([alias(binary), alias(path)], env, sampler_steps=steps, cancel_step=cancel)
            stdout = folder/(name+'.stdout'); stderr = folder/(name+'.stderr')
            stdout.write_bytes(logs[0]); stderr.write_bytes(logs[1])
            item = dict(name=name, request=request, process=result, stdout_sha256=sha(stdout), stderr_sha256=sha(stderr))
            (folder/(name+'-capture.json')).write_text(json.dumps(item, indent=2)+'\n', encoding='utf-8')
            check(not result['timed_out'] and not result['protocol_errors'] and not any(result['logs_truncated']), name+': bounded structured protocol')
            complete = [e for e in result['events'] if e.get('event') == 'complete']
            if cancel:
                check(result['forced_host_termination'] and result['cancel_trigger']['step'] == 1 and result['cancel_to_exit_seconds'] < 5,
                      name+': actual sampler step triggers owned child termination')
                check(not complete and not output.exists(), name+': no cancelled result published')
            elif error:
                check(result['returncode'] != 0 and [e.get('message') for e in result['events'] if e.get('event') == 'error'] == [error]
                      and not output.exists(), name+': explicit structured local rejection')
            else:
                check(result['returncode'] == 0 and len(complete) == 1 and output.is_file(), name+': complete trained RGB video')
                execution = [e.get('details', {}) for e in result['events'] if e.get('event') == 'execution']
                check(len(execution) == 1 and execution[0].get('vulkanGraphObserved') is True and execution[0].get('textBackend') == 'cpu'
                      and execution[0].get('vaeBackend') == 'cpu' and execution[0].get('diffusionBackend') == 'vulkan0'
                      and execution[0].get('remoteInference') is False, name+': completed real GPU matrix operation with CPU text/VAE')
                if output.is_file():
                    item['frames'] = frame_stats(output); outputs[name] = item['frames']
                    check((item['frames']['width'], item['frames']['height'], item['frames']['frames'], item['frames']['fps']) == (256, 256, 5, 8), name+': exact explicitly selected small test geometry')
                    check(item['frames']['changed_from_first'] > 0 and max(max(v) for v in item['frames']['channel_stddev']) > 1,
                          name+': actual nonuniform moving frames, not a quality assessment')
                check(any(e.get('event') == 'progress' and e.get('stage') == 'generating' and e.get('step') == steps
                          and e.get('steps') == steps for e in result['events']), name+': actual final sampler step')
                check(result['resources']['observed'] and result['resources']['observed_peak_working_set_bytes'] > 0, name+': observed Windows process memory')
            runs.append(item)
            (folder/(name+'-result.json')).write_text(json.dumps(item, indent=2)+'\n', encoding='utf-8')
        historical = json.loads(subprocess.check_output(['git', 'show', '0ec5042515656481c7c728cce5039a1aec979dff:verification/development/wan-trained.json'], cwd=ROOT))
        original = next(r['frames']['sha256'] for r in historical['runs'] if r['name'] == 'a')
        check(outputs.get('legacy-a', {}).get('sha256') == original,
              'Legacy frozen parameters reproduce the exact dev39 RGB SHA with the updated production worker')
        for right in ['b', 'one-step', 'recovery-a']:
            check('a' in outputs and right in outputs and
                  ((outputs['a']['sha256'] == outputs[right]['sha256']) if right == 'recovery-a' else (outputs['a']['sha256'] != outputs[right]['sha256'])),
                  right+': exact deterministic recovery or changed prompt/steps')
    finally:
        subprocess.run(['subst', drive, '/D'], capture_output=True, check=True)
    current(before)
    report = dict(schema='lma.wan-trained-host/1', selection_id='16', bundle_id=BUNDLE_ID,
        components=lock['components'], capture_directory=folder.relative_to(ROOT).as_posix(), compilation=compilation,
        runs=runs, checks=checks, passed=sum(c['passed'] for c in checks), host_execution_checks_passed=all(c['passed'] for c in checks),
        full_components_executed=True, production_worker_source_unmodified=True, physical_android=False,
        android_codec_tested=False, independent_numerics_accepted=False, video_quality_accepted=False,
        complete_target16_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    report['files'] = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
    for path in [folder/'results.json', folder.parent/'results.json']: path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'], checks=len(checks), runs=len(runs), outputs=len(outputs))), flush=True)
    if not report['host_execution_checks_passed']: raise RuntimeError('Inspect retained real Wan failures; no gate was relaxed')


if __name__ == '__main__': main()
