"""Copy actual HOST PNGs and render labelled contact sheets and a still GIF/MP4 slideshow."""
import json
from pathlib import Path
import shutil
import subprocess
import time

from evidence import current, fingerprint
from fetch_sd15_trained import sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/media/development'


def main():
    from PIL import Image,ImageDraw,ImageFont
    before=fingerprint('tools/render_sd_distilled_trained.py')
    sources=[ROOT/'build/sd-distilled-asset-probe'/name for name in ['sd-turbo-probe-results.json','lcm-checkpoint-probe-results.json']]
    reports=[json.loads(p.read_text(encoding='utf-8')) for p in sources]
    for report in reports:
        current(report['input_fingerprint'])
        if not report['host_checks_passed'] or report['physical_android']:raise ValueError('Require complete scoped native captures')
    receipt=OUT/'sd-distilled-trained-media.json'
    if receipt.exists():raise FileExistsError('Preserve existing media receipt')
    temp=ROOT/'build/sd-distilled-trained-media'/str(time.time_ns());temp.mkdir(parents=True,exist_ok=False)
    title=ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf',23)
    font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',19)
    small=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',15)
    files=[];slides=[];originals={}
    for family,report,names in [('sd-turbo',reports[0],['one-step','four-step']),('lcm-checkpoint',reports[1],['converted-original','fixed-guidance8p5'])]:
        folder=ROOT/report['capture_directory'];jobs={j['name']:j for j in report['jobs']}
        sheet=Image.new('RGB',(1056,710),'#0f172a');draw=ImageDraw.Draw(sheet)
        draw.text((12,12),'LMA / ACTUAL TRAINED HOST PNG / '+family,fill='#f8fafc',font=title)
        draw.text((12,47),'CPU / identical prompt, seed42, 512x512 / native production math unchanged',fill='#cbd5e1',font=small)
        for index,name in enumerate(names):
            job=jobs[name];path=folder/(name+'.png');expected=job['image'];key=family+'-'+name
            if path.stat().st_size!=expected['bytes'] or sha(path)!=expected['sha256']:raise ValueError('Changed trained source PNG')
            output='sd-distilled-'+key+'.png';shutil.copyfile(path,temp/output);files.append(output);originals[key]=expected['sha256']
            with Image.open(path) as raw:raw.load();image=raw.convert('RGB')
            x=8+index*524;sheet.paste(image,(x,110));draw.text((x,80),name,fill='#93c5fd',font=font)
            p=job['parameters'];memory=job['resources']['observed_peak_working_set_bytes']/1024**2
            label=f"{p['steps']} {p['sampler']} steps / CFG {p['cfg']:g} / {job['seconds']:.2f}s incl. load"
            draw.text((x,632),label,fill='#cbd5e1',font=small)
            draw.text((x,651),f"Observed host peak WS {memory:.1f} MiB; non-exclusive",fill='#cbd5e1',font=small)
            slide=Image.new('RGB',(1000,800),'#0f172a');sd=ImageDraw.Draw(slide)
            sd.text((18,15),'LMA / ACTUAL TRAINED HOST PNG / '+key,fill='#f8fafc',font=title)
            sd.text((18,51),label+' / seed42 / threads6',fill='#cbd5e1',font=small)
            slide.paste(image,((1000-image.width)//2,100))
            for row,text in enumerate(['Prompt: A small red fox sitting beside a blue ceramic teapot on a wooden table, clean composition',
                'LCM: original conversion omits a learned condition; fixed8.5 candidate is a private derivation.',
                'Image quality, canonical pipeline equivalence, product preparation and phone acceptance remain open.']):
                sd.text((18,682+row*24),text,fill='#cbd5e1',font=small)
            sd.text((18,771),'STILL SLIDESHOW / NOT APP OR ANDROID RECORDING / NO COMPLETE RELEASE ACCEPTANCE',fill='#fbbf24',font=small)
            slides.append(slide)
        draw.text((12,682),'HOST ONLY / quality not accepted / no physical Android, background or full target03 acceptance',fill='#fbbf24',font=small)
        sheet_name='sd-distilled-'+family+'-contact-sheet.png';sheet.save(temp/sheet_name);files.append(sheet_name)
    gif='sd-distilled-trained-slideshow.gif';mp4='sd-distilled-trained-slideshow.mp4'
    slides[0].save(temp/gif,save_all=True,append_images=slides[1:],duration=2200,loop=0,optimize=False)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('Native local FFmpeg required')
    child=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','1000x800','-framerate','10','-i','pipe:0','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p',
        '-movflags','+faststart',str(temp/mp4)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for slide in slides:
            for _ in range(22):child.stdin.write(slide.tobytes())
        child.stdin.close();child.wait(timeout=90)
        if child.returncode:raise RuntimeError('Local labelled slideshow encoding failed')
    finally:
        if child.poll() is None:child.kill();child.wait(timeout=10)
        for stream in [child.stdin,child.stdout,child.stderr]:stream.close()
    files.extend([gif,mp4]);current(before)
    if any((OUT/name).exists() for name in files):raise FileExistsError('Preserve existing output media')
    for name in files:shutil.copyfile(temp/name,OUT/name)
    record=dict(schema='lma.sd-distilled-trained-media/1',kind='actual_trained_host_png_outputs',source_pngs=originals,
        slideshow_frames=4,gif_duration_ms=8800,mp4_frames=88,mp4_fps=10,original_pngs_copied_without_reencoding=True,
        sources={str(p.relative_to(ROOT)):sha(p) for p in sources},files={name:dict(bytes=(OUT/name).stat().st_size,sha256=sha(OUT/name)) for name in files},
        physical_android=False,app_screen_recording=False,semantic_quality_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print('Four original PNGs, two contact sheets and a labelled four-slide GIF/MP4; HOST only.',flush=True)


if __name__=='__main__':main()
