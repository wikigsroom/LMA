"""Audit retained trained TTS captures independently and prevent unsupported scope claims."""
import argparse
import array
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import wave

from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
PATHS = {'tts-assets.json': 'build/tts-trained/receipt.json',
         'tts-trained.json': 'build/tts-trained-tests/results.json',
         'tts-app-host.json': 'build/tts-app-host-tests/results.json',
         'tts-capture-audit.json': 'build/tts-trained-tests/capture-audit.json'}
PIPELINES = ['kokoro', 'piper_vits', 'matcha']
FALSE_DIRECT = ['fixture', 'asset_download_attempted', 'physical_android', 'app_executed',
    'android_log_interposition_tested', 'host_oov_guard_accepted', 'speech_quality_accepted',
    'device_resource_fit_accepted', 'android_background_accepted', 'complete_target10_accepted', 'complete_release_accepted']
FALSE_APP = ['physical_android', 'android_saf_tested', 'android_background_accepted',
    'android_log_interposition_tested', 'speech_quality_accepted', 'complete_target10_accepted', 'complete_release_accepted']


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(data): return hashlib.sha256(data).hexdigest()


def identity(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''): value.update(block)
    return dict(bytes=path.stat().st_size, sha256=value.hexdigest())


def check(records, status, digest, root, with_audit=True, with_media=True):
    from build_tts_host import inputs as build_inputs
    from fetch_tts_trained import inputs as asset_inputs, selected, distinct
    from test_tts_trained import inputs as direct_inputs, PROMPT_A, PROMPT_B
    from test_tts_app_host import inputs as app_inputs
    assets, trained, app, compilation = [records[name] for name in
        ['tts-assets.json', 'tts-trained.json', 'tts-app-host.json', 'tts-host-build.json']]
    for value, expected in [(assets,asset_inputs()),(trained,direct_inputs()),(app,app_inputs()),(compilation,build_inputs())]:
        current(value['input_fingerprint']); assert value['input_fingerprint'] == expected
    lock = selected(); bundles = lock['bundles']; unique = distinct()
    assert assets['schema'] == 'lma.tts-trained-assets/1' and assets['explicit_download'] and assets['developer_assets_only']
    assert not assets['app_assets_modified'] and not assets['model_executed']
    assert assets['hf_download_origin'] in ['https://huggingface.co', 'https://hf-mirror.com']
    assert assets['bundles'] == bundles and len(assets['components']) == 9
    assert [{k:v for k,v in item.items() if k!='local_path'} for item in assets['components']] == unique
    catalogue = load(root / 'catalogue/model-bundles.json')['bundles']
    for pinned in bundles:
        declared = next(b for b in catalogue if b['id']==pinned['id'])
        assert declared['components'] == pinned['components'] and declared['license'] == pinned['license']
        assert declared['pipeline'] == pinned['pipeline'] and declared['languages'] == [pinned['language']]
        assert declared['tasks'] == ['audio'] and declared['engine'] == 'sherpa_tts'
    assert compilation['schema'] == 'lma.tts-host-build/1' and compilation['backend'] == 'cpu'
    assert compilation['production_worker_source_unmodified'] and compilation['windows_crt_parent_compatibility'] and compilation['external_model_data']
    assert not any(compilation[k] for k in ['android_log_interposition_tested','physical_android','android_compiled','packaged_in_apk','model_executed'])
    runtime = load(root / 'research/tts_host/runtime.json')
    assert compilation['runtime'] == runtime and runtime['version'] == '2.0.1' and runtime['host_only']
    assert compilation['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}',compilation['sha256'])
    assert trained['schema'] == 'lma.tts-trained-host/1' and trained['host_execution_checks_passed'] and not trained['failures']
    assert trained['compilation'] == compilation and trained['acquisition'] == assets
    assert trained['trained_production_worker_executed'] and trained['production_worker_source_unmodified'] and trained['backend'] == 'cpu'
    assert not any(trained[k] for k in FALSE_DIRECT) and not trained['seed_control_available']
    asset_path = root / 'verification/development/tts-assets.json'
    assert trained['acquisition_receipt_sha256'] == digest((asset_path if asset_path.exists() else root / PATHS['tts-assets.json']).read_bytes())
    info = trained['info']; assert info['returncode'] == 0 and not info['protocol_errors'] and len(info['events']) == 1
    assert info['events'][0] == dict(schema='lma.engine/1',engine='sherpa_tts',revision=compilation['source_revision'],sherpa='2.0.1',onnxruntime='1.28.2',backend='cpu',bundled_model_data=False,generation_tested=False)
    jobs = trained['jobs']; by_name = {job['name']:job for job in jobs}
    expected_jobs = {p+'-'+suffix for p in PIPELINES for suffix in ['a','b','speed','speaker-clamp','recovery-a']} | {f'kokoro-voice-{n:02d}' for n in range(1,54)}
    assert len(jobs) == len(by_name) == 68 and set(by_name) == expected_jobs
    assert trained['voice_coverage'] == dict(kokoro=list(range(54)),piper_vits=[0],matcha=[0])
    for job in jobs:
        pipeline = job['pipeline']; bundle = next(b for b in bundles if b['pipeline']==pipeline)
        assert job['passed'] and job['returncode'] == 0 and job['seconds'] > 0 and not job['timed_out']
        assert not job['protocol_errors'] and not any(job['logs_truncated']) and not job['forced_host_termination']
        audio = job['audio']; execution = job['execution']; effective = dict(job['parameters'],speaker=min(job['parameters']['speaker'],bundle['declared_speakers']-1))
        assert execution['effectiveParameters'] == effective and execution['speakerCount'] == bundle['declared_speakers']
        assert execution['pipeline'] == pipeline and execution['sampleRate'] == audio['sample_rate']
        assert audio['format'] == 'WAV' and audio['channels'] == 1 and audio['sample_width'] == 2
        assert audio['samples'] == execution['audio']['samples'] and audio['sample_rate'] == execution['audio']['sampleRate']
        assert audio['seconds'] == audio['samples']/audio['sample_rate'] and 0<audio['seconds']<=job['parameters']['maxAudioSeconds']
        assert audio['rms']>1e-5 and audio['nonzero_samples']>10 and 0<audio['peak']<=1
        assert job['resources']['observed'] and job['resources']['samples']>0 and job['resources']['observed_peak_working_set_bytes']>0
        assert not job['resources']['gpu_memory_measured'] and not job['resources']['physical_device_memory_measured']
        assert len([e for e in job['events'] if e.get('event')=='complete'])==1 and not any(e.get('event')=='error' for e in job['events'])
    for pipeline in PIPELINES:
        assert by_name[pipeline+'-a']['prompt'] == PROMPT_A and by_name[pipeline+'-b']['prompt'] == PROMPT_B
        assert by_name[pipeline+'-speed']['audio']['seconds'] < by_name[pipeline+'-a']['audio']['seconds']
        assert trained['repeat_a_bitwise_identical'][pipeline] == (by_name[pipeline+'-a']['audio']['sha256']==by_name[pipeline+'-recovery-a']['audio']['sha256'])
    errors = dict(zip(['bad-schema','empty-prompt','bad-threads','bad-speed','bad-speaker','missing-lexicon','bad-pipeline'],
        ['Unsupported TTS task','Invalid speech text or output','TTS parameter exceeds application bounds','TTS parameter exceeds application bounds','TTS parameter exceeds application bounds','A required TTS component is missing','Unsupported TTS pipeline']))
    errors.update({p+'-duration-limit':'Audio exceeded the selected duration limit; no partial output was accepted' for p in PIPELINES})
    assert len(trained['controls'])==13 and {c['name'] for c in trained['controls']} == set(errors)|{p+'-cancel' for p in PIPELINES}
    for control in trained['controls']:
        assert control['passed'] and not control['output_exists'] and not control['timed_out'] and not control['protocol_errors'] and not any(control['logs_truncated'])
        assert not any(e.get('event')=='complete' for e in control['events'])
        if control['name'] in errors:
            actual = [e for e in control['events'] if e.get('event')=='error']
            assert control['returncode']==1 and len(actual)==1 and actual[0]['message']==errors[control['name']]
        else:
            trigger = control['cancel_trigger']; assert control['forced_host_termination'] and control['returncode']!=0
            assert trigger in control['events'] and trigger['stage']=='synthesizing' and 0<trigger['fraction']<1
            assert control['cancel_to_exit_seconds']>=0
    assert app['schema']=='lma.tts-app-host/1' and app['production_java_native_host_executed'] and app['compilation']==compilation
    assert not any(app[k] for k in FALSE_APP)
    direct_path = root / 'verification/development/tts-trained.json'
    assert app['direct_trained_report_sha256']==digest((direct_path if direct_path.exists() else root/PATHS['tts-trained.json']).read_bytes())
    java=app['java']; assert java['passed']==157 and java['actual_host_children']==12 and java['network_calls']==0
    assert java['imported_component_references']==11 and java['imported_objects']==9 and java['imported_bytes']==sum(c['bytes'] for c in unique)
    assert java['host_java_production_binding'] and not java['seed_control_available']
    assert not any(java[k] for k in ['android_application_executed','android_saf_tested','android_background_tested','speech_quality_accepted'])
    assert len(java['launches'])==len(java['runs'])==12 and len(app['outputs'])==6
    for launch,run in zip(java['launches'],java['runs']):
        bundle=next(b for b in bundles if b['id']==run['bundle_id']); index=PIPELINES.index(bundle['pipeline'])
        assert launch['schema']=='lma.engine-request/1' and launch['type']=='speech.synthesize' and launch['pipeline']==run['pipeline']
        expected_speed=1+index*.1
        assert launch['parameters']['speed']==expected_speed and launch['parameters']['threads']==4 and launch['parameters']['speaker']==0
        assert launch['parameters']['maxAudioSeconds']==(1 if run['name']=='duration-limit' else 180)
        assert launch['input']['prompt']==((PROMPT_A+' ')*11+PROMPT_A if run['name']=='cancel-after-progress' else PROMPT_A)
        assert set(launch['components'])=={c['role'] for c in bundle['components']}
        for component in bundle['components']:
            assert launch['components'][component['role']].replace('\\','/').endswith('/data/files/bundles/objects/'+component['sha256'])
        if 'output' in run:
            import struct
            expected_float=struct.unpack('f',struct.pack('f',expected_speed))[0]
            assert launch['output']==run['output'] and run['execution']['effectiveParameters']['speed']==expected_float
            assert run['execution']['effectiveParameters']['threads']==4
    for bundle in bundles:
        runs=[r for r in java['runs'] if r['bundle_id']==bundle['id']]
        assert [r['name'] for r in runs]==['initial-a','cancel-after-progress','duration-limit','recovery-a']
        cancel=runs[1]; assert cancel['cancelled'] and 'output' not in cancel
        assert any(e['stage']=='synthesizing' and isinstance(e.get('fraction'),(int,float)) and 0<e['fraction']<1 for e in cancel['progress'])
        assert runs[2]['expected_error']==errors[bundle['pipeline']+'-duration-limit'] and 'output' not in runs[2]
        for run in [runs[0],runs[3]]:
            assert run['bytes']>44 and run['execution']['speakerCount']==bundle['declared_speakers']
            assert 'audio' in run['execution'] and 'effectiveParameters' in run['execution']
    assert status['tts_trained_production_source_host_executed'] and status['tts_production_java_native_host_executed']
    assert not any(status[k] for k in ['tts_complete_android_speech_tested','tts_speech_quality_accepted','release_ready','all_selected_models_supported'])
    if with_audit:
        audit=records['tts-capture-audit.json']; current(audit['input_fingerprint'])
        assert audit['input_fingerprint']==fingerprint('tools/check_tts_trained_evidence.py') and audit['schema']=='lma.tts-capture-audit/1'
        assert audit['raw_files']==394 and audit['protocol_streams']==82 and audit['independent_wav_recalculations']==74
        assert audit['production_java_native_children']==12 and audit['imported_objects_verified']==9
        assert audit['trained_report_sha256']==app['direct_trained_report_sha256']
        app_path=root/'verification/development/tts-app-host.json'
        assert audit['app_report_sha256']==digest((app_path if app_path.exists() else root/PATHS['tts-app-host.json']).read_bytes())
        assert audit['physical_android'] is False and audit['complete_release_accepted'] is False
    if with_media:
        media=load(root/'docs/media/development/tts-trained-media.json'); current(media['input_fingerprint'])
        assert media['schema']=='lma.tts-trained-media/1' and media['kind']=='actual_trained_host_wav_and_waveform_slideshow'
        assert len(media['files'])==6 and len(media['source_audio'])==3
        assert not any(media[k] for k in ['physical_android','app_screen_recording','speech_quality_accepted','complete_release_accepted'])
        for name,expected in media['sources'].items(): assert digest((root/name).read_bytes())==expected
        for name,expected in media['files'].items(): assert identity(root/'docs/media/development'/name)==expected
        for item,pipeline in zip(media['source_audio'],PIPELINES): assert item['case']==pipeline+'-a' and item['audio']==by_name[pipeline+'-a']['audio']


def wav_audit(path, expected):
    assert identity(path)=={k:expected[k] for k in ['bytes','sha256']}
    with wave.open(str(path),'rb') as stream:
        assert (stream.getnchannels(),stream.getsampwidth(),stream.getframerate(),stream.getnframes())==(1,2,expected['sample_rate'],expected['samples'])
        pcm=array.array('h',stream.readframes(stream.getnframes()))
    if sys.byteorder!='little':pcm.byteswap()
    assert len(pcm)==expected['samples']
    values=dict(rms=math.sqrt(math.fsum(int(x)*int(x) for x in pcm)/len(pcm))/32768,
        peak=max(abs(x) for x in pcm)/32768,clipping_fraction=sum(abs(x)>=32767 for x in pcm)/len(pcm),nonzero_samples=sum(x!=0 for x in pcm))
    assert all(math.isclose(values[k],expected[k],rel_tol=0,abs_tol=1e-12) for k in values)


def raw_audit(records):
    from fetch_tts_trained import verify, distinct
    trained=records['tts-trained.json']; app=records['tts-app-host.json']; compilation=records['tts-host-build.json']; verify()
    folder=(ROOT/trained['capture_directory']).resolve(); folder.relative_to(ROOT/'build/tts-trained-tests')
    assert {p.name for p in folder.iterdir() if p.is_file()}==set(trained['files'])|{'results.json'}
    for name,expected in trained['files'].items(): assert Path(name).name==name and identity(folder/name)==expected
    streams=[dict(name='info',**trained['info'])]+trained['jobs']+trained['controls']
    for run in streams:
        assert [json.loads(line) for line in (folder/(run['name']+'.stdout')).read_text(encoding='utf-8').splitlines()]==run['events']
        if run['name']=='info': continue
        assert load(folder/(run['name']+'-capture.json'))==run
        request_path=folder/(run['name']+'.json'); request=load(request_path)
        assert identity(request_path)['sha256']==run['request_sha256'] and request['parameters']==run['parameters'] and request['input']['prompt']==run['prompt']
        bundle=next(b for b in records['tts-assets.json']['bundles'] if b['id']==run['bundle_id'])
        for component in bundle['components']:
            if run['name']=='missing-lexicon' and component['role']=='lexicon':continue
            assert request['components'][component['role']].endswith('/build/tts-trained/originals/'+component['sha256']+'/'+component['path'])
        if run.get('audio'):wav_audit(folder/(run['name']+'.wav'),run['audio'])
        else:assert not (folder/(run['name']+'.wav')).exists()
    binary=ROOT/compilation['executable']; assert identity(binary)=={k:compilation[k] for k in ['bytes','sha256']}
    for name,expected in compilation['runtime']['files'].items():
        if name.endswith('.dll'):assert identity(binary.parent/name)=={k:expected[k] for k in ['bytes','sha256']}
    app_folder=(ROOT/app['capture_directory']).resolve();app_folder.relative_to(ROOT/'build/tts-app-host-tests')
    assert load(app_folder/'data/java-results.json')==app['java']
    assert json.loads((app_folder/'java.stdout').read_text(encoding='utf-8'))==app['java']
    for output in app['outputs']:wav_audit(ROOT/output['file'],output['audio'])
    for item in distinct():
        objects=list((app_folder/'data/files/bundles/objects').glob(item['sha256']+'*'))
        assert len(objects)==1 and identity(objects[0])=={k:item[k] for k in ['bytes','sha256']}
    assert not list((app_folder/'data').rglob('*.wav.json'))
    for run in app['java']['runs']:
        run_folder=app_folder/'data'/(run['pipeline']+'-'+run['name']); assert not list(run_folder.glob('*.json'))
    audit=dict(schema='lma.tts-capture-audit/1',raw_files=len(trained['files']),protocol_streams=len(streams),
        independent_wav_recalculations=len(trained['jobs'])+len(app['outputs']),production_java_native_children=12,imported_objects_verified=9,
        trained_report_sha256=identity(ROOT/PATHS['tts-trained.json'])['sha256'],app_report_sha256=identity(ROOT/PATHS['tts-app-host.json'])['sha256'],
        physical_android=False,complete_release_accepted=False,input_fingerprint=fingerprint('tools/check_tts_trained_evidence.py'))
    (ROOT/PATHS['tts-capture-audit.json']).write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8');return audit


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--raw',action='store_true');parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    records={name:load(ROOT/path) for name,path in PATHS.items() if name!='tts-capture-audit.json'}
    records['tts-host-build.json']=records['tts-trained.json']['compilation']
    status=dict(tts_trained_production_source_host_executed=True,tts_production_java_native_host_executed=True,
        tts_complete_android_speech_tested=False,tts_speech_quality_accepted=False,release_ready=False,all_selected_models_supported=False)
    check(records,status,digest,ROOT,with_audit=False,with_media=False)
    if args.raw:print(json.dumps(raw_audit(records),indent=2))
    if args.self_test:
        mutations=[('tts-trained.json','physical_android'),('tts-trained.json','speech_quality_accepted'),('tts-trained.json','complete_target10_accepted'),
            ('tts-trained.json','complete_release_accepted'),('tts-trained.json','android_log_interposition_tested'),('tts-app-host.json','android_saf_tested'),
            ('tts-app-host.json','android_background_accepted'),('tts-app-host.json','complete_release_accepted')]
        for filename,key in mutations:
            changed=copy.deepcopy(records);changed[filename][key]=True
            try:check(changed,status,digest,ROOT,with_audit=False,with_media=False)
            except AssertionError:continue
            raise AssertionError('Accepted false scope promotion: '+filename+':'+key)
        receipt=dict(rejected_false_scope_promotions=len(mutations),input_fingerprint=fingerprint('tools/check_tts_trained_evidence.py'))
        (ROOT/'build/tts-trained-tests/adversarial-audit.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print('Rejected eight false Android/quality/log/target/Release claims')
    print('All three trained TTS and production Java host identities/scopes passed')


if __name__=='__main__':main()
