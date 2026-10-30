"""Display actual trained PNGs with explicit host/slideshow labels, not phone footage."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from evidence import current, fingerprint, version

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from PIL import Image,ImageDraw,ImageFont
    direct_path=ROOT/'build/zimage-trained-tests/results.json';bridge_path=ROOT/'build/zimage-app-host-tests/results.json'
    direct=json.loads(direct_path.read_text(encoding='utf-8'));bridge=json.loads(bridge_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint']);current(bridge['input_fingerprint'])
    if not direct['host_execution_checks_passed'] or not bridge['production_java_native_host_executed']:raise ValueError('Complete actual trained execution first')
    out=ROOT/'docs/media/development/zimage-trained';out.mkdir(parents=True,exist_ok=True)
    work=ROOT/'build/zimage-trained-media';work.mkdir(parents=True,exist_ok=True)
    body=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',22)
    products=[];frames=[];tiles=[]
    rows={r['name']:r for r in direct['runs']}
    for index,(name,file,label) in enumerate([('a','01-robot.png','Robot and teapot / 8 steps'),('b','02-sailboat.png','Sailboat landscape / 8 steps'),('one-step','03-one-step.png','Same robot prompt / 1 step')]):
        source=ROOT/direct['capture_directory']/(name+'.png');item=rows[name]['image']
        if source.stat().st_size!=item['bytes'] or sha(source)!=item['sha256']:raise ValueError('Actual source PNG changed')
        shutil.copyfile(source,out/file)
        canvas=Image.new('RGB',(768,640),'#eef2f8');draw=ImageDraw.Draw(canvas)
        draw.text((22,12),'LMA / Z-Image-Turbo / Native Windows CPU',font=title,fill='#102f5a')
        draw.text((22,43),'Actual output slideshow; not Android footage or generation timing.',font=body,fill='#48576b')
        with Image.open(source) as image:canvas.paste(image.convert('RGB'),(128,80))
        draw.text((22,604),label+' | seed 42 | SHA '+item['sha256'][:12],font=body,fill='#102f5a')
        frame=work/('frame-'+str(index)+'.png');canvas.save(frame);frames.append(frame);tiles.append(canvas)
        products.append(dict(name=name,file=file,sha256=item['sha256'],bytes=item['bytes'],request=rows[name]['request'],quality_accepted=False))
    sheet=Image.new('RGB',(1536,1280),'#eef2f8')
    for i,tile in enumerate(tiles):sheet.paste(tile,((i%2)*768,(i//2)*640))
    panel=Image.new('RGB',(768,640),'#e0eaf5');draw=ImageDraw.Draw(panel)
    draw.text((30,40),'Four complete user-selected runtime components',font=title,fill='#102f5a')
    for index,label in enumerate(['Z-Image-Turbo Q4_0 diffusion','Original Qwen3-4B Q4_K_M encoder','Original full official 16-channel VAE','External official Qwen merge rules','All learned bytes stay outside the APK','Windows CPU evidence; Android remains unverified']):
        draw.text((30,105+index*63),label,font=body,fill='#30445f')
    sheet.paste(panel,(768,640));sheet.save(out/'contact-sheet.png')
    concat=work/'frames.txt'
    concat.write_text(''.join("file '"+p.name+"'\nduration 3\n" for p in frames)+"file '"+frames[-1].name+"'\n",encoding='utf-8')
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('Use the local FFmpeg installation')
    def run(args):
        result=subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error',*args],cwd=ROOT,capture_output=True,timeout=120)
        if result.returncode:raise RuntimeError('Inspect actual-output FFmpeg error: '+result.stderr.decode('utf-8',errors='replace')[-800:])
    video=out/'zimage-trained.mp4';gif=out/'zimage-trained.gif'
    run(['-f','concat','-safe','0','-i',str(concat),'-r','12','-an','-c:v','libx264','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(video)])
    run(['-i',str(video),'-vf','fps=3,scale=480:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(gif)])
    files=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.suffix in ['.png','.gif','.mp4']]
    report=dict(schema='lma.zimage-trained-media/1',version=version(),real_trained_host_execution=True,android_recording=False,
                slideshow_not_generation_timing=True,image_quality_accepted=False,complete_release_accepted=False,
                products=products,files=files,
                direct_report_sha256=sha(direct_path),java_report_sha256=sha(bridge_path),
                input_fingerprint=fingerprint('tools/render_zimage_trained.py','build/zimage-trained-tests/results.json','build/zimage-app-host-tests/results.json'))
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(products=len(products),files=len(files),android_recording=False)),flush=True)


if __name__=='__main__':main()
