"""Publish actual generated Wan frames and labelled host videos, never Android footage."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from evidence import current, fingerprint, version
from fetch_wan_trained import sha
from test_wan_trained import frame_stats

ROOT=Path(__file__).resolve().parents[1]


def main():
    from PIL import Image,ImageDraw,ImageFont
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decoder-capture',help='Existing owned 512-pixel/temporal decoder experiment; not the model defaults')
    args=parser.parse_args()
    direct_path=ROOT/'build/wan-trained-tests/results.json';bridge_path=ROOT/'build/wan-app-host-tests/results.json'
    direct=json.loads(direct_path.read_text(encoding='utf-8'));bridge=json.loads(bridge_path.read_text(encoding='utf-8'))
    current(direct['input_fingerprint']);current(bridge['input_fingerprint'])
    if not direct['host_execution_checks_passed'] or not bridge['production_java_native_host_executed']:raise ValueError('Complete actual native and Java execution first')
    source_inputs=['tools/render_wan_trained.py','tools/test_wan_trained.py','build/wan-trained-tests/results.json','build/wan-app-host-tests/results.json']
    candidates=[]
    for name,label in [('a','Robot / 4 steps / explicit small test'),('b','Sailboat / 4 steps / explicit small test'),('one-step','Robot / 1 step / not a quality claim')]:
        run=next(r for r in direct['runs'] if r['name']==name)
        candidates.append((name,ROOT/direct['capture_directory']/(name+'.rgb'),run['frames'],run['request'],label))
    if args.decoder_capture:
        folder=(ROOT/args.decoder_capture).resolve()
        if folder.parent not in [(ROOT/'build/wan-smoke').resolve(),(ROOT/'build/wan-quality').resolve()] or not (folder.name.startswith('run-') or folder.name.startswith('current-default-')):raise ValueError('Not an owned default capture')
        report_path=folder/'result.json';report=json.loads(report_path.read_text(encoding='utf-8'))
        if report['compilation']!=direct['compilation'] or report['components']!=direct['components'] or report['process']['returncode']!=0:raise ValueError('Default capture differs from current complete source/assets')
        request=report['request'];params=request['parameters']
        if request['backend']!='vulkan' or request['pipeline']!='wan21_13b' or tuple(params[k] for k in ['width','height','frames','fps','steps','cfg','flowShift'])!=(512,288,17,8,20,6,3):raise ValueError('Not the exact default configuration')
        if params.get('vaeTileSize')!=512 or params.get('vaeTemporalTiling') is not True:raise ValueError('Not the explicit experimental decoder configuration')
        execution=[e['details'] for e in report['process']['events'] if e.get('event')=='execution']
        if len(execution)!=1 or not execution[0]['vulkanGraphObserved'] or execution[0]['remoteInference']:raise ValueError('No completed GPU operation in default capture')
        raw=folder/Path(request['output'].replace('\\','/')).name;stats=frame_stats(raw)
        if stats['sha256']!=report['output']['sha256'] or stats['changed_from_first']==0:raise ValueError('Default output changed or lacks motion')
        candidates.insert(0,('decoder',raw,stats,request,'Explicit VAE 512 / temporal / NOT defaults / quality unaccepted'))
        source_inputs.append(report_path.relative_to(ROOT).as_posix())
    before=fingerprint(*source_inputs)
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg:raise RuntimeError('Native Windows FFmpeg is required')
    out=ROOT/'docs/media/development/wan-trained';out.mkdir(parents=True,exist_ok=True)
    work=ROOT/'build/wan-trained-media';work.mkdir(parents=True,exist_ok=True)
    title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',18);body=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    products=[]
    for name,source,stats,request,label in candidates:
        actual=frame_stats(source)
        if actual!=stats:raise ValueError('Actual generated RGB frames changed')
        data=source.read_bytes()[28:];width=stats['width'];height=stats['height'];count=stats['frames'];extent=width*height*3
        frames=[Image.frombytes('RGB',(width,height),data[i*extent:(i+1)*extent]) for i in range(count)]
        canvases=[]
        for i,frame in enumerate(frames):
            canvas=Image.new('RGB',(640,410),'#101b2b');draw=ImageDraw.Draw(canvas)
            draw.text((14,10),'LMA / WAN 2.1 / ACTUAL WINDOWS VULKAN OUTPUT',font=title,fill='white')
            draw.text((14,38),'CPU text/VAE; host FFmpeg; NOT Android footage or timing.',font=body,fill='#c1d4e7')
            canvas.paste(frame,((640-width)//2,68))
            draw.text((14,370),label,font=body,fill='#ffd29d');draw.text((14,390),str(i+1)+' / '+str(count)+' | SHA '+stats['sha256'][:16],font=body,fill='#c1d4e7')
            canvases.append(canvas)
        sheet=Image.new('RGB',(1280,820),'#101b2b')
        for index,frame in enumerate([canvases[0],canvases[len(canvases)//2],canvases[-1]]):sheet.paste(frame,((index%2)*640,(index//2)*410))
        draw=ImageDraw.Draw(sheet);draw.text((660,470),'Actual moving model frames',font=title,fill='white')
        draw.text((660,510),'Independent numerics and quality: NOT accepted',font=body,fill='#ffd29d')
        draw.text((660,545),'Phone resources / Android encoding: NOT tested',font=body,fill='#ffd29d')
        sheet.save(out/(name+'-frames.png'))
        input_png=work/(name+'-%03d.png')
        for i,canvas in enumerate(canvases):canvas.save(work/(name+'-'+str(i).zfill(3)+'.png'))
        video=out/(name+'.mp4');gif=out/(name+'.gif')
        for command in [
            ['-framerate',str(stats['fps']),'-i',str(input_png),'-frames:v',str(count),'-an','-c:v','libx264','-threads','2','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],
            ['-i',str(video),'-vf','fps=8,scale=480:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(gif)]]:
            result=subprocess.run([ffmpeg,'-y','-hide_banner','-loglevel','error',*command],capture_output=True,timeout=120)
            if result.returncode:raise RuntimeError(result.stderr.decode('utf-8',errors='replace')[-700:])
        products.append(dict(name=name,source_sha256=stats['sha256'],source_bytes=stats['bytes'],frames=stats['frames'],width=width,height=height,
            request=request,quality_accepted=False,default_smoke=False,controlled_full_geometry=name=='decoder'))
    for output in bridge['outputs']:
        source=ROOT/output['file']
        if sha(source)!=output['sha256']:raise ValueError('Actual Java MP4 changed')
        shutil.copyfile(source,out/('java-'+output['name']+'.mp4'))
    current(before)
    report=dict(schema='lma.wan-trained-media/1',version=version(),real_trained_host_execution=True,android_recording=False,
        host_encoder='native_windows_ffmpeg_libx264',generation_timing_depicted=False,independent_numerics_accepted=False,
        video_quality_accepted=False,complete_release_accepted=False,products=products,
        historical_default_smoke=dict(checkpoint='0.3.0-dev.39',current_execution=False,quality_accepted=False,
            files=['default-frames.png','default.gif','default.mp4']),
        files=[dict(file=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir()) if p.suffix in ['.png','.gif','.mp4']],
        direct_report_sha256=sha(direct_path),java_report_sha256=sha(bridge_path),input_fingerprint=before)
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(products=len(products),files=len(report['files']),android_recording=False)),flush=True)


if __name__=='__main__':main()
