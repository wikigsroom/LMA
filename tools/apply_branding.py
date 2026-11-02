"""Derive Android assets from approved Logo 21, preserving the source artwork."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from render_brand_banner import character_for_composition, SOURCE, SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    character = character_for_composition(Image.open(SOURCE))
    res = ROOT / 'app/src/main/res'
    outputs = {}
    # The entire approved silhouette fits inside the adaptive icon's 66dp safe circle.
    for density, size in [('mdpi',108),('hdpi',162),('xhdpi',216),('xxhdpi',324),('xxxhdpi',432)]:
        folder = res / ('mipmap-' + density); folder.mkdir(exist_ok=True)
        image = Image.new('RGBA', (size,size))
        thumb = character.copy(); thumb.thumbnail((round(size*.58),round(size*.58)),Image.Resampling.LANCZOS)
        image.alpha_composite(thumb,((size-thumb.width)//2,(size-thumb.height)//2))
        path = folder / 'ic_launcher_foreground.png'; image.save(path)
        outputs[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    target = ROOT / 'app/src/main/assets/lma-logo.png'
    target.write_bytes((ROOT/'docs/media/branding/lma-logo.png').read_bytes())
    manifest = {'schema':'lma.android-branding/1','logo':21,'sourceSha256':SOURCE_SHA256,
                'sloganZh':'把无审查 AI，装进口袋。','sloganEn':'Uncensored AI, right in your pocket.',
                'foregroundSafeFraction':.58,'assets':outputs}
    (ROOT/'docs/media/branding/android-icon.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Logo 21: adaptive launcher foregrounds and in-app logo generated')


if __name__ == '__main__': main()
