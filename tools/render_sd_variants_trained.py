"""Publish byte-identical actual host PNGs with labelled contact sheets/GIF/MP4 still slides."""
import json
from pathlib import Path
import shutil
import subprocess
import textwrap
import time

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media/development'


def main():
    from PIL import Image, ImageDraw, ImageFont
    before = fingerprint('tools/render_sd_variants_trained.py')
    source = ROOT / 'build/sd-variants-trained-tests/results.json'; report = json.loads(source.read_text(encoding='utf-8'))
    current(report['input_fingerprint'])
    if not report['host_execution_checks_passed'] or report['physical_android']: raise ValueError('Require successful scoped actual trained host execution')
    receipt = OUT / 'sd-variants-trained-media.json'
    if receipt.exists(): raise FileExistsError('Preserve existing media')
    directory = (ROOT / report['capture_directory']).resolve(); directory.relative_to(ROOT / 'build')
    temp = ROOT / 'build/sd-variants-trained-media' / str(time.time_ns()); temp.mkdir(parents=True, exist_ok=False)
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 19)
    small = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 15)
    title = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 23)
    effect_source = ROOT/'build/sd-variants-lcm-effect-tests/results.json'
    effect = json.loads(effect_source.read_text(encoding='utf-8')); current(effect['input_fingerprint'])
    if not effect['host_weight_effect_checks_passed']: raise ValueError('Require both LCM weight-effect controls')
    jobs = report['jobs'] + effect['jobs']; slides = []; files = []; images = {}
    for job in jobs:
        name = job['name']; source_dir = ROOT/effect['capture_directory'] if job.get('diagnostic_only') else directory
        path = source_dir / (name + '.png'); expected = job['image']
        if path.stat().st_size != expected['bytes'] or sha(path) != expected['sha256']: raise ValueError('Changed actual PNG source')
        original = 'sd-variants-' + name + '.png'; shutil.copyfile(path, temp / original); files.append(original)
        with Image.open(path) as raw:
            raw.load(); image = raw.convert('RGB')
        images[name] = image
        preview = image.copy(); preview.thumbnail((620, 620), Image.Resampling.LANCZOS)
        slide = Image.new('RGB', (1000, 800), '#0f172a'); draw = ImageDraw.Draw(slide)
        draw.text((18, 15), 'LMA / ACTUAL TRAINED HOST PNG / ' + name, fill='#f8fafc', font=title)
        p = job['parameters']; adapters = ', '.join(str(a['scale']) for a in job['adapters']) or 'none'
        line = f"CPU / {p['width']}x{p['height']} / {p['steps']} {p['sampler']} steps / CFG {p['cfg']:g} / seed 42 / LoRA scales {adapters}"
        draw.text((18, 51), line, fill='#cbd5e1', font=small)
        slide.paste(preview, ((1000-preview.width)//2, 80))
        for i,line in enumerate(textwrap.wrap(job['case']['prompt'], width=114)): draw.text((18, 713+i*18), line, fill='#e2e8f0', font=small)
        draw.text((18, 771), 'STILL SLIDESHOW / NOT APP OR ANDROID RECORDING / QUALITY AND PHONE ACCEPTANCE PENDING', fill='#fbbf24', font=small)
        slides.append(slide)
    for family in ['sd15','sdxl']:
        selected = [j for j in jobs if j['case']['family'] == family]; rows = (len(selected)+2)//3
        sheet = Image.new('RGB', (1584, 106+rows*598+38), '#0f172a'); draw = ImageDraw.Draw(sheet)
        draw.text((12, 14), 'LMA / ACTUAL TRAINED HOST PNGs / ' + family.upper() + ' / CPU', fill='#f8fafc', font=title)
        draw.text((12, 48), 'Style scale 0 / 1, LCM / style combination, cancellation recovery; independent user assets', fill='#cbd5e1', font=font)
        for index,job in enumerate(selected):
            x = 12+(index%3)*524; y = 88+(index//3)*598; image = images[job['name']].copy(); image.thumbnail((512,512),Image.Resampling.LANCZOS)
            draw.text((x,y),job['name'],fill='#93c5fd',font=font); sheet.paste(image,(x+(512-image.width)//2,y+30))
            p=job['parameters']; memory=job['resources']['observed_peak_working_set_bytes']/1024**3
            draw.text((x,y+548),f"{p['width']}x{p['height']} / {p['steps']} {p['sampler']} / CFG {p['cfg']:g}",fill='#cbd5e1',font=small)
            draw.text((x,y+570),f"{job['seconds']:.2f}s incl. load / sampled host peak WS {memory:.2f} GiB",fill='#cbd5e1',font=small)
        draw.text((12,sheet.height-27),'HOST ONLY / unchanged production math / no quality, phone, background or full Release acceptance',fill='#fbbf24',font=small)
        name='sd-variants-'+family+'-contact-sheet.png';sheet.save(temp/name);files.append(name)
    gif='sd-variants-trained-slideshow.gif'; mp4='sd-variants-trained-slideshow.mp4'
    slides[0].save(temp/gif,save_all=True,append_images=slides[1:],duration=1800,loop=0,optimize=False)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('Native local FFmpeg required')
    encoder=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','1000x800','-framerate','10','-i','pipe:0','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(temp/mp4)],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for slide in slides:
            pixels=slide.tobytes()
            for _ in range(18): encoder.stdin.write(pixels)
        encoder.stdin.close(); encoder.wait(timeout=90)
        if encoder.returncode: raise RuntimeError('Local slideshow encoding failed')
    finally:
        if encoder.poll() is None: encoder.kill();encoder.wait(timeout=10)
        for stream in [encoder.stdin,encoder.stdout,encoder.stderr]: stream.close()
    files.extend([gif,mp4]); current(before)
    if any((OUT/name).exists() for name in files): raise FileExistsError('Preserve existing output names')
    for name in files: shutil.copyfile(temp/name,OUT/name)
    record=dict(schema='lma.sd-variants-trained-media/1',kind='actual_trained_host_png_outputs',
        source_pngs={j['name']:j['image']['sha256'] for j in jobs},slideshow_frames=len(slides),gif_duration_ms=len(slides)*1800,
        mp4_frames=len(slides)*18,mp4_fps=10,original_pngs_copied_without_reencoding=True,
        files={name:dict(bytes=(OUT/name).stat().st_size,sha256=sha(OUT/name)) for name in files},
        sources={'verification/development/sd-variants-trained.json':sha(source),
                 'verification/development/sd-variants-assets.json':sha(ROOT/'build/sd-variants-trained/receipt.json'),
                 'verification/development/sd-variants-lcm-effect.json':sha(effect_source)},
        physical_android=False,app_screen_recording=False,semantic_quality_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('Copied 16 byte-identical actual PNGs; rendered two contact sheets and a labelled still GIF/MP4 slideshow.')


if __name__ == '__main__': main()
