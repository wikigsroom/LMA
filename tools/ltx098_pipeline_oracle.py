"""Offline original-model oracle for real-prompt old-LTX single-scale runs.

Shared explicit noise is an input, not a claim of PyTorch seed parity. Original
Transformers and publisher model forward methods execute on the native host CPU.
No native inference executable is called, and no assets are downloaded.
"""
import argparse
import gc
import json
import time
from pathlib import Path
from evidence import current, fingerprint
from ltx098_pipeline import inputs as pipeline_inputs, T5, TOKENIZER
from ltx098_vae import decoder, sha, CHECKPOINT
from ltx098_assets import Checkpoint, PREFIX, validate_transformer
from ltx098_text_oracle import dependencies, paged_reference
from ltx098_sampling_oracle import publisher_geometry, trajectory

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**pipeline_inputs(), **fingerprint('tools/ltx098_pipeline_oracle.py',
            'tools/ltx098_text_oracle.py', 'tools/ltx098_sampling_oracle.py')}


def generate(directories, output):
    before = inputs()
    output = output.resolve()
    if not output.is_relative_to((ROOT / 'build').resolve()): raise ValueError('Oracle output must stay below project build/')
    output.mkdir(parents=True, exist_ok=False)
    cases = []
    for directory in directories:
        directory = directory.resolve()
        if not directory.is_relative_to((ROOT / 'build').resolve()): raise ValueError('Unexpected pipeline input location')
        record = json.loads((directory / 'pipeline.json').read_text(encoding='utf-8'))
        current(record['input_fingerprint'])
        if record['input_fingerprint'] != pipeline_inputs() or not record['full_trained_host_text_to_frames'] or record['physical_android']:
            raise ValueError('Require current real trained host pipeline run')
        for name, item in record['files'].items():
            path = directory / name
            if path.parent != directory or path.stat().st_size != item['bytes'] or sha(path) != item['sha256']:
                raise ValueError('Changed native pipeline result: ' + name)
        case_dir = output / ('case-' + str(len(cases))); case_dir.mkdir()
        cases.append(dict(directory=directory, output=case_dir, record=record))
    lock = json.loads((ROOT / 'third_party/ltx098-text-source-lock.json').read_text(encoding='utf-8'))
    if T5.stat().st_size != lock['model']['bytes'] or sha(T5) != lock['model']['sha256']:
        raise ValueError('Changed community trained T5 quantization')
    for asset in lock['oracle_assets']:
        path = TOKENIZER.parent / asset['file']
        if path.parent != TOKENIZER.parent or path.stat().st_size != asset['bytes'] or sha(path) != asset['sha256']:
            raise ValueError('Changed original T5 reference asset: ' + asset['file'])
    print('Import pinned independent offline T5 reference', flush=True)
    np, torch, gguf, transformers, versions = dependencies(lock)
    # Verify original publisher and dependency sources, without downloads.
    from ltx098_vae import environment
    environment(); torch.set_num_threads(4)
    tokenizer = transformers.T5Tokenizer.from_pretrained(str(TOKENIZER.parent), local_files_only=True, legacy=True)
    reader = gguf.GGUFReader(T5)
    config = transformers.T5Config.from_pretrained(str(TOKENIZER.parent), local_files_only=True)
    model, used, tensors, hooks = paged_reference(np, torch, gguf, transformers, reader, config)
    start = time.perf_counter()
    for i, case in enumerate(cases):
        print('Original T5 prompt', i, flush=True)
        tokens = tokenizer(case['record']['request']['prompt'].strip(), max_length=256, truncation=True, return_tensors='pt')
        with torch.inference_mode(): caption = model(**tokens).last_hidden_state.detach().numpy().copy()
        ids = tokens['input_ids'][0].tolist()
        if not tokens['attention_mask'].bool().all() or list(caption.shape) != [1, len(ids), 4096]: raise ValueError('Unexpected original T5 compact shape')
        caption.astype('<f4').tofile(case['output'] / 'caption.f32')
        case['tokens'] = ids
    if used != set(tensors): raise ValueError('Incomplete trained T5 parameter coverage')
    text_seconds = time.perf_counter() - start
    for hook in hooks: hook.remove()
    del model, tensors, reader, hooks; gc.collect()
    print('Verify original trained old-LTX checkpoint', flush=True)
    trained = json.loads((ROOT / 'third_party/ltx098-trained-assets.json').read_text(encoding='utf-8'))['models'][0]
    if CHECKPOINT.stat().st_size != trained['bytes'] or sha(CHECKPOINT) != trained['sha256']:
        raise ValueError('Different original LTX checkpoint')
    checkpoint = Checkpoint(CHECKPOINT); config, items = validate_transformer(checkpoint)
    from ltx_video.models.transformers.transformer3d import Transformer3DModel
    from ltx_video.models.transformers.symmetric_patchifier import SymmetricPatchifier
    with torch.device('meta'): model = Transformer3DModel(**{k: v for k, v in config.items() if not k.startswith('_')}).eval()
    used = set(); stats = dict(loads=0, max_scheduled_parameter_bytes=0); hooks = []
    def before_module(prefix):
        def load(module, args):
            state = {}
            for name in module.state_dict():
                value = checkpoint.array(PREFIX + prefix + name)
                # Match the explicitly pinned converted dense F16 weights, while
                # retaining all original equations and the other F32 parameters.
                if value.ndim == 2 and name.endswith('.weight'): value = value.astype('<f2').astype('<f4')
                state[name] = torch.from_numpy(value)
            used.update(prefix + name for name in state)
            stats['loads'] += 1
            stats['max_scheduled_parameter_bytes'] = max(stats['max_scheduled_parameter_bytes'], sum(x.numel() * 4 for x in state.values()))
            module.load_state_dict(state, strict=True, assign=True)
        return load
    def after_module(module, args, result): module.to_empty(device='meta')
    for name in ['patchify_proj', 'adaln_single', 'caption_projection', 'proj_out'] + ['transformer_blocks.' + str(i) for i in range(28)]:
        module = model.get_submodule(name)
        hooks.extend([module.register_forward_pre_hook(before_module(name + '.')),
                      module.register_forward_hook(after_module, always_call=True)])
    model.scale_shift_table = torch.nn.Parameter(torch.from_numpy(checkpoint.array(PREFIX + 'scale_shift_table')), requires_grad=False)
    used.add('scale_shift_table')
    for i, case in enumerate(cases):
        print('Original eight-step DiT trajectory', i, flush=True)
        shape = case['record']['shape']; n = ((shape['frames'] - 1) // 8 + 1) * (shape['height'] // 32) * (shape['width'] // 32)
        latent = torch.from_numpy(np.fromfile(case['directory'] / 'initial-tokens.f32', dtype='<f4').reshape(1, n, 128))
        context = torch.from_numpy(np.fromfile(case['output'] / 'caption.f32', dtype='<f4').reshape(1, len(case['tokens']), 4096))
        _, coords, _ = publisher_geometry(torch, **shape, channels=128)
        mask = torch.ones((1, len(case['tokens'])), dtype=torch.int64)
        case['sampling_steps'] = trajectory(torch, model, latent, context, coords, mask, case['output'], 'sampling')
        final = torch.from_numpy(np.fromfile(case['output'] / 'sampling-step-7.f32', dtype='<f4').reshape(1, n, 128))
        restored = SymmetricPatchifier(1).unpatchify(final, shape['height'] // 32, shape['width'] // 32, 128)
        restored.numpy().astype('<f4').tofile(case['output'] / 'denoised-ncthw.f32')
    if used != set(items): raise ValueError('Incomplete original trained DiT parameter coverage')
    for hook in hooks: hook.remove()
    del model, hooks, checkpoint; gc.collect()
    print('Original trained decoder forward, no export wrappers', flush=True)
    model, mean, std, _ = decoder()
    from diffusers.image_processor import VaeImageProcessor
    for i, case in enumerate(cases):
        shape = case['record']['shape']; grid = (1, 128, (shape['frames'] - 1) // 8 + 1, shape['height'] // 32, shape['width'] // 32)
        latent = torch.from_numpy(np.fromfile(case['output'] / 'denoised-ncthw.f32', dtype='<f4').reshape(grid))
        noise = torch.from_numpy(np.fromfile(case['directory'] / 'decode-noise.f32', dtype='<f4').reshape(grid))
        start = time.perf_counter()
        with torch.inference_mode():
            mixed = latent * (1 - .025) + noise * .025
            denormalized = mixed * std.view(1, 128, 1, 1, 1) + mean.view(1, 128, 1, 1, 1)
            decoded = model(denormalized, target_shape=(1, 3, grid[2] * 8, shape['height'], shape['width']), timestep=torch.tensor([.05]))
            if list(decoded.shape) != [1, 3, shape['frames'], shape['height'], shape['width']]: raise ValueError('Original decoded geometry differs')
            decoded.numpy().astype('<f4').tofile(case['output'] / 'decoded-ncthw.f32')
            rgb = (VaeImageProcessor.denormalize(decoded)[0].permute(1, 2, 3, 0).numpy() * 255).astype(np.uint8)
            (case['output'] / 'rgb.bin').write_bytes(rgb.tobytes())
        case['decoder_seconds'] = time.perf_counter() - start
        print('Original decoder finished', i, case['decoder_seconds'], flush=True)
    del model; gc.collect(); current(before)
    records = []
    for case in cases:
        files = {path.name: dict(bytes=path.stat().st_size, sha256=sha(path)) for path in sorted(case['output'].iterdir()) if path.is_file()}
        records.append(dict(name=case['output'].name, native_pipeline=case['directory'].relative_to(ROOT).as_posix(),
                            native_record_sha256=sha(case['directory'] / 'pipeline.json'), tokens=case['tokens'],
                            shape=case['record']['shape'], sampling_steps=case['sampling_steps'],
                            decoder_seconds=case['decoder_seconds'], files=files))
    result = dict(schema='lma.ltx098-pipeline-oracle/1', cases=records, versions=versions,
                  reference='Original Transformers T5EncoderModel plus original publisher Transformer3DModel, RectifiedFlowScheduler and Decoder forwards',
                  trained_t5_tensors=219, trained_dit_tensors=715, trained_decoder_tensors=132,
                  t5_reference_seconds=text_seconds, dit_parameter_paging=stats,
                  quantized_t5_dequantized=True, converted_dit_f16_equivalent=True,
                  original_unquantized_t5_compared=False, explicit_noise_shared_as_inputs=True,
                  matches_pytorch_seed=False, official_multiscale_default_reproduced=False,
                  official_pixart_weight_identity_compared=False, physical_android=False,
                  video_quality_accepted=False, native_inference_called=False, input_fingerprint=before)
    (output / 'references.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(cases=len(records), physical_android=False, native_inference_called=False)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pipeline', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); generate(args.pipeline, args.output)
