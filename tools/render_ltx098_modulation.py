"""Render measured modulation and trained-sampler errors, not an App screen."""
import json
import os
from pathlib import Path

from check_ltx098_modulation_evidence import ANALYSES, SAMPLERS, SOURCES
from evidence import current, fingerprint
from fetch_ltx098_text import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    before = fingerprint('tools/render_ltx098_modulation.py')
    paths = {name: ROOT / path for name, path in SOURCES.items()}
    paths['ltx098-context-reference-vulkan.json'] = ROOT / 'verification/development/ltx098-context-reference-vulkan.json'
    paths['ltx098-pipeline.json'] = ROOT / 'verification/development/ltx098-pipeline.json'
    records = {name: json.loads(path.read_text(encoding='utf-8')) for name, path in paths.items()}
    for record in records.values(): current(record['input_fingerprint'])
    if any(records[name]['latent_gate_matched'] for name in SAMPLERS):
        raise ValueError('This explicitly failed-candidate visualization needs review')
    output = ROOT / 'docs/media/development/ltx098-modulation-errors.png'
    receipt = output.with_name('ltx098-modulation-media.json')
    if output.exists() or receipt.exists(): raise FileExistsError('Preserve existing media')
    os.environ['MPLCONFIGDIR'] = str(ROOT / 'build/matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    figure, axes = plt.subplots(1, 3, figsize=(16, 5), dpi=140)
    for name, label, color in zip(ANALYSES, ['Original step 0', 'Original step 7'], ['#2563eb', '#0f766e']):
        metrics = records[name]['metrics']
        axes[0].plot(np.arange(57), [m['reassociated_max_abs'] for m in metrics], label=label + ': x + x*scale', color=color)
    axes[0].plot(np.arange(57), [0] * 57, color='#111827', linestyle='--', label='x*(1+scale): exact at all sites')
    axes[0].set_xlabel('56 transformer sites + output site')
    axes[0].set_ylabel('Maximum absolute error vs original input')
    axes[0].set_title('Actual original trained forward: 114 sites')
    axes[0].legend(fontsize=7); axes[0].grid(alpha=.2)
    series = [('ltx098-context-reference-vulkan.json', 'Existing / reference caption', '#64748b'),
              (SAMPLERS[0], 'Ordered / reference caption', '#0f766e'),
              (SAMPLERS[1], 'Ordered / native F32 T5 caption', '#7c3aed')]
    for axis, field, gate, title in [
        (axes[1], 'max_abs', 'full_chain_max_absolute_error', 'Frozen maximum-error gate'),
        (axes[2], 'relative_rmse', 'full_chain_max_relative_rmse', 'Frozen relative-RMSE gate')]:
        for name, label, color in series:
            axis.plot(np.arange(1, 9), [m[field] for m in records[name]['metrics']], marker='o', markersize=3, label=label, color=color)
        axis.axhline(records['ltx098-pipeline.json']['gates'][gate], color='#dc2626', linestyle='--', label='Unchanged gate')
        axis.set_yscale('log'); axis.set_xlabel('Eight actual trained native sampler steps')
        axis.set_title(title); axis.set_ylabel(field.replace('_', ' ')); axis.legend(fontsize=7); axis.grid(alpha=.2)
    figure.suptitle('Old LTX 0.9.8 / native modulation candidate / final numeric gates: FAIL', fontsize=13)
    figure.text(.5, .025, 'ACTUAL HOST measurements. Reference-conditioned diagnosis is separate from native T5 conditioning.\nNo new VAE/video run, App registration, Android execution, quality certification or Release acceptance.', ha='center', fontsize=9)
    figure.subplots_adjust(top=.84, bottom=.23, wspace=.3)
    figure.savefig(output); plt.close(figure)
    current(before)
    record = dict(schema='lma.ltx098-modulation-media/1', kind='measured_host_errors',
                  sources={'verification/development/' + name: sha(path) for name, path in paths.items()},
                  files={output.name: dict(bytes=output.stat().st_size, sha256=sha(output))},
                  physical_android=False, app_screen_recording=False, candidate_numeric_gates_passed=False,
                  new_video_generated=False, video_quality_accepted=False, complete_release_accepted=False,
                  input_fingerprint=before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print('Rendered actual host modulation/error measurements with FAIL labels')


if __name__ == '__main__': main()
