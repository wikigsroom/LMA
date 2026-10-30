"""Offline Windows diagnosis: capture actual Wan latents or decode with the official CPU VAE.

Requires explicitly prepared test weights and pinned research dependencies. No downloads.
The capture intentionally returns the worker's generation error: it never decodes a video.
Independent VAE comparison does not establish diffusion numerics or Android acceptance.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import time
import subprocess

from evidence import current, fingerprint
from fetch_wan_trained import verify, asset_path, sha
from sd_variants_capture import execute

ROOT = Path(__file__).resolve().parents[1]
REVISION = '9737cba9c1c3c4d04b33fcad41c111989865d315'


def local(name):
    path = (ROOT / name).resolve()
    if not path.is_relative_to(ROOT): raise ValueError('Keep diagnostic files inside this project')
    return path


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def tensor(path):
    import numpy as np
    with path.open('rb') as stream:
        if stream.read(8) != b'LMAWZ1\0\0': raise ValueError('Not a captured Wan tensor')
        rank, = struct.unpack('<I', stream.read(4))
        if rank not in (4, 5): raise ValueError('Unexpected latent rank')
        dims = struct.unpack('<'+'q'*rank, stream.read(8*rank))
        count, = struct.unpack('<q', stream.read(8))
        if dims not in ((64, 36, 5, 16), (64, 36, 5, 16, 1)) or count != 64*36*5*16:
            raise ValueError('Diagnostic must preserve full 512x288/17-frame geometry')
        values = np.frombuffer(stream.read(), dtype='<f4').copy()
        if values.size != count or not np.isfinite(values).all(): raise ValueError('Invalid latent data')
    return values.reshape(1, 16, 5, 36, 64), dims


def capture(baseline):
    from build_wan_latent_probe import build_probe
    if os.name != 'nt': raise RuntimeError('Native Windows research only')
    before = fingerprint('tools/probe_wan_latents.py')
    binary, compilation = build_probe()
    lock = verify()
    original = json.loads(baseline.read_text(encoding='utf-8'))
    if original['parameters']['flowShift'] != 3 or original['parameters']['steps'] != 20:
        raise ValueError('Use the preserved flow3/20-step baseline')
    folder = ROOT/'build/wan-quality'/('latents-'+str(time.time_ns())); folder.mkdir()
    drive = next((c+':' for c in 'UVWXYZT' if not Path(c+':/').exists()), None)
    if not drive: raise RuntimeError('No free task-owned ASCII alias')
    subprocess.run(['subst', drive, str(ROOT)], check=True, capture_output=True)
    def alias(path): return drive+'/'+path.relative_to(ROOT).as_posix()
    try:
        request = dict(original)
        request['components'] = {c['role']: alias(asset_path(c)) for c in lock['components']}
        request['output'] = alias(folder/'must-not-exist.rgb')
        save(folder/'request.json', request)
        env = dict(os.environ, LMA_WAN_PROBE_LATENTS=alias(folder/'denoised.f32'),
                   LMA_VOCAB_UMT5_JSON=request['components']['umt5_tokenizer'])
        print('CAPTURE '+folder.relative_to(ROOT).as_posix(), flush=True)
        process, logs = execute([alias(binary), alias(folder/'request.json')], env,
                                sampler_steps=20, timeout=3600)
        (folder/'stdout').write_bytes(logs[0]); (folder/'stderr').write_bytes(logs[1])
        report = dict(schema='lma.wan-latent-capture/1', compilation=compilation,
                      baseline=dict(path=baseline.relative_to(ROOT).as_posix(), sha256=sha(baseline)),
                      components=lock['components'], request=request, process=process,
                      generation_completed=False, physical_android=False, video_quality_accepted=False,
                      independent_diffusion_numerics_accepted=False, complete_release_accepted=False,
                      input_fingerprint=before)
        if (folder/'denoised.f32').exists():
            values, dims = tensor(folder/'denoised.f32')
            report['latent'] = dict(bytes=(folder/'denoised.f32').stat().st_size,
                                    sha256=sha(folder/'denoised.f32'), dimensions=dims,
                                    minimum=float(values.min()), maximum=float(values.max()))
        current(before); save(folder/'result.json', report)
        if process['returncode'] == 0 or not report.get('latent') or (folder/'must-not-exist.rgb').exists():
            raise RuntimeError('Inspect retained diagnostic; expected latent capture and generation error')
        print(json.dumps(dict(report=(folder/'result.json').relative_to(ROOT).as_posix(),
                              expected_worker_error=True, seconds=process['seconds'])), flush=True)
    finally:
        subprocess.run(['subst', drive, '/d'], check=True, capture_output=True)


def decode(folder, comparison):
    # Reject missing comparisons before the expensive reference run.
    if comparison and not comparison.is_file(): raise ValueError('Comparison frame stream is missing')
    before = fingerprint('tools/probe_wan_latents.py')
    captured = json.loads((folder/'result.json').read_text(encoding='utf-8'))
    if captured['latent']['sha256'] != sha(folder/'denoised.f32'): raise ValueError('Latent capture changed')
    source = ROOT/'build/wan-reference-source'
    receipt = json.loads((source/'receipt.json').read_text(encoding='utf-8'))
    if receipt['revision'] != REVISION: raise ValueError('Unexpected official reference revision')
    for name, record in receipt['files'].items():
        path = source/Path(name).name
        if sha(path) != record['sha256'] or path.stat().st_size != record['bytes']: raise ValueError('Reference source changed')
    sys.path.insert(0, str(ROOT/'build/wan-reference-python'))
    import numpy as np
    import torch
    import einops
    import safetensors
    from safetensors.torch import load_file
    from PIL import Image, ImageDraw
    spec = importlib.util.spec_from_file_location('lma_official_wan_vae', source/'vae.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    torch.set_num_threads(6)
    weights = next(c for c in verify()['components'] if c['role']=='vae')
    cfg = dict(dim=96, z_dim=16, dim_mult=[1,2,4,4], num_res_blocks=2, attn_scales=[],
               temperal_downsample=[False,True,True], dropout=0.0)
    model = module.WanVAE_(**cfg)
    state = load_file(str(asset_path(weights)))
    model.load_state_dict(state, strict=True); del state
    model = model.float().eval().requires_grad_(False)
    values, dims = tensor(folder/'denoised.f32')
    # Read normalization constants from the pinned wrapper rather than reimplementing them.
    import ast
    tree = ast.parse((source/'vae.py').read_text(encoding='utf-8'))
    wrapper = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=='WanVAE')
    init = next(n for n in wrapper.body if isinstance(n, ast.FunctionDef) and n.name=='__init__')
    constants = {n.targets[0].id: ast.literal_eval(n.value) for n in init.body
                 if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('mean','std')}
    scale = [torch.tensor(constants['mean']), 1/torch.tensor(constants['std'])]
    print('Official CPU VAE / F32 / full captured latent', flush=True)
    start = time.perf_counter()
    with torch.inference_mode():
        result = model.decode(torch.from_numpy(values), scale).clamp(-1,1)
    if tuple(result.shape) != (1,3,17,288,512) or not torch.isfinite(result).all(): raise ValueError('Invalid reference frames')
    rgb = ((result[0].permute(1,2,3,0).numpy()+1)*127.5).clip(0,255).astype(np.uint8)
    out = folder/'official-vae.rgb'
    with out.open('wb') as stream:
        stream.write(b'LMAFRM1\0'+struct.pack('<5I',512,288,17,8,3)); stream.write(rgb.tobytes())
    contact = Image.new('RGB',(1536,328),(15,26,40)); draw = ImageDraw.Draw(contact)
    for col, index in enumerate((0,8,16)):
        contact.paste(Image.fromarray(rgb[index]),(col*512,40))
        draw.text((col*512+8,9),f'OFFICIAL CPU VAE / {index+1}/17 / QUALITY UNACCEPTED',fill='white')
    contact.save(folder/'official-vae.png')
    report = dict(schema='lma.wan-reference-vae/1', source=receipt, capture_sha256=sha(folder/'result.json'),
                  latent_sha256=sha(folder/'denoised.f32'), weights=weights, dtype='float32', device='cpu',
                  implementation='unchanged official WanVAE_', strict_weight_loading=True, seconds=time.perf_counter()-start,
                  packages=dict(torch=torch.__version__, numpy=np.__version__, einops=einops.__version__, safetensors=safetensors.__version__),
                  output=dict(bytes=out.stat().st_size, sha256=sha(out)), physical_android=False,
                  video_quality_accepted=False, independent_diffusion_numerics_accepted=False,
                  complete_release_accepted=False, input_fingerprint=before)
    current(before); save(folder/'reference.json', report)
    if comparison:
        with comparison.open('rb') as stream:
            if stream.read(28) != b'LMAFRM1\0'+struct.pack('<5I',512,288,17,8,3): raise ValueError('Comparison geometry differs')
            other = np.frombuffer(stream.read(),np.uint8).reshape(rgb.shape)
        delta = np.abs(rgb.astype(np.int16)-other.astype(np.int16))
        report['comparison'] = dict(path=comparison.relative_to(ROOT).as_posix(), sha256=sha(comparison),
                                    mean_absolute_byte_error=float(delta.mean()),
                                    per_frame_mean_absolute_byte_error=delta.mean(axis=(1,2,3)).tolist(),
                                    maximum_absolute_byte_error=int(delta.max()))
    current(before); save(folder/'reference.json', report)
    print(json.dumps(dict(report=(folder/'reference.json').relative_to(ROOT).as_posix(), seconds=report['seconds'])),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture',help='Preserved production request.json, full default geometry')
    mode.add_argument('--decode',help='Retained latent-capture directory')
    parser.add_argument('--comparison',help='Retained production untiled RGB stream')
    args=parser.parse_args()
    if args.capture: capture(local(args.capture))
    else: decode(local(args.decode),local(args.comparison) if args.comparison else None)


if __name__=='__main__': main()
