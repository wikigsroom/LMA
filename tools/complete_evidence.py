"""Version-specific release evidence; preserve every published v0.3.5 record.

All checks are bounded program checks. Random source networks and synthetic
stage fixtures are recorded separately from complete trained-model inference.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from evidence import ROOT, current, fingerprint, version
from preparation_build_inputs import build_inputs
from program_evidence import SOURCES as BASE_SOURCES, MINIMUM as BASE_MINIMUM, CERTIFICATE, counted
from audit_adaptations import MODULES, required_records, require_complete

OUT = ROOT / 'verification/releases' / ('v' + version())
CURRENT_MEDIA = ['community', 'release-workbench', 'expansion', 'multiview', 'shape', 'spatial', 'material', 'ultratex', 'adaptation', 'recommendations']
EXTRA = {
    'api-publication.json': 'build/api-publication-tests/results.json',
    'sub2api-gateway.json': 'build/sub2api-gateway-tests/results.json',
    'ui-performance.json': 'build/device-tests/ui-performance.json',
    'material.json': 'build/material-tests/results.json',
    'vision-android.json': 'build/vision-build-info.json',
    'adaptation-audit-checks.json': 'build/adaptation-audit-tests/results.json',
    'portable-sparse-models.json': 'build/portable-sparse-model-tests/results.json',
    'cascade.json': 'build/cascade-tests/results.json',
    'ultratex-attention.json': 'build/ultratex-attention-tests/results.json',
}
for item in required_records():
    if item not in BASE_SOURCES.values():
        EXTRA[Path(item).parent.name + '.json' if item.endswith('/results.json') else Path(item).name] = item
SOURCES = BASE_SOURCES | EXTRA
MINIMUM = BASE_MINIMUM | {'api-publication': 34, 'sub2api-gateway': 12, 'ui-performance': 8, 'expansion': 875, 'portable-sparse-models': 97, 'cascade': 95, 'ultratex-attention': 47, 'material': 61}
for module in MODULES.values():
    for name, minimum in module['tests'].items():
        if name != 'expansion-tests':
            MINIMUM[name] = max(MINIMUM.get(name, 0), minimum)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def identity(path):
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream, 'sha256').hexdigest())


def declared_deviation():
    relative='verification/releases/v'+version()+'/validation-deviation.json'
    path=ROOT/relative
    if version()=='0.3.10': assert path.exists(), 'Preserve the declared legacy-run deviation'
    if not path.exists():
        return dict(validation_run_scope=('Program gates counted separately from required physical API/model benchmarks' if version()=='0.3.12' else 'Program gate records; optional authorized phone model probes reported separately'),validation_deviation=None,
            accidental_legacy_host_model_execution=False)
    data=read(path)
    assert data['version']==version() and data['excluded_from_program_suite_counts']
    assert not data['physical_model_execution'] and not data['new_model_downloads']
    if version()=='0.3.10':
        assert data['legacy_nano_host_children']==3 and data['legacy_nano_output_records']==2
    return dict(validation_run_scope='Program gate records only; an accidental legacy host-model test is declared separately',
        validation_deviation=relative,accidental_legacy_host_model_execution=True)


def inputs():
    return fingerprint('tools/complete_evidence.py', 'tools/program_evidence.py', 'tools/program_release.py',
        'tools/physical_model_evidence.py', 'tools/physical_api_evidence.py', 'tools/device_model_probe.py', 'tools/check_repository.py', 'tools/package_delivery.py', 'tools/prepare_release.py', 'tools/publish_release.py',
        'tools/release_scope.py', 'tools/audit_adaptations.py', 'tools/physical_evidence.py', 'tools/recommendations.py', 'tools/task_diagnostics_evidence.py',
        *([declared_deviation()['validation_deviation']] if declared_deviation()['validation_deviation'] else []),
        *(['verification/releases/v'+version()+'/physical-models.json'] if (OUT/'physical-models.json').exists() else []),
        *(['docs/media/models/v'+version()+'/manifest.json'] if (ROOT/'docs/media/models'/('v'+version())/'manifest.json').exists() else []),
        *(['verification/releases/v'+version()+'/physical-api.json'] if (OUT/'physical-api.json').exists() else []),
        *(['docs/media/benchmarks/v'+version()+'/manifest.json'] if (ROOT/'docs/media/benchmarks'/('v'+version())/'manifest.json').exists() else []),
        *(['tools/port_update_evidence.py', 'tools/device_lan_http.py', 'tools/export_lan_http_evidence.py',
           'verification/supplemental/v0.3.13/lan-http.json', 'docs/media/tests/lan-http-v0313/manifest.json'] if version() == '0.3.13' else []),
        'research/portability/adaptation-current.json', 'docs/proposals/program-validation-policy.json',
        'docs/proposals/multimodal-release-scope.json', 'catalogue/release-'+version()+'-implementation.json')


def historical_identity():
    """Hash bytes only, including archived opaque assets; never parse them."""
    paths = ['verification/program', 'verification/history', 'verification/research/input-opening-issue']
    tree = subprocess.check_output(['git', 'ls-tree', '-r', '-z', 'v0.3.5', *paths], cwd=ROOT)
    count = 0
    for item in tree.split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        path = ROOT / name.decode('utf-8')
        body = path.read_bytes()
        actual = hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
        assert actual == metadata.split()[2].decode('ascii'), 'Changed historical evidence: '+str(path)
        count += 1
    assert count > 100
    return count


def physical_models_and_api(directory):
    from physical_model_evidence import check as legacy
    from physical_api_evidence import check as api
    result = legacy(directory) | api(directory)
    if version() == '0.3.13':
        from port_update_evidence import check as port_check
        result |= port_check()
    return result


def export():
    require_complete()
    from recommendations import check as recommendations_check
    recommendations_check()
    from release_scope import check as scope_check
    scope_check()
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name, original in SOURCES.items():
        target = OUT / name
        target.write_bytes((ROOT/original).read_bytes())
        sources[name] = dict(source=original, **identity(target))
    media = {}
    for name in CURRENT_MEDIA:
        path = ROOT/'docs/media/development'/name/'manifest.json'
        media[name] = dict(path=path.relative_to(ROOT).as_posix(), **identity(path))
    from physical_evidence import check as physical_check
    physical = physical_check(OUT)
    from task_diagnostics_evidence import check as task_diagnostics_check
    diagnostics = task_diagnostics_check(OUT)
    model_probe_check = physical_models_and_api
    model_probes = model_probe_check(OUT)
    physical_identity = identity(OUT/'physical-device.json') if physical['physical_device_tested'] else None
    status = dict(schema='lma.complete-program-release/1', version=version(), validation_mode='program_only',
        sources=sources, current_ui_media=media, input_fingerprint=inputs(),
        previous_published_evidence='verification/program', previous_release='v0.3.5',
        historical_files_preserved=historical_identity(), release_ready=True,
        full_scope_implementation_complete=True, all_requested_adaptations_complete=True,
        all_benchmark_architectures_integrated=True, full_benchmark_workflows_reproduced=False,
        unported_benchmark_configurations=[], partially_integrated_benchmark_configurations=[],
        implementation_scope='Frozen F01-F12 / selections 01-14,16,17, text and P01-P06; bounded versioned CPU adapters, not arbitrary HF architectures',
        implementation_matrix='catalogue/release-'+version()+'-implementation.json',
        benchmark_portability_audit='research/portability/adaptation-current.json',
        known_implementation_gaps=[], public_matched_complete_packages_verified=False,
        **physical, **diagnostics, physical_program_evidence=physical_identity, **model_probes, complete_model_downloads_for_validation=0,
        complete_model_copies_for_validation=0, model_quality_accepted=False,
        **declared_deviation(),
        background_endurance_tested=False, all_selected_models_tested=False,
        model_weights_in_apk=False, automatic_model_asset_downloads=False,
        browser_closed=True, virtualization_used=False)
    (OUT/'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return check()


def check():
    audit = require_complete()
    from release_scope import check as scope_check
    matrix = scope_check()
    status = read(OUT/'status.json')
    current(status['input_fingerprint'])
    assert status['input_fingerprint'] == inputs()
    assert status['version'] == version() and status['validation_mode'] == 'program_only'
    for key,value in declared_deviation().items(): assert status[key]==value, key
    for key in ('release_ready', 'full_scope_implementation_complete', 'all_requested_adaptations_complete', 'all_benchmark_architectures_integrated', 'browser_closed'):
        assert status[key], key
    assert not status['known_implementation_gaps'] and not status['unported_benchmark_configurations']
    assert not status['partially_integrated_benchmark_configurations'] and not status['full_benchmark_workflows_reproduced']
    from physical_evidence import check as physical_check
    physical = physical_check(OUT)
    for key, value in physical.items(): assert status[key] == value, key
    from task_diagnostics_evidence import check as task_diagnostics_check
    for key, value in task_diagnostics_check(OUT).items(): assert status[key] == value, key
    if physical['physical_device_tested']: assert status['physical_program_evidence'] == identity(OUT/'physical-device.json')
    else: assert status['physical_program_evidence'] is None
    model_probe_check = physical_models_and_api
    for key,value in model_probe_check(OUT).items(): assert status[key]==value,key
    if version() == '0.3.12':
        assert status['physical_device_tested'] and status['physical_api_integration_tested']
        assert status['physical_api_checks'] >= 28 and status['final_video_over_five_seconds']
    if version() == '0.3.13':
        assert status['physical_device_tested'] and status['physical_api_integration_tested']
        assert status['port_upgrade_verified'] and status['api_port'] == 52187
        assert status['physical_direct_lan_tested'] and status['physical_api_checks'] >= 63
        assert status['direct_lan_http_requests'] > 100 and not status['existing_video_generated_by_this_apk']
    for key in ('complete_model_downloads_for_validation', 'complete_model_copies_for_validation', 'model_quality_accepted',
        'background_endurance_tested', 'all_selected_models_tested', 'model_weights_in_apk',
        'automatic_model_asset_downloads', 'virtualization_used'):
        assert not status[key], key
    policy = read(ROOT/'docs/proposals/program-validation-policy.json')
    scope = read(ROOT/'docs/proposals/multimodal-release-scope.json')
    assert policy['validation_mode']=='program_only' and not policy['full_model_execution_required']
    assert not policy['missing_feature_implementation_waived']
    assert scope['selected_ids']==policy['selected_ids']==audit['preserved_scope']['selections']
    assert scope['preserved_recommendation_ids']==['m08','m06','m01'] and policy['lora_required_base_families']==['sd15','sdxl']
    assert status['historical_files_preserved']==historical_identity()
    assert set(status['sources'])==set(SOURCES)
    records = {}
    for name, item in status['sources'].items():
        path=OUT/name
        assert item['source']==SOURCES[name] and identity(path)=={k:item[k] for k in ('bytes','sha256')}
        data=read(path)
        current(data.get('source_inputs',data.get('input_fingerprint',{})))
        assert data.get('source_inputs') or data.get('input_fingerprint'), name
        for key in ('completeModelsRun','completeModelsDownloaded','complete_trained_model_runs','phoneTests','physicalDeviceTests','physical_device_tests','virtualizationUsed','virtualization_used','model_inference_tested','model_inference','modelInference'):
            assert not data.get(key,False), name+' '+key
        records[name]=data
    counts={name:counted(name,records[name+'.json']) for name in MINIMUM}
    for name, minimum in MINIMUM.items():
        assert counts[name]>=minimum, name
    assert counted('adaptation-audit-checks',records['adaptation-audit-checks.json'])>=15
    counts['adaptation-audit-checks']=counted('adaptation-audit-checks',records['adaptation-audit-checks.json'])
    performance = records['ui-performance.json']
    assert performance['version'] == version() and performance['passed'] == 8
    assert performance['apk_sha256'] == records['build.json']['sha256']
    if performance['schema'] == 'lma.physical-ui-performance-comparison/1':
        assert performance['optimized']['mainThread']['gapsOver100Ms'] == 0
    elif performance['schema'] == 'lma.physical-installed-ui-performance/1':
        assert performance['measurement']['existingModelsPreserved'] and performance['measurement']['generationIdle']
        assert performance['measurement']['mainThread']['gapsOver100Ms'] == 0
    else:
        assert performance['schema'] == 'lma.historical-ui-performance-preservation/1'
        assert performance['measured_version'] == '0.3.9' and not performance['current_physical_performance_measured']
        assert identity(ROOT/performance['historical_evidence'])['sha256'] == performance['historical_evidence_sha256']
    build, package, lint=(records[n+'.json'] for n in ('build','package','lint'))
    assert build['version']==version() and build['input_fingerprint']==build_inputs()
    apk=ROOT/'dist'/build['apk']
    assert identity(apk)==dict(bytes=build['bytes'],sha256=build['sha256'])
    assert build['sha256']==package['sha256']==lint['applicationApkSha256'] and build['signatures_verified']
    assert package['signing_certificate_sha256']==CERTIFICATE and package['native_libraries_verified']==41
    for key in ('all_native_dependencies_resolved','all_elf_load_segments_16k_aligned','final_apk_zip_alignment_verified','packaged_ui_matches_source','apk_signatures_independently_verified'):
        assert package[key], key
    assert lint['errors']==0 and lint['java_source_files']==len(list((ROOT/'app/src/main/java').rglob('*.java')))
    ui=records['ui.json'];assert not ui['errors'] and ui['passed']==len(ui['checks'])
    for name,data in records.items():
        if name.endswith('-android.json') or name.endswith('-build-info.json'):
            assert data['abi']=='arm64-v8a' and data['android_api_notes']==[28], name
    f5=records['f5-frontend-tests.json']
    assert f5['exactSegmentation'] and f5['exactPinyinTokens'] and f5['exactVocabularyIds']
    assert records['expansion.json']['java']['actual_host_child_processes']
    assert records['sana-sprint.json']['production_worker_handshake'] and records['sana-sprint.json']['production_parameter_rejection']
    for name,multiscale in [('ltx-multiscale-app.json',True),('ltx-single-scale-app.json',False)]:
        data=records[name];assert data['productionEngineAndQueue'] and data['syntheticNeuralStages'] and data['multiscale']==multiscale
    assert matrix['recipe_templates']==62 and matrix['extension_engine_families']==18
    assert set(status['current_ui_media'])==set(CURRENT_MEDIA)
    for name,item in status['current_ui_media'].items():
        path=ROOT/item['path'];assert identity(path)=={k:item[k] for k in ('bytes','sha256')}
        media=read(path);current(media['input_fingerprint'])
        assert media['version']==version() and media['browser_closed'] and not media['browser_errors']
        assert not media['android_device'] and not media['model_inference'] and not media['weights_downloaded']
        assert len(media['screenshots'])>=5 and len(media['checks'])>=8, name
        for entry in media['files']:
            assert identity(path.parent/entry['file'])=={k:entry[k] for k in ('bytes','sha256')}
    for name, expected in {'license.js':'838317c7653ca35291e9e18f2a7e2d98ed46a10880dfe144176f04ad994433d0',
        'foundation.js':'a2bd9f0a92807a0d60a97884fb3dd123ddfc5cf42258b6577bff36b37f99cb14'}.items():
        assert identity(ROOT/'app/src/main/assets'/name)['sha256']==expected
    result=dict(passed=True,version=version(),validation_mode='program_only',current_records=len(records),
        program_suites=len(counts),program_assertions=sum(counts.values()),checks=counts,
        historical_files_preserved=status['historical_files_preserved'],historical_ui_manifests=15,current_ui_manifests=len(CURRENT_MEDIA),
        original_failure_preserved=True,native_libraries=41,lint_errors=0,lint_warnings=len(lint['warnings']),
        apk=build['apk'],apk_sha256=build['sha256'],release_ready=True,full_scope_implementation_complete=True,
        **physical,**task_diagnostics_check(OUT),**model_probe_check(OUT),implementation_scope=status['implementation_scope'],
        **declared_deviation(),
        all_benchmark_architectures_integrated=True,all_requested_adaptations_complete=True,
        full_benchmark_workflows_reproduced=False,unported_benchmark_configurations=[],partially_integrated_benchmark_configurations=[])
    (ROOT/'build/program-evidence-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
