"""Export measured, zero-model physical UI performance without exposing app state."""
import json
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def export():
    build = read(ROOT/'dist/build-info.json')
    baseline = read(ROOT/'build/device-tests/performance-baseline.json')
    optimized = read(ROOT/'build/device-tests/performance-optimized.json')
    previous = read(ROOT/'verification/releases/v0.3.8/build.json')
    for data in (baseline, optimized):
        current(data['input_fingerprint'])
        assert data['status'] == 'passed' and data['physicalDevice']
        assert not data['modelInference'] and not data['completeWeightsDownloaded']
        assert data['bundleCount'] == 82 and data['uiReceive']['cards'] == 14
        assert len(data['snapshot']['samplesMs']) == 7
    assert baseline['version'] == '0.3.8' and baseline['apk_sha256'] == previous['sha256']
    assert optimized['version'] == version() and optimized['apk_sha256'] == build['sha256']
    assert baseline['device'] == optimized['device']
    assert optimized['snapshot']['p50Ms'] < baseline['snapshot']['p50Ms'] / 2
    assert optimized['mainThread']['maximumGapMs'] < 200
    assert optimized['mainThread']['gapsOver100Ms'] == 0
    assert optimized['uiReceive']['viewsCalls'] == optimized['uiReceive']['updates'] == 12
    assert optimized['uiReceive']['mutations'] < baseline['uiReceive']['mutations']
    result = dict(schema='lma.physical-ui-performance-comparison/1', version=version(), passed=8,
        apk_sha256=build['sha256'], baseline=baseline, optimized=optimized,
        input_fingerprint=fingerprint('tools/performance_evidence.py', 'tools/profile_device.py',
            'tests/android/com/lma/app/DevicePerformance.java', 'app/src/main/java',
            'app/src/main/assets/app.js', 'app/src/main/assets/recommendations.js'),
        model_inference=False, complete_trained_model_runs=0,
        measurement_scope='Warm zero-model status serialization and UI updates on one physical phone; not FPS, cold-start, inference or endurance benchmarks')
    out = ROOT/'build/device-tests/ui-performance.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(version=version(), passed=result['passed'], main_thread_maximum_gap_ms=optimized['mainThread']['maximumGapMs'])))


if __name__ == '__main__':
    export()
