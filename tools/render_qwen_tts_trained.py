"""Publish original trained speech samples and explicitly labelled HOST waveform media."""
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
    before = fingerprint('tools/render_qwen_tts_trained.py')
    source = ROOT / 'build/qwen-tts-trained-tests/results.json'; report = json.loads(source.read_text(encoding='utf-8'))
    app_source = ROOT / 'build/qwen-tts-app-host-tests/results.json'; app = json.loads(app_source.read_text(encoding='utf-8'))
    current(report['input_fingerprint']); current(app['input_fingerprint'])
    if not report['host_execution_checks_passed'] or report['physical_android']: raise ValueError('Require successful actual HOST execution')
    cases = ['prompt-a', 'language-en', 'reference-a']
    titles = ['Qwen Base / Chinese', 'Qwen Base / English', 'Qwen Base / selected reference']
    audio_names = ['qwen-tts-trained-'+p+'.wav' for p in ['zh','en','reference']]
    names = audio_names + ['qwen-tts-trained-contact-sheet.png','qwen-tts-trained-waveforms.gif','qwen-tts-trained-speech.mp4']
    receipt = OUT / 'qwen-tts-trained-media.json'
    if receipt.exists() or any((OUT/name).exists() for name in names): raise FileExistsError('Preserve existing published media')
    temporary = ROOT / 'build/qwen-tts-trained-media' / str(time.time_ns()); temporary.mkdir(parents=True,exist_ok=False)
    font_path = r'C:\Windows\Fonts\msyh.ttc'
    title_font = ImageFont.truetype(font_path,31); font = ImageFont.truetype(font_path,22); small = ImageFont.truetype(font_path,17)
    jobs = {j['name']:j for j in report['jobs']}; slides = []; originals = []
    for index,(case,title,name) in enumerate(zip(cases,titles,audio_names)):
        job=jobs[case]; path=ROOT/report['capture_directory']/(case+'.wav')
        if sha(path)!=job['audio']['sha256'] or path.stat().st_size!=job['audio']['bytes']: raise ValueError('Changed trained audio')
        shutil.copyfile(path,temporary/name)
        with wave.open(str(path),'rb') as stream:
            if (stream.getnchannels(),stream.getsampwidth(),stream.getframerate())!=(1,2,job['audio']['sample_rate']): raise ValueError('Different PCM format')
            pcm=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float64)/32768
        slide=Image.new('RGB',(960,660),'#101827'); draw=ImageDraw.Draw(slide)
        draw.rounded_rectangle((26,24,192,58),radius=9,fill='#173b49'); draw.text((39,28),'ACTUAL HOST WAV',font=small,fill='#70edc0')
        draw.text((26,82),'LMA / '+title,font=title_font,fill='#f4f8ff')
        draw.text((26,135),'0.6B Base Q4_K_M / 12Hz codec Q8_0 / CPU / 4 threads',font=font,fill='#a9c6e7')
        draw.text((26,190),job['prompt'],font=font,fill='#f1f5f9')
        draw.text((26,234),'Actual seed: 1234 / reference mode: '+job['execution']['referenceMode'],font=small,fill='#cbd5e1')
        left,top,width,height=30,295,900,170
        for amplitude in [-1,-.5,0,.5,1]:
            y=top+(1-amplitude)*height/2; draw.line((left,y,left+width,y),fill='#28374c',width=1)
        for x in range(width):
            window=pcm[x*len(pcm)//width:(x+1)*len(pcm)//width]
            draw.line((left+x,top+(1-float(window.max()))*height/2,left+x,top+(1-float(window.min()))*height/2),fill='#66d9c0',width=1)
        for n in range(5):draw.text((left+n*width/4-(15 if n else 0),top+height+9),f"{job['audio']['seconds']*n/4:.2f}s",font=small,fill='#a9b9ce')
        memory=job['resources']['observed_peak_working_set_bytes']/1024**2
        draw.text((26,515),f"{job['audio']['sample_rate']} Hz / mono PCM16 / {job['audio']['seconds']:.2f}s audio / {job['seconds']:.2f}s process incl. load",font=small,fill='#cbd5e1')
        draw.text((26,547),f"Observed HOST peak WS: {memory:.1f} MiB / SHA256: {job['audio']['sha256'][:20]}...",font=small,fill='#cbd5e1')
        draw.text((26,602),'HOST WAVEFORM SLIDESHOW / Android, speech quality and Release acceptance pending',font=small,fill='#f9ce79')
        slide.save(temporary/(str(index)+'.png')); slides.append(slide); originals.append(dict(case=case,file=name,audio=job['audio']))
    sheet=Image.new('RGB',(1440,990),'#101827')
    for index,slide in enumerate(slides):sheet.paste(slide.resize((720,495)),((index%2)*720,(index//2)*495))
    draw=ImageDraw.Draw(sheet)
    lines=['Evidence scope / 验证范围',f"{len(report['jobs'])} actual WAV jobs / {len(report['controls'])} controls",
        '10 languages / reference / frame16 cancellation',f"Java production binding: {app['java']['passed']} checks",'2 user-owned GGUFs / no APK weights','Phone, quality and licenses: pending']
    for index,text in enumerate(lines):draw.text((755,560+index*48),text,font=font,fill='#f9ce79' if index in [0,5] else '#dbe6f4')
    sheet.save(temporary/names[3]); slides[0].save(temporary/names[4],save_all=True,append_images=slides[1:],duration=1800,loop=0,optimize=False)
    ffmpeg,ffprobe=shutil.which('ffmpeg'),shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:raise RuntimeError('Native FFmpeg/ffprobe required')
    for index,name in enumerate(audio_names):
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-loop','1','-framerate','10','-i',str(index)+'.png','-i',name,
            '-t',str(jobs[cases[index]]['audio']['seconds']),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-tune','stillimage','-crf','20',
            '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000','-ac','1','-shortest',str(index)+'.mp4'],cwd=temporary,check=True,capture_output=True,timeout=90)
    (temporary/'clips.txt').write_text("file '0.mp4'\nfile '1.mp4'\nfile '2.mp4'\n",encoding='ascii')
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-f','concat','-safe','0','-i','clips.txt','-c','copy','-movflags','+faststart',names[5]],cwd=temporary,check=True,capture_output=True,timeout=90)
    probe=json.loads(subprocess.run([ffprobe,'-v','error','-show_streams','-show_format','-of','json',str(temporary/names[5])],capture_output=True,check=True,timeout=30).stdout)
    assert sorted(x['codec_type'] for x in probe['streams'])==['audio','video']
    current(before)
    for name in names:shutil.copyfile(temporary/name,OUT/name)
    sources={'verification/development/qwen-tts-trained.json':sha(source),'verification/development/qwen-tts-assets.json':sha(ROOT/'build/qwen-tts-trained/receipt.json'),
        'verification/development/qwen-tts-app-host.json':sha(app_source)}
    record=dict(schema='lma.qwen-tts-trained-media/1',kind='actual_trained_host_wav_and_waveform_slideshow',sources=sources,source_audio=originals,
        gif_frames=3,gif_duration_ms=5400,mp4_duration_seconds=float(probe['format']['duration']),mp4_codecs=[x['codec_name'] for x in probe['streams']],
        waveform_amplitude_normalized=False,original_wav_bytes_unchanged=True,mp4_audio_transcoded_aac=True,mp4_audio_resampled_hz=48000,
        files={name:dict(bytes=(OUT/name).stat().st_size,sha256=sha(OUT/name)) for name in names},
        physical_android=False,app_screen_recording=False,speech_quality_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Published three unmodified Qwen trained HOST WAVs, waveform sheet/GIF and actual-audio slideshow MP4',flush=True)


if __name__=='__main__':main()
