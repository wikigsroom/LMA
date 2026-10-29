"""Private complete trained CPU UNet comparison; synthetic inputs, not images/native/App."""
import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Optional
import socket
import sys
import time
import zipfile

directory = Path(__file__).resolve().parent
root = directory.parents[1]
for key, value in {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
                   'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'CUDA_VISIBLE_DEVICES': '',
                   'HF_HOME': str(root / 'build/hf-reference-cache'),
                   'TORCH_HOME': str(root / 'build/torch-reference-cache'),
                   'TORCHINDUCTOR_CACHE_DIR': str(root / 'build/torch-reference-inductor'),
                   'TORCH_EXTENSIONS_DIR': str(root / 'build/torch-reference-extensions')}.items():
    os.environ[key] = value
sys.path.insert(0, str(root / 'tools'))
from fetch_sd15_trained import sha

print('Wait for the complete Java/native suite before allocating trained reference UNet.', flush=True)
deadline = time.monotonic() + 21600
java_result = root / 'build/sd-variants-app-host-tests/results.json'
while not java_result.exists():
    producer_log = root / 'build/sd-variants-asset-probe/app-run-5.log'
    if b'Traceback (most recent call last)' in producer_log.read_bytes():
        raise RuntimeError('Current Java producer failed; no reference allocation')
    if time.monotonic() > deadline:
        raise RuntimeError('Bounded wait for Java suite exhausted')
    time.sleep(10)
app = json.loads(java_result.read_text(encoding='utf-8'))
assert app['capture_directory'] == 'build/sd-variants-app-host-tests/run-1793296745112181400'
assert app['java']['actual_host_children'] == 8 and len(app['outputs']) == 4 and not app['physical_android']

package = json.loads((directory / 'diffusers-package-reference.json').read_text())
package_source = root / package['source_path']
wheel = package_source.parent / package['filename']
assert sha(wheel) == package['sha256'] and package['version'] == '0.42.1'
with zipfile.ZipFile(wheel) as archive:
    for name in archive.namelist():
        if name.startswith('diffusers/') and name.endswith('.py'):
            assert (package_source / name).read_bytes() == archive.read(name)
sys.path.insert(0, str(package_source))
import numpy as np
import torch
from safetensors import safe_open
import diffusers
from diffusers import UNet2DConditionModel
from diffusers.models.attention_processor import AttnProcessor
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

attempts = []
def deny_network(*args, **kwargs):
    attempts.append('blocked')
    raise RuntimeError('Local trained reference forbids network access')
socket.create_connection = deny_network
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network

original_receipt = json.loads((directory / 'original-unet-acquisition-receipt.json').read_text())
asset = original_receipt['asset']
source = directory / 'originals' / asset['sha256'] / Path(asset['path']).name
stamp = (source.stat().st_size, source.stat().st_mtime_ns)
assert stamp[0] == asset['bytes'] and sha(source) == asset['sha256']
comparison = json.loads((directory / 'lcm-full-unet-comparison.json').read_text())
mapping = json.loads((directory / 'lcm-tensor-mapping.json').read_text())
converted_header = json.loads((directory / 'lcm-checkpoint-header.json').read_text())
prepared = json.loads((directory / 'lcm-fixed-guidance-derivation.json').read_text())
assert comparison['all_mapped_values_equal_original_cast'] and comparison['mapped_tensors'] == 686
assert prepared['source_assets'][0] == asset and prepared['source_parameter_comparison_sha256'] == sha(directory / 'lcm-full-unet-comparison.json')
prepared_path = root / prepared['output']['path']
assert prepared_path.stat().st_size == prepared['output']['bytes'] and sha(prepared_path) == prepared['output']['sha256']
config_raw = (directory / 'original-unet--config.json').read_bytes()
config = json.loads(config_raw)
capture = directory / ('lcm-full-unet-fold-' + str(time.time_ns()))
capture.mkdir(exist_ok=False)
with torch.device('meta'):
    model = UNet2DConditionModel.from_config(config)
with safe_open(source, framework='pt', device='cpu') as stream:
    state = {name: stream.get_tensor(name) for name in stream.keys()}
assert len(state) == 687 and all(value.dtype == torch.float32 and value.device.type == 'cpu' for value in state.values())
assert sum(t.numel() for t in state.values()) == 859602884
model.load_state_dict(state, strict=True, assign=True)
model.eval().requires_grad_(False)
model.set_attn_processor(AttnProcessor())
assert len(list(model.named_parameters())) == 687 and all(p.device.type == 'cpu' for p in model.parameters())
projection = model.time_embedding.cond_proj
original_bias = model.time_embedding.linear_1.bias
assert projection.weight.shape == (320, 256) and original_bias.numel() == 1280
guidance = prepared['distilled_guidance_embedding']
guidance_lock = json.loads((directory / 'diffusers-reference.json').read_text())
guidance_source = next(item for item in guidance_lock['files'] if item['path'].endswith('pipeline_latent_consistency_text2img.py'))
guidance_raw = (directory / guidance_source['local_file']).read_bytes()
assert hashlib.sha256(guidance_raw).hexdigest() == guidance_source['sha256']
guidance_definition = next(node for node in ast.walk(ast.parse(guidance_raw.decode('utf-8')))
                           if isinstance(node, ast.FunctionDef) and node.name == 'get_guidance_scale_embedding')
guidance_scope = dict(torch=torch, Optional=Optional)
exec(compile(ast.fix_missing_locations(ast.Module(body=[guidance_definition], type_ignores=[])),
             'pinned-official-guidance-embedding', 'exec'), guidance_scope)
condition = guidance_scope['get_guidance_scale_embedding'](None, torch.tensor([guidance - 1.]), embedding_dim=256)
cases = []
for index, timestep in enumerate([0, 1, 249, 499, 749, 999]):
    generator = torch.Generator(device='cpu').manual_seed(61000 + index)
    side = 8 if index % 2 == 0 else 16
    cases.append(dict(index=index, timestep=timestep, latent=torch.randn((1, 4, side, side), generator=generator),
                      context=torch.randn((1, 77, 768), generator=generator)))
metrics = []

def run(label, conditioned):
    values = []
    for case in cases:
        started = time.monotonic()
        with torch.inference_mode():
            output = model(case['latent'], torch.tensor([case['timestep']]), encoder_hidden_states=case['context'],
                           timestep_cond=condition if conditioned else None, return_dict=False)[0].detach().clone()
        assert output.shape == case['latent'].shape and torch.isfinite(output).all()
        name = label + '-' + str(case['index']) + '.f32'
        raw = output.numpy().astype('<f4', copy=False).tobytes()
        (capture / name).write_bytes(raw)
        values.append(output)
        print(json.dumps(dict(phase=label, case=case['index'], timestep=case['timestep'],
                              shape=list(output.shape), seconds=time.monotonic() - started,
                              output_sha256=hashlib.sha256(raw).hexdigest())), flush=True)
    return values

def compare(label, actual, expected, gate):
    for case, a, b in zip(cases, actual, expected):
        error = (a - b).double()
        maximum = float(error.abs().max())
        rmse = float(torch.sqrt(torch.mean(error * error)))
        cosine = float(torch.nn.functional.cosine_similarity(a.flatten().double(), b.flatten().double(), dim=0))
        metrics.append(dict(name=label, case=case['index'], timestep=case['timestep'], shape=list(a.shape),
                            max_abs=maximum, rmse=rmse, cosine=cosine, numerical_gate=gate))
        if gate:
            assert maximum <= 2e-4 and rmse <= 5e-5 and cosine >= .99999

original_values = run('original-conditioned-f32', True)
model.time_embedding.cond_proj = None
omitted_values = run('original-omitted-branch-f32', False)
compare('omitted-branch-vs-original', omitted_values, original_values, False)
assert all(float((a - b).abs().max()) > 2e-4 for a, b in zip(omitted_values, original_values))
with torch.inference_mode():
    delta = torch.nn.functional.linear(torch.nn.functional.linear(condition, projection.weight), model.time_embedding.linear_1.weight)[0]
model.time_embedding.linear_1.bias = torch.nn.Parameter(original_bias.detach() + delta, requires_grad=False)
folded_values = run('original-folded-f32', False)
compare('f32-folded-vs-conditioned', folded_values, original_values, True)

model.time_embedding.cond_proj = projection
model.time_embedding.linear_1.bias = original_bias
native_tensors = {t['name']: t for t in converted_header['tensors']}
assert {m['original'] for m in mapping['mapping']} | {'time_embedding.cond_proj.weight'} == set(state)
for entry in mapping['mapping']:
    name = entry['original']
    kind = native_tensors[entry['candidate']]['ggml_type']
    assert kind in [0, 1]
    value = state[name] if kind == 0 else state[name].to(torch.float16).to(torch.float32)
    parent, attribute = name.rsplit('.', 1)
    setattr(model.get_submodule(parent), attribute, torch.nn.Parameter(value, requires_grad=False))
converted_values = run('converted-conditioned-f32-compute', True)
compare('converted-conditioned-vs-original-f32', converted_values, original_values, False)
converted_bias = model.time_embedding.linear_1.bias
with torch.inference_mode():
    delta = torch.nn.functional.linear(torch.nn.functional.linear(condition, projection.weight), model.time_embedding.linear_1.weight)[0]
folded_bias = converted_bias.detach() + delta
bias_header = native_tensors['model.diffusion_model.time_embed.0.bias']
assert bias_header['ggml_type'] == 0 and bias_header['bytes'] == 5120
with prepared_path.open('rb') as stream:
    stream.seek(converted_header['data_offset'] + bias_header['offset'])
    assert stream.read(5120) == folded_bias.numpy().astype('<f4', copy=False).tobytes()
model.time_embedding.cond_proj = None
model.time_embedding.linear_1.bias = torch.nn.Parameter(folded_bias, requires_grad=False)
converted_folded_values = run('converted-folded-f32-compute', False)
compare('converted-folded-vs-converted-conditioned', converted_folded_values, converted_values, True)
assert not attempts and (source.stat().st_size, source.stat().st_mtime_ns) == stamp
record = dict(schema='lma.private-lcm-complete-trained-unet-fold/1',
              experiment_source_sha256=sha(Path(__file__)), reference_package=package,
              reference_versions=dict(torch=torch.__version__, diffusers=diffusers.__version__),
              source_asset=asset, source_full_sha256_verified=True, original_tensors=687, original_parameters=859602884,
              config_sha256=hashlib.sha256(config_raw).hexdigest(), prepared_output=prepared['output'],
              guidance_embedding_reference=guidance_lock,
              parameter_comparison_sha256=sha(directory / 'lcm-full-unet-comparison.json'),
              folded_bias_matches_prepared_candidate=True, guidance=guidance,
              synthetic_latents_and_text_conditioning=True, reduced_latent_geometries=[[1, 4, 8, 8], [1, 4, 16, 16]],
              complete_unet_forward=True, forward_calls=30, actual_trained_weights=True,
              reference_attention='official unfused AttnProcessor', numerical_gates=dict(max_abs=2e-4, rmse=5e-5, min_cosine=.99999),
              metrics=metrics, omitted_branch_negative_controls=6, network_attempts=len(attempts),
              cpu_threads=1, paired_full_unet_fold_checks_passed=True,
              native_cpp_forward=False, complete_canonical_image_pipeline=False, product_preparation_implemented=False,
              physical_android=False, image_quality_accepted=False, complete_target03_accepted=False, complete_release_accepted=False,
              capture_directory=capture.relative_to(root).as_posix())
(capture / 'results.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
(directory / 'lcm-full-unet-fold-results.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: record[k] for k in ['complete_unet_forward', 'forward_calls', 'paired_full_unet_fold_checks_passed',
                                      'native_cpp_forward', 'physical_android', 'image_quality_accepted']}), flush=True)
