"""Render a labelled still-image slideshow from actual trained host PNGs."""
import json
import shutil
import subprocess
import textwrap
import time
from pathlib import Path

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media/development'


def main():
    from PIL import Image, ImageDraw, ImageFont
    before = fingerprint('tools/render_sd15_trained.py')
    source = ROOT / 'build/sd15-trained-tests/results.json'
    report = json.loads(source.read_text(encoding='utf-8')); current(report['input_fingerprint'])
    if not report['host_execution_checks_passed'] or not report['trained_model_executed'] or report['physical_android']:
        raise ValueError('Require successful scoped actual host PNG execution')
    names = ['sd15-trained-contact-sheet.png', 'sd15-trained-slideshow.gif', 'sd15-trained-slideshow.mp4']
    receipt = OUT / 'sd15-trained-media.json'
    if receipt.exists() or any((OUT / name).exists() for name in names): raise FileExistsError('Preserve existing media')
    directory = (ROOT / report['capture_directory']).resolve()
    if not directory.is_relative_to(ROOT / 'build'): raise ValueError('Capture outside ignored build directory')
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 19)
    small = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 15)
    title_font = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 23)
    labels = ['Prompt A', 'Prompt B', 'Recovery A after cancellation']
    images = []; slides = []; sheet = Image.new('RGB', (1580, 760), '#0f172a')
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 14), 'LMA / ACTUAL TRAINED HOST PNGs / SD 1.5 Q4_0 / CPU', fill='#f8fafc', font=title_font)
    draw.text((12, 48), '512 x 512 / 20 Euler steps / discrete scheduler / CFG 7 / seed 42 / four threads', fill='#cbd5e1', font=font)
    for index, (job, label) in enumerate(zip(report['jobs'], labels)):
        path = directory / (job['name'] + '.png')
        if path.stat().st_size != job['image']['bytes'] or sha(path) != job['image']['sha256']:
            raise ValueError('Changed actual generated image')
        with Image.open(path) as raw:
            raw.load()
            if raw.size != (512, 512) or raw.format != 'PNG': raise ValueError('Wrong actual output geometry')
            image = raw.convert('RGB')
        images.append(image)
        x = 12 + index * 520
        draw.text((x, 86), label, fill='#93c5fd', font=font); sheet.paste(image, (x, 116))
        for line_index, line in enumerate(textwrap.wrap(job['prompt'], width=57)):
            draw.text((x, 638 + line_index * 20), line, fill='#e2e8f0', font=small)
        memory = job['resources']['observed_peak_working_set_bytes'] / 1024**3
        draw.text((x, 690), f"{job['seconds']:.2f}s incl. load / observed host peak WS {memory:.2f} GiB", fill='#cbd5e1', font=small)
        slide = Image.new('RGB', (800, 720), '#0f172a'); sd = ImageDraw.Draw(slide)
        sd.text((16, 16), 'LMA / ACTUAL HOST PNG / ' + label, fill='#f8fafc', font=font)
        sd.text((16, 45), 'SD 1.5 Q4_0 / 512 x 512 / 20 steps / seed 42 / CPU', fill='#cbd5e1', font=small)
        slide.paste(image, (144, 88))
        for line_index, line in enumerate(textwrap.wrap(job['prompt'], width=91)):
            sd.text((16, 617 + line_index * 20), line, fill='#e2e8f0', font=small)
        sd.text((16, 680), 'STILL-IMAGE SLIDESHOW / NOT APP OR ANDROID / QUALITY ACCEPTANCE PENDING', fill='#fbbf24', font=small)
        slides.append(slide)
    draw.text((12, 730), 'HOST ONLY / A and recovery A are byte-identical / no phone, App recording, quality or Release acceptance', fill='#fbbf24', font=font)
    temporary = ROOT / 'build/sd15-trained-media' / str(time.time_ns()); temporary.mkdir(parents=True, exist_ok=False)
    sheet.save(temporary / names[0])
    slides[0].save(temporary / names[1], save_all=True, append_images=slides[1:], duration=1800, loop=0, optimize=False)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('Native host FFmpeg required')
    pixels = b''.join(slide.tobytes() * 18 for slide in slides)
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'rawvideo',
                    '-pixel_format', 'rgb24', '-video_size', '800x720', '-framerate', '10', '-i', 'pipe:0',
                    '-an', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    str(temporary / names[2])], input=pixels, check=True, capture_output=True, timeout=90)
    current(before)
    for name in names: shutil.copyfile(temporary / name, OUT / name)
    sources = {'verification/development/sd15-trained.json': sha(source),
               'verification/development/sd15-assets.json': sha(ROOT / 'build/sd15-trained/receipt.json')}
    record = dict(schema='lma.sd15-trained-media/1', kind='actual_trained_host_png_outputs', sources=sources,
                  source_images=[job['image'] for job in report['jobs']], slideshow_frames=3,
                  gif_duration_ms=5400, mp4_frames=54, mp4_fps=10,
                  files={name: dict(bytes=(OUT / name).stat().st_size, sha256=sha(OUT / name)) for name in names},
                  physical_android=False, app_screen_recording=False, semantic_quality_accepted=False,
                  android_background_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print('Rendered actual host PNG contact sheet and labelled still-image GIF/MP4 slideshow')


if __name__ == '__main__': main()
