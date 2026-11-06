"""Export labelled production-page media and theme checks without using a phone."""
import hashlib
import json
import shutil
import subprocess
from evidence import ROOT, current, fingerprint, version


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    report=read(ROOT/'build/workspace-ui/results.json')
    current(report['input_fingerprint'])
    assert report['version']==version() and report['passed']>=29 and report['browser_closed']
    assert not any(report[k] for k in ('physicalDevice','modelInference','weightsDownloaded'))
    tokens=read(ROOT/'docs/design/tokens.json')
    def luminance(value):
        values=[int(value[n:n+2],16)/255 for n in (1,3,5)]
        values=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in values]
        return sum(x*w for x,w in zip(values,(.2126,.7152,.0722)))
    pairs=[]
    for theme,colors in tokens['themes'].items():
        for pair in tokens['contrast']['pairs']:
            a,b=sorted((luminance(colors[pair['foreground']]),luminance(colors[pair['background']])))
            ratio=(b+.05)/(a+.05)
            assert ratio>=pair['minimum'],(theme,pair,ratio)
            pairs.append(dict(theme=theme,**pair,ratio=round(ratio,3),passed=True))
    media=ROOT/('docs/media/workspace-v'+version())
    executable=shutil.which('ffmpeg')
    assert executable,'Native FFmpeg is required to encode the program recording'
    video=ROOT/'build/workspace-ui/workspace-demo.webm'
    subprocess.run([executable,'-hide_banner','-loglevel','error','-y','-i',str(video),'-an','-c:v','libx264','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(media/'walkthrough.mp4')],check=True)
    subprocess.run([executable,'-hide_banner','-loglevel','error','-y','-i',str(media/'walkthrough.mp4'),'-vf','fps=5,scale=300:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(media/'walkthrough.gif')],check=True)
    files=[dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(media.iterdir()) if p.suffix in ('.png','.gif','.mp4')]
    manifest=dict(schema='lma.workspace-program-media/1',version=version(),program_fixture=True,physical_device=False,model_inference=False,weights_downloaded=False,
                  source='tests/workspace-ui.cjs',reference='docs/design/workspace-decision.json',browser_closed=True,files=files,
                  input_fingerprint=report['input_fingerprint']|fingerprint('tools/workspace_evidence.py'))
    (media/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    result=dict(schema='lma.workspace-theme-contrast/1',version=version(),passed=len(pairs),pairs=pairs,physical_device=False,input_fingerprint=fingerprint('tools/workspace_evidence.py','docs/design/tokens.json'))
    (ROOT/'docs/design/workspace-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(media=len(files),contrast_pairs=len(pairs),program_checks=report['passed'],physical_device=False)))


if __name__=='__main__':
    main()
