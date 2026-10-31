"""Offline UltraTex flow component conversion, NOT a complete Android model.

Explicit local config/base/optional LoRA -> matched CPU ONNX with source and
hash receipt. Does not download, encode text, generate materials or register a
ready-to-run app bundle. Supply all later runtime stages on the same phone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--family', choices=['flux1', 'flux2'], required=True)
    p.add_argument('--config', type=Path, required=True, help='Exact constructor parameters as JSON')
    p.add_argument('--weights', type=Path, required=True, help='Explicit local base .safetensors')
    p.add_argument('--lora', type=Path)
    p.add_argument('--lora-scale', type=float, default=1.)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--float-attention', action='store_true', help='Use FP32 attention; default preserves BF16 attention casts')
    a = p.parse_args(); out = a.output.resolve()
    assert not out.exists(), 'Choose a new output directory'
    assert a.config.is_file() and not a.config.is_symlink() and a.config.stat().st_size <= 65536
    cfg = json.loads(a.config.read_text('utf-8')); assert isinstance(cfg, dict)
    for file in [a.weights] + ([a.lora] if a.lora else []):
        assert file.is_file() and not file.is_symlink() and file.suffix == '.safetensors'
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1')
    import torch
    from safetensors.torch import load_file
    from ultratex_flows import architecture, export, merge_lora
    torch.set_num_threads(4)
    model, _ = architecture(a.family, cfg, bfloat16=not a.float_attention)
    state = load_file(str(a.weights), device='cpu')
    assert all(x.is_floating_point() and torch.isfinite(x).all() for x in state.values()), 'Nonfinite/incompatible base weights'
    model.load_state_dict(state, strict=True); del state
    merged = merge_lora(model, a.family, load_file(str(a.lora), device='cpu'), a.lora_scale) if a.lora else 0
    out.mkdir(parents=True)
    names = export(model, a.family, cfg, out/'flow.onnx')
    files = []
    for file in sorted(out.iterdir()):
        assert file.is_file() and not file.is_symlink()
        with file.open('rb') as f: sha = hashlib.file_digest(f, 'sha256').hexdigest()
        files.append(dict(file=file.name, bytes=file.stat().st_size, sha256=sha))
    lock = json.loads((ROOT/'third_party/ultratex-flow-source-lock.json').read_text('utf-8'))
    inputs = []
    for role, file in [('config', a.config), ('weights', a.weights)] + ([('lora', a.lora)] if a.lora else []):
        with file.open('rb') as f: sha = hashlib.file_digest(f, 'sha256').hexdigest()
        inputs.append(dict(role=role, bytes=file.stat().st_size, sha256=sha))
    receipt = dict(schema='lma.ultratex-flow-export/1', family=a.family, parameters=cfg,
        source={k:lock[k] for k in ('repository','revision')}, inputs=inputs, components=files,
        input_names=names, output_names=['velocity','target_indices'], merged_lora_layers=merged,
        lora_scale=a.lora_scale, opset=17, dtype='float32', attention_cast='float32' if a.float_attention else 'bfloat16',
        position_ids=dict(dtype='int64' if a.family=='flux1' else 'float32',minimum=0,maximum=8191,
            rotary='publisher_float64_to_float32_lookup' if a.family=='flux1' else 'publisher_float32'),
        input_contract=dict(batch_minimum=1,batch_maximum=2,target_foreground_minimum=1,
            masks='int64 0 or 1 vectors, shared across batch',finite_float_inputs=True,
            equal_query_key_value_lengths=True,attention_work_limit=32000000000),
        complete_adapter=False, app_recipe_registered=False, network=False,
        complete_models_downloaded=0, complete_model_generation_tested=False, physical_device_tests=0,
        missing_stages=['local text/tokenization','matched VAE','geometry conditions','Euler sampling/background restoration','PBR bake','app bundle/recipe'])
    (out/'export-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', 'utf-8')
    print(json.dumps(dict(family=a.family, flow_exported=True, complete_adapter=False, merged_lora_layers=merged)))


if __name__ == '__main__': main()
