"""Trim the provisional owned recording, then mark only visually reviewed app media.

Capture output stays unreviewed until the operator inspects screenshots and the
complete clip/contact sheet. Original recordings and instrumentation output stay
in ignored build storage; they may contain the user's previous page.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from evidence import ROOT, fingerprint, current, version


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start-seconds',type=float,default=5)
    p.add_argument('--duration-seconds',type=float,default=20)
    p.add_argument('--mark-reviewed',action='store_true',help='Only after actual visual review of every public image and the trimmed clip')
    args=p.parse_args()
    output=ROOT/'docs/media/device'/('v'+version())
    manifest=json.loads((output/'manifest.json').read_text('utf8'))
    current(manifest['input_fingerprint'])
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    assert manifest['apk_sha256']==build['sha256']
    if not args.mark_reviewed:
        assert 0<=args.start_seconds<=40 and 6<=args.duration_seconds<=30
        private=ROOT/('build/mica-v'+version().replace('.',''))
        match=re.search(r'lma_ui=(\{[^\r\n]+\})',(private/'capture-private.txt').read_text('utf8'))
        native=json.loads(match.group(1));rect=native['screenshots'][0]
        crop=f"crop={rect['width']//2*2}:{rect['height']//2*2}:{rect['x']}:{rect['y']}"
        ffmpeg=shutil.which('ffmpeg');assert ffmpeg
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(private/'screenrecord-private.mp4'),
            '-ss',str(args.start_seconds),'-t',str(args.duration_seconds),'-vf',crop,'-an','-c:v','libx264','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'physical-walkthrough.mp4')],check=True,timeout=120)
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(output/'physical-walkthrough.mp4'),
            '-vf','fps=5,scale=300:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
            '-loop','0',str(output/'physical-walkthrough.gif')],check=True,timeout=120)
        manifest.update(reviewed_app_only=False,recording_seconds=args.duration_seconds,source_trim_start_seconds=args.start_seconds,
            privacy_scope='Real app only after initial page/history transition is trimmed; empty new chat and explicit test-task search. Credential fields masked. All public images and trimmed clip require visual review.')
    else:
        assert manifest.get('source_trim_start_seconds',0)>=args.start_seconds,'Trim the initial private transition before review'
        manifest['reviewed_app_only']=True
    def identity(path):
        return dict(file=path.name,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest['screenshots']=[identity(output/item['file']) for item in manifest['screenshots']]
    manifest['files']=[identity(path) for path in sorted(output.iterdir()) if path.suffix in ('.png','.mp4','.gif')]
    manifest['input_fingerprint'].update(fingerprint('tools/finalize_mica_media.py'))
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(reviewed_app_only=manifest['reviewed_app_only'],screenshots=len(manifest['screenshots']),recording_seconds=manifest['recording_seconds'])))


if __name__=='__main__':main()
