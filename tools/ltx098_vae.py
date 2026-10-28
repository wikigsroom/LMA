"""Offline, exact old-LTX decoder export and original-forward oracle.

Developer assets only. Does not download, install or register an App model.
The original Decoder.forward remains unmodified and is the independent oracle.
"""
import argparse, gc, hashlib, json, math, os, sys, time
from pathlib import Path
from evidence import fingerprint, current

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'third_party/ltx098-vae-source-lock.json'
CHECKPOINT = ROOT / 'build/ltx098-trained/originals/ltxv-2b-0.9.8-distilled.safetensors'
OUT = ROOT / 'build/ltx098-vae-assets'


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inputs():
    return fingerprint('tools/ltx098_vae.py', 'tools/ltx098_assets.py',
                       'tools/ltx098_fixture.py', 'tools/build_ltx098.py',
                       'third_party/ltx098-source-lock.json',
                       'third_party/ltx098-vae-source-lock.json')


def environment():
    from ltx098_fixture import environment as original_environment
    original_environment()
    import importlib.metadata
    lock = json.loads(LOCK.read_text(encoding='utf-8'))
    for name, version in lock['python_versions'].items():
        if importlib.metadata.version(name) != version:
            raise RuntimeError('Changed decoder dependency: ' + name)
    return lock


def decoder(checkpoint=CHECKPOINT):
    lock = environment()
    from ltx098_assets import Checkpoint
    import torch
    from ltx_video.models.autoencoders.causal_video_autoencoder import Decoder
    asset = lock['checkpoint']
    if not checkpoint.is_file() or checkpoint.stat().st_size != asset['bytes'] or sha(checkpoint) != asset['sha256']:
        raise ValueError('Missing/changed pinned developer checkpoint; no automatic download')
    source = Checkpoint(checkpoint)
    if source.config.get('vae') != lock['vae_config']:
        raise ValueError('Different old-LTX VAE configuration')
    with torch.device('meta'):
        model = Decoder(**lock['decoder_options']).eval()
    layout = {key: list(value.shape) for key, value in model.state_dict().items()}
    actual = {key[len('vae.decoder.'):]: value['shape'] for key, value in source.tensors.items() if key.startswith('vae.decoder.')}
    if actual != layout or actual != lock['layout'] or len(layout) != 132 or sum(math.prod(s) for s in layout.values()) != 552814641:
        raise ValueError('Different/incomplete old-LTX decoder layout')
    print('Load 132 trained decoder tensors only (no VAE encoder)', flush=True)
    state = {name: torch.from_numpy(source.array('vae.decoder.' + name)) for name in layout}
    model.load_state_dict(state, assign=True, strict=True)
    mean = torch.from_numpy(source.array('vae.per_channel_statistics.mean-of-means'))
    std = torch.from_numpy(source.array('vae.per_channel_statistics.std-of-means'))
    if mean.shape != (128,) or std.shape != (128,) or not torch.all(std > 0):
        raise ValueError('Invalid per-channel decoder statistics')
    return model, mean, std, lock


def stages(model, mean, std):
    import torch
    from ltx_video.models.autoencoders.causal_video_autoencoder import unpatchify

    class Input(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv = model.conv_in
            self.register_buffer('mean', mean.view(1, 128, 1, 1, 1))
            self.register_buffer('std', std.view(1, 128, 1, 1, 1))

        def forward(self, latent, noise, noise_scale):
            # Pipeline order matters: blend in normalized latent space FIRST.
            mixed = latent * (1 - noise_scale.reshape(1, 1, 1, 1, 1)) + noise * noise_scale.reshape(1, 1, 1, 1, 1)
            return self.conv(mixed * self.std + self.mean, causal=False)

    class Up(torch.nn.Module):
        def __init__(self, index):
            super().__init__()
            self.block = model.up_blocks[index]
            self.conditioned = index % 2 == 0
            if self.conditioned:
                self.multiplier = model.timestep_scale_multiplier

        def forward(self, sample, timestep=None):
            if self.conditioned:
                return self.block(sample, causal=False, timestep=timestep * self.multiplier)
            return self.block(sample, causal=False)

    class Tail(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.norm = model.conv_norm_out
            self.embed = model.last_time_embedder
            self.table = model.last_scale_shift_table
            self.multiplier = model.timestep_scale_multiplier
            self.act = model.conv_act
            self.conv = model.conv_out

        def forward(self, sample, timestep):
            sample = self.norm(sample)
            embedded = self.embed(timestep=(timestep * self.multiplier).flatten(), resolution=None,
                                  aspect_ratio=None, batch_size=sample.shape[0], hidden_dtype=sample.dtype)
            ada = self.table[None, ..., None, None, None] + embedded.reshape(sample.shape[0], 2, -1, 1, 1, 1)
            shift, scale = ada.unbind(dim=1)
            sample = sample * (1 + scale) + shift
            return unpatchify(self.conv(self.act(sample), causal=False), patch_size_hw=4, patch_size_t=1)

    return [Input().eval()] + [Up(i).eval() for i in range(7)] + [Tail().eval()]


def run_stages(modules, latent, noise, noise_scale, timestep):
    value = latent
    for i, module in enumerate(modules):
        args = (value, noise, noise_scale) if i == 0 else ((value, timestep) if i in (1, 3, 5, 7, 8) else (value,))
        value = module(*args)
        yield i, args, value


def export(directory=OUT, checkpoint=CHECKPOINT):
    before = inputs()
    import torch
    # The helper prepares and validates offline dependencies before model imports.
    model, mean, std, lock = decoder(checkpoint)
    import onnx
    torch.set_num_threads(4)
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / 'ltx098-vae.json'
    if manifest_path.exists() or any(directory.glob('stage-*.onnx*')):
        raise ValueError('Refuse to overwrite an existing exported decoder directory')
    modules = stages(model, mean, std)
    generator = torch.Generator().manual_seed(98309)
    latent = torch.randn((1, 128, 3, 2, 2), generator=generator)
    noise = torch.randn(latent.shape, generator=generator)
    noise_scale = torch.tensor([.025]); timestep = torch.tensor([.05])
    records = []
    with torch.no_grad():
        for i, args, value in run_stages(modules, latent, noise, noise_scale, timestep):
            name = f'stage-{i:02d}.onnx'; path = directory / name
            raw = directory / (name + '.raw')
            names = ['latent', 'noise', 'noise_scale'] if i == 0 else (['sample', 'timestep'] if len(args) == 2 else ['sample'])
            dynamic = {n: {2: n + '_t', 3: n + '_h', 4: n + '_w'} for n, a in zip(names, args) if a.ndim == 5}
            dynamic['output'] = {2: 'out_t', 3: 'out_h', 4: 'out_w'}
            print('Export', name, list(value.shape), flush=True)
            torch.onnx.export(modules[i], args, str(raw), input_names=names, output_names=['output'],
                              dynamic_axes=dynamic, opset_version=17, dynamo=False,
                              do_constant_folding=True, keep_initializers_as_inputs=False)
            graph = onnx.load(str(raw), load_external_data=True)
            if any(node.domain not in ('', 'ai.onnx') for node in graph.graph.node):
                raise ValueError('Decoder graph contains a custom operator')
            onnx.save_model(graph, str(path), save_as_external_data=True, all_tensors_to_one_file=True,
                            location=name + '.data', size_threshold=0, convert_attribute=False)
            del graph; gc.collect(); raw.unlink()
            onnx.checker.check_model(str(path))
            records.append(dict(index=i, file=name, inputs=names, input_shapes=[list(a.shape) for a in args],
                                output_shape=list(value.shape)))
    assets = [dict(file=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(directory.glob('stage-*.onnx*'))]
    current(before)
    record = dict(schema='lma.ltx098-vae/1', source=lock['checkpoint'], precision='float32', stages=records,
                  assets=assets, decoder_tensors=132, decoder_parameters=552814641, temporal_scale=8,
                  spatial_scale=32, output_channels=3, decode_timestep=.05, decode_noise_scale=.025,
                  tone_map_compression_ratio=0., complete_video_pipeline=False, engine_registered=False,
                  packaged_in_apk=False, physical_android=False, input_fingerprint=before)
    manifest_path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(exported_stages=len(records), external_assets=len(assets),
                          bytes=sum(x['bytes'] for x in assets))), flush=True)


def references(directory, checkpoint=CHECKPOINT):
    before = inputs()
    model, mean, std, lock = decoder(checkpoint)
    import numpy as np
    import torch
    torch.set_num_threads(4)
    directory.mkdir(parents=True, exist_ok=True)
    cases = []; files = {}
    observed = []
    handles = [module.register_forward_hook(lambda _m, _a, out: observed.append(out.detach().clone()))
               for module in [model.conv_in, *model.up_blocks]]
    try:
        with torch.no_grad():
            for index, (shape, time_value, scale) in enumerate([
                    ((1, 128, 3, 2, 2), .05, .025), ((1, 128, 1, 1, 1), .05, 0.),
                    ((1, 128, 3, 1, 2), .1, .05), ((1, 128, 2, 2, 1), 0., .025)]):
                gen = torch.Generator().manual_seed(98320 + index)
                latent = torch.randn(shape, generator=gen); noise = torch.randn(shape, generator=gen)
                timestep = torch.tensor([time_value]); observed.clear()
                mixed = latent * (1 - scale) + noise * scale
                unnormalized = mixed * std.view(1, 128, 1, 1, 1) + mean.view(1, 128, 1, 1, 1)
                start = time.perf_counter()
                # Original upstream forward, NOT the export wrappers.
                result = model(unnormalized, target_shape=(1, 3, shape[2] * 8, shape[3] * 32, shape[4] * 32), timestep=timestep)
                assert list(result.shape) == [1, 3, (shape[2] - 1) * 8 + 1, shape[3] * 32, shape[4] * 32]
                values = dict(latent=latent, noise=noise, output=result,
                              **{f'stage-{i:02d}': v for i, v in enumerate(observed)})
                paths = {}
                for kind, tensor in values.items():
                    name = f'case-{index}-{kind}.f32'; path = directory / name
                    tensor.detach().cpu().numpy().astype('<f4').tofile(path)
                    files[name] = dict(bytes=path.stat().st_size, sha256=sha(path), shape=list(tensor.shape))
                    paths[kind] = name
                cases.append(dict(name=f'case-{index}', latent_shape=list(shape), timestep=time_value,
                                  noise_scale=scale, files=paths, output_shape=list(result.shape),
                                  seconds=time.perf_counter() - start))
                print('Original trained VAE', cases[-1]['name'], cases[-1]['output_shape'], flush=True)
    finally:
        for handle in handles: handle.remove()
    current(before)
    record = dict(schema='lma.ltx098-vae-oracle/1', checkpoint=lock['checkpoint'], cases=cases, files=files,
                  oracle='unmodified Lightricks Decoder.forward; checkpoint BF16 cast to F32',
                  trained=True, complete_video_pipeline=False, physical_android=False, input_fingerprint=before)
    (directory / 'references.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['export', 'references'])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.operation == 'export': export(args.output or OUT)
    else: references(args.output or ROOT / 'build/ltx098-vae-tests/references')
