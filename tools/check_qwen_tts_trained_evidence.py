"""Independently audit Qwen trained captures without promoting HOST evidence to Android."""
import argparse
import array
import copy
import hashlib
import json
import math
from pathlib import Path
import wave

from evidence import current, fingerprint

ROOT=Path(__file__).resolve().parents[1]
PATHS={'qwen-tts-assets.json':'build/qwen-tts-trained/receipt.json',
    'qwen-tts-trained.json':'build/qwen-tts-trained-tests/results.json',
    'qwen-tts-app-host.json':'build/qwen-tts-app-host-tests/results.json',
    'qwen-tts-capture-audit.json':'build/qwen-tts-trained-tests/capture-audit.json'}
FALSE_DIRECT=['fixture','asset_download_attempted','physical_android','app_executed','speech_quality_accepted',
    'voice_similarity_accepted','device_resource_fit_accepted','android_background_accepted','complete_target11_accepted','complete_release_accepted']
FALSE_APP=['physical_android','android_saf_tested','android_background_accepted','speech_quality_accepted','complete_target11_accepted','complete_release_accepted']


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def digest(data):return hashlib.sha256(data).hexdigest()
def identity(path):
    d=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(4*1024*1024),b''):d.update(b)
    return dict(bytes=path.stat().st_size,sha256=d.hexdigest())


def check(records,status,root=ROOT,with_audit=True,with_media=True):
    from build_qwen_tts_host import inputs as build_inputs
    from fetch_qwen_tts_trained import inputs as asset_inputs,selected
    from test_qwen_tts_trained import inputs as direct_inputs,LANGUAGES,PROMPT_A,PROMPT_B,REFERENCE
    from test_qwen_tts_app_host import inputs as app_inputs
    assets,direct,app,build=[records[k] for k in ['qwen-tts-assets.json','qwen-tts-trained.json','qwen-tts-app-host.json','qwen-tts-host-build.json']]
    for r,fp in [(assets,asset_inputs()),(direct,direct_inputs()),(app,app_inputs()),(build,build_inputs())]:current(r['input_fingerprint']);assert r['input_fingerprint']==fp
    bundle=selected();assert assets['schema']=='lma.qwen-tts-trained-assets/1' and assets['bundle_id']==bundle['id']
    assert assets['explicit_download'] and assets['developer_assets_only'] and not assets['app_assets_modified'] and not assets['model_executed']
    assert [{k:v for k,v in c.items() if k!='local_path'} for c in assets['components']]==bundle['components']
    assert sum(c['bytes'] for c in assets['components'])==920055680
    assert build['schema']=='lma.qwen-tts-host-build/1' and build['compiled_library_sources']==35 and build['backend']=='cpu'
    assert build['production_worker_source_unmodified'] and build['upstream_sources_unmodified'] and build['windows_crt_parent_environment_compatibility']
    assert not any(build[k] for k in ['bundled_model_data','physical_android','android_compiled','packaged_in_apk','model_executed'])
    assert direct['schema']=='lma.qwen-tts-trained-host/1' and direct['host_execution_checks_passed'] and not direct['smoke_only'] and not direct['failures']
    assert direct['compilation']==build==app['compilation'] and direct['acquisition']==assets and not any(direct[k] for k in FALSE_DIRECT)
    assert direct['trained_production_worker_executed'] and direct['production_worker_source_unmodified'] and direct['backend']=='cpu'
    assert direct['reference']==dict(path=REFERENCE,sha256=identity(root/REFERENCE)['sha256'],synthetic_trained_kokoro_output=True,human_identity_claimed=False)
    assets_path=root/'verification/development/qwen-tts-assets.json'
    assert direct['acquisition_receipt_sha256']==identity(assets_path if assets_path.exists() else root/PATHS['qwen-tts-assets.json'])['sha256']
    jobs={j['name']:j for j in direct['jobs']}
    names={'prompt-a','prompt-b','auto-language','seed-change','greedy','frame-budget','reference-a','reference-b','recovery-a'}|{'language-'+k for k,_ in LANGUAGES}
    assert len(jobs)==len(direct['jobs'])==18 and set(jobs)==names
    assert jobs['prompt-a']['prompt']==PROMPT_A and jobs['prompt-b']['prompt']==PROMPT_B
    assert [(jobs['language-'+k]['parameters']['language'],jobs['language-'+k]['prompt']) for k,_ in LANGUAGES]==LANGUAGES
    for name,j in jobs.items():
        assert j['passed'] and j['returncode']==0 and not j['timed_out'] and not j['forced_host_termination']
        assert not j['protocol_errors'] and not any(j['logs_truncated'])
        a=j['audio'];e=j['execution'];p=j['parameters']
        assert a['format']=='WAV' and (a['sample_rate'],a['sample_width'],a['channels'])==(24000,2,1)
        assert 0<a['samples']<=p['maxAudioTokens']*1920+48000 and a['rms']>1e-5 and a['nonzero_samples']>10 and 0<a['peak']<=1
        assert e['audioSamples']==a['samples'] and e['audioDurationSeconds']==a['seconds']==a['samples']/24000 and e['sampleRate']==24000
        assert e['effectiveParameters']==p and e['pipeline']=='qwen3_tts_06b_base' and e['backend']=='cpu'
        assert e['referenceMode']==('speaker_embedding' if name.startswith('reference-') else 'none')
        assert 0<e['inputTokens']<=p['maxInputTokens'] and e['modelLoadMs']>=0 and e['synthesisMs']>0 and e['pipelineMs']>=e['synthesisMs']
        assert e['synthesisRTF']==e['synthesisMs']/1000/a['seconds'] and e['pipelineRTF']==e['pipelineMs']/1000/a['seconds']
        assert j['resources']['observed'] and j['resources']['samples']>0 and j['resources']['observed_peak_working_set_bytes']>0
        assert not j['resources']['gpu_memory_measured'] and not j['resources']['physical_device_memory_measured']
    assert jobs['seed-change']['parameters']['seed']==5678 and jobs['greedy']['parameters']['temperature']==0 and jobs['greedy']['parameters']['topK']==1
    assert jobs['frame-budget']['parameters']['maxAudioTokens']==16 and jobs['frame-budget']['audio']['samples']==16*1920
    for name,equal in direct['comparison_to_a_bitwise_identical'].items():assert equal==(jobs[name]['audio']['sha256']==jobs['prompt-a']['audio']['sha256'])
    expected_controls={'bad-schema','empty-prompt','bad-threads','bad-language','bad-seed','bad-frame-budget','negative-prompt','token-budget','missing-codec','swapped-talker','bad-reference','cancel'}
    assert len(direct['controls'])==12 and {c['name'] for c in direct['controls']}==expected_controls
    for c in direct['controls']:
        assert c['passed'] and c['returncode']!=0 and not c['output_exists'] and not c['timed_out'] and not c['protocol_errors'] and not any(c['logs_truncated'])
        assert not any(e.get('event')=='complete' for e in c['events'])
        if c['name']=='cancel':
            t=c['cancel_trigger'];assert c['forced_host_termination'] and t in c['events'] and t['event']=='execution'
            assert 16<=t['details']['generatedAudioFrames']<t['details']['audioFrameLimit'] and not c['android_cooperative_cancellation_tested']
        else:assert not c['forced_host_termination'] and c['returncode']==1 and [e['message'] for e in c['events'] if e.get('event')=='error']==[c['expected_error']]
    assert direct['info']['events']==[dict(schema='lma.engine/1',engine='qwen_tts_native',revision=build['source_revision'],backend='cpu',bundled_model_data=False,generation_tested=False)]
    assert app['schema']=='lma.qwen-tts-app-host/1' and app['production_java_native_host_executed'] and not any(app[k] for k in FALSE_APP)
    java=app['java'];assert java['passed']>=90 and java['actual_host_children']==len(java['runs'])==len(java['launches'])==6 and java['network_calls']==0
    assert java['imported_objects']==2 and java['imported_bytes']==920055680 and java['reference_sha256']==direct['reference']['sha256']
    assert java['host_java_production_binding'] and not any(java[k] for k in ['android_application_executed','android_saf_tested','android_background_tested','speech_quality_accepted'])
    assert len(app['outputs'])==4 and {r['name'] for r in app['outputs']}=={'initial-a','reference-a','random-seed','recovery-a'}
    for launch,run in zip(java['launches'],java['runs']):
        assert launch['pipeline']=='qwen3_tts_06b_base' and launch['input']['prompt']==PROMPT_A and launch['parameters']['threads']==4
        if run['name']=='cancel-after-frame16':assert run['cancelled'] and 16<=run['execution']['generatedAudioFrames']<run['execution']['audioFrameLimit']
        elif run['name']=='token-budget':assert not run['cancelled'] and launch['parameters']['maxInputTokens']==1
        else:assert run['execution']['audioSamples']>0 and run['execution']['sampleRate']==24000
        assert ('referenceAudio' in launch)==(run['name']=='reference-a')
    direct_path=root/'verification/development/qwen-tts-trained.json'
    assert app['direct_trained_report_sha256']==identity(direct_path if direct_path.exists() else root/PATHS['qwen-tts-trained.json'])['sha256']
    assert status['qwen_tts_trained_production_source_host_executed'] and status['qwen_tts_production_java_native_host_executed']
    assert not any(status[k] for k in ['qwen_tts_complete_android_speech_tested','qwen_tts_speech_quality_accepted','release_ready','published','all_selected_models_supported'])
    if with_audit:
        audit=records['qwen-tts-capture-audit.json'];current(audit['input_fingerprint']);assert audit['input_fingerprint']==fingerprint('tools/check_qwen_tts_trained_evidence.py')
        assert audit['raw_capture_checks_passed'] and audit['protocol_streams_checked']==31 and audit['original_wavs_recomputed']==22 and audit['imported_objects_rehashed']==2
        assert not audit['physical_android'] and not audit['speech_quality_accepted'] and not audit['complete_release_accepted']
        for name in ['qwen-tts-assets.json','qwen-tts-trained.json','qwen-tts-app-host.json','qwen-tts-host-build.json']:assert audit['sources'][name]==digest(json.dumps(records[name],ensure_ascii=False,sort_keys=True).encode())
    if with_media:
        media=load(root/'docs/media/development/qwen-tts-trained-media.json');current(media['input_fingerprint'])
        assert media['schema']=='lma.qwen-tts-trained-media/1' and media['input_fingerprint']==fingerprint('tools/render_qwen_tts_trained.py')
        assert media['original_wav_bytes_unchanged'] and not any(media[k] for k in ['physical_android','app_screen_recording','speech_quality_accepted','complete_release_accepted'])
        assert media['gif_frames']==3 and len(media['files'])==6
        assert [(i['case'],i['file']) for i in media['source_audio']]==list(zip(['prompt-a','language-en','reference-a'],
            ['qwen-tts-trained-zh.wav','qwen-tts-trained-en.wav','qwen-tts-trained-reference.wav']))
        for name in ['qwen-tts-trained.json','qwen-tts-assets.json','qwen-tts-app-host.json']:
            assert media['sources']['verification/development/'+name]==identity(root/'verification/development'/name)['sha256']
        for name,item in media['files'].items():assert identity(root/'docs/media/development'/name)==item
        for item in media['source_audio']:assert item['audio']==jobs[item['case']]['audio'] and media['files'][item['file']]==dict(bytes=item['audio']['bytes'],sha256=item['audio']['sha256'])


def raw(records):
    d=records['qwen-tts-trained.json'];a=records['qwen-tts-app-host.json'];b=records['qwen-tts-host-build.json'];count=0;waves=0;streams=0
    folder=ROOT/d['capture_directory']
    for name,item in d['files'].items():assert identity(folder/name)==item;count+=1
    for item in [d['info']]+d['jobs']+d['controls']:
        name=item.get('name','info');events=[json.loads(line) for line in (folder/(name+'.stdout')).read_bytes().splitlines()]
        assert events==item['events'] and not (folder/(name+'.stderr')).read_bytes();streams+=1
        if name!='info':
            request=load(folder/(name+'.json'));assert identity(folder/(name+'.json'))['sha256']==item['request_sha256']
            assert request['parameters']==item['parameters'] and request['input']['prompt']==item['prompt']
            assert load(folder/(name+'-capture.json'))==item
            execution={}
            for event in events:
                if event.get('event')=='execution':execution.update(event['details'])
            assert execution==item['execution']
        if 'audio' in item:
            assert [e for e in events if e.get('event')=='complete']==[dict(event='complete',output=request['output'])]
            verify_wave(folder/(name+'.wav'),item['audio']);waves+=1
    assert identity(ROOT/b['executable'])==dict(bytes=b['bytes'],sha256=b['sha256'])
    app_folder=ROOT/a['capture_directory'];assert load(app_folder/'data/java-results.json')==json.loads((app_folder/'java.stdout').read_bytes())==a['java']
    assert not (app_folder/'java.stderr').read_bytes()
    for item in a['outputs']:verify_wave(ROOT/item['file'],item['audio']);waves+=1
    objects=app_folder/'data/files/bundles/objects';assert len(list(objects.iterdir()))==2
    for c in records['qwen-tts-assets.json']['components']:assert identity(objects/c['sha256'])==dict(bytes=c['bytes'],sha256=c['sha256'])
    assert not list((app_folder/'data/files/engine-work').iterdir()) and not list((app_folder/'data').glob('*/'+ '*.json'))
    sources={n:digest(json.dumps(records[n],ensure_ascii=False,sort_keys=True).encode()) for n in ['qwen-tts-assets.json','qwen-tts-trained.json','qwen-tts-app-host.json','qwen-tts-host-build.json']}
    result=dict(schema='lma.qwen-tts-capture-audit/1',raw_capture_checks_passed=True,files_rehashed=count,protocol_streams_checked=streams,
        original_wavs_recomputed=waves,imported_objects_rehashed=2,sources=sources,physical_android=False,speech_quality_accepted=False,complete_release_accepted=False,
        input_fingerprint=fingerprint('tools/check_qwen_tts_trained_evidence.py'))
    (ROOT/PATHS['qwen-tts-capture-audit.json']).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result


def verify_wave(path,a):
    assert identity(path)==dict(bytes=a['bytes'],sha256=a['sha256'])
    with wave.open(str(path),'rb') as wav:
        assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes())==(1,2,24000,a['samples'])
        values=array.array('h');values.frombytes(wav.readframes(wav.getnframes()))
    assert len(values)==a['samples'] and sum(v!=0 for v in values)==a['nonzero_samples']
    assert max(abs(v) for v in values)/32768==a['peak']
    assert math.isclose(math.sqrt(math.fsum((v/32768)**2 for v in values)/len(values)),a['rms'],rel_tol=0,abs_tol=1e-15)
    assert sum(abs(v)>=32767 for v in values)/len(values)==a['clipping_fraction']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--recompute-raw',action='store_true');parser.add_argument('--adversarial',action='store_true');args=parser.parse_args()
    records={n:load(ROOT/p) for n,p in PATHS.items() if (ROOT/p).exists()}
    executable=ROOT/records['qwen-tts-trained.json']['compilation']['executable'];records['qwen-tts-host-build.json']=load(executable.parent.parent/'receipt.json')
    status=dict(qwen_tts_trained_production_source_host_executed=True,qwen_tts_production_java_native_host_executed=True,
        qwen_tts_complete_android_speech_tested=False,qwen_tts_speech_quality_accepted=False,release_ready=False,published=False,all_selected_models_supported=False)
    check(records,status,with_audit=False,with_media=False)
    if args.recompute_raw:records['qwen-tts-capture-audit.json']=raw(records)
    check(records,status,with_media=False)
    if args.adversarial:
        mutations=[('qwen-tts-trained.json',k) for k in ['physical_android','speech_quality_accepted','voice_similarity_accepted','complete_target11_accepted','complete_release_accepted']]
        mutations += [('qwen-tts-app-host.json',k) for k in ['physical_android','android_saf_tested','complete_release_accepted']]
        for name,key in mutations:
            changed=copy.deepcopy(records);changed[name][key]=True
            try:check(changed,status,with_media=False)
            except AssertionError:continue
            raise AssertionError('False HOST promotion accepted: '+key)
        print('Rejected eight false Android/quality/voice/target/Release claims')
    print('Qwen trained/native Java capture identities and HOST-only scope passed')


if __name__=='__main__':main()
