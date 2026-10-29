"""Re-read actual trained diffusion captures; never promote HOST evidence to Android/quality."""
import copy
import hashlib
import json
import math
from pathlib import Path

from evidence import current, fingerprint

ROOT = Path(__file__).resolve().parents[1]
PATHS = {'sd-variants-assets.json': 'build/sd-variants-trained/receipt.json',
         'sd-variants-trained.json': 'build/sd-variants-trained-tests/results.json',
         'sd-variants-lcm-effect.json': 'build/sd-variants-lcm-effect-tests/results.json',
         'sd-variants-app-host.json': 'build/sd-variants-app-host-tests/results.json',
         'sd-variants-capture-audit.json': 'build/sd-variants-trained-tests/capture-audit.json'}
FALSE_DIRECT = ['fixture', 'asset_download_attempted', 'android_compiled', 'physical_android', 'app_executed',
                'semantic_quality_accepted', 'device_resource_fit_accepted', 'android_background_accepted',
                'complete_target02_accepted', 'complete_target03_accepted', 'complete_target05_accepted', 'complete_release_accepted']
FALSE_APP = ['physical_android', 'android_saf_tested', 'android_background_accepted', 'image_quality_accepted',
             'complete_target02_accepted', 'complete_target03_accepted', 'complete_target05_accepted', 'complete_release_accepted']


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(data): return hashlib.sha256(data).hexdigest()
def identity(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''): h.update(block)
    return dict(bytes=path.stat().st_size, sha256=h.hexdigest())


def record_path(root, name):
    public = root / 'verification/development' / name
    return public if public.exists() else root / PATHS[name]


def check(records, status, root=ROOT, with_audit=True, with_media=True):
    from build_sd_host import inputs as build_inputs
    from fetch_sd_variants_trained import inputs as asset_inputs, selected
    from test_sd_variants_trained import inputs as trained_inputs, cases
    from test_sd_variants_app_host import inputs as app_inputs
    from test_sd_lcm_effect import inputs as effect_inputs
    assets, direct, app = [records[key] for key in ['sd-variants-assets.json', 'sd-variants-trained.json', 'sd-variants-app-host.json']]
    effect = records['sd-variants-lcm-effect.json']
    for report, expected in [(assets, asset_inputs()), (direct, trained_inputs()), (app, app_inputs()), (effect, effect_inputs())]:
        current(report['input_fingerprint']); assert report['input_fingerprint'] == expected
    lock = selected(); assert assets['lock'] == lock and assets['schema'] == 'lma.sd-variants-trained-assets/1'
    assert [{k:v for k,v in item.items() if k != 'local_path'} for item in assets['assets']] == lock['assets']
    assert sum(item['bytes'] for item in assets['assets']) == 3324276168 and len(assets['assets']) == 5
    assert assets['developer_assets_only'] and assets['explicit_download'] and not assets['model_executed'] and not assets['app_assets_modified']
    assert assets['download_origin'] in ['https://huggingface.co', 'https://hf-mirror.com']
    compilation = direct['compilation']; current(compilation['input_fingerprint']); assert compilation['input_fingerprint'] == build_inputs()
    assert compilation == app['compilation'] == records['sd15-host-build.json']
    assert compilation['source_revision'] == 'be486498eadc29dc3cd234d944c2180ed42b1415' and compilation['ggml_revision'] == 'a5915eb0e47adef21c3f25b889a008925ea838c2'
    assert compilation['production_worker_source_unmodified'] and compilation['production_vocabulary_source_unmodified'] and compilation['backend'] == 'cpu'
    assert direct['schema'] == 'lma.sd-variants-trained-host/1' and direct['trained_model_executed'] and direct['host_execution_checks_passed'] and not direct['failures']
    assert direct['acquisition'] == assets and direct['acquisition_receipt_sha256'] == identity(record_path(root, 'sd-variants-assets.json'))['sha256']
    assert direct['production_worker_source_unmodified'] and direct['production_vocabulary_source_unmodified'] and direct['all_assets_already_present'] and direct['backend'] == 'cpu'
    assert not any(direct[key] for key in FALSE_DIRECT)
    headers = direct['headers']; assert set(headers) == {item['id'] for item in lock['assets']}
    xl = headers['sdxl_base_q4_0']; assert xl['format'] == 'gguf' and xl['version'] == 3 and xl['tensor_count'] == 2641 and not xl['learned_data_exported']
    tensors = {t['name']:t for t in xl['tensors']}; assert len(tensors) == xl['tensor_count']
    assert [tensors[name]['shape'] for name in ['cond_stage_model.transformer.text_model.embeddings.token_embedding.weight',
        'cond_stage_model.1.transformer.text_model.embeddings.token_embedding.weight']] == [[768,49408],[1280,49408]]
    assert sum(n.startswith('first_stage_model.decoder.') for n in tensors) >= 100 and sum(n.startswith('model.diffusion_model.') for n in tensors) >= 1000
    for key,h in headers.items(): assert not h['learned_data_exported'] and h['tensor_count'] == len(h['tensors']) and h['tensor_count'] >= 50
    expected = [json.loads(json.dumps(c)) for c in cases() if c['cancel_step'] is None]
    jobs = direct['jobs']; assert len(jobs) == 14 and [j['case'] for j in jobs] == expected
    for j,c in zip(jobs,expected):
        p = j['parameters']; lcm = c['profile'] == 'lcm'; steps = 4 if lcm else 8
        assert j['passed'] and j['returncode'] == 0 and not j['protocol_errors'] and not j['timed_out'] and not j['forced_host_termination'] and not any(j['logs_truncated'])
        assert p == dict(width=c['width'], height=c['height'], steps=steps, cfg=1. if lcm else 7., sampler='lcm' if lcm else 'euler',
                         scheduler='lcm' if lcm else 'discrete', seed=42, threads=6, vaeTiling=True, flowShift=0)
        assert j['pipeline'] == c['family'] and j['sampling_profile'] == c['profile'] and len(j['adapters']) == len(c['adapters'])
        assert [item['scale'] for item in j['adapters']] == [item[1] for item in c['adapters']]
        assert j['progress_phase_consistent'] and j['sampling_steps_observed'] == list(range(steps+1))
        assert [e['stage'] for e in j['events'] if e.get('event') == 'stage'] == ['loading','generating']
        image = j['image']; assert (image['width'],image['height'],image['format'],image['mode']) == (c['width'],c['height'],'PNG','RGB')
        assert image['bytes'] > 10000 and all(math.isfinite(v) and 1<v<=128 for v in image['channel_stddev'])
        assert direct['files'][j['name']+'.png'] == {k:image[k] for k in ['bytes','sha256']}
        assert j['resources']['observed'] and j['resources']['samples'] > 0 and j['resources']['observed_peak_working_set_bytes'] > 0
        assert not j['resources']['physical_device_memory_measured'] and not j['resources']['gpu_memory_measured']
    by_name = {j['name']:j for j in jobs}; comparisons = {}
    for family in ['sd15','sdxl']:
        for label,a,b,equal in [('zero_matches_base','base-a','style-zero',True),('style_changes_output','base-a','style-one',False),
                                ('combined_style_changes_output','lcm-a','lcm-style',False),('recovery_matches_lcm','lcm-a','lcm-recovery-a',True)]:
            comparisons[family+'_'+label] = ((by_name[family+'-'+a]['image']['sha256'] == by_name[family+'-'+b]['image']['sha256']) == equal)
    comparisons['sdxl_prompt_changes_output'] = by_name['sdxl-base-a']['image']['sha256'] != by_name['sdxl-base-b']['image']['sha256']
    assert direct['comparisons'] == comparisons and all(comparisons.values())
    assert effect['schema']=='lma.sd-lcm-weight-effect-host/1' and effect['host_weight_effect_checks_passed'] and not effect['failures']
    assert effect['diagnostic_only'] and effect['compilation']==compilation and not any(effect[k] for k in ['app_recipe','asset_download_attempted','physical_android','semantic_quality_accepted','complete_release_accepted'])
    assert effect['direct_trained_report_sha256']==identity(record_path(root,'sd-variants-trained.json'))['sha256']
    assert len(effect['jobs'])==2 and [j['family'] for j in effect['jobs']]==['sd15','sdxl']
    for j in effect['jobs']:
        baseline=by_name[j['family']+'-lcm-a']
        assert j['passed'] and j['returncode']==0 and not j['protocol_errors'] and not j['timed_out'] and not j['forced_host_termination'] and not any(j['logs_truncated'])
        assert j['diagnostic_only'] and not j['app_recipe'] and j['only_scale_changed'] and j['enabled_weights_change_output']
        assert j['parameters']==baseline['parameters'] and j['enabled_scale']==1. and j['diagnostic_scale']==0.
        assert j['enabled_image_sha256']==baseline['image']['sha256'] and j['image']['sha256']!=baseline['image']['sha256']
        image=j['image']; assert (image['width'],image['height'],image['format'],image['mode'])==(512,512,'PNG','RGB')
        assert image['bytes']>10000 and all(math.isfinite(v) and 1<v<=128 for v in image['channel_stddev'])
        assert j['resources']['observed'] and j['resources']['samples']>0 and j['resources']['observed_peak_working_set_bytes']>0
        assert not j['resources']['physical_device_memory_measured'] and not j['resources']['gpu_memory_measured']
        assert j['sampling_steps_observed']==list(range(5)) and len(j['adapters'])==1 and j['adapters'][0]['scale']==0.
        assert effect['files'][j['name']+'.png']=={k:j['image'][k] for k in ['bytes','sha256']}
    controls = direct['controls']; assert len(controls) == 8 and len({c['name'] for c in controls}) == 8
    for c in controls:
        assert c['passed'] and c['returncode'] != 0 and not c['output_exists'] and not c['timed_out'] and not c['protocol_errors'] and not any(c['logs_truncated'])
        assert not any(e.get('event') == 'complete' for e in c['events'])
        if 'cancel-step1' in c['name']:
            t = c['cancel_trigger']; assert c['forced_host_termination'] and t in c['events'] and t['event'] == 'progress' and t['stage'] == 'generating'
            assert t['steps'] == 4 and 1 <= t['step'] < 4 and c['cancel_to_exit_seconds'] >= 0 and not c['android_cooperative_cancellation_tested']
        else:
            assert c['returncode'] == 1 and not c['forced_host_termination'] and [e['message'] for e in c['events'] if e.get('event')=='error'] == [c['expected_error']]
    assert direct['info']['events'] == [dict(schema='lma.engine/1',engine='sd_cpp',revision=compilation['source_revision'],backend='cpu',bundled_model_data=False,generation_tested=False)]
    assert app['schema'] == 'lma.sd-variants-app-host/1' and app['production_java_native_host_executed'] and not any(app[key] for key in FALSE_APP)
    assert app['direct_trained_report_sha256'] == identity(record_path(root, 'sd-variants-trained.json'))['sha256']
    java = app['java']; assert java['passed'] >= 100 and java['actual_host_children'] == len(java['runs']) == len(java['launches']) == 8
    assert java['network_calls'] == 0 and java['imported_objects'] == 7 and java['imported_unique_bytes'] == 4891569203 and java['host_java_production_binding']
    composed=java['production_hf_recipes_composed']; assert len(composed)==5 and [item['asset'] for item in composed]==[item['id'] for item in lock['assets']]
    assert len({item['bundle_id'] for item in composed})==5 and all(item['bundle_id'].startswith('hfb_') for item in composed)
    for selected,asset in zip(composed,lock['assets']):
        component=next(c for c in selected['components'] if c['role']==asset['role'])
        assert {k:component[k] for k in ['repository','revision','path','bytes','sha256','url']}=={k:asset[k] for k in ['repository','revision','path','bytes','sha256','url']}
    assert java['host_metadata_port']=='windows_atomic_replace_functional_only' and not java['host_metadata_fsync']
    assert not any(java[k] for k in ['android_application_executed','android_saf_tested','android_background_tested','image_quality_accepted',
                                   'java_cancel_at_sampler_step_tested','metadata_power_loss_durability_tested','android_atomicfile_tested'])
    for command,run in zip(java['launches'],java['runs']):
        assert command['pipeline'] == run['family'] and command['architecture'] == run['family'] and command['samplingProfile'] == 'lcm'
        p = command['parameters']; assert p['steps'] == 4 and p['cfg'] == 1 and p['sampler'] == p['scheduler'] == 'lcm' and p['seed'] == 42 and p['threads'] == 6
        assert len(command['loras']) == 2 and [item['scale'] for item in command['loras']] == [1., .9 if run['family']=='sd15' else 1.2]
        if run['name'].endswith('empty-prompt'): assert command['input']['prompt'] == '' and run['expected_error'] == 'Invalid prompt or output' and not run['cancelled']
        elif run['name'].endswith('cancel-stage-entry'): assert run['cancelled'] and any(e['stage']=='generating' and e['fraction'] is None for e in run['progress'])
    assert len(app['outputs']) == 4
    for output in app['outputs']:
        assert output['bitwise_equal_to_direct_native'] and output['image']['sha256'] == by_name[output['family']+'-lcm-style']['image']['sha256']
    assert status['sd_variants_trained_production_source_host_executed'] and status['sd_variants_production_java_native_host_executed'] and status['sd_variants_lcm_weights_effect_host_tested']
    assert status['sd_variants_trained_host_execution_checks_passed'] and not status['sd_variants_image_quality_accepted']
    assert not status['sd_variants_complete_android_image_tested'] and not status['release_ready'] and not status['all_selected_models_supported']
    if with_audit:
        audit = records['sd-variants-capture-audit.json']; current(audit['input_fingerprint'])
        assert audit['schema'] == 'lma.sd-variants-capture-audit/1' and audit['raw_capture_audit_passed'] and audit['direct_protocols'] == 25
        assert audit['actual_java_native_children'] == 8 and audit['png_files'] == 20 and audit['full_trained_objects'] == 7 and audit['full_imported_objects'] == 7
        assert len(audit['negative_controls']) == 9 and all(item['rejected'] for item in audit['negative_controls'])
        assert not any(audit[k] for k in ['physical_android','image_quality_accepted','complete_release_accepted'])
        assert audit['files'] >= 100
        for name,expected_sha in audit['sources'].items(): assert identity(record_path(root,name))['sha256'] == expected_sha
    if with_media:
        media = load(root/'docs/media/development/sd-variants-trained-media.json'); current(media['input_fingerprint'])
        assert media['schema'] == 'lma.sd-variants-trained-media/1' and not any(media[k] for k in ['physical_android','app_screen_recording','semantic_quality_accepted','complete_release_accepted'])
        assert media['source_pngs'] == {j['name']:j['image']['sha256'] for j in jobs+effect['jobs']}
        assert media['slideshow_frames']==16 and media['original_pngs_copied_without_reencoding']
        for j in jobs+effect['jobs']:
            assert identity(root/'docs/media/development'/('sd-variants-'+j['name']+'.png'))=={k:j['image'][k] for k in ['bytes','sha256']}
        for name,expected_identity in media['files'].items(): assert identity(root/'docs/media/development'/name) == expected_identity
        for name,sha in media['sources'].items(): assert identity(root/name)['sha256'] == sha


def raw_audit(records):
    from fetch_sd15_trained import asset_path as sd15_path
    from fetch_sd_variants_trained import asset_path
    from test_sd_variants_trained import image_stats
    direct,app,effect = records['sd-variants-trained.json'],records['sd-variants-app-host.json'],records['sd-variants-lcm-effect.json']
    files = 0; protocols = 0; pngs = 0
    for report in [direct,effect,app]:
        directory = (ROOT/report['capture_directory']).resolve(); directory.relative_to((ROOT/'build').resolve())
        for name,expected in report['files'].items():
            path = (directory/name).resolve(); path.relative_to(directory); assert identity(path) == expected; files += 1
            if path.suffix == '.png':
                stats = image_stats(path); assert stats['format'] == 'PNG' and all(v>1 for v in stats['channel_stddev']); pngs += 1
    directory = ROOT/direct['capture_directory']
    for name,c in [('info',direct['info'])] + [(c['name'],c) for c in direct['jobs']+direct['controls']]:
        raw = (directory/(name+'.stdout')).read_bytes(); events = [json.loads(line) for line in raw.splitlines()]
        assert events == c['events']; protocols += 1
        if name != 'info':
            request = directory/(name+'.json'); assert identity(request)['sha256'] == c['request_sha256']
            assert load(directory/(name+'-capture.json')) == c
    effect_dir=ROOT/effect['capture_directory']
    def normalized_request(value):
        def relative(name):
            assert len(name)>3 and name[0] in 'TUVWXYZ' and name[1:3]==':/'
            path=(ROOT/name[3:]).resolve();return path.relative_to(ROOT.resolve()).as_posix()
        normalized=copy.deepcopy(value);normalized.pop('output')
        normalized['components']={k:relative(v) for k,v in value['components'].items()}
        for item in normalized['loras']:item['path']=relative(item['path'])
        return normalized
    for j in effect['jobs']:
        name=j['name'];assert [json.loads(line) for line in (effect_dir/(name+'.stdout')).read_bytes().splitlines()]==j['events'];protocols+=1
        request=effect_dir/(name+'.json');assert identity(request)['sha256']==j['request_sha256'] and load(effect_dir/(name+'-capture.json'))==j
        enabled=normalized_request(load(directory/(j['baseline_name']+'.json')));disabled=normalized_request(load(request))
        assert enabled['loras'][0]['scale']==1. and disabled['loras'][0]['scale']==0.
        disabled['loras'][0]['scale']=1.;assert enabled==disabled
    assert protocols == 25 and pngs == 20
    assert load(ROOT/app['capture_directory']/'data/java-results.json') == app['java']
    assert json.loads((ROOT/app['capture_directory']/'java.stdout').read_text(encoding='utf-8')) == app['java']
    assets = records['sd-variants-assets.json']['assets']; all_assets = [(asset_path(item),item) for item in assets]
    all_assets += [(sd15_path(item),item) for item in direct['existing_sd15_bundle']['components']]
    for path,item in all_assets: assert identity(path) == {k:item[k] for k in ['bytes','sha256']}
    imported=ROOT/app['capture_directory']/'data/files/bundles/objects'
    assert {p.name for p in imported.iterdir()}=={item['sha256'] for _,item in all_assets}
    for _,item in all_assets: assert identity(imported/item['sha256'])=={k:item[k] for k in ['bytes','sha256']}
    assert identity(ROOT/direct['compilation']['executable']) == {k:direct['compilation'][k] for k in ['bytes','sha256']}
    return dict(files=files, direct_protocols=protocols, actual_java_native_children=8, png_files=pngs, full_trained_objects=len(all_assets),full_imported_objects=len(all_assets))


def main():
    before = fingerprint('tools/check_sd_variants_trained_evidence.py')
    records = {key:load(ROOT/path) for key,path in PATHS.items() if key!='sd-variants-capture-audit.json'}
    records['sd15-host-build.json'] = records['sd-variants-trained.json']['compilation']
    status = dict(sd_variants_trained_production_source_host_executed=True,sd_variants_production_java_native_host_executed=True,
                  sd_variants_lcm_weights_effect_host_tested=True,sd_variants_trained_host_execution_checks_passed=True,
                  sd_variants_image_quality_accepted=False,sd_variants_complete_android_image_tested=False,release_ready=False,all_selected_models_supported=False)
    check(records,status,with_audit=False,with_media=False); counts = raw_audit(records); negatives = []
    def mutate_asset(r): r['sd-variants-assets.json']['assets'][0]['bytes'] -= 1
    def mutate_encoder(r):
        next(t for t in r['sd-variants-trained.json']['headers']['sdxl_base_q4_0']['tensors']
             if t['name']=='cond_stage_model.1.transformer.text_model.embeddings.token_embedding.weight')['shape'][0] += 1
    def mutate_cancel(r): next(c for c in r['sd-variants-trained.json']['controls'] if 'cancel-step1' in c['name'])['cancel_trigger']['step'] = 0
    def mutate_style(r):
        jobs = {j['name']:j for j in r['sd-variants-trained.json']['jobs']}; jobs['sd15-style-one']['image']['sha256'] = jobs['sd15-base-a']['image']['sha256']
    def mutate_zero(r): next(j for j in r['sd-variants-trained.json']['jobs'] if j['name']=='sdxl-style-zero')['image']['sha256'] = '0'*64
    def mutate_lcm(r):
        job=r['sd-variants-lcm-effect.json']['jobs'][0];job['image']['sha256']=job['enabled_image_sha256']
    for name,mutate in [('promote-physical',lambda r:r['sd-variants-trained.json'].update(physical_android=True)),
                        ('promote-quality',lambda r:r['sd-variants-trained.json'].update(semantic_quality_accepted=True)),
                        ('changed-complete-asset',mutate_asset),('changed-sdxl-encoder',mutate_encoder),
                        ('cancel-before-sampler',mutate_cancel),('ignored-style-adapter',mutate_style),('changed-zero-scale-output',mutate_zero),
                        ('changed-java-output',lambda r:r['sd-variants-app-host.json']['outputs'][0]['image'].update(sha256='0'*64)),
                        ('ignored-lcm-weights',mutate_lcm)]:
        altered = copy.deepcopy(records); mutate(altered); rejected = False
        try: check(altered,status,with_audit=False,with_media=False)
        except (AssertionError,ValueError,KeyError): rejected = True
        if not rejected: raise AssertionError('False evidence accepted: '+name)
        negatives.append(dict(name=name,rejected=True))
    current(before)
    report = dict(schema='lma.sd-variants-capture-audit/1',raw_capture_audit_passed=True,**counts,negative_controls=negatives,
                  sources={key:identity(ROOT/path)['sha256'] for key,path in PATHS.items() if key!='sd-variants-capture-audit.json'},
                  physical_android=False,image_quality_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    (ROOT/PATHS['sd-variants-capture-audit.json']).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(**counts,negative_controls=len(negatives),raw_capture_audit_passed=True)))


if __name__ == '__main__': main()
