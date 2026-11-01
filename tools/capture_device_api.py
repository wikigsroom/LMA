"""Capture five privacy-reviewed physical LMA model/service pages, never chats/tasks.

Only native ADB navigation/screenrecord is used. No browser, emulator, UI fixture,
model downloads or generation. Unlock the already authorized phone first.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from evidence import ROOT, current, fingerprint, version


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serial',required=True);args=parser.parse_args()
    adb=str(Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe')
    output=ROOT/'docs/media/device'/('v'+version());output.mkdir(parents=True,exist_ok=True)
    def run(*a,binary=False,timeout=30):
        r=subprocess.run([adb,'-s',args.serial,*map(str,a)],capture_output=True,timeout=timeout)
        if r.returncode:raise RuntimeError('Physical media command failed')
        return r.stdout if binary else r.stdout.decode('utf8',errors='replace')
    if args.serial.startswith('emulator-') or run('shell','getprop','ro.kernel.qemu').strip()=='1':raise RuntimeError('Physical device required')
    apk=run('shell','pm','path','com.lma.app').strip().removeprefix('package:')
    actual=run('shell','sha256sum',apk).split()[0];build=json.loads((ROOT/'dist/build-info.json').read_text(encoding='utf8'));assert actual==build['sha256']
    inputs=fingerprint('tools/capture_device_api.py','app/src/main/assets/app.js','app/src/main/assets/app.css','app/src/main/assets/index.html')
    def ui():
        path='/sdcard/Download/LMA-media-ui.xml'
        try:
            run('shell','uiautomator','dump',path);text=run('shell','cat',path)
            assert not re.search(r'\blma_[a-f0-9]{48}\b',text),'Hide API key before media capture'
            return ET.fromstring(text[text.index('<?xml'):])
        finally:run('shell','rm','-f',path)
    def tap(text):
        nodes=[]
        for attempt in range(5):
            try:nodes=[n for n in ui().iter('node') if (n.get('text') or n.get('content-desc'))==text]
            except (ET.ParseError,ValueError):nodes=[]
            if nodes:break
            if attempt==0:run('shell','am','start','-W','-n','com.lma.app/.MainActivity')
            time.sleep(2)
        if not nodes:raise RuntimeError('Cannot locate safe navigation control: '+text)
        positions=[]
        for n in nodes:
            b=list(map(int,re.findall(r'\d+',n.get('bounds',''))));positions.append(((b[0]+b[2])//2,(b[1]+b[3])//2))
        x,y=max(positions,key=lambda p:p[1]);run('shell','input','tap',x,y);time.sleep(1)
    def top():
        for _ in range(3):run('shell','input','swipe','1000','650','1000','1800','200')
    screens=[]
    def capture(name):
        ui();time.sleep(1);data=run('exec-out','screencap','-p',binary=True)
        assert data.startswith(b'\x89PNG');(output/name).write_bytes(data);screens.append(dict(file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    run('shell','am','start','-W','-n','com.lma.app/.MainActivity');time.sleep(3);tap('模型库');tap('推荐');top()
    remote='/sdcard/Download/LMA-api-walkthrough.mp4'
    recorder=subprocess.Popen([adb,'-s',args.serial,'shell','screenrecord','--time-limit','60','--bit-rate','2000000',remote],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        capture('01-recommended.png')
        for _ in range(2):run('shell','input','swipe','1000','1850','1000','700','350')
        capture('02-multimodal-recommendations.png');top();tap('本地');top();capture('03-local-models.png')
        tap('服务');top();capture('04-api-overview.png')
        run('shell','input','swipe','1000','1850','1000','700','350');capture('05-published-models.png')
        recorder.wait(timeout=70)
        raw=ROOT/'build/device-tests/api-walkthrough-original.mp4';run('pull',remote,raw,timeout=40)
        ffmpeg=shutil.which('ffmpeg');assert ffmpeg
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(raw),'-an','-c:v','libx264','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'physical-walkthrough.mp4')],check=True,timeout=90)
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(output/'physical-walkthrough.mp4'),'-vf','fps=5,scale=300:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(output/'physical-walkthrough.gif')],check=True,timeout=90)
        current(inputs)
        files=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(output.iterdir()) if p.suffix in ('.png','.mp4','.gif')]
        manifest=dict(schema='lma.physical-api-media/1',version=version(),apk_sha256=actual,android_device=True,desktop_fixture=False,model_inference=False,weights_downloaded=False,
            reviewed_app_only=False,playback_speed=1,screenshots=screens,files=files,input_fingerprint=inputs,
            privacy_scope='Only Recommended, Local and Service pages; no personal chat, task history or logs. API key hidden before each capture.',browser_used=False,browser_closed=True)
        (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(json.dumps(dict(screenshots=len(screens),files=len(files),needs_visual_review=True)))
    finally:
        if recorder.poll() is None:recorder.terminate();recorder.wait(timeout=10)
        run('shell','rm','-f',remote)


if __name__=='__main__':main()
