"""Export fresh idle UI measurements with all installed user assets preserved."""
import json
from pathlib import Path
from evidence import ROOT, current, fingerprint, version


def main():
    path=ROOT/'build/device-tests/performance-optimized.json'
    measured=json.loads(path.read_text(encoding='utf-8'))
    build=json.loads((ROOT/'dist/build-info.json').read_text(encoding='utf-8'))
    current(measured['input_fingerprint'])
    checks={
        'exact_current_signed_apk': measured['apk_sha256']==build['sha256'] and measured['version']==version(),
        'actual_physical_device': measured['physicalDevice'] and not measured['modelInference'],
        'existing_assets_preserved': measured['existingModelsPreserved'] and not measured['completeWeightsDownloaded'],
        'idle_generation': measured['generationIdle'],
        'bounded_warm_snapshot':len(measured['snapshot']['samplesMs'])>=5 and measured['snapshot']['p95Ms']<1000,
        'main_thread_under_200ms':measured['mainThread']['callbacks']>=20 and measured['mainThread']['maximumGapMs']<200,
        'no_main_thread_gaps_over_100ms':measured['mainThread']['gapsOver100Ms']==0,
        'repeated_ui_updates':measured['uiReceive']['viewsCalls']==measured['uiReceive']['updates']==12,
    }
    assert all(checks.values()), {k:v for k,v in checks.items() if not v}
    result=dict(schema='lma.physical-installed-ui-performance/1',version=version(),passed=len(checks),checks=checks,
        apk_sha256=build['sha256'],measurement=measured,current_physical_performance_measured=True,
        historical_zero_model_comparison='verification/releases/v0.3.9/ui-performance.json',
        model_inference=False,complete_trained_model_runs=0,
        input_fingerprint=measured['input_fingerprint']|fingerprint('tools/installed_performance_evidence.py','app/src/main/java','app/src/main/assets/app.js'),
        measurement_scope='Fresh idle app serialization, UI updates and main-thread heartbeat with existing models preserved. No FPS or cross-version speedup is inferred.')
    (ROOT/'build/device-tests/ui-performance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=len(checks),snapshot_p50_ms=measured['snapshot']['p50Ms'],snapshot_p95_ms=measured['snapshot']['p95Ms'],maximum_main_thread_gap_ms=measured['mainThread']['maximumGapMs'])))


if __name__=='__main__':main()
