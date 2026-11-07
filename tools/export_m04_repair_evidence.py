"""Whitelist actual m04/DSH observations; never export raw snapshots or credentials."""
import argparse,json
from pathlib import Path
from evidence import ROOT,fingerprint,version


def public_error(error):
    # Native failures can quote generated text; keep private prompts and paths out
    # of release records. The code/type/parameter still identify the failure.
    if error is None:return None
    return {k:error[k] for k in ['code','type','param'] if k in error}

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
            finish_reason=trace.get('finishReason'),error_code=trace.get('errorCode'),note=a['note'],
            rounds=[dict(input_tokens=r['inputTokens'],tool_count=r['toolCount'],definitions_sha256=r['toolDefinitionsSha256'],
                tool_choice=r['toolChoice'],stream=r['stream'],server_delivery=r['delivery'],finish_reason=r.get('finishReason'),
                calls=r.get('calls',[]),result_ids=r.get('toolResultIds',[]),error_code=r.get('errorCode')) for r in a.get('rounds',[])]))
    for source, target in zip(private['attempts'], attempts):
        if 'native_output_diagnostic' in source:
            target['native_output_diagnostic']={k:source['native_output_diagnostic'][k] for k in
                ['source','raw_content_sha256','native_function_name','complete_argument_object',
                 'unexpected_outer_fields','arguments_rewritten','commands_executed']}
    raw=private['direct_api'];direct=dict(apk_sha256=raw['apk_sha256'],not_dsh_execution=True,calls=[])
    for case in raw['calls']:
        call=case['tool_call'];function=call['function']
        direct['calls'].append(dict(case=case['case'],status=case['status'],seconds=case['seconds'],finish_reason=case['finish_reason'],
            tool_call=dict(id=call['id'],type=call['type'],function=dict(name=function['name'],arguments=function['arguments']))))
    direct['resume']={k:raw['resume'][k] for k in ['status','tool_call_id','client_result','answer','answer_uses_client_result']}
    direct['invalid_strict_schema']={k:raw['invalid_strict_schema'][k] for k in ['status','param','scope']}
    direct['context_controls']=[{k:c[k] for k in ['case','seconds','roles','input_tokens','finish_reason','tool_call']}
        for c in raw['context_controls']]
    if 'schema_admission_observation' in raw:
        direct['schema_admission_observation']={k:raw['schema_admission_observation'][k] for k in
            ['case','apk_sha256','status','http_status_captured','seconds','original_test_expected_status','test_expectation_corrected',
             'schema_root_type','observed_rejection_stage','error','executable_tool_fragments','commands_executed','scope']}
    if 'strict_output_controls' in raw:
        direct['strict_output_controls']=[{k:c[k] for k in ['case','apk_sha256','status','seconds',
            'expected_failure_observed','rejection_stage','error','executable_tool_fragments','success_done_sent',
            'commands_executed','strict_schema','requested_value']} for c in raw['strict_output_controls']]
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
            'Plugin presentation requires actual post-reload evidence; source review or an installation request is insufficient',
            'The accepted web pet does not establish Android system-overlay bridging, wallet/payment or voice features',
            'Accepted guided calls and DSH-owned installation do not establish arbitrary unguided 1B-model agent reliability'],
        input_fingerprint=fingerprint('tools/export_m04_repair_evidence.py','tools/physical_dsh_evidence.py',
            'tools/build_llama_chat_runtime.py','native/chat-runtime','third_party/runtime-lock.json',
            'third_party/patches/0002-bare-json-parallel-tools.patch','tools/device_native_template_probe.py',
            'app/src/main/java/com/lma/app/ApiHost.java','app/src/main/java/com/lma/app/TemplateProfiles.java',
            'app/src/main/java/com/lma/app/core','app/src/main/assets/chat-template-profiles.json','app/src/main/assets/chat-templates'))
    if private['tool_loop_passed']:report['accepted_loop']=private['accepted_loop']
    if private['plugin_installation_passed']:report['plugin']=private['plugin']
    if tuple(map(int,version().split('.'))) >= (1,2,2):
        from build_llama_chat_runtime import verify_patch_record
        report['native_runtime_patch']=verify_patch_record()
        followup=private['full_context_followup']
        report['full_context_followup']={k:followup[k] for k in ['profile','effective_template_sha256',
            'input_tokens','original_message_count','normalized_request_messages_preserved','all_message_contents_present',
            'background_before_pending_task','all_tools_preserved','tool_choice_preserved',
            'positional_metadata','native_schema_controls','bos_controls','name_controls']}
        report['full_context_followup']['historical_controls']=[{k:c[k] for k in
            ['case','apk_sha256','status','input_tokens','seconds','finish_reason','tool_call_count','note']}
            for c in followup['historical_controls']]
        if 'historical_native_format_controls' in followup:
            report['full_context_followup']['historical_native_format_controls']=[{k:c[k] for k in
                ['case','apk_sha256','status','seconds','started_at','tool_count','original_message_count',
                 'all_tools_preserved','all_message_contents_preserved','native_endpoint',
                 'not_public_gateway_acceptance','not_dsh_execution','commands_executed',
                 'diagnostic_output_ceiling','temperature','seed','grammar_enabled','input_tokens',
                 'prompt_sha256','raw_content_sha256','raw_content_chars','xml_marker_observed',
                 'raw_named_objects','stop_type','tokens_predicted','tokens_evaluated','tokens_cached',
                 'timings','settings_changed']} for c in followup['historical_native_format_controls']]
        if 'observed_envelope_replay' in followup:
            report['full_context_followup']['observed_envelope_replay']={k:followup['observed_envelope_replay'][k] for k in
                ['actual_observed_output_replayed','observed_apk_sha256','native_host_parser_rebuilt',
                 'native_binary_sha256','raw_content_sha256','complete_arguments_preserved',
                 'function_name','external_execution','model_inference']}
        if 'physical_timing' in followup:
            report['full_context_followup']['physical_timing']={k:followup['physical_timing'][k] for k in
                ['prompt_tokens','sampling_interval_seconds','first_decode_elapsed_lower_seconds',
                 'first_decode_elapsed_upper_seconds','retry_cached_input_tokens','scope']}
        if 'resource_observation' in followup:
            observation=followup['resource_observation']
            report['full_context_followup']['resource_observation']={k:observation[k] for k in
                ['apk_sha256','sampled_at','scope','model','saved_context','native_process','parameters_changed']}
        if 'health_observation' in followup:
            report['full_context_followup']['health_observation']={k:followup['health_observation'][k] for k in
                ['apk_sha256','sampled_at','scope','samples','health_min_ms','health_median_ms',
                 'health_max_ms','actual_active_text_requests','model_inference_triggered']}
        report['full_context_followup']['api_mode_controls']=[{**{k:c[k] for k in
            ['case','apk_sha256','status','seconds','tool_count','full_context_preserved','tool_definitions_preserved',
             'requested_max_tokens','temperature','finish_reason','protocol_delivered_call','calls','usage','error',
             'not_dsh_execution','commands_executed']},'error':public_error(c['error'])} for c in followup['api_mode_controls']]
    out=ROOT/('verification/releases/v'+version());out.mkdir(parents=True,exist_ok=True)
    (out/'physical-dsh.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    from physical_dsh_evidence import check
    print(json.dumps(check(out)))

if __name__=='__main__':main()
