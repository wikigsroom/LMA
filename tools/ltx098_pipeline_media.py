"""Render clearly labelled host-only media from verified real trained outputs."""
import json
import shutil
import subprocess
from pathlib import Path
from evidence import current, fingerprint
from ltx098_vae import sha

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'build/ltx098-pipeline-tests/results.json'
OUT = ROOT / 'docs/media/development'


def render():
    from PIL import Image, ImageDraw, ImageFont
    record = json.loads(RESULTS.read_text(encoding='utf-8'))
    current(record['input_fingerprint'])
    if not record['real_prompt_to_video_host_executed'] or not record['original_forward_comparison_executed'] or record['physical_android']:
        raise ValueError('Expected actual host-only pipeline execution and comparison evidence')
    before = fingerprint('tools/ltx098_pipeline_media.py', 'third_party/ltx098-pipeline-source-lock.json')
    names = ['ltx098-host-contact-sheet.png', 'ltx098-host-comparison.gif', 'ltx098-host-comparison.mp4']
    if any((OUT / name).exists() for name in names + ['ltx098-host-media.json']):
        raise ValueError('Preserve existing media; choose an explicit new rendering')
    frames = []
    for case in record['original_oracle']['cases']:
        path = ROOT / case['native_pipeline'] / 'frames.lma'
        expected = record['jobs'][len(frames)]['files']['frames.lma']
        if path.stat().st_size != expected['bytes'] or sha(path) != expected['sha256']: raise ValueError('Changed actual frame source')
        raw = path.read_bytes()
        frames.append([Image.frombytes('RGB', (256, 256), raw[28 + i * 256 * 256 * 3:28 + (i + 1) * 256 * 256 * 3]) for i in range(33)])
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 18)
    small = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 14)
    def header(canvas, subtitle):
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), 'LMA / ACTUAL TRAINED HOST OUTPUT', fill='#f1f5f9', font=font)
        draw.text((16, 39), 'Old LTX 0.9.8 distilled / single-scale / Google T5 Q5', fill='#cbd5e1', font=small)
        draw.text((16, 61), subtitle, fill='#cbd5e1', font=small)
        warning = 'NOT APP/ANDROID; QUALITY NOT ACCEPTED' if record['numerical_acceptance_passed'] else 'NOT APP/ANDROID; NUMERIC + QUALITY GATES OPEN'
        draw.text((16, 83), warning, fill='#fbbf24', font=small)
    sheet = Image.new('RGB', (1304, 710), '#0f172a'); header(sheet, 'Same seed 42 / 256x256 / 33 frames at 24 fps / 8 steps / real prompts')
    draw = ImageDraw.Draw(sheet)
    for row, label in enumerate(('A: red balloon, blue sky', 'B: blue toy car, white tabletop')):
        y = 121 + row * 290
        draw.text((16, y), label, fill='#f1f5f9', font=font)
        for col, index in enumerate((0, 8, 16, 24, 32)):
            x = 8 + col * 260; sheet.paste(frames[row][index], (x, y + 28))
            draw.text((x + 6, y + 265), f'frame {index:02d} / {index / 24:.3f}s', fill='white', stroke_width=2, stroke_fill='black', font=small)
    OUT.mkdir(exist_ok=True)
    sheet.save(OUT / names[0], optimize=True)
    animation = []
    for i in range(33):
        canvas = Image.new('RGB', (544, 422), '#0f172a')
        header(canvas, f'256x256 / 33 frames / 24 fps / seed 42 / frame {i:02d}')
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 115), 'A: red balloon', fill='white', font=font)
        draw.text((280, 115), 'B: blue toy car', fill='white', font=font)
        canvas.paste(frames[0][i], (12, 144)); canvas.paste(frames[1][i], (276, 144))
        draw.text((16, 404), 'Developer demo; no quality, phone or background-endurance claim', fill='#cbd5e1', font=small)
        animation.append(canvas)
    # GIF time is quantized to 10 ms. Record actual timing instead of claiming 24 fps.
    animation[0].save(OUT / names[1], save_all=True, append_images=animation[1:], duration=40, loop=0, optimize=False)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: raise ValueError('Native host FFmpeg is required to render developer MP4')
    target = OUT / names[2]
    if target.exists(): raise ValueError('Preserve an existing media output; choose an explicit new rendering')
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                    '-video_size', '544x422', '-framerate', '24', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-crf', '18',
                    '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)],
                   input=b''.join(x.tobytes() for x in animation), check=True, capture_output=True, timeout=120)
    current(before)
    result = dict(schema='lma.ltx098-host-media/1', kind='actual_trained_host_output',
                  source_evidence='verification/development/ltx098-pipeline.json', source_evidence_sha256=sha(RESULTS),
                  raw_source_frames=[dict(file=x['native_pipeline'] + '/frames.lma', **record['jobs'][i]['files']['frames.lma']) for i, x in enumerate(record['original_oracle']['cases'])],
                  gif_frame_duration_ms=40, gif_duration_seconds=1.32, mp4_fps=24, mp4_duration_seconds=1.375,
                  physical_android=False, app_screen_recording=False, video_quality_accepted=False,
                  numerical_acceptance_passed=record['numerical_acceptance_passed'],
                  official_multiscale_default_reproduced=False, official_pixart_weight_identity_compared=False,
                  files={name: dict(bytes=(OUT / name).stat().st_size, sha256=sha(OUT / name)) for name in names}, input_fingerprint=before)
    (OUT / 'ltx098-host-media.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(media_files=len(names), physical_android=False, app_screen_recording=False)), flush=True)


if __name__ == '__main__': render()
