"""Publish the executed production host video and honestly labelled derived previews."""
import hashlib,json,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from evidence import fingerprint,current,version

ROOT=Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    source=ROOT/'build/ltx098-app-trained/results.json';report=json.loads(source.read_text(encoding='utf-8'))
    current(report['input_fingerprint'])
    assert report['passed'] and report['modelInference'] and report['productionEngineAndQueue']
    assert not any(report[k] for k in ['physicalAndroid','qualityAccepted','numericalAccepted','original_numerical_acceptance_passed'])
    assert all(item['byte_identical'] for item in report['prior_original_native_chain_comparison'].values())
    before=report['input_fingerprint']|fingerprint('tools/ltx098_app_media.py','build/ltx098-app-trained/results.json')
    run=report['runs'][0];video=(ROOT/report['captured_video']).resolve();assert video.is_relative_to(ROOT/'build/ltx098-app-trained')
    assert video.stat().st_size==run['videoBytes'] and sha(video)==run['videoSha256']
    out=ROOT/'docs/media/development/ltx-app-trained';out.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(video,out/'video.mp4')
    ffmpeg=shutil.which('ffmpeg');assert ffmpeg
    raw=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True,timeout=60).stdout
    width=height=256;count=33;extent=width*height*3;assert len(raw)==extent*count
    frames=[Image.frombytes('RGB',(width,height),raw[i*extent:(i+1)*extent]) for i in range(count)]
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
    sheet=Image.new('RGB',(816,388),'#101b2b');draw=ImageDraw.Draw(sheet)
    draw.text((16,12),'ACTUAL PRODUCTION JAVA + NATIVE HOST / OLD LTX 0.9.8',font=font,fill='white')
    draw.text((16,38),'Google T5 Q5 / single scale / 8 steps / 256 x 256 / 33 frames / seed 42',font=small,fill='#bfcfdd')
    draw.text((16,60),'Numerical gates FAILED; quality NOT accepted. Desktop FFmpeg; NOT Android.',font=small,fill='#ffcfa4')
    for column,index in enumerate([0,16,32]):
        x=16+column*264;sheet.paste(frames[index],(x,88));draw.text((x,352),'Actual frame '+str(index),font=small,fill='white')
    sheet.save(out/'frames.png')
    labelled=[]
    for i,frame in enumerate(frames):
        canvas=Image.new('RGB',(512,330),'#101b2b');d=ImageDraw.Draw(canvas)
        d.text((10,8),'ACTUAL HOST MODEL OUTPUT / NOT ANDROID',font=font,fill='white')
        d.text((10,31),'Original numerical gates failed; quality unaccepted.',font=small,fill='#ffcfa4')
        canvas.paste(frame,(128,60));d.text((10,307),str(i)+' / 32',font=small,fill='white');labelled.append(canvas)
    labelled[0].save(out/'preview.gif',save_all=True,append_images=labelled[1:],duration=[40 if i%6 else 50 for i in range(count)],loop=0,disposal=2)
    current(before)
    files=[dict(file=name,bytes=(out/name).stat().st_size,sha256=sha(out/name)) for name in ['video.mp4','frames.png','preview.gif']]
    manifest=dict(schema='lma.ltx098-app-trained-media/1',version=version(),actual_production_java_native_host=True,
        model_inference=True,physical_android=False,numerical_accepted=False,quality_accepted=False,complete_release_accepted=False,
        host_encoder='ffmpeg_libx264_not_android',trained_report_sha256=sha(source),original_numerical_failures_preserved=True,
        baseline_bridge_files_byte_identical=7,original_video_preserved_byte_exact=True,files=files,input_fingerprint=before)
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(files=len(files),model_inference=True,physical_android=False,numerical_accepted=False,quality_accepted=False)))

if __name__=='__main__':main()
