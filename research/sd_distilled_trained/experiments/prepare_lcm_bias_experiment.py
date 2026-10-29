"""Ignored fixed-guidance derivation experiment, not a product preparation or parity gate."""
import ast
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Optional

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
import numpy as np
import torch
torch.set_num_threads(1)

directory = Path(__file__).resolve().parent
root = directory.parents[1]
sys.path.insert(0, str(root / 'tools'))
from fetch_sd15_trained import sha

source_lock = json.loads((directory / 'diffusers-reference.json').read_text())
reference_sources = {}
for item in source_lock['files']:
    raw = (directory / item['local_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['sha256']
    reference_sources[Path(item['path']).name] = raw.decode('utf-8')
scope = dict(torch=torch, math=math, nn=torch.nn, Optional=Optional, USE_PEFT_BACKEND=True,
             get_activation=lambda name: torch.nn.SiLU() if name == 'silu' else (_ for _ in ()).throw(ValueError(name)))
definitions = []
for filename, names in [('embeddings.py', {'TimestepEmbedding', 'get_timestep_embedding'}),
                        ('pipeline_latent_consistency_text2img.py', {'get_guidance_scale_embedding'})]:
    found = {node.name: node for node in ast.walk(ast.parse(reference_sources[filename]))
             if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names}
    assert set(found) == names
    definitions.extend(found.values())
exec(compile(ast.fix_missing_locations(ast.Module(body=definitions, type_ignores=[])), 'pinned-lcm-subgraph', 'exec'), scope)

receipt = json.loads((directory / 'original-unet-acquisition-receipt.json').read_text())
original = receipt['asset']
candidate = next(a for a in json.loads((directory / 'asset-plan.json').read_text())['assets']
                 if a['id'] == 'lcm_dreamshaper_v7_f16')
original_path = directory / 'originals' / original['sha256'] / Path(original['path']).name
candidate_path = directory / 'originals' / candidate['sha256'] / candidate['path']
header = json.loads((directory / 'lcm-checkpoint-header.json').read_text())
comparison = json.loads((directory / 'lcm-full-unet-comparison.json').read_text())
assert comparison['all_mapped_values_equal_original_cast'] and comparison['mapped_tensors'] == 686
assert comparison['assets'] == [original, candidate] and not comparison['complete_unet_forward']
stamps = [(p.stat().st_size, p.stat().st_mtime_ns) for p in [original_path, candidate_path]]
assert stamps[0][0] == original['bytes'] and stamps[1][0] == candidate['bytes']
print('Rehash complete original before deriving a private fixed-guidance candidate.', flush=True)
assert sha(original_path) == original['sha256']

source_tensors = {t['name']: t for t in receipt['header']['tensors']}
converted_tensors = {t['name']: t for t in header['tensors']}

def original_tensor(name):
    tensor = source_tensors['time_embedding.' + name]
    assert tensor['dtype'] == 'F32'
    start, end = tensor['data_offsets']
    with original_path.open('rb') as stream:
        stream.seek(8 + receipt['header']['header_bytes'] + start)
        raw = stream.read(end - start)
    assert len(raw) == end - start
    return torch.from_numpy(np.frombuffer(raw, dtype='<f4').copy().reshape(tensor['shape']))

names = {'linear_1.weight': 'model.diffusion_model.time_embed.0.weight',
         'linear_1.bias': 'model.diffusion_model.time_embed.0.bias',
         'linear_2.weight': 'model.diffusion_model.time_embed.2.weight',
         'linear_2.bias': 'model.diffusion_model.time_embed.2.bias'}
original_state = {name: original_tensor(name) for name in [*names, 'cond_proj.weight']}
converted_state = {'cond_proj.weight': original_state['cond_proj.weight']}
for name, native_name in names.items():
    tensor = converted_tensors[native_name]
    assert tensor['ggml_type'] in [0, 1]
    dtype = '<f4' if tensor['ggml_type'] == 0 else '<f2'
    with candidate_path.open('rb') as stream:
        stream.seek(header['data_offset'] + tensor['offset'])
        raw = stream.read(tensor['bytes'])
    assert len(raw) == tensor['bytes']
    array = np.frombuffer(raw, dtype=dtype).reshape(list(reversed(tensor['shape'])))
    assert np.array_equal(array, original_state[name].numpy().astype(dtype))
    converted_state[name] = torch.from_numpy(array.astype(np.float32, copy=True))

guidance = 8.5
condition = scope['get_guidance_scale_embedding'](None, torch.tensor([guidance - 1.]), embedding_dim=256)
reference = scope['TimestepEmbedding'](320, 1280, cond_proj_dim=256).eval()
reference.load_state_dict(original_state, strict=True)
quantized_reference = scope['TimestepEmbedding'](320, 1280, cond_proj_dim=256).eval()
quantized_reference.load_state_dict(converted_state, strict=True)
folded = scope['TimestepEmbedding'](320, 1280).eval()
folded.load_state_dict({k: v for k, v in converted_state.items() if k != 'cond_proj.weight'}, strict=True)
samples = scope['get_timestep_embedding'](torch.tensor([0, 1, 249, 499, 749, 999]), 320,
                                         flip_sin_to_cos=True, downscale_freq_shift=0)
with torch.no_grad():
    offset = torch.nn.functional.linear(condition, converted_state['cond_proj.weight'])
    delta = torch.nn.functional.linear(offset, converted_state['linear_1.weight'])[0]
    new_bias = converted_state['linear_1.bias'] + delta
    folded.linear_1.bias.copy_(new_bias)
    measured = folded(samples)
    cast_reference = quantized_reference(samples, condition)
    fp32_reference = reference(samples, condition)
    maximum = float((measured - cast_reference).abs().max())
    assert torch.isfinite(measured).all() and maximum <= 2e-6
    original_maximum = float((measured - fp32_reference).abs().max())

bias_tensor = converted_tensors[names['linear_1.bias']]
assert bias_tensor['ggml_type'] == 0 and bias_tensor['shape'] == [1280] and bias_tensor['bytes'] == 5120
bias_offset = header['data_offset'] + bias_tensor['offset']
replacement = new_bias.numpy().astype('<f4', copy=False).tobytes()
assert len(replacement) == 5120
target_directory = directory / ('lcm-fixed-guidance-experiment-' + str(time.time_ns()))
target_directory.mkdir(exist_ok=False)
partial = target_directory / 'LCM_Dreamshaper_v7-f16-guidance8p5.gguf.partial'
target = partial.with_suffix('')
input_digest = hashlib.sha256()
output_digest = hashlib.sha256()
position = 0
changed = 0
print('Stream one candidate copy; alter only its 5120-byte first time-MLP bias.', flush=True)
with candidate_path.open('rb') as source, partial.open('xb') as output:
    while raw := source.read(4 * 1024 * 1024):
        input_digest.update(raw)
        start, end = max(position, bias_offset), min(position + len(raw), bias_offset + len(replacement))
        if start < end:
            modified = bytearray(raw)
            a, b = start - position, end - position
            portion = replacement[start - bias_offset:end - bias_offset]
            changed += sum(x != y for x, y in zip(modified[a:b], portion))
            modified[a:b] = portion
            raw = modified
        output.write(raw)
        output_digest.update(raw)
        position += len(raw)
    output.flush()
    os.fsync(output.fileno())
assert input_digest.hexdigest() == candidate['sha256'] and position == candidate['bytes'] and changed > 0
for path, stamp in zip([original_path, candidate_path], stamps):
    assert (path.stat().st_size, path.stat().st_mtime_ns) == stamp
assert partial.stat().st_size == candidate['bytes'] and sha(partial) == output_digest.hexdigest()
partial.rename(target)
record = dict(schema='lma.private-lcm-fixed-guidance-derivation/1',
              experiment_source_sha256=sha(Path(__file__)),
              source_assets=[original, candidate], source_objects_full_sha256_verified=True,
              source_parameter_comparison_sha256=sha(directory / 'lcm-full-unet-comparison.json'),
              official_subgraph_source=source_lock, distilled_guidance_embedding=guidance,
              time_mlp_quantization='Use exact converted F16/F32 MLP values with original FP32 condition projection',
              sampler_cfg=1., fixed_guidance_only=True, changed_tensor=names['linear_1.bias'],
              changed_region_bytes=len(replacement), changed_bytes=changed, unchanged_file_length=True,
              output=dict(path=target.relative_to(root).as_posix(), bytes=target.stat().st_size, sha256=output_digest.hexdigest()),
              subgraph_timesteps=[0, 1, 249, 499, 749, 999],
              folded_vs_converted_conditioned_subgraph_max_abs=maximum,
              folded_vs_original_fp32_conditioned_subgraph_max_abs=original_maximum,
              private_experiment_only=True, prepared_checkpoint=True,
              canonical_model_equivalence_proven=False, complete_unet_forward=False,
              native_generation_tested=False, android_preparation_implemented=False,
              physical_android=False, image_quality_accepted=False, complete_release_accepted=False)
(target_directory / 'derivation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
(directory / 'lcm-fixed-guidance-derivation.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in record.items() if k not in ['source_assets', 'official_subgraph_source']}), flush=True)
