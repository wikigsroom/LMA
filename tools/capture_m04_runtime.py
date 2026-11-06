"""Record only LMA's runtime/API controls on an authorized phone; never unload or inspect chats."""
import argparse,hashlib,json,os,re,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
from evidence import ROOT,fingerprint,version

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serial',required=True);args=parser.parse_args()
    adb=str(Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe');base=[adb,'-s',args.serial]
    out=ROOT/'docs/media/device'/('v'+version());out.mkdir(parents=True,exist_ok=True)
    private=ROOT/'build/m04-repair-private';private.mkdir(exist_ok=True)
    def command(*items):return subprocess.run(base+list(items),capture_output=True,check=True,timeout=30).stdout
    def ui():
        command('shell','uiautomator','dump','/sdcard/lma-runtime-capture.xml')
        return ET.fromstring(command('shell','cat','/sdcard/lma-runtime-capture.xml'))
    def tap(label):
        for n in ui().iter('node'):
            if label in [n.attrib.get('content-desc'),n.attrib.get('text')]:
                a=list(map(int,re.findall(r'\d+',n.attrib['bounds'])))
                command('shell','input','tap',str((a[0]+a[2])//2),str((a[1]+a[3])//2));return
        raise RuntimeError('Required runtime UI control absent: '+label)
    def capture(name):
        from PIL import Image
        import io
        body=command('exec-out','screencap','-p');image=Image.open(io.BytesIO(body))
        image.crop((0,96,image.width,image.height-300)).save(out/name)
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    installed=command('shell','pm','path','com.lma.app').decode().strip().removeprefix('package:')
    assert command('shell','sha256sum',installed).decode().split()[0]==build['sha256']
    command('shell','am','start','-n','com.lma.app/.MainActivity')
    try:tap('关闭')
    except RuntimeError:pass
    tap('API 服务')
    for _ in range(5):command('shell','input','swipe','800','500','800','1900','100')
    capture('m04-runtime.png')
    remote='/sdcard/lma-m04-runtime.mp4'
    recording=subprocess.Popen(base+['shell','screenrecord','--size','720x1560','--bit-rate','1500000','--time-limit','12',remote],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        tap('运行管理');time.sleep(1);capture('m04-runtime-manager.png')
        recording.wait(timeout=20)
        command('pull',remote,str(private/'runtime-raw.mp4'))
    finally:
        if recording.poll() is None:recording.terminate();recording.wait(timeout=5)
        command('shell','rm','-f',remote,'/sdcard/lma-runtime-capture.xml')
        command('shell','am','start','-n','app.dsh.mobile/.MainActivity')
    for output,extra in [('runtime-controls.mp4',['-vf','crop=iw:ih-288:0:64','-c:v','libx264','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart']),('runtime-controls.gif',['-vf','crop=iw:ih-288:0:64,fps=4,scale=300:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0'])]:
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(private/'runtime-raw.mp4'),'-an',*extra,str(out/output)],check=True)
    files=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.suffix in ['.png','.mp4','.gif']]
    manifest=dict(schema='lma.physical-runtime-media/1',version=version(),apk_sha256=build['sha256'],physical_device=True,
        source='tools/capture_m04_runtime.py',status_bar_and_navigation_cropped=True,model_id='m04',background_request_may_be_active=True,
        scope='Actual API/runtime controls only; no Unload confirmation or personal chat capture; recording is not agent acceptance',
        files=files,input_fingerprint=fingerprint('tools/capture_m04_runtime.py','app/src/main/assets/app.js','app/src/main/assets/app.css'))
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(physical_media=len(files),apk_sha256=build['sha256'],unload_invoked=False)))

if __name__=='__main__':main()
