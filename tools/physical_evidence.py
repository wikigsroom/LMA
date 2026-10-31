"""Optional, version-bound physical program evidence; never a model-quality gate."""
import json
import hashlib
from pathlib import Path
from evidence import ROOT, current, version


def read(path):
    return Path(path).read_text(encoding='utf-8')


def load(path):
    return json.loads(read(path))


def check(directory):
    path = Path(directory) / 'physical-device.json'
    if not path.exists():
        return dict(physical_device_tests=0, physical_device_tested=False,
                    background_program_tested=False, screen_off_program_seconds=0)
    data = load(path)
    build = load(ROOT / 'dist/build-info.json')
    assert data['status'] == 'passed' and data['version'] == version()
    assert data['apk_sha256'] == build['sha256']
    current(data['input_fingerprint'])
    checks = data['instrumentation']['checks'] + data['external_program_checks']
    assert data['instrumentation']['status'] == 'passed'
    assert data['instrumentation']['physicalDevice'] is True
    assert data['physical_device_tests'] == len(checks) and len(checks) >= 19
    assert not any(data.get(key, False) for key in (
        'phone_inference_tested', 'model_inference_tested', 'background_endurance_tested',
        'complete_model_downloads_for_validation', 'emulator_used', 'virtualization_used'))
    assert data['external_api_auth_tested'] and data['background_program_tested']
    assert data['screen_off_program_seconds'] >= 60
    assert len(data['screen_off_health_samples_seconds']) >= 7
    assert int(data['device']['api']) >= 28 and 'arm64-v8a' in data['device']['abis']
    media_path = ROOT/'docs/media/device'/('v'+version())/'manifest.json'
    if media_path.exists():
        media = load(media_path)
        assert media['version']==version() and media['apk_sha256']==build['sha256']
        assert media['android_device'] and not media['desktop_fixture']
        assert not media['model_inference'] and not media['weights_downloaded']
        assert media['reviewed_app_only'] and media['playback_speed']==1
        current(media['input_fingerprint'])
        assert len(media['screenshots'])==7 and len(media['files'])==9
        for item in media['files']:
            path = media_path.parent/item['file']
            assert path.parent==media_path.parent and path.stat().st_size==item['bytes']
            with path.open('rb') as stream:
                assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
    return dict(physical_device_tests=len(checks), physical_device_tested=True,
                background_program_tested=True, screen_off_program_seconds=data['screen_off_program_seconds'])


def export(directory):
    """Allowlist only: no serial, Wi-Fi endpoint, pairing code, key or personal logs."""
    original = load(ROOT / 'build/device-tests/device-results.json')
    allowed = ('checked_at', 'status', 'device', 'apk_sha256', 'input_fingerprint',
        'instrumentation', 'physical_device_tests', 'external_program_checks',
        'external_api_auth_tested', 'background_program_tested',
        'screen_off_program_seconds', 'screen_off_health_samples_seconds',
        'phone_inference_tested', 'background_endurance_tested', 'emulator_used')
    data = {key: original[key] for key in allowed}
    assert 'apiKey' not in data['instrumentation']
    data.update(schema='lma.physical-program-acceptance/1', version=version(),
        validation_mode='program_only', model_inference_tested=False,
        complete_model_downloads_for_validation=0, virtualization_used=False,
        scope='Real Android UI, SQLite, no-model API and short screen-off foreground service; no trained-model inference or endurance')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'physical-device.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return check(directory)


if __name__ == '__main__':
    print(json.dumps(export(ROOT / 'verification/releases' / ('v' + version())), ensure_ascii=False))
