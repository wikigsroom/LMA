"""Keep host association evidence separate from model inference and phone acceptance."""
import json
from check_preparation_evidence import canonical


def check(records, status, digest, root):
    core, trained = records['assembly-core.json'], records['assembly-trained.json']
    for record in (core, trained):
        assert record['schema'] == 'lma.assembly-core-tests/1' and record['passed']
        assert not any(record[k] for k in ('modelInference', 'physicalAndroid', 'release_ready', 'automatic_downloads', 'app_service_or_saf_executed'))
        assert record['model_bytes_copied'] == 0
    assert core['checks'] >= 47 and core['actualTrainedAssociations'] == 0
    assert trained['checks'] >= 28 and trained['actualTrainedAssociations'] == 1
    descriptor, = json.loads((root / 'catalogue/model-assemblies.json').read_text(encoding='utf-8'))['plans']
    assert (root / 'catalogue/model-assemblies.json').read_bytes() == (root / 'app/src/main/assets/model-assemblies.json').read_bytes()
    preparation, = json.loads((root / 'catalogue/asset-preparations.json').read_text(encoding='utf-8'))['plans']
    target = next(b for b in json.loads((root / 'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['id'] == descriptor['bundleId'])
    bound = dict(plan=descriptor, preparationFingerprint=digest(canonical(preparation).encode('utf-8')), bundleFingerprint=digest(canonical(target).encode('utf-8')))
    result = trained['association']
    assert result['assemblyFingerprint'] == digest(canonical(bound).encode('utf-8'))
    assert result['bundleFingerprint'] == bound['bundleFingerprint']
    assert result['sourceRetained'] and result['hardlinksVerified'] == result['linkedComponents'] == len(descriptor['roles']) == 20
    assert result['linkedBytes'] == records['preparation-trained.json']['outputBytes'] == 6061184991
    assert result['remainingBytes'] == 3386858497
    assert not any(result[k] for k in ('installed', 'automaticDownloads', 'modelInference', 'physicalAndroid'))
    assert len(target['components']) == 22 and target['evidence']['status'] == 'runtime_assets_only'
    assert not target['evidence']['generationSupported'] and target['pipeline'] == 'ltx098_single_scale_google_q5'
    roles = {item['target'] for item in descriptor['roles']}
    assert all(not c.get('url') for c in target['components'] if c['role'] in roles)
    assert {c['role'] for c in target['components'] if c['role'] not in roles} == {'text_encoder', 'tokenizer_config'}
    assert status['app_model_assembly_registered'] and status['app_model_assembly_core_host_tested'] and status['app_model_assembly_trained_host_tested']
    assert not status['app_model_assembly_android_executed'] and not status['ltx098_app_engine_registered'] and not status['release_ready']
