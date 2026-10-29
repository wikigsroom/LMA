"""Separate local T5 operator roundoff from propagated intermediate differences.

Only captured real trained intermediates are accepted. Torch operators consume
the exact native input values; none of these diagnostics changes either model
forward or the frozen full-chain acceptance thresholds.
"""
import argparse
import json
import time
from pathlib import Path

from diagnose_ltx098_text import inputs as diagnosis_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import DIRECTORY, assets, sha, sources
from ltx098_text_oracle import dependencies

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**diagnosis_inputs(), **fingerprint('tools/analyze_ltx098_text.py')}


def run(directory):
    before = inputs(); directory = directory.resolve()
    if not directory.is_relative_to(ROOT / 'build'):
        raise ValueError('Diagnostic capture must stay below build/')
    record = json.loads((directory / 'results.json').read_text(encoding='utf-8'))
    current(record['input_fingerprint'])
    if record['input_fingerprint'] != diagnosis_inputs() or not record['baseline_native_caption_bitwise_identical']:
        raise ValueError('Require current, bitwise-preserving trained intermediate capture')
    target = directory / 'operators.json'
    if target.exists(): raise FileExistsError('Preserve existing operator diagnostic')
    lock = sources(); assets(oracle=True)
    np, torch, gguf, transformers, versions = dependencies(lock)
    from transformers.activations import ACT2FN
    from transformers.models.t5.modeling_t5 import T5Attention
    config = transformers.T5Config.from_pretrained(str(DIRECTORY / 'oracle'), local_files_only=True)
    activation = ACT2FN[config.dense_act_fn]
    reader = gguf.GGUFReader(DIRECTORY / 'originals' / lock['model']['file'])
    tensors = {tensor.name: tensor for tensor in reader.tensors}
    shapes = {item['name']: item['shape'] for item in record['metrics']}
    identities = {item['name']: item for item in record['metrics']}
    count = len(record['tokens']); metrics = []
    def load(name):
        path = directory / 'native' / (name + '.f32')
        if sha(path) != identities[name]['native_sha256']:
            raise ValueError('Changed native intermediate: ' + name)
        return torch.from_numpy(np.fromfile(path, dtype='<f4').reshape(shapes[name]))
    def weight(name):
        tensor = tensors[name]
        return torch.from_numpy(gguf.quants.dequantize(tensor.data, tensor.tensor_type).astype(np.float32, copy=True))
    def compare(name, candidate, observed):
        left = candidate.detach().numpy().astype(np.float64).ravel()
        right = observed.detach().numpy().astype(np.float64).ravel()
        if left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
            raise ValueError('Invalid local operator comparison: ' + name)
        delta = left - right
        metrics.append(dict(name=name, max_abs=float(abs(delta).max()),
                            relative_rmse=float(np.linalg.norm(delta) / max(np.linalg.norm(right), 1e-12)),
                            bitwise_identical=bool(np.array_equal(left, right))))
    relative = torch.arange(count)[None, :] - torch.arange(count)[:, None]
    buckets = T5Attention._relative_position_bucket(relative, bidirectional=True, num_buckets=32, max_distance=128)
    position_bias = weight('enc.blk.0.attn_rel_b.weight')[buckets].permute(2, 0, 1).unsqueeze(0)
    start = time.perf_counter()
    with torch.inference_mode():
        for layer in range(24):
            prefix = 'block-' + str(layer) + '-'; tensor_prefix = 'enc.blk.' + str(layer) + '.'
            for kind, source_name, weight_name in [
                ('attn', 'embedding' if layer == 0 else 'block-' + str(layer - 1) + '-residual', 'attn_norm.weight'),
                ('ffn', prefix + 'attn-residual', 'ffn_norm.weight')]:
                source = load(source_name)
                original = weight(tensor_prefix + weight_name) * (source * torch.rsqrt(source.pow(2).mean(-1, keepdim=True) + 1e-6))
                compare(prefix + kind + '-norm-same-input', original, load(prefix + kind + '-norm'))
            gate = load(prefix + 'gate'); up = load(prefix + 'up')
            compare(prefix + 'geglu-same-input', activation(gate) * up, load(prefix + 'geglu'))
            q, k, v = [load(prefix + name).reshape(1, count, 64, 64).transpose(1, 2) for name in ('q', 'k', 'v')]
            observed = load(prefix + 'mixed')
            fused = torch.nn.functional.scaled_dot_product_attention(q, k, v, attn_mask=position_bias, dropout_p=0, is_causal=False, scale=1.)
            compare(prefix + 'sdpa-same-input', fused.transpose(1, 2).reshape(1, count, 4096), observed)
            eager = (q @ k.transpose(2, 3) + position_bias).softmax(-1) @ v
            compare(prefix + 'eager-attention-same-input', eager.transpose(1, 2).reshape(1, count, 4096), observed)
    current(before)
    report = dict(schema='lma.ltx098-text-operators/1', metrics=metrics, versions=versions,
                  seconds=time.perf_counter() - start, dense_act_fn=config.dense_act_fn,
                  activation_class=type(activation).__name__, native_capture_sha256=sha(directory / 'results.json'),
                  original_attention_implementation=record['original_attention_implementation'],
                  matched_native_input_comparisons=True, full_model_rerun=False,
                  original_forward_modified=False, acceptance_gates_changed=False,
                  physical_android=False, apk_changed=False, input_fingerprint=before)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    worst = {kind: max((item['max_abs'] for item in metrics if item['name'].endswith(kind)))
             for kind in ('attn-norm-same-input', 'ffn-norm-same-input', 'geglu-same-input', 'sdpa-same-input', 'eager-attention-same-input')}
    print(json.dumps(dict(output=target.relative_to(ROOT).as_posix(), comparisons=len(metrics), worst=worst)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    run(parser.parse_args().directory)
