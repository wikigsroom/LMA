"""Render labelled actual host outputs as a contact sheet and still GIF/MP4."""
import json
from pathlib import Path
import shutil
import subprocess
import time

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    from PIL import Image, ImageDraw, ImageFont
    before = fingerprint('tools/render_lcm_preparation.py')
    report_path = ROOT / 'build/lcm-overlay-trained/results.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    current(report['input_fingerprint'])
    if len(report['jobs']) != 5 or not all(j['passed'] for j in report['jobs']) or report['passed'] or report['physical_android'] or report['production_app_executed']:
        raise ValueError('Require completed scoped actual host captures')
    destination = ROOT / 'docs/media/development'
    receipt = destination / 'lcm-preparation-media.json'
    if receipt.exists(): raise FileExistsError('Preserve existing media receipt')
    temp = ROOT / 'build/lcm-preparation-media' / str(time.time_ns())
    temp.mkdir(parents=True)
    title = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 23)
    font = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 19)
    small = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 15)
    sheet = Image.new('RGB', (1056, 746), '#0f172a')
    draw = ImageDraw.Draw(sheet)
    draw.text((12,12), 'LMA / ACTUAL TRAINED HOST PNG / small LCM condition component', fill='#f8fafc', font=title)
    draw.text((12,48), 'CPU / same complete checkpoint, prompt, seed42, 512x512 / no App or phone execution', fill='#cbd5e1', font=small)
    files = []; originals = {}; slides = []
    for index, name in enumerate(['original-bias-control', 'native-prepared']):
        job = next(j for j in report['jobs'] if j['name'] == name)
        source = ROOT / report['capture_directory'] / (name + '.png')
        if sha(source) != job['image']['sha256'] or source.stat().st_size != job['image']['bytes']:
            raise ValueError('Changed source image')
        filename = 'lcm-preparation-' + name + '.png'
        shutil.copyfile(source, temp / filename);files.append(filename);originals[name] = sha(source)
        with Image.open(source) as raw: image = raw.convert('RGB')
        x = 8 + 524 * index
        draw.text((x,80), name, fill='#93c5fd', font=font);sheet.paste(image, (x,110))
        memory = job['resources']['observed_peak_working_set_bytes'] / 1024**2
        label = f"4 LCM steps / CFG1 / {job['seconds']:.2f}s incl. load / host WS {memory:.1f} MiB"
        draw.text((x,632), label, fill='#cbd5e1', font=small)
        draw.text((x,656), 'Original bias control' if index == 0 else 'Native-prepared 5696-byte component; 5120 learned bytes', fill='#cbd5e1', font=small)
        slide = Image.new('RGB', (1000,800), '#0f172a'); sd = ImageDraw.Draw(slide)
        sd.text((18,15), 'LMA / ACTUAL TRAINED HOST PNG / ' + name, fill='#f8fafc', font=title)
        sd.text((18,52), label + ' / seed42 / threads6', fill='#cbd5e1', font=small)
        slide.paste(image, (244,100))
        for row, text in enumerate(['Native preparer reads and verifies the complete original UNet; source weights stay separate.',
            'Fixed distilled guidance8.5 is distinct from sampler CFG1; base/source hashes are recorded.',
            'Pixel equivalence FAILED: max difference8 exceeds gate5. Image quality remains unaccepted.']):
            sd.text((18,675 + row * 24), text, fill='#cbd5e1', font=small)
        sd.text((18,771), 'STILL SLIDESHOW / NOT APP OR ANDROID RECORDING / FULL RELEASE NOT ACCEPTED', fill='#fbbf24', font=small)
        slides.append(slide)
    draw.text((12,690), 'Pixel equivalence FAILED: max8 > gate5. Candidate is not accepted or integrated into the App.', fill='#cbd5e1', font=small)
    draw.text((12,718), 'HOST ONLY / image quality not accepted / no physical Android, background or complete target03 acceptance', fill='#fbbf24', font=small)
    name = 'lcm-preparation-contact-sheet.png';sheet.save(temp/name);files.append(name)
    gif='lcm-preparation-slideshow.gif';mp4='lcm-preparation-slideshow.mp4'
    slides[0].save(temp/gif, save_all=True, append_images=slides[1:], duration=2400, loop=0, optimize=False)
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: raise RuntimeError('Native local FFmpeg required')
    child = subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','1000x800','-framerate','10','-i','pipe:0','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p',
        '-movflags','+faststart',str(temp/mp4)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for slide in slides:
            for _ in range(24): child.stdin.write(slide.tobytes())
        child.stdin.close();child.wait(timeout=90)
        if child.returncode: raise RuntimeError('Labelled still-video encoding failed')
    finally:
        if child.poll() is None: child.kill();child.wait(timeout=10)
        for stream in [child.stdin, child.stdout, child.stderr]: stream.close()
    files.extend([gif,mp4]);current(before)
    if any((destination/name).exists() for name in files): raise FileExistsError('Preserve existing output media')
    for name in files: shutil.copyfile(temp/name,destination/name)
    record = dict(schema='lma.lcm-preparation-media/1', kind='actual_trained_host_png_outputs',
                  original_pngs_copied_without_reencoding=True, source_pngs=originals,
                  slideshow_frames=2, gif_duration_ms=4800, mp4_frames=48, mp4_fps=10,
                  sources={report_path.relative_to(ROOT).as_posix():sha(report_path)},
                  files={name:dict(bytes=(destination/name).stat().st_size,sha256=sha(destination/name)) for name in files},
                  physical_android=False, app_screen_recording=False, semantic_quality_accepted=False,
                  image_comparison_gate_passed=False,
                  complete_release_accepted=False,input_fingerprint=before)
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('Two original PNGs, contact sheet and labelled still GIF/MP4; HOST only.')


if __name__ == '__main__': main()
