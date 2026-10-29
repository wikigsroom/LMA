"""Publish unchanged generated WAV samples and labelled HOST waveform media."""
import json
from pathlib import Path
import shutil
import subprocess
import time
import wave

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/media/development'


def main():
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    before = fingerprint('tools/render_moss_nano_trained.py')
    source = ROOT / 'build/moss-nano-trained-tests/results.json'; report = json.loads(source.read_text(encoding='utf-8'))
    current(report['input_fingerprint'])
    if not report['host_execution_checks_passed'] or report['physical_android']: raise ValueError('Require actual successful HOST execution')
    cases = ['prompt-a', 'english', 'japanese']; suffixes = ['zh', 'en', 'ja']
    audio_names = ['moss-nano-trained-' + lang + '.wav' for lang in suffixes]
    names = audio_names + ['moss-nano-trained-contact-sheet.png', 'moss-nano-trained-waveforms.gif', 'moss-nano-trained-speech.mp4']
    receipt = OUT / 'moss-nano-trained-media.json'
    if receipt.exists() or any((OUT / name).exists() for name in names): raise FileExistsError('Preserve existing captured media')
    temporary = ROOT / 'build/moss-nano-trained-media' / str(time.time_ns()); temporary.mkdir(parents=True, exist_ok=False)
    font_path = r'C:\Windows\Fonts\msyh.ttc'
    title_font = ImageFont.truetype(font_path, 31); font = ImageFont.truetype(font_path, 22); small = ImageFont.truetype(font_path, 17)
    jobs = {j['name']: j for j in report['jobs']}; slides = []; originals = []
    for index, (case, lang, name) in enumerate(zip(cases, suffixes, audio_names)):
        job = jobs[case]; path = ROOT / report['capture_directory'] / (case + '.wav')
        if sha(path) != job['audio']['sha256'] or path.stat().st_size != job['audio']['bytes']: raise ValueError('Changed actual source audio')
        shutil.copyfile(path, temporary / name)
        with wave.open(str(path), 'rb') as stream:
            if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 48000): raise ValueError('Unexpected PCM format')
            pcm = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').astype(np.float64) / 32768
        slide = Image.new('RGB', (960, 660), '#101827'); draw = ImageDraw.Draw(slide)
        draw.rounded_rectangle((26, 24, 192, 58), radius=9, fill='#173b49')
        draw.text((39, 28), 'ACTUAL HOST WAV', font=small, fill='#70edc0')
        draw.text((26, 82), 'LMA / MOSS-TTS-Nano 100M', font=title_font, fill='#f4f8ff')
        draw.text((26, 135), lang.upper() + ' / voice ' + str(job['parameters']['speaker']) + ' / CPU / seed 1234 / 4 threads', font=font, fill='#a9c6e7')
        prompt_lines = []; line = ''
        for char in job['prompt']:
            if draw.textlength(line + char, font=font) > 900:
                prompt_lines.append(line); line = char
            else: line += char
        prompt_lines.append(line)
        for n, line in enumerate(prompt_lines): draw.text((26, 187 + 34*n), line, font=font, fill='#f1f5f9')
        left, top, width, height = 30, 295, 900, 170
        for amplitude in [-1, -.5, 0, .5, 1]:
            y = top + (1 - amplitude) * height / 2
            draw.line((left, y, left + width, y), fill='#28374c', width=1)
        for x in range(width):
            window = pcm[x*len(pcm)//width:(x+1)*len(pcm)//width]
            draw.line((left+x, top+(1-float(window.max()))*height/2,
                       left+x, top+(1-float(window.min()))*height/2), fill='#66d9c0', width=1)
        for n in range(5):
            draw.text((left+n*width/4-(15 if n else 0), top+height+9), f"{job['audio']['seconds']*n/4:.2f}s", font=small, fill='#a9b9ce')
        memory = job['resources']['observed_peak_working_set_bytes'] / 1024**2
        draw.text((26, 515), f"48 kHz / mono PCM16 / {job['audio']['seconds']:.2f}s audio / {job['seconds']:.2f}s process incl. load", font=small, fill='#cbd5e1')
        draw.text((26, 547), f"Observed HOST peak WS: {memory:.1f} MiB / SHA256: {job['audio']['sha256'][:20]}...", font=small, fill='#cbd5e1')
        draw.text((26, 602), 'HOST WAVEFORM SLIDESHOW / Android, speech quality and Release acceptance pending', font=small, fill='#f9ce79')
        slide.save(temporary / (str(index) + '.png')); slides.append(slide)
        originals.append(dict(case=case, file=name, audio=job['audio']))
    sheet = Image.new('RGB', (1440, 990), '#101827')
    for index, slide in enumerate(slides): sheet.paste(slide.resize((720, 495)), ((index % 2)*720, (index//2)*495))
    draw = ImageDraw.Draw(sheet); x, y = 755, 560
    for offset, text in enumerate(['Evidence scope / 验证范围', '7 actual WAV jobs / 7 control cases', 'Java production binding: 40 checks', '11 user-imported model components', 'No model assets inside the APK', 'Phone and speech quality: pending']):
        draw.text((x, y+offset*48), text, font=font, fill='#f9ce79' if offset in [0,5] else '#dbe6f4')
    sheet.save(temporary / names[3])
    slides[0].save(temporary / names[4], save_all=True, append_images=slides[1:], duration=1800, loop=0, optimize=False)
    ffmpeg, ffprobe = shutil.which('ffmpeg'), shutil.which('ffprobe')
    if not ffmpeg or not ffprobe: raise RuntimeError('Native FFmpeg/ffprobe required')
    for index, name in enumerate(audio_names):
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-loop', '1', '-framerate', '10',
            '-i', str(index)+'.png', '-i', name, '-t', str(jobs[cases[index]]['audio']['seconds']), '-map', '0:v:0', '-map', '1:a:0',
            '-c:v', 'libx264', '-tune', 'stillimage', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
            '-shortest', str(index)+'.mp4'], cwd=temporary, check=True, capture_output=True, timeout=90)
    (temporary / 'clips.txt').write_text("file '0.mp4'\nfile '1.mp4'\nfile '2.mp4'\n", encoding='ascii')
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-n', '-f', 'concat', '-safe', '0',
        '-i', 'clips.txt', '-c', 'copy', '-movflags', '+faststart', names[5]], cwd=temporary, check=True, capture_output=True, timeout=90)
    probe = json.loads(subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(temporary / names[5])],
        capture_output=True, check=True, timeout=30).stdout)
    assert sorted(x['codec_type'] for x in probe['streams']) == ['audio', 'video']
    current(before)
    for name in names: shutil.copyfile(temporary / name, OUT / name)
    sources = {'verification/development/moss-nano-trained.json': sha(source),
        'verification/development/moss-nano-assets.json': sha(ROOT / 'build/moss-nano-trained/receipt.json'),
        'verification/development/moss-nano-app-host.json': sha(ROOT / 'build/moss-nano-app-host-tests/results.json')}
    record = dict(schema='lma.moss-nano-trained-media/1', kind='actual_trained_host_wav_and_waveform_slideshow', sources=sources,
        source_audio=originals, gif_frames=3, gif_duration_ms=5400, mp4_duration_seconds=float(probe['format']['duration']),
        mp4_codecs=[x['codec_name'] for x in probe['streams']], waveform_amplitude_normalized=False,
        original_wav_bytes_unchanged=True, mp4_audio_transcoded_aac=True,
        files={name: dict(bytes=(OUT/name).stat().st_size, sha256=sha(OUT/name)) for name in names},
        physical_android=False, app_screen_recording=False, speech_quality_accepted=False,
        complete_release_accepted=False, input_fingerprint=before)
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Published 3 unmodified actual HOST WAVs, waveform sheet/GIF and real-audio slideshow MP4')


if __name__ == '__main__': main()
