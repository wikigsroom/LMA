"""Check actual DSH observations separately from SDK fixtures and agent quality."""
import hashlib,json
from evidence import ROOT,current,version

def check(directory):
    path=directory/'physical-dsh.json'
    if not path.exists():
        assert tuple(map(int,version().split('.'))) < (1,2,1), 'm04 repair requires actual DSH observations'
        return {}
    data=json.loads(path.read_text('utf8'));build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    assert data['schema']=='lma.physical-dsh/1' and data['version']==version()
    assert data['final_apk_sha256']==build['sha256'];current(data['input_fingerprint'])
    assert data['same_android_phone'] and data['model_id']=='m04' and data['context']==131072
    assert data['weight_sha256']=='7ed39ee0638e18d3e47bf12e60e917c792ca5332606a72bd1882ab1f62a13a7a'
    assert data['settings_preserved'] and not data['weights_downloaded'] and not data['external_agent_execution_substituted']
    template=data['native_template'];profile=json.loads((ROOT/'app/src/main/assets/chat-template-profiles.json').read_text('utf8'))['profiles'][0]
    assert template['state']=='native_template_verified' and template['toolDefinitionsRendered'] and template['toolParserReady']
    assert template['weightSha256']==data['weight_sha256'] and template['effectiveTemplateSha256']==profile['sha256']
    assert data['dsh_version']=='1.4.76' and data['dsh_version_code']==327
    assert data['attempts'] and any(a['apk_sha256']==build['sha256'] for a in data['attempts'])
    for attempt in data['attempts']:
        assert attempt['tool_count']==41 and len(attempt['tool_names'])==41 and attempt['input_tokens']>1000
        assert len(attempt['definitions_sha256'])==64 and attempt['model_id']=='m04'
        assert attempt['status'] in ['passed','failed','explicitly_cancelled']
    direct=data['direct_api'];assert direct['apk_sha256']==build['sha256'] and direct['not_dsh_execution']
    assert {c['case'] for c in direct['calls']}=={'auto','required','named','stream'}
    for case in direct['calls']:
        assert case['status']==200 and case['finish_reason']=='tool_calls'
        call=case['tool_call'];assert call['id'] and call['function']['name']=='lma_sum'
        assert json.loads(call['function']['arguments'])=={'a':17,'b':26}
    resume=direct['resume'];assert resume['status']==200 and resume['answer_uses_client_result']
    assert resume['tool_call_id']==next(c['tool_call']['id'] for c in direct['calls'] if c['case']=='named')
    negative=direct['invalid_strict_schema'];assert negative['status']==400 and negative['param']=='tools[0].function.parameters.type'
    controls=direct['context_controls'];assert {c['case'] for c in controls}=={'late_system','leading_system'}
    for case in controls:
        assert case['finish_reason']=='tool_calls' and case['tool_call']['id']
        assert case['tool_call']['function']['name']=='lma_sum' and json.loads(case['tool_call']['function']['arguments'])=={'a':17,'b':26}
    if data['tool_loop_passed']:
        calls=data['accepted_loop']['calls'];assert [c['name'] for c in calls]==['bash','write','read']
        ids=[c['id'] for c in calls];assert len(set(ids))==3 and all(c['result_returned'] for c in calls)
        assert data['accepted_loop']['independent_file_verified'] and data['accepted_loop']['answer_uses_read_result']
        result=data['accepted_loop']['file_content'];assert hashlib.sha256(result.encode()).hexdigest()==data['accepted_loop']['file_sha256']
    if data['plugin_installation_passed']:
        assert data['plugin']['executed_by_dsh'] and data['plugin']['exit_code']==0 and data['plugin']['call_id']
    media_path=ROOT/'docs/media/device'/('v'+version())/'manifest.json'
    media=json.loads(media_path.read_text('utf8'));current(media['input_fingerprint'])
    assert media['schema']=='lma.physical-runtime-media/1' and media['apk_sha256']==build['sha256'] and media['physical_device']
    for item in media['files']:
        path=media_path.parent/item['file'];assert path.parent==media_path.parent
        assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    final=[a for a in data['attempts'] if a['apk_sha256']==build['sha256']]
    completed=sum(a['server_delivery']=='validated' and a['finish_reason'] in ['stop','tool_calls','length'] for a in final)
    return dict(direct_api_model_requests=5+len(controls),direct_api_tool_modes_tested=True,
        dsh_final_apk_model_attempts=len(final),dsh_final_apk_completed_generations=completed,
        dsh_final_apk_successful_attempts=sum(a['status']=='passed' for a in final),
        dsh_app_tested=True,dsh_actual_requests=len(data['attempts']),dsh_full_tools_loop_passed=data['tool_loop_passed'],
        dsh_plugin_installation_passed=data['plugin_installation_passed'],dsh_model_quality_accepted=False,physical_runtime_media_tested=True)
