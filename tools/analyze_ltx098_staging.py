"""Compare explicit F32 operation staging using preserved trained intermediates.

The grouped-mean simulation and Torch activation-order analysis are local
operator diagnostics. They do not execute a replacement native T5 or count as
full video, Android or quality acceptance.
"""
import argparse
import json
import time
from pathlib import Path

from diagnose_ltx098_text import inputs as diagnosis_inputs
from evidence import current, fingerprint
from fetch_ltx098_text import sha
from ltx098_text_oracle import dependencies

ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {**diagnosis_inputs(), **fingerprint('research/ltx098_text_order', 'research/ltx098_text_f32',
                                              'tools/analyze_ltx098_staging.py')}


def run(directory):
    before = inputs(); directory = directory.resolve()
    if not directory.is_relative_to(ROOT / 'build'): raise ValueError('Capture must stay below build/')
    capture_path = directory / 'results.json'
    record = json.loads(capture_path.read_text(encoding='utf-8')); current(record['input_fingerprint'])
    published = ROOT / 'verification/development/ltx098-text-diagnosis.json'
    if sha(capture_path) != sha(published) or record['input_fingerprint'] != diagnosis_inputs():
        raise ValueError('Different original trained intermediate capture')
    lock = json.loads((ROOT / 'third_party/ltx098-text-source-lock.json').read_text(encoding='utf-8'))
    np, torch, _, _, versions = dependencies(lock)
    torch.set_num_threads(1)
    from transformers.activations import ACT2FN
    activation = ACT2FN['gelu_new']
    identities = {item['name']: item for item in record['metrics']}
    files = {}; metrics = []; start = time.perf_counter()

    def load(name):
        path = directory / 'native' / (name + '.f32'); identity = identities[name]
        if sha(path) != identity['native_sha256']: raise ValueError('Changed native input: ' + name)
        shape = identity['shape']
        if path.stat().st_size != int(np.prod(shape)) * 4: raise ValueError('Invalid captured tensor shape')
        files[name] = dict(shape=shape, bytes=path.stat().st_size, sha256=sha(path))
        return np.fromfile(path, dtype='<f4').reshape(shape)

    with torch.inference_mode():
        for layer in range(24):
            prefix = 'block-' + str(layer) + '-'
            for kind, name in [('attn', 'embedding' if layer == 0 else 'block-' + str(layer - 1) + '-residual'),
                               ('ffn', prefix + 'attn-residual')]:
                x = load(name).reshape(-1, 4096)
                squares = (x * x).reshape(-1, 8, 16, 32)
                streams = np.zeros((x.shape[0], 32), dtype=np.float32)
                for group in range(8):
                    local = np.zeros_like(streams)
                    for index in range(16): local += squares[:, group, index]
                    streams += local
                streams = streams.reshape(-1, 4, 8)
                lanes = streams[:, 0].copy()
                for index in range(1, 4): lanes += streams[:, index]
                total = np.zeros(x.shape[0], dtype=np.float32)
                for index in range(8): total += lanes[:, index]
                candidate = total * np.float32(1 / 4096)
                original = torch.from_numpy(x).pow(2).mean(-1).numpy()
                metrics.append(dict(layer=layer, kind=kind + '_mean', input=name, elements=x.shape[0],
                                    max_abs=float(abs(candidate - original).max()),
                                    bitwise_identical=bool(np.array_equal(candidate, original))))
            gate = torch.from_numpy(load(prefix + 'gate'))
            up = torch.from_numpy(load(prefix + 'up'))
            original = activation(gate) * up
            ordered = (.5 * gate) * (1 + torch.tanh(.7978845608028654 * (gate + .044715 * ((gate * gate) * gate)))) * up
            baseline = torch.from_numpy(load(prefix + 'geglu'))
            metrics.append(dict(layer=layer, kind='geglu_order', elements=gate.numel(),
                                original_baseline_max_abs=float((baseline - original).abs().max()),
                                max_abs=float((ordered - original).abs().max()),
                                bitwise_identical=bool(torch.equal(ordered, original))))
    current(before)
    report = dict(schema='lma.ltx098-staging-analysis/1', metrics=metrics, files=files, versions=versions,
                  input_capture_sha256=sha(capture_path), seconds=time.perf_counter() - start,
                  mean_values=sum(item['elements'] for item in metrics if item['kind'].endswith('_mean')),
                  mean_bitwise_identical=all(item['bitwise_identical'] for item in metrics if item['kind'].endswith('_mean')),
                  activation_order_bitwise_identical=all(item['bitwise_identical'] for item in metrics if item['kind'] == 'geglu_order'),
                  retained_trained_intermediates=True, mean_simulation_is_numpy=True, activation_order_analysis_is_torch=True,
                  native_replacement_executed=False, full_model_rerun=False, original_forward_modified=False,
                  acceptance_gates_changed=False, physical_android=False, input_fingerprint=before)
    out = ROOT / 'build/ltx098-staging-analysis'; out.mkdir(exist_ok=True)
    (out / 'results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(comparisons=len(metrics), mean_values=report['mean_values'],
                          mean_bitwise_identical=report['mean_bitwise_identical'],
                          activation_order_bitwise_identical=report['activation_order_bitwise_identical'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    run(parser.parse_args().capture)
