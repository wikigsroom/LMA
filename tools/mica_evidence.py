"""Version-bound UI evidence; program fixtures and actual phone remain distinct."""
import json
from pathlib import Path
from evidence import ROOT, current, version


def check():
    if tuple(map(int,version().split('.')))<(1,0,0):return {}
    program=json.loads((ROOT/'build/mica-ui/results.json').read_text('utf8'))
    current(program['input_fingerprint'])
    assert program['version']==version() and program['passed']>=20 and len(program['matrix'])==520
    assert program['browser_closed'] and not program['physicalDevice']
    if tuple(map(int,version().split('.'))) >= (1,2,0):
        workspace=json.loads((ROOT/'build/workspace-ui/results.json').read_text('utf8'))
        current(workspace['input_fingerprint'])
        assert workspace['version']==version() and workspace['passed']>=29
        assert workspace['browser_closed'] and not workspace['physicalDevice']
        assert not workspace['modelInference'] and not workspace['weightsDownloaded']
        media=json.loads((ROOT/('docs/media/workspace-v'+version()+'/manifest.json')).read_text('utf8'))
        current(media['input_fingerprint'])
        assert media['version']==version() and media['program_fixture'] and not media['physical_device']
        assert len(media['files'])>=14 and len(workspace['captures'])>=12
        import hashlib
        for item in media['files']:
            path=ROOT/('docs/media/workspace-v'+version())/item['file']
            assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
        return dict(workspace_ui_implemented=True,workspace_program_checks=workspace['passed'],
                    mica_program_layouts=520,mica_physical_ui_checks=0,mica_physical_font_scales=[],
                    current_ui_phone_acceptance=False,phone_deferral_reason='Shared phone occupied by another task; user requested code/program review first')
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
