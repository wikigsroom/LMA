"""Render source-linked host T5 roundoff measurements with Matplotlib."""
import json
import math
import os
from pathlib import Path

from evidence import current, fingerprint
from fetch_ltx098_text import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media/development'
SOURCES = ['verification/development/ltx098-text-diagnosis.json',
           'verification/development/ltx098-text-operators.json']


def render():
    before = fingerprint('tools/plot_ltx098_text_diagnosis.py')
    records = [json.loads((ROOT / name).read_text(encoding='utf-8')) for name in SOURCES]
    for record in records: current(record['input_fingerprint'])
    diagnosis, operators = records
    if not diagnosis['baseline_native_caption_bitwise_identical'] or not operators['matched_native_input_comparisons']:
        raise ValueError('Require captured trained intermediates and matched-input analysis')
    if operators['native_capture_sha256'] != sha(ROOT / SOURCES[0]):
        raise ValueError('Operator analysis refers to another capture')
    os.environ['MPLCONFIGDIR'] = str(ROOT / 'build/matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    path = OUT / 'ltx098-text-roundoff.png'; receipt_path = OUT / 'ltx098-text-roundoff.json'
    if path.exists() or receipt_path.exists(): raise FileExistsError('Preserve existing diagnostic media')
    blocks = list(range(24))
    propagated = {item['name']: item['relative_rmse'] for item in diagnosis['metrics']}
    local = {item['name']: item['relative_rmse'] for item in operators['metrics']}
    plotted = {}
    try:
        figure, axes = plt.subplots(1, 2, figsize=(12, 5.8), layout='constrained')
        figure.suptitle('LTX 0.9.8: locating text-encoder roundoff', fontsize=16)
        series = [
            (axes[0], propagated, [('attn-norm', 'Attention input norm'), ('mixed', 'Attention mix'),
                                   ('geglu', 'GeGLU'), ('residual', 'Block residual')]),
            (axes[1], local, [('attn-norm-same-input', 'Attention norm'), ('ffn-norm-same-input', 'FFN norm'),
                              ('geglu-same-input', 'GeGLU'), ('sdpa-same-input', 'Attention vs SDPA')])]
        for axis, values, specs in series:
            for key, label in specs:
                points = [values['block-' + str(i) + '-' + key] for i in blocks]
                if not all(math.isfinite(x) and x > 0 for x in points):
                    raise ValueError('Invalid logarithmic measurement')
                axis.plot(blocks, points, marker='.', linewidth=1.5, label=label)
                plotted[key] = points
            axis.set_yscale('log'); axis.set_xlabel('Encoder block (zero based)')
            axis.set_ylabel('Relative RMSE'); axis.set_xticks([0, 4, 8, 12, 16, 20, 23])
            axis.grid(True, alpha=.25, which='both'); axis.legend(fontsize=8, loc='upper left')
        axes[0].set_title('Propagated: native vs original forward', fontsize=11)
        axes[1].set_title('Local: identical native operator inputs', fontsize=11)
        figure.supxlabel('Actual host capture / same Q5 weights / no App or Android evidence\nBaseline complete-pipeline numerical acceptance remains FAILED', fontsize=9)
        figure.savefig(path, dpi=160)
    finally:
        plt.close('all')
    current(before)
    receipt = dict(kind='actual_host_numerical_diagnostic',
                   sources={name: sha(ROOT / name) for name in SOURCES},
                   file=path.name, bytes=path.stat().st_size, sha256=sha(path),
                   plotted_relative_rmse=plotted, blocks=blocks,
                   renderer='Matplotlib/Agg', matplotlib_version=matplotlib.__version__,
                   baseline_full_chain_numeric_accepted=False, physical_android=False,
                   app_screen_recording=False, video_quality_accepted=False,
                   input_fingerprint=before)
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(file=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size,
                          measured_series=len(plotted), points_per_series=24)), flush=True)


if __name__ == '__main__': render()
