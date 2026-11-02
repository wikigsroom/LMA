"""Capture UI10 from the exact installed APK. No browser, mock bridge or inference."""
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, time
from pathlib import Path
from evidence import ROOT, fingerprint, version


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--baseline',type=Path,required=True,help='Private pre-upgrade UI baseline')
    args=parser.parse_args()
    adb=Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe'
    private=ROOT/'build/mica-v100';private.mkdir(parents=True,exist_ok=True)
    output=ROOT/'docs/media/device'/('v'+version());output.mkdir(parents=True,exist_ok=True)
    def run(*a,timeout=60):
        p=subprocess.run([str(adb),'-s',args.serial,*map(str,a)],capture_output=True,timeout=timeout)
        if p.returncode:raise RuntimeError('Owned physical UI operation failed')
        return p.stdout.decode('utf8',errors='replace')
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    apk=run('shell','pm','path','com.lma.app').strip().removeprefix('package:')
    assert run('shell','sha256sum',apk).split()[0]==build['sha256']
    assert run('shell','getprop','ro.kernel.qemu').strip()!='1'
    run('shell','input','keyevent','224');run('shell','cmd','statusbar','collapse');run('shell','am','start','-W','-n','com.lma.app/.MainActivity');time.sleep(1)
    font=float(run('shell','settings','get','system','font_scale').strip() or '1')
    remote='/sdcard/Download/LMA-mica-v100-owned.mp4'
    recorder=subprocess.Popen([str(adb),'-s',args.serial,'shell','screenrecord','--time-limit','55','--bit-rate','8000000',remote],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        raw=run('shell','am','instrument','-w','-e','mode','capture','com.lma.app.acceptance/com.lma.app.DeviceUiProbe',timeout=180)
        (private/'capture-private.txt').write_text(raw,'utf8')
        match=re.search(r'lma_ui=(\{[^\r\n]+\})',raw);assert match,'Missing native UI report'
        data=json.loads(match.group(1));assert data['status']=='passed',data.get('error')
        recorder.wait(timeout=60)
        baseline=json.loads(args.baseline.read_text('utf8'))['before']
        final=data['after']
        asset_fields=('models','bundles')
        preserved=all(sorted(baseline[k],key=lambda r:r['id'])==sorted(final[k],key=lambda r:r['id']) for k in asset_fields)
        assert preserved,'Existing installed assets changed'
        for item in data['screenshots']:
            run('pull','/sdcard/Android/data/com.lma.app/files/lma-ui-v100/'+item['file'],output/item['file'])
        original=private/'screenrecord-private.mp4';run('pull',remote,original)
        ffmpeg=shutil.which('ffmpeg');assert ffmpeg
        rect=dict(data['screenshots'][0]);rect['width']=rect['width']//2*2;rect['height']=rect['height']//2*2
        # Keep the portrait tour before the keyboard/rotation checks. OS chrome is cropped.
        movie=output/'physical-walkthrough.mp4'
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(original),'-ss','1','-t','20','-vf',f"crop={rect['width']}:{rect['height']}:{rect['x']}:{rect['y']}",'-an','-c:v','libx264','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)],check=True,timeout=120)
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(movie),'-vf','fps=5,scale=300:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(output/'physical-walkthrough.gif')],check=True,timeout=120)
        def identity(p):return dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        inputs=fingerprint('tools/capture_mica_device.py','tests/android/com/lma/app/DeviceUiProbe.java','app/src/main/java/com/lma/app/MainActivity.java','app/src/main/assets/mica.css','app/src/main/assets/mica.js','app/src/main/assets/app.js','app/src/main/assets/index.html')
        manifest=dict(schema='lma.physical-mica-media/1',version=version(),apk_sha256=build['sha256'],android_device=True,desktop_fixture=False,model_inference=False,weights_downloaded=False,
            reviewed_app_only=False,playback_speed=1,browser_used=False,browser_closed=True,recording_seconds=20,
            screenshots=[identity(output/i['file']) for i in data['screenshots']],files=[identity(p) for p in sorted(output.iterdir()) if p.suffix in ('.png','.mp4','.gif')],input_fingerprint=inputs,
            privacy_scope='Actual app area; empty new conversation; explicit task search hides personal jobs; no deletion of history or installed assets. API credential fields stay masked. Manual visual review required.')
        (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
        result=dict(schema='lma.mica-physical-ui/1',version=version(),apk_sha256=build['sha256'],status='passed',physicalDevice=True,modelInference=False,weightsDownloaded=False,
            checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),device=dict(model=run('shell','getprop','ro.product.model').strip(),android=run('shell','getprop','ro.build.version.release').strip()),
            passed=len(data['checks']),checks=data['checks'],font_scale=font,installed_assets_preserved=preserved,installed_model_count=len(final['models']),installed_bundle_count=len(final['bundles']),
            user_preferences_preserved=baseline['preferences']==final['preferences'],history_preserved=final['sessions']>=baseline['sessions'],media='docs/media/device/v'+version()+'/manifest.json',input_fingerprint=inputs,
            limits=['Single physical slab phone; no physical hinge or tablet','No full TalkBack listening pass','No new trained-model, codec quality or endurance acceptance'])
        dest=ROOT/'verification/releases'/('v'+version());dest.mkdir(parents=True,exist_ok=True)
        (dest/'mica-physical-ui.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
        print(json.dumps(dict(passed=result['passed'],screenshots=len(data['screenshots']),installed_assets_preserved=preserved,needs_visual_review=True)))
    finally:
        if recorder.poll() is None:recorder.terminate();recorder.wait(timeout=10)
        run('shell','rm','-f',remote)


if __name__=='__main__':main()
