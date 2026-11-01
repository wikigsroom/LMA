"""Publish allowlisted program diagnostics, excluding private task inputs and asset contents."""
import json
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def check(directory):
    path = Path(directory)/'task-diagnostics.json'
    if version() == '0.3.10': assert path.exists(), 'Current task diagnostics must be preserved'
    if not path.exists():
        return dict(physical_task_diagnostic_checks=0)
    data = read(path)
    current(data['input_fingerprint'])
    assert data['version'] == version() and data['status'] == 'passed'
    assert data['apk_sha256'] == read(ROOT/'dist/build-info.json')['sha256']
    assert data['physicalDevice'] and not data['modelInference'] and not data['completeWeightsDownloaded']
    assert len(data['checks']) == 10 and data['failed_records_removed'] == 5
    assert data['successful_records_preserved'] == 2 and data['artifacts_preserved'] == 5
    assert data['installed_models_preserved'] == 5
    return dict(physical_task_diagnostic_checks=10)


def export():
    source = ROOT/'build/device-task-audit'
    before = read(source/'device-diagnostics-private.json')
    after = read(source/'device-diagnostics-fixed-private.json')
    cleaned = read(source/'cleanup-private.json')
    jobs = read(source/'jobs-before-private.json')
    assert before['version'] == '0.3.9' and after['version'] == version()
    assert before['status'] == after['status'] == cleaned['status'] == 'passed'
    assert not before['nioHardlink']['success'] and 'EACCES' in before['osHardlink']['message']
    assert before['nioSymlink']['success'] and before['osSymlink']['success']
    assert not before['workspace']['success'] and after['workspace']['success']
    for report in (before, after):
        assert not report['modelInference'] and not report['completeWeightsDownloaded']
        assert sum(len(m['components']) for m in report['models']) == 17
        assert all(c['present'] and c['bytesMatch'] and c['receiptValid'] for m in report['models'] for c in m['components'])
        assert report['wanInfo']['exit'] == 0 and report['wanDevices']['exit'] == 0
        assert 'Vulkan 1.2 required' in report['wanDevices']['output']
    assert not after['wanPreflight']['canEnqueue'] and after['wanPreflight']['historyUnchanged']
    assert any('Vulkan 1.2' in x['message'] for x in after['wanPreflight']['issues'])
    assert len(cleaned['removed_failed_records']) == 5 and cleaned['successful_tasks_preserved'] == 2
    assert cleaned['artifacts_preserved'] == 5 and len(cleaned['installed_model_ids_preserved']) == 5
    failed = sorted((j for j in jobs if j['state'] == 'failed'), key=lambda j: j['createdAt'])
    assert {j['id'] for j in failed} == {j['id'] for j in cleaned['removed_failed_records']}
    failures = []
    for i, job in enumerate(failed, 1):
        video = job['request']['type'] == 'video.generate'
        failures.append(dict(case=i, bundle_id=job['request']['bundleId'],
            elapsed_ms=job['finishedAt']-job['startedAt'],
            diagnosed_cause='vulkan_1_2_required' if video else 'hardlink_access_denied',
            disposition='archived_privately_then_removed',
            fix='preflight_rejects_unsupported_gpu; optional_explicit_cpu_import' if video else 'verified_symlink_fallback_without_weight_copy',
            complete_model_retried=False))
    data = dict(schema='lma.physical-task-diagnostics/1', version=version(), status='passed',
        apk_sha256=read(ROOT/'dist/build-info.json')['sha256'], baseline_version='0.3.9',
        physicalDevice=True, modelInference=False, completeWeightsDownloaded=False,
        checks=['Hardlink EACCES reproduced with four-byte owned source',
            'Symbolic links accepted by the same Android app identity',
            'Original workspace staging failure reproduced',
            'Fixed workspace resolves the same four-byte source',
            'Seventeen installed component receipts and sizes remain valid',
            'Signed Wan executable starts successfully without weights',
            'Native device query reports Vulkan 1.2 required and no GPU route',
            'Production preflight rejects unsupported GPU without adding jobs',
            'Exactly five archived failed records removed; two successes retained',
            'Five artifacts and five installed models/settings preserved'],
        task_failures=failures, failed_records_removed=5, successful_records_preserved=2,
        artifacts_preserved=5, installed_models_preserved=5,
        full_3d_generation_retested=False, full_video_generation_retested=False,
        raw_prompts_published=False, raw_asset_contents_published=False,
        input_fingerprint=fingerprint('tools/task_diagnostics_evidence.py',
            'tests/android/com/lma/app/DeviceTaskDiagnostics.java', 'app/src/main/java',
            'docs/examples/wan21_13b_q4_cpu_phone.json'))
    out = ROOT/'verification/releases'/('v'+version())
    out.mkdir(parents=True, exist_ok=True)
    (out/'task-diagnostics.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(check(out)))


if __name__ == '__main__':
    export()
