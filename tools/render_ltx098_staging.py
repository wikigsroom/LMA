"""Render measured errors and actual host frames for the staging experiment."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from evidence import current, fingerprint
from fetch_ltx098_text import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media/development'


def render(reference):
    before = fingerprint('tools/render_ltx098_staging.py')
    reference = reference.resolve()
    if not reference.is_relative_to(ROOT / 'build'): raise ValueError('Reference must stay below build/')
    source_names = ['ltx098-pipeline.json', 'ltx098-text-precision-attention.json', 'ltx098-text-precision-linear.json',
                    'ltx098-accuracy-activation.json', 'ltx098-accuracy-order.json', 'ltx098-accuracy-staging.json',
                    'ltx098-accuracy-f32.json', 'ltx098-accuracy-trajectory-f32.json']
    paths = [ROOT / 'verification/development' / name for name in source_names]
    records = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    for record in records: current(record['input_fingerprint'])
    baseline, *_, chain = records
    if (chain['variant'] != 'f32' or not chain['aba_bitwise_identical'] or chain['physical_android'] or
        sha(reference / 'references.json') != chain['original_oracle_sha256']):
        raise ValueError('Expected verified host-only trained A/B/A with original references')
    filenames = ['ltx098-staging-errors.png', 'ltx098-staging-frames.png', 'ltx098-staging-comparison.gif', 'ltx098-staging-comparison.mp4']
    receipt_path = OUT / 'ltx098-staging-media.json'
    if receipt_path.exists() or any((OUT / name).exists() for name in filenames): raise FileExistsError('Preserve existing staging media')
    os.environ['MPLCONFIGDIR'] = str(ROOT / 'build/matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    passed = chain['full_chain_original_numeric_gates_passed']
    labels = ['F32 baseline', 'F64 attention', '+ F64 linear', '+ F64 RMS/GeGLU', '+ ordered GeGLU', 'baseline RMS/order', 'F32 staged RMS/order']
    caption = [[next(m['max_abs'] for m in baseline['metrics'] if m['kind'] == 'full_chain' and m['case'] == case and m['file'] == 'caption.f32')
                for case in [0, 1]]]
    caption += [[record['jobs'][case]['metric']['max_abs'] for case in [0, 1]] for record in records[1:7]]
    figure, axes = plt.subplots(1, 2, figsize=(14, 5), dpi=140)
    x = np.arange(len(labels))
    for case, color in [(0, '#2563eb'), (1, '#0f766e')]:
        axes[0].bar(x + (case - .5) * .36, [row[case] for row in caption], .36, color=color, label='Prompt ' + 'AB'[case])
    axes[0].set_xticks(x, labels, rotation=32, ha='right', fontsize=8)
    axes[0].set_yscale('log'); axes[0].set_ylabel('Maximum absolute caption error')
    axes[0].set_title('Full trained T5: unchanged original forward')
    axes[0].legend(fontsize=8); axes[0].grid(axis='y', alpha=.2)
    groups = [('A latent', 0, 'denoised-tokens.f32'), ('A decoded', 0, 'decoded-ncthw.f32'),
              ('B latent', 1, 'denoised-tokens.f32'), ('B decoded', 1, 'decoded-ncthw.f32')]
    x = np.arange(4)
    old = [next(m['max_abs'] for m in baseline['metrics'] if m['kind'] == 'full_chain' and m['case'] == case and m['file'] == file) for _, case, file in groups]
    new = [next(m['max_abs'] for m in chain['jobs'][case]['decode']['metrics'] if m['file'] == file) for _, case, file in groups]
    axes[1].bar(x - .18, old, .36, color='#64748b', label='Existing native baseline')
    axes[1].bar(x + .18, new, .36, color='#0f766e', label='Isolated F32 staging candidate')
    axes[1].axhline(baseline['gates']['full_chain_max_absolute_error'], color='#dc2626', linestyle='--', linewidth=1.2, label='Frozen maximum-error gate')
    axes[1].set_xticks(x, [g[0] for g in groups], fontsize=9)
    axes[1].set_yscale('log'); axes[1].set_ylabel('Maximum absolute error')
    axes[1].set_title('Native DiT + original trained VAE'); axes[1].grid(axis='y', alpha=.2); axes[1].legend(fontsize=8)
    figure.suptitle('Old LTX 0.9.8 / actual HOST experiment / full candidate numeric gates: ' + ('PASS' if passed else 'FAIL'), fontsize=12)
    figure.text(.5, .015, 'Two real prompts, same external Google Q5 weights and original references. Other RMSE/cosine/RGB gates also apply.\nNot an Android test, registered App engine, quality score or complete Release.', ha='center', fontsize=8)
    figure.subplots_adjust(bottom=.27, top=.84, wspace=.25)
    figure.savefig(OUT / filenames[0]); plt.close(figure)
    native_frames = []; originals = []; source_frames = []

    def frame_file(path, identity):
        if path.stat().st_size != identity['bytes'] or sha(path) != identity['sha256']: raise ValueError('Changed host frame source')
        raw = path.read_bytes()
        if raw[:8] != b'LMAFRM1\0' or len(raw) != 28 + 33 * 256 * 256 * 3: raise ValueError('Wrong host frame container')
        source_frames.append(dict(file=path.relative_to(ROOT).as_posix(), **identity))
        return [Image.frombytes('RGB', (256, 256), raw[28 + i * 196608:28 + (i + 1) * 196608]) for i in range(33)]

    for case in [0, 1]:
        original = baseline['original_oracle']['cases'][case]
        old_path = ROOT / original['native_pipeline'] / 'frames.lma'
        new_path = ROOT / chain['jobs'][case]['decode']['capture_directory'] / 'frames.lma'
        native_frames.append([frame_file(old_path, baseline['jobs'][case]['files']['frames.lma']),
                              frame_file(new_path, chain['jobs'][case]['decode']['files']['frames.lma'])])
        rgb_path = reference / original['name'] / 'rgb.bin'; identity = original['files']['rgb.bin']
        if rgb_path.stat().st_size != identity['bytes'] or sha(rgb_path) != identity['sha256']: raise ValueError('Changed original RGB reference')
        raw = rgb_path.read_bytes(); source_frames.append(dict(file=rgb_path.relative_to(ROOT).as_posix(), **identity))
        originals.append([Image.frombytes('RGB', (256, 256), raw[i * 196608:(i + 1) * 196608]) for i in range(33)])
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 18)
    small = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 14)
    animation = []
    for index in range(33):
        canvas = Image.new('RGB', (808, 742), '#0f172a'); draw = ImageDraw.Draw(canvas)
        draw.text((12, 12), 'LMA / ACTUAL TRAINED HOST OUTPUT / precision experiment', fill='#f1f5f9', font=font)
        draw.text((12, 40), 'Old LTX 0.9.8 distilled / single scale / Google T5 Q5', fill='#cbd5e1', font=small)
        draw.text((12, 63), 'Candidate original numeric gates: ' + ('PASS' if passed else 'FAIL') + ' / not registered in App', fill='#a7f3d0', font=small)
        for column, label in enumerate(['Existing native baseline', 'F32 staging candidate', 'Original trained forward']):
            draw.text((10 + 266 * column, 95), label, fill='#f1f5f9', font=small)
        for case, title in [(0, 'A / red-balloon prompt'), (1, 'B / blue-toy-car prompt')]:
            y = 142 + 286 * case
            draw.text((12, y - 22), title + ' / frame ' + str(index) + '/32', fill='#cbd5e1', font=small)
            for column, source in enumerate(native_frames[case] + [originals[case]]): canvas.paste(source[index], (10 + 266 * column, y))
        draw.text((12, 703), 'HOST ONLY / NOT ANDROID / NO VIDEO QUALITY ACCEPTANCE', fill='#fbbf24', font=small)
        animation.append(canvas)
    animation[16].save(OUT / filenames[1])
    animation[0].save(OUT / filenames[2], save_all=True, append_images=animation[1:], duration=40, loop=0, optimize=False, disposal=2)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('Native host FFmpeg required')
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                    '-video_size', '808x742', '-framerate', '24', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                    '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(OUT / filenames[3])],
                   input=b''.join(frame.tobytes() for frame in animation), capture_output=True, check=True, timeout=120)
    current(before)
    receipt = dict(schema='lma.ltx098-staging-media/1', kind='actual_trained_host_comparison_and_measurements',
                   sources={path.relative_to(ROOT).as_posix(): sha(path) for path in paths}, raw_source_frames=source_frames,
                   candidate_numeric_gates_passed=passed, gif_duration_ms=1320, mp4_fps=24, frames=33,
                   physical_android=False, app_screen_recording=False, video_quality_accepted=False,
                   engine_registered=False, official_multiscale_default_reproduced=False,
                   files={name: dict(bytes=(OUT / name).stat().st_size, sha256=sha(OUT / name)) for name in filenames},
                   input_fingerprint=before)
    (receipt_path).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(media_files=4, candidate_numeric_gates_passed=passed, physical_android=False)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    render(parser.parse_args().reference)
