"""Audit retained complete SD-Turbo/LCM experiments and production Java/native captures.

Exports bounded HOST observations; never substitutes them for Android or quality acceptance.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

from evidence import current, fingerprint
from fetch_sd15_trained import sha, asset_path as sd15_path, bundle
from fetch_sd_distilled_trained import selected, asset_path, inputs as asset_inputs
from build_sd_host import inputs as build_inputs
from test_sd_turbo_app_host import inputs as app_inputs
from test_sd_variants_trained import image_stats

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'build/sd-distilled-asset-probe'
OUT = ROOT / 'build/sd-distilled-tests'
PUBLIC = ROOT / 'verification/development'
FILES = ['sd-distilled-assets.json', 'sd-distilled-native.json', 'sd-distilled-lcm-analysis.json',
         'sd-turbo-app-host.json', 'sd-distilled-capture-audit.json']


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def identity(path): return dict(bytes=path.stat().st_size, sha256=sha(path))
def stats(path): return json.loads(json.dumps(image_stats(path)))
def inputs():
    return {**build_inputs(), **asset_inputs(), **app_inputs(), **fingerprint(
        'tools/check_sd_distilled_evidence.py', 'tools/replay_sd_turbo_native.py', 'research/sd_distilled_trained')}


def bounded(path, parent):
    resolved = path.resolve(); resolved.relative_to(parent.resolve())
    if path.is_symlink() or not path.is_file(): raise ValueError('Expected owned regular capture file')
    return resolved


def capture(report):
    folder = bounded_directory(ROOT / report['capture_directory'], PRIVATE)
    for job in report['jobs']:
        name = job['name']; request = load(folder / (name + '.json'))
        raw = (folder / (name + '.stdout')).read_bytes()
        assert len(raw) < 2 * 1024 * 1024
        events = [json.loads(line) for line in raw.splitlines()]
        assert events == job['events'] and load(folder / (name + '-capture.json')) == job
        assert not job['timed_out'] and not job['protocol_errors'] and not any(job['logs_truncated']) and job['passed']
        assert request['schema'] == 'lma.engine-request/1' and request['type'] == 'image.generate' and request['loras'] == []
        assert request['parameters'] == job['parameters'] and request['parameters']['width'] == request['parameters']['height'] == 512
        assert request['parameters']['seed'] == 42 and request['parameters']['threads'] == 6
        assert job['resources']['observed'] and job['resources']['samples'] > 0 and job['resources']['observed_peak_working_set_bytes'] > 0
        assert not job['resources']['gpu_memory_measured'] and not job['resources']['physical_device_memory_measured']
        generating = [e for e in events if e.get('event') == 'progress' and e.get('stage') == 'generating'
                      and e.get('steps') == request['parameters']['steps']]
        if 'image' in job:
            image = folder / (name + '.png'); assert stats(image) == job['image']
            assert job['returncode'] == 0 and not job['forced_host_termination'] and job['cancel_trigger'] is None
            assert [e['step'] for e in generating] == list(range(request['parameters']['steps'] + 1))
            assert len([e for e in events if e.get('event') == 'complete']) == 1
        elif name == 'invalid-cfg':
            assert job['returncode'] == 1 and not job['forced_host_termination'] and not (folder / (name + '.png')).exists()
            assert [e['message'] for e in events if e.get('event') == 'error'] == ['Distilled sampling parameters do not match the frozen plan']
        else:
            assert name == 'cancel-step1' and job['returncode'] != 0 and job['forced_host_termination']
            assert job['cancel_trigger'] in generating and job['cancel_trigger']['step'] == 1 and job['cancel_trigger']['steps'] == 4
            assert math.isfinite(job['cancel_to_exit_seconds']) and 0 <= job['cancel_to_exit_seconds'] < 10
            assert not (folder / (name + '.png')).exists() and not any(e.get('event') == 'complete' for e in events)
    return {p.relative_to(ROOT).as_posix(): identity(p) for p in folder.iterdir() if p.is_file()}


def bounded_directory(path, parent):
    resolved = path.resolve(); resolved.relative_to(parent.resolve())
    if path.is_symlink() or not path.is_dir(): raise ValueError('Expected owned capture directory')
    return resolved


def archived(name, captured_sha=None):
    path = ROOT / 'research/sd_distilled_trained/experiments' / name
    original = PRIVATE / name
    assert identity(path) == identity(original)
    if captured_sha: assert sha(path) == captured_sha
    return dict(file=path.relative_to(ROOT).as_posix(), **identity(path))


def observations():
    before = inputs(); lock = selected(); assets = load(PRIVATE / 'public-asset-receipt.json')
    current(assets['input_fingerprint']); assert assets['lock'] == lock and assets['developer_assets_only']
    assert not assets['model_executed'] and not assets['app_assets_modified']
    turbo = load(PRIVATE / 'sd-turbo-probe-results.json'); lcm = load(PRIVATE / 'lcm-checkpoint-probe-results.json')
    for report in [turbo, lcm]:
        current(report['input_fingerprint']); current(report['compilation']['input_fingerprint'])
        assert report['compilation']['input_fingerprint'] == build_inputs() and report['host_checks_passed'] and report['recovery_matches']
        assert not any(report[k] for k in ['production_app_executed','physical_android','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
        assert len(report['jobs']) == 5 and report['compilation']['production_worker_source_unmodified']
    assert turbo['compilation'] == lcm['compilation']
    assert turbo['jobs'][0]['image']['sha256'] != turbo['jobs'][1]['image']['sha256']
    assert lcm['condition_fold_changes_native_image'] and lcm['jobs'][0]['image']['sha256'] != lcm['jobs'][1]['image']['sha256']
    raw_files = {**capture(turbo), **capture(lcm)}
    for key, report in [('sd_turbo', turbo), ('lcm_checkpoint', lcm)]:
        for job in report['jobs']:
            request = load(ROOT / report['capture_directory'] / (job['name'] + '.json'))
            assert request['pipeline'] == ('sd21_turbo' if key == 'sd_turbo' else 'sd15_lcm')
            assert request['architecture'] == ('sd21' if key == 'sd_turbo' else 'sd15')
            assert request['samplingProfile'] == ('sd_turbo' if key == 'sd_turbo' else 'lcm')
    comparison = load(PRIVATE / 'lcm-full-unet-comparison.json'); fold = load(PRIVATE / 'lcm-full-unet-fold-results.json')
    bias_comparison=load(PRIVATE/'lcm-bias-comparison.json')
    assert bias_comparison['original_projection_nonzero_elements']==81920 and bias_comparison['original_condition_projection_shape']==[320,256]
    assert not bias_comparison['candidate_has_named_projection'] and all(c['equals_original_cast'] for c in bias_comparison['comparisons'])
    derivation = load(PRIVATE / 'lcm-fixed-guidance-derivation.json'); mapping = load(PRIVATE / 'lcm-tensor-mapping.json')
    schedule = load(PRIVATE / 'lcm-schedule-version-comparison.json'); subgraph = load(PRIVATE / 'lcm-condition-fold-probe.json')
    assert comparison['full_object_sha256s_reverified'] and comparison['all_mapped_values_equal_original_cast']
    assert comparison['mapped_tensors'] == 686 and comparison['parameters_compared'] == 859520964 and comparison['mismatch_tensors'] == 0
    assert len(comparison['metrics']) == 686 and all(m['mismatches_from_original_cast'] == 0 for m in comparison['metrics'])
    assert mapping['mapped_tensors'] == 686 and len(mapping['missing']) == 1 and not mapping['unexpected_candidate']
    assert fold['original_tensors'] == 687 and fold['original_parameters'] == 859602884 and fold['forward_calls'] == 30
    assert fold['paired_full_unet_fold_checks_passed'] and fold['folded_bias_matches_prepared_candidate'] and fold['network_attempts'] == 0
    assert fold['omitted_branch_negative_controls'] == 6 and fold['cpu_threads'] == 1
    assert fold['guidance'] == 8.5 and fold['synthetic_latents_and_text_conditioning'] and fold['reduced_latent_geometries'] == [[1,4,8,8],[1,4,16,16]]
    assert not any(fold[k] for k in ['native_cpp_forward','complete_canonical_image_pipeline','product_preparation_implemented','physical_android','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
    assert derivation['source_parameter_comparison_sha256'] == sha(PRIVATE / 'lcm-full-unet-comparison.json')
    assert derivation['output'] == fold['prepared_output'] == lcm['derivation']['output']
    assert derivation['changed_region_bytes'] == 5120 and derivation['changed_bytes'] == 4987 and derivation['unchanged_file_length']
    assert derivation['distilled_guidance_embedding'] == 8.5 and derivation['sampler_cfg'] == 1 and derivation['fixed_guidance_only']
    import numpy as np
    fold_folder=bounded_directory(ROOT/fold['capture_directory'],PRIVATE)
    assert load(fold_folder/'results.json') == fold
    pairs={'omitted-branch-vs-original':('original-omitted-branch-f32','original-conditioned-f32'),
        'f32-folded-vs-conditioned':('original-folded-f32','original-conditioned-f32'),
        'converted-conditioned-vs-original-f32':('converted-conditioned-f32-compute','original-conditioned-f32'),
        'converted-folded-vs-converted-conditioned':('converted-folded-f32-compute','converted-conditioned-f32-compute')}
    assert len(fold['metrics']) == 24 and len(list(fold_folder.glob('*.f32'))) == 30
    for metric in fold['metrics']:
        a,b=pairs[metric['name']];case=metric['case'];arrays=[]
        assert case in range(6) and metric['timestep']==[0,1,249,499,749,999][case]
        assert metric['shape']==[1,4,8 if case%2==0 else 16,8 if case%2==0 else 16]
        for prefix in [a,b]:
            path=bounded(fold_folder/(prefix+'-'+str(case)+'.f32'),fold_folder)
            value=np.fromfile(path,dtype='<f4').astype(np.float64)
            assert value.size==math.prod(metric['shape']) and np.isfinite(value).all();arrays.append(value)
            raw_files[path.relative_to(ROOT).as_posix()]=identity(path)
        x,y=arrays;delta=(x.astype(np.float32)-y.astype(np.float32)).astype(np.float64)
        actual=dict(max_abs=float(np.max(np.abs(delta))),rmse=float(np.sqrt(np.mean(delta*delta))),
            cosine=float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y))))
        for key,value in actual.items():assert math.isclose(value,metric[key],rel_tol=1e-7,abs_tol=1e-12)
        if metric['numerical_gate']:
            assert actual['max_abs']<=2e-4 and actual['rmse']<=5e-5 and actual['cosine']>=.99999
        elif metric['name']=='omitted-branch-vs-original':assert actual['max_abs']>2e-4
    forward_log=PRIVATE/'lcm-full-unet-fold-retry.log';forward_events=[]
    for line in forward_log.read_text(encoding='utf-8').splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if 'phase' in event and 'output_sha256' in event:forward_events.append(event)
    assert len(forward_events)==30
    assert len({(e['phase'],e['case']) for e in forward_events})==30
    for event in forward_events:
        path=fold_folder/(event['phase']+'-'+str(event['case'])+'.f32')
        assert sha(path)==event['output_sha256'] and event['seconds']>0
    raw_files[forward_log.relative_to(ROOT).as_posix()]=identity(forward_log)
    sources = {name:archived(name) for name in ['probe_sd_turbo.py','probe_lcm_checkpoint.py','inspect_lcm_header.py',
        'compare_lcm_bias.py','map_lcm_tensors.py','compare_lcm_unet.py','probe_condition_fold.py','probe_lcm_schedules.py']}
    sources['prepare_lcm_bias_experiment.py'] = archived('prepare_lcm_bias_experiment.py',derivation['experiment_source_sha256'])
    sources['probe_lcm_full_unet_fold.py'] = archived('probe_lcm_full_unet_fold.py',fold['experiment_source_sha256'])
    assert schedule['experiment_source_sha256']==sources['probe_lcm_schedules.py']['sha256']
    assert schedule['extracted_block_compiled_and_executed'] and schedule['official_python_method_executed']
    assert [c['steps'] for c in schedule['cases'] if c['equal']]==[1,2,5,7]
    assert [c['steps'] for c in schedule['cases'] if not c['equal']]==[3,4,6,8]
    for name in ['diffusers-reference.json','diffusers-package-reference.json','diffusers-scheduler-reference.json','original-unet--config.json']:
        assert identity(PRIVATE / name) == identity(ROOT / 'research/sd_distilled_trained' / name)
    native = dict(schema='lma.sd-distilled-native-host/1', sd_turbo=copy.deepcopy(turbo), lcm_checkpoint=copy.deepcopy(lcm),
        archived_experiment_sources=sources, host_execution_checks_passed=True, physical_android=False,
        source_native_reports={str((PRIVATE/name).relative_to(ROOT)):sha(PRIVATE/name) for name in ['sd-turbo-probe-results.json','lcm-checkpoint-probe-results.json']},
        product_lcm_preparation_implemented=False, canonical_lcm_pipeline_equivalence=False, image_quality_accepted=False,
        complete_target03_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    # Preserve old hashes as historical provenance, not current public source inputs.
    for report in [native['sd_turbo'], native['lcm_checkpoint']]: report['captured_source_hashes'] = report.pop('input_fingerprint')
    analysis = dict(schema='lma.lcm-condition-analysis-host/1', complete_parameter_comparison=comparison, tensor_mapping=mapping,
        bias_projection_comparison=bias_comparison,
        timestep_subgraph=subgraph, fixed_guidance_derivation=derivation, complete_trained_unet=fold,
        scheduler_version_observation=schedule, archived_experiment_sources=sources, numerical_fold_checks_passed=True,
        trained_unet_forward_calls=30, synthetic_reduced_latents=True, complete_canonical_image_pipeline=False,
        product_preparation_implemented=False, physical_android=False, image_quality_accepted=False,
        complete_target03_accepted=False, complete_release_accepted=False, input_fingerprint=before)
    app = load(ROOT / 'build/sd-turbo-app-host-tests/results.json'); current(app['input_fingerprint']); assert app['input_fingerprint'] == app_inputs()
    assert app['schema'] == 'lma.sd-turbo-app-host/1' and app['production_java_native_host_executed'] and len(app['outputs']) == 3
    java = app['java']; assert java['actual_host_children'] == 5 and java['network_calls'] == 0 and java['imported_objects'] == 2 and java['imported_unique_bytes'] == 2024269995
    assert java['host_metadata_port'] == 'windows_atomic_replace_functional_only' and not java['host_metadata_fsync']
    assert not any(java[k] for k in ['android_application_executed','android_saf_tested','android_background_tested','image_quality_accepted','java_cancel_at_sampler_step_tested','metadata_power_loss_durability_tested','android_atomicfile_tested'])
    assert not any(app[k] for k in ['asset_download_attempted','physical_android','android_saf_tested','android_background_accepted','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
    assert app['direct_trained_report_sha256'] == sha(PRIVATE / 'sd-turbo-probe-results.json') and app['compilation'] == turbo['compilation']
    folder = bounded_directory(ROOT / app['capture_directory'], ROOT / 'build/sd-turbo-app-host-tests')
    for name, expected in app['files'].items():
        path = bounded(folder / name, folder); assert identity(path) == expected; raw_files[path.relative_to(ROOT).as_posix()] = expected
    assert load(folder / 'data/java-results.json') == java
    assert json.loads((folder/'java.stdout').read_text(encoding='utf-8'))==java
    by_name = {j['name']:j for j in turbo['jobs']}
    for output in app['outputs']:
        assert stats(bounded(ROOT / output['file'], folder)) == output['image']
        assert output['bitwise_equal_to_direct_native'] and output['image']['sha256'] == by_name[output['name']]['image']['sha256']
    current(before)
    return assets, native, analysis, app, raw_files


def prepared_difference(analysis):
    descriptor=analysis['fixed_guidance_derivation'];item=selected()['assets'][1]
    source=asset_path(item);target=ROOT/descriptor['output']['path']
    header=load(PRIVATE/'lcm-checkpoint-header.json')
    tensor=next(t for t in header['tensors'] if t['name']==descriptor['changed_tensor'])
    assert tensor['ggml_type']==0 and tensor['bytes']==5120 and tensor['shape']==[1280]
    offset=header['data_offset']+tensor['offset'];position=0;changed=0
    original=hashlib.sha256();prepared=hashlib.sha256()
    with source.open('rb') as a,target.open('rb') as b:
        while x:=a.read(4*1024*1024):
            y=b.read(len(x));assert len(y)==len(x);original.update(x);prepared.update(y)
            left=max(0,offset-position);right=min(len(x),offset+5120-position)
            if left<right:
                assert x[:left]==y[:left] and x[right:]==y[right:]
                changed+=sum(i!=j for i,j in zip(x[left:right],y[left:right]))
            else:assert x==y
            position+=len(x)
        assert not b.read(1)
    assert position==item['bytes']==target.stat().st_size==descriptor['output']['bytes']
    assert changed==4987 and original.hexdigest()==item['sha256'] and prepared.hexdigest()==descriptor['output']['sha256']
    return dict(bytes=position,sha256=original.hexdigest())


def check(records, status, root=ROOT):
    for name in FILES:
        current(records[name]['input_fingerprint'])
    assets,native,analysis,app,audit = [records[name] for name in FILES]
    assert assets['lock'] == selected() and assets['developer_assets_only'] and not assets['app_assets_modified']
    assert native['host_execution_checks_passed'] and analysis['numerical_fold_checks_passed'] and app['production_java_native_host_executed']
    assert audit['raw_capture_audit_passed'] and audit['native_children'] == 10 and audit['java_native_children'] == 5 and audit['png_files'] == 9 and audit['trained_unet_forward_calls'] == 30
    assert audit['full_original_objects'] == 4 and audit['full_imported_objects'] == 2 and len(audit['negative_controls']) >= 5
    assert not any(native[k] for k in ['physical_android','product_lcm_preparation_implemented','canonical_lcm_pipeline_equivalence','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
    assert not any(analysis[k] for k in ['complete_canonical_image_pipeline','product_preparation_implemented','physical_android','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
    assert not any(app[k] for k in ['physical_android','android_saf_tested','android_background_accepted','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
    for key,names in [('sd_turbo',['one-step','four-step','invalid-cfg','cancel-step1','recovery']),
        ('lcm_checkpoint',['converted-original','fixed-guidance8p5','invalid-cfg','cancel-step1','recovery'])]:
        report=native[key];assert report['host_checks_passed'] and report['recovery_matches'] and len(report['jobs'])==5
        assert [j['name'] for j in report['jobs']]==names
        assert report['compilation']['input_fingerprint']==build_inputs()
        assert not any(report[k] for k in ['production_app_executed','physical_android','image_quality_accepted','complete_target03_accepted','complete_release_accepted'])
        assert report['jobs'][1]['image']['sha256']==report['jobs'][4]['image']['sha256']
        assert report['jobs'][0]['image']['sha256']!=report['jobs'][1]['image']['sha256']
        assert report['jobs'][3]['cancel_trigger']['step']==1 and report['jobs'][3]['cancel_trigger']['steps']==4
        assert report['jobs'][2]['returncode']==1 and all(j['passed'] and not j['timed_out'] and not j['protocol_errors'] for j in report['jobs'])
    java=app['java'];assert java['actual_host_children']==5 and java['network_calls']==0 and java['imported_objects']==2 and java['imported_unique_bytes']==2024269995
    assert len(java['runs'])==5 and len(java['launches'])==5 and len(app['outputs'])==3
    by_name={j['name']:j for j in native['sd_turbo']['jobs']}
    for output in app['outputs']:
        assert output['bitwise_equal_to_direct_native'] and output['image']['sha256']==by_name[output['name']]['image']['sha256']
        assert output['image']['width']==output['image']['height']==512
    folded=analysis['complete_trained_unet'];assert folded['forward_calls']==30 and folded['original_parameters']==859602884 and folded['paired_full_unet_fold_checks_passed']
    assert folded['numerical_gates']==dict(max_abs=2e-4,rmse=5e-5,min_cosine=.99999) and len(folded['metrics'])==24
    for metric in folded['metrics']:
        assert all(math.isfinite(metric[k]) for k in ['max_abs','rmse','cosine'])
        if metric['numerical_gate']:assert metric['max_abs']<=2e-4 and metric['rmse']<=5e-5 and metric['cosine']>=.99999
        elif metric['name']=='omitted-branch-vs-original':assert metric['max_abs']>2e-4
    assert status['sd_turbo_production_java_native_host_executed'] and status['lcm_checkpoint_fixed_guidance_native_host_tested']
    assert status['lcm_checkpoint_complete_trained_unet_fold_host_tested'] and not status['sd_distilled_complete_android_image_tested']
    assert not status['sd_distilled_image_quality_accepted'] and not status['lcm_checkpoint_product_preparation_implemented']
    for name in FILES[:-1]: assert audit['sources'][name] == hashlib.sha256((root/'verification/development'/name).read_bytes()).hexdigest()
    media_path=root/'docs/media/development/sd-distilled-trained-media.json'
    # The isolated negative controls validate record semantics before media copying.
    if root==ROOT or media_path.exists():
        media=load(media_path);current(media['input_fingerprint'])
        assert media['sources']==native['source_native_reports'] and media['original_pngs_copied_without_reencoding']
        assert not any(media[k] for k in ['physical_android','app_screen_recording','semantic_quality_accepted','complete_release_accepted'])
        assert media['slideshow_frames']==4 and media['gif_duration_ms']==8800 and media['mp4_frames']==88 and media['mp4_fps']==10
        for family,report,names in [('sd-turbo',native['sd_turbo'],['one-step','four-step']),('lcm-checkpoint',native['lcm_checkpoint'],['converted-original','fixed-guidance8p5'])]:
            jobs={j['name']:j for j in report['jobs']}
            for name in names:
                key=family+'-'+name;assert media['source_pngs'][key]==jobs[name]['image']['sha256']
                assert identity(root/'docs/media/development'/('sd-distilled-'+key+'.png'))=={k:jobs[name]['image'][k] for k in ['bytes','sha256']}
        for name,expected in media['files'].items():assert identity(root/'docs/media/development'/name)==expected


def main():
    assets,native,analysis,app,raw_files = observations(); before = inputs()
    executable=ROOT/native['sd_turbo']['compilation']['executable']
    assert identity(executable)=={k:native['sd_turbo']['compilation'][k] for k in ['bytes','sha256']}
    # Whole developer originals, prepared candidate and imported object store are re-read independently.
    compared=prepared_difference(analysis);complete = []
    for item in selected()['assets']:
        path = asset_path(item);actual=compared if item['id']=='lcm_dreamshaper_v7_f16' else identity(path)
        assert actual == {k:item[k] for k in ['bytes','sha256']};complete.append(dict(id=item['id'],**actual))
    merges = next(c for c in bundle()['components'] if c['role']=='clip_merges')
    assert identity(sd15_path(merges)) == {k:merges[k] for k in ['bytes','sha256']}; complete.append(dict(id='clip_merges',**identity(sd15_path(merges))))
    prepared = analysis['fixed_guidance_derivation']['output']; prepared_path = ROOT / prepared['path']
    imported = ROOT / app['capture_directory'] / 'data/files/bundles/objects'
    assert {p.name for p in imported.iterdir()}=={selected()['assets'][0]['sha256'],merges['sha256']}
    for item in [selected()['assets'][0],merges]:
        path = imported / item['sha256']; assert identity(path) == {k:item[k] for k in ['bytes','sha256']}
    OUT.mkdir(parents=True,exist_ok=True)
    values = dict(zip(FILES[:-1],[assets,native,analysis,app]))
    for name, value in values.items(): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sources = {name:sha(OUT/name) for name in values}
    status = dict(sd_turbo_production_java_native_host_executed=True,lcm_checkpoint_fixed_guidance_native_host_tested=True,
        lcm_checkpoint_complete_trained_unet_fold_host_tested=True,sd_distilled_complete_android_image_tested=False,
        sd_distilled_image_quality_accepted=False,lcm_checkpoint_product_preparation_implemented=False)
    negatives=[]
    audit=dict(schema='lma.sd-distilled-capture-audit/1',raw_capture_audit_passed=True,native_children=10,java_native_children=5,png_files=9,
        trained_unet_forward_calls=30,full_original_objects=4,full_imported_objects=2,originals=complete,prepared_candidate=prepared,
        files=raw_files,sources=sources,negative_controls=['pending']*5,physical_android=False,image_quality_accepted=False,
        complete_target03_accepted=False,complete_release_accepted=False,input_fingerprint=before)
    values[FILES[-1]]=audit
    # Validate against the just-written source records without rewriting existing public evidence early.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='sd-distilled-audit-',dir=ROOT/'build/tmp') as tmp:
        scratch=Path(tmp); target=scratch/'verification/development';target.mkdir(parents=True)
        for name in FILES[:-1]: (target/name).write_bytes((OUT/name).read_bytes())
        check(values,status,scratch)
        for name,section,field in [('promote-android','sd-distilled-native.json','physical_android'),
            ('promote-quality','sd-distilled-lcm-analysis.json','image_quality_accepted'),
            ('promote-product-preparation','sd-distilled-native.json','product_lcm_preparation_implemented'),
            ('promote-complete-target','sd-turbo-app-host.json','complete_target03_accepted')]:
            changed=copy.deepcopy(values);changed[section][field]=True
            try: check(changed,status,scratch)
            except AssertionError: negatives.append(name)
            else: raise AssertionError('Incorrect promotion accepted')
        changed=copy.deepcopy(values);changed[FILES[-1]]['java_native_children']=0
        try:check(changed,status,scratch)
        except AssertionError:negatives.append('missing-actual-java-children')
        else:raise AssertionError('Incorrect child count accepted')
        for name,mutate in [('changed-output',lambda r:r['sd-turbo-app-host.json']['outputs'][0]['image'].update(sha256='0'*64)),
            ('changed-cancel-step',lambda r:r['sd-distilled-native.json']['lcm_checkpoint']['jobs'][3]['cancel_trigger'].update(step=0)),
            ('relaxed-numerical-gate',lambda r:r['sd-distilled-lcm-analysis.json']['complete_trained_unet']['numerical_gates'].update(max_abs=1.))]:
            changed=copy.deepcopy(values);mutate(changed)
            try:check(changed,status,scratch)
            except AssertionError:negatives.append(name)
            else:raise AssertionError('Incorrect evidence accepted: '+name)
    audit['negative_controls']=negatives;current(before)
    (OUT/FILES[-1]).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(native_children=10,java_native_children=5,png_files=9,trained_unet_forward_calls=30,files=len(raw_files),negative_controls=len(negatives),passed=True)),flush=True)


if __name__=='__main__':main()
