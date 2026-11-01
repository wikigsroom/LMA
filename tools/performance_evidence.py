"""Export measured, zero-model physical UI performance without exposing app state."""
import json
import hashlib
import re
import subprocess
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def export():
    if version() != '0.3.9':
        return preserve()
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


def preserve():
    """Keep measured v0.3.9 numbers historical; verify relevant UI paths have not changed."""
    measured_path = ROOT/'verification/releases/v0.3.9/ui-performance.json'
    measured = read(measured_path)
    paths = ['app/src/main/java/com/lma/app/MainActivity.java',
        'app/src/main/java/com/lma/app/core/BundleStore.java',
        'app/src/main/java/com/lma/app/LocalEngines.java',
        'app/src/main/assets/app.js', 'app/src/main/assets/recommendations.js',
        'tests/android/com/lma/app/DevicePerformance.java', 'app/src/main/java/com/lma/app/LmaApp.java']
    for name in paths:
        previous = subprocess.check_output(['git', 'show', 'v0.3.9:'+name], cwd=ROOT)
        current_bytes = (ROOT/name).read_bytes()
        if name.endswith('/LmaApp.java'):
            previous = re.sub(rb'VERSION = "[^"]+"', b'VERSION = "release"', previous)
            current_bytes = re.sub(rb'VERSION = "[^"]+"', b'VERSION = "release"', current_bytes)
        assert previous == current_bytes, 'UI performance source changed; measure again: '+name
    assert measured['version'] == '0.3.9' and measured['passed'] == 8
    build = read(ROOT/'dist/build-info.json')
    result = dict(schema='lma.historical-ui-performance-preservation/1', version=version(), passed=8,
        apk_sha256=build['sha256'], current_physical_performance_measured=False,
        measured_version='0.3.9', measured_apk_sha256=measured['apk_sha256'],
        historical_evidence='verification/releases/v0.3.9/ui-performance.json',
        historical_evidence_sha256=hashlib.sha256(measured_path.read_bytes()).hexdigest(),
        checked_source_paths=paths, model_inference=False, complete_trained_model_runs=0,
        input_fingerprint=fingerprint('tools/performance_evidence.py', measured_path.relative_to(ROOT).as_posix(), *paths),
        measurement_scope='Eight preservation checks: seven relevant source paths and the immutable historical result; no current-version latency benchmark')
    (ROOT/'build/device-tests/ui-performance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(version=version(), preservation_checks=8, fresh_performance_measurement=False)))


if __name__ == '__main__':
    export()
