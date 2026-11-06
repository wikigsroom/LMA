"""Whitelist actual m04/DSH observations; never export raw snapshots or credentials."""
import argparse,json
from pathlib import Path
from evidence import ROOT,fingerprint,version

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--observations',required=True);args=parser.parse_args()
    private=json.loads(Path(args.observations).read_text('utf8'));build=json.loads((ROOT/'dist/build-info.json').read_text('utf8'))
    assert private['final_apk_sha256']==build['sha256'] and private['settings_preserved']
    attempts=[]
    for a in private['attempts']:
        assert a['status'] in ['passed','failed','explicitly_cancelled'], 'Do not export an unfinished task as an accepted observation'
        trace=a['trace'];assert trace['toolCount']==41
        attempts.append(dict(case=a['case'],apk_sha256=a['apk_sha256'],model_id=trace['model'],tool_count=trace['toolCount'],
            tool_names=trace['toolNames'],definitions_sha256=trace['toolDefinitionsSha256'],input_tokens=trace['inputTokens'],
            tool_choice=trace['toolChoice'],stream=trace['stream'],status=a['status'],observation_seconds=a['seconds'],
            calls=trace.get('calls',[]),result_ids=trace.get('toolResultIds',[]),server_delivery=trace['delivery'],
            finish_reason=trace.get('finishReason'),error_code=trace.get('errorCode'),note=a['note']))
    raw=private['direct_api'];direct=dict(apk_sha256=raw['apk_sha256'],not_dsh_execution=True,calls=[])
    for case in raw['calls']:
        call=case['tool_call'];function=call['function']
        direct['calls'].append(dict(case=case['case'],status=case['status'],seconds=case['seconds'],finish_reason=case['finish_reason'],
            tool_call=dict(id=call['id'],type=call['type'],function=dict(name=function['name'],arguments=function['arguments']))))
    direct['resume']={k:raw['resume'][k] for k in ['status','tool_call_id','client_result','answer','answer_uses_client_result']}
    direct['invalid_strict_schema']={k:raw['invalid_strict_schema'][k] for k in ['status','param','scope']}
    direct['context_controls']=[{k:c[k] for k in ['case','seconds','roles','input_tokens','finish_reason','tool_call']}
        for c in raw['context_controls']]
    report=dict(schema='lma.physical-dsh/1',version=version(),final_apk_sha256=build['sha256'],
        device=dict(model='motorola edge plus',android='12'),dsh_version='1.4.76',dsh_version_code=327,
        model_id='m04',context=131072,weight_sha256=private['weight_sha256'],
        saved_parameters={k:private['saved_parameters'][k] for k in ['context','maxTokens','temperature','threads','reasoning']},
        same_android_phone=True,settings_preserved=True,weights_downloaded=False,external_agent_execution_substituted=False,
        tool_loop_passed=private['tool_loop_passed'],plugin_installation_passed=private['plugin_installation_passed'],
        attempts=attempts,model_quality_accepted=False,background_endurance_tested=False,
        native_template=private['native_template'],independent_file=private['independent_file'],
        direct_api=direct,
        earlier_unbound_trials=[{k:a[k] for k in ['case','status','tool_count','input_tokens','observation_seconds','note']}
            for a in private.get('earlier_unbound_trials',[])],
        limits=['Actual DSH observations are separate from the six SDK arithmetic generations',
            'Cancelled or unfinished computation is not proof that the model lacks tool ability',
            'No external command/file/plugin installation is substituted for DSH execution',
            'Plugin Android presentation is not established by source review or an installation request'],
        input_fingerprint=fingerprint('tools/export_m04_repair_evidence.py','tools/physical_dsh_evidence.py',
            'app/src/main/java/com/lma/app/ApiHost.java','app/src/main/java/com/lma/app/TemplateProfiles.java',
            'app/src/main/java/com/lma/app/core','app/src/main/assets/chat-template-profiles.json','app/src/main/assets/chat-templates'))
    if private['tool_loop_passed']:report['accepted_loop']=private['accepted_loop']
    if private['plugin_installation_passed']:report['plugin']=private['plugin']
    out=ROOT/('verification/releases/v'+version());out.mkdir(parents=True,exist_ok=True)
    (out/'physical-dsh.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    from physical_dsh_evidence import check
    print(json.dumps(check(out)))

if __name__=='__main__':main()
