"""Export/check the current complete program release without running trained models.

Historical model records retain their original identity. Required program
implementation is traced separately; phone and model quality remain untested.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from evidence import current, fingerprint, version
from preparation_build_inputs import build_inputs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification/program'
VERSION = version()
PRIOR_COMMIT = 'da179315377957a449d94817f0a2b7d2030aea44'
CERTIFICATE = '90444a717a55549e2094364d8d7d005cf8b7f4df24562da62cc1884a2f341c17'
SOURCES = {
    'community.json': 'build/community-tests/results.json',
    'expansion.json': 'build/expansion-tests/results.json',
    'spatial.json': 'build/spatial-tests/results.json',
    'spatial-graphs.json': 'build/spatial-shape-tests/graph-results.json',
    'spatial-sparse.json': 'build/spatial-sparse-tests/results.json',
    'spatial-android.json': 'build/spatial-build-info.json',
    'shape.json': 'build/shape-tests/results.json',
    'shape-android.json': 'build/shape-build-info.json',
    'multiview.json': 'build/multiview-tests/results.json',
    'multiview-android.json': 'build/multiview-build-info.json',
    'speech-extra-android.json': 'build/speech_extra-build-info.json',
    'mesh-android.json': 'build/mesh-build-info.json',
    'tts-android.json': 'build/tts-build-info.json',
    'build.json': 'dist/build-info.json',
    'package.json': 'build/package-verification.json',
    'foundation.json': 'build/foundation-tests/results.json',
    'backend.json': 'build/backend-tests/results.json',
    'bundle-pause.json': 'build/bundle-pause-tests/results.json',
    'document-input.json': 'build/document-input-tests/results.json',
    'api.json': 'build/api-tests/results.json',
    'workbench.json': 'build/workbench-tests/results.json',
    'recovery.json': 'build/recovery-tests/results.json',
    'inputs.json': 'build/input-tests/results.json',
    'text.json': 'build/text-tests/results.json',
    'migration.json': 'build/migration-tests/results.json',
    'scheduler.json': 'build/scheduler-tests/results.json',
    'preparations.json': 'build/preparation-tests/results.json',
    'assemblies.json': 'build/assembly-tests/results.json',
    'diffusion.json': 'build/diffusion-tests/results.json',
    'mnn.json': 'build/mnn-tests/results.json',
    'sana-sprint.json': 'build/sana-sprint-tests/results.json',
    'mnn-android.json': 'build/mnn-build-info.json',
    'hub.json': 'build/hub-tests/results.json',
    'recipe-suggestions.json': 'build/recipe-suggestion-tests/results.json',
    'speech-voices.json': 'build/speech-voice-tests/results.json',
    'ui.json': 'build/ui-qa/results.json',
    'lint.json': 'build/android-lint/results.json',
    'ltx-official.json': 'build/ltx098-official-tests/results.json',
    'ltx-multiscale-app.json': 'build/ltx098-multiscale-app-tests/results.json',
    'ltx-single-scale-app.json': 'build/ltx098-app-tests/results.json',
    'ltx-android.json': 'build/ltx098-app-build-info.json',
}
MINIMUM = dict(spatial=188, **{'spatial-graphs':60,'spatial-sparse':109}, shape=161, multiview=63, expansion=533, community=818, foundation=995, backend=138, **{'bundle-pause':22, 'document-input':15},
    api=68, workbench=44, recovery=47, inputs=64, text=66, migration=69, scheduler=151,
    preparations=44, assemblies=47, diffusion=197, mnn=101, hub=80,
    **{'recipe-suggestions':73, 'speech-voices':70, 'sana-sprint':448}, ui=653, **{'ltx-official':89, 'ltx-multiscale-app':280, 'ltx-single-scale-app':127})
CURRENT_MEDIA = ['community', 'release-workbench', 'expansion', 'multiview', 'shape', 'spatial']
MEDIA = ['workbench', 'preflight', 'recovery', 'lcm', 'audio', 'ltx', 'resources',
         'curated', 'speech', 'components', 'wan', 'openmoss', 'sana', 'v030-ltx-official', 'v030-release-workbench']
UI_LOGIC = ['app/src/main/assets/' + name for name in (
    'index.html', 'app.css', 'app.js', 'foundation.css', 'foundation.js',
    'audio-preview.js', 'workbench.js', 'recipes.js', 'versions.js', 'community.js', 'expansion.js', 'glb-preview.js')]


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    return json.loads(path.read_text(encoding='utf-8'))


def identity(path):
    return dict(bytes=path.stat().st_size, sha256=sha(path))


def counted(name, value):
    passed = value.get('passed')
    assert passed, 'Program checks did not pass: ' + name
    if isinstance(passed, int) and not isinstance(passed, bool): return passed
    for key in ('count', 'checks', 'assertions'):
        count = value.get(key)
        if isinstance(count, int): return count
        if isinstance(count, list): return len(count)
        if isinstance(count, dict) and isinstance(count.get('passed'), int): return count['passed']
    raise AssertionError('Missing assertion count: ' + name)


def export():
    assert version() == VERSION
    OUT.mkdir(exist_ok=True)
    items = {}
    for name, original in SOURCES.items():
        data = (ROOT / original).read_bytes()
        (OUT / name).write_bytes(data)
        items[name] = dict(source=original, **identity(OUT / name))
    historical = ROOT / 'verification/history/dev45-program/status.json'
    assert record(historical)['version'] == '0.3.0-dev.45'
    media = {}
    for name in MEDIA:
        path = (ROOT / 'docs/media/history/v0.3.0' / name[5:] if name.startswith('v030-') else ROOT / 'docs/media/development' / name) / 'manifest.json'
        media[name] = dict(path=path.relative_to(ROOT).as_posix(), **identity(path))
    fresh_media = {name:ROOT/'docs/media/development'/name/'manifest.json' for name in CURRENT_MEDIA}
    from release_scope import check as check_scope
    check_scope()
    status = dict(schema='lma.program-release/1', version=VERSION,
        validation_mode='program_only', sources=items, historical_ui_media=media,
        historical_media_comparison='historical_identity_only; not current page or APK validation',
        current_ui_media={name:dict(path=path.relative_to(ROOT).as_posix(), **identity(path)) for name,path in fresh_media.items()},
        prior_checkpoint=dict(commit=PRIOR_COMMIT, version='0.3.0-dev.45',
            path=historical.relative_to(ROOT).as_posix(), **identity(historical)),
        prior_release_archive='verification/history/v0.3.0-program-archive.json',
        prior_additive_release_archive='verification/history/v0.3.1-program-archive.json',
        prior_multiview_release_archive='verification/history/v0.3.3-program-archive.json',
        prior_shape_release_archive='verification/history/v0.3.4-program-archive.json',
        prior_speech_release_archive='verification/history/v0.3.2-program-archive.json',
        policy='docs/proposals/program-validation-policy.json',
        release_ready=True, full_scope_implementation_complete=True,
        implementation_matrix='catalogue/release-'+VERSION+'-implementation.json', known_implementation_gaps=[],
        implementation_scope='frozen F01-F12, existing text and selections 01-14/16/17; not every newly researched architecture',
        benchmark_portability_audit='research/portability/audit-v0.3.5.json',
        all_benchmark_architectures_integrated=False,
        unported_benchmark_configurations=['D04','D05','D07','D08','D09','D10'],
        partially_integrated_benchmark_configurations=['D07'], all_requested_adaptations_complete=False,
        selected_ids=record(ROOT / 'docs/proposals/multimodal-release-scope.json')['selected_ids'],
        physical_device_tests=0, phone_inference_tested=False, model_inference_tested=False,
        all_selected_models_tested=False, model_quality_accepted=False, background_endurance_tested=False,
        historical_model_results_are_current_apk_validation=False,
        complete_model_downloads_for_validation=0, complete_model_copies_for_validation=0,
        small_program_metadata_fetched=True, metadata_audit='research/community/metadata.json',
        sana_text_to_image_variant='matched Sana-Sprint 0.6B MNN; program adapter, not device or image-quality evidence',
        model_weights_in_apk=False, automatic_model_asset_downloads=False,
        browser_closed=True, virtualization_used=False,
        input_fingerprint=fingerprint('tools/program_evidence.py', 'tools/check_repository.py',
            'docs/proposals/program-validation-policy.json', 'docs/proposals/multimodal-release-scope.json',
            'app/build.gradle', 'app/src/main/AndroidManifest.xml', 'catalogue/release-'+VERSION+'-implementation.json',
            'tools/program_release.py', 'tools/package_delivery.py', 'tools/prepare_release.py'))
    status['input_fingerprint'].update(fingerprint('research/portability/audit-v0.3.5.json', 'tools/audit_portability.py', 'tools/audit_shape.py', 'tools/audit_spatial.py', 'verification/history/v0.3.4-program-archive.json'))
    (OUT / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return check()


def check():
    assert version() == VERSION
    status = record(OUT / 'status.json'); current(status['input_fingerprint'])
    assert status['version'] == VERSION and status['validation_mode'] == 'program_only'
    policy = record(ROOT / status['policy'])
    assert policy['validation_mode'] == 'program_only' and not policy['full_model_execution_required']
    assert not policy['missing_feature_implementation_waived']
    scope = record(ROOT / 'docs/proposals/multimodal-release-scope.json')
    assert status['selected_ids'] == policy['selected_ids'] == scope['selected_ids']
    assert scope['preserved_recommendation_ids'] == ['m08', 'm06', 'm01']
    assert policy['lora_required_base_families'] == ['sd15', 'sdxl']
    assert status['release_ready'] and status['full_scope_implementation_complete'] and not status['known_implementation_gaps']
    audit = record(ROOT/status['benchmark_portability_audit'])
    current(audit['input_fingerprint'])
    assert not status['all_benchmark_architectures_integrated'] and not audit['all_benchmark_architectures_integrated']
    assert audit['integrated_architectures']==['trellis2','pixal3d','pixal3d_mv','triposg','partcrafter','ultrashape_1_refine','hunyuan3d_21_shape'] and len(audit['cases'])==16
    assert status['unported_benchmark_configurations']==[x['id'] for x in audit['unported_configurations']]
    assert all(x['remaining_implementation'] for x in audit['unported_configurations'])
    assert status['partially_integrated_benchmark_configurations']==[x['id'] for x in audit['partial_configurations']]
    assert not status['all_requested_adaptations_complete'] and audit['shared_cpu_operator_only_targets']==['D05','D08','D09','D10']
    from release_scope import check as check_scope
    check_scope()
    assert not any(status[key] for key in ['phone_inference_tested', 'model_inference_tested', 'all_selected_models_tested',
        'model_quality_accepted', 'background_endurance_tested', 'model_weights_in_apk',
        'historical_model_results_are_current_apk_validation', 'automatic_model_asset_downloads',
        'virtualization_used', 'complete_model_downloads_for_validation', 'complete_model_copies_for_validation'])
    assert status['physical_device_tests'] == 0 and status['browser_closed']
    assert set(status['sources']) == set(SOURCES)
    records = {}
    for name, item in status['sources'].items():
        assert item['source'] == SOURCES[name] and identity(OUT / name) == {k:item[k] for k in ['bytes','sha256']}
        value = record(OUT / name); current(value['source_inputs'] if name in ['mnn-android.json','ltx-android.json','speech-extra-android.json','mesh-android.json','tts-android.json','multiview-android.json','shape-android.json','spatial-android.json'] else value['input_fingerprint']); records[name] = value
        for key in ['model_inference', 'model_inference_tested', 'modelInference']:
            assert not value.get(key, False), 'Unexpected neural execution in program evidence: ' + name
    counts = {name:counted(name, records[name+'.json']) for name in MINIMUM}
    for name, minimum in MINIMUM.items(): assert counts[name] >= minimum, name
    build, package, lint = (records[name+'.json'] for name in ['build', 'package', 'lint'])
    assert build['input_fingerprint'] == build_inputs() and build['version'] == VERSION
    apk = ROOT / 'dist' / build['apk']
    assert sha(apk) == build['sha256'] == package['sha256'] == lint['applicationApkSha256']
    assert apk.stat().st_size == build['bytes'] and build['signatures_verified']
    assert package['signing_certificate_sha256'] == CERTIFICATE
    assert package['native_libraries_verified'] == 40 and package['all_native_dependencies_resolved']
    assert package['all_elf_load_segments_16k_aligned'] and package['final_apk_zip_alignment_verified']
    assert package['packaged_ui_matches_source'] and package['apk_signatures_independently_verified']
    assert lint['errors'] == 0 and lint['java_source_files'] == len(list((ROOT/'app/src/main/java').rglob('*.java')))
    ui = records['ui.json']; assert not ui['errors'] and ui['passed'] == len(ui['checks'])
    sprint=records['sana-sprint.json']; arm=records['mnn-android.json']
    assert sprint['bounded_graphs'] == 2 and sprint['production_worker_handshake'] and sprint['production_parameter_rejection']
    assert not any(sprint[k] for k in ['trained_model_execution','complete_model_downloaded','physical_android','image_generation'])
    assert arm['abi'] == 'arm64-v8a' and arm['min_sdk'] == 28 and arm['android_api_notes'] == [28]
    assert arm['static_dependencies']['sentencepiece'] == '31646a467d2051eb904e0b45de3a73e91fe1c1e3'
    assert not arm['http_resources_compiled'] and not arm['logcat_compiled'] and not arm['virtualization_used']
    for name in ['speech-extra-android.json','mesh-android.json','tts-android.json','multiview-android.json','shape-android.json','spatial-android.json']:
        arm_extra=records[name]
        assert arm_extra['abi']=='arm64-v8a' and arm_extra['android_api_notes']==[28]
        assert not arm_extra.get('model_data_embedded',False) and not arm_extra.get('deviceValidated',False)
    assert records['expansion.json']['java']['actual_host_child_processes'] and not records['expansion.json']['model_inference']
    for name in ('spatial.json','spatial-sparse.json'):
        extra=records[name]
        assert extra['completeModelsDownloaded']==extra['completeModelsRun']==extra['physicalDeviceTests']==0
        assert not extra['virtualizationUsed']
    assert records['spatial-graphs.json']['trainedModels']==0
    assert records['spatial-sparse.json']['modelAdaptersCompleted']==[]
    spatial_arm=records['spatial-android.json']
    assert spatial_arm['engine']=='spatial_ort' and spatial_arm['runtime_version']=='ORT 1.28.2 API17'
    assert spatial_arm['source_revisions']['D06']=='5e8dcef05df101ab00ab6cd5fdd0ed0c74fbca66'
    assert spatial_arm['source_revisions']['D07']=='82920d643c0dc2f7bfd7255f45f62d386edfe60c'
    ltx, official = records['ltx-android.json'], records['ltx-official.json']
    assert ltx['abi'] == 'arm64-v8a' and ltx['min_sdk'] == 28 and ltx['android_api_notes'] == [28]
    assert 'ltx098_pixart_multiscale_v1' in ltx['pipelines']
    assert not ltx['model_data_embedded'] and not ltx['deviceValidated']
    assert official['fixture_neural_graphs_only'] and official['complete_trained_model_runs'] == 0
    assert official['complete_model_downloads'] == official['complete_model_copies'] == 0
    for name, multiscale in [('ltx-multiscale-app.json', True), ('ltx-single-scale-app.json', False)]:
        case = records[name]
        assert case['productionEngineAndQueue'] and case['syntheticNeuralStages'] and case['multiscale'] == multiscale
        assert not any(case[k] for k in ['physicalAndroid', 'modelInference', 'qualityAccepted', 'numericalAccepted'])
    # Old fixture media retains identity; changed workbench code is checked by current UI tests.
    assert set(status['historical_ui_media']) == set(MEDIA)
    for item in status['historical_ui_media'].values():
        path = ROOT / item['path']; assert identity(path) == {k:item[k] for k in ['bytes','sha256']}
        media = record(path)
        assert media['version'] == ('0.3.0' if 'history/v0.3.0/' in path.as_posix() else '0.3.0-dev.45' if path.parent.name=='sana' else '0.3.0-dev.42') and media['browser_closed'] and not media['browser_errors']
        assert not media['android_device'] and not media['model_inference']
        for file in media['files']:
            assert identity(path.parent / file['file']) == {k:file[k] for k in ['bytes','sha256']}
    assert set(status['current_ui_media']) == set(CURRENT_MEDIA)
    for item in status['current_ui_media'].values():
        path=ROOT/item['path']; assert identity(path)=={k:item[k] for k in ['bytes','sha256']}
        media=record(path); current(media['input_fingerprint'])
        assert media['version']==VERSION and media['browser_closed'] and not media['browser_errors']
        assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded']
        assert len(media['screenshots'])==5
        assert len(media['checks']) >= ({'community':25,'release-workbench':8,'expansion':32,'multiview':19,'shape':17,'spatial':20}[path.parent.name])
        for file in media['files']: assert identity(path.parent/file['file'])=={k:file[k] for k in ['bytes','sha256']}
    prior = status['prior_checkpoint']; assert prior['commit'] == PRIOR_COMMIT and prior['version'] == '0.3.0-dev.45'
    assert identity(ROOT / prior['path']) == {k:prior[k] for k in ['bytes','sha256']}
    tree = subprocess.run(['git', 'ls-tree', '-rz', PRIOR_COMMIT, 'verification/program'], cwd=ROOT, capture_output=True, check=True)
    archived = ROOT / 'verification/history/dev45-program'
    originals = {}
    for item in tree.stdout.decode('utf-8').strip('\0').split('\0'):
        metadata, path = item.split('\t'); originals[Path(path).name] = metadata.split()[2]
    assert set(originals) == {p.name for p in archived.iterdir() if p.is_file()}
    for name, blob in originals.items():
        data = (archived / name).read_bytes()
        assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest() == blob, 'Changed historical evidence: '+name
    # Preserve the first reproduced failure without evaluating old model acceptance gates.
    archived_release = record(ROOT / status['prior_release_archive'])
    assert archived_release['version'] == '0.3.0' and archived_release['commit'] == 'd659da11e3b3d81fedbfbd1ba54344612c5bf6da'
    archive_root = ROOT / archived_release['archivePath']
    assert set(archived_release['files']) == {p.name for p in archive_root.iterdir() if p.is_file()}
    for name, item in archived_release['files'].items():
        assert Path(name).name == name
        body = (archive_root / name).read_bytes()
        assert identity(archive_root / name) == {k:item[k] for k in ['bytes', 'sha256']}
        assert hashlib.sha1(('blob '+str(len(body))+'\0').encode()+body).hexdigest() == item['gitBlob']
        frozen_blob = subprocess.check_output(['git', 'rev-parse', archived_release['commit']+':verification/program/'+name], cwd=ROOT).decode('ascii').strip()
        assert frozen_blob == item['gitBlob'], 'Archived release identity changed: '+name
    previous=record(ROOT/status['prior_additive_release_archive'])
    assert previous['version']=='0.3.1'
    for name,item in previous['files'].items():
        path=ROOT/previous['directory']/name
        assert identity(path)=={k:item[k] for k in ['bytes','sha256']}
        data=path.read_bytes()
        assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==item['gitBlob']
        frozen=subprocess.check_output(['git','rev-parse',previous['commit']+':verification/program/'+name],cwd=ROOT).decode('ascii').strip()
        assert frozen==item['gitBlob'],'Changed v0.3.1 evidence: '+name
    previous=record(ROOT/status['prior_speech_release_archive'])
    assert previous['version']=='0.3.2' and previous['commit']=='3f59f2e9f61e72ea3400fe268f85f959c759fc3b'
    archive_root=ROOT/previous['directory']
    assert set(previous['files'])=={p.name for p in archive_root.iterdir() if p.is_file()}
    for name,item in previous['files'].items():
        path=archive_root/name
        assert identity(path)=={k:item[k] for k in ['bytes','sha256']}
        with path.open('rb') as stream:
            blob_hash=hashlib.sha1(('blob '+str(item['bytes'])+'\0').encode())
            while chunk:=stream.read(1024*1024):blob_hash.update(chunk)
        assert blob_hash.hexdigest()==item['gitBlob']
        frozen=subprocess.check_output(['git','rev-parse',previous['commit']+':verification/program/'+name],cwd=ROOT).decode('ascii').strip()
        assert frozen==item['gitBlob'],'Changed v0.3.2 evidence: '+name
    previous=record(ROOT/status['prior_multiview_release_archive'])
    assert previous['version']=='0.3.3' and previous['commit']=='e59b76dbccd3a8cfdf09944f0d1ab08069b18786'
    archive_root=ROOT/previous['directory']
    assert set(previous['files'])=={p.name for p in archive_root.iterdir() if p.is_file()}
    for name,item in previous['files'].items():
        path=archive_root/name;assert identity(path)=={k:item[k] for k in ['bytes','sha256']}
        data=path.read_bytes();assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==item['gitBlob']
        frozen=subprocess.check_output(['git','rev-parse',previous['commit']+':verification/program/'+name],cwd=ROOT).decode('ascii').strip()
        assert frozen==item['gitBlob'],'Changed v0.3.3 evidence: '+name
    previous=record(ROOT/status['prior_shape_release_archive'])
    assert previous['version']=='0.3.4' and previous['commit']=='03c19aa892a5224b92ca3289914a366ca488cbbf'
    assert subprocess.check_output(['git','rev-parse','v0.3.4^{commit}'],cwd=ROOT).decode('ascii').strip()==previous['commit']
    archived=ROOT/previous['directory']
    assert len(previous['files'])==38 and set(previous['files'])=={p.name for p in archived.iterdir() if p.is_file()}
    tree=subprocess.check_output(['git','ls-tree','-rz',previous['commit'],'verification/program','docs/media/development'],cwd=ROOT)
    frozen={}
    for item in tree.decode('utf-8').strip('\0').split('\0'):
        metadata,path=item.split('\t');frozen[path]=metadata.split()[2]
    assert set(previous['files'])=={Path(p).name for p in frozen if p.startswith('verification/program/')}
    assert len(previous['media'])==40
    media_root=ROOT/'docs/media/history/v0.3.4'
    assert set(previous['media'])=={p.relative_to(ROOT).as_posix() for p in media_root.rglob('*') if p.is_file()}
    for path,item,original in [(archived/name,item,'verification/program/'+name) for name,item in previous['files'].items()]+[(ROOT/name,item,item['original']) for name,item in previous['media'].items()]:
        assert identity(path)=={k:item[k] for k in ('bytes','sha256')}
        data=path.read_bytes()
        assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==item['gitBlob']==frozen[original], 'Changed v0.3.4 archive: '+original
    issue = ROOT / 'verification/research/input-opening-issue'
    capture = record(issue / 'capture.json'); assert not capture['host_contract_passed']
    for name, item in capture['files'].items():
        assert Path(name).name == name and identity(issue/name) == item
    for name, expected in {
        'license.js':'838317c7653ca35291e9e18f2a7e2d98ed46a10880dfe144176f04ad994433d0',
        'foundation.js':'a2bd9f0a92807a0d60a97884fb3dd123ddfc5cf42258b6577bff36b37f99cb14'}.items():
        assert sha(ROOT/'app/src/main/assets'/name) == expected
    result = dict(passed=True, version=VERSION, validation_mode='program_only',
        current_records=len(records), program_suites=len(counts), program_assertions=sum(counts.values()),
        checks=counts, historical_ui_manifests=len(MEDIA), current_ui_manifests=len(CURRENT_MEDIA), original_failure_preserved=True,
        native_libraries=40, lint_errors=0, lint_warnings=len(lint['warnings']),
        apk=build['apk'], apk_sha256=build['sha256'], release_ready=True, full_scope_implementation_complete=True,
        model_inference_tested=False, phone_inference_tested=False)
    result.update(implementation_scope=status['implementation_scope'],all_benchmark_architectures_integrated=False,
        all_requested_adaptations_complete=False,
        partially_integrated_benchmark_configurations=status['partially_integrated_benchmark_configurations'],
        unported_benchmark_configurations=status['unported_benchmark_configurations'])
    (ROOT/'build/program-evidence-check.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--export',action='store_true')
    args=parser.parse_args(); print(json.dumps(export() if args.export else check()))
