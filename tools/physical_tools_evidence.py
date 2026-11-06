"""Check selected phone tools/SDK evidence independently of program fixtures."""
import json
from evidence import ROOT, current, version


def check(directory):
    path = directory/'physical-tools.json'
    if not path.exists():
        assert tuple(map(int,version().split('.'))) < (1,1,0), 'Current tools release requires its selected physical probe'
        return dict(physical_tool_protocol_tested=False,physical_tool_protocol_checks=0,dsh_app_tested=False)
    data=json.loads(path.read_text('utf8'))
    build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    assert data['schema']=='lma.physical-tools/1' and data['status']=='passed'
    assert data['version']==version() and data['apk_sha256']==build['sha256']
    current(data['input_fingerprint'])
    assert data['passed']==len(data['checks']) and data['passed']>=20
    for field in ('phone_inference_tested','client_executed_tools','openai_sdk_tested','same_android_phone','settings_preserved','installed_assets_preserved'):assert data[field],field
    for field in ('dsh_app_tested','weights_downloaded','model_quality_accepted','background_endurance_tested','virtualization_used'):assert not data[field],field
    assert {m['case'] for m in data['measurements']}=={'named_strict_tool','tool_result_resume','streamed_strict_tool','two_concurrent_children','api_reload_after_unload'}
    queue=next(m for m in data['measurements'] if m['case']=='two_concurrent_children')
    assert queue['peak_admitted']>=2 and queue['health_max_seconds']<5
    assert data['requested_output_tokens']==192
    return dict(physical_tool_protocol_tested=True,physical_tool_protocol_checks=data['passed'],
        physical_tool_model_id=data['model_id'],physical_tool_model_requests=6,dsh_app_tested=False)
