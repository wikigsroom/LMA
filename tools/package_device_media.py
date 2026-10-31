"""Package reviewed actual Android screen captures, separately from desktop fixtures."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def identity(path):
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', type=float, required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--reviewed', action='store_true', help='Confirm the selected interval contains only LMA and no visible credentials')
    args = parser.parse_args()
    assert args.reviewed and args.start >= 0 and 1 <= args.seconds <= 60
    source = ROOT/'build/device-tests/physical-media'
    report = json.loads((ROOT/'build/device-tests/device-results.json').read_text(encoding='utf-8'))
    build = json.loads((ROOT/'dist/build-info.json').read_text(encoding='utf-8'))
    assert report['status']=='passed' and report['apk_sha256']==build['sha256']
    assert report['instrumentation']['physicalDevice'] and not report['phone_inference_tested']
    current(report['input_fingerprint'])
    out = ROOT/'docs/media/device'/('v'+version())
    out.mkdir(parents=True, exist_ok=True)
    screenshots = ['01-recommended.png','02-all.png','03-local.png','04-chat.png',
                   '04-tasks.png','04-server.png','04-settings.png']
    for name in screenshots:
        shutil.copyfile(source/name, out/name)
    original = source/'physical-walkthrough.mp4'
    video = out/'physical-walkthrough.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss',str(args.start),
        '-i',str(original),'-t',str(args.seconds),'-vf','scale=540:-2','-an',
        '-c:v','libx264','-preset','fast','-crf','23','-movflags','+faststart',str(video)],check=True)
    gif = out/'physical-walkthrough.gif'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),
        '-filter_complex','fps=6,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer',
        '-loop','0',str(gif)],check=True)
    manifest = dict(schema='lma.physical-screen-media/1',version=version(),
        android_device=True,desktop_fixture=False,model_inference=False,weights_downloaded=False,
        apk_sha256=build['sha256'],device=report['device'],reviewed_app_only=True,
        input_fingerprint=report['input_fingerprint']|fingerprint('tools/package_device_media.py'),
        source_recording=identity(original),trim_start_seconds=args.start,
        trim_duration_seconds=args.seconds,playback_speed=1,
        screenshots=[dict(file=name,**identity(out/name)) for name in screenshots],
        files=[dict(file=path.name,**identity(path)) for path in [*(out/n for n in screenshots),video,gif]],
        checks=report['instrumentation']['checks']+report['external_program_checks'])
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(version=version(),screenshots=len(screenshots),actual_android_device=True,
        model_inference=False,files=len(manifest['files'])),ensure_ascii=False))


if __name__=='__main__':
    main()
