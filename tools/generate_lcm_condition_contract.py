"""Verify/generate unlearned fixed-guidance constants from pinned official source."""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import struct

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_SHA = '3723feda1acdf64913f6a8911f7f578dd3725fec61ff9a5174ef863b742f3549'


def generate():
    import torch
    torch.set_num_threads(1)
    source = ROOT / 'build/sd-distilled-asset-probe/reference-pipeline_latent_consistency_text2img.py'
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REFERENCE_SHA:
        raise ValueError('Changed pinned diffusers guidance source')
    nodes = [n for n in ast.walk(ast.parse(raw.decode('utf-8')))
             if isinstance(n, ast.FunctionDef) and n.name == 'get_guidance_scale_embedding']
    if len(nodes) != 1:
        raise ValueError('Ambiguous official guidance helper')
    scope = dict(torch=torch, math=math)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 'pinned-official-guidance-helper', 'exec'), scope)
    # This vector is mathematical sin/cos data, independent of any trained model.
    vector = scope['get_guidance_scale_embedding'](None, torch.tensor([8.5 - 1.]), embedding_dim=256)
    values = vector.contiguous().numpy().astype('<f4').tobytes()
    if len(values) != 1024 or not torch.isfinite(vector).all():
        raise ValueError('Invalid mathematical guidance constants')
    assets = json.loads((ROOT / 'research/sd_distilled_trained/assets.json').read_text(encoding='utf-8'))['assets']
    source_asset = next(a for a in assets if a['id'] == 'lcm_original_unet_f32')
    base_asset = next(a for a in assets if a['id'] == 'lcm_dreamshaper_v7_f16')
    return dict(schema='lma.lcm-condition-contract/1', algorithm='lcm-fixed-guidance-f16-mlp-double-dot/1',
                source=source_asset, base=base_asset, source_tensor_count=687,
                source_header_bytes=83784,
                source_header_sha256='4850c950d96e975e15c267703769bfd3d32f6f2d63bb2e4424b40aeff53b6728',
                distilled_guidance=8.5, sampler_cfg=1.0, guidance_dimensions=256,
                guidance_u32_le=list(struct.unpack('<256I', values)),
                guidance_bytes_sha256=hashlib.sha256(values).hexdigest(),
                mathematical_constants_only=True, learned_data_embedded=False,
                official_reference=dict(repository='huggingface/diffusers', tag='v0.22.0',
                    revision='df60b35e4747c6fba196922de42a383ec0e82c06',
                    path='src/diffusers/pipelines/latent_consistency_models/pipeline_latent_consistency_text2img.py',
                    sha256=REFERENCE_SHA),
                rounding='IEEE-754 nearest ties-to-even; sequential F64 dot, F32 at each linear result; no FMA',
                source_w0_cast='F32 to F16 nearest ties-to-even and back to F32',
                output_tensor='model.diffusion_model.time_embed.0.bias', output_shape=[1280], output_type='F32',
                complete_model_equivalence_proven=False, production_app_integrated=False, physical_android=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = generate()
    destination = ROOT / 'research/lcm_prepare/contract.json'
    if args.write:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    elif json.loads(destination.read_text(encoding='utf-8')) != result:
        raise ValueError('Changed unlearned guidance contract; inspect explicit regeneration')
    print(json.dumps(dict(mathematical_constants=256, learned_data_embedded=False,
                          guidance_bytes_sha256=result['guidance_bytes_sha256'])))
