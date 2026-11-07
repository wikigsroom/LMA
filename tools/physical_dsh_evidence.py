"""Check actual DSH observations separately from SDK fixtures and agent quality."""
import hashlib,json,re
from pathlib import Path
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
        if 'native_output_diagnostic' in attempt:
            diagnostic=attempt['native_output_diagnostic']
            assert attempt['apk_sha256']==build['sha256'] and attempt['status']=='failed'
            assert attempt['error_code']=='invalid_model_output' and len(diagnostic['raw_content_sha256'])==64
            assert diagnostic['native_function_name']=='bash' and diagnostic['complete_argument_object']
            assert diagnostic['unexpected_outer_fields']==['timeoutMs']
            assert diagnostic['arguments_rewritten'] is False and diagnostic['commands_executed'] is False
        for round in attempt.get('rounds',[]):
            assert round['tool_count']==41 and round['definitions_sha256']==attempt['definitions_sha256']
            assert round['input_tokens']>1000 and round['tool_choice']=='auto' and round['stream']
    direct=data['direct_api'];assert direct['apk_sha256']==build['sha256'] and direct['not_dsh_execution']
    assert {c['case'] for c in direct['calls']}=={'auto','required','named','stream'}
    for case in direct['calls']:
        assert case['status']==200 and case['finish_reason']=='tool_calls'
        call=case['tool_call'];assert call['id'] and call['function']['name']=='lma_sum'
        assert json.loads(call['function']['arguments'])=={'a':17,'b':26}
    resume=direct['resume'];assert resume['status']==200 and resume['answer_uses_client_result']
    assert resume['tool_call_id']==next(c['tool_call']['id'] for c in direct['calls'] if c['case']=='named')
    negative=direct['invalid_strict_schema'];assert negative['status']==400 and negative['param']=='tools[0].function.parameters.type'
    array_observation=direct.get('schema_admission_observation')
    if array_observation:
        assert array_observation['apk_sha256']==build['sha256'] and array_observation['http_status_captured']
        assert array_observation['original_test_expected_status']==400 and array_observation['test_expectation_corrected']
        assert array_observation['schema_root_type']=='array' and array_observation['status']==502
        assert array_observation['observed_rejection_stage']=='strict_function_schema'
        assert array_observation['error']['code']=='invalid_model_output'
        assert array_observation['executable_tool_fragments']==0 and not array_observation['commands_executed']
    output_controls=direct.get('strict_output_controls',[])
    if output_controls:
        assert {c['case'] for c in output_controls}=={'nonstream','stream'}
        for case in output_controls:
            assert case['apk_sha256']==build['sha256'] and case['commands_executed'] is False
            assert isinstance(case['expected_failure_observed'],bool)
            assert case['strict_schema']['properties']['value']['format']=='email'
            assert case['requested_value']=='not-an-email'
            if case['expected_failure_observed']:
                assert case['rejection_stage']=='strict_function_schema'
                assert case['status']==(200 if case['case']=='stream' else 502)
                assert case['error']['code']=='invalid_model_output'
                assert case['executable_tool_fragments']==0 and not case['success_done_sent']
    controls=direct['context_controls'];assert {c['case'] for c in controls}=={'late_system','leading_system'}
    for case in controls:
        assert case['finish_reason']=='tool_calls' and case['tool_call']['id']
        assert case['tool_call']['function']['name']=='lma_sum' and json.loads(case['tool_call']['function']['arguments'])=={'a':17,'b':26}
    if data['tool_loop_passed']:
        calls=data['accepted_loop']['calls'];assert [c['name'] for c in calls]==['bash','write','read']
        ids=[c['id'] for c in calls];assert len(set(ids))==3 and all(c['result_returned'] for c in calls)
        assert data['accepted_loop']['independent_file_verified'] and data['accepted_loop']['answer_uses_read_result']
        result=data['accepted_loop']['file_content'];assert hashlib.sha256(result.encode()).hexdigest()==data['accepted_loop']['file_sha256']
        if tuple(map(int,version().split('.'))) >= (1,2,2):
            loop=data['accepted_loop'];assert loop['apk_sha256']==build['sha256'] and loop['tool_count']==41
            assert isinstance(loop['guided_stepwise'],bool), 'Disclose whether the actual task used stepwise format guidance'
            assert result.strip() and result.strip() in loop['answer_excerpt']
            assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',result.strip())
            assert loop['independent_verification']=='adb_read_only'
            assert json.loads(calls[0]['arguments_json'])['command']=='cat /proc/sys/kernel/random/uuid'
            write_arguments=json.loads(calls[1]['arguments_json']);read_arguments=json.loads(calls[2]['arguments_json'])
            assert write_arguments['file_path']==read_arguments['file_path']==loop['owned_test_path']
            assert write_arguments['content'].strip()==calls[0]['result_text'].strip()==result.strip()
            assert result.strip() in calls[2]['result_text']
            media_path=ROOT/loop['media_manifest'];assert media_path==ROOT/'docs/media/device'/('v'+version())/'dsh-loop/manifest.json'
            loop_media=json.loads(media_path.read_text('utf8'))
            assert loop_media['schema']=='lma.physical-dsh-loop-media/1' and loop_media['version']==version()
            assert loop_media['apk_sha256']==build['sha256'] and loop_media['physical_device']
            assert loop_media['guided_stepwise'] and loop_media['tool_count']==41
            assert loop_media['privacy_reviewed'] and not loop_media['credentials_visible']
            assert not loop_media['model_generation_recorded'] and loop_media['owned_device_files_cleaned']
            assert loop_media['calls']==[dict(name=c['name'],id=c['id']) for c in calls]
            assert {Path(item['file']).suffix for item in loop_media['files']}=={'.png','.gif','.mp4'}
            for item in loop_media['files']:
                path=media_path.parent/item['file'];assert path.parent==media_path.parent
                assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
            observed=[r for a in data['attempts'] if a['apk_sha256']==build['sha256'] for r in (a.get('rounds') or [a])]
            for call in calls:
                assert call['result_id']==call['id'] and len(call['result_sha256'])==64
                assert hashlib.sha256(call['arguments_json'].encode()).hexdigest()==call['arguments_sha256']
                assert call['server_arguments_capture']=='reconstructed_serialization_matched_to_recorded_sha256'
                assert json.loads(call['server_arguments_json'])==json.loads(call['arguments_json'])
                assert hashlib.sha256(call['server_arguments_json'].encode()).hexdigest()==call['server_arguments_sha256']
                assert hashlib.sha256(call['result_text'].encode()).hexdigest()==call['result_sha256']
                assert any(c['id']==call['id'] and c['name']==call['name'] and c['argumentsSha256']==call['server_arguments_sha256']
                    for r in observed for c in r['calls']), 'A passing call must occur in the final-APK server traces'
                assert any(call['id'] in r['result_ids'] for r in observed), 'DSH must return the actual matching result'
    if data['plugin_installation_passed']:
        assert data['plugin']['executed_by_dsh'] and data['plugin']['call_id']
        assert data['plugin']['exit_code'] in [0,None]
        if tuple(map(int,version().split('.'))) >= (1,2,2):
            plugin=data['plugin'];assert plugin['apk_sha256']==build['sha256'] and plugin['target']=='PC2005-cloud/dsh-pet'
            assert plugin['installed_manifest_verified'] and plugin['package_name']=='dsh-pet' and plugin['package_version']
            assert plugin['tool_execution_succeeded'] and not plugin['host_installer_used'] and not plugin['compatibility_waiver_used']
            # DSH's actual plain-text tool result has no numeric exit-code field.
            # Preserve that absence instead of inventing zero; require actual
            # package-manager completion plus independent installed-manifest UI.
            if plugin['exit_code'] is None:
                assert plugin['exit_code_source']=='DSH_tool_result_did_not_expose_numeric_exit_code'
                assert '+ dsh-pet '+plugin['package_version'] in plugin['result_text']
                assert re.search(r'Done in [0-9.]+s using pnpm v',plugin['result_text'])
            media_path=ROOT/plugin['installation_media_manifest']
            assert media_path==ROOT/'docs/media/device'/('v'+version())/'dsh-plugin/manifest.json'
            proof=json.loads(media_path.read_text('utf8'))
            assert proof['schema']=='lma.physical-dsh-plugin/1' and proof['apk_sha256']==build['sha256']
            assert proof['physical_device'] and proof['installed_version']==plugin['package_version']
            assert proof['privacy_reviewed'] and not proof['host_installer_used']
            assert not proof['plugin_center_install_button_clicked'] and not proof['upgrade_button_clicked']
            assert plugin['activation_verified'] and proof['engine_reload_completed']
            assert proof['engine_ready_after_reload'] and proof['web_pet_visible_after_reload']
            assert not proof['system_overlay_bridge_tested'] and not proof['payment_voice_features_tested']
            assert not proof['model_generation_recorded'] and proof['owned_device_recording_cleaned']
            assert {Path(item['file']).suffix for item in proof['files']}=={'.png','.mp4','.gif'}
            for item in proof['files']:
                path=media_path.parent/item['file'];assert path.parent==media_path.parent
                assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
            assert plugin['tool_count']==41 and plugin['result_id']==plugin['call_id']
            assert hashlib.sha256(plugin['arguments_json'].encode()).hexdigest()==plugin['arguments_sha256']
            assert plugin['server_arguments_capture']=='reconstructed_serialization_matched_to_recorded_sha256'
            assert json.loads(plugin['server_arguments_json'])==json.loads(plugin['arguments_json'])
            assert hashlib.sha256(plugin['server_arguments_json'].encode()).hexdigest()==plugin['server_arguments_sha256']
            assert hashlib.sha256(plugin['result_text'].encode()).hexdigest()==plugin['result_sha256']
            command=json.loads(plugin['arguments_json'])['command']
            assert 'plugin --profile web add dsh-pet' in command and 'allow-version' not in command
            observed=[r for a in data['attempts'] if a['apk_sha256']==build['sha256'] for r in (a.get('rounds') or [a])]
            assert any(c['id']==plugin['call_id'] and c['name']=='bash' and c['argumentsSha256']==plugin['server_arguments_sha256']
                for r in observed for c in r['calls'])
            assert any(plugin['call_id'] in r['result_ids'] for r in observed)
    if tuple(map(int,version().split('.'))) >= (1,2,2):
        from build_llama_chat_runtime import verify_patch_record
        runtime=verify_patch_record();assert data['native_runtime_patch']==runtime
        assert runtime['bare_final_envelope_only_recovery'] and not runtime['argument_json_repair']
        assert runtime['incomplete_final_native_records_rejected']
        android=json.loads((directory/'physical-native-template.json').read_text('utf8'))
        current(android['input_fingerprint'])
        assert android['apk_sha256']==build['sha256'] and android['version']==version()
        assert android['physical_device'] and android['passed']==14 and android['synthetic_output']
        assert not android['model_inference_tested'] and not android['commands_executed']
        assert android['owned_device_files_cleaned']
        assert android['libraries']['libllama-common.so']==runtime['library_sha256']
        followup=data['full_context_followup']
        assert followup['profile']==profile['id'] and followup['effective_template_sha256']==profile['sha256']
        assert followup['input_tokens']>10000 and followup['original_message_count']>=5
        for key in ['normalized_request_messages_preserved','all_message_contents_present','background_before_pending_task',
                    'all_tools_preserved','tool_choice_preserved']:assert followup[key],key
        metadata=followup['positional_metadata'];assert metadata['tensorDataRead'] is False and metadata['modelModified'] is False
        assert metadata['metadata']['llama.context_length']==131072 and metadata['metadata']['llama.rope.freq_base']==500000
        assert metadata['positionalTensors']==[dict(name='rope_freqs.weight',shape=[32],ggmlType=0)]
        assert set(metadata['savedSettings'])=={'context','maxTokens','threads','temperature','reasoning'}
        native=followup['native_schema_controls'];assert native['tool_count']==41 and not native['model_inference']
        assert native['synthetic_generated_output'] and not native['external_execution']
        assert {c['mode'] for c in native['cases']}=={'auto','required','named','none'}
        assert all(c['passed'] and c['rendered_tools']==41 and c['actual_native_parser'] and not c['model_inference'] for c in native['cases'])
        names=followup['name_controls'];assert not names['model_inference'] and not names['external_execution']
        assert {c['name'] for c in names['cases']}=={'read','write'}
        assert all(c['passed'] and c['actual_native_parser'] and c['all41_definitions'] and c['synthetic_generated_output'] for c in names['cases'])
        modes=followup['api_mode_controls']
        assert {c['case'] for c in modes}=={'required','named','stream_named'}
        for case in modes:
            assert case['apk_sha256']==build['sha256'] and case['tool_count']==41
            assert case['full_context_preserved'] and case['tool_definitions_preserved']
            assert case['not_dsh_execution'] and case['commands_executed'] is False
            assert case['requested_max_tokens']==192, 'Diagnostic request ceiling is disclosed; saved parameters remain unchanged'
            assert isinstance(case['protocol_delivered_call'],bool)
            if case['protocol_delivered_call']:
                assert case['status']==200 and case['finish_reason']=='tool_calls' and case['calls']
                assert all(c['id'] and c['name'] and len(c['arguments_sha256'])==64 for c in case['calls'])
                if case['case'] in ['named','stream_named']:
                    assert all(c['name']=='bash' for c in case['calls']), 'Named choice must preserve the selected function'
        bos=followup['bos_controls'];assert bos['native_add_special'] and bos['preflight_add_special']
        assert bos['without_special']+1==bos['with_special']==followup['input_tokens']
        historical_formats=followup.get('historical_native_format_controls',[])
        if historical_formats:
            assert {c['case'] for c in historical_formats}=={'bare','xml'}
            for case in historical_formats:
                assert case['apk_sha256']=='00b8a94dd35230f4adfcbca9325d448922cf4a2c0112a33ef1c2965ee6e21486'
                assert case['native_endpoint']=='/completion' and case['not_public_gateway_acceptance']
                assert case['not_dsh_execution'] and not case['commands_executed'] and not case['settings_changed']
                assert case['tool_count']==41 and case['original_message_count']==5
                assert case['all_tools_preserved'] and case['all_message_contents_preserved']
                assert case['diagnostic_output_ceiling']==128 and not case['grammar_enabled']
                assert case['status']==200 and case['stop_type']=='eos'
            replay=followup['observed_envelope_replay']
            assert replay['actual_observed_output_replayed'] and replay['native_host_parser_rebuilt']
            assert replay['observed_apk_sha256']==historical_formats[0]['apk_sha256']
            assert replay['complete_arguments_preserved'] and replay['function_name']=='bash'
            assert not replay['external_execution'] and not replay['model_inference']
            assert replay['raw_content_sha256']==next(c['raw_content_sha256'] for c in historical_formats if c['case']=='xml')
        if 'physical_timing' in followup:
            timing=followup['physical_timing'];assert timing['prompt_tokens']==followup['input_tokens']
            assert 0<timing['first_decode_elapsed_lower_seconds']<=timing['first_decode_elapsed_upper_seconds']
            assert timing['first_decode_elapsed_upper_seconds']-timing['first_decode_elapsed_lower_seconds']<=timing['sampling_interval_seconds']+1
            final_rounds=[r for a in data['attempts'] if a['apk_sha256']==build['sha256'] for r in (a.get('rounds') or [a])]
            assert 0<timing['retry_cached_input_tokens']<=max(r['input_tokens'] for r in final_rounds), 'Retry cache may include the previous assistant call as well as the original prompt'
        if 'resource_observation' in followup:
            observation=followup['resource_observation']
            assert observation['apk_sha256']==build['sha256']
            assert observation['model']=='m04' and observation['saved_context']==131072
            assert observation['parameters_changed'] is False
            assert set(observation['native_process'])=={'total_pss_kib','total_rss_kib','total_swap_pss_kib'}
            assert all(isinstance(v,int) and v>=0 for v in observation['native_process'].values())
            assert observation['native_process']['total_pss_kib']>0 and observation['native_process']['total_rss_kib']>0
        if 'health_observation' in followup:
            observation=followup['health_observation'];assert observation['apk_sha256']==build['sha256']
            assert observation['samples']==10 and observation['actual_active_text_requests']>=1
            assert 0<observation['health_min_ms']<=observation['health_median_ms']<=observation['health_max_ms']
            assert not observation['model_inference_triggered']
    media_path=ROOT/'docs/media/device'/('v'+version())/'manifest.json'
    media=json.loads(media_path.read_text('utf8'));current(media['input_fingerprint'])
    assert media['schema']=='lma.physical-runtime-media/1' and media['apk_sha256']==build['sha256'] and media['physical_device']
    for item in media['files']:
        path=media_path.parent/item['file'];assert path.parent==media_path.parent
        assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    final=[a for a in data['attempts'] if a['apk_sha256']==build['sha256']]
    completed=sum(r['server_delivery']=='validated' and r['finish_reason'] in ['stop','tool_calls','length'] for a in final for r in (a.get('rounds') or [a]))
    modes=data.get('full_context_followup',{}).get('api_mode_controls',[])
    return dict(direct_api_model_requests=5+len(controls)+len(modes)+len(output_controls)+bool(array_observation),direct_api_tool_modes_tested=True,
        direct_api_successful_model_requests=5+len(controls)+sum(c['protocol_delivered_call'] for c in modes),
        strict_output_validation_negative_tested=bool(output_controls),
        strict_output_validation_rejections=sum(c['expected_failure_observed'] for c in output_controls),
        physical_native_parser_tested=bool(data.get('native_runtime_patch')),physical_native_parser_checks=14 if data.get('native_runtime_patch') else 0,
        dsh_final_apk_model_attempts=sum(len(a.get('rounds') or [a]) for a in final),dsh_final_apk_task_attempts=len(final),dsh_final_apk_completed_generations=completed,
        dsh_final_apk_successful_attempts=sum(a['status']=='passed' for a in final),
        dsh_app_tested=True,dsh_actual_requests=sum(len(a.get('rounds') or [a]) for a in data['attempts']),dsh_full_tools_loop_passed=data['tool_loop_passed'],
        dsh_plugin_installation_passed=data['plugin_installation_passed'],dsh_model_quality_accepted=False,physical_runtime_media_tested=True)
