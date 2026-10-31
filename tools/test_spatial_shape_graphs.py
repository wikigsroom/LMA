"""Small random publisher-model parity. Does not fetch or run trained weights."""
import copy
import json
import os
from pathlib import Path
import sys
from evidence import fingerprint,current

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build/shape-reference-python'))
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')


def main():
    import numpy as np
    import onnxruntime as ort
    import torch
    from shape_graphs import export_graph
    from spatial_shape_graphs import modules, portable, HunyuanFlow, UltraFlow
    out = ROOT / 'build/spatial-shape-tests'
    out.mkdir(exist_ok=True)
    torch.set_num_threads(2)
    torch.manual_seed(901)
    inputs = fingerprint('tools/test_spatial_shape_graphs.py','tools/spatial_shape_graphs.py','tools/spatial_reference.py','third_party/spatial-shape-source-lock.json')
    checks = []
    for target in ('D06', 'D07'):
        fc = dict(input_size=16, in_channels=4, hidden_size=16, context_dim=8, depth=3, num_heads=2,
                  qk_norm=True, qkv_bias=False, num_moe_layers=1, num_experts=3, moe_top_k=2)
        if target == 'D07':
            fc.update(use_attention_pooling=False, use_pos_emb=False)
        vc = dict(num_latents=16, embed_dim=4, width=16, heads=2, num_decoder_layers=2, qkv_bias=False,
                  qk_norm=True, num_freqs=2, scale_factor=1.0039506158752403)
        model, cache, query, sched = modules(target, fc, vc)
        original = copy.deepcopy(model)
        portable(model, target)
        wrapper = UltraFlow(model) if target == 'D06' else HunyuanFlow(model)
        folder = out / target
        folder.mkdir(exist_ok=True)
        x, t, cond, indices = torch.randn(1, 7, 4), torch.tensor([.4]), torch.randn(1, 5, 8), torch.randint(0, 128, (1, 7, 3)).float()
        args = (x, t, cond, indices) if target == 'D06' else (x, t, cond)
        names = ['latents', 'timestep', 'image_embeddings'] + (['voxel_indices'] if target == 'D06' else [])
        dynamic = {'latents': {1: 'tokens'}, 'velocity': {1: 'tokens'}, 'image_embeddings': {1: 'image_tokens'}}
        if target == 'D06':
            dynamic['voxel_indices'] = {1: 'tokens'}
        export_graph(wrapper, args, folder / 'flow.onnx', names, 'velocity', dynamic)
        export_graph(cache, (x,), folder / 'cache.onnx', ['latents'], 'cache', {'latents': {1: 'tokens'}, 'cache': {1: 'tokens'}})
        export_graph(query, (torch.randn(1, 7, 16), torch.randn(1, 11, 3)), folder / 'query.onnx', ['cache', 'points'], 'sdf',
                     {'cache': {1: 'tokens'}, 'points': {1: 'queries'}, 'sdf': {1: 'queries'}})
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        sessions = {name: ort.InferenceSession(str(folder / (name + '.onnx')), options, providers=['CPUExecutionProvider']) for name in ('flow', 'cache', 'query')}
        def compare(label, expected, actual):
            expected = expected.detach().numpy()
            error = float(np.max(np.abs(expected - actual)))
            assert np.allclose(expected, actual, atol=3e-5, rtol=3e-4), (label, error)
            checks.append(dict(target=target, case=label, maxAbsoluteError=error))
        with torch.inference_mode():
            for tokens in (3, 7, 19):
                for length, unconditional in ((3, False), (5, False), (9, False), (5, True)):
                    x = torch.randn(1, tokens, 4)
                    indices = torch.randint(0, 128, (1, tokens, 3)).float()
                    c = torch.zeros(1, length, 8) if unconditional else torch.randn(1, length, 8)
                    original_args = {'voxel_cond': indices} if target == 'D06' else {}
                    expected = original(x, t, {'main': c}, **original_args)
                    data = dict(latents=x.numpy(), timestep=t.numpy(), image_embeddings=c.numpy())
                    if target == 'D06':
                        data['voxel_indices'] = indices.numpy()
                    compare('flow_' + str(tokens) + '_' + str(length) + '_' + str(unconditional), expected, sessions['flow'].run(None, data)[0])
                value = cache(x)
                got = sessions['cache'].run(None, {'latents': x.numpy()})[0]
                compare('cache_' + str(tokens), value, got)
                for count in (1, 13, 53):
                    points = torch.randn(1, count, 3)
                    compare('query_' + str(tokens) + '_' + str(count), query(value, points), sessions['query'].run(None, dict(cache=got, points=points.numpy()))[0])
            for steps in (1, 2, 7):
                for shift in (1., 2.5):
                    s = sched.FlowMatchEulerDiscreteScheduler(shift=shift)
                    sigmas = np.linspace(0, 1, steps)
                    s.set_timesteps(steps, sigmas=sigmas)
                    state = torch.randn(3)
                    native = state.numpy().copy()
                    for i, time in enumerate(s.timesteps):
                        v = torch.tensor([.3, -.7, 1.2])
                        state = s.step(v, time, state, return_dict=False)[0]
                        a = 0 if steps == 1 else i / (steps - 1)
                        b = 1 if i + 1 == steps else (i + 1) / (steps - 1)
                        f = lambda z: shift * z / (1 + (shift - 1) * z)
                        native += np.float32(f(b) - f(a)) * v.numpy()
                    compare('schedule_' + str(steps) + '_' + str(shift), state, native)
    current(inputs)
    (out / 'graph-results.json').write_text(json.dumps(dict(passed=True, count=len(checks), checks=checks, trainedModels=0, input_fingerprint=inputs), indent=2) + '\n', 'utf-8')
    print(json.dumps(dict(passed=len(checks), trainedModels=0)))


if __name__ == '__main__':
    main()
