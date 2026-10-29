"""Observe actual publisher DiT modulation inputs without changing its forward.

This offline developer analysis deliberately uses original reference captions
and latent inputs. It never counts as native model/Android acceptance.
"""
import argparse
import gc
import json
import time
import uuid
from pathlib import Path

from evidence import current, fingerprint
from ltx098_assets import Checkpoint, PREFIX, validate_transformer
from ltx098_pipeline import inputs as pipeline_inputs
from ltx098_sampling_oracle import publisher_geometry, scheduler
from ltx098_vae import CHECKPOINT, environment, sha

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**pipeline_inputs(), **fingerprint('tools/analyze_ltx098_modulation.py',
            'tools/ltx098_pipeline_oracle.py', 'tools/ltx098_sampling_oracle.py')}


def run(reference, case_index, step):
    before = inputs(); reference = reference.resolve()
    if not reference.is_relative_to(ROOT / 'build'): raise ValueError('Reference outside build/')
    baseline = json.loads((ROOT / 'verification/development/ltx098-pipeline.json').read_text(encoding='utf-8'))
    current(baseline['input_fingerprint'])
    oracle = json.loads((reference / 'references.json').read_text(encoding='utf-8'))
    current(oracle['input_fingerprint'])
    if oracle != baseline['original_oracle']: raise ValueError('Different frozen reference')
    case = oracle['cases'][case_index]
    trained = json.loads((ROOT / 'third_party/ltx098-trained-assets.json').read_text(encoding='utf-8'))['models'][0]
    if CHECKPOINT.stat().st_size != trained['bytes'] or sha(CHECKPOINT) != trained['sha256']:
        raise ValueError('Different original trained checkpoint')
    environment()
    import numpy as np
    import torch
    from ltx_video.models.transformers.transformer3d import Transformer3DModel
    torch.set_num_threads(4)
    checkpoint = Checkpoint(CHECKPOINT); config, items = validate_transformer(checkpoint)
    with torch.device('meta'):
        model = Transformer3DModel(**{k: v for k, v in config.items() if not k.startswith('_')}).eval()
    capture = ROOT / 'build/ltx098-modulation-analysis' / ('run-' + str(time.time_ns()) + '-' + uuid.uuid4().hex[:8])
    capture.mkdir(parents=True, exist_ok=False)
    used = set(); held = {}; metrics = []; files = {}; hooks = []
    stats = dict(loads=0, max_scheduled_parameter_bytes=0)

    def load(prefix):
        def callback(module, args):
            state = {}
            for name in module.state_dict():
                value = checkpoint.array(PREFIX + prefix + name)
                if value.ndim == 2 and name.endswith('.weight'): value = value.astype('<f2').astype('<f4')
                state[name] = torch.from_numpy(value)
            used.update(prefix + name for name in state)
            stats['loads'] += 1
            stats['max_scheduled_parameter_bytes'] = max(stats['max_scheduled_parameter_bytes'], sum(v.numel() * 4 for v in state.values()))
            module.load_state_dict(state, strict=True, assign=True)
        return callback

    def unload(module, args, result): module.to_empty(device='meta')

    def record(name, normalized, scale, shift, expected):
        old = (normalized + normalized * scale) + shift
        ordered = normalized * (1 + scale) + shift
        if not all(torch.isfinite(v).all() for v in [normalized, scale, shift, expected, old, ordered]):
            raise ValueError('Non-finite observed stage')
        values = dict(normalized=normalized, scale=scale, shift=shift, expected=expected)
        for label, tensor in values.items():
            path = capture / (name + '-' + label + '.f32')
            tensor.detach().numpy().astype('<f4').tofile(path)
            files[path.name] = dict(bytes=path.stat().st_size, shape=list(tensor.shape), sha256=sha(path))
        metrics.append(dict(stage=name, elements=expected.numel(),
                            reassociated_max_abs=float((old - expected).abs().max()),
                            reassociated_different_elements=int((old != expected).sum()),
                            ordered_max_abs=float((ordered - expected).abs().max()),
                            ordered_bitwise_identical=torch.equal(ordered, expected)))

    for name in ['patchify_proj', 'adaln_single', 'caption_projection', 'proj_out'] + ['transformer_blocks.' + str(i) for i in range(28)]:
        module = model.get_submodule(name)
        hooks.extend([module.register_forward_pre_hook(load(name + '.')), module.register_forward_hook(unload, always_call=True)])
    model.scale_shift_table = torch.nn.Parameter(torch.from_numpy(checkpoint.array(PREFIX + 'scale_shift_table')), requires_grad=False)
    used.add('scale_shift_table')

    def block_pre(name):
        def callback(module, args, kwargs):
            timestep = kwargs['timestep']
            held[name] = module.scale_shift_table[None, None] + timestep.reshape(1, timestep.shape[1], 6, -1)
        return callback

    def norm_post(name):
        def callback(module, args, output): held[name + '-norm'] = output.detach()
        return callback

    def stage_pre(name, slot, block):
        def callback(module, args, kwargs):
            expected = args[0] if args else kwargs['hidden_states']
            mods = held[block]
            record(name, held.pop(name + '-norm'), mods[:, :, slot + 1], mods[:, :, slot], expected)
            if slot == 3: held.pop(block)
        return callback

    for i, block in enumerate(model.transformer_blocks):
        name = 'block-' + str(i)
        hooks.append(block.register_forward_pre_hook(block_pre(name), with_kwargs=True))
        for norm, target, label, slot in [(block.norm1, block.attn1, 'attention', 0), (block.norm2, block.ff, 'feedforward', 3)]:
            stage = name + '-' + label
            hooks.append(norm.register_forward_hook(norm_post(stage)))
            hooks.append(target.register_forward_pre_hook(stage_pre(stage, slot, name), with_kwargs=True))

    def timestep_post(module, args, output): held['embedded'] = output[1].detach().reshape(1, -1, 2048)
    def final_pre(module, args):
        mods = model.scale_shift_table[None, None] + held.pop('embedded')[:, :, None]
        record('output', held.pop('output-norm'), mods[:, :, 1], mods[:, :, 0], args[0])
    hooks.extend([model.adaln_single.register_forward_hook(timestep_post),
                  model.norm_out.register_forward_hook(norm_post('output')),
                  model.proj_out.register_forward_pre_hook(final_pre)])
    source = ROOT / baseline['captured_native_pipelines'][case_index]
    if sha(source / 'pipeline.json') != baseline['captured_native_record_sha256'][case_index]: raise ValueError('Changed baseline capture')
    request = baseline['jobs'][case_index]['request']; shape = case['shape']
    _, coords, _ = publisher_geometry(torch, shape['width'], shape['height'], shape['frames'], request['fps'], 128)
    initial = source / 'initial-tokens.f32' if step == 0 else reference / case['name'] / ('sampling-step-' + str(step - 1) + '.f32')
    expected_input = baseline['jobs'][case_index]['files']['initial-tokens.f32'] if step == 0 else case['files'][initial.name]
    if sha(initial) != expected_input['sha256']: raise ValueError('Changed latent input')
    caption = reference / case['name'] / 'caption.f32'
    if sha(caption) != case['files']['caption.f32']['sha256']: raise ValueError('Changed reference caption')
    n = coords.shape[-1]
    latent = torch.from_numpy(np.fromfile(initial, dtype='<f4').reshape(1, n, 128))
    context = torch.from_numpy(np.fromfile(caption, dtype='<f4').reshape(1, len(case['tokens']), 4096))
    rf = scheduler(); sigma = rf.timesteps[step]
    print('Observe original trained modulation', case_index, step, flush=True)
    start = time.monotonic()
    try:
        with torch.inference_mode():
            velocity = model(latent, coords, context, sigma.reshape(1), encoder_attention_mask=torch.ones(1, len(case['tokens']), dtype=torch.int64)).sample
            sampled = rf.step(velocity, sigma, latent).prev_sample
    finally:
        for hook in hooks: hook.remove()
    seconds = time.monotonic() - start
    if held or used != set(items) or len(metrics) != 57: raise ValueError('Incomplete original trained observation')
    expected = reference / case['name'] / ('sampling-step-' + str(step) + '.f32')
    if sha(expected) != case['files'][expected.name]['sha256']: raise ValueError('Changed frozen trajectory')
    right = np.fromfile(expected, dtype='<f4').reshape(sampled.shape)
    delta = sampled.numpy().astype(np.float64) - right.astype(np.float64)
    comparison = dict(max_abs=float(abs(delta).max()), relative_rmse=float(np.linalg.norm(delta) / np.linalg.norm(right)), bitwise_identical=np.array_equal(sampled.numpy(), right))
    del model; gc.collect(); current(before)
    report = dict(schema='lma.ltx098-modulation-analysis/1', case=case_index, step=step, sigma=float(sigma),
                  metrics=metrics, files=files, trained_tensors=len(used), trained_parameters=1923385472,
                  parameter_paging=stats, original_forward_seconds=seconds, frozen_trajectory_comparison=comparison,
                  original_oracle_sha256=sha(reference / 'references.json'), caption_sha256=sha(caption), latent_input_sha256=sha(initial),
                  source_checkpoint_sha256=trained['sha256'], output_directory=capture.relative_to(ROOT).as_posix(),
                  original_forward_modified=False, reference_conditioned=True, torch_operator_analysis=True,
                  native_replacement_executed=False, full_model_accepted=False, physical_android=False,
                  packaged_in_apk=False, engine_registered=False, acceptance_gates_changed=False, input_fingerprint=before)
    out = ROOT / 'build/ltx098-modulation-analysis'
    (out / ('case-' + str(case_index) + '-step-' + str(step) + '-results.json')).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(stages=len(metrics), reassociated_max=max(m['reassociated_max_abs'] for m in metrics),
                          ordered_bitwise_identical=all(m['ordered_bitwise_identical'] for m in metrics), frozen_trajectory=comparison)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--case', type=int, choices=[0, 1], required=True)
    parser.add_argument('--step', type=int, choices=[0, 7], required=True)
    args = parser.parse_args(); run(args.reference, args.case, args.step)
