"""Pinned UltraTex flow export building blocks, without upstream package import.

The two actual publisher architectures remain distinct. Text encoders, VAE,
rendering and material baking are not provided by this component. No recipe or
download candidate is registered until that whole on-phone path exists.
"""
import ast
from contextlib import nullcontext
import dataclasses
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import types

import torch
from torch import Tensor, nn
from einops import rearrange
from ultratex_attention import Attention

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'third_party/ultratex-flow-source-lock.json'


def source(relative):
    lock = json.loads(LOCK.read_text('utf-8'))
    assert lock['repository'] == 'yiboz2001/UltraTex'
    assert lock['revision'] == 'a726678f3f3631fe2c5e3d1fb4597114784c7a8b'
    item = next(x for x in lock['files'] if x['path'] == relative)
    path = ROOT / lock['directory'] / relative
    data = path.read_bytes()
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'], relative
    return path, data.decode('utf-8-sig')


def definitions(relative, injections=None):
    path, text = source(relative)
    # Only definitions execute; imports, CUDA/SLA constructors, training,
    # download helpers and caption-cache directories never run.
    class Clean(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if (relative == 'ultratex/backbones/flux1/math.py'
                    and ast.unparse(node.func) == 'torch.einsum'
                    and len(node.args) == 3 and ast.unparse(node.args[1]) == 'pos'
                    and ast.unparse(node.args[2]) == 'omega'):
                # Torch promotes this outer product to the float64 frequency
                # dtype; ONNX Einsum requires explicit matching input types.
                node.args[1] = ast.Call(ast.Attribute(ast.Name('pos', ast.Load()), 'to', ast.Load()),
                    [ast.Name('omega', ast.Load())], [])
            return node
        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'print':
                return None
            return self.generic_visit(node)
    tree = ast.parse(text, str(path))
    body = [Clean().visit(n) for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
    module = types.ModuleType('lma_ultratex_' + relative.replace('/', '_').replace('.', '_'))
    module.__file__ = str(path)
    module.__dict__.update(torch=torch, Tensor=Tensor, nn=nn, F=nn.functional, math=math,
        rearrange=rearrange, dataclass=dataclasses.dataclass, field=dataclasses.field,
        nvtx=lambda *a, **kw: nullcontext())
    module.__dict__.update(injections or {})
    sys.modules[module.__name__] = module
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(path), 'exec'), module.__dict__)
    return module


def architecture(family, parameters, *, query_block=128, key_block=64, ratio=.2, bfloat16=True):
    assert family in ('flux1', 'flux2')
    assert isinstance(parameters, dict)
    if family == 'flux1':
        assert parameters.get('guidance_embed') is True, 'This source export supports the guidance-distilled Flux1 dev path'
    attention = Attention(query_block, key_block, ratio, bfloat16)
    if family == 'flux1':
        math_source = definitions('ultratex/backbones/flux1/math.py', {'sparse_attn': attention})
        layers = definitions('ultratex/backbones/flux1/modules/layers.py',
            {name: getattr(math_source, name) for name in ('attention', 'attention_masked', 'rope')})
        module = definitions('ultratex/backbones/flux1/model.py',
            {name: getattr(layers, name) for name in ('DoubleStreamBlock', 'EmbedND', 'LastLayer', 'MLPEmbedder', 'SingleStreamBlock', 'timestep_embedding')})
        params = module.FluxParams(**parameters)
        model = module.Flux(params)
    else:
        module = definitions('ultratex/backbones/flux2/model.py',
            {'_SPARSE_ATTENTION': attention, '_SPARSE_ATTENTION_CONFIG': {'enabled': True, 'backend': 'lma_cpu'}})
        params = module.Flux2Params(**parameters)
        model = module.Flux2(params)
    model.float().eval().requires_grad_(False)
    return model, module


class Flux1Flow(nn.Module):
    """Publisher forward, including mask compaction and original RoPE IDs."""
    names = ['latents', 'latent_ids', 'normals', 'normal_ids', 'reference', 'reference_ids',
             'text', 'text_ids', 'pooled_text', 'timestep', 'guidance', 'target_mask', 'normal_mask']

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, latents, latent_ids, normals, normal_ids, reference, reference_ids,
                text, text_ids, pooled_text, timestep, guidance, target_mask, normal_mask):
        result = self.model(img=latents, img_ids=latent_ids, txt=text, txt_ids=text_ids,
            timesteps=timestep, y=pooled_text, guidance=guidance,
            ref_img=(normals, reference), ref_img_ids=(normal_ids, reference_ids),
            masks=[[target_mask, normal_mask]])
        return result, target_mask.nonzero().reshape(-1)


class Flux2Flow(nn.Module):
    """Joint foreground sequence; preserves the publisher's ordinary refs path.

    This deliberately does not invoke the optional causal KV-cache path,
    whose reference attention and modulation differ from UltraTex training.
    """
    names = ['latents', 'latent_ids', 'normals', 'normal_ids', 'reference', 'reference_ids',
             'text', 'text_ids', 'timestep', 'target_mask', 'normal_mask']

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.names = self.names + (['guidance'] if model.use_guidance_embed else [])

    def forward(self, latents, latent_ids, normals, normal_ids, reference, reference_ids,
                text, text_ids, timestep, target_mask, normal_mask, guidance=None):
        ti = target_mask.nonzero().reshape(-1)
        ni = normal_mask.nonzero().reshape(-1)
        values = torch.cat((latents[:, ti], normals[:, ni], reference), dim=1)
        ids = torch.cat((latent_ids[:, ti], normal_ids[:, ni], reference_ids), dim=1)
        prediction = self.model(values, ids, timestep, text, text_ids, guidance)
        return prediction[:, :ti.shape[0]], ti


def example(family, cfg, target=29, normals=29, reference=7, text=11, batch=1):
    assert min(target, normals, reference, text, batch) > 0 and batch <= 2
    c = cfg['in_channels']; axes = 3 if family == 'flux1' else 4
    args = [torch.randn(batch, n, c) if i % 2 == 0 else torch.randint(0, 32, (batch, n, axes))
            for i, n in enumerate((target, target, normals, normals, reference, reference))]
    if family == 'flux2': args = [v if i % 2 == 0 else v.float() for i,v in enumerate(args)]
    args += [torch.randn(batch, text, cfg['context_in_dim']), torch.zeros(batch, text, axes,dtype=torch.int64 if family=='flux1' else torch.float32)]
    if family == 'flux1':
        args += [torch.randn(batch, cfg['vec_in_dim']), torch.full((batch,), .8), torch.full((batch,), 4.)]
    else:
        args += [torch.full((batch,), .8)]
    args += [(torch.arange(target) % 3 != 0).to(torch.int64), (torch.arange(normals) % 4 != 0).to(torch.int64)]
    if family == 'flux2' and cfg.get('use_guidance_embed', True):
        args += [torch.full((batch,), 4.)]
    return tuple(args)


def axes(names):
    result = {n: {0: 'batch', 1: 'target' if n in ('latents', 'latent_ids') else 'normals' if n in ('normals', 'normal_ids') else 'reference' if n in ('reference', 'reference_ids') else 'text'}
              for n in names if n not in ('timestep', 'guidance', 'pooled_text', 'target_mask', 'normal_mask')}
    for n in names:
        if n in ('timestep', 'guidance', 'pooled_text'): result[n] = {0: 'batch'}
    result.update(target_mask={0: 'target'}, normal_mask={0: 'normals'}, velocity={0: 'batch', 1: 'active'}, target_indices={0: 'active'})
    return result


def wrapper(family, model):
    return (Flux1Flow if family == 'flux1' else Flux2Flow)(model).eval()


class IntegerRotary(nn.Module):
    """Exact publisher FP64 -> FP32 tables for declared integer position IDs.

    ORT CPU has no FP64 Cos kernel. The publisher's image offsets and text
    IDs are integers. A fixed 8192-coordinate table avoids changing the trig
    precision or introducing a downloadable native operator. Negative IDs or
    IDs >=8192 are outside this component's declared input contract.
    """
    limit = 8192

    def __init__(self, original):
        super().__init__()
        rope = original.forward.__globals__['rope']
        self.count = len(original.axes_dim)
        for i, dimension in enumerate(original.axes_dim):
            table = rope(torch.arange(self.limit)[None], dimension, original.theta)[0]
            self.register_buffer('axis_'+str(i), table, persistent=False)

    def forward(self, ids):
        return torch.cat([getattr(self,'axis_'+str(i))[ids[...,i]] for i in range(self.count)],dim=-3).unsqueeze(1)


def merge_lora(model, family, state, scale=1.):
    """Merge only the publisher's two declared formats; unknown keys fail.

    Flux1 processors have alpha=None; Flux2 PEFT sets alpha=rank, dropout=0,
    bias=none in the fixed trainer. Thus the supported delta is scale*B@A.
    All deltas validate before any parameter is changed.
    """
    assert family in ('flux1', 'flux2') and isinstance(state, dict) and state
    assert isinstance(scale, (float, int)) and math.isfinite(scale) and -4 <= scale <= 4
    named = dict(model.named_parameters()); groups = {}; updates = []
    for key, value in state.items():
        assert isinstance(value, Tensor) and value.ndim == 2 and value.is_floating_point() and torch.isfinite(value).all(), key
        if family == 'flux1':
            match = re.fullmatch(r'((?:double|single)_blocks\.\d+)\.processor\.(qkv_lora[12]?|proj_lora[12]?)\.(down|up)\.weight', key)
            assert match, 'Unknown Flux1 LoRA key: ' + key
            block, part, side = match.groups(); base = block + '.'
            if block.startswith('double_blocks.'):
                assert part.endswith(('1', '2')), key
                base += ('img_attn.' if part[-1] == '1' else 'txt_attn.') + ('qkv.weight' if part.startswith('qkv') else 'proj.weight')
                prefix_rows = False
            else:
                assert part in ('qkv_lora', 'proj_lora'), key
                base += 'linear1.weight' if part == 'qkv_lora' else 'linear2.weight'
                prefix_rows = part == 'qkv_lora'
            signature = (base, prefix_rows)
            a_side = side == 'down'
        else:
            match = re.fullmatch(r'(?:base_model\.model\.)?((?:double|single)_blocks\.\d+\..+)\.lora_([AB])\.default\.weight', key)
            assert match, 'Unknown Flux2 PEFT key: ' + key
            base, side = match.groups(); base += '.weight'
            assert base.endswith(('.qkv.weight', '.proj.weight', '.linear1.weight', '.linear2.weight')), key
            signature = (base, False); a_side = side == 'A'
        group = groups.setdefault(signature, {})
        assert a_side not in group, 'Duplicate LoRA factor'
        group[a_side] = value.detach().float().cpu()
    for (name, prefix_rows), factors in groups.items():
        assert name in named and len(factors) == 2, 'Missing LoRA base or factor: ' + name
        a, b = factors[True], factors[False]; base = named[name]
        rows = 3 * model.hidden_size if prefix_rows else base.shape[0]
        assert 1 <= a.shape[0] <= 1024 and a.shape[1] == base.shape[1] and b.shape == (rows, a.shape[0]), name
        delta = (b @ a) * scale
        assert torch.isfinite(delta).all() and torch.isfinite(base[:rows].detach().float() + delta).all(), name
        updates.append((base, rows, delta))
    with torch.no_grad():
        for base, rows, delta in updates: base[:rows].add_(delta.to(base))
    return len(updates)


def export(model, family, config, output):
    assert not output.exists(), 'Choose a new flow ONNX output'
    graph = wrapper(family, model)
    original = model.pe_embedder
    try:
        if family == 'flux1': model.pe_embedder = IntegerRotary(original)
        with torch.no_grad():
            # The publisher's floor(topk * key_blocks) needs at least five 64-key
            # blocks at ratio .2, including in a small architecture tracing fixture.
            torch.onnx.export(graph, example(family, config, text=320), str(output), input_names=graph.names,
                output_names=['velocity', 'target_indices'], dynamic_axes=axes(graph.names),
                opset_version=17, custom_opsets={'lma.spatial': 1}, dynamo=False, external_data=True)
    finally: model.pe_embedder = original
    return graph.names
