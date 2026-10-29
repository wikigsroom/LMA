"""Audit App preparation integration without promoting host conversion to phone inference."""
import json
from evidence import current


def canonical(value):
    # DataFiles.canonical is the existing App fingerprint protocol: sorted
    # objects and arrays include an element terminator, including the last one.
    if isinstance(value, dict):
        return '{' + ''.join(json.dumps(k, ensure_ascii=False) + ':' + canonical(value[k]) + ',' for k in sorted(value)) + '}'
    if isinstance(value, list):
        return '[' + ''.join(canonical(item) + ',' for item in value) + ']'
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def check(records, status, digest, root):
    core = records['preparation-core.json']
    trained = records['preparation-trained.json']
    for record in (core, trained):
        current(record['input_fingerprint'])
        assert record['schema'] == 'lma.preparation-core-tests/1' and record['passed']
        assert not any(record[k] for k in ('model_inference', 'physical_android', 'release_ready', 'app_service_or_saf_executed'))
    assert core['checks'] >= 44 and core['fixtureNativeChildren'] == 4
    assert core['actual_trained_preparations'] == 0
    assert trained['checks'] == 5 and trained['actual_trained_preparations'] == 1
    assert trained['nativeChildren'] == 2 and trained['component_inference_validation_reused']
    prepared = trained['prepared_assets']
    assert prepared['hostProductionCore'] and prepared['sourceRetained']
    assert not any(prepared[k] for k in ('modelInference', 'physicalAndroid', 'releaseReady'))
    catalogue = json.loads((root / 'catalogue/asset-preparations.json').read_text(encoding='utf-8'))
    assert (root / 'catalogue/asset-preparations.json').read_bytes() == (root / 'app/src/main/assets/asset-preparations.json').read_bytes()
    plan, = catalogue['plans']
    assert digest(canonical(plan).encode('utf-8')) == prepared['planFingerprint']
    assert plan['id'] == prepared['planId'] == 'ltx098_dit_vae_v1'
    assert prepared['sourceBytes'] == plan['sourceBytes'] == 6340744492
    assert prepared['sourceSha256'] == plan['sourceSha256']
    source = next(b for b in json.loads((root / 'catalogue/model-bundles.json').read_text(encoding='utf-8'))['bundles'] if b['id'] == prepared['bundleId'])
    component, = source['components']
    assert component['sha256'] == plan['sourceSha256'] and component['bytes'] == plan['sourceBytes']
    assert source['tasks'] == ['video'] and source['evidence']['status'] == 'source_assets_only'
    assert not source['evidence']['generationSupported']
    outputs = {stage['id'] + '/' + item['file']: item for stage in plan['stages'] for item in stage['outputs']}
    assert len(outputs) == len(prepared['outputs']) == 20
    for actual in prepared['outputs']:
        expected = outputs[actual['path']]
        assert all(actual[k] == expected[k] for k in ('role', 'bytes', 'sha256'))
    assert sum(f['bytes'] for f in outputs.values()) == prepared['bytes'] == trained['outputBytes'] == 6061184991
    assert outputs['dit/ltx098-dit.gguf']['sha256'] == records['ltx098-prepare.json']['trained']['native']['output_sha256']
    for stem, receipt in trained['builds'].items():
        current(receipt['input_fingerprint'])
        assert receipt == records[stem + '-host.json']
    manifest = json.loads((root / 'app/src/main/assets/engine-builds.json').read_text(encoding='utf-8'))
    lock = json.loads((root / 'third_party/engine-lock.json').read_text(encoding='utf-8'))
    programs = manifest['preparations']
    assert len(programs) == 2 and {p['engine'] for p in programs} == {s['module'] for s in plan['stages']}
    for program in programs:
        pinned = next(p for p in lock['preparations'] if p['engine'] == program['engine'])
        assert all(program[k] == pinned[k] for k in ('file', 'bytes', 'sha256'))
        assert program['file'] in records['package.json']['native']
        assert not program['model_data_embedded'] and not program['deviceValidated']
    assert source['engine'] not in {p['engine'] for p in manifest['engines']}
    assert all(status[k] for k in ('app_asset_preparation_registered', 'app_asset_preparation_core_host_tested', 'app_asset_preparation_trained_host_tested'))
    assert not any(status[k] for k in ('app_asset_preparation_android_executed', 'ltx098_app_engine_registered', 'ltx098_complete_android_video_tested', 'release_ready'))
