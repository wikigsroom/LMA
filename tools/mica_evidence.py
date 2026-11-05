"""Version-bound UI10 evidence; browser fixtures and actual phone remain distinct."""
import json
from pathlib import Path
from evidence import ROOT, current, version


def check():
    if tuple(map(int,version().split('.')))<(1,0,0):return {}
    program=json.loads((ROOT/'build/mica-ui/results.json').read_text('utf8'))
    current(program['input_fingerprint'])
    assert program['version']==version() and program['passed']>=20 and len(program['matrix'])==520
    assert program['browser_closed'] and not program['physicalDevice']
    physical=json.loads((ROOT/('verification/releases/v'+version()+'/mica-physical-ui.json')).read_text('utf8'))
    current(physical['input_fingerprint'])
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    assert physical['version']==version() and physical['apk_sha256']==build['sha256']
    assert physical['status']=='passed' and physical['physicalDevice'] and physical['passed']>=34
    assert not physical['modelInference'] and not physical['weightsDownloaded']
    for key in ('installed_assets_preserved','user_preferences_preserved','history_preserved'):assert physical[key],key
    fonts=json.loads((ROOT/('verification/releases/v'+version()+'/mica-fonts.json')).read_text('utf8'))
    current(fonts['input_fingerprint'])
    assert fonts['apk_sha256']==build['sha256'] and fonts['restored']
    assert {r['font_scale'] for r in fonts['runs']}=={1.3,1.5,2.0}
    assert all(r['status']=='passed' for r in fonts['runs'])
    return dict(mica_ui_implemented=True,mica_program_layouts=520,mica_physical_ui_checks=physical['passed'],mica_physical_font_scales=[1.3,1.5,2.0])


if __name__=='__main__':print(json.dumps(check()))
