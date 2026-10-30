"""Explicit offline full-default Wan decoder experiment, never an acceptance shortcut.

Runs the production worker with complete user-owned test assets on native Windows.
No downloads, remote inference, synthetic frames, or quality/device pass claims.
"""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import time

from build_sd_vulkan import build, inputs as build_inputs
from evidence import current, fingerprint
from fetch_wan_trained import asset_path, inputs as asset_inputs, sha, verify
from sd_variants_capture import execute
from test_wan_trained import PROMPT_A, frame_stats

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**build_inputs(), **asset_inputs(), **fingerprint('tools/probe_wan_quality.py',
            'tools/test_wan_trained.py', 'tools/sd_variants_capture.py',
            'research/wan_trained/catalogue-bundle.json')}


def contact(path, target, mode):
    from PIL import Image, ImageDraw
    with path.open('rb') as stream:
        header = stream.read(28)
        if header[:8] != b'LMAFRM1\0': raise ValueError('Not a generated frame stream')
        w, h, n, fps, ch = struct.unpack('<5I', header[8:])
        if (w, h, n, fps, ch) != (512, 288, 17, 8, 3): raise ValueError('Full default geometry changed')
        canvas = Image.new('RGB', (w*3, h+40), (15, 26, 40)); draw = ImageDraw.Draw(canvas)
        for col, index in enumerate((0, n//2, n-1)):
            stream.seek(28+index*w*h*ch)
            canvas.paste(Image.frombytes('RGB', (w, h), stream.read(w*h*ch)), (col*w, 40))
            draw.text((col*w+8, 9), f'{mode} / WINDOWS / {index+1}/{n} / QUALITY UNACCEPTED', fill='white')
        canvas.save(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['legacy-untiled', 'temporal', 'current-default'], required=True)
    parser.add_argument('--baseline', help='Optional previous complete run/result.json; preserves prompt and sampling values')
    parser.add_argument('--flow-shift', type=float, help='Explicit one-variable sampling experiment')
    parser.add_argument('--steps', type=int, help='Explicit sampling-step experiment; retains full geometry')
    args = parser.parse_args()
    if os.name != 'nt': raise RuntimeError('Native Windows development only')
    before = inputs(); binary, compilation = build(); lock = verify()
    baseline = None
    if args.baseline:
        path = (ROOT/args.baseline).resolve()
        if not path.is_relative_to(ROOT): raise ValueError('Keep experiment inputs inside the requested project')
        baseline = json.loads(path.read_text(encoding='utf-8'))
        if baseline['components'] != lock['components']: raise ValueError('Baseline assets differ')
        source = baseline['request']; prompt = source['input']
        parameters = dict(source['parameters'])
        baseline = dict(file=path.relative_to(ROOT).as_posix(), sha256=sha(path))
    else:
        bundle = json.loads((ROOT/'research/wan_trained/catalogue-bundle.json').read_text(encoding='utf-8'))
        parameters = {key: field['default'] for key, field in bundle['parameters']['fields'].items()}
        parameters.update(threads=6, seed=42)
        prompt = dict(prompt=PROMPT_A, negativePrompt='')
    if args.mode != 'current-default':
        parameters.update(vaeTiling=False, vaeTileSize=128, vaeTemporalTiling=args.mode=='temporal')
    if args.flow_shift is not None: parameters['flowShift'] = args.flow_shift
    if args.steps is not None: parameters['steps'] = args.steps
    if (parameters['width'], parameters['height'], parameters['frames'], parameters['fps']) != (512, 288, 17, 8):
        raise ValueError('This experiment must retain full default video geometry')
    folder = ROOT/'build/wan-quality'/(args.mode+'-'+str(time.time_ns())); folder.mkdir(parents=True, exist_ok=False)
    # Keep T available for existing compiler caches; never touch the user's S alias.
    drive = next((c+':' for c in 'UVWXYZT' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No free task-owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], capture_output=True, check=True)
    def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
    try:
        output = folder/'generated.rgb'
        request = dict(schema='lma.engine-request/1', backend='vulkan', type='video.generate', pipeline='wan21_13b',
                       architecture='wan21', samplingProfile='standard', input=prompt, parameters=parameters,
                       components={c['role']: alias(asset_path(c)) for c in lock['components']}, loras=[], output=alias(output))
        path = folder/'request.json'; path.write_text(json.dumps(request, indent=2)+'\n', encoding='utf-8')
        env = dict(os.environ); env['LMA_VOCAB_UMT5_JSON'] = request['components']['umt5_tokenizer']
        print('CAPTURE '+folder.relative_to(ROOT).as_posix(), flush=True)
        process, logs = execute([alias(binary), alias(path)], env, sampler_steps=parameters['steps'], timeout=7200)
        (folder/'stdout').write_bytes(logs[0]); (folder/'stderr').write_bytes(logs[1])
        report = dict(schema='lma.wan-decoder-experiment/1', mode=args.mode, baseline=baseline,
                      compilation=compilation, components=lock['components'], request=request, process=process,
                      physical_android=False, independent_numerics_accepted=False, video_quality_accepted=False,
                      complete_target16_accepted=False, complete_release_accepted=False, input_fingerprint=before)
        if process['returncode'] == 0:
            report['output'] = frame_stats(output); contact(output, folder/'contact.png', args.mode)
        current(before)
        report['files'] = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(folder.iterdir()) if p.is_file()}
        (folder/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(dict(returncode=process['returncode'], seconds=process['seconds'],
                             report=(folder/'result.json').relative_to(ROOT).as_posix(),
                             output_sha256=report.get('output', {}).get('sha256'))), flush=True)
        if process['returncode'] != 0: raise RuntimeError('Inspect retained actual experiment failure')
    finally:
        subprocess.run(['subst', drive, '/d'], capture_output=True, check=True)


if __name__ == '__main__': main()
