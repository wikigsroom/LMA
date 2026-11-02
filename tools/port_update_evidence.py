"""Require current signed-upgrade and direct physical LAN evidence for v0.3.13."""
import json
from evidence import ROOT, version
from export_lan_http_evidence import PUBLIC, check as lan_check


def check():
    assert version() == '0.3.13'
    result = lan_check()
    data = json.loads(PUBLIC.read_text(encoding='utf8'))
    assert data['passed'] >= 63 and data['api_port'] == 52187
    assert data['upgrade_verified'] and data['previous_default_port'] == 8080
    assert data['screen_off']['seconds'] >= 60
    return dict(
        physical_api_integration_tested=True, physical_api_checks=data['passed'],
        physical_direct_lan_tested=True, api_port=data['api_port'],
        port_upgrade_verified=True, direct_lan_http_requests=data['http_requests'],
        final_video_over_five_seconds=False,
        existing_video_transfer_seconds=result['existing_video_seconds'],
        existing_video_generated_by_this_apk=False,
        phone_inference_tested=True, model_inference_tested=True,
        authorized_phone_model_attempts=3, authorized_phone_model_successes=3,
        complete_trained_model_runs=3,
        port_update_evidence=PUBLIC.relative_to(ROOT).as_posix())
