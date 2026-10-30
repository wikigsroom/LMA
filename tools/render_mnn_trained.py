"""Publish exact real Sana host outputs and a labelled artifact slideshow, never fake phone footage."""
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageOps

from evidence import current, fingerprint, version
from fetch_mnn_trained import sha

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'docs/media/development/sana-trained'


def main():
    direct_path = ROOT / 'build/mnn-trained-tests/results.json'; bridge_path = ROOT / 'build/mnn-app-host-tests/results.json'
    direct = json.loads(direct_path.read_text(encoding='utf-8')); bridge = json.loads(bridge_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint']); current(bridge['input_fingerprint'])
    if not direct['passed'] or not bridge['passed']: raise ValueError('Complete real native and Java pipeline checks first')
    DESTINATION.mkdir(parents=True, exist_ok=True)
    work = ROOT / 'build/mnn-trained-media'; work.mkdir(parents=True, exist_ok=True)
    regular = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 21)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
    title = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
    cases = [('a', 'Prompt A / 无 CFG'), ('b', 'Prompt B / 无 CFG'), ('cfg-a', 'Prompt A + CFG / 负面条件 A'),
             ('cfg-b', 'Prompt A + CFG / 负面条件 B'), ('rectangle', '320 × 256 / 非方形'), ('single-step', '256 × 256 / 单步边界')]
    frames = []; products = []; raw_images = []
    for index, (name, label) in enumerate(cases, 1):
        run = next(i for i in direct['runs'] if i['name'] == name)
        source = ROOT / direct['capture_directory'] / (name + '.png')
        if sha(source) != run['image']['sha256']: raise ValueError('Changed actual output')
        filename = '%02d-%s.png' % (index, name); shutil.copy2(source, DESTINATION / filename)
        products.append(dict(case=name, file=filename, sha256=sha(source), request=run['request'], image=run['image'], host_resources=run['process']['resources']))
        with Image.open(source) as opened: raw = opened.convert('RGB')
        raw_images.append(raw.copy())
        frame = Image.new('RGB', (960, 800), '#101c2a'); draw = ImageDraw.Draw(frame)
        draw.text((34, 22), 'LMA · Sana mobile · REAL HOST OUTPUT', font=title, fill='#eef5ff')
        draw.text((34, 70), label, font=regular, fill='#79d8c8')
        image = ImageOps.contain(raw, (650, 568)); frame.paste(image, ((960 - image.width) // 2, 112 + (568 - image.height) // 2))
        draw.text((34, 695), '真实模型主机产物展示；不是 Android 录屏。画质未验收。', font=regular, fill='#ffd79b')
        draw.text((34, 739), 'All 13 user assets · local CPU · no model data in APK · seed 42', font=small, fill='#b5c7d8')
        frame.save(work / ('frame-%02d.png' % index)); frames.append(frame)
    sheet = Image.new('RGB', (1280, 1070), '#101c2a'); draw = ImageDraw.Draw(sheet)
    draw.text((28, 19), 'Sana · production worker · actual Windows CPU outputs', font=title, fill='#eef5ff')
    draw.text((28, 67), '真实组件运行 / 主机证据；Android、独立数值与画质尚未通过', font=regular, fill='#ffd79b')
    for i, raw in enumerate(raw_images):
        x = 28 + (i % 3) * 420; y = 120 + (i // 3) * 455
        image = ImageOps.contain(raw, (396, 396)); sheet.paste(image, (x + (396 - image.width) // 2, y + (396 - image.height) // 2))
        draw.text((x, y + 404), cases[i][1], font=small, fill='#b5c7d8')
    sheet.save(DESTINATION / '00-contact-sheet.png')
    resized = [frame.resize((600, 500), Image.Resampling.LANCZOS) for frame in frames]
    resized[0].save(DESTINATION / 'sana-host-outputs.gif', save_all=True, append_images=resized[1:], duration=1800, loop=0)
    ffmpeg = shutil.which('ffmpeg'); ffprobe = shutil.which('ffprobe')
    if not ffmpeg or not ffprobe: raise RuntimeError('Use configured native ffmpeg/ffprobe')
    command = [ffmpeg, '-y', '-hide_banner', '-loglevel', 'error', '-framerate', '1/2', '-i', str(work / 'frame-%02d.png'),
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p', '-r', '24', '-movflags', '+faststart', str(DESTINATION / 'sana-host-outputs.mp4')]
    subprocess.run(command, check=True, capture_output=True, timeout=90)
    probe = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-show_streams', '-of', 'json', str(DESTINATION / 'sana-host-outputs.mp4')], timeout=30))
    stream = probe['streams'][0]
    if stream['codec_name'] != 'h264' or (stream['width'], stream['height']) != (960, 800): raise ValueError('Different media export')
    files = [dict(file=path.name, bytes=path.stat().st_size, sha256=sha(path)) for path in sorted(DESTINATION.iterdir()) if path.suffix in ['.png', '.gif', '.mp4']]
    before = {**direct['input_fingerprint'], **bridge['input_fingerprint'],
              **fingerprint('tools/render_mnn_trained.py', 'app/src/main/AndroidManifest.xml', 'build/mnn-trained-tests/results.json', 'build/mnn-app-host-tests/results.json')}
    current(before)
    report = dict(schema='lma.mnn-trained-media/1', version=version(), kind='actual_native_windows_output_slideshow', files=files,
                  products=products, direct_report_sha256=sha(direct_path), java_report_sha256=sha(bridge_path),
                  real_trained_host_execution=True, production_java_native_host_executed=True, android_recording=False,
                  physical_android=False, image_quality_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    (DESTINATION / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(actual_outputs=len(products), files=len(files), android_recording=False)))


if __name__ == '__main__': main()
